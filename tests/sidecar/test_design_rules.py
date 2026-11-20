"""Design rules: shipped profiles, the engineer's own file and the two MCP tools."""

import json
from unittest.mock import AsyncMock

import pytest

from nx_mcp import design_rules
from nx_mcp.server import create_server
from nx_mcp.workspace import Workspace


@pytest.fixture(autouse=True)
def no_install_setting(monkeypatch):
    monkeypatch.delenv(design_rules.ENV, raising=False)


def server(tmp_path):
    return create_server(AsyncMock(), Workspace(tmp_path), surface="agent", build="v2406")


async def call(tmp_path, name, arguments):
    answer = await server(tmp_path).call_tool(name, arguments)
    return answer.structuredContent


def test_shipped_profiles_are_well_formed():
    known = design_rules.profiles()
    assert set(known) == {"ISO", "CH", "DE", "US"}
    base = known["ISO"]["topics"]
    for name, profile in known.items():
        assert name == "ISO" or profile["extends"] == "ISO"
        for topic, body in profile["topics"].items():
            assert topic in base, (name, topic)  # overlays replace rules, never invent topics
            for key, text in (body.get("rules") or {}).items():
                assert design_rules.NAME.match(key) and len(text) <= design_rules.MAX_TEXT
            for table in (body.get("tables") or {}).values():
                assert all(len(r) == len(table["columns"]) for r in table["rows"])


def test_index_and_topic_follow_the_profile(tmp_path):
    index = design_rules.get(tmp_path)
    assert index["profile"] == "ISO" and index["chain"] == ["ISO"]
    assert {"drawing", "tolerances", "shaft", "threads", "materials"} <= {
        t["topic"] for t in index["topics"]
    }
    shaft = design_rules.get(tmp_path, "Shaft")
    keys = shaft["tables"]["keys_din6885"]
    assert next(r[2:] for r in keys["rows"] if r[0] == 22) == [8, 7, 4.0, 3.3]
    us = design_rules.get(tmp_path, "drawing", "us")
    assert "projection method 3" in us["rules"]["projection"] and us["chain"] == ["ISO", "US"]
    assert "Massstab" in design_rules.get(tmp_path, "drawing", "CH")["rules"]["language"]


def test_install_setting_then_user_file_pick_the_profile(tmp_path, monkeypatch):
    monkeypatch.setenv(design_rules.ENV, "de")
    assert design_rules.get(tmp_path)["profile"] == "DE"
    monkeypatch.setenv(design_rules.ENV, "${user_config.rules_profile}")  # unset .mcpb field
    assert design_rules.get(tmp_path)["profile"] == "ISO"
    monkeypatch.setenv(design_rules.ENV, "XX")
    odd = design_rules.get(tmp_path)
    assert odd["profile"] == "ISO" and "Unknown profile 'XX'" in odd["warnings"][0]
    (tmp_path / design_rules.USER_FILE).write_text('{"profile": "CH"}', encoding="utf-8")
    assert design_rules.get(tmp_path)["chain"] == ["ISO", "CH", "user"]


def test_user_rules_win_and_null_switches_a_profile_rule_off(tmp_path):
    design_rules.save(tmp_path, topic="shaft", rule="material", text="Shafts in 42CrMo4.")
    design_rules.save(tmp_path, topic="shaft", rule="centre_holes", remove=True)
    done = design_rules.save(
        tmp_path,
        topic="house_norms",
        rule="fits",
        table={"columns": ["seat", "fit"], "rows": [["bearing", "k6"]]},
        title="Our house norms",
    )
    assert done["action"] == "saved"
    shaft = design_rules.get(tmp_path, "shaft")
    assert shaft["rules"]["material"] == "Shafts in 42CrMo4."
    assert "centre_holes" not in shaft["rules"] and shaft["from_user_file"] == ["material"]
    saved = json.loads((tmp_path / design_rules.USER_FILE).read_text(encoding="utf-8"))
    assert saved["topics"]["shaft"]["rules"]["centre_holes"] is None
    own = design_rules.get(tmp_path, "house_norms")
    assert own["title"] == "Our house norms" and own["tables"]["fits"]["rows"] == [
        ["bearing", "k6"]
    ]
    # removing the engineer's own entry brings the profile's rule back
    back = design_rules.save(tmp_path, topic="shaft", rule="material", remove=True)
    assert back["action"] == "reverted_to_profile"
    assert "C45E" in design_rules.get(tmp_path, "shaft")["rules"]["material"]
    off = design_rules.save(tmp_path, topic="shaft", rule="material", remove=True)
    assert off["action"] == "disabled"
    again = design_rules.save(tmp_path, topic="house_norms", rule="fits", remove=True)
    assert again["action"] == "removed"


async def test_tools_are_listed_and_saving_needs_the_engineers_agreement(tmp_path):
    names = [t.name for t in await server(tmp_path).list_tools()]
    assert {"nx_get_design_rules", "nx_save_design_rule"} <= set(names)
    refused = await call(
        tmp_path, "nx_save_design_rule", {"topic": "shaft", "rule": "x_rule", "text": "t"}
    )
    assert not refused["ok"] and refused["error"]["field"] == "/agreed"
    assert not (tmp_path / design_rules.USER_FILE).exists()
    saved = await call(
        tmp_path,
        "nx_save_design_rule",
        {
            "topic": "drawing",
            "rule": "scale_note",
            "text": "Scale beside every view.",
            "agreed": True,
        },
    )
    assert saved["ok"] and saved["mutation_outcome"] == "committed"
    read = await call(tmp_path, "nx_get_design_rules", {"topic": "drawing"})
    assert read["data"]["rules"]["scale_note"] == "Scale beside every view."
    missing = await call(tmp_path, "nx_get_design_rules", {"topic": "gears"})
    assert (
        missing["error"]["code"] == "NX_NOT_FOUND"
        and "shaft" in missing["error"]["details"]["topics"]
    )
    via = await call(tmp_path, "nx_invoke", {"tool": "nx_get_design_rules", "arguments": {}})
    assert via["error"]["code"] == "NX_UNSUPPORTED_OPTION"


async def test_a_broken_user_file_is_reported_and_never_overwritten(tmp_path):
    path = tmp_path / design_rules.USER_FILE
    path.write_text("{not json", encoding="utf-8")
    read = await call(tmp_path, "nx_get_design_rules", {})
    assert read["ok"] and "not valid JSON" in read["data"]["warnings"][0]
    refused = await call(
        tmp_path,
        "nx_save_design_rule",
        {"topic": "shaft", "rule": "a_rule", "text": "t", "agreed": True},
    )
    assert not refused["ok"] and path.read_text(encoding="utf-8") == "{not json"
    bad = await call(
        tmp_path,
        "nx_save_design_rule",
        {"topic": "Shaft!", "rule": "a", "text": "t", "agreed": True},
    )
    assert bad["error"]["field"] == "/topic"
