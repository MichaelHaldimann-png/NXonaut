# Install

## Claude Desktop (easiest)

1. Download `nxonaut-<version>.mcpb` from the
   [latest release](https://github.com/MichaelHaldimann-png/NXonaut/releases/latest).
2. Double-click it (or drag it into Claude Desktop, *Settings > Extensions*) and click
   **Install**. Claude Desktop sets up Python and everything else by itself.
3. Restart NX. With **Start with NX** on (the default), NX starts NXonaut by itself and
   a small **NX MCP** panel appears. If you already use `UGII_USER_DIR`, press
   **Alt+F8** in NX instead and play `Start NXonaut.py` from your workspace folder
   (`C:\Users\<you>\NX_MCP_WORKSPACE`).

Then ask Claude, for example: *"Create a 100 x 60 x 10 mm plate with four 6.6 mm holes
10 mm from the edges, and show me a picture."*

## Claude Code (plugin)

Needs [uv](https://docs.astral.sh/uv/) (`winget install astral-sh.uv`). In Claude Code:

```text
/plugin install nxonaut --marketplace MichaelHaldimann-png/nxonaut
```

On older Claude Code versions: `/plugin marketplace add MichaelHaldimann-png/NXonaut`,
then `/plugin install nxonaut@nxonaut`. In NX, press **Alt+F8** and play
`Start NXonaut.py` from your workspace folder (written when the server first starts).
Some NX calls take a minute or more: set the `MCP_TOOL_TIMEOUT` environment variable to
`300000` if Claude Code gives up too early.

## Manual install

For other MCP clients (Codex, Cursor and others) and for development.

You need Git and Python 3.10 or newer:

```powershell
git clone https://github.com/MichaelHaldimann-png/NXonaut.git
cd NXonaut
python -m venv .venv
.venv\Scripts\pip install -e .
```

Point your MCP client at `.venv\Scripts\nx-mcp.exe`, for example in Codex:
`codex mcp add nx -- "C:\path\to\NXonaut\.venv\Scripts\nx-mcp.exe"`, or in
`claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "nx": { "command": "C:\\path\\to\\NXonaut\\.venv\\Scripts\\nx-mcp.exe" }
  }
}
```

In NX, play `nx_app\journals\start.py` with **Alt+F8**, or let NX start it by itself:
`setx UGII_USER_DIR "C:\path\to\NXonaut\nx_app"` (if you already use
`UGII_USER_DIR`, add the `nx_app` folder to `custom_dirs.dat` instead).
