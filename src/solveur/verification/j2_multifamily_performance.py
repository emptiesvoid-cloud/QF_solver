"""Four-family bounded J2 nonlinear performance characterization."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, cast

import numpy as np

from solveur.api import solve_model
from solveur.benchmarks.gmsh_factory import BenchmarkMeshFactory
from solveur.io.json_writer import JsonResultWriter
from solveur.io.manifest import write_json_file
from solveur.mesh.gmsh_importer import GmshModelImporter

CONTRACT_RELATIVE_PATH = Path("qualification/0_2_9/wp13_r2_multifamily/wp13_r2_1_execution_contract.json")
RAW_OUTPUT_RELATIVE_PATH = Path("qualification/0_2_9/wp13_r2_multifamily/raw")
EXPECTED_BRANCH = "codex/wp13-r2-multifamily"
EXPECTED_POLICY_DIGEST = "93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac"


class J2MultiFamilyPerformanceCampaign:
    """Record bounded solve-cost indicators for TET4/TET10/HEX8/HEX20 J2 bars.

    Every case uses the same physical bar, material, load path and traction.
    Mesh topology differs by family and is recorded explicitly. Timings are
    characterization only; this is not a speedup or scalability benchmark.
    """

    campaign_id = "VNV-J2-MULTIFAMILY-NONLINEAR-PERFORMANCE-001"
    element_types = ("TET4", "TET10", "HEX8", "HEX20")
    dimensions = (1.0, 0.2, 0.2)
    hex_cells = (6, 2, 2)
    tetra_mesh_size = 0.18

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir).resolve()

    def run(self) -> dict[str, object]:
        expected_output = Path.cwd() / RAW_OUTPUT_RELATIVE_PATH
        if self.output_dir != expected_output.resolve():
            raise RuntimeError(f"WP13 R2 output must be the frozen raw path: {expected_output}.")
        if self.output_dir.exists() and any(self.output_dir.iterdir()):
            raise FileExistsError(f"WP13 R2 output directory is not empty: {self.output_dir}")
        execution_metadata = _capture_execution_metadata()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        rows = [self._run_case(family) for family in self.element_types]
        status = "PASS_INTERNAL" if all(row["status"] == "PASS" for row in rows) else "FAIL"
        summary: dict[str, object] = {
            "campaign_id": self.campaign_id,
            "status": status,
            "maturity": "experimental",
            "execution_metadata": execution_metadata,
            "scope": {
                "purpose": "bounded nonlinear driver performance characterization",
                "element_types": list(self.element_types),
                "geometry": {"length": self.dimensions[0], "width": self.dimensions[1], "height": self.dimensions[2]},
                "material": {
                    "type": "von_mises_elastoplastic_3d",
                    "E": 210.0e9,
                    "nu": 0.3,
                    "yield_stress": 250.0e6,
                    "hardening_modulus": 50.0e9,
                },
                "load_path": _j2_cyclic_setup("TET4")["analysis"]["load_path"],
                "x_max_traction": [300.0e6, 0.0, 0.0],
                "tetra_mesh_size": self.tetra_mesh_size,
                "hexa_cells": list(self.hex_cells),
                "scalability_claim": False,
                "external_correlation": False,
            },
            "cases": rows,
            "interpretation": (
                "The measurements characterize this bounded small J2 bar on one machine. "
                "Different interpolation orders and mesh topologies mean raw times are descriptive, "
                "not an element-efficiency ranking or a scaling result."
            ),
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._write_report(summary)
        return summary

    def _run_case(self, family: str) -> dict[str, object]:
        case_dir = self.output_dir / family
        case_dir.mkdir(parents=True, exist_ok=False)
        if family.startswith("TET"):
            order = 2 if family == "TET10" else 1
            mesh_path = BenchmarkMeshFactory().box_tetra(
                case_dir / "mesh.msh",
                length=self.dimensions[0],
                width=self.dimensions[1],
                height=self.dimensions[2],
                mesh_size=self.tetra_mesh_size,
                order=order,
                anchors=True,
                include_anchor_x=False,
            )
            mesh_configuration: dict[str, object] = {
                "generator": "BenchmarkMeshFactory.box_tetra",
                "mesh_size": self.tetra_mesh_size,
                "order": order,
            }
        else:
            order = 2 if family == "HEX20" else 1
            mesh_path = BenchmarkMeshFactory().box_hexa(
                case_dir / "mesh.msh",
                length=self.dimensions[0],
                width=self.dimensions[1],
                height=self.dimensions[2],
                cells=self.hex_cells,
                order=order,
                anchors=True,
            )
            mesh_configuration = {
                "generator": "BenchmarkMeshFactory.box_hexa",
                "cells": list(self.hex_cells),
                "order": order,
            }

        setup = _j2_cyclic_setup(family)
        setup_path = case_dir / "setup.json"
        write_json_file(setup_path, setup)
        imported = GmshModelImporter().import_model(mesh_path, setup_path)
        model = imported.model
        write_json_file(case_dir / "import_report.json", imported.report.to_dict())
        expected_import_warnings = (
            {
                "Physical group 'y_min' (dimension 2) is unused.",
                "Physical group 'z_min' (dimension 2) is unused.",
            }
            if family.startswith("TET")
            else set()
        )
        import_valid = (
            imported.report.mesh_status == "PASS" and set(imported.report.warnings) == expected_import_warnings
        )

        tracemalloc.start()
        started = perf_counter()
        try:
            result = solve_model(model)
            elapsed = perf_counter() - started
            _, peak_python_bytes = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()

        JsonResultWriter().write(result, case_dir / "result.json")
        data = result.to_dict()
        try:
            json.dumps(data, allow_nan=False)
            full_result_finite = True
        except (TypeError, ValueError):
            full_result_finite = False
        steps = data["solver"]["steps"]
        residuals = [float(step["relative_residual"]) for step in steps]
        residual_history = [float(value) for step in steps for value in step.get("residual_history", [])]
        state_count = sum(len(item.get("integration_points", [])) for item in data["material_states"])
        displacements = np.asarray(result.displacements, dtype=float)
        finite = (
            bool(np.all(np.isfinite(displacements)))
            and all(np.isfinite(residuals))
            and all(np.isfinite(residual_history))
        )
        valid_steps = len(steps) == 24 and len(residuals) == 24 and len(residual_history) > 0
        case_status = (
            "PASS"
            if result.status == "PASS" and finite and full_result_finite and valid_steps and import_valid
            else "FAIL"
        )
        return {
            "element_type": family,
            "status": case_status,
            "solver_status": result.status,
            "solver_method": data["method"],
            "solver_message": data["message"],
            "import_status": imported.report.status,
            "import_mesh_status": imported.report.mesh_status,
            "import_warnings": imported.report.warnings,
            "mesh_configuration": mesh_configuration,
            "node_count": model.node_count,
            "element_count": len(model.elements),
            "dof_count": int(displacements.size),
            "integration_point_state_count": state_count,
            "elapsed_seconds": float(elapsed),
            "peak_python_memory_bytes": int(peak_python_bytes),
            "increments": len(steps),
            "all_expected_increments_present": valid_steps,
            "full_result_json_finite": full_result_finite,
            "total_newton_iterations": int(sum(int(step["iterations"]) for step in steps)),
            "maximum_relative_residual": max(residuals, default=float("inf")),
            "final_relative_residual": residuals[-1] if residuals else float("inf"),
            "residual_samples": len(residual_history),
            "full_result_archived": True,
            "notes": [
                "Timing covers solve_model after mesh generation and import.",
                "Memory is Python tracemalloc peak, not process RSS.",
            ],
        }

    def _write_report(self, summary: dict[str, object]) -> None:
        lines = [
            f"# {self.campaign_id}",
            "",
            f"Status: **{summary['status']}**",
            "",
            "| Element | Nodes | Elements | DOFs | Gauss states | Time [s] | Newton | Max residual | Python peak [B] | Status |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
        for row in cast(list[dict[str, Any]], summary["cases"]):
            lines.append(
                f"| {row['element_type']} | {row['node_count']} | {row['element_count']} | {row['dof_count']} | "
                f"{row['integration_point_state_count']} | {row['elapsed_seconds']:.6f} | "
                f"{row['total_newton_iterations']} | {row['maximum_relative_residual']:.6e} | "
                f"{row['peak_python_memory_bytes']} | {row['status']} |"
            )
        lines.extend(["", str(summary["interpretation"]), ""])
        (self.output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def _j2_cyclic_setup(element_type: str) -> dict[str, Any]:
    """Return the frozen common J2 bar setup without R1's TET-only guard."""
    family = element_type.upper()
    if family not in J2MultiFamilyPerformanceCampaign.element_types:
        raise ValueError(f"Unsupported WP13 R2 element family: {element_type!r}.")
    return {
        "schema_version": 1,
        "mesh_scale_to_m": 1.0,
        "units": {"system": "SI"},
        "verification_profile": "engineering",
        "analysis": {
            "type": "nonlinear_static",
            "method": "newton_raphson",
            "load_steps": 25,
            "load_path": [
                0.25,
                0.5,
                0.75,
                1.0,
                0.75,
                0.5,
                0.25,
                0.0,
                -0.25,
                -0.5,
                -0.75,
                -1.0,
                -1.2,
                -1.0,
                -0.75,
                -0.5,
                -0.25,
                0.0,
                0.25,
                0.5,
                0.75,
                1.0,
                1.2,
                1.4,
            ],
            "max_iterations": 50,
            "tolerance": 1.0e-7,
        },
        "materials": {
            "j2": {
                "type": "von_mises_elastoplastic_3d",
                "E": 210.0e9,
                "nu": 0.3,
                "yield_stress": 250.0e6,
                "hardening_modulus": 50.0e9,
            }
        },
        "groups": [
            {
                "name": "domain",
                "dimension": 3,
                "actions": [{"type": "elements", "element_type": family, "material": "j2"}],
            },
            {"name": "x_min", "dimension": 2, "actions": [{"type": "fixed_dofs", "dofs": ["UX"]}]},
            {"name": "anchor_origin", "dimension": 0, "actions": [{"type": "fixed_dofs", "dofs": ["UY", "UZ"]}]},
            {"name": "anchor_xy", "dimension": 0, "actions": [{"type": "fixed_dofs", "dofs": ["UZ"]}]},
            {"name": "x_max", "dimension": 2, "actions": [{"type": "surface_traction", "value": [300.0e6, 0.0, 0.0]}]},
        ],
    }


