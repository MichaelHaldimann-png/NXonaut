# Supported NX versions

| NX release | Support |
| --- | --- |
| 2406 | **Tested**: the tools are checked on live NX before a release |
| 2512 | **Used in practice**: parts, dimension changes, sketch and extrude, assemblies with fix, concentric and touch constraints, and STEP export worked on NX 2512.6002 (November 2026). The full acceptance run is still to come |
| 2412, 2506, 2606 | **Expected to work**: every NXOpen call NX MCP makes exists there, but it is not tested on them |
| 2306, 2312 | **Best effort**: some tools may fail (about 35 on 2306, 8 on 2312) |

NX's own Python must be 3.10 or newer: `start.py` refuses an older one and says so.
The MCP program needs Python 3.10 or newer too.

On a release it was not tested on, the agent is offered every tool tested on another
release, marked untested. A tool that fails there because NX lacks a call it needs
reports `NX_VERSION_UNSUPPORTED`: nothing is changed, and the tool is not offered again
until NX restarts. Set `NX_MCP_UNTESTED=read_only` for NX and the client to offer
only the tools that read or change the view on such a release.

`.venv\Scripts\python -m nx_mcp.report --capabilities` writes
`<workspace>\.nx-mcp\capabilities.html`, a page for you only: per domain, the tools
tested on your NX, offered untested, not supported there, and refused for a licence in
this NX session.

**Reporting a problem.** Run `.venv\Scripts\python -m nx_mcp.report` while NX runs: it
writes `<workspace>\nx-mcp-report-<build>-<date>.json` (NX, NX MCP, Python and Windows
versions, the tools that failed for a missing NXOpen call, the last verify's counts;
never licences, error messages, part names, paths or user names). Check it, then attach
it to an issue with the lines `start.py` printed, the tool name, the error code the
agent got, and `<workspace>\.nx-mcp\resident-error.txt` if the add-on did not start.
Leave out which NX licences or modules you have, and your parts, drawings and file
names; a small part made only to show the problem is welcome.

**Verifying your NX release** (to make it a tested one). With NX running and no part
loaded in it, from this folder:

```powershell
.venv\Scripts\python -m nx_mcp.acceptance verify --owner <your-name>
```

It replays every acceptance scenario on new parts under `<workspace>\smoke\` (or only
the domains you name, e.g. `verify modeling sketch`) and closes them; it refuses to
start while other parts are loaded, and counts a tool NX refuses for a licence as
skipped without recording it. Scenarios that play the engineer need NX started with
`NX_MCP_DEV=1`; without it they are skipped. At the end it prints the files under
`acceptance\evidence\<build>\` to send (in a pull request or attached to an issue) and a
summary. Those files hold only pass/fail, check counts, error codes and numbers.
