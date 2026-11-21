"""nx_create_joint on the assembly fake: the constraint set of each joint type."""

import pytest

from tests.kit import run
from tests.unit.assembly.fakes import TYPE, assembly_nx, place


@pytest.fixture
def nx():
    nx = assembly_nx()
    nx.a = place(nx, nx.blk, "A")
    nx.b = place(nx, nx.pin, "B", (60, 0, 0))
    return nx


def face(nx, c, kind="cylinder"):
    return nx.ref_of(c.face(kind), "face")


def edge(nx, c):
    return nx.ref_of(c.edge([0, 0, 0], [1, 0, 0], True), "edge")


def types(nx):
    return [c.ConstraintType for c in nx.assembly.positioner.Constraints]


def test_revolute_on_circular_edges_is_one_concentric(nx):
    ok = run(nx, "nx_create_joint", type="revolute", component=nx.b.ref,
             target_component=nx.a.ref, axis=edge(nx, nx.b), target_axis=edge(nx, nx.a))  # fmt: skip
    assert ok.ok, ok
    assert types(nx) == [TYPE.Concentric]
    assert ok.data["freedom"] == "rotation about the axis"
    assert [c["type"] for c in ok.data["constraints"]] == ["concentric"]


def test_revolute_on_faces_aligns_axes_and_touches_the_stop(nx):
    ok = run(nx, "nx_create_joint", type="revolute", component=nx.b.ref,
             target_component=nx.a.ref, axis=face(nx, nx.b), target_axis=face(nx, nx.a),
             face=face(nx, nx.b, "plane"), target_face=face(nx, nx.a, "plane"))  # fmt: skip
    assert ok.ok, ok
    assert [c["type"] for c in ok.data["constraints"]] == ["align", "touch"]
    missing = run(nx, "nx_create_joint", type="revolute", component=nx.b.ref,
                  target_component=nx.a.ref, axis=face(nx, nx.b), target_axis=face(nx, nx.a))  # fmt: skip
    assert missing.error["field"] == "/face" and missing.mutation_outcome == "not_started"


def test_cylindrical_slider_and_fixed(nx):
    cyl = run(nx, "nx_create_joint", type="cylindrical", component=nx.b.ref,
              target_component=nx.a.ref, axis=face(nx, nx.b), target_axis=face(nx, nx.a))  # fmt: skip
    assert cyl.ok and [c["type"] for c in cyl.data["constraints"]] == ["align"], cyl
    fixed = run(nx, "nx_create_joint", type="fixed", component=nx.b.ref, target_component=nx.a.ref)
    assert fixed.ok and [c["type"] for c in fixed.data["constraints"]] == ["bond"], fixed
    bad = run(nx, "nx_create_joint", type="fixed", component=nx.b.ref, target_component=nx.a.ref,
              axis=face(nx, nx.b))  # fmt: skip
    assert bad.error["field"] == "/axis"
    stop = run(nx, "nx_create_joint", type="slider", component=nx.b.ref, target_component=nx.a.ref,
               axis=face(nx, nx.b), target_axis=face(nx, nx.a), face=face(nx, nx.b, "plane"))  # fmt: skip
    assert stop.error["field"] == "/face"
