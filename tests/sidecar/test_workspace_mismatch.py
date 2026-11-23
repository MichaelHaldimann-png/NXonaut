"""NX_WORKSPACE_MISMATCH: NX and the MCP server use two workspace folders. The status read
flags it, a path call is refused before it is sent, and NX's own path refusal is
explained with both folders and the remedy."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from nx_mcp.core import catalogue, evidence
from nx_mcp.server import create_server
from nx_mcp.workspace import Workspace


@pytest.fixture(autouse=True)
def every_tool(monkeypatch):
    every = {
        n: {"v2406": {"variants": list(s.variant_values())}} for n, s in catalogue.load().items()
    }
    monkeypatch.setattr(evidence, "_CACHE", every)
    monkeypatch.delenv("NX_MCP_DEV", raising=False)


def status_answer(root):
    return {"ok": True, "tool": "nx_get_status", "mutation_outcome": "not_applicable",
            "data": {"workspace": {"root": str(root)}}}  # fmt: skip


def outside_answer():
    return {"ok": False, "tool": "nx_create_part", "mutation_outcome": "not_started",
            "error": {"code": "NX_PATH_OUTSIDE_WORKSPACE", "message": "/path: outside",
                      "field": "/path", "retry": "after_fix"}}  # fmt: skip


def server(tmp_path, bridge):
    return create_server(bridge, Workspace(tmp_path), surface="full", build="v2406")


async def call(srv, name, arguments):
    return (await srv.call_tool(name, arguments)).structuredContent


async def test_status_flags_another_workspace_and_path_calls_are_refused(tmp_path):
    other = tmp_path.parent / "NXONAUT_TEST_WS"
    bridge = AsyncMock()
    bridge.call.return_value = status_answer(other)
    srv = server(tmp_path, bridge)
    status = await call(srv, "nx_get_status", {"include": ["workspace"]})
    workspace = status["data"]["workspace"]
    assert workspace["mismatch"] is True and workspace["root"] == str(other)
    assert workspace["server_root"] == str(tmp_path)
    assert [w["code"] for w in status["warnings"]] == ["NX_WORKSPACE_MISMATCH"]

    bridge.call.reset_mock()
    refused = await call(srv, "nx_create_part", {"path": "smoke/a.prt"})
    error = refused["error"]
    assert error["code"] == "NX_WORKSPACE_MISMATCH" and error["retry"] == "ask_engineer"
    assert str(other) in error["message"] and str(tmp_path) in error["message"]
    assert "Start NXonaut.py" in error["hint"]
    assert refused["mutation_outcome"] == "not_started"
    bridge.call.assert_not_called()  # nothing sent


async def test_same_workspace_in_another_spelling_is_no_mismatch(tmp_path):
    bridge = AsyncMock()
    bridge.call.return_value = status_answer(str(tmp_path).upper() + "/")
    srv = server(tmp_path, bridge)
    status = await call(srv, "nx_get_status", {"include": ["workspace"]})
    assert status["data"]["workspace"]["mismatch"] is False
    assert "server_root" not in status["data"]["workspace"]
    assert not status.get("warnings")


async def test_nx_path_refusal_is_explained_by_the_workspace_mismatch(tmp_path):
    other = tmp_path.parent / "elsewhere"
    bridge = AsyncMock()
    bridge.call.side_effect = [outside_answer(), status_answer(other)]
    srv = server(tmp_path, bridge)
    refused = await call(srv, "nx_create_part", {"path": "smoke/a.prt"})
    error = refused["error"]
    assert error["code"] == "NX_WORKSPACE_MISMATCH" and error["field"] == "/path"
    assert error["details"] == {"nx_root": str(other), "server_root": str(tmp_path)}
    assert bridge.call.call_args.args == ("nx_get_status", {"include": ["workspace"]})


async def test_nx_path_refusal_stays_when_both_use_one_workspace(tmp_path):
    bridge = AsyncMock()
    bridge.call.side_effect = [outside_answer(), status_answer(tmp_path)]
    srv = server(tmp_path, bridge)
    refused = await call(srv, "nx_create_part", {"path": "smoke/a.prt"})
    assert refused["error"]["code"] == "NX_PATH_OUTSIDE_WORKSPACE"
