# Settings

Set these in the client's server entry (`claude mcp add ... -e NAME=value`, or `env` in
Codex), and for NX where noted.

| Variable | Use |
| --- | --- |
| `NX_MCP_WORKSPACE` | Another workspace folder. Set the same value for NX and the client |
| `NX_MCP_SURFACE` | `full` shows every NX tool to the client directly (more context, fewer steps); default `agent` |
| `NXONAUT_ERROR_REPORTS` | `on` or `off`: anonymous error reports (see [Error reports](error-reports.md)); off by default |
| `NX_MCP_BRIDGE_DESCRIPTOR` | Only for a non-standard setup: the bridge file NX writes (for NX, `NX_MCP_UI_DESCRIPTOR` sets where it writes it) |
