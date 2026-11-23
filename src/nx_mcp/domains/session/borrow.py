"""License borrowing (FlexNet ``lmborrow``): take NX's floating licenses offline for a while.

NX's floating licenses come from a FlexNet server (vendor daemon ``ugslmd``), often only
reachable on a company or university VPN. FlexNet lets a seat *borrow* features for a
period the license file allows (its ``BORROW`` keyword sets the longest period; without
it the server refuses). These tools only drive FlexNet's own ``lmutil lmborrow``, the same
step as lmtools' Borrowing tab: the server decides what may be borrowed and for how long.

Borrowing in FlexNet works in three steps, which is why it is three tools:

1. ``nx_set_license_borrowing`` sets the borrow period (``lmborrow <vendor> <date> <time>``,
   stored per Windows user as ``LM_BORROW``). Nothing is checked out yet.
2. While still connected, NX (re)starts and opens every application needed offline:
   each feature NX checks out during the period is borrowed until the end date.
   Features NX checked out before the period started are not borrowed.
3. ``nx_finish_license_borrowing`` clears the period (``lmborrow -clear``) so later checkouts
   are normal again, and with ``return_now`` returns borrowed features early
   (``lmborrow -return``, needs the server again). ``nx_get_license_borrowing`` shows both.

They run in the sidecar (``runs="sidecar"``): no NX needed, so they also work while NX is
closed for the restart. ``lmutil`` comes with NX (``<NX>/UGFLEXLM``) or the Siemens license
server; ``NX_MCP_LMUTIL`` names another copy.
"""

from __future__ import annotations

import datetime as dt
import glob
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Annotated, TypedDict

from nx_mcp.core.catalogue import tool
from nx_mcp.core.errors import fail
from nx_mcp.core.tx import Tx
from nx_mcp.core.types import Doc, Items, Range, Text

VENDOR = "ugslmd"  # Siemens NX's FlexNet vendor daemon
MAX_DAYS = 180  # FlexNet's own ceiling; the license file usually allows less
TIMEOUT = 60
MONTHS = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
SEARCH = (
    r"C:\Program Files\Siemens\*\UGFLEXLM\lmutil.exe",
    r"C:\Program Files\Siemens\PLMLicenseServer\lmutil.exe",
    r"C:\Program Files\Siemens\*\NXBIN\lmutil.exe",
)
# lmborrow keeps LM_BORROW in the Borrow subkey; older FlexNet in the key itself.
REGISTRY_KEYS = (r"Software\FLEXlm License Manager\Borrow", r"Software\FLEXlm License Manager")
NEXT_STEPS = (
    "While still on the VPN: restart NX and open every application needed offline "
    "(Modeling, Drafting, Assemblies...) so NX checks their licenses out, then check "
    "nx_get_license_borrowing and call nx_finish_license_borrowing; then the VPN may go"
)
DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:[ T](\d{1,2}:\d{2}))?$")
EXPIRY_RE = re.compile(r"(\d{1,2})-([A-Za-z]{3})-(\d{4}|\d{2})(?:\s+(\d{1,2}):(\d{2}))?")


class Borrowed(TypedDict, total=False):
    vendor: str
    feature: str
    expires: str


class BorrowStatus(TypedDict, total=False):
    period_active: bool
    expired: int
    period: str
    borrowed: list[Borrowed]
    lmutil: str
    note: str


class BorrowData(BorrowStatus, total=False):
    vendor: str
    until: str


class EndData(BorrowStatus, total=False):
    returned: list[str]
    failed: list[str]


def lmutil() -> str:
    """Path to ``lmutil.exe`` (or ``lmutil``): NX_MCP_LMUTIL, NX's UGFLEXLM, PATH."""
    named = os.environ.get("NX_MCP_LMUTIL")
    if named:
        if Path(named).is_file():
            return named
        fail("NX_NOT_FOUND", f"NX_MCP_LMUTIL names {named}, which does not exist",
             hint="Point NX_MCP_LMUTIL at lmutil.exe or unset it")  # fmt: skip
    candidates = []
    for var in ("UGII_BASE_DIR", "UGII_ROOT_DIR"):
        base = os.environ.get(var)
        if base:
            root = Path(base)
            candidates += [
                root / "UGFLEXLM" / "lmutil.exe",
                root.parent / "UGFLEXLM" / "lmutil.exe",
            ]
    for path in candidates:
        if path.is_file():
            return str(path)
    for pattern in SEARCH:
        found = sorted(glob.glob(pattern), reverse=True)  # newest NX first
        if found:
            return found[0]
    on_path = shutil.which("lmutil")
    if on_path:
        return on_path
    fail("NX_NOT_FOUND", "lmutil (FlexNet's license utility) was not found",
         hint="It ships with NX in <NX>/UGFLEXLM; set NX_MCP_LMUTIL to its path")  # fmt: skip


