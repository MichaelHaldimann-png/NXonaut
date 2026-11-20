<p align="center">
  <img src="docs/assets/nxonaut-hero.svg" width="900" alt="NXonaut: AI agents model, inspect and export in Siemens NX" />
</p>

# NXonaut

Let Claude work next to you in **Siemens NX**: parts, sketches, assemblies with
constraints, measurements, drawings and STEP export.

**Documentation: [michaelhaldimann-png.github.io/NXonaut](https://michaelhaldimann-png.github.io/NXonaut/)**

## Install

**Claude Desktop:** download `nxonaut-<version>.mcpb` from the
[latest release](https://github.com/MichaelHaldimann-png/NXonaut/releases/latest),
double-click it and click **Install**.

**Claude Code:** `/plugin install nxonaut --marketplace MichaelHaldimann-png/nxonaut`
(needs [uv](https://docs.astral.sh/uv/)).

## Start in NX

Restart NX: NXonaut starts with it and a small **NX MCP** panel appears. If not, press
**Alt+F8** and play `Start NXonaut.py` from `C:\Users\<you>\NX_MCP_WORKSPACE`.

Then ask Claude, for example:

> *Create a 100 x 60 x 10 mm plate with a 10 mm hole, put a 30 mm pin in it as an
> assembly and show me a picture.*

Claude only changes parts it made, or parts you allow on the panel, and only uses files
in the workspace folder.

## Credits

NXonaut builds on [skyf0l/siemens-nx-mcp](https://github.com/skyf0l/siemens-nx-mcp),
[DreamEnding/NX_MCP](https://github.com/DreamEnding/NX_MCP),
[xuio/NX_MCP](https://github.com/xuio/NX_MCP) and
[LT60/nx-agent](https://github.com/LT60/nx-agent) (all MIT). It is a weekly updated
version, based on the NX MCP projects where the licence allows it.
[What comes from where](https://michaelhaldimann-png.github.io/NXonaut/credits/).

MIT licence, see [LICENSE](LICENSE) and [licenses/](licenses/). **Not affiliated with or
endorsed by Siemens**; Siemens, NX and NXOpen are trademarks of Siemens. You need your
own licensed NX.
