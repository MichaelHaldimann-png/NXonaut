<p align="center"><img src="assets/nxonaut-hero.svg" alt="NXonaut" /></p>

## Install and start in 5 steps

1. Download `nxonaut-<version>.mcpb` from the
   [latest release](https://github.com/MichaelHaldimann-png/NXonaut/releases/latest).
2. Double-click the file and click **Install** in Claude Desktop. Leave **Workspace
   folder** empty: NXonaut then uses `C:\Users\<you>\NX_MCP_WORKSPACE`. If **Save**
   stays grey, switch **Start with NX** off and on once.
3. Restart Claude Desktop.
4. Start NX. If the small **NX MCP** panel does not appear by itself, press **Alt+F8**,
   type the full path `C:\Users\<you>\NX_MCP_WORKSPACE\Start NXonaut.py` and click
   **Run**.
5. Ask Claude something, for example:

   > *Create a 100 x 60 x 10 mm plate with a 10 mm hole, put a 30 mm pin in it as an
   > assembly and show me a picture.*

Claude only changes parts it made, or parts you allow on the panel, and only uses files
in the workspace folder.

**Claude Code:** `/plugin install nxonaut --marketplace MichaelHaldimann-png/nxonaut`
(needs [uv](https://docs.astral.sh/uv/)), then steps 4 and 5.
Other MCP clients and more options: [Install](install.md).

## Example: a red road bike frame

One sentence to Claude, in German:

> *Modelliere einen schnellen roten Fahrradrahmen mit Schweisszeichnung.*
> (Model a fast red bike frame with a welding drawing.)

Claude built a parametric diamond frame in NX 2512: tube centrelines in a fully
constrained sketch driven by expressions (seat and head angle, reach, stack, tube sizes),
11 separate steel tubes and dropouts with coped (fishmouth) ends, checked for 14 weld
seams with no overlap. Then an A2 welding drawing with three views, main dimensions,
ISO 2553 fillet weld symbols, a parts list and a weld table, exported to PDF.
From the prompt to the finished PDF took about 11 minutes: some 8 for the model and
3 for the drawing.

<p align="center">
  <img src="assets/examples/bike-frame.png" width="440" alt="Red road bike frame modelled in NX by Claude" />
  <img src="assets/examples/bike-frame-drawing.png" width="440" alt="Welding drawing of the bike frame with weld symbols, parts list and weld table" />
  <br /><sub>Modelled and drawn by NXonaut with Claude in NX 2512, in about 11 minutes.</sub>
</p>

## Example: a gearbox shaft with a production drawing

One sentence to Claude, in German:

> *Modelliere eine Getriebewelle mit Fertigungszeichnung.*
> (Model a gearbox shaft with a production drawing.)

Claude built a stepped shaft in NX 2512 from one revolved profile: k6 bearing and
coupling seats, an m6 gear seat, keyways for DIN 6885 keys, DIN 471 retaining-ring
grooves, a thread undercut, an M30x1.5 thread, DIN 332 centre holes, shoulder radii and
chamfers, plus the two keys as a small assembly. Then an A3 production drawing to Swiss
practice (first-angle projection): fits on every diameter, chained lengths below the
shaft, keyway sections, groove details, datums A and B with circular runout, surface
finish symbols, notes and a filled-in title block, exported to PDF.

<p align="center">
  <img src="assets/examples/shaft.png" width="440" alt="Stepped gearbox shaft with two keys modelled in NX by Claude" />
  <img src="assets/examples/shaft-drawing.png" width="440" alt="Production drawing of the shaft with fits, runout tolerances, sections and details" />
  <br /><sub>Modelled and drawn by NXonaut with Claude in NX 2512.</sub>
</p>

## Example: a workbench assembly from aluminium slot profiles

One sentence to Claude, in German:

> *Baue eine Werkbank aus Alu-Nutprofilen als Baugruppe, mit Zeichnung und Stückliste.*
> (Build a workbench from aluminium slot profiles as an assembly, with a drawing and parts list.)

Claude modelled a generic 40 x 40 slot-8 profile from its cross-section, with the length
as a parameter, and cut it to 850, 1420 and 670 mm. It added corner brackets, levelling
feet and a 1500 x 750 worktop, then assembled the 27 components in NX 2512 with
59 assembly constraints (touch, align, distance, concentric), all solved. Then an A2
assembly drawing to Swiss practice (first-angle projection): front, side and isometric
views, overall dimensions, balloons, a parts list with the cut lengths and a filled-in
title block, exported to PDF.

<p align="center">
  <img src="assets/examples/workbench.png" width="440" alt="Workbench of aluminium slot profiles with a wooden worktop, modelled in NX by Claude" />
  <img src="assets/examples/workbench-drawing.png" width="440" alt="Assembly drawing of the workbench with views, dimensions and balloons" />
  <br /><sub>Modelled and drawn by NXonaut with Claude in NX 2512.</sub>
</p>

## Example: a spur gearbox assembly with an exploded view

One sentence to Claude, in German:

> *Konstruiere ein einstufiges Stirnradgetriebe als Baugruppe, mit Explosionsansicht und Zusammenbauzeichnung.*
> (Design a single-stage spur gearbox as an assembly, with an exploded view and an assembly drawing.)

Claude modelled a split cast housing (cast radii on every unmachined edge, machined faces left sharp), an input shaft with an integral pinion and an output
shaft with a gear (involute teeth, module 2, 19 and 57 teeth, ratio 3 : 1, centre
distance 76 mm), four ball bearings, two shaft seals, four bearing caps, an inspection
cover and the bolts. It assembled the 42 components in NX 2512 with assembly constraints
and component patterns, ran an interference check (clean apart from the thread engagement
of the bolts) and measured the centre distance at 76.000 mm. Then an exploded view and an
A2 assembly drawing to Swiss practice (first-angle projection): two sections through the
shafts, an exploded isometric view, balloons, a parts list, a gear data table and a
filled-in title block, exported to PDF.

<p align="center">
  <img src="assets/examples/gearbox.png" width="440" alt="Coloured exploded view of a single-stage spur gearbox with a green cast housing, shafts, gears, bearings and bolts, modelled in NX by Claude" />
  <img src="assets/examples/gearbox-drawing.png" width="440" alt="A2 assembly drawing of the gearbox with sections, exploded view, balloons and parts list" />
  <br /><sub>Modelled and drawn by NXonaut with Claude in NX 2512.</sub>
</p>

## About NXonaut

Community MCP server for Siemens NX, built first for Claude (Claude Desktop and Claude
Code) and open to any MCP client (Codex, Cursor and others): let an AI assistant model, inspect and draw in NX on Windows: parts, sketches, curves, features,
synchronous edits and body repair, freeform surfaces, sheet metal, assemblies
(arrangements, clearance sets, weight and centre of gravity), motion, topology
optimization and strength checks, measurements and surface analysis, drawings, part
families, Knowledge Fusion rules, render materials and decals, and exports (STEP, PDF,
DXF/DWG and more). You keep working in NX while the agent works next to you.

> NXonaut is a community project. It is **not affiliated with or endorsed by Siemens**
> and contains no Siemens software; Siemens, NX and NXOpen are trademarks of Siemens.
> You need your own licensed NX installation.

NXonaut builds on [skyf0l/siemens-nx-mcp](https://github.com/skyf0l/siemens-nx-mcp),
which grew out of [DreamEnding/NX_MCP](https://github.com/DreamEnding/NX_MCP), and adds
file snapshots with rollback from [LT60/nx-agent](https://github.com/LT60/nx-agent).
See [Credits](credits.md).

**A weekly updated version, based on the different NX MCP projects where the licence
allows it.** Once a week, new open-source NX MCP work on GitHub is reviewed; what is
useful and under a compatible licence (MIT, BSD, Apache 2.0) is merged in, with its
licence kept in [licenses/](https://github.com/MichaelHaldimann-png/NXonaut/blob/master/licenses/) and its authors added to the credits.

The Python package and program keep the upstream name
`nx-mcp` so that upstream changes can still be merged.

Tested on NX 2406; NX 2412 to 2606 are expected to work (see
[Supported NX versions](nx-versions.md)). The full list of tools is in
[Tools](tools.md).
