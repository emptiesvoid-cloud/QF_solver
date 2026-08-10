"""CLI commands for external mesh import."""

from __future__ import annotations

import argparse
from pathlib import Path

from solveur.api import import_gmsh_model, save_model
from solveur.io.manifest import write_json_file


def command_import_mesh(args: argparse.Namespace) -> int:
    """Import one Gmsh mesh and persist model plus provenance report."""
    imported = import_gmsh_model(
        args.mesh,
        args.setup,
        repair_tetra_orientation=bool(args.repair_tetra_orientation),
    )
    save_model(imported.model, args.output)
    report_path = args.report or _default_report_path(args.output)
    write_json_file(report_path, imported.report.to_dict())
    print(
        f"GMSH IMPORT {imported.report.status}: family={imported.report.element_family}, "
        f"nodes={imported.report.node_count}, elements={imported.report.element_count}"
    )
    print(f"model: {Path(args.output)}")
    print(f"report: {Path(report_path)}")
    return 0


def _default_report_path(output: str | Path) -> Path:
    path = Path(output)
    return path.with_name(f"{path.stem}.import_report.json")
