"""host.autosave: after a committed model call, the agent's own NX MCP parts are saved
(at most once per interval); the engineer's parts never are."""

from types import SimpleNamespace as NS

import pytest

from nx_mcp.host import autosave
from nx_mcp.kit import files

MODEL = NS(effect="model", name="nx_test_model")
COMMITTED = {"ok": True, "mutation_outcome": "committed"}


def _agent_part(rig):
    rig.e.own(rig.part)  # created or opened by the agent
    files.note_created(rig.e.workspace.root, rig.part.FullPath, tool="nx_create_part")
    rig.part.IsModified = True


def test_saves_the_agents_own_modified_part_once_per_interval(rig, monkeypatch):
    monkeypatch.delenv(autosave.ENV, raising=False)
    _agent_part(rig)
    envelope = dict(COMMITTED)
    autosave.after_call(rig.e, MODEL, envelope, now=1000.0)
    assert rig.part.IsModified is False
    assert "Autosaved test.prt" in envelope["warnings"][0]["message"]
    rig.part.IsModified = True
    soon = dict(COMMITTED)
    autosave.after_call(rig.e, MODEL, soon, now=1060.0)  # within 2 minutes: kept for undo
    assert rig.part.IsModified is True and "warnings" not in soon
    autosave.after_call(rig.e, MODEL, dict(COMMITTED), now=1130.0)
    assert rig.part.IsModified is False


def test_never_saves_the_engineers_part(rig, monkeypatch):
    monkeypatch.delenv(autosave.ENV, raising=False)
    rig.e.owned_parts.clear()
    rig.part.IsModified = True
    rig.e.grant(rig.part)  # allowed on the panel, but not made by NX MCP
    envelope = dict(COMMITTED)
    autosave.after_call(rig.e, MODEL, envelope, now=1000.0)
    assert rig.part.IsModified is True and "warnings" not in envelope


def test_opened_file_not_written_by_nx_mcp_is_not_saved(rig, monkeypatch):
    monkeypatch.delenv(autosave.ENV, raising=False)
    rig.e.own(rig.part)  # opened by the agent, but the engineer's file
    rig.part.IsModified = True
    autosave.after_call(rig.e, MODEL, dict(COMMITTED), now=1000.0)
    assert rig.part.IsModified is True


@pytest.mark.parametrize("value", ["0", "off"])
def test_can_be_turned_off(rig, monkeypatch, value):
    monkeypatch.setenv(autosave.ENV, value)
    _agent_part(rig)
    autosave.after_call(rig.e, MODEL, dict(COMMITTED), now=1000.0)
    assert rig.part.IsModified is True


def test_reads_and_failed_calls_save_nothing(rig, monkeypatch):
    monkeypatch.delenv(autosave.ENV, raising=False)
    _agent_part(rig)
    autosave.after_call(rig.e, NS(effect="read", name="x"), dict(COMMITTED), now=1000.0)
    autosave.after_call(rig.e, MODEL, {"ok": True, "mutation_outcome": "rolled_back"}, now=1000.0)
    assert rig.part.IsModified is True


@pytest.mark.parametrize(("value", "seconds"), [("", 120.0), ("5", 300.0), ("x", 120.0)])
def test_interval_is_in_minutes(monkeypatch, value, seconds):
    monkeypatch.setenv(autosave.ENV, value)
    assert autosave.interval() == seconds
