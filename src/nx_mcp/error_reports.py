"""Opt-in, anonymous error reports so NXonaut can improve from other users' NX setups.

Off by default. Nothing is collected or sent until the user says yes once
(``python -m nx_mcp.error_reports ask``, the installer's question) or sets
``NXONAUT_ERROR_REPORTS=on``; ``NXONAUT_ERROR_REPORTS=off`` always wins (for a company
that forbids it) and ``python -m nx_mcp.error_reports off`` turns it off again.

A report holds only: the tool name, the error category and code, NX's numeric error
code, the Python exception type, NX's message with every quoted name, path, file name,
e-mail, user and host name replaced, and the NXonaut, NX, Python and OS versions. Never
arguments, part or file names, paths, geometry, a traceback or anything that names a
person or a company. Only faults NXonaut should fix are reported (``REPORTED``), not
refusals of a wrong argument, a missing licence or the engineer's own control.

Reports wait in ``<workspace>/.nx-mcp/error-reports.json`` (one row per fingerprint, so a
fault repeated a hundred times is one report with a count). With a relay set
(``NXONAUT_REPORT_RELAY`` or :data:`RELAY_URL`, see ``docs/error-reports.md``) a new
fingerprint is posted to it in the background and the relay files or bumps a GitHub
issue. Without a relay, ``python -m nx_mcp.error_reports send`` opens a prefilled GitHub
issue per new report in the browser: the user sees exactly what is sent and submits it.
"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import platform
import re
import socket
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any

from nx_mcp import __version__
from nx_mcp.workspace import default_workspace

REPO = "MichaelHaldimann-png/NXonaut"
# The maintainer's relay (docs/error-reports.md); empty: reports go by browser only.
RELAY_URL = ""
ENV = "NXONAUT_ERROR_REPORTS"
RELAY_ENV = "NXONAUT_REPORT_RELAY"
STORE = Path(".nx-mcp") / "error-reports.json"
FORMAT = 1
MAX_ROWS = 50
MAX_MESSAGE = 240
# Faults in NXonaut or in how it drives NX: worth a fix. User errors, licences, the
# engineer's control and workspace refusals are not reported.
REPORTED = frozenset(
    {
        "geometry_failed",
        "solver_failed",
        "verification_failed",
        "file_failed",
        "bridge",
        "interrupted",
        "rollback_failed",
        "nx_error",
    }
)
ON = ("1", "on", "yes", "true")
OFF = ("0", "off", "no", "false")
_LOCK = threading.Lock()

_SCRUB = [
    (re.compile(r"""'[^']*'|"[^"]*"|`[^`]*`|«[^»]*»"""), "<name>"),
    (re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"), "<email>"),
    (re.compile(r"(?:[A-Za-z]:|\\\\[^\\\s]+)[\\/][^\s,;:()\[\]{}<>]*"), "<path>"),
    (re.compile(r"(?<![\w<])/(?:[^\s/,;:()\[\]{}<>]+/)+[^\s,;:()\[\]{}<>]*"), "<path>"),
    (re.compile(r"\b[\w-]+\.(?:prt|step|stp|igs|iges|x_t|x_b|stl|jt|dxf|dwg|pdf|"
                r"catpart|catproduct|json|txt|log|py|dat|csv)\b", re.I), "<file>"),
]  # fmt: skip


def anonymize(text: Any) -> str:
    """``text`` with quoted names, paths, file names, e-mails, user and host replaced."""
    if not isinstance(text, str):
        return ""
    for pattern, token in _SCRUB:
        text = pattern.sub(token, text)
    for who in _local_names():
        text = re.sub(re.escape(who), "<user>", text, flags=re.I)
    text = " ".join(text.split())
    return text[:MAX_MESSAGE]


def _local_names() -> set[str]:
    names = set()
    for get in (getpass.getuser, socket.gethostname):
        try:
            name = get()
        except Exception:
            continue
        if name and len(name) >= 3:
            names.add(name)
    return names


# -- consent ------------------------------------------------------------------------------


