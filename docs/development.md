# For developers

Architecture: [docs/design/architecture.md](design/architecture.md); tool rules:
[docs/design/tool-surface.md](design/tool-surface.md); how to add a tool and the
live NX test loop: [CLAUDE.md](https://github.com/MichaelHaldimann-png/NXonaut/blob/master/CLAUDE.md); tested scope per NX build:
[docs/capability-matrix.md](capability-matrix.md). Several agents building one
product in one NX: [docs/guides/multi-agent-builds.md](guides/multi-agent-builds.md).

```powershell
.venv\Scripts\pip install -e ".[dev]"
.venv\Scripts\python -m pre_commit install --install-hooks
.venv\Scripts\python -m pre_commit run --all-files
.venv\Scripts\python -m pytest -q -p no:cacheprovider -m "not real_nx" --basetemp .pytest-tmp
.venv\Scripts\python -m mypy src/nx_mcp
```
