"""Opt-in anonymous error reports: off by default, nothing personal, one row per fault."""

from __future__ import annotations

import json
import urllib.parse
from unittest.mock import AsyncMock

import pytest

from nx_mcp import error_reports as er
from nx_mcp.core.errors import NXError
from nx_mcp.server import create_server
from nx_mcp.workspace import Workspace


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv(er.ENV, raising=False)
    monkeypatch.delenv(er.RELAY_ENV, raising=False)


def failed(category="nx_error", code="NX_ERROR", message="boom", nx_code=670024):
    return {
        "ok": False,
        "tool": "nx_create_extrude",
        "error": {"category": category, "code": code, "message": message,
                  "nx_code": nx_code, "details": {"exception_type": "NXException"}},
    }  # fmt: skip


def test_off_by_default_records_nothing(tmp_path):
    assert not er.enabled(tmp_path)
    assert er.record(tmp_path, "nx_create_extrude", failed()) is None
    assert not (tmp_path / er.STORE).exists()


def test_env_off_wins_over_consent(tmp_path, monkeypatch):
    er.set_enabled(True, tmp_path)
    monkeypatch.setenv(er.ENV, "off")
    assert not er.enabled(tmp_path)


def test_anonymize_removes_names_paths_and_files():
    text = (
        "Cannot open 'Bracket_Customer' at C:\\Users\\anna\\Work\\a.prt and "
        "/home/anna/secret/b.step, mail anna@firm.ch, file gear.prt"
    )
    clean = er.anonymize(text)
    for word in ("Bracket", "anna", "Work", "secret", "firm", "gear"):
        assert word not in clean
    assert "<name>" in clean and "<path>" in clean and "<email>" in clean


def test_user_errors_are_not_reported(tmp_path):
    er.set_enabled(True, tmp_path)
    for category in ("invalid_argument", "unavailable", "engineer_control", "path_rejected"):
        assert er.record(tmp_path, "nx_x", failed(category=category)) is None


def test_repeats_are_one_row_with_a_count(tmp_path):
    er.set_enabled(True, tmp_path)
    for _ in range(3):
        er.record(tmp_path, "nx_create_extrude", failed(message="at 'Part7'"), nx_build="2406.9")
    rows = json.loads((tmp_path / er.STORE).read_text())["reports"]
    assert len(rows) == 1
    row = next(iter(rows.values()))
    assert row["count"] == 3
    report = row["report"]
    assert set(report) == {"tool", "category", "code", "nx_code", "exception", "message",
                           "nxonaut", "nx", "python", "os", "fingerprint"}  # fmt: skip
    assert "Part7" not in json.dumps(report)


def test_send_without_relay_gives_prefilled_issue_once(tmp_path):
    er.set_enabled(True, tmp_path)
    er.record(tmp_path, "nx_create_extrude", failed())
    links = er.send(tmp_path, open_browser=False)
    assert len(links) == 1 and links[0].startswith(f"https://github.com/{er.REPO}/issues/new?")
    query = urllib.parse.parse_qs(urllib.parse.urlparse(links[0]).query)
    assert "NX_ERROR" in query["title"][0] and "error-report" in query["labels"][0]
    assert er.send(tmp_path, open_browser=False) == []


def test_turning_off_forgets_waiting_reports(tmp_path):
    er.set_enabled(True, tmp_path)
    er.record(tmp_path, "nx_create_extrude", failed())
    er.set_enabled(False, tmp_path)
    assert json.loads((tmp_path / er.STORE).read_text())["reports"] == {}


def test_ask_is_asked_once(tmp_path):
    assert er.ask(tmp_path, answer="ja") is True
    assert er.ask(tmp_path) is True  # no prompt the second time
    assert er.ask(tmp_path, answer="n") is False


async def test_proxy_records_a_failed_call(tmp_path):
    er.set_enabled(True, tmp_path)
    bridge = AsyncMock()
    bridge.call.side_effect = NXError("NX_ERROR", "NX said no to 'Secret'")
    srv = create_server(bridge, Workspace(tmp_path), surface="full", build="v2406")
    answer = await srv.call_tool("nx_list_parts", {})
    assert answer.structuredContent["ok"] is False
    rows = json.loads((tmp_path / er.STORE).read_text())["reports"]
    assert any(r["report"]["tool"] == "nx_list_parts" for r in rows.values())
    assert "Secret" not in json.dumps(rows)
