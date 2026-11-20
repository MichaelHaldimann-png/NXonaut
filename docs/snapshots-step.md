# Snapshots and STEP checks

- **File snapshots** (`nx_create_snapshot`, `nx_list_snapshots`, `nx_restore_snapshot`):
  before a risky change the agent copies a saved part file into
  `<workspace>\.nx-mcp\file-snapshots\` and can restore it later. A restore writes a
  new file by default; replacing the original works only for files NX MCP created and
  that are not loaded in NX, and it snapshots the current file first. Like every new
  tool they stay hidden until the acceptance scenario
  `acceptance/parts_files/file_snapshots.json` has passed on your NX
  (`python -m nx_mcp.acceptance verify parts_files`).
- **STEP check outside NX**: `scripts/validate_step.py <file.step> --dims X Y Z
  --volume V` reads an exported STEP with OpenCASCADE and checks that it holds valid
  closed solids of the expected size. It runs in its own Python environment (see the
  script's header).
