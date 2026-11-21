"""nx_list_assembly_constraints on the assembly fake: rows and component states."""

import pytest

from tests.kit import run
from tests.unit.assembly.fakes import STATUS, assembly_nx, place


@pytest.fixture
def nx():
    nx = assembly_nx()
    nx.a = place(nx, nx.blk, "A")
    nx.b = place(nx, nx.blk, "B", (60, 0, 0))
    nx.c = place(nx, nx.pin, "C", (0, 60, 0))
    return nx


def face(nx, c):
    return nx.ref_of(c.face(), "face")


def states(data):
    return {r["component"]["id"]: r["state"] for r in data["components"]}


def test_states_fixed_constrained_and_free(nx):
    assert run(nx, "nx_create_assembly_constraint", type="fix", component=nx.a.ref).ok
    assert run(nx, "nx_create_assembly_constraint", type="touch", component=nx.b.ref,
               geometry=face(nx, nx.b), target_component=nx.a.ref,
               target_geometry=face(nx, nx.a)).ok  # fmt: skip
    ok = run(nx, "nx_list_assembly_constraints", part="asm")
    assert ok.ok, ok
    assert [i["type"] for i in ok.data["items"]] == ["fix", "touch"]
    assert states(ok.data) == {nx.a.ref: "fixed", nx.b.ref: "constrained", nx.c.ref: "free"}
    counts = ok.data["counts"]
    assert counts["free"] == 1 and counts["constraints"] == 2 and counts["unsolved"] == 0
    only_b = run(nx, "nx_list_assembly_constraints", part="asm", component=nx.b.ref)
    assert [i["type"] for i in only_b.data["items"]] == ["touch"]
    assert states(only_b.data) == {nx.b.ref: "constrained"}


def test_a_failing_constraint_marks_its_components_broken(nx):
    assert run(nx, "nx_create_assembly_constraint", type="touch", component=nx.b.ref,
               geometry=face(nx, nx.b), target_component=nx.a.ref,
               target_geometry=face(nx, nx.a)).ok  # fmt: skip
    nx.assembly.positioner.Constraints[0].status = STATUS.OverConstrained
    ok = run(nx, "nx_list_assembly_constraints", part="asm")
    assert ok.ok, ok
    assert states(ok.data)[nx.b.ref] == "broken" and ok.data["counts"]["unsolved"] == 1
    assert ok.data["items"][0]["status"] == "OverConstrained"


def test_suppressed_constraints_do_not_hold(nx):
    assert run(nx, "nx_create_assembly_constraint", type="fix", component=nx.a.ref).ok
    nx.assembly.positioner.Constraints[0].Suppressed = True
    ok = run(nx, "nx_list_assembly_constraints", part="asm")
    assert states(ok.data)[nx.a.ref] == "free"
    assert ok.data["items"][0]["suppressed"] is True
