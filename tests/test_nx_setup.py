import runpy
import sys

from nx_mcp import nx_setup


def test_prepare_writes_a_start_journal_for_this_installation(tmp_path):
    nx_setup.prepare(tmp_path / "ws")
    shim = tmp_path / "ws" / nx_setup.SHIM_NAME
    text = shim.read_text(encoding="utf-8")
    assert text.startswith("# nx: threaded\n")
    assert str(nx_setup.nx_app_folder() / "journals" / "start.py") in text


def test_the_journal_plays_start_py(tmp_path, monkeypatch):
    target = tmp_path / "start.py"
    target.write_text("import sys\nsys.modules['_nxonaut_probe'] = True\n", encoding="utf-8")
    shim = tmp_path / "shim.py"
    shim.write_text(nx_setup.shim_text(target), encoding="utf-8")
    monkeypatch.delitem(sys.modules, "_nxonaut_probe", raising=False)
    runpy.run_path(str(shim))
    assert sys.modules.pop("_nxonaut_probe") is True


def test_prepare_never_raises_on_an_unwritable_workspace(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    nx_setup.prepare(blocker / "ws")  # mkdir fails: logged, not raised
