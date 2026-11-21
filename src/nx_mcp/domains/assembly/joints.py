"""``nx_create_joint``: a mechanism joint between two sibling components, built from
assembly constraints (no NX Motion: its solver needs a Simcenter Motion licence and opens
a blocking licence dialog without one, ``kit.kinematics``).

Each joint is the constraint set that leaves exactly its freedom:

- ``revolute``: rotation about the axis only. Circular edges (axis and target_axis):
  one concentric constraint (coaxial and coplanar). Cylindrical faces: align on the axes
  plus touch of face and target_face (the axial stop).
- ``cylindrical``: rotation about and sliding along the axis: align on the axes.
- ``slider``: sliding along the axis, no rotation: align_lock on the axes.
- ``fixed``: no motion: bond.

The constraints are created one after another in this call (under its undo mark: a
failure removes every one). Drive the joint with ``nx_run_motion_sweep`` (joint revolute
or slider about the same axis), or give it a limit with a distance or angle constraint.
"""

from __future__ import annotations

from typing import Annotated, Literal, TypedDict

from nx_mcp.core.catalogue import tool
from nx_mcp.core.errors import fail
from nx_mcp.core.tx import Tx
from nx_mcp.core.types import RefTo
from nx_mcp.domains.assembly import constraints
from nx_mcp.domains.assembly.common import ComponentId
from nx_mcp.kit import select

JointType = Literal["revolute", "cylindrical", "slider", "fixed"]
Axis = Annotated[
    str,
    RefTo("face", "edge", doc="Component's cylindrical face or circular edge on the axis"),
]
TargetAxis = Annotated[str, RefTo("face", "edge", doc="The target's face or edge on the axis")]
Face = Annotated[str, RefTo("face", doc="revolute on faces: the component's stop face")]
TargetFace = Annotated[str, RefTo("face", doc="revolute on faces: the target face it touches")]
TargetComponent = Annotated[str, RefTo("component", doc="The sibling 'o:N' it moves against")]
FREEDOM = {
    "revolute": "rotation about the axis",
    "cylindrical": "rotation about and sliding along the axis",
    "slider": "sliding along the axis",
    "fixed": "none",
}


class JointData(TypedDict):
    joint: str
    freedom: str
    constraints: list[constraints.ConstraintData]


def _is_edge(tx, ref, field) -> bool:
    obj = select.resolve(tx, ref, "face", "edge", field=field)
    return tx.kind_of(obj) == "edge"


def _plan(tx, type, axis, target_axis, face, target_face) -> list[dict]:
    """The constraint calls of a joint, checked before any is made."""
    if type == "fixed":
        for name, given in (("axis", axis), ("target_axis", target_axis), ("face", face),
                            ("target_face", target_face)):  # fmt: skip
            if given is not None:
                fail("NX_INVALID_ARGUMENT", f"A fixed joint takes no {name}", field="/" + name)
        return [{"type": "bond"}]
    for name, given in (("axis", axis), ("target_axis", target_axis)):
        if given is None:
            fail("NX_INVALID_ARGUMENT", f"A {type} joint needs {name}", field="/" + name)
    axes = {"geometry": axis, "target_geometry": target_axis}
    stop = face is not None or target_face is not None
    if type != "revolute" and stop:
        fail("NX_INVALID_ARGUMENT", f"face and target_face are for revolute joints, not {type}",
             field="/face" if face is not None else "/target_face")  # fmt: skip
    if type == "cylindrical":
        return [{"type": "align", **axes}]
    if type == "slider":
        return [{"type": "align_lock", **axes}]
    with tx.checks():
        edges = [_is_edge(tx, axis, "/axis"), _is_edge(tx, target_axis, "/target_axis")]
    if all(edges) and not stop:
        return [{"type": "concentric", **axes}]
    if face is None or target_face is None:
        fail(
            "NX_INVALID_ARGUMENT",
            "A revolute joint on cylindrical faces needs face and target_face (the axial stop)",
            field="/face" if face is None else "/target_face",
            hint="Or give circular edges as axis and target_axis: one concentric constraint",
        )
    return [
        {"type": "align", **axes},
        {"type": "touch", "geometry": face, "target_geometry": target_face},
    ]


@tool(
    effect="model",
    label="Create joint (revolute, slider, ...)",
    summary=lambda a, say: (
        f"{str(a.get('type')).capitalize()} joint {a.get('component')} "
        f"to {a.get('target_component')}"
    ),
    keywords=(
        "joint",
        "hinge",
        "revolute joint",
        "slider joint",
        "cylindrical joint",
        "pivot",
        "mechanism",
        "gelenk",
    ),  # fmt: skip
    requires=("work_part", "no_active_sketch", "assembly"),
    variants="type",
    cost="heavy",
    invalidates="deleted",
    example={
        "type": "revolute",
        "component": "o:5",
        "target_component": "o:4",
        "axis": "e:12",
        "target_axis": "e:30",
    },
)
def nx_create_joint(
    tx: Tx,
    *,
    type: JointType,
    component: ComponentId,
    target_component: TargetComponent,
    axis: Axis | None = None,
    target_axis: TargetAxis | None = None,
    face: Face | None = None,
    target_face: TargetFace | None = None,
) -> JointData:
    """Join two components as a mechanism joint made of assembly constraints. revolute: turns
    about the axis (circular edges: concentric; cylinder faces: align + touch face on
    target_face); cylindrical: turns and slides; slider: slides only; fixed: bond. Drive it
    with nx_run_motion_sweep."""
    calls = _plan(tx, type, axis, target_axis, face, target_face)
    made = []
    for call in calls:
        made.append(
            constraints.nx_create_assembly_constraint(
                tx, component=component, target_component=target_component, **call
            )
        )
    return {"joint": type, "freedom": FREEDOM[type], "constraints": made}