def _capture_execution_metadata() -> dict[str, object]:
    """Fail closed unless the exact frozen R2 checkout and sources are active."""
    root_text = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], check=True, capture_output=True, text=True
    ).stdout.strip()
    root = Path(root_text).resolve()

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
        ).stdout.strip()

    branch = git("branch", "--show-current")
    head = git("rev-parse", "HEAD")
    parent = git("rev-parse", "HEAD^")
    if branch != EXPECTED_BRANCH:
        raise RuntimeError(f"WP13 R2 must execute on {EXPECTED_BRANCH}; found {branch!r}.")
    if git("status", "--porcelain", "--untracked-files=all"):
        raise RuntimeError("WP13 R2 requires a clean Git worktree before execution.")

    contract_path = root / CONTRACT_RELATIVE_PATH
    if not contract_path.is_file():
        raise RuntimeError(f"WP13 R2 frozen contract is missing: {contract_path}.")
    contract_bytes = contract_path.read_bytes()
    contract = json.loads(contract_bytes)
    if contract.get("contract_id") != "QF-029-WP13-EXEC-003":
        raise RuntimeError("WP13 R2.1 contract ID does not match this runner.")
    if contract.get("status") != "FROZEN_EXECUTION_PROTOCOL":
        raise RuntimeError("WP13 R2 contract is not frozen.")
    if contract.get("execution_branch") != branch:
        raise RuntimeError("WP13 R2 contract branch does not match the active branch.")
    if contract.get("policy_digest") != EXPECTED_POLICY_DIGEST:
        raise RuntimeError("WP13 R2 solver policy digest does not match the approved frozen policy.")
    if contract.get("raw_output_path") != RAW_OUTPUT_RELATIVE_PATH.as_posix():
        raise RuntimeError("WP13 R2 contract raw output path does not match the runner.")
    if contract.get("pre_contract_sha") != parent:
        raise RuntimeError("WP13 R2 HEAD is not the commit immediately following the bound implementation SHA.")
    source_hashes = contract.get("source_sha256")
    if not isinstance(source_hashes, dict) or not source_hashes:
        raise RuntimeError("WP13 R2 contract has no source-file hash bindings.")
    observed_hashes: dict[str, str] = {}
    for relative_path, expected_hash in source_hashes.items():
        path = root / str(relative_path)
        observed = hashlib.sha256(path.read_bytes()).hexdigest()
        observed_hashes[str(relative_path)] = observed
        if observed != expected_hash:
            raise RuntimeError(f"WP13 R2 source hash mismatch: {relative_path}.")

    try:
        import psutil

        physical_cpu_count = psutil.cpu_count(logical=False)
        total_ram_bytes = psutil.virtual_memory().total
    except ImportError:
        physical_cpu_count = None
        total_ram_bytes = None

    return {
        "branch": branch,
        "execution_sha": head,
        "implementation_sha": parent,
        "working_tree_clean_before_run": True,
        "contract_path": CONTRACT_RELATIVE_PATH.as_posix(),
        "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
        "policy_digest": contract["policy_digest"],
        "source_sha256": observed_hashes,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": sys.argv,
        "environment": {
            "platform": platform.platform(),
            "processor": platform.processor(),
            "physical_cpu_count": physical_cpu_count,
            "logical_cpu_count": os.cpu_count(),
            "total_ram_bytes": total_ram_bytes,
            "python": sys.version,
            "numpy": np.__version__,
            "gmsh": _package_version("gmsh"),
        },
    }


def _package_version(package: str) -> str | None:
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version(package)
    except PackageNotFoundError:
        return None
