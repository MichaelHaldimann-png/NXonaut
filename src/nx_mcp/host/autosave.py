"""Autosave: after a committed model call, save the parts NX MCP made itself.

A dropped connection or a crashed NX then loses at most the last few minutes of the
agent's work instead of every unsaved step. Only parts that are both

* created or opened by the agent in this NX session (``services.created``: never a part
  the engineer only allowed on the panel), and
* written by an NX MCP tool (``kit.files.created_row``: the file is NX MCP's own),

are saved, through ``nx_save_part`` itself (the kernel's ownership, busy and workspace
gates), so the engineer's own parts are never saved by it. A save expires NX's undo marks,
so one part is saved at most once per interval (``NX_MCP_AUTOSAVE`` minutes, default 2;
``0`` or ``off`` turns autosave off): nx_undo_operation still goes back over the steps
since the last save. A failed autosave never fails the call; it is a warning.
"""

from __future__ import annotations

import contextlib
import os
import time
from pathlib import Path

from nx_mcp.core import catalogue, kernel
from nx_mcp.core.receipts import new_operation_id
from nx_mcp.kit import files, parts

ENV = "NX_MCP_AUTOSAVE"
DEFAULT_MINUTES = 2.0
SAVE_TOOL = "nx_save_part"


def interval() -> float | None:
    """Seconds between two autosaves of one part; None: autosave is off."""
    text = os.environ.get(ENV, "").strip().casefold()
    if not text:
        return DEFAULT_MINUTES * 60
    if text in ("off", "no", "false", "never"):
        return None
    try:
        minutes = float(text)
    except ValueError:
        return DEFAULT_MINUTES * 60
    return minutes * 60 if minutes > 0 else None


def candidates(services) -> list:
    """The loaded parts autosave may save now: the agent's own NX MCP files with unsaved
    changes."""
    root = Path(services.workspace.root)
    out = []
    for part in services.parts():
        with contextlib.suppress(Exception):
            if not services.created(part):
                continue
            path = parts.file_of(part)
            if not path or files.created_row(root, path) is None:
                continue
            if parts.unchanged_on_disk(part):
                continue
            out.append(part)
    return out


def after_call(services, spec, envelope: dict, caller=None, now: float | None = None) -> None:
    """Autosave after one committed model call; notes go on ``envelope['warnings']``."""
    if spec.effect != "model" or envelope.get("mutation_outcome") != "committed":
        return
    seconds = interval()
    save = catalogue.get(SAVE_TOOL)
    if seconds is None or save is None:
        return
    now = time.time() if now is None else now
    last: dict = services.__dict__.setdefault("autosaved_at", {})
    root = Path(services.workspace.root)
    for part in candidates(services):
        key = services.part_key(part)
        if now - last.get(key, 0.0) < seconds:
            continue
        path = Path(parts.file_of(part))
        try:
            shown = path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            continue
        result = kernel.run(
            save,
            {"part": shown},
            kernel.Context(services, operation_id=new_operation_id(), caller=caller),
        )
        last[key] = now  # a failed save is not retried before the next interval either
        warnings = envelope.setdefault("warnings", [])
        if result.get("ok") and (result.get("data") or {}).get("saved"):
            warnings.append(
                {
                    "code": "NX_NOTE",
                    "message": f"Autosaved {path.name} (undo goes back to this save, not past it)",
                }
            )
        elif not result.get("ok"):
            code = (result.get("error") or {}).get("code", "NX_SAVE_FAILED")
            warnings.append(
                {
                    "code": "NX_UPDATE_WARNING",
                    "message": f"Autosave of {path.name} failed ({code}); save it with "
                    "nx_save_part",
                }
            )
