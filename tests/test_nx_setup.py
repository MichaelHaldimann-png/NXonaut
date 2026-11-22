import runpy
import sys

from nx_mcp import nx_setup


def test_prepare_writes_a_start_journal_for_this_installation(tmp_path):
    nx_setup.prepare(tmp_path / "ws")
    shim = tmp_path / "ws" / nx_setup.SHIM_NAME
    text = shim.read_text(encoding="utf-8")
    assert text.startswith("# nx: threaded\n")
    assert repr(str(nx_setup.nx_app_folder() / "journals" / "start.py")) in text  # a literal


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


def test_prepare_repairs_a_stale_user_workspace_variable(tmp_path, monkeypatch):
    env = {"NX_MCP_WORKSPACE": "${HOME}\\NX_MCP_WORKSPACE"}
    monkeypatch.setattr(nx_setup.sys, "platform", "win32")
    monkeypatch.setattr(nx_setup, "_get_user_env", env.get)
    monkeypatch.setattr(nx_setup, "_set_user_env", env.__setitem__)
    monkeypatch.setattr(nx_setup.Path, "home", classmethod(lambda cls: tmp_path))
    workspace = tmp_path / "NX_MCP_WORKSPACE"
    nx_setup.prepare(workspace)
    assert env["NX_MCP_WORKSPACE"] == str(workspace)


def _fake_user_env(monkeypatch, env):
    monkeypatch.setattr(nx_setup.sys, "platform", "win32")
    monkeypatch.setattr(nx_setup, "_get_user_env", env.get)
    monkeypatch.setattr(nx_setup, "_set_user_env", env.__setitem__)
    monkeypatch.setattr(nx_setup, "_delete_user_env", env.pop)


NX_APP = r"C:\Ext\nxonaut\nx_app"
SITE = r"\\site\NX\UGII_USER_DIR"


def test_autostart_sets_the_user_dir(monkeypatch):
    env = {}
    _fake_user_env(monkeypatch, env)
    nx_setup._autostart(nx_setup.Path(NX_APP))
    assert env == {"UGII_USER_DIR": NX_APP}


def test_autostart_keeps_the_group_dir_once_moved_there(monkeypatch):
    env = {"UGII_GROUP_DIR": r"C:\Old\nxonaut\nx_app", "UGII_USER_DIR": r"C:\Old\nxonaut\nx_app"}
    _fake_user_env(monkeypatch, env)
    nx_setup._autostart(nx_setup.Path(NX_APP))
    assert env == {"UGII_GROUP_DIR": NX_APP}  # updated, and never both


def test_a_launcher_overriding_the_user_dir_moves_nxonaut_to_the_group_dir(monkeypatch):
    env = {"UGII_USER_DIR": NX_APP}
    _fake_user_env(monkeypatch, env)
    note = nx_setup.launcher_override(nx_setup.Path(NX_APP), {"UGII_USER_DIR": SITE})
    assert env == {"UGII_GROUP_DIR": NX_APP}
    assert "UGII_GROUP_DIR" in note


def test_no_repair_when_nx_sees_the_user_dir_or_autostart_is_off(monkeypatch):
    env = {"UGII_USER_DIR": NX_APP}
    _fake_user_env(monkeypatch, env)
    assert nx_setup.launcher_override(nx_setup.Path(NX_APP), {"UGII_USER_DIR": NX_APP}) is None
    env.clear()
    assert nx_setup.launcher_override(nx_setup.Path(NX_APP), {"UGII_USER_DIR": SITE}) is None
    assert env == {}


def test_a_launcher_using_both_dirs_is_reported_not_changed(monkeypatch):
    env = {"UGII_USER_DIR": NX_APP}
    _fake_user_env(monkeypatch, env)
    note = nx_setup.launcher_override(
        nx_setup.Path(NX_APP), {"UGII_USER_DIR": SITE, "UGII_GROUP_DIR": r"\\site\group"}
    )
    assert env == {"UGII_USER_DIR": NX_APP}
    assert "custom_dirs.dat" in note
