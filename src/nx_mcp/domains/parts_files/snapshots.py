"""File snapshots and rollback of workspace files (idea and design from LT60/nx-agent).

A ``.prt`` is binary, so git cannot roll a part back. These sidecar tools copy a
workspace file into ``<workspace>/.nx-mcp/file-snapshots/`` before a risky change and
copy it back on request. They never reach NX: a snapshot holds the file as last saved
on disk, not unsaved changes in an open part.

Restore never overwrites by default: it writes a new file next to the original. With
``overwrite`` it replaces the original only when an NX MCP tool created it
(``kit.files.created_row``) and NX does not have it loaded, and it snapshots the
current file first so the restore can be undone the same way.

Adapted from ``tools/snapshot.py`` of https://github.com/LT60/nx-agent (MIT,
Copyright (c) 2026 Liu Tang); see ``licenses/``.
"""

from __future__ import annotations

import json
import os
import shutil
import time
import uuid
from pathlib import Path
from typing import Annotated, TypedDict

from nx_mcp.core.catalogue import tool
from nx_mcp.core.errors import fail
from nx_mcp.core.tx import Tx
from nx_mcp.core.types import Doc, Offset, PageLimit, PathIn, PathTo, Text
from nx_mcp.domains.parts_files.workspace import _loaded_part_file
from nx_mcp.kit import files, result

FOLDER = "file-snapshots"
MANIFEST = "manifest.json"
MAX_SNAPSHOT_BYTES = 2 * 1024 * 1024 * 1024
SnapshotId = Annotated[str, Text(40, r"^snap_[a-f0-9]{12}$"), Doc("Snapshot id (snap_...)")]
Note = Annotated[str, Text(200), Doc("Why the snapshot was taken")]


class SnapshotRow(TypedDict, total=False):
    snapshot_id: str
    source: str
    size: int
    sha256: str
    taken: str
    note: str


class SnapshotData(TypedDict):
    snapshot: SnapshotRow


class SnapshotsData(TypedDict):
    items: list[SnapshotRow]
    page: dict


class RestoreData(TypedDict):
    snapshot_id: str
    path: str
    overwritten: bool
    sha256: str
    safety_snapshot_id: Annotated[str | None, Doc("Snapshot of the replaced file (overwrite only)")]


def _folder(root: Path) -> Path:
    return root / ".nx-mcp" / FOLDER


def _locked(root: Path):
    """Exclusive access to the manifest across processes (``kit.files.lock_file``)."""
    return files.lock_file(_folder(root) / (MANIFEST + ".lock"))


