# Third-party licences

NXonaut is built from the following MIT-licensed projects. Their licence texts are
kept here unchanged; the root `LICENSE` keeps the original copyright line.

| File | Project | Copyright | What NXonaut uses |
| --- | --- | --- | --- |
| `siemens-nx-mcp_and_NX_MCP.LICENSE` | [skyf0l/siemens-nx-mcp](https://github.com/skyf0l/siemens-nx-mcp), [DreamEnding/NX_MCP](https://github.com/DreamEnding/NX_MCP), [xuio/NX_MCP](https://github.com/xuio/NX_MCP) (same licence text) | 2026 NX MCP contributors | The whole server (base: skyf0l); the STEP check in `scripts/validate_step.py` (DreamEnding) |
| `LT60-nx-agent.LICENSE` | [LT60/nx-agent](https://github.com/LT60/nx-agent) | 2026 Liu Tang | The file snapshot and rollback design in `src/nx_mcp/domains/parts_files/snapshots.py` |

Siemens, NX and NXOpen are trademarks of Siemens. NXonaut is not affiliated with or
endorsed by Siemens and contains no Siemens software.
