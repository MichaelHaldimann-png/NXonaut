"""Claude Desktop extension entry point: runs the NXonaut MCP server (stdio)."""

import sys
from pathlib import Path

# The bundle carries the package source next to this folder (src/nx_mcp).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nx_mcp.server import main  # noqa: E402

if __name__ == "__main__":
    main()
