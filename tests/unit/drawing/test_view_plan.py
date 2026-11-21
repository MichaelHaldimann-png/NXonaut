"""nx_get_drawing_plan on the fake kit and its NX-free heuristics."""

from types import SimpleNamespace as NS

import pytest

from nx_mcp.domains.drawing import view_plan as vp
from tests.kit import fake_nx, run


def plan_nx():
    nx = fake_nx()
    boxes = lambda tag: next(b.box for b in nx.part.Bodies if b.Tag == tag)  # noqa: E731
    nx.uf.ModlGeneral = NS(AskBoundingBox=lambda tag: list(boxes(tag)))
    return nx


def test_shapes_and_front_views():
    assert vp.shape_of([200, 40, 40]) == "turned"
    assert vp.shape_of([300, 200, 10]) == "flat"
    assert vp.shape_of([80, 50, 20]) == "prismatic"
    assert vp.front_of([80, 50, 20]) == "top"  # x by y is the largest area
    assert vp.front_of([80, 20, 50]) == "front"
    assert vp.front_of([20, 80, 50]) == "right"


def test_scale_and_sheet_follow_the_size():
    small = vp.views_of([15, 10, 5], "prismatic")
    assert vp.choose(small)[:2] == ("A4", 2.0)
    big = vp.views_of([1200, 600, 500], "prismatic")
    sheet, scale, _ = vp.choose(big)
    assert sheet == "A2" and scale == 0.2  # A3 would need 1:10
    assert vp.choose(big, "a1")[:2] == ("A1", 0.2)


@pytest.mark.parametrize(("size", "shape", "views"), [
    ((200, 40, 40), "turned", ["front", "isometric"]),
    ((300, 200, 10), "flat", ["top", "front", "isometric"]),
    ((80, 30, 60), "prismatic", ["front", "top", "right", "isometric"]),
])  # fmt: skip
def test_plan_reads_the_work_part(size, shape, views):
    nx = plan_nx()
    nx.block(*size)
    ok = run(nx, "nx_get_drawing_plan")
    assert ok.ok, ok
    assert ok.data["shape"] == shape and ok.data["extents"] == list(map(float, size))
    assert [v["orientation"] for v in ok.data["views"]] == views
    assert ok.data["scale"] in ("1:1", "2:1", "1:2") and ok.data["sheet"] in ("A4", "A3")


def test_no_body_is_refused():
    bad = run(plan_nx(), "nx_get_drawing_plan")
    assert bad.error["code"] == "NX_NOT_FOUND"
