"""Bill of materials of the work part's assembly: ``nx_get_bill_of_materials`` and its
CSV export ``nx_export_bill_of_materials``. Reads only.

Rows group the occurrences by their part file (the prototype), in the order the parts
first appear depth first, so the item numbers follow the assembly navigator:

- ``parts`` (default): purchased and made parts only, every leaf occurrence counted at
  every level (a subassembly used twice doubles its parts' quantities).
- ``top_level``: the work part's direct components, subassemblies as one row each.
- ``indented``: one row per part under each assembly, item numbers ``1``, ``1.1``, ...
  and the quantity per parent assembly, as on a structured parts list.

A suppressed component (or one under a suppressed parent) is left out and counted in
``skipped`` unless ``include_suppressed``. A component whose part is not loaded keeps
its row with ``loaded`` false and no material: open the assembly with
``load_components`` to fill it. Material: the physical materials of the part's solid
bodies (``kit.massprops.material_name``), ``None`` when none is assigned. Attributes:
string user attributes of the part (``DB_PART_NO``, ``DESCRIPTION`` ...), ``None``
where a part has none. Weights per part: ``nx_measure_assembly_mass(group_by="part")``.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Annotated, Any, Literal, TypedDict

from nx_mcp.core.catalogue import tool
from nx_mcp.core.errors import fail
from nx_mcp.core.tx import Tx
from nx_mcp.core.types import Doc, Items, PathTo, Text
from nx_mcp.domains.assembly import common
from nx_mcp.kit import files, records
from nx_mcp.kit import massprops as mp
from nx_mcp.kit import parts as kparts

Structure = Literal["parts", "top_level", "indented"]
AttributeTitles = Annotated[
    list[Annotated[str, Text(64)]],
    Items(1, 10),
    Doc("Part attribute titles to add as columns, e.g. DB_PART_NO, DESCRIPTION"),
]
MAX_ROWS = 500


class BomRow(TypedDict, total=False):
    item: str
    level: int
    part: str
    name: str
    quantity: int
    material: str | None
    loaded: bool
    attributes: dict[str, str | None]
    components: list[str]


class BomData(TypedDict):
    structure: str
    rows: list[BomRow]
    row_count: int
    part_count: int
    total_quantity: int
    skipped: int
    truncated: bool


def _key(component) -> str:
    """The part a row counts: its file, or the component name when it is not loaded."""
    path = kparts.prototype_file(component)
    return path.casefold() if path else "?" + str(getattr(component, "Name", "") or "")


def _materials(prototype) -> str | None:
    names: list[str] = []
    for body in list(getattr(prototype, "Bodies", None) or []):
        if not getattr(body, "IsSolidBody", True):
            continue
        name = mp.material_name(body)
        if name and name not in names:
            names.append(name)
    return ", ".join(names) or None


def _attribute(tx, prototype, title) -> str | None:
    if prototype is None or not hasattr(prototype, "HasUserAttribute"):
        return None
    try:
        return records.get_text(tx, prototype, title)
    except Exception:
        return None


class _Bom:
    def __init__(self, tx, structure, include_suppressed, attributes):
        self.tx = tx
        self.structure = structure
        self.include_suppressed = include_suppressed
        self.attributes = list(attributes or [])
        self.rows: list[dict[str, Any]] = []
        self.skipped = 0

    def _row(self, component, item, level) -> dict[str, Any]:
        prototype = getattr(component, "Prototype", None)
        path = kparts.prototype_file(component)
        loaded = bool(path) and bool(getattr(prototype, "IsFullyLoaded", True))
        row: dict[str, Any] = {
            "item": item,
            "level": level,
            "part": common.relative_path(self.tx, path) if path else "",
            "name": Path(path).stem if path else str(getattr(component, "Name", "") or ""),
            "quantity": 0,
            "material": _materials(prototype) if loaded else None,
            "loaded": loaded,
            "components": [],
        }
        if self.attributes:
            row["attributes"] = {t: _attribute(self.tx, prototype, t) for t in self.attributes}
        return row

    def _kept(self, children) -> list:
        out = []
        for child in children:
            if getattr(child, "IsSuppressed", False) and not self.include_suppressed:
                self.skipped += 1 + sum(1 for _ in _descendants(child))
                continue
            out.append(child)
        return out

    def _count(self, groups, order, component, level, prefix) -> None:
        key = _key(component)
        row = groups.get(key)
        if row is None:
            item = f"{prefix}{len(order) + 1}"
            row = groups[key] = self._row(component, item, level)
            order.append(row)
        row["quantity"] += 1
        if len(row["components"]) < 5:
            row["components"].append(self.tx.ref(component, "component")["id"])

    def build(self, root) -> None:
        children = self._kept(root.GetChildren())
        if self.structure == "indented":
            self._indented(children, 0, "")
            return
        groups: dict[str, dict[str, Any]] = {}
        if self.structure == "top_level":
            for child in children:
                self._count(groups, self.rows, child, 0, "")
            return
        todo = list(reversed(children))
        while todo:
            node = todo.pop()
            below = self._kept(node.GetChildren())
            if below:
                todo.extend(reversed(below))
            else:
                self._count(groups, self.rows, node, 0, "")

    def _indented(self, children, level, prefix) -> None:
        groups: dict[str, dict[str, Any]] = {}
        order: list[dict[str, Any]] = []
        first: dict[str, Any] = {}
        for child in children:
            first.setdefault(_key(child), child)
            self._count(groups, order, child, level, prefix)
        for key, row in zip(first, order, strict=True):  # both in first-appearance order
            self.rows.append(row)
            sub = self._kept(first[key].GetChildren())
            if sub:
                self._indented(sub, level + 1, row["item"] + ".")


def _descendants(component):
    for child in component.GetChildren():
        yield child
        yield from _descendants(child)


def bill(tx, structure="parts", include_suppressed=False, attributes=None) -> dict:
    """The full bill (every row) for either tool."""
    root = getattr(getattr(tx.part, "ComponentAssembly", None), "RootComponent", None)
    if root is None or not root.GetChildren():
        fail("NX_NOT_FOUND", "The work part has no components",
             hint="Open or make an assembly the work part, or add components with "
                  "nx_create_component")  # fmt: skip
    walk = _Bom(tx, structure, include_suppressed, attributes)
    walk.build(root)
    rows = walk.rows
    counted = rows if structure != "indented" else [r for r in rows if r["level"] == 0]
    return {
        "structure": structure,
        "rows": rows,
        "row_count": len(rows),
        "part_count": len({(r["part"] or r["name"]).casefold() for r in rows}),
        "total_quantity": sum(r["quantity"] for r in counted),
        "skipped": walk.skipped,
    }


def _summary(a, say) -> str:
    return f"Bill of materials ({a.get('structure') or 'parts'})"


@tool(
    effect="read",
    label="Get bill of materials",
    summary=_summary,
    keywords=(
        "bill of materials",
        "bom",
        "parts list",
        "stueckliste",
        "quantities",
        "indented bom",
        "part numbers",
    ),  # fmt: skip
    requires=("work_part", "assembly"),
    cost="light",
    example={"structure": "indented", "attributes": ["DB_PART_NO"]},
)
def nx_get_bill_of_materials(
    tx: Tx,
    *,
    structure: Structure = "parts",
    include_suppressed: bool = False,
    attributes: AttributeTitles | None = None,
) -> BomData:
    """Bill of materials of the work assembly: one row per part with item number, quantity,
    material and attributes. structure parts: leaf parts counted over all levels; top_level:
    direct components; indented: item 1.1 rows, quantity per parent. Suppressed: skipped."""
    out = bill(tx, structure, include_suppressed, attributes)
    out["truncated"] = len(out["rows"]) > MAX_ROWS
    out["rows"] = out["rows"][:MAX_ROWS]
    return out  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# CSV export


def csv_text(out, attributes) -> str:
    """The bill as one Excel-friendly table (semicolons, as Excel reads them in CH/DE)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
    titles = list(attributes or [])
    writer.writerow(["item", "level", "quantity", "name", "part", "material", *titles])
    for row in out["rows"]:
        values = row.get("attributes") or {}
        writer.writerow([row["item"], row["level"], row["quantity"], row["name"], row["part"],
                         row.get("material") or "", *(values.get(t) or "" for t in titles)])  # fmt: skip
    return buffer.getvalue()


