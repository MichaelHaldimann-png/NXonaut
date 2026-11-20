# Changelog

## 0.2.0 (2026-11-20)

First release after trying NXonaut on a real NX 2512 with Claude Desktop.

**New**
- Install in five steps: download the `.mcpb`, double-click, restart Claude, start NX, ask.
- The NX MCP panel in NX got the NXonaut look: dark night sky, the astronaut, and a
  status pill that says Ready, Working, Waiting for you or NX dialog open. Its step
  history stays short: grouped by part, latest steps only, the rest in Open log.
- Opt-in, anonymous error reports. Off until you say yes; never part names, paths or
  geometry. Reports end up as GitHub issues and feed the weekly build.
- Documentation site with install, settings, troubleshooting and credits, and a short
  README.
- Showcase example: a red bicycle frame modelled by Claude.

**Fixed**
- The workspace field showed `${HOME}` literally (it is now empty, which means
  `C:\Users\<you>\NX_MCP_WORKSPACE`), and a stale `NX_MCP_WORKSPACE` user
  variable could point NX somewhere else. Both are repaired at start now.

**Tested**
- NX 2512.6002: parts, changing a dimension, sketch and extrude, an assembly with fix,
  concentric and touch constraints, STEP export. See
  [Supported NX versions](docs/nx-versions.md).

**Known issues on NX 2512**
- Creating a new part can miss NX's blank template; Claude falls back to another way
  of creating it.
- A feature height cannot yet be bound directly to your own expression; set the value,
  then edit the expression.

## 0.1 (2026-11-20)

First public version, built on skyf0l/siemens-nx-mcp with parts of DreamEnding/NX_MCP,
xuio/NX_MCP and LT60/nx-agent (file snapshots). Claude Desktop extension, Claude Code
plugin, STEP check script.
