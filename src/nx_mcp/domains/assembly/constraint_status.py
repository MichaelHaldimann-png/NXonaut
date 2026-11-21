"""``nx_list_assembly_constraints``: the work assembly's constraints and how well each
direct component is held, read only.

Per direct component (``components``): how many unsuppressed constraints position it and
a ``state``:

- ``fixed``: a fix constraint holds it.
- ``constrained``: other constraints position it (NX does not report the degrees of
  freedom left; drag it or run ``nx_run_motion_sweep`` to see what still moves).
- ``broken``: one of its constraints does not solve (``kit.positioning.BROKEN``).
- ``free``: no constraint at all; it stays where it was placed and moves with any drag.

Constraints of a subassembly live in its own part: make it the work part to list them.
"""

from __future__ import annotations

import contextlib
from typing import Annotated, Any, TypedDict

from nx_mcp.core.catalogue import tool
from nx_mcp.core.tx import Tx
from nx_mcp.core.types import Offset, PageLimit, RefTo
from nx_mcp.domains.assembly import constraints, structure
from nx_mcp.domains.assembly.common import ComponentRow
from nx_mcp.kit import positioning, result, select

ComponentFilter = Annotated[str, RefTo("component", doc="Only this component's constraints")]


class ComponentState(TypedDict):
    component: ComponentRow
    state: str
    constraints: int


class ConstraintListData(TypedDict):
    items: list[constraints.ConstraintData]
    page: dict[str, Any]
    components: list[ComponentState]
    counts: dict[str, int]


def _tags(constraint) -> set[int]:
    out = set()
    for c in positioning.components(constraint):
        with contextlib.suppress(Exception):
            out.add(int(c.Tag))
    return out


def states(tx, part) -> list[dict]:
    """``[{component, state, constraints}]`` of the direct components of ``part``."""
    held: dict[int, list] = {}
    for constraint in positioning.all_constraints(part):
        with contextlib.suppress(Exception):
            if constraint.Suppressed:
                continue
            for tag in _tags(constraint):
                held.setdefault(tag, []).append(constraint)
    out = []
    for component in structure.direct_children(part):
        mine = held.get(int(component.Tag), [])
        kinds, statuses = [], []
        for constraint in mine:
            with contextlib.suppress(Exception):
                kinds.append(positioning.kind_name(tx, constraint))
                statuses.append(positioning.status_name(tx, constraint))
        if any(s in positioning.BROKEN for s in statuses):
            state = "broken"
        elif "fix" in kinds:
            state = "fixed"
        elif mine:
            state = "constrained"
        else:
            state = "free"
        row = tx.ref(component, "component")
        out.append({"component": row, "state": state, "constraints": len(mine)})
    return out


@tool(
    effect="read",
    label="List assembly constraints",
    summary=lambda a, say: (
        "List assembly constraints" + (f" of {a['component']}" if a.get("component") else "")
    ),
    keywords=(
        "list mates",
        "constraint status",
        "unconstrained components",
        "free components",
        "assembly constraints",
        "constraint navigator",
        "fully constrained",
    ),  # fmt: skip
    requires=("work_part", "assembly"),
    cost="light",
    example={"component": "o:12"},
)
def nx_list_assembly_constraints(
    tx: Tx,
    *,
    component: ComponentFilter | None = None,
    offset: Offset = 0,
    limit: PageLimit = 20,
) -> ConstraintListData:
    """List the work assembly's constraints and how each direct component is held. Items:
    type, status, value, references (paged). components: state fixed, constrained, broken
    (a constraint fails) or free (no constraint). counts sums states and unsolved ones."""
    part = tx.part
    wanted = None
    if component is not None:
        wanted = int(select.resolve(tx, component, "component", field="/component").Tag)
    found = [c for c in positioning.all_constraints(part) if wanted is None or wanted in _tags(c)]
    selected, page = result.page(found, offset, limit)
    items = [constraints.record(tx, c) for c in selected]
    rows = states(tx, part)
    counts = dict.fromkeys(("fixed", "constrained", "broken", "free"), 0)
    for row in rows:
        counts[row["state"]] += 1
    counts["constraints"] = len(positioning.all_constraints(part))
    counts["unsolved"] = len(positioning.unsolved(tx, part))
    if wanted is not None:
        rows = [r for r in rows if r["component"]["id"] == component]
    return {"items": items, "page": page, "components": rows, "counts": counts}  # type: ignore[typeddict-item]