def _env() -> dict:
    env = dict(os.environ)
    server = env.get("SPLM_LICENSE_SERVER")
    if server and not env.get("UGSLMD_LICENSE_FILE") and not env.get("LM_LICENSE_FILE"):
        env["UGSLMD_LICENSE_FILE"] = server  # NX's own variable, which lmutil does not read
    return env


def run(exe: str, *args: str) -> tuple[int, str]:
    """Run ``lmutil lmborrow ...``; returns (exit code, combined output)."""
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        done = subprocess.run([exe, "lmborrow", *args], capture_output=True, text=True,
                              timeout=TIMEOUT, env=_env(), creationflags=flags)  # fmt: skip
    except subprocess.TimeoutExpired:
        fail("NX_LICENSE_UNAVAILABLE", f"lmborrow {' '.join(args)} did not answer in {TIMEOUT} s",
             hint="Check the VPN and the license server (SPLM_LICENSE_SERVER)")  # fmt: skip
    except OSError as exc:
        fail("NX_NOT_FOUND", f"lmutil could not start: {exc}",
             hint="Set NX_MCP_LMUTIL to a working lmutil.exe")  # fmt: skip
    return done.returncode, ((done.stdout or "") + (done.stderr or "")).strip()


def _flex_date(moment: dt.datetime) -> tuple[str, str]:
    return f"{moment.day:02d}-{MONTHS[moment.month - 1]}-{moment.year}", moment.strftime("%H:%M")


def end_of(days: int | None, until: str | None, now: dt.datetime) -> dt.datetime:
    """The borrow end from ``days`` (whole days from now, at 23:59) or an ISO ``until``."""
    if (days is None) == (until is None):
        fail("NX_INVALID_ARGUMENT", "Give either days or until", field="/days",
             hint="days: 1-180, or until: '2026-12-04' or '2026-12-04 18:00'")  # fmt: skip
    if days is not None:
        return (now + dt.timedelta(days=days)).replace(hour=23, minute=59, second=0, microsecond=0)
    match = DATE_RE.match((until or "").strip())
    try:
        if not match:
            raise ValueError
        end = dt.datetime.fromisoformat(f"{match.group(1)} {match.group(2) or '23:59'}")
    except ValueError:
        fail("NX_INVALID_ARGUMENT", f"until {until!r} is not a date", field="/until",
             hint="Use YYYY-MM-DD, optionally with HH:MM")  # fmt: skip
    if end <= now:
        fail("NX_INVALID_ARGUMENT", "until lies in the past", field="/until")
    if end - now > dt.timedelta(days=MAX_DAYS):
        fail("NX_INVALID_ARGUMENT", f"FlexNet borrows for at most {MAX_DAYS} days",
             field="/until", hint="The license file usually allows less (often 7 days)")  # fmt: skip
    return end


def parse_status(text: str) -> list[Borrowed]:
    """Rows of ``lmborrow -status``: vendor, feature, expiry (after the ``____`` rule)."""
    rows: list[Borrowed] = []
    started = False
    for line in text.splitlines():
        if line.strip().startswith("___"):
            started = True
            continue
        parts = line.split()
        if not started or len(parts) < 3:
            continue
        row: Borrowed = {"vendor": parts[0], "feature": parts[1]}
        end = expiry_of(line)
        if end:
            row["expires"] = end.strftime("%Y-%m-%d %H:%M")
        rows.append(row)
    return rows


def expiry_of(line: str) -> dt.datetime | None:
    """The expiry in an ``lmborrow -status`` row ('6-Nov-26 19:24' or '29-Nov-2026')."""
    match = EXPIRY_RE.search(line)
    if not match or match.group(2).lower() not in MONTHS:
        return None
    day, month, year, hour, minute = match.groups()
    full = int(year) + (2000 if len(year) == 2 else 0)
    try:
        return dt.datetime(full, MONTHS.index(month.lower()) + 1, int(day),
                           int(hour or 23), int(minute or 59))  # fmt: skip
    except ValueError:
        return None


def borrow_period() -> str:
    """The ``LM_BORROW`` period FlexNet keeps for this user ('' when none)."""
    value = os.environ.get("LM_BORROW", "")
    if value or sys.platform != "win32":
        return value
    import winreg

    for name in REGISTRY_KEYS:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, name) as key:
                value = str(winreg.QueryValueEx(key, "LM_BORROW")[0] or "")
        except OSError:
            continue
        if value:
            return value
    return ""


