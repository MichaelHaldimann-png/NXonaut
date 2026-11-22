"""nx_get_bill_of_materials and nx_export_bill_of_materials on the assembly fake."""

import pytest

from nx_mcp.kit import geom
from tests.kit import run
from tests.kit.attributes import UserAttributes
from tests.kit.kernel import services
from tests.unit.assembly.fakes import assembly_nx, place


@pytest.fixture
def nx():
    """asm: 2 x blk, a subassembly 'sub' (blk + 2 x pin) twice, and a suppressed pin."""
    nx = assembly_nx()
    sub = nx.new_part("parts/sub.prt")
    sub.Save()
    nx.sub = sub
    place(nx, nx.blk, "blk_a")
    place(nx, nx.blk, "blk_b", translation=(100, 0, 0))
    for i in range(2):
        s = place(nx, sub, f"sub_{i}", translation=(0, 200 * i, 0))
        for name, proto in (("inner", nx.blk), ("pin_1", nx.pin), ("pin_2", nx.pin)):
            c = nx.assembly.add(proto, name, ([0, 0, 0], geom.IDENTITY), parent=s)
            c.ref = nx.ref_of(c, "component")
    off = place(nx, nx.pin, "spare")
    off.IsSuppressed = True
    return nx


def rows_by_name(data):
    return {r["name"]: r for r in data["rows"]}


def test_parts_counts_leaf_parts_over_all_levels(nx):
    ok = run(nx, "nx_get_bill_of_materials", part="asm")
    assert ok.ok, ok
    rows = rows_by_name(ok.data)
    assert [r["name"] for r in ok.data["rows"]] == ["blk", "pin"]
    assert rows["blk"]["quantity"] == 4 and rows["pin"]["quantity"] == 4
    assert [r["item"] for r in ok.data["rows"]] == ["1", "2"]
    assert rows["blk"]["part"].endswith("blk.prt") and rows["blk"]["loaded"] is True
    assert ok.data["total_quantity"] == 8 and ok.data["skipped"] == 1
    assert len(rows["blk"]["components"]) == 4


def test_top_level_and_suppressed(nx):
    ok = run(nx, "nx_get_bill_of_materials", part="asm", structure="top_level")
    assert ok.ok, ok
    assert {r["name"]: r["quantity"] for r in ok.data["rows"]} == {"blk": 2, "sub": 2}
    every = run(nx, "nx_get_bill_of_materials", part="asm", structure="top_level",
                include_suppressed=True)  # fmt: skip
    assert rows_by_name(every.data)["pin"]["quantity"] == 1 and every.data["skipped"] == 0


def test_indented_numbers_items_and_counts_per_parent(nx):
    ok = run(nx, "nx_get_bill_of_materials", part="asm", structure="indented")
    assert ok.ok, ok
    got = [(r["item"], r["level"], r["name"], r["quantity"]) for r in ok.data["rows"]]
    assert got == [
        ("1", 0, "blk", 2),
        ("2", 0, "sub", 2),
        ("2.1", 1, "blk", 1),
        ("2.2", 1, "pin", 2),
    ]
    assert ok.data["total_quantity"] == 4


def test_attributes_and_materials(nx):
    class Attributed(UserAttributes):
        pass

    nx.blk.__class__ = type("BlkPart", (type(nx.blk), Attributed), {})
    nx.blk.SetUserAttribute("DB_PART_NO", -1, "100-200", None)
    ok = run(nx, "nx_get_bill_of_materials", part="asm", attributes=["DB_PART_NO"])
    assert ok.ok, ok
    rows = rows_by_name(ok.data)
    assert rows["blk"]["attributes"] == {"DB_PART_NO": "100-200"}
    assert rows["pin"]["attributes"] == {"DB_PART_NO": None}
    assert rows["pin"]["material"] is None


def test_export_writes_a_semicolon_csv(nx):
    target = services(nx).root / "reports" / "bom.csv"
    ok = run(nx, "nx_export_bill_of_materials", part="asm", path=str(target),
             structure="indented")  # fmt: skip
    assert ok.ok, ok
    text = target.read_text(encoding="utf-8-sig").splitlines()
    assert text[0] == "item;level;quantity;name;part;material"
    assert text[3].startswith("2.1;1;1;blk;")
    assert ok.data["row_count"] == 4 and ok.data["overwritten"] is False
    again = run(nx, "nx_export_bill_of_materials", part="asm", path=str(target))
    assert again.error["code"] == "NX_ALREADY_EXISTS", again


def test_empty_assembly_is_refused():
    nx = assembly_nx()
    bad = run(nx, "nx_get_bill_of_materials", part="asm")
    assert not bad.ok


def test_rows_follow_navigator_order_not_nx_list_order(nx):
    """Live NX 2512 listed children in another order than they were added (a pin before
    the plate): rows follow the active order, else creation (tag) order."""
    root = nx.asm.ComponentAssembly.RootComponent
    root.children.reverse()
    ok = run(nx, "nx_get_bill_of_materials", part="asm")
    assert [r["name"] for r in ok.data["rows"]] == ["blk", "pin"]

    class Order:
        def AskChildrenOrder(self, parent):
            return sorted(parent.GetChildren(), key=lambda c: -int(c.Tag))

    nx.asm.ComponentAssembly.ActiveOrder = Order()
    top = run(nx, "nx_get_bill_of_materials", part="asm", structure="top_level")
    assert [r["name"] for r in top.data["rows"]] == ["sub", "blk"]
