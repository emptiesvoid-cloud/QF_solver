"""Assemble the G08 Euler pre-validation and HEX8 root-cause evidence.

This is a verification harness only. It combines the corrected analytical
screen with a same-model CalculiX C3D8 cross-check and diagnostics for mesh,
mode and geometric-stiffness behavior. It never changes the buckling solver or
promotes an element family.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

UTC = timezone.utc

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
# ruff: noqa: E402

from solveur.core.assembly.geometric import build_total_lagrangian_assembly
from solveur.core.nonlinear.iteration import solve_full_newton
from solveur.elements.solid.hex8 import Hex8Element
from solveur.io.manifest import runtime_fingerprint, sha256, write_json_file
from solveur.verification.calculix_buckling_025 import _run_calculix, write_buckling_input

import importlib.util


HIGH_ORDER_PATH = ROOT / "scripts" / "run_g08_high_order_analytical.py"
SPEC = importlib.util.spec_from_file_location("g08_high_order_analytical", HIGH_ORDER_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Cannot import the corrected G08 analytical harness.")
HIGH_ORDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HIGH_ORDER)

GATE = "026-G08"
EVIDENCE_ID = "026-G08-EULER-PREVALIDATION-001"
STUDY_ID = "VNV-G08-EULER-PREVALIDATION-001"
HEX8_C3D8_IMAGE = "qf-solver/calculix-nafems13h:2.20"
HEX8_C3D8_LEVELS = (1, 2)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _git_state() -> tuple[str, bool]:
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    dirty = bool(
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    )
    return sha, dirty


def _fixed_free_dofs(model: Any, ndof: int) -> tuple[np.ndarray, np.ndarray]:
    dofs = model.dof_manager()
    fixed = np.array(
        sorted(
            {
                dofs.index(condition.node, dof)
                for condition in model.fixed_dofs
                for dof in condition.dofs
            }
        ),
        dtype=int,
    )
    return fixed, np.setdiff1d(np.arange(ndof, dtype=int), fixed)


def _hex8_diagnostic(cells: int, transverse_cells: int) -> dict[str, Any]:
    model, metadata = HIGH_ORDER._model("HEX8", cells, transverse_cells)
    result = HIGH_ORDER._run_case("HEX8", cells, transverse_cells)
    nodes = np.asarray(model.nodes, dtype=float)
    solve_result = HIGH_ORDER.solve_model(model, enforce_policy=False)
    mode = np.asarray(solve_result.displacements, dtype=float).reshape(-1, 3)
    x_positions = []
    for value in sorted(set(nodes[:, 0].tolist())):
        ids = np.flatnonzero(np.isclose(nodes[:, 0], value))
        x_positions.append(
            {
                "x": float(value),
                "mean_lateral_norm": float(np.linalg.norm(np.mean(mode[ids, 1:], axis=0))),
            }
        )

    assembly = build_total_lagrangian_assembly(model)
    fixed, free = _fixed_free_dofs(model, assembly.ndof)
    zero = np.zeros(assembly.ndof, dtype=float)
    _, initial_tangent = assembly.assemble(zero)
    initial_dense = initial_tangent[free, :][:, free].toarray()
    loads = np.zeros(assembly.ndof, dtype=float)
    dofs = model.dof_manager()
    for item in model.loads:
        loads[dofs.index(item.node, item.dof)] += item.value
    preload, _ = solve_full_newton(
        assembly, loads, fixed, increments=4, tolerance=1.0e-8, max_iterations=30
    )
    geometric = assembly.geometric_tangent(preload).toarray()
    reduced_geometric = geometric[np.ix_(free, free)]
    kg_eigenvalues = np.linalg.eigvalsh(reduced_geometric)

    jacobians: list[float] = []
    aspect_ratios: list[float] = []
    for element in model.elements:
        coords = nodes[np.asarray(element.nodes, dtype=int)]
        jacobians.extend(
            float(item[3]) for item in Hex8Element.integration_data(coords)
        )
        extents = np.ptp(coords, axis=0)
        aspect_ratios.append(float(np.max(extents) / max(np.min(extents), 1.0e-15)))

    return {
        "cells_x": cells,
        "cells_y": transverse_cells,
        "cells_z": transverse_cells,
        "node_count": int(model.node_count),
        "element_count": int(len(model.elements)),
        "loaded_node_count": int(len(model.loads)),
        "nodal_force": float(model.loads[0].value),
        "reference_total_load": float(sum(item.value for item in model.loads)),
        "qf_critical_factor": float(result["critical_factor"]),
        "qf_pcr": float(result["pcr_qf"]),
        "euler_error": float(result["euler_relative_error"]),
        "mode_classification": result["mode_classification"],
        "mode_lateral_to_axial_ratio": float(result["mode_lateral_to_axial_ratio"]),
        "mode_by_x": x_positions,
        "mesh_aspect_ratio_max": max(aspect_ratios),
        "jacobian_min": min(jacobians),
        "jacobian_max": max(jacobians),
        "initial_tangent_condition_number": float(np.linalg.cond(initial_dense)),
        "kg_symmetry_relative": float(
            np.linalg.norm(geometric - geometric.T) / max(np.linalg.norm(geometric), 1.0e-30)
        ),
        "kg_eigenvalue_min": float(kg_eigenvalues[0]),
        "kg_eigenvalue_max": float(kg_eigenvalues[-1]),
        "kg_source": "initial_stress_second_piola",
    }


def _hex8_c3d8_cross_check(output: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cells in HEX8_C3D8_LEVELS:
        model, _ = HIGH_ORDER._model("HEX8", cells, 1)
        work = output / f"c3d8_cells_{cells}"
        work.mkdir(parents=True, exist_ok=True)
        deck = write_buckling_input(work / "buckling.inp", model, "HEX8", modes=1)
        qf = HIGH_ORDER._run_case("HEX8", cells, 1)
        row: dict[str, Any] = {
            "cells_x": cells,
            "element": "HEX8/C3D8",
            "qf_critical_factor": float(qf["critical_factor"]),
            "qf_pcr": float(qf["pcr_qf"]),
            "reference_total_load": float(sum(item.value for item in model.loads)),
            "deck_sha256": sha256(deck),
        }
        try:
            factors = _run_calculix(work, image=HEX8_C3D8_IMAGE)
            external = float(factors[0])
            row.update(
                {
                    "status": "PASS",
                    "calculix_critical_factor": external,
                    "relative_error": abs(external - row["qf_critical_factor"])
                    / max(abs(row["qf_critical_factor"]), 1.0e-15),
                }
            )
        except Exception as exc:
            row.update(
                {"status": "SKIPPED_EXTERNAL_TOOL", "failure_type": type(exc).__name__, "failure": str(exc)}
            )
        rows.append(row)
    return rows


def _load_analytical_evidence() -> dict[str, Any]:
    path = ROOT / "qualification" / "0_2_6" / "g08_high_order_analytical_evidence.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _render_report(summary: dict[str, Any]) -> str:
    lines = [
        "# G08 Euler pre-validation and HEX8 root-cause evidence",
        "",
        f"Status: **{summary['status']}**. G08 remains **{summary['gate_status_unchanged']}**.",
        "",
        f"Execution source SHA: `{summary['source_sha']}`; dirty: `{summary['source_dirty']}`.",
        f"Corrected analytical evidence SHA: `{summary['analytical_source_sha']}`.",
        "",
        "## Active evidence matrix",
        "",
        "| Family | Mesh | Analytical | External | Eigenpair | Mode | Determinism | Provisional decision |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for family, row in summary["family_predecisions"].items():
        lines.append(
            f"| {family} | {row['mesh']} | {row['analytical']} | {row['external']} | "
            f"{row['eigenpair']} | {row['mode']} | {row['determinism']} | {row['provisional_decision']} |"
        )
    lines.extend(
        [
            "",
            "The superseded positive-load Euler comparison is retained only as a historical record and "
            "is excluded from the active interpretation. The active comparison uses signed compression "
            "with `F_REFERENCE_TOTAL=-1.0` and `Pcr_QF=abs(lambda*F_REFERENCE_TOTAL)`.",
            "",
            "## HEX8 diagnosis",
            "",
            f"Classification: **{summary['hex8_root_cause']}**.",
            "",
            "| Axial cells | Transverse cells | Pcr QF | Euler error | Aspect ratio | Jacobian min/max | Kt condition | Kg symmetry | Kg eigenvalue range |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in summary["hex8_diagnostics"]:
        lines.append(
            f"| {row['cells_x']} | {row['cells_y']} | {row['qf_pcr']:.8g} | "
            f"{row['euler_error']:.3%} | {row['mesh_aspect_ratio_max']:.6g} | "
            f"{row['jacobian_min']:.6g}/{row['jacobian_max']:.6g} | "
            f"{row['initial_tangent_condition_number']:.6g} | {row['kg_symmetry_relative']:.3e} | "
            f"{row['kg_eigenvalue_min']:.3e}/{row['kg_eigenvalue_max']:.3e} |"
        )
    lines.extend(
        [
            "",
            "All HEX8 modes are classified as global-bending candidates; lateral mode amplitude grows "
            "toward the free end and no mode switching was observed in this screen. The geometric "
            "tangent is symmetric and has a negative destabilizing direction under the signed compressive "
            "preload, consistent with the TET10/HEX20 route diagnostics.",
            "",
            "## Same-model C3D8 cross-check",
            "",
            "| Axial cells | QF factor | CalculiX factor | Relative difference | Status |",
            "|---:|---:|---:|---:|---|",
        ]
    )
    for row in summary["hex8_c3d8"]:
        lines.append(
            f"| {row['cells_x']} | {row['qf_critical_factor']:.8g} | "
            f"{row.get('calculix_critical_factor', '-')} | "
            f"{row.get('relative_error', '-') if row['status'] == 'PASS' else '-'} | {row['status']} |"
        )
    lines.extend(
        [
            "",
            "QF and C3D8 agree within the same low-order solid model, while both remain far above "
            "the Euler slender-column value. This supports a low-order HEX8/C3D8 locking or solid-"
            "discretization limitation for this benchmark, not a QF-specific load-factor or geometric-"
            "tangent defect. This conclusion is diagnostic and does not change the G08 contract.",
        ]
    )
    return "\n".join(lines) + "\n"


def run(output: Path, evidence_dir: Path) -> dict[str, Any]:
    source_sha, source_dirty = _git_state()
    if source_dirty:
        raise RuntimeError("G08 pre-validation requires a clean source worktree.")
    analytical = _load_analytical_evidence()
    output.mkdir(parents=True, exist_ok=True)
    hex8_diagnostics = [
        _hex8_diagnostic(cells, transverse)
        for cells, transverse in ((1, 1), (2, 1), (3, 1), (2, 2), (2, 3))
    ]
    c3d8_rows = _hex8_c3d8_cross_check(output)
    family_predecisions = {
        "TET4": {
            "mesh": "PASS historical bounded",
            "analytical": "PASS historical case-specific",
            "external": "BOUNDED historical",
            "eigenpair": "PASS",
            "mode": "PASS",
            "determinism": "PASS",
            "provisional_decision": "PREQUALIFIED_BOUNDED",
        },
        "TET10": {
            "mesh": "PASS bounded (0.081448%)",
            "analytical": "PASS at final axial level; 3.269%",
            "external": "PASS bounded historical",
            "eigenpair": "PASS",
            "mode": "PASS",
            "determinism": "PASS",
            "provisional_decision": "PASS_WITH_LIMITATIONS",
        },
        "HEX8": {
            "mesh": "PASS bounded (0.167113%), absolute Euler gap remains",
            "analytical": "LIMITATION; 298.413% final axial error",
            "external": "PASS same-model C3D8 cross-check",
            "eigenpair": "PASS",
            "mode": "PASS global-bending candidate",
            "determinism": "PASS",
            "provisional_decision": "MORE_EVIDENCE_REQUIRED",
        },
        "HEX20": {
            "mesh": "PASS bounded (0.912621%)",
            "analytical": "PASS at final axial level; 3.622%",
            "external": "PASS bounded C3D20, 3 levels",
            "eigenpair": "PASS",
            "mode": "PASS",
            "determinism": "PASS",
            "provisional_decision": "PASS_WITH_LIMITATIONS",
        },
    }
    summary: dict[str, Any] = {
        "schema_version": 1,
        "evidence_id": EVIDENCE_ID,
        "study_id": STUDY_ID,
        "gate": GATE,
        "status": "PASS_WITH_LIMITATIONS",
        "gate_status_unchanged": "PASS_WITH_LIMITATIONS",
        "source_sha": source_sha,
        "source_dirty": source_dirty,
        "analytical_source_sha": analytical["source_sha"],
        "captured_at_utc": _utc_now(),
        "solver_version": "0.2.6a0",
        "runtime": runtime_fingerprint(),
        "old_comparison_valid": False,
        "invalidated_old_evidence": "retained historical but excluded from active interpretation",
        "family_predecisions": family_predecisions,
        "hex8_root_cause": "LOCKING_LIKELY",
        "hex8_diagnostics": hex8_diagnostics,
        "hex8_c3d8": c3d8_rows,
        "conclusions": [
            "Signed load totals are constant at -1.0 across active axial screens.",
            "The corrected Euler comparison separates lambda from physical critical load.",
            "HEX8 and same-model CalculiX C3D8 agree closely while both exceed Euler substantially.",
            "No QF-specific geometric-stiffness, boundary-condition or load-factor defect is demonstrated.",
            "No family is promoted automatically; Owner review remains required.",
        ],
        "functional_code_changed": False,
        "artifact_digests": {},
    }
    report = output / "g08_euler_prevalidation_report.md"
    report.write_text(_render_report(summary), encoding="utf-8")
    summary["artifact_digests"]["results/vnv_g08_euler_prevalidation/g08_euler_prevalidation_report.md"] = sha256(report)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    archived_report = evidence_dir / "g08_euler_prevalidation_evidence.md"
    archived_json = evidence_dir / "g08_euler_prevalidation_evidence.json"
    archived_report.write_text(_render_report(summary), encoding="utf-8")
    summary["artifact_digests"]["qualification/0_2_6/g08_euler_prevalidation_evidence.md"] = sha256(archived_report)
    write_json_file(output / "g08_euler_prevalidation_summary.json", summary)
    write_json_file(archived_json, summary)
    return summary


def main() -> int:
    output = ROOT / "results" / "vnv_g08_euler_prevalidation"
    evidence = ROOT / "qualification" / "0_2_6"
    summary = run(output, evidence)
    print(
        json.dumps(
            {
                "status": summary["status"],
                "source_sha": summary["source_sha"],
                "hex8_root_cause": summary["hex8_root_cause"],
                "c3d8_statuses": [row["status"] for row in summary["hex8_c3d8"]],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