def _status(exe: str) -> BorrowStatus:
    code, text = run(exe, "-status")
    period = borrow_period()
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    rows = parse_status(text)
    active = [r for r in rows if r.get("expires", "9999") > now]  # an old borrow stays listed
    data: BorrowStatus = {"period_active": bool(period), "borrowed": active, "lmutil": exe}
    if len(active) < len(rows):
        data["expired"] = len(rows) - len(active)
    if period:
        data["period"] = period
    if code and not data["borrowed"] and "no licenses" not in text.lower():
        data["note"] = text[-300:]
    return data


def _refused(text: str, what: str):
    fail("NX_LICENSE_UNAVAILABLE", f"FlexNet refused to {what}: {text[-300:] or 'no output'}",
         hint="Connect the VPN; the license file decides how long borrowing is allowed")  # fmt: skip


@tool(
    effect="session",
    label="Borrow licenses",
    summary=lambda a, say: (
        f"Borrow NX licenses for {a['days']} days"
        if a.get("days")
        else f"Borrow NX licenses until {say('until')}"
    ),
    keywords=(
        "borrow license",
        "lmborrow",
        "offline license",
        "without vpn",
        "license checkout",
        "ausleihen",
        "floating license",
        "take license home",
    ),  # fmt: skip
    cost="light",
    runs="sidecar",
    example={"days": 7},
)
def nx_set_license_borrowing(
    tx: Tx,
    *,
    days: Annotated[
        int, Range(ge=1, le=MAX_DAYS), Doc("Borrow until 23:59 that many days from today")
    ]
    | None = None,
    until: Annotated[str, Text(16), Doc("End as YYYY-MM-DD or 'YYYY-MM-DD HH:MM'")] | None = None,
    vendor: Annotated[str, Text(32, r"^[A-Za-z0-9_]+$"), Doc("FlexNet vendor daemon")] = VENDOR,
) -> BorrowData:
    """Borrow NX licenses so NX works without the license server or VPN until a date.
    Uses FlexNet lmborrow. The license file sets the longest period; FlexNet
    refuses more. Needs the server now, then an NX restart: only features NX checks out
    during the period are borrowed. Then nx_finish_license_borrowing."""
    end = end_of(days, until, dt.datetime.now())
    exe = lmutil()
    date, time = _flex_date(end)
    tx.touched = True
    code, text = run(exe, vendor, date, time)
    if code:
        _refused(text, f"start borrowing until {date} {time}")
    tx.outcome = "not_applicable"
    data: BorrowData = {**_status(exe), "vendor": vendor, "until": end.strftime("%Y-%m-%d %H:%M")}
    data["note"] = NEXT_STEPS
    return data


@tool(
    effect="read",
    label="Get borrowed licenses",
    summary="List borrowed NX licenses",
    keywords=("borrowed licenses", "lmborrow status", "license expiry", "offline license status"),
    cost="light",
    runs="sidecar",
    example={},
)
def nx_get_license_borrowing(tx: Tx) -> BorrowStatus:
    """List the NX licenses this PC has borrowed, with their expiry. Also says whether a
    borrow period is still set (lmborrow -status); works offline and with NX closed."""
    return _status(lmutil())


@tool(
    effect="session",
    label="End license borrowing",
    summary=lambda a, say: (
        "Return borrowed NX licenses" if a.get("return_now") else "End the license borrow period"
    ),
    keywords=(
        "return license",
        "return borrowed license",
        "lmborrow return",
        "clear borrow",
        "zurückgeben",
    ),  # fmt: skip
    cost="light",
    runs="sidecar",
    example={"return_now": True},
)
def nx_finish_license_borrowing(
    tx: Tx,
    *,
    return_now: Annotated[bool, Doc("Also hand borrowed licenses back to the server now")] = False,
    features: Annotated[
        list[Annotated[str, Text(64, r"^[A-Za-z0-9_.\-]+$")]],
        Items(1, 50),
        Doc("Features to return; default all borrowed"),
    ]
    | None = None,  # fmt: skip
) -> EndData:
    """End the license borrow period (lmborrow -clear): later checkouts are normal again.
    Borrowed licenses stay until their expiry. return_now gives them back early: it needs the
    server (VPN) and NX must not be using them, so close NX first."""
    exe = lmutil()
    tx.touched = True
    code, text = run(exe, "-clear")
    if code and borrow_period():
        _refused(text, "clear the borrow period")
    data: EndData = {}
    if return_now:
        borrowed = [row["feature"] for row in _status(exe)["borrowed"]]
        returned: list[str] = []
        failed: list[str] = []
        for feature in features or borrowed:
            code, text = run(exe, "-return", feature)
            (failed if code else returned).append(feature)
            if code:
                data["note"] = text[-300:]
        data["returned"], data["failed"] = returned, failed
        if failed and not returned:
            _refused(data.get("note", ""), f"return {', '.join(failed)}")
    tx.outcome = "not_applicable"
    return {**_status(exe), **data}
