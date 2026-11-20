import hashlib
import json

from nx_mcp.domains.parts_files import snapshots as snap
from nx_mcp.kit import files
from tests.unit.parts_files.support import side


def _setup(tmp_path, data=b"part-v1", created=True):
    (tmp_path / "proj").mkdir()
    part = tmp_path / "proj" / "bracket.prt"
    part.write_bytes(data)
    if created:
        files.note_created(tmp_path, part, tool="nx_create_part")
    return part


def test_snapshot_list_and_restore_to_new_file(tmp_path):
    part = _setup(tmp_path)
    ok = side(tmp_path, snap.nx_create_snapshot, path="proj/bracket.prt", note="before wall")
    assert ok.ok, ok
    row = ok.data["snapshot"]
    assert row["source"] == "proj/bracket.prt" and row["size"] == 7
    assert row["sha256"] == hashlib.sha256(b"part-v1").hexdigest()
    assert row["note"] == "before wall"

    part.write_bytes(b"part-v2-broken")
    listed = side(tmp_path, snap.nx_list_snapshots, path="proj/bracket.prt")
    assert [r["snapshot_id"] for r in listed.data["items"]] == [row["snapshot_id"]]

    back = side(tmp_path, snap.nx_restore_snapshot, snapshot_id=row["snapshot_id"],
                to="proj/bracket_old.prt")  # fmt: skip
    assert back.ok, back
    assert back.data["overwritten"] is False and back.data["path"] == "proj/bracket_old.prt"
    assert (tmp_path / "proj" / "bracket_old.prt").read_bytes() == b"part-v1"
    assert part.read_bytes() == b"part-v2-broken"  # the original is untouched
    assert files.created_row(tmp_path, tmp_path / "proj" / "bracket_old.prt")


def test_restore_default_name_never_overwrites(tmp_path):
    _setup(tmp_path)
    ident = side(tmp_path, snap.nx_create_snapshot, path="proj/bracket.prt").data["snapshot"][
        "snapshot_id"
    ]
    back = side(tmp_path, snap.nx_restore_snapshot, snapshot_id=ident)
    assert back.ok and back.data["path"].startswith("proj/bracket_restored_")


def test_overwrite_takes_a_safety_snapshot_first(tmp_path):
    part = _setup(tmp_path)
    ident = side(tmp_path, snap.nx_create_snapshot, path="proj/bracket.prt").data["snapshot"][
        "snapshot_id"
    ]
    part.write_bytes(b"part-v2")
    back = side(tmp_path, snap.nx_restore_snapshot, snapshot_id=ident, overwrite=True)
    assert back.ok, back
    assert part.read_bytes() == b"part-v1" and back.data["overwritten"] is True
    safety = back.data["safety_snapshot_id"]
    again = side(tmp_path, snap.nx_restore_snapshot, snapshot_id=safety, overwrite=True)
    assert again.ok and part.read_bytes() == b"part-v2"


def test_overwrite_refuses_engineer_files(tmp_path):
    part = _setup(tmp_path, created=False)
    ident = side(tmp_path, snap.nx_create_snapshot, path="proj/bracket.prt").data["snapshot"][
        "snapshot_id"
    ]
    part.write_bytes(b"engineer edit")
    back = side(tmp_path, snap.nx_restore_snapshot, snapshot_id=ident, overwrite=True)
    assert not back.ok and back.error["code"] == "NX_READ_ONLY"
    assert back.mutation_outcome == "not_started"
    assert part.read_bytes() == b"engineer edit"


def test_overwrite_refuses_a_part_loaded_in_nx(tmp_path):
    part = _setup(tmp_path)
    ident = side(tmp_path, snap.nx_create_snapshot, path="proj/bracket.prt").data["snapshot"][
        "snapshot_id"
    ]
    owners = {"parts": {"t1": {"file": str(part.resolve()).replace("\\", "/").casefold()}}}
    (tmp_path / ".nx-mcp" / "owners.json").write_text(json.dumps(owners), encoding="utf-8")
    from nx_mcp.core import busy

    (tmp_path / ".nx-mcp" / busy.OWNERS_FILE).write_text(json.dumps(owners), encoding="utf-8")
    back = side(tmp_path, snap.nx_restore_snapshot, snapshot_id=ident, overwrite=True)
    assert not back.ok and back.error["code"] == "NX_PART_IN_USE"


def test_tampered_or_unknown_snapshot_is_refused(tmp_path):
    _setup(tmp_path)
    missing = side(tmp_path, snap.nx_restore_snapshot, snapshot_id="snap_000000000000")
    assert not missing.ok and missing.error["code"] == "NX_FILE_NOT_FOUND"
    row = side(tmp_path, snap.nx_create_snapshot, path="proj/bracket.prt").data["snapshot"]
    stored = next((tmp_path / ".nx-mcp" / snap.FOLDER).glob(row["snapshot_id"] + "*"))
    stored.write_bytes(b"tampered")
    bad = side(tmp_path, snap.nx_restore_snapshot, snapshot_id=row["snapshot_id"])
    assert not bad.ok and bad.error["code"] == "NX_FILE_NOT_FOUND"


def test_snapshot_refuses_paths_outside_and_internal_state(tmp_path):
    _setup(tmp_path)
    for path in ("../x.prt", ".nx-mcp/created-files.json"):
        refused = side(tmp_path, snap.nx_create_snapshot, path=path)
        assert not refused.ok and refused.mutation_outcome == "not_started"
