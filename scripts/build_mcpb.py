"""Build the Claude Desktop extension: dist/nxonaut-<version>.mcpb.

The bundle holds the manifest and icon from packaging/claude-desktop, the package
source (src/nx_mcp), the NX side (nx_app), pyproject.toml for Claude's uv runtime,
and the licences. Usage: python scripts/build_mcpb.py
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGING = ROOT / "packaging" / "claude-desktop"
SKIP_PARTS = {"__pycache__", ".pytest_cache"}


def files() -> list[tuple[Path, str]]:
    """(source, name in the bundle) for every bundled file."""
    out = [(p, p.relative_to(PACKAGING).as_posix()) for p in PACKAGING.rglob("*") if p.is_file()]
    for name in ("pyproject.toml", "README.md", "LICENSE"):
        out.append((ROOT / name, name))
    for folder in ("src", "nx_app", "licenses"):
        for path in sorted((ROOT / folder).rglob("*")):
            if path.is_file() and not SKIP_PARTS & set(path.parts) and path.suffix != ".pyc":
                out.append((path, path.relative_to(ROOT).as_posix()))
    return out


def build() -> Path:
    version = json.loads((PACKAGING / "manifest.json").read_text(encoding="utf-8"))["version"]
    target = ROOT / "dist" / f"nxonaut-{version}.mcpb"
    target.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as bundle:
        for source, name in sorted(files(), key=lambda item: item[1]):
            bundle.write(source, name)
    return target


if __name__ == "__main__":
    print(build())
