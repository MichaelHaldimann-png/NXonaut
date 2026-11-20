<p align="center"><img src="assets/nxonaut-hero.svg" alt="NXonaut" /></p>


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


Start with [Install](install.md).
