"""Design rules: the engineering conventions an agent applies while it models and draws.

Shipped profiles (``profiles/*.json``, read-only): ``ISO`` is the base; ``CH``, ``DE``
and ``US`` extend it and replace single rules. The engineer's own file
``<workspace>/nxonaut-rules.json`` goes on top: its rules replace or add to the
profile's, a ``null`` rule removes one, and its ``profile`` key picks the profile.
Without that key the install setting ``NXONAUT_RULES_PROFILE`` picks it, else ``ISO``.

Only :func:`save` writes, and only the engineer's file: agents propose a rule and save
it after the engineer agreed (the tool description says so). NX-free; the sidecar
serves it as ``nx_get_design_rules`` and ``nx_save_design_rule``.
"""

from __future__ import annotations

import copy
import json
import os
import re
from pathlib import Path
from typing import Any

from nx_mcp.core.errors import NXError

PROFILE_DIR = Path(__file__).resolve().parent / "profiles"
USER_FILE = "nxonaut-rules.json"
ENV = "NXONAUT_RULES_PROFILE"
BASE = "ISO"
NAME = re.compile(r"^[a-z][a-z0-9_]{1,39}$")
MAX_TEXT = 600
MAX_ROWS = 60


def profiles() -> dict[str, dict]:
    """``{name: profile}`` of the shipped profiles."""
    found = {}
    for path in sorted(PROFILE_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        found[data["profile"]] = data
    return found


def user_path(root: str | Path) -> Path:
    return Path(root) / USER_FILE


def read_user(root: str | Path) -> tuple[dict, str | None]:
    """The engineer's file (``{}`` when absent) and a warning when it cannot be read."""
    path = user_path(root)
    if not path.is_file():
        return {}, None
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as error:
        return {}, f"{USER_FILE} is not valid JSON and was ignored: {error}"
    if not isinstance(data, dict):
        return {}, f"{USER_FILE} must hold a JSON object; it was ignored"
    return data, None


def choose(requested: str | None, user: dict) -> tuple[str, str | None]:
    """The profile name and a warning for an unknown one: ``requested``, then the
    user file's ``profile``, then the install setting, then ``ISO``."""
    known = profiles()
    for source, value in (
        ("profile", requested),
        (USER_FILE, user.get("profile")),
        ("install setting", os.environ.get(ENV)),
    ):
        text = str(value or "").strip()
        if not text or text.startswith("${"):  # an unset .mcpb field arrives literally
            continue
        name = text.upper()
        if name in known:
            return name, None
        return BASE, f"Unknown profile {text!r} ({source}); using {BASE}. Known: " + ", ".join(
            known
        )
    return BASE, None


def _chain(name: str, known: dict[str, dict]) -> list[str]:
    chain: list[str] = []
    seen: set[str] = set()
    while name and name not in seen:
        seen.add(name)
        chain.insert(0, name)
        name = known[name].get("extends") or ""
    return chain


def _overlay(topics: dict, origin: dict, layer: dict, source: str) -> None:
    for topic, body in (layer.get("topics") or {}).items():
        if not isinstance(body, dict):
            continue
        into = topics.setdefault(topic, {"title": "", "rules": {}, "tables": {}})
        if body.get("title"):
            into["title"] = body["title"]
        for kind in ("rules", "tables"):
            for key, value in (body.get(kind) or {}).items():
                if value is None:
                    into[kind].pop(key, None)
                    origin.pop(f"{topic}.{key}", None)
                else:
                    into[kind][key] = copy.deepcopy(value)
                    origin[f"{topic}.{key}"] = source


def merged(root: str | Path, profile: str | None = None, *, own: bool = True) -> dict[str, Any]:
    """``{profile, chain, note, topics, origin, warnings}`` with the user file on top
    (``own`` false: the profile alone)."""
    known = profiles()
    user, problem = read_user(root)
    name, unknown = choose(profile, user)
    chain = _chain(name, known)
    topics: dict[str, dict] = {}
    origin: dict[str, str] = {}
    for layer in chain:
        _overlay(topics, origin, known[layer], layer)
    if user and own:
        _overlay(topics, origin, user, "user")
        chain.append("user")
    return {
        "profile": name,
        "chain": chain,
        "note": known[BASE].get("note", ""),
        "topics": topics,
        "origin": origin,
        "warnings": [w for w in (problem, unknown) if w],
    }


def get(root: str | Path, topic: str | None = None, profile: str | None = None) -> dict:
    """The topic index (no ``topic``) or one topic's rules and tables."""
    rules = merged(root, profile)
    topics = rules["topics"]
    data: dict[str, Any] = {"profile": rules["profile"], "chain": rules["chain"]}
    if topic is None:
        data["topics"] = [
            {"topic": k, "title": v["title"], "rules": len(v["rules"]), "tables": len(v["tables"])}
            for k, v in topics.items()
        ]
        data["user_file"] = USER_FILE
        data["note"] = rules["note"]
    else:
        key = topic.strip().casefold()
        if key not in topics:
            raise NXError(
                "NX_NOT_FOUND",
                f"No design-rule topic {topic!r}",
                field="/topic",
                hint="Call nx_get_design_rules without topic to list them",
                details={"topics": sorted(topics)},
            )
        body = topics[key]
        data.update(topic=key, title=body["title"], rules=body["rules"])
        if body["tables"]:
            data["tables"] = body["tables"]
        mine = sorted(
            k.split(".", 1)[1]
            for k, v in rules["origin"].items()
            if v == "user" and k.startswith(key + ".")
        )
        if mine:
            data["from_user_file"] = mine
    if rules["warnings"]:
        data["warnings"] = rules["warnings"]
    return data


def _check_table(table: Any) -> dict:
    if not isinstance(table, dict) or not isinstance(table.get("columns"), list):
        raise NXError(
            "NX_INVALID_ARGUMENT",
            "table needs columns (a list of names) and rows (lists of values)",
            field="/table",
        )
    columns, rows = table["columns"], table.get("rows")
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_ROWS:
        raise NXError("NX_INVALID_ARGUMENT", f"table needs 1-{MAX_ROWS} rows", field="/table/rows")
    for n, row in enumerate(rows):
        if not isinstance(row, list) or len(row) != len(columns):
            raise NXError(
                "NX_INVALID_ARGUMENT",
                f"row {n} must have {len(columns)} values, one per column",
                field=f"/table/rows/{n}",
            )
    return {k: table[k] for k in ("title", "columns", "rows", "note") if k in table}


def save(
    root: str | Path,
    *,
    topic: str,
    rule: str,
    text: str | None = None,
    table: dict | None = None,
    remove: bool = False,
    title: str | None = None,
) -> dict:
    """Write one rule (``text``) or table into the engineer's file, or remove it there
    (``remove``: a profile rule is then switched off with ``null``)."""
    topic, rule = topic.strip().casefold(), rule.strip().casefold()
    for field, value in (("/topic", topic), ("/rule", rule)):
        if not NAME.match(value):
            raise NXError(
                "NX_INVALID_ARGUMENT",
                f"{field[1:]} must be 2-40 characters a-z 0-9 _, starting with a letter",
                field=field,
            )
    given = [x for x in (text, table) if x is not None]
    if remove == bool(given) or len(given) > 1:
        raise NXError(
            "NX_INVALID_ARGUMENT",
            "Give exactly one of text, table or remove: true",
            field="/text",
        )
    if text is not None and not 1 <= len(text.strip()) <= MAX_TEXT:
        raise NXError("NX_INVALID_ARGUMENT", f"text must be 1-{MAX_TEXT} characters", field="/text")
    path = user_path(root)
    user, problem = read_user(root)
    if problem:
        raise NXError(
            "NX_INVALID_ARGUMENT",
            problem,
            hint=f"Ask the engineer to fix or rename {USER_FILE} first; it was not changed",
        )
    profile_only = merged(root, own=False)["topics"].get(topic, {})
    shipped = rule in profile_only.get("rules", {}) or rule in profile_only.get("tables", {})
    body = user.setdefault("topics", {}).setdefault(topic, {})
    if title:
        body["title"] = title.strip()[:120]
    if remove:
        had = [k for k in ("rules", "tables") if (body.get(k) or {}).get(rule) is not None]
        if not had and not shipped:
            raise NXError(
                "NX_NOT_FOUND",
                f"No rule {rule!r} in topic {topic!r}",
                field="/rule",
                hint="nx_get_design_rules with the topic lists its rules",
            )
        for k in had:
            body[k].pop(rule)
        if had:  # the engineer's own entry goes; a profile rule of that id applies again
            action = "reverted_to_profile" if shipped else "removed"
        else:  # switch the profile's rule off
            kind = "tables" if rule in profile_only.get("tables", {}) else "rules"
            body.setdefault(kind, {})[rule] = None
            action = "disabled"
    else:
        kind = "tables" if table is not None else "rules"
        entry: Any = _check_table(table) if table is not None else str(text).strip()
        other = "rules" if kind == "tables" else "tables"
        (body.get(other) or {}).pop(rule, None)
        body.setdefault(kind, {})[rule] = entry
        action = "overrides_profile" if shipped else "saved"
    for k in ("rules", "tables"):
        if k in body and not body[k]:
            del body[k]
    user.setdefault("format", 1)
    temp = path.with_suffix(".json.tmp")
    try:
        temp.write_text(json.dumps(user, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temp, path)
    except OSError as error:
        raise NXError(
            "NX_TRANSFER_FAILED",
            f"Cannot write {USER_FILE}: {getattr(error, 'strerror', None) or error}",
        ) from None
    return {"topic": topic, "rule": rule, "action": action, "user_file": USER_FILE}
