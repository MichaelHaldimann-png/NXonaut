"""``nx_get_design_rules`` and ``nx_save_design_rule``: MCP tools of the sidecar.

They read the shipped rule profiles and write the engineer's own rule file
(:mod:`nx_mcp.design_rules`); they never reach NX, so they are listed in both
profiles without evidence and work before NX connects.
"""

from __future__ import annotations

from typing import Any

from mcp.types import CallToolResult, Tool, ToolAnnotations

from nx_mcp import design_rules
from nx_mcp.core.errors import NXError
from nx_mcp.sidecar.proxy import failure, result

GET, SAVE = "nx_get_design_rules", "nx_save_design_rule"
NAMES = (GET, SAVE)
NAME = {"type": "string", "maxLength": 40}
DESCRIPTIONS = {
    GET: (
        "Engineering rules to follow when modelling and drawing: manufacturing processes "
        "(casting, machining, sheet_metal...) with checks, modelling style, drawing, tolerances, "
        "shaft, threads. "
        "Profile ISO, CH, DE or US, then the engineer's own rules, which win. No topic: list."
    ),
    SAVE: (
        "Save a rule in the engineer's own rule file (shipped profiles never change), only "
        "after they agreed to its wording. text: add or replace; table: {columns, rows}; "
        "remove: delete it or switch a profile rule off."
    ),
}
SCHEMAS: dict[str, dict[str, Any]] = {
    GET: {
        "type": "object",
        "properties": {
            "topic": NAME,
            "profile": {"type": "string", "enum": ["ISO", "CH", "DE", "US"]},
        },
        "additionalProperties": False,
    },
    SAVE: {
        "type": "object",
        "properties": {
            "topic": NAME,
            "rule": {**NAME, "description": "id; an existing id is replaced"},
            "text": {"type": "string", "maxLength": design_rules.MAX_TEXT},
            "table": {"type": "object"},
            "remove": {"type": "boolean"},
            "title": {"type": "string", "maxLength": 120, "description": "of a new topic"},
            "agreed": {"const": True},
        },
        "required": ["topic", "rule", "agreed"],
        "additionalProperties": False,
    },
}


def tools() -> list[Tool]:
    return [
        Tool(
            name=name,
            description=DESCRIPTIONS[name],
            inputSchema=SCHEMAS[name],
            annotations=ToolAnnotations(
                readOnlyHint=True if name == GET else None,
                destructiveHint=False if name == SAVE else None,
                idempotentHint=True,
                openWorldHint=False,
            ),
        )
        for name in NAMES
    ]


def _bad(name: str, message: str, field: str) -> CallToolResult:
    problem = NXError("NX_INVALID_ARGUMENT", message, field=field)
    return result(failure(name, problem, "not_applicable" if name == GET else "not_started"))


def call(name: str, arguments: dict, root) -> CallToolResult:
    allowed = set(SCHEMAS[name]["properties"])
    extra = sorted(set(arguments) - allowed - {"intent", "operation_id"})
    if extra:
        return _bad(name, f"Unknown argument {extra[0]!r}", f"/{extra[0]}")
    for key, value in arguments.items():
        want = SCHEMAS[name]["properties"].get(key, {}).get("type")
        types = {"string": str, "boolean": bool, "object": dict}
        if want in types and value is not None and not isinstance(value, types[want]):
            return _bad(name, f"{key} must be a {want}", f"/{key}")
    try:
        if name == GET:
            data = design_rules.get(root, arguments.get("topic"), arguments.get("profile"))
            outcome = "not_applicable"
        else:
            if arguments.get("agreed") is not True:
                return _bad(
                    name,
                    "Save a rule only after the engineer agreed to it (agreed: true)",
                    "/agreed",
                )
            for key in ("topic", "rule"):
                if not isinstance(arguments.get(key), str):
                    return _bad(name, f"{key} is required", f"/{key}")
            data = design_rules.save(
                root,
                topic=arguments["topic"],
                rule=arguments["rule"],
                text=arguments.get("text"),
                table=arguments.get("table"),
                remove=bool(arguments.get("remove")),
                title=arguments.get("title"),
            )
            outcome = "committed"
    except NXError as error:
        return result(failure(name, error, "not_applicable" if name == GET else "not_started"))
    return result({"ok": True, "tool": name, "mutation_outcome": outcome, "data": data})