def _manifest_rows(root: Path) -> list[dict]:
    try:
        data = json.loads((_folder(root) / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    rows = data.get("snapshots") if isinstance(data, dict) else None
    return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []


def _write_rows(root: Path, rows: list[dict]) -> None:
    target = _folder(root) / MANIFEST
    temp = target.with_suffix(".tmp")
    temp.write_text(json.dumps({"snapshots": rows}, indent=1), encoding="utf-8")
    os.replace(temp, target)


def _public(row: dict) -> SnapshotRow:
    return {k: row[k] for k in ("snapshot_id", "source", "size", "sha256", "taken", "note")
            if k in row}  # type: ignore[return-value]  # fmt: skip


def _take(root: Path, source: Path, note: str) -> dict:
    """Copy ``source`` into the snapshot folder and record it; the new manifest row."""
    size = source.stat().st_size
    if size > MAX_SNAPSHOT_BYTES:
        fail("NX_REQUEST_TOO_LARGE", f"Snapshots hold files up to 2 GiB; this one has {size} bytes",
             field="/path")  # fmt: skip
    ident = "snap_" + uuid.uuid4().hex[:12]
    stored = _folder(root) / f"{ident}{source.suffix.lower()}"
    stored.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, stored)
    row = {
        "snapshot_id": ident,
        "source": files.relative(source, root),
        "stored": stored.name,
        "size": size,
        "sha256": files.sha256(stored),
        "taken": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "at": time.time(),
        "note": note,
    }
    with _locked(root):
        rows = _manifest_rows(root)
        rows.append(row)
        _write_rows(root, rows)
    return row


@tool(
    effect="file",
    label="Snapshot workspace file",
    summary="Snapshot {path}",
    keywords=("snapshot", "backup part", "checkpoint", "save point", "rollback point"),
    cost="light",
    runs="sidecar",
    example={"path": "projects/demo/bracket.prt", "note": "before changing the wall"},
)
def nx_create_snapshot(tx: Tx, *, path: PathIn, note: Note = "") -> SnapshotData:
    """Copy a workspace file (e.g. a .prt) to a snapshot before a risky change; restore
    it later with nx_restore_snapshot. Holds the file as saved on disk: save the part
    first to include recent changes."""
    root = Path(tx.workspace.root)
    source = Path(path)
    if source.is_dir():
        fail("NX_WRONG_KIND", f"{files.relative(source, root)} is a folder; snapshot files",
             field="/path")  # fmt: skip
    tx.touched = True
    return {"snapshot": _public(_take(root, source, note))}


@tool(
    effect="read",
    label="List file snapshots",
    summary=lambda a, say: f"List snapshots of {say('path') if a.get('path') else 'workspace'}",
    keywords=("snapshots", "backups", "checkpoints", "rollback points"),
    cost="light",
    runs="sidecar",
    example={"path": "projects/demo/bracket.prt"},
)
def nx_list_snapshots(
    tx: Tx,
    *,
    path: Annotated[str, Text(260), Doc("Only snapshots of this workspace file")] = "",
    offset: Offset = 0,
    limit: PageLimit = 20,
) -> SnapshotsData:
    """List file snapshots, newest first, one page at a time: id, source file, size,
    SHA-256, time and note."""
    root = Path(tx.workspace.root)
    rows = list(reversed(_manifest_rows(root)))
    if path:
        wanted = path.replace("\\", "/").strip("/").casefold()
        rows = [r for r in rows if str(r.get("source", "")).casefold() == wanted]
    selected, page = result.page(rows, offset, limit)
    return {"items": [_public(r) for r in selected], "page": page}


@tool(
    effect="file",
    label="Restore file snapshot",
    summary="Restore snapshot {snapshot_id}",
    keywords=("restore snapshot", "rollback", "revert file", "undo file change", "backup"),
    cost="light",
    runs="sidecar",
    example={"snapshot_id": "snap_0123456789ab"},
)
def nx_restore_snapshot(
    tx: Tx,
    *,
    snapshot_id: SnapshotId,
    to: Annotated[str, PathTo("new")] | None = None,
    overwrite: Annotated[bool, Doc("Replace the original file (see description)")] = False,
) -> RestoreData:
    """Write a snapshot back as a new file (to, default <name>_restored_<time>). overwrite
    replaces the original instead: only files NX MCP created and NX has not loaded; the
    current file is snapshotted first."""
    root = Path(tx.workspace.root)
    row = next((r for r in _manifest_rows(root) if r.get("snapshot_id") == snapshot_id), None)
    if row is None:
        fail("NX_FILE_NOT_FOUND", f"No snapshot {snapshot_id}", field="/snapshot_id",
             hint="List snapshots with nx_list_snapshots")  # fmt: skip
    stored = _folder(root) / str(row.get("stored", ""))
    if not stored.is_file() or files.sha256(stored) != row.get("sha256"):
        fail("NX_FILE_NOT_FOUND", f"The stored copy of {snapshot_id} is missing or changed",
             field="/snapshot_id")  # fmt: skip
    if overwrite and to:
        fail("NX_INVALID_ARGUMENT", "Pass to (a new file) or overwrite, not both", field="/to")
    original = Path(tx.workspace.resolve(str(row["source"])))
    shown = files.relative(original, root)
    safety = None
    if overwrite:
        if original.exists() and files.created_row(root, original) is None:
            fail("NX_READ_ONLY",
                 f"{shown} was not created by an NX MCP tool: it is never overwritten",
                 field="/overwrite", hint="Restore to a new file (leave overwrite false)")  # fmt: skip
        if _loaded_part_file(root, original):
            fail("NX_PART_IN_USE", f"{shown} is loaded in NX", field="/overwrite",
                 hint="Close it with nx_close_part first, then restore")  # fmt: skip
        tx.touched = True
        if original.exists():
            safety = _take(root, original, f"before restoring {snapshot_id}")["snapshot_id"]
        temp = files.temp_path(root, original.name, getattr(tx, "operation_id", None))
        shutil.copy2(stored, temp)
        os.replace(temp, original)
        target = original
    else:
        if to:
            target = Path(to)
        else:
            stamp = time.strftime("%Y%m%d-%H%M%S")
            target = original.with_name(f"{original.stem}_restored_{stamp}{original.suffix}")
        tx.touched = True
        files.write_new(target, stored.read_bytes(), field="/to", root=root)
    files.note_written(tx, target)
    return {
        "snapshot_id": snapshot_id,
        "path": files.relative(target, root),
        "overwritten": bool(overwrite),
        "sha256": files.sha256(target),
        "safety_snapshot_id": safety,
    }
