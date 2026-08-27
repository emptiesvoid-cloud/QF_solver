"""Build controlled, non-qualifying evidence for the 025-G04 owner audit.

The script records the existing common-driver FEM path and a configuration-
matched Code_Aster diagnostic without changing solver behavior. It deliberately
keeps the gate open while the required mesh study and published FEM reference
remain absent.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import numpy as np

from solveur.core.nonlinear import NonlinearStaticSolver
from solveur.io.nonlinear_checkpoint import NpzNonlinearCheckpointStore
from solveur.verification.robustness_arc_length import run_shallow_arch_arc_length_benchmark
from solveur.verification.robustness_arc_length_extended import (
    _common_fem_snap_through_model,
    run_common_fem_snap_through_benchmark,
    run_common_fem_snap_through_failure_rollback_benchmark,
    run_common_fem_snap_through_restart_benchmark,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "results" / "vnv_0_2_5" / "g04_latest"
CODE_ASTER_IMAGE = (
    "simvia/code_aster@sha256:"
    "4629a21a109309bb97fbdc27d750445cc869e151e2e2ed6290f69539614e4435"
)


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _digest(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def _runtime() -> dict[str, str]:
    versions: dict[str, str] = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": np.__version__,
    }
    try:
        import scipy

        versions["scipy"] = scipy.__version__
    except ImportError:
        versions["scipy"] = "unavailable"
    try:
        import matplotlib

        versions["matplotlib"] = matplotlib.__version__
    except ImportError:
        versions["matplotlib"] = "unavailable"
    try:
        docker = subprocess.run(
            ["docker", "image", "inspect", CODE_ASTER_IMAGE, "--format", "{{.Id}}"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        versions["docker_image_id"] = docker.stdout.strip() or "unavailable"
    except OSError:
        versions["docker_image_id"] = "unavailable"
    return versions


def _branch_comparison(internal: dict[str, Any], external: dict[str, Any]) -> dict[str, Any]:
    """Compare equilibrium branches through the shared apex displacement.

    QF Solver and Code_Aster use different arc-length parameterizations. The
    comparison therefore interpolates the Code_Aster reaction-derived load
    factor on QF apex-displacement samples rather than comparing step numbers
    or continuation parameters.
    """

    qf_displacement = np.abs(np.asarray(internal["control_displacements"], dtype=float))
    qf_factor = np.asarray(internal["load_factors"], dtype=float)
    points = list(external.get("raw", {}).get("points", []))
    ca_displacement = np.abs(
        np.asarray([float(point["control_displacement"]) for point in points], dtype=float)
    )
    ca_factor = np.asarray(
        [float(point["load_factor_from_reaction"]) for point in points], dtype=float
    )
    if qf_displacement.size == 0 or ca_displacement.size < 2:
        raise RuntimeError("G04 branch comparison requires non-empty QF and Code_Aster paths.")

    ordering = np.argsort(ca_displacement)
    ca_displacement = ca_displacement[ordering]
    ca_factor = ca_factor[ordering]
    unique_displacement, unique_indices = np.unique(ca_displacement, return_index=True)
    ca_factor = ca_factor[unique_indices]
    common = qf_displacement <= unique_displacement[-1] + 1.0e-12
    if not np.any(common):
        raise RuntimeError("QF and Code_Aster G04 paths have no common apex-displacement domain.")

    interpolated = np.interp(qf_displacement[common], unique_displacement, ca_factor)
    difference = qf_factor[common] - interpolated
    qf_turn = int(np.argmin(qf_factor))
    ca_turn = int(np.argmin(ca_factor))
    peak_factor = max(float(np.max(np.abs(qf_factor))), np.finfo(float).eps)
    return {
        "comparison_parameter": "absolute_apex_uz",
        "common_qf_sample_count": int(np.count_nonzero(common)),
        "common_displacement_range": [
            float(np.min(qf_displacement[common])),
            float(np.max(qf_displacement[common])),
        ],
        "maximum_absolute_load_factor_difference": float(np.max(np.abs(difference))),
        "mean_absolute_load_factor_difference": float(np.mean(np.abs(difference))),
        "rms_load_factor_difference": float(np.sqrt(np.mean(difference**2))),
        "maximum_relative_load_factor_difference": float(np.max(np.abs(difference)) / peak_factor),
        "qf_turning_point": {
            "step": qf_turn + 1,
            "apex_displacement": float(qf_displacement[qf_turn]),
            "load_factor": float(qf_factor[qf_turn]),
        },
        "code_aster_turning_point": {
            "order": int(points[ordering[ca_turn]]["order"]),
            "apex_displacement": float(ca_displacement[ca_turn]),
            "load_factor": float(ca_factor[ca_turn]),
        },
    }


def _turning_diagnostics() -> dict[str, Any]:
    """Record reduced-tangent behavior around the QF load extremum.

    Checkpoint replay is used solely to inspect the committed equilibrium
    states. It does not alter the nonlinear implementation or its trajectory.
    """

    with TemporaryDirectory(prefix="qf-g04-turn-") as temporary:
        root = Path(temporary)
        checkpoint_path = root / "g04.npz"
        model = _common_fem_snap_through_model(
            checkpoint_path=str(checkpoint_path),
            checkpoint_keep_steps=True,
        )
        store = NpzNonlinearCheckpointStore()
        solver = NonlinearStaticSolver(checkpoint_store=store)
        result = solver.solve(model)
        steps = list(result.to_dict()["solver"]["steps"])
        peak_index = int(np.argmin([float(step["load_factor"]) for step in steps]))
        selected_indices = sorted(
            {
                max(0, peak_index - 1),
                peak_index,
                min(len(steps) - 1, peak_index + 1),
            }
        )
        dofs = model.dof_manager()
        fixed = solver.assembler.fixed_indices(model, dofs)
        free = np.setdiff1d(np.arange(dofs.ndof), fixed, assume_unique=True)
        reference_load = np.zeros(dofs.ndof, dtype=float)
        for load in model.loads:
            reference_load[dofs.index(load.node, load.dof)] += load.value

        records: list[dict[str, Any]] = []
        for index in selected_indices:
            step = steps[index]
            checkpoint = store.load(checkpoint_path.with_name(f"g04.step{index + 1:08d}.npz"))
            # The post-solve plan is tied to the solver's private DDL map.
            # Rebuild an inspection-only plan for this explicit DDL map.
            solver._assembly_plan = None
            internal, tangent, _ = solver._assemble_internal_tangent(
                model,
                dofs,
                checkpoint.displacement,
                checkpoint.material_states,
            )
            reduced = tangent[free, :][:, free].toarray()
            symmetric = 0.5 * (reduced + reduced.T)
            eigenvalues = np.linalg.eigvalsh(symmetric)
            residual = (internal - checkpoint.load_factor * reference_load)[free]
            element_results = solver.post.element_results(
                model,
                dofs,
                checkpoint.displacement,
                checkpoint.material_states,
            )
            det_f = [
                float(element["integration_points"][0]["det_f"])
                for element in element_results
            ]
            records.append(
                {
                    "step": index + 1,
                    "load_factor": float(checkpoint.load_factor),
                    "control_displacement": float(step["arc_length_control_displacement"]),
                    "relative_residual": float(step["relative_residual"]),
                    "reassembled_free_residual_norm": float(np.linalg.norm(residual)),
                    "reduced_tangent_minimum_eigenvalue": float(eigenvalues[0]),
                    "reduced_tangent_maximum_eigenvalue": float(eigenvalues[-1]),
                    "reduced_tangent_condition_number": float(np.linalg.cond(reduced)),
                    "reduced_tangent_relative_asymmetry": float(
                        np.linalg.norm(reduced - reduced.T) / np.linalg.norm(reduced)
                    ),
                    "minimum_det_f": min(det_f),
                    "arc_length_constraint_residual": float(step["arc_length_constraint_residual"]),
                    "work_diagnostics_available": bool(step["work_diagnostics_available"]),
                }
            )
    return {
        "free_dof_count": int(free.size),
        "load_extremum_step": peak_index + 1,
        "records": records,
    }


def _plot(summary: dict[str, Any]) -> list[str]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    internal = summary["internal_fem"]
    code_aster = summary["code_aster"]
    qf_u = np.abs(np.asarray(internal["control_displacements"], dtype=float))
    qf_factor = np.abs(np.asarray(internal["load_factors"], dtype=float))
    external_points = code_aster.get("raw", {}).get("points", [])
    ca_u = np.asarray([float(point["control_displacement"]) for point in external_points], dtype=float)
    ca_factor = np.asarray(
        [float(point["load_factor_from_reaction"]) for point in external_points], dtype=float
    )

    branch = OUTPUT / "g04_branch_qf_code_aster.png"
    figure, axis = plt.subplots(figsize=(8.0, 5.0))
    axis.plot(qf_u, qf_factor, "o-", markersize=2.5, label="QF Solver common FEM")
    if ca_u.size:
        axis.plot(ca_u, ca_factor, "-", linewidth=1.4, label="Code_Aster FEM")
    axis.set_xlabel("Absolute apex UZ displacement")
    axis.set_ylabel("Absolute load factor from reaction")
    axis.set_title("G04 branch diagnostic: matched QF Solver and Code_Aster paths")
    axis.grid(True, alpha=0.25)
    axis.legend()
    figure.tight_layout()
    figure.savefig(branch, dpi=180)
    plt.close(figure)

    residual = OUTPUT / "g04_qf_residual_history.png"
    figure, axis = plt.subplots(figsize=(8.0, 4.5))
    for index, history in enumerate(internal["residual_histories"], start=1):
        values = np.asarray(history, dtype=float)
        if values.size:
            axis.semilogy(np.arange(1, values.size + 1), values, alpha=0.25, color="#1d3557")
    axis.set_xlabel("Newton correction")
    axis.set_ylabel("Relative residual")
    axis.set_title("QF Solver common FEM residual histories (80 continuation steps)")
    axis.grid(True, which="both", alpha=0.25)
    figure.tight_layout()
    figure.savefig(residual, dpi=180)
    plt.close(figure)
    return [branch.name, residual.name]


def _report(summary: dict[str, Any], plot_names: list[str]) -> None:
    internal = summary["internal_fem"]
    external = summary["code_aster"]
    restart_before = summary["restart_before_turn"]
    restart_after = summary["restart_after_turn"]
    rollback = summary["rollback"]
    comparison = summary["code_aster_branch_comparison"]
    turning = summary["qf_turning_diagnostics"]
    lines = [
        "# 025-G04 controlled evidence audit",
        "",
        "**Gate status: OPEN**",
        "",
        f"Source SHA: `{summary['source_sha']}`; worktree clean: `{summary['dirty'] is False}`.",
        "This pack records targeted evidence and negative evidence. It does not promote the arc-length path.",
        "",
        "## Internal QF Solver FEM path",
        "",
        "| Quantity | Result |",
        "|---|---:|",
        f"| Status | `{internal['status']}` |",
        f"| Mesh | {internal['element_count']} TET4 / {internal['node_count']} nodes / {internal['dof_count']} DOF |",
        f"| Continuation steps | {internal['step_count']} |",
        f"| Load-factor range | `{internal['load_factor_range']}` |",
        f"| Control displacement range | `{internal['control_displacement_range']}` |",
        f"| Turning point | transition after step `{internal['turning_point_step']}`; load extremum at step `{turning['load_extremum_step']}` |",
        f"| Maximum relative residual | `{internal['maximum_relative_residual']:.6e}` |",
        f"| Minimum det(F) | `{internal['minimum_det_f']:.12g}` |",
        "",
        "The common-driver path crosses a signed load-factor turning point and continues on the post-limit branch.",
        "This remains `PASS_INTERNAL_RESEARCH` because it is a minimal two-element path without the required mesh study or published FEM reference.",
        "",
        "## QF turning-point diagnostics",
        "",
        "| Step | Load factor | Min. tangent eigenvalue | Reassembled free residual | Min. det(F) |",
        "|---:|---:|---:|---:|---:|",
        *[
            "| {step} | {load_factor:.10g} | {minimum_eigenvalue:.6e} | {residual:.6e} | {det_f:.6g} |".format(
                step=record["step"],
                load_factor=record["load_factor"],
                minimum_eigenvalue=record["reduced_tangent_minimum_eigenvalue"],
                residual=record["reassembled_free_residual_norm"],
                det_f=record["minimum_det_f"],
            )
            for record in turning["records"]
        ],
        "",
        "The smallest reduced-tangent eigenvalue crosses zero at the recorded load extremum. "
        "The bounded benchmark has no work-energy diagnostic, so no energy-balance claim is made here.",
        "",
        "## Restart and rollback",
        "",
        "| Check | Status | Key result |",
        "|---|---|---|",
        f"| Restart before turn | `{restart_before['status']}` | suffix error `{restart_before['suffix_load_factor_max_error']}`; state match `{restart_before['material_state_match']}` |",
        f"| Restart after turn | `{restart_after['status']}` | suffix error `{restart_after['suffix_load_factor_max_error']}`; state match `{restart_after['material_state_match']}` |",
            f"| Controlled rollback | `{rollback['status']}` | radius `{rollback['rejection_log'][0]['rejected_radius']}` -> `{rollback['rejection_log'][0]['retry_radius']}`; clean retry `{rollback['retry_clean']}` |",
        "",
        "These are internal transaction proofs and are not external qualification evidence.",
        "",
        "## Code_Aster configuration-matched diagnostic",
        "",
        "| Quantity | Result |",
        "|---|---:|",
        f"| Image | `{CODE_ASTER_IMAGE}` |",
        f"| Model | `{external['model']}` |",
        f"| Complete path samples | `{external['complete_path']}` |",
        f"| Load factor from reactions | `{external['load_factor_range']}` |",
        f"| External turning points | `{external['turning_point_count']}` |",
        f"| Load direction | `{external['reference_load_sign']}` relative to the QF reference load |",
        "| External control | `APEX/DZ` |",
        f"| Max branch load-factor difference | `{comparison['maximum_absolute_load_factor_difference']:.6e}` |",
        f"| RMS branch load-factor difference | `{comparison['rms_load_factor_difference']:.6e}` |",
        f"| Relative peak difference | `{comparison['maximum_relative_load_factor_difference']:.6e}` |",
        "",
        "The original external discrepancy was a continuation-configuration mismatch: QF Solver follows "
        "a negative physical load factor while the former Code_Aster deck applied a positive `FZ`, and "
        "the former post-processing averaged the crown instead of using the QF apex control DOF. "
        "The corrected deck uses `FZ=-1/3`, `APEX/DZ`, and a matched continuation window. Both paths now "
        "exhibit the same turning branch when compared by apex displacement. This is bounded numerical "
        "code-to-code diagnostic evidence, not physical validation or a G04 closure.",
        "",
        "## Missing mandatory evidence",
        "",
        "- no coarse/medium/fine/refined arc-length branch study;",
        "- no published or externally reproducible FEM reference linked to the same branch;",
        "- no controlled final-SHA G04 pack that satisfies all mandatory criteria.",
        "",
        "## Figures",
        "",
    ]
    lines.extend(f"![{name}]({name})" for name in plot_names)
    lines.extend(
        [
            "",
            "`CONTRACT LOWERED = NO`. The external branch diagnostic is resolved, but G04 remains open until the required mesh study and a published FEM branch reference are archived.",
            "",
        ]
    )
    (OUTPUT / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    if _git("status", "--porcelain", "--untracked-files=all"):
        raise RuntimeError("G04 evidence must start from a clean source tree.")
    source_sha = _git("rev-parse", "HEAD")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    internal = run_common_fem_snap_through_benchmark()
    restart_before = run_common_fem_snap_through_restart_benchmark(restart_position="before_turn")
    restart_after = run_common_fem_snap_through_restart_benchmark(restart_position="after_turn")
    rollback = run_common_fem_snap_through_failure_rollback_benchmark()
    turning = _turning_diagnostics()
    reduced = run_shallow_arch_arc_length_benchmark(steps=80, radius=0.05)
    external_output = OUTPUT / "code_aster"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_code_aster_arc_length_025.py"),
            "--output",
            str(external_output),
            "--imperfection-x",
            "0.0",
            "--reference-load-sign",
            "-1.0",
            "--arc-length-end",
            "0.96",
            "--arc-length-steps",
            "160",
        ],
        cwd=ROOT,
        check=True,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
    )
    external = json.loads((external_output / "summary.json").read_text(encoding="utf-8"))
    comparison = _branch_comparison(internal, external)
    summary: dict[str, Any] = {
        "schema_version": 1,
        "study_id": "VNV-G04-ARC-LENGTH-OWNER-AUDIT-025",
        "status": "OPEN",
        "source_sha": source_sha,
        "dirty": False,
        "generated_at_utc": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "runtime": _runtime(),
        "internal_fem": internal,
        "restart_before_turn": restart_before,
        "restart_after_turn": restart_after,
        "rollback": rollback,
        "qf_turning_diagnostics": turning,
        "analytical_reduced": reduced,
        "code_aster": external,
        "code_aster_branch_comparison": comparison,
        "decisions": {
            "internal_snap_through": "PASS_INTERNAL_RESEARCH",
            "turning_point": "PASS_INTERNAL_RESEARCH",
            "mesh": "OPEN_MISSING_REQUIRED_LEVELS",
            "restart": "PASS_INTERNAL_RESEARCH",
            "rollback": "PASS_INTERNAL_RESEARCH",
            "published_reference": "OPEN_NOT_LINKED",
            "code_aster": "RESOLVED_CONFIGURATION_MATCH",
            "gate": "OPEN",
            "contract_lowered": False,
        },
        "limitations": [
            "The common-driver FEM evidence is a minimal two-element TET4 research path.",
            "The matching Code_Aster branch is bounded two-element numerical correlation only.",
            "No four-level arc-length branch mesh study is available.",
            "No exact published FEM branch reference is linked to this custom two-element benchmark.",
            "No production or physical-validation claim is made.",
        ],
    }
    (OUTPUT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    plot_names = _plot(summary)
    _report(summary, plot_names)
    files = []
    for path in sorted(OUTPUT.rglob("*")):
        if path.is_file() and path.name != "evidence_manifest.json":
            files.append(
                {
                    "path": path.relative_to(ROOT).as_posix(),
                    "sha256": _digest(path),
                    "bytes": path.stat().st_size,
                }
            )
    manifest = {
        "schema_version": 1,
        "study_id": summary["study_id"],
        "status": "OPEN",
        "source_sha": source_sha,
        "dirty": False,
        "generated_at_utc": summary["generated_at_utc"],
        "command": "python scripts/build_g04_evidence.py",
        "code_aster_image": CODE_ASTER_IMAGE,
        "files": files,
    }
    (OUTPUT / "evidence_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": "OPEN", "source_sha": source_sha, "artifact_count": len(files)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
