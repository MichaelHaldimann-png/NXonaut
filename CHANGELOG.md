# Changelog

## Unreleased

**New**
- Bill of materials: `nx_get_bill_of_materials` lists the parts of an assembly with item
  number, quantity, material and part attributes (parts only, top level or indented
  with 1.1 numbering), and `nx_export_bill_of_materials` writes it as a CSV Excel opens.
  Experimental until the live acceptance run.
- `nx_list_assembly_constraints` lists an assembly's constraints and says for every
  component whether it is fixed, constrained, broken (a constraint fails) or free.
- Panel: a progress bar for longer jobs (the agent starts its step note with `[3/7]`),
  and a refused step shows what was wrong (`/height must be more than 0`) instead of
  «invalid argument».
- Joints: `nx_create_joint` joins two components as a revolute, cylindrical, slider or
  fixed joint made of assembly constraints (no NX Motion licence needed); drive it with
  `nx_run_motion_sweep`.
- Drawings: a small shaded 3D view top right (drawing rule `pictorial`), and PDF exports
  keep shaded views shaded.
- Rules: a `naming` topic with selectable schemes for part and file names
  (descriptive, number, number_description or your own pattern); pick one in your rule
  file. Part number and description attributes keep BOM and title block in step.

**Fixed**
- NX in German (2512): expressions in «Millimeter» or «Grad» are lengths and angles
  again, so sizes, heights, sketch dimensions and drafts bind to parameters without the
  `name+0` workaround, and expression imports no longer report a unit clash.
- A base drawing view of a part with several bodies is drawn (all bodies, with a note)
  instead of refused, so multi-body parts need no wrapper assembly.

## 0.2.3 (2026-11-20)

- NXonaut button in NX: an **NXonaut** ribbon tab and an **NXonaut** menu with
  **Start NXonaut**. One click starts the bridge (or says it already runs). It appears
  after an NX restart, when **Start with NX** is on.

## 0.2.2 (2026-11-20)

**New**
- The panel shows the NXonaut version and a line when a newer release is on GitHub
  (checked at most once a day, anonymous; `NXONAUT_UPDATE_CHECK=off` turns it off).
- New drawing sheets get a small «made with NXonaut» note top right, as one named note
  (NXONAUT_MARK) you can delete in one step; `nxonaut_mark: false` leaves it out.
- Engineering rules built in: Claude reads them before it designs shafts, fits, threads
  or drawings (`nx_get_design_rules`). Profiles ISO, CH, DE and US, chosen at install
  (**Engineering standards**). Drawing rules include: nothing overlaps.
- Your own rules in `nxonaut-rules.json` in the workspace win over the profile. Claude
  proposes a rule when you correct it and saves it only after you agree
  (`nx_save_design_rule`).
- Manufacturing rules: Claude decides first how a part is made (casting, machining,
  sheet metal, thermoforming, welding, 3D printing) and models to it, e.g. draft and
  radii on cast parts. Each process has a check step that Claude runs before a part is
  done (draft, wall thickness, radii, bend radii, overhangs).
- Hatching: small cut areas are hatched denser than large ones (ISO 128-50); without a
  given spacing `nx_create_hatch` picks it from the region's size.

**Fixed**
- Pictures of assemblies no longer show the constraint symbols, and `nx_set_visibility`
  hides or shows them (`ac:` refs, or `types: ["constraint"]`).
- Hiding datums, sketches, curves and points in a whole assembly no longer fails when
  NX keeps a sketch curve shown (it follows its sketch); the result counts them.
- A revolve that subtracts from two or more bodies now cuts every body, not only the
  first.
- Saving a component no longer reports a failed save because NX marks the assembly
  that shows it as modified; a note says so instead.
- `align` on two cylinders of different size now makes them coaxial instead of tangent.
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
