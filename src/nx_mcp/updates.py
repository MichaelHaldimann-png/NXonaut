"""NXonaut's own version, and a notice when a newer release is on GitHub.

The sidecar asks GitHub for the latest release at most once a day, in the background,
and writes the answer to ``<workspace>/.nx-mcp/update-check.json``; the NX panel reads
that file and shows a line while a newer version exists. The request is one anonymous
GET of the public releases API: nothing about the user, NX or the parts is sent.
``NXONAUT_UPDATE_CHECK=off`` turns it off. Never stops the server: errors are ignored.
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
import urllib.request
from pathlib import Path

logger = logging.getLogger("nx_mcp")

REPO = "MichaelHaldimann-png/NXonaut"
LATEST_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{REPO}/releases/latest"
CHECK_FILE = "update-check.json"
CHECK_EVERY_SECONDS = 24 * 3600
SWITCH_ENV = "NXONAUT_UPDATE_CHECK"


def installed_version() -> str | None:
    """The NXonaut version of this installation: the extension's manifest.json (bundle
    root, or packaging/claude-desktop in a source checkout), else None."""
    root = Path(__file__).resolve().parents[2]
    for manifest in (
        root / "manifest.json",
        root / "packaging" / "claude-desktop" / "manifest.json",
    ):
        try:
            version = json.loads(manifest.read_text(encoding="utf-8")).get("version")
        except (OSError, ValueError, AttributeError):
            continue
        if isinstance(version, str) and version:
            return version
    return None


def _key(version: str) -> tuple[int, ...]:
    return tuple(int(n) for n in re.findall(r"\d+", version)[:4])


def newer(latest: str | None, installed: str | None) -> bool:
    """Whether release ``latest`` (``v0.2.2`` or ``0.2.2``) is newer than ``installed``."""
    if not latest or not installed:
        return False
    try:
        return _key(latest) > _key(installed)
    except ValueError:
        return False


def _file(workspace: Path) -> Path:
    return Path(workspace) / ".nx-mcp" / CHECK_FILE


def read(workspace: Path) -> dict:
    try:
        data = json.loads(_file(workspace).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def notice(workspace: Path) -> str | None:
    """The panel's update line, or None while this installation is the newest."""
    installed = installed_version()
    latest = read(workspace).get("latest")
    if not newer(latest, installed):
        return None
    shown = str(latest).lstrip("v")
    return f"⬆  NXonaut {shown} is available (you have {installed}): {RELEASES_PAGE}"


def _fetch(timeout: float = 10.0) -> str | None:
    request = urllib.request.Request(
        LATEST_URL, headers={"Accept": "application/vnd.github+json", "User-Agent": "NXonaut"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed https URL
        tag = json.loads(response.read().decode("utf-8")).get("tag_name")
    return tag if isinstance(tag, str) else None


def check(workspace: Path, *, fetch=_fetch, now: float | None = None) -> dict:
    """Ask GitHub once a day (cached in the workspace); the cached answer otherwise."""
    if os.environ.get(SWITCH_ENV, "").strip().lower() in ("0", "off", "false", "no"):
        return {}
    now = time.time() if now is None else now
    cached = read(workspace)
    last = cached.get("checked_at")
    if isinstance(last, (int, float)) and now - last < CHECK_EVERY_SECONDS:
        return cached
    try:
        latest = fetch()
    except Exception as error:  # offline, proxy, rate limit: try again tomorrow
        logger.info("Update check skipped: %s", error)
        latest = cached.get("latest")
    data = {"checked_at": now, "latest": latest, "installed": installed_version()}
    try:
        target = _file(workspace)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data), encoding="utf-8")
    except OSError:
        pass
    return data


def start(workspace: Path) -> None:
    """Run :func:`check` in a background thread (never delays the server)."""
    threading.Thread(target=check, args=(workspace,), name="nxonaut-update", daemon=True).start()
