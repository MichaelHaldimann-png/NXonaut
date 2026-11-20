import json
from pathlib import Path

from nx_mcp import updates


def test_newer_compares_release_tags():
    assert updates.newer("v0.2.2", "0.2.1")
    assert updates.newer("0.10.0", "0.9.9")
    assert not updates.newer("v0.2.1", "0.2.1")
    assert not updates.newer(None, "0.2.1") and not updates.newer("v1.0", None)


def test_check_asks_once_a_day_and_the_panel_line_follows(tmp_path, monkeypatch):
    monkeypatch.delenv(updates.SWITCH_ENV, raising=False)
    monkeypatch.setattr(updates, "installed_version", lambda: "0.2.1")
    calls = []

    def fetch():
        calls.append(1)
        return "v0.2.2"

    assert updates.check(tmp_path, fetch=fetch, now=1000.0)["latest"] == "v0.2.2"
    updates.check(tmp_path, fetch=fetch, now=2000.0)  # cached: no second request
    assert len(calls) == 1
    line = updates.notice(tmp_path)
    assert line.startswith("⬆  NXonaut 0.2.2 is available (you have 0.2.1)")
    monkeypatch.setattr(updates, "installed_version", lambda: "0.2.2")
    assert updates.notice(tmp_path) is None


def test_offline_and_switched_off_never_fail(tmp_path, monkeypatch):
    monkeypatch.delenv(updates.SWITCH_ENV, raising=False)

    def offline():
        raise OSError("no network")

    assert updates.check(tmp_path, fetch=offline, now=1.0)["latest"] is None
    monkeypatch.setenv(updates.SWITCH_ENV, "off")
    assert updates.check(tmp_path, fetch=offline, now=10**9) == {}
    (tmp_path / ".nx-mcp" / updates.CHECK_FILE).write_text("not json", encoding="utf-8")
    assert updates.notice(tmp_path) is None


def test_installed_version_reads_the_extension_manifest():
    path = Path("packaging/claude-desktop/manifest.json")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert updates.installed_version() == manifest["version"]
