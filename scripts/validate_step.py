"""Check an exported STEP file independently of NX, with OpenCASCADE (OCP).

Reads the STEP, checks that it holds valid, closed B-rep solids and prints their
bounding box and volume in millimetres. With ``--dims`` and/or ``--volume`` it also
compares them with what you expect, e.g. after changing a dimension in NX.

Runs in its own Python (3.10+) environment, never in NX or the MCP sidecar:

    python -m venv .venv-step
    .venv-step\\Scripts\\pip install "cadquery-ocp>=7.8,<7.10"
    .venv-step\\Scripts\\python scripts\\validate_step.py out\\plate.step --dims 100 60 12

Adapted from ``examples/validate_step_geometry.py`` of
https://github.com/DreamEnding/NX_MCP (MIT, Copyright (c) 2026 NX MCP contributors),
generalised from one fixed acceptance solid to any part.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any


def compare(measured: dict[str, Any], dims=None, volume=None, *, tol=1e-3, vol_tol=None):
    """Problems (text) where ``measured`` differs from the expected values; empty: fine.
    ``dims`` are compared sorted unless ``measured["ordered"]`` is set."""
    problems = []
    if dims is not None:
        actual = list(measured["dimensions"])
        if not measured.get("ordered"):
            actual, dims = sorted(actual), sorted(dims)
        for got, want in zip(actual, dims, strict=True):
            if not math.isclose(got, want, rel_tol=0, abs_tol=tol):
                problems.append(f"dimensions {actual} mm differ from {list(dims)} mm (tol {tol})")
                break
    if volume is not None:
        allowed = vol_tol if vol_tol is not None else max(1e-3, volume * 1e-6)
        if not math.isclose(measured["volume"], volume, rel_tol=0, abs_tol=allowed):
            problems.append(f"volume {measured['volume']:.6g} mm^3 differs from {volume} mm^3")
    return problems


def _inspect_step(path: Path) -> dict[str, Any]:
    # Keep the native geometry dependency out of the sidecar and NX interpreters.
    from OCP.Bnd import Bnd_Box
    from OCP.BRep import BRep_Tool
    from OCP.BRepBndLib import BRepBndLib
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.STEPControl import STEPControl_Reader
    from OCP.TopAbs import (
        TopAbs_EDGE,
        TopAbs_FACE,
        TopAbs_SHELL,
        TopAbs_SOLID,
        TopAbs_VERTEX,
        TopAbs_WIRE,
    )
    from OCP.TopExp import TopExp, TopExp_Explorer
    from OCP.TopTools import TopTools_IndexedMapOfShape

    reader = STEPControl_Reader()
    if reader.ReadFile(str(path)) != IFSelect_RetDone:
        raise ValueError("STEP could not be read")
    file_units = None  # the file's declared length units, where this OCP build reports them
    try:
        from OCP.TColStd import TColStd_SequenceOfAsciiString

        lengths, angles, solid_angles = (TColStd_SequenceOfAsciiString() for _ in range(3))
        reader.FileUnits(lengths, angles, solid_angles)
        file_units = [lengths.Value(i).ToCString() for i in range(1, lengths.Length() + 1)]
    except (ImportError, AttributeError, TypeError):
        pass
    # OCCT expresses this scale in millimetres; set it after loading the STEP model.
    reader.SetSystemLengthUnit(1.0)
    roots = reader.NbRootsForTransfer()
    if roots < 1 or reader.TransferRoots() != roots:
        raise ValueError("STEP transfer failed or left untranslated roots")
    shape = reader.OneShape()
    if shape.IsNull() or not BRepCheck_Analyzer(shape).IsValid():
        raise ValueError("STEP contains null or invalid B-rep geometry")
    solids = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(shape, TopAbs_SOLID, solids)
    if solids.Extent() < 1:
        raise ValueError("STEP contains no solid")
    for kind in (TopAbs_SHELL, TopAbs_FACE, TopAbs_WIRE, TopAbs_EDGE, TopAbs_VERTEX):
        if TopExp_Explorer(shape, kind, TopAbs_SOLID).More():
            raise ValueError("STEP contains geometry outside its solid")
    shells = TopExp_Explorer(shape, TopAbs_SHELL)
    while shells.More():
        if not BRep_Tool.IsClosed_s(shells.Current()):
            raise ValueError("STEP solid contains an open shell")
        shells.Next()
    bounds = Bnd_Box()
    BRepBndLib.AddOptimal_s(shape, bounds, False, False)
    if bounds.IsVoid() or bounds.IsOpen():
        raise ValueError("STEP bounding box is empty or unbounded")
    minimum, maximum = list(bounds.Get()[:3]), list(bounds.Get()[3:])
    properties = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, properties, True, False, False)
    dimensions = [high - low for low, high in zip(minimum, maximum, strict=True)]
    volume = properties.Mass()
    if not all(math.isfinite(value) for value in [*minimum, *maximum, *dimensions, volume]):
        raise ValueError("STEP measurements are nonfinite")
    return {
        "file_length_units": file_units,
        "solid_count": solids.Extent(),
        "length_units": "mm",
        "volume_units": "mm^3",
        "coordinate_system": "step_absolute",
        "min": minimum,
        "max": maximum,
        "dimensions": dimensions,
        "volume": volume,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("step", type=Path, help="The .step/.stp file")
    parser.add_argument(
        "--dims",
        type=float,
        nargs=3,
        metavar=("X", "Y", "Z"),
        help="Expected bounding box size in mm (any order)",
    )
    parser.add_argument("--ordered", action="store_true", help="Compare --dims as X Y Z")
    parser.add_argument("--volume", type=float, help="Expected volume in mm^3")
    parser.add_argument("--tol", type=float, default=1e-3, help="Length tolerance, mm")
    parser.add_argument("--report", type=Path, help="Also write the result as JSON here")
    args = parser.parse_args(argv)
    if args.step.suffix.lower() not in {".step", ".stp"} or not args.step.is_file():
        print(f"Not a STEP file: {args.step}", file=sys.stderr)
        return 2
    report: dict[str, Any] = {"input": str(args.step), "status": "failed"}
    try:
        report["input_sha256"] = hashlib.sha256(args.step.read_bytes()).hexdigest()
        measured = _inspect_step(args.step)
        measured["ordered"] = args.ordered
        report["measurements"] = measured
        report["problems"] = compare(measured, args.dims, args.volume, tol=args.tol)
        report["status"] = "failed" if report["problems"] else "passed"
    except ImportError as error:
        print(
            f'OCP 7.9 is needed (pip install "cadquery-ocp>=7.8,<7.10" in a separate venv): {error}',
            file=sys.stderr,
        )
        return 2
    except Exception as error:  # a broken STEP: report it, never a traceback
        report["problems"] = [str(error)]
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    m = report.get("measurements")
    if m:
        size = " x ".join(f"{v:.4f}" for v in m["dimensions"])
        print(f"{m['solid_count']} solid(s), {size} mm, volume {m['volume']:.4f} mm^3")
    for problem in report["problems"]:
        print("FAIL:", problem)
    print("PASSED" if report["status"] == "passed" else "FAILED")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
