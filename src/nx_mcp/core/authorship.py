"""Whose objects: the engineer's work in a part the agent works in (never deleted unasked).

The kernel compares the part's snapshot at the start of every model call with the one
the agent's previous call left (:func:`observe`): an object that appeared in between
was made by the engineer (in NX, between agent calls) and stays marked as theirs for
the part's lifetime. :func:`settle` records what a call left (committed or rolled back).
Session calls that change the model without a snapshot of their own (a redo, a preview)
observe and settle every tracked part around the call, so the agent's redone objects
never count as the engineer's.

A part the agent has not changed yet has no baseline: what it holds is not marked (the
part-ownership gate already keeps the engineer's own parts away). Only tags are kept, so
the check at delete time costs no NX call (``domains/session/delete``)."""

from __future__ import annotations

import contextlib

# Kinds the engineer makes on purpose; bodies, expressions, views and analyses follow
# from features or the display and never mark work of their own.
KINDS = frozenset(
    {
        "feature",
        "sketch",
        "curve",
        "point",
        "component",
        "component_pattern",
        "assembly_constraint",
        "explosion",
        "traceline",
        "drawing_sheet",
        "drawing_view",
        "dimension",
        "annotation",
        "drawing_table",
    }
)


def _state(services) -> tuple[dict, dict]:
    """``(baselines, engineer)``: part key -> snapshot keys the agent left, and part key
    -> tags of the engineer's objects."""
    baselines = getattr(services, "authorship_baselines", None)
    engineer = getattr(services, "engineer_objects", None)
    if baselines is None or engineer is None:
        baselines, engineer = {}, {}
        with contextlib.suppress(Exception):
            services.authorship_baselines = baselines
            services.engineer_objects = engineer
    return baselines, engineer


def observe(services, part, snapshot: dict) -> list[dict]:
    """Mark the objects of ``snapshot`` (the part now) that the agent's last call did not
    leave as the engineer's, then take ``snapshot`` as the baseline. Returns what changed
    since that call (``{"added": [...], "removed": n}`` rows of the snapshot, the
    engineer's new objects first): empty when nothing changed or nothing is known."""
    if part is None:
        return []
    changed: list[dict] = []
    with contextlib.suppress(Exception):
        baselines, engineer = _state(services)
        key = services.part_key(part)
        baseline = baselines.get(key)
        if baseline is not None:
            added = [k for k in snapshot if k[0] in KINDS and k not in baseline]
            removed = [k for k in baseline if k[0] in KINDS and k not in snapshot]
            if added:
                engineer.setdefault(key, set()).update(int(t) for _kind, t in added)
            if added or removed:
                changed.append({"added": [snapshot[k] for k in added], "removed": len(removed)})
        baselines[key] = set(snapshot)
    return changed


def note(changed: list[dict]) -> str | None:
    """The ``NX_NOTE`` of a part the engineer changed since the agent's last call."""
    if not changed:
        return None
    added = [r for c in changed for r in c["added"]]
    removed = sum(c["removed"] for c in changed)
    names = [str(r.get("name") or r.get("id") or "") for r in added[:5]]
    parts = []
    if added:
        parts.append(f"added {len(added)} ({', '.join(n for n in names if n)})")
    if removed:
        parts.append(f"removed {removed}")
    return (
        "The engineer changed this part since your last call (" + "; ".join(parts) + "): "
        "re-read it before you rebuild; nx_delete_objects never deletes their objects unasked"
    )


def settle(services, part, snapshot: dict) -> None:
    """The agent's call left ``snapshot``: the baseline of the next :func:`observe`."""
    if part is None:
        return
    with contextlib.suppress(Exception):
        baselines, _ = _state(services)
        baselines[services.part_key(part)] = set(snapshot)


def _tracked(services) -> list:
    baselines, _ = _state(services)
    if not baselines:
        return []
    parts = []
    with contextlib.suppress(Exception):
        for part in services.parts() or []:
            if services.part_key(part) in baselines:
                parts.append(part)
    return parts


def observe_tracked(services) -> list[dict]:
    """:func:`observe` on every loaded part that has a baseline (before a session call)."""
    changed: list[dict] = []
    for part in _tracked(services):
        with contextlib.suppress(Exception):
            changed += observe(services, part, services.snapshot(part))
    return changed


def settle_tracked(services) -> None:
    """:func:`settle` on every loaded part that has a baseline (after a session call)."""
    for part in _tracked(services):
        with contextlib.suppress(Exception):
            settle(services, part, services.snapshot(part))


def engineer_tags(services, part) -> set[int]:
    """Tags of the engineer's objects in ``part`` (empty when none are known)."""
    with contextlib.suppress(Exception):
        _, engineer = _state(services)
        return set(engineer.get(services.part_key(part)) or ())
    return set()


def mark_engineer(services, part, tags) -> None:
    """Mark ``tags`` of ``part`` as the engineer's (the host or a test that knows it)."""
    with contextlib.suppress(Exception):
        _, engineer = _state(services)
        engineer.setdefault(services.part_key(part), set()).update(int(t) for t in tags)


def forget(services, keys) -> None:
    """Parts NX closed: drop their baselines and marks."""
    with contextlib.suppress(Exception):
        baselines, engineer = _state(services)
        for key in keys:
            baselines.pop(key, None)
            engineer.pop(key, None)