class BomExportData(TypedDict):
    path: str
    size: int
    sha256: str
    row_count: int
    total_quantity: int
    overwritten: bool


@tool(
    target="assembly",
    switch="none",  # reading only; the CSV is written by the host
    effect="file",
    label="Export bill of materials (CSV)",
    summary=lambda a, say: f"Bill of materials to {say('path')}",
    keywords=("bom csv", "export bom", "parts list excel", "stueckliste export"),
    requires=("work_part", "assembly"),
    cost="light",
    example={"path": "reports/bom.csv", "structure": "indented"},
)
def nx_export_bill_of_materials(
    tx: Tx,
    *,
    path: Annotated[str, PathTo("replace", ".csv")],
    structure: Structure = "parts",
    include_suppressed: bool = False,
    attributes: AttributeTitles | None = None,
    overwrite: bool = False,
) -> BomExportData:
    """Write the bill of materials (nx_get_bill_of_materials rows) to a .csv Excel opens:
    semicolon separated, UTF-8. Columns item, level, quantity, name, part, material, then
    the attributes. overwrite replaces a file; the model is not changed."""
    target = Path(path)
    replacing = target.exists()
    if replacing and not overwrite:
        fail("NX_ALREADY_EXISTS", "/path: a file already exists there; set overwrite=true to "
             "replace it", field="/path", details={"path": path})  # fmt: skip
    with tx.checks():  # reading only: no file yet (not_started on a refusal)
        out = bill(tx, structure, include_suppressed, attributes)
    temp = tx.files.stage(target, replace=overwrite)
    temp.write_text(csv_text(out, attributes), encoding="utf-8-sig", newline="")
    published = tx.files.publish()[0]
    return {
        **files.metadata(published, tx.workspace.root),
        "row_count": out["row_count"],
        "total_quantity": out["total_quantity"],
        "overwritten": replacing,
    }
