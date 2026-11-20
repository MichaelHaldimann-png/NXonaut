import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_step.py"
spec = importlib.util.spec_from_file_location("validate_step", SCRIPT)
vs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vs)

BLOCK = {"dimensions": [100.0, 60.0, 12.0], "volume": 72000.0}


def test_matching_dimensions_in_any_order_and_volume_pass():
    assert vs.compare(BLOCK, [12, 100, 60], 72000.0) == []


def test_a_changed_dimension_or_volume_is_reported():
    assert vs.compare(BLOCK, [100, 60, 10]) and vs.compare(BLOCK, volume=60000.0)


def test_ordered_comparison_checks_axes():
    assert vs.compare({**BLOCK, "ordered": True}, [60, 100, 12])


def test_a_file_that_is_not_step_is_refused(tmp_path, capsys):
    other = tmp_path / "part.prt"
    other.write_bytes(b"x")
    assert vs.main([str(other)]) == 2
