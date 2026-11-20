# Changelog

## Unreleased

**New**
- Engineering rules built in: Claude reads them before it designs shafts, fits, threads
  or drawings (`nx_get_design_rules`). Profiles ISO, CH, DE and US, chosen at install
  (**Engineering standards**). Drawing rules include: nothing overlaps.
- Your own rules in `nxonaut-rules.json` in the workspace win over the profile. Claude
  proposes a rule when you correct it and saves it only after you agree
  (`nx_save_design_rule`).

**Fixed**
- Drawings: a tolerance frame, surface finish symbol, weld symbol or note now starts its
  leader on the side that faces the edge it points to. Before, NX always put it on the
  left, so a leader to an edge on the right ran under the frame.
- Drawings: notes, symbols, tolerance frames and dimensions warn when they lie over
  another annotation or cross a dimension's lines.

## 0.2.1 (2026-11-20)

Same content as the published 0.2.0. A new number because an earlier test build was
also called 0.2.0; with 0.2.1 Claude Desktop clearly sees the update.

- Several Claude chats on one NX take turns, and NX gets a short pause after heavy
  steps such as large drawing views.
- Pure NX information dialogs such as «Ereignisliste aktualisieren» are closed with OK
  and noted in the panel. Every other dialog is only reported, as before.

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
