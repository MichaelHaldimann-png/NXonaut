import datetime as dt

import pytest

from nx_mcp.core.errors import NXError
from nx_mcp.domains.session import borrow
from tests.unit.parts_files.support import side

STATUS = """lmutil - Copyright (c) 1989-2023 Flexera. All Rights Reserved.
Vendor    Feature                Expiration
______    ________               __________

ugslmd    nx_base                29-Nov-2026 23:59
ugslmd    drafting               29-Nov-2026 23:59
"""


@pytest.fixture
def lm(monkeypatch, tmp_path):
    calls = []
    state = {"period": ""}

    def run(exe, *args):
        calls.append(args)
        if args[0] == "-status":
            return 0, STATUS
        if args[0] == "-clear":
            state["period"] = ""
            return 0, ""
        if args[0] == "-return":
            return (1, "lmborrow: license in use") if args[1] == "drafting" else (0, "")
        state["period"] = f"x:{args[0]}:{args[1]}:{args[2]}"
        return 0, ""

    monkeypatch.setattr(borrow, "lmutil", lambda: "lmutil.exe")
    monkeypatch.setattr(borrow, "run", run)
    monkeypatch.setattr(borrow, "borrow_period", lambda: state["period"])
    return calls


def test_borrow_for_days_sets_the_period_and_reports_status(lm, tmp_path):
    result = side(tmp_path, borrow.nx_set_license_borrowing, days=7)
    end = dt.date.today() + dt.timedelta(days=7)
    month = borrow.MONTHS[end.month - 1]
    assert lm[0] == ("ugslmd", f"{end.day:02d}-{month}-{end.year}", "23:59")
    data = result.data
    assert data["period_active"] and data["until"].endswith("23:59")
    assert [r["feature"] for r in data["borrowed"]] == ["nx_base", "drafting"]
    assert data["borrowed"][0]["expires"] == "29-Nov-2026 23:59"
    assert "restart NX" in data["note"]


def test_borrow_until_a_date_and_time():
    year = dt.date.today().year + 1
    now = dt.datetime(year, 1, 1, 9, 0)
    assert borrow.end_of(None, f"{year}-01-05 18:30", now) == dt.datetime(year, 1, 5, 18, 30)
    assert borrow.end_of(None, f"{year}-01-05", now).hour == 23


@pytest.mark.parametrize(
    "days, until",
    [
        (None, None),
        (3, "2030-01-01"),
        (None, "05.01.2030"),
        (None, "2000-01-01"),
        (None, "2099-01-01"),
    ],
)
def test_bad_periods_are_refused(days, until):
    with pytest.raises(NXError) as err:
        borrow.end_of(days, until, dt.datetime(2026, 11, 22, 12, 0))
    assert err.value.code == "NX_INVALID_ARGUMENT"


def test_status_and_end_with_early_return(lm, tmp_path):
    data = side(tmp_path, borrow.nx_get_license_borrowing).data
    assert not data["period_active"] and len(data["borrowed"]) == 2
    data = side(tmp_path, borrow.nx_finish_license_borrowing, return_now=True).data
    assert ("-clear",) in lm
    assert data["returned"] == ["nx_base"] and data["failed"] == ["drafting"]
    assert "in use" in data["note"]


def test_a_refused_borrow_names_the_license_server(monkeypatch, tmp_path):
    monkeypatch.setattr(borrow, "lmutil", lambda: "lmutil.exe")
    monkeypatch.setattr(borrow, "run", lambda exe, *a: (1, "Cannot connect to license server"))
    result = side(tmp_path, borrow.nx_set_license_borrowing, days=2)
    assert result.error["code"] == "NX_LICENSE_UNAVAILABLE"
    assert "VPN" in result.error["hint"]


def test_parse_status_ignores_the_banner():
    assert borrow.parse_status("lmutil - Copyright\nno licenses borrowed\n") == []
