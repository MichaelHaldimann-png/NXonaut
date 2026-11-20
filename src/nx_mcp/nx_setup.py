"""Make starting NXonaut in NX easy, wherever Claude installed this package.

Claude Desktop (``.mcpb`` extension) and Claude Code (plugin) unpack NXonaut into
folders the engineer never sees. When the server starts, :func:`prepare` therefore

* writes ``<workspace>/Start NXonaut.py``, a two-line journal that plays this
  installation's ``nx_app/journals/start.py``: in NX, Alt+F8 and pick it from the
  workspace folder;
* with ``NXONAUT_NX_AUTOSTART=1`` (or ``true``) (the extension's "Start with NX" option) on Windows,
  points ``UGII_USER_DIR`` at this ``nx_app`` folder so NX starts NXonaut by itself,
  but only when ``UGII_USER_DIR`` is unset or already points to an NXonaut ``nx_app``;
* copies a workspace other than the default to the user environment
  (``NX_MCP_WORKSPACE``) so that NX uses the same one.

Nothing here may stop the server: every step is best effort and only logged.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger("nx_mcp")

SHIM_NAME = "Start NXonaut.py"
AUTOSTART_ENV = "NXONAUT_NX_AUTOSTART"


def nx_app_folder() -> Path | None:
    """The ``nx_app`` folder of this installation (next to ``src``), if there is one."""
    folder = Path(__file__).resolve().parents[2] / "nx_app"
    return folder if (folder / "journals" / "start.py").is_file() else None


def shim_text(start: Path) -> str:
    # Line 1 keeps the journal in NX's main interpreter (see nx_app/journals/start.py).
    return (
        "# nx: threaded\n"
        '"""Starts NXonaut in NX: Alt+F8 (Play Journal), then pick this file."""\n\n'
        "import runpy\n\n"
        f"runpy.run_path({str(start)!r})\n"
    )


def _set_user_env(name: str, value: str) -> None:
    import winreg  # Windows only

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_ALL_ACCESS) as key:
        winreg.SetValueEx(key, name, 0, winreg.REG_EXPAND_SZ, value)
    _announce_env_change()


def _announce_env_change() -> None:
    """Tell Windows (Explorer, and so NX started from it) that the user environment
    changed, as ``setx`` does; without it the change shows only after a new login."""
    import ctypes

    result = ctypes.c_ulong()
    ctypes.windll.user32.SendMessageTimeoutW(
        0xFFFF, 0x001A, 0, "Environment", 0x0002, 2000, ctypes.byref(result)
    )


def _get_user_env(name: str) -> str | None:
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            return str(winreg.QueryValueEx(key, name)[0])
    except OSError:
        return None


def prepare(workspace: Path) -> None:
    """Write the start journal and, when asked, set up NX's autostart (best effort)."""
    nx_app = nx_app_folder()
    if nx_app is None:
        return
    try:
        workspace.mkdir(parents=True, exist_ok=True)
        shim = workspace / SHIM_NAME
        text = shim_text(nx_app / "journals" / "start.py")
        if not shim.is_file() or shim.read_text(encoding="utf-8") != text:
            shim.write_text(text, encoding="utf-8")
    except OSError as error:
        logger.warning("Could not write %s: %s", SHIM_NAME, error)
    if sys.platform != "win32":
        return
    try:
        if os.environ.get(AUTOSTART_ENV, "").lower() in ("1", "true"):
            current = _get_user_env("UGII_USER_DIR")
            ours = current and Path(current).name == "nx_app" and "nxonaut" in current.lower()
            if (not current or ours) and current != str(nx_app):
                _set_user_env("UGII_USER_DIR", str(nx_app))
            elif current and not ours:
                logger.warning("UGII_USER_DIR is already %s: NX autostart left alone", current)
        default = Path.home() / "NX_MCP_WORKSPACE"
        if workspace.resolve() != default.resolve() and _get_user_env("NX_MCP_WORKSPACE") != str(
            workspace
        ):
            _set_user_env("NX_MCP_WORKSPACE", str(workspace))
    except Exception as error:  # never stop the server for a convenience
        logger.warning("NX setup skipped: %s", error)