def _path(root: Path | str | None) -> Path:
    return Path(root or default_workspace()) / STORE


def _load(root=None) -> dict:
    try:
        data = json.loads(_path(root).read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("format") == FORMAT:
            data.setdefault("reports", {})
            return data
    except (OSError, ValueError):
        pass
    return {"format": FORMAT, "enabled": False, "asked": None, "reports": {}}


def _save(data: dict, root=None) -> None:
    path = _path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=1, sort_keys=True), encoding="utf-8")
    os.replace(temp, path)


def enabled(root=None) -> bool:
    """Whether the user opted in (the environment variable wins over the stored answer)."""
    env = os.environ.get(ENV, "").strip().casefold()
    if env in OFF:
        return False
    if env in ON:
        return True
    return bool(_load(root).get("enabled"))


def set_enabled(on: bool, root=None) -> None:
    with _LOCK:
        data = _load(root)
        data["enabled"] = bool(on)
        data["asked"] = time.strftime("%Y-%m-%d")
        if not on:
            data["reports"] = {}  # turning it off also forgets what waits to be sent
        _save(data, root)


# -- collecting ---------------------------------------------------------------------------


def build_report(tool: str, error: Any, *, nx_build: str | None = None) -> dict | None:
    """The anonymous report of one error envelope's ``error``, else None (not reported)."""
    if not isinstance(error, dict) or error.get("category") not in REPORTED:
        return None
    details = error["details"] if isinstance(error.get("details"), dict) else {}
    nx_code = error.get("nx_code")
    report = {
        "tool": _token(tool),
        "category": _token(error.get("category")),
        "code": _token(error.get("code")),
        "nx_code": nx_code if isinstance(nx_code, int) else None,
        "exception": _token(details.get("exception_type")),
        "message": anonymize(error.get("message")),
        "nxonaut": __version__,
        "nx": _token(nx_build),
        "python": platform.python_version(),
        "os": _token(f"{platform.system()} {platform.release()}"),
    }
    key = "|".join(str(report[k]) for k in ("tool", "code", "nx_code", "exception"))
    report["fingerprint"] = hashlib.sha256(key.encode()).hexdigest()[:10]
    return report


def _token(value: Any) -> str | None:
    """A short plain token (tool names, codes, versions), else None."""
    if not isinstance(value, str):
        return None
    value = value.strip()[:60]
    return value if re.fullmatch(r"[\w.#: -]+", value) else None


def record(root, tool: str, envelope: dict, *, nx_build: str | None = None) -> dict | None:
    """Keep the report of a failed envelope when the user opted in; post a new one to the
    relay in the background. Never raises: a report must never fail a tool call."""
    try:
        if not isinstance(envelope, dict) or envelope.get("ok", True) or not enabled(root):
            return None
        report = build_report(tool, envelope.get("error"), nx_build=nx_build)
        if report is None:
            return None
        with _LOCK:
            data = _load(root)
            rows = data["reports"]
            row = rows.get(report["fingerprint"])
            now = time.strftime("%Y-%m-%d")
            if row is None:
                if len(rows) >= MAX_ROWS:
                    return None
                row = rows[report["fingerprint"]] = {"report": report, "count": 0,
                                                     "first": now, "sent": False}  # fmt: skip
            row["count"] += 1
            row["last"] = now
            row["report"] = report  # the latest versions
            fresh = not row["sent"]
            _save(data, root)
        if fresh and relay_url():
            threading.Thread(target=_post_pending, args=(root,), daemon=True).start()
        return report
    except Exception:
        return None


# -- sending ------------------------------------------------------------------------------


def relay_url() -> str:
    return os.environ.get(RELAY_ENV, "").strip() or RELAY_URL


