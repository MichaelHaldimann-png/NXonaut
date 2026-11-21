"""``nx_get_drawing_plan``: which views, sheet size and scale suit the work part, before
the drawing is made. Reads only (bounding box of the solids, ``kit.measure.bounds``).

Heuristics (ISO 128-30, ISO 5455 scales, first-angle placement by NX):

- The front view is the principal view with the largest projected area; ties keep the
  longest extent horizontal (front: x across, z up; top: x across, y up; right: y across).
- ``turned``: two extents within 3 % and the third at least 1.5 times as long, a shaft or
  pin. One front view with the axis horizontal, sections or details for grooves.
- ``flat``: the smallest extent under 15 % of the largest, a plate or sheet part. The view
  onto the plate plus one projected view for the thickness.
- ``prismatic``: front plus the top and the side view.
- Every plan adds a small shaded isometric view (drawing rule ``pictorial``).

The scale is the largest ISO 5455 scale (5:1 ... 1:50) at which the views, their gaps
(30 mm for dimensions) and the title block fit the sheet; the sheet is A4 or A3 at 1:1 or
larger, else A3 reduced down to 1:5, else the smallest sheet that keeps 1:5.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, TypedDict

from nx_mcp.core.catalogue import tool
from nx_mcp.core.errors import fail
from nx_mcp.core.tx import Tx
from nx_mcp.core.types import Doc
from nx_mcp.domains.drawing.sheets import SIZES
from nx_mcp.kit import bodies as kbodies
from nx_mcp.kit import measure
from nx_mcp.kit import units as kunits

SCALES = (5.0, 2.0, 1.0, 0.5, 0.2, 0.1, 0.05, 0.02)
GAP_MM = 30.0  # between views and to the border: room for dimensions
TITLE_BLOCK_MM = (180.0, 60.0)  # ISO 7200 width and a typical height
BORDER_MM = (20.0, 10.0)  # filing margin left, frame elsewhere
# View -> (horizontal axis, vertical axis) of the absolute extents, NX principal views.
AXES = {"front": (0, 2), "top": (0, 1), "right": (1, 2)}
Sheet = Literal["a4", "a3", "a2", "a1", "a0"]


class ViewRow(TypedDict):
    orientation: str
    role: str
    size: list[float]


class PlanData(TypedDict):
    shape: str
    extents: list[float]  # mm, x y z
    views: list[ViewRow]
    sheet: str
    scale: str
    scale_value: float
    alternatives: list[dict]
    notes: list[str]


def _ratio(scale: float) -> str:
    return f"{scale:g}:1" if scale >= 1 else f"1:{1 / scale:g}"


def shape_of(ext) -> str:
    a, b, c = sorted(ext)
    if c > 0 and a / c < 0.15:
        return "flat"
    for x, y, z in ((a, b, c), (b, c, a), (a, c, b)):
        if y > 0 and abs(x - y) / y <= 0.03 and z >= 1.5 * y:
            return "turned"
    return "prismatic"


def front_of(ext) -> str:
    area = {v: ext[h] * ext[w] for v, (h, w) in AXES.items()}
    best = max(area.values())
    tied = [v for v in AXES if area[v] >= best * 0.999]
    return max(tied, key=lambda v: (ext[AXES[v][0]] >= ext[AXES[v][1]], ext[AXES[v][0]]))


def views_of(ext, shape) -> list[ViewRow]:
    front = front_of(ext)
    h, v = AXES[front]
    rows: list[ViewRow] = [{"orientation": front, "role": "base", "size": [ext[h], ext[v]]}]
    depth = ({0, 1, 2} - {h, v}).pop()
    if shape == "turned":
        pass  # sections and details per feature, chosen while dimensioning
    else:
        # The view below or above the front shows its width and the depth; the side
        # view its depth and height (the projected views NX places by projection angle).
        below = {"front": "top", "top": "front", "right": "top"}[front]
        side = {"front": "right", "top": "right", "right": "front"}[front]
        rows.append({"orientation": below, "role": "projected", "size": [ext[h], ext[depth]]})
        if shape == "prismatic":
            rows.append({"orientation": side, "role": "projected", "size": [ext[depth], ext[v]]})
    return rows


def _needed(rows, scale) -> tuple[float, float]:
    """Sheet room (mm) the views take at ``scale``: the front, the view below it (rows[1])
    and the side view right of it (rows[2]), with gaps around each."""
    front = rows[0]["size"]
    width = front[0] * scale + 2 * GAP_MM
    height = front[1] * scale + 2 * GAP_MM
    if len(rows) > 1:
        height += rows[1]["size"][1] * scale + GAP_MM
    if len(rows) > 2:
        width += rows[2]["size"][0] * scale + GAP_MM
    return width, height


def fits(rows, scale, sheet) -> bool:
    w, h = SIZES[sheet]
    room_w, room_h = w - BORDER_MM[0] - BORDER_MM[1], h - 2 * BORDER_MM[1]
    need_w, need_h = _needed(rows, scale)
    # The title block takes the bottom right corner: views keep above it or left of it.
    return need_w <= room_w and (need_h + TITLE_BLOCK_MM[1] <= room_h
                                 or need_w + TITLE_BLOCK_MM[0] <= room_w and need_h <= room_h)  # fmt: skip


def best_scale(rows, sheet) -> float | None:
    return next((s for s in SCALES if fits(rows, s, sheet)), None)


def choose(rows, sheet=None) -> tuple[str, float, list[dict]]:
    order = ("a4", "a3", "a2", "a1", "a0")
    options: list[dict[str, Any]] = []
    for name in order if sheet is None else (sheet,):
        scale = best_scale(rows, name)
        if scale is not None:
            options.append({"sheet": name.upper(), "scale": _ratio(scale), "scale_value": scale})
    if not options:
        fail("NX_INVALID_ARGUMENT", "The part does not fit this sheet at 1:50",
             field="/sheet", hint="Pick a larger sheet or omit sheet")  # fmt: skip
    pick: dict[str, Any] | None = options[0] if sheet is not None else None
    if pick is None:
        # A4/A3 at 1:1 or larger; else A3 reduced down to 1:5; else the smallest sheet
        # that keeps 1:5; else whatever fits.
        small = [o for o in options if o["sheet"] in ("A4", "A3")]
        a3 = next((o for o in small if o["sheet"] == "A3"), None)
        pick = next((o for o in small if o["scale_value"] >= 1.0), None)
        if pick is None and a3 is not None and a3["scale_value"] >= 0.2:
            pick = a3
        if pick is None:
            pick = next((o for o in options if o["scale_value"] >= 0.2), a3 or options[-1])
    assert pick is not None
    return pick["sheet"], pick["scale_value"], [o for o in options if o is not pick][:3]


@tool(
    effect="read",
    label="Get drawing plan (views, sheet, scale)",
    summary=lambda a, say: "Plan drawing views" + (f" on {a['sheet']}" if a.get("sheet") else ""),
    keywords=(
        "view selection",
        "which views",
        "drawing layout",
        "drawing scale",
        "sheet size",
        "front view choice",
        "ansichten",
    ),  # fmt: skip
    requires=("work_part",),
    cost="light",
    example={"sheet": "a3"},
)
def nx_get_drawing_plan(
    tx: Tx,
    *,
    sheet: Annotated[Sheet, Doc("Keep this sheet size; omitted: the plan picks one")] | None = None,
) -> PlanData:
    """Suggest the views, sheet size and ISO 5455 scale for drawing the work part. From the
    extents of its solids: front = largest projected area; turned parts one view, flat parts
    two, prismatic three, plus a shaded isometric. Reads only."""
    solids = [b for b in kbodies.scope(tx) if getattr(b, "IsSolidBody", True)]
    if not solids:
        fail("NX_NOT_FOUND", "The work part has no solid body to draw", hint="Model a body first")
    low, high = measure.bounds(tx, solids)
    mm = kunits.MM_PER[kunits.part_units(tx)]
    ext = [max(0.0, (b - a) * mm) for a, b in zip(low, high, strict=True)]
    shape = shape_of(ext)
    rows = views_of(ext, shape)
    name, scale, others = choose(rows, sheet)
    plan_rows = [*rows, {"orientation": "isometric", "role": "pictorial", "size": []}]
    notes = []
    if shape == "turned":
        notes.append("Axis horizontal; add sections for keyways and details (2:1-10:1) for "
                     "grooves and undercuts")  # fmt: skip
    if shape == "flat":
        notes.append("One projected view gives the thickness; a sheet-metal part adds its "
                     "flat pattern")  # fmt: skip
    notes.append("Pictorial: fully shaded, one scale step smaller, no dimensions")
    return {
        "shape": shape,
        "extents": [round(e, 3) for e in ext],
        "views": plan_rows,  # type: ignore[typeddict-item]
        "sheet": name,
        "scale": _ratio(scale),
        "scale_value": scale,
        "alternatives": others,
        "notes": notes,
    }