def _post_pending(root=None) -> int:
    """POST each unsent report to the relay; returns how many it accepted."""
    url = relay_url()
    if not url or not enabled(root):
        return 0
    sent = 0
    for fingerprint, row in list(_load(root)["reports"].items()):
        if row.get("sent"):
            continue
        body = json.dumps({**row["report"], "count": row["count"]}).encode()
        request = urllib.request.Request(
            url, data=body, method="POST", headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(request, timeout=8) as answer:  # noqa: S310
                if answer.status >= 300:
                    continue
        except Exception:
            continue
        _mark_sent(root, fingerprint)
        sent += 1
    return sent


def _mark_sent(root, fingerprint: str) -> None:
    with _LOCK:
        data = _load(root)
        if fingerprint in data["reports"]:
            data["reports"][fingerprint]["sent"] = True
            _save(data, root)


def issue_title(report: dict) -> str:
    return f"[error-report] {report['tool']}: {report['code']} ({report['fingerprint']})"


def issue_url(report: dict, count: int = 1) -> str:
    """A prefilled new-issue link: the user sees the text in the browser and submits it."""
    lines = ["Automatic, anonymous NXonaut error report (opt-in). Edit or delete anything",
             "before you submit. Add what you did if you like.", "", "```json",
             json.dumps({**report, "count": count}, indent=1), "```"]  # fmt: skip
    query = urllib.parse.urlencode(
        {
            "template": "error_report.md",
            "labels": "error-report",
            "title": issue_title(report),
            "body": "\n".join(lines),
        }  # fmt: skip
    )
    return f"https://github.com/{REPO}/issues/new?{query}"


def send(root=None, *, open_browser: bool = True) -> list[str]:
    """Send unsent reports: through the relay when set, else as prefilled issue links."""
    if not enabled(root):
        return []
    if relay_url():
        _post_pending(root)
    links = []
    for fingerprint, row in _load(root)["reports"].items():
        if row.get("sent"):
            continue
        links.append(issue_url(row["report"], row["count"]))
        if open_browser:
            webbrowser.open(links[-1])
        _mark_sent(root, fingerprint)
    return links


# -- command line -------------------------------------------------------------------------


def ask(root=None, *, answer: str | None = None) -> bool:
    """The installer's one question; asked only once unless ``answer`` is given."""
    data = _load(root)
    if answer is None and data.get("asked"):
        return bool(data.get("enabled"))
    if answer is None:
        print(
            "NXonaut can send anonymous error reports so it gets better on other NX setups.\n"
            "Only the tool name, error code, NX's message without names or paths and the\n"
            "versions are sent. Never part names, file paths, geometry or user names.\n"
            "Turn it off any time: python -m nx_mcp.error_reports off"
        )
        try:
            answer = input("Send anonymous error reports? [y/N] ")
        except EOFError:
            answer = ""
    on = answer.strip().casefold() in ON + ("y", "j", "ja")
    set_enabled(on, root)
    return on


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m nx_mcp.error_reports", description=__doc__.split("\n\n")[0]
    )
    parser.add_argument("command", choices=("status", "ask", "on", "off", "list", "send"))
    parser.add_argument("--answer", help="ask: y or n without a prompt (installers)")
    parser.add_argument("--workspace", help="another workspace folder")
    parser.add_argument("--no-browser", action="store_true", help="send: print the links")
    args = parser.parse_args(argv)
    root = args.workspace
    if args.command == "ask":
        on = ask(root, answer=args.answer)
        print("Error reports: " + ("on" if on else "off"))
    elif args.command in ("on", "off"):
        set_enabled(args.command == "on", root)
        print("Error reports: " + args.command)
    elif args.command == "status":
        rows = _load(root)["reports"].values()
        waiting = sum(not r.get("sent") for r in rows)
        print(f"Error reports: {'on' if enabled(root) else 'off'}; {waiting} waiting; "
              f"relay: {relay_url() or 'none (browser)'}")  # fmt: skip
    elif args.command == "list":
        for row in _load(root)["reports"].values():
            print(json.dumps({**row["report"], "count": row["count"], "sent": row["sent"]}))
    else:
        if not enabled(root):
            print("Error reports are off: python -m nx_mcp.error_reports on")
            return 1
        for link in send(root, open_browser=not args.no_browser):
            print(link)
    return 0


if __name__ == "__main__":
    sys.exit(main())
