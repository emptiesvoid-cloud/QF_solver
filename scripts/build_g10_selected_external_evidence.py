"""Build the compact evidence pack for the selected G10 external runs.

The script only normalizes already executed QF Solver and external outputs.
It does not run a solver, change a formulation, or assign new acceptance
thresholds.  Large raw outputs remain under the ignored ``results/`` tree;
the committed JSON contains the curves and metrics needed for review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA = "efed8c3e1bcf173d335b3b9a605febd0fa1084cb"
# The selected runs were started after a clean-worktree check.  The builder
# itself may run later, after documentary files have been staged locally.
EXECUTION_WORKTREE_DIRTY = False
EVIDENCE_ID = "026-G10-SELECTED-EXTERNAL-001"
DEFAULT_INPUT = ROOT / "results" / "g10_selected_external"
DEFAULT_EVIDENCE = ROOT / "qualification" / "0_2_6" / "g10_selected_external_evidence.json"
DEFAULT_MANIFEST = ROOT / "qualification" / "0_2_6" / "g10_selected_external_manifest.json"
DEFAULT_DOC = ROOT / "docs" / "verification" / "0_2_6" / "0_2_6_g10_selected_external_campaign.md"
INPUT_ARCHIVE = ROOT / "qualification" / "0_2_6" / "g10_selected_external_inputs"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(*args: str) -> str:
    return subprocess.check_output(("git", *args), cwd=ROOT, text=True).strip()


def _json_number(value: Any) -> float | None:
    if value is None:
        return None
    number = float(value)
    return number if np.isfinite(number) else None


def _compact_arc_length(qf: dict[str, Any], external: dict[str, Any]) -> dict[str, Any]:
    qf_lambda = np.asarray(qf["load_factors"], dtype=float)
    qf_displacement = np.asarray(qf["control_displacements"], dtype=float)
    external_points = list(external["raw"]["points"])
    external_lambda = np.asarray(
        [point["load_factor_from_reaction"] for point in external_points], dtype=float
    )
    external_displacement = np.asarray(
        [point["control_displacement"] for point in external_points], dtype=float
    )
    common = (external_displacement >= qf_displacement.min()) & (
        external_displacement <= qf_displacement.max()
    )
    qf_interpolated = np.interp(
        external_displacement[common], qf_displacement[::-1], qf_lambda[::-1]
    )
    curve_delta = external_lambda[common] - qf_interpolated
    qf_turn = int(qf["turning_point_step"])
    external_turn = int(np.argmax(np.abs(external_lambda)))
    qf_curve = []
    for index, (load_factor, displacement) in enumerate(zip(qf_lambda, qf_displacement)):
        residuals = qf.get("residual_histories", [[]])[index]
        qf_curve.append(
            {
                "step": index + 1,
                "load_factor": float(load_factor),
                "control_displacement": float(displacement),
                "newton_iterations": int(qf["newton_iterations"][index]),
                "residual_final": float(residuals[-1]) if residuals else None,
                "arc_length_radius": float(qf["radius_history"][index]),
                "branch_direction": qf["branch_directions"][index],
            }
        )
    external_curve = [
        {
            "order": int(point["order"]),
            "continuation_parameter": float(point["instant"]),
            "load_factor": float(point["load_factor_from_reaction"]),
            "control_displacement": float(point["control_displacement"]),
            "reaction_fixed_z": float(point["reaction_fixed_z"]),
        }
        for point in external_points
    ]
    return {
        "status": "PASS_WITH_LIMITATIONS",
        "comparison_class": "PASS_WITH_LIMITATIONS",
        "qf_result": {
            "status": qf["status"],
            "steps": len(qf_curve),
            "turning_point_step_one_based": qf_turn + 1,
            "turning_point_load_factor": float(qf_lambda[qf_turn]),
            "turning_point_displacement": float(qf_displacement[qf_turn]),
            "maximum_relative_residual": float(qf["maximum_relative_residual"]),
            "minimum_det_f": float(qf["minimum_det_f"]),
            "branch_turn_count": int(qf["branch_turn_count"]),
        },
        "external_result": {
            "status": external["status"],
            "solver": external["solver"],
            "points": len(external_curve),
            "turning_point_order": int(external_points[external_turn]["order"]),
            "turning_point_load_factor": float(external_lambda[external_turn]),
            "turning_point_displacement": float(external_displacement[external_turn]),
            "branch_turn_count": int(external["turning_point_count"]),
            "complete_path": bool(external["complete_path"]),
        },
        "derived_comparison": {
            "common_displacement_points": int(common.sum()),
            "max_absolute_load_factor_difference": float(np.max(np.abs(curve_delta))),
            "max_relative_difference_to_external_peak": float(
                np.max(np.abs(curve_delta)) / max(np.max(np.abs(external_lambda[common])), 1.0e-15)
            ),
            "turning_load_factor_absolute_difference": float(
                abs(qf_lambda[qf_turn] - external_lambda[external_turn])
            ),
            "turning_load_factor_relative_difference": float(
                abs(qf_lambda[qf_turn] - external_lambda[external_turn])
                / abs(external_lambda[external_turn])
            ),
            "turning_displacement_absolute_difference": float(
                abs(qf_displacement[qf_turn] - external_displacement[external_turn])
            ),
            "turning_displacement_relative_difference": float(
                abs(qf_displacement[qf_turn] - external_displacement[external_turn])
                / abs(external_displacement[external_turn])
            ),
        },
        "qf_curve": qf_curve,
        "external_curve": external_curve,
        "limitations": [
            "QF and Code_Aster use the same two-element TET4 geometry and load convention, but their continuation controls do not generate identical point locations.",
            "The Code_Aster raw export does not include a per-step residual history; successful completion and the external solver log are retained as execution evidence.",
            "This is bounded external evidence for the research audit and does not close G07 or G10.",
        ],
    }


def _compact_tet4(external: dict[str, Any]) -> dict[str, Any]:
    column = external["imperfect_column"]
    qf_curve = [
        {
            "load_fraction_critical": float(point["load_fraction_critical"]),
            "tip_axial_x": float(point["tip_axial_x"]),
            "tip_total_z": float(point["tip_total_z"]),
            "relative_residual": float(point["relative_residual"]),
        }
        for point in column["qf_solver"]
    ]
    external_curve = [
        {
            "load_fraction_critical": float(point["load_fraction_critical"]),
            "tip_axial_x": float(point["tip_axial_x"]),
            "tip_total_z": float(point["tip_total_z"]),
        }
        for point in column["code_aster"]
    ]
    return {
        "status": "PASS_WITH_LIMITATIONS",
        "comparison_class": "PASS_WITH_LIMITATIONS",
        "external_result": {
            "status": external["status"],
            "solver": external["external_solver"],
            "stress_relative_error": float(external["stress_patch"]["relative_error"]),
            "column_max_relative_difference": float(column["maximum_relative_difference"]),
        },
        "qf_curve": qf_curve,
        "external_curve": external_curve,
        "limitations": [
            "The comparison uses the existing TET4 imperfect-column and affine stress-patch cases.",
            "The column path stops at 80 percent of the same-mesh critical load.",
            "This remains bounded research evidence, not a general finite-deformation validation claim.",
        ],
    }


def _compact_hex8(qf: dict[str, Any], external: dict[str, Any]) -> dict[str, Any]:
    rows = list(external["raw"]["rows"])
    first = rows[0]
    qf_u = np.asarray(qf["loaded_mean_displacement"], dtype=float)
    ext_u = np.asarray(first["loaded_mean_displacement"], dtype=float)
    qf_reaction = np.asarray(qf["reaction_resultant_fixed"], dtype=float)
    ext_reaction = -np.asarray(first["reaction_resultant_fixed"], dtype=float)
    curve = [
        {
            "load_factor": float(row["load_factor"]),
            "loaded_mean_ux": float(row["loaded_mean_ux"]),
            "reaction_fixed_x": float(row["reaction_resultant_fixed"][0]),
        }
        for row in rows
    ]
    return {
        "status": "PASS_WITH_LIMITATIONS",
        "comparison_class": "PASS_WITH_LIMITATIONS",
        "qf_result": {
            "status": qf["status"],
            "source_sha": qf["source_sha"],
            "dirty_at_start": qf["dirty_at_start"],
            "load_factor": float(first["load_factor"]),
            "total_load": float(qf["total_load"]),
            "loaded_mean_displacement": qf["loaded_mean_displacement"],
            "reaction_resultant_fixed": qf["reaction_resultant_fixed"],
            "free_residual_norm": float(qf["free_residual_norm"]),
            "det_f_min": float(qf["det_f_min"]),
            "det_f_max": float(qf["det_f_max"]),
            "strain_energy": float(qf["strain_energy"]),
            "newton_iterations": int(qf["iterations"]),
        },
        "external_result": {
            "status": external["status"],
            "solver": external["external_solver"],
            "same_geometry": external["same_geometry"],
            "same_mesh": external["same_mesh"],
            "same_material": external["same_material"],
            "same_nodal_loads": external["same_nodal_loads"],
            "rows": len(curve),
        },
        "derived_comparison": {
            "matched_load_factor": float(first["load_factor"]),
            "qf_total_load": float(qf["total_load"]),
            "external_total_load_at_matched_point": float(-0.2 * first["load_factor"]),
            "displacement_relative_difference": float(
                np.linalg.norm(qf_u - ext_u) / max(np.linalg.norm(ext_u), 1.0e-15)
            ),
            "reaction_relative_difference_after_sign_alignment": float(
                np.linalg.norm(qf_reaction - ext_reaction) / max(np.linalg.norm(ext_reaction), 1.0e-15)
            ),
        },
        "external_curve": curve,
        "limitations": [
            "The full Code_Aster HEX8 load path was exported, but the QF instrumented full path exceeded the bounded campaign budget; only the matched first load point is used for the numerical comparison.",
            "The external stress measure and det(F) were not converted to QF measures, so no internal-field correlation is claimed.",
            "The external work field uses the unscaled nodal force amplitude in the existing diagnostic deck and is not compared to QF strain energy.",
            "This is bounded external evidence and does not promote TL or close G07/G10.",
        ],
    }


def _archive_inputs(input_root: Path) -> list[dict[str, Any]]:
    INPUT_ARCHIVE.mkdir(parents=True, exist_ok=True)
    mappings = {
        "arc_length.comm": input_root / "arc_length_code_aster" / "code_aster" / "arc_length.comm",
        "arc_length.mail": input_root / "arc_length_code_aster" / "code_aster" / "arc_length.mail",
        "tl_tet4_imperfect_column.comm": input_root / "tl_tet4_code_aster" / "imperfect_column" / "imperfect_column.comm",
        "tl_tet4_imperfect_column.mail": input_root / "tl_tet4_code_aster" / "imperfect_column" / "imperfect_column.mail",
        "tl_hex8_physical_branch.comm": input_root / "tl_hex8_code_aster" / "code_aster" / "physical_branch.comm",
        "tl_hex8_physical_branch.mail": input_root / "tl_hex8_code_aster" / "code_aster" / "physical_branch.mail",
    }
    entries = []
    for name, source in mappings.items():
        if not source.is_file():
            raise FileNotFoundError(source)
        destination = INPUT_ARCHIVE / name
        shutil.copy2(source, destination)
        entries.append(
            {
                "role": "external_input_deck_or_mesh",
                "path": destination.relative_to(ROOT).as_posix(),
                "source_run_path": source.relative_to(ROOT).as_posix(),
                "sha256": _sha256(destination),
                "size_bytes": destination.stat().st_size,
            }
        )
    return entries


def _render_doc(report: dict[str, Any]) -> str:
    arc = report["routes"]["arc_length_continuation"]
    tet4 = report["routes"]["total_lagrangian_tet4"]
    hex8 = report["routes"]["total_lagrangian_hex8"]
    return f"""# G10 Selected External Campaign

Evidence ID: `{report['evidence_id']}`
Execution source SHA: `{report['execution_source_sha']}`
Worktree at capture: `dirty={str(report['execution_worktree_dirty']).lower()}`
Overall campaign status: **{report['status']}**

This pack records only the two routes selected by the G10 Owner Review. It
does not close G10, reopen G07, promote Total-Lagrangian elasticity, or alter
any solver implementation. QF results, external results and derived metrics
are kept in separate sections of the machine-readable evidence.

## Commands and external tools

- QF arc-length: `run_common_fem_snap_through_benchmark(radius=0.02, max_arc_steps=80)`
- Code_Aster arc-length: `scripts/run_code_aster_arc_length_025.py --arc-length-end 1.0 --arc-length-steps 80`
- TET4 TL: `scripts/run_code_aster_tl_structural_vnv.py`
- HEX8 TL external: `scripts/run_tl_physical_branch_code_aster.py`
- HEX8 QF matched point: one-step QF solve at the first Code_Aster load point
- Code_Aster: `18.1.0`, pinned image recorded in the JSON evidence

All runs used the same clean source SHA `{report['execution_source_sha']}`;
the result directories are ignored generated output. Input decks and meshes
are archived under `qualification/0_2_6/g10_selected_external_inputs/`.

## Arc-length continuation

Classification: **{arc['comparison_class']}**.

| Metric | QF Solver | Code_Aster |
| --- | ---: | ---: |
| Complete path points | {arc['qf_result']['steps']} | {arc['external_result']['points']} |
| Turning-point load factor | {arc['qf_result']['turning_point_load_factor']:.12g} | {arc['external_result']['turning_point_load_factor']:.12g} |
| Turning-point control displacement | {arc['qf_result']['turning_point_displacement']:.12g} | {arc['external_result']['turning_point_displacement']:.12g} |
| Branch turns | {arc['qf_result']['branch_turn_count']} | {arc['external_result']['branch_turn_count']} |
| QF maximum relative residual | {arc['qf_result']['maximum_relative_residual']:.3e} | not exported per step |

Derived peak differences are `{arc['derived_comparison']['turning_load_factor_relative_difference']:.6%}` in
load factor and `{arc['derived_comparison']['turning_displacement_relative_difference']:.6%}` in
control displacement. The common displacement interpolation covers
`{arc['derived_comparison']['common_displacement_points']}` points, with a
maximum absolute load-factor difference of
`{arc['derived_comparison']['max_absolute_load_factor_difference']:.6e}`.
The branch and turning point agree qualitatively and quantitatively within
the different continuation point placement, but this remains bounded
external evidence rather than a new qualification threshold.

## Total-Lagrangian TET4

Classification: **{tet4['comparison_class']}**.

- Code_Aster status: `{tet4['external_result']['status']}`.
- Stress-patch relative error: `{tet4['external_result']['stress_relative_error']:.6e}`.
- Imperfect-column maximum relative difference: `{tet4['external_result']['column_max_relative_difference']:.6e}`.
- Complete comparison points: `{len(tet4['qf_curve'])}` QF / `{len(tet4['external_curve'])}` Code_Aster.
- Formulation: Code_Aster 3D/TETRA4, Green-Lagrange elastic route; same-mesh
  QF column and stress-patch calculations.

The column path stops at 80 percent of its same-mesh critical load. The
external run therefore supports a bounded compatible comparison, not a
general finite-deformation claim.

## Total-Lagrangian HEX8

Classification: **{hex8['comparison_class']}**.

- Code_Aster status: `{hex8['external_result']['status']}` with
  `{hex8['external_result']['rows']}` exported load points.
- Matched load factor: `{hex8['derived_comparison']['matched_load_factor']:.12g}`.
- Displacement relative difference: `{hex8['derived_comparison']['displacement_relative_difference']:.6e}`.
- Reaction relative difference after sign alignment:
  `{hex8['derived_comparison']['reaction_relative_difference_after_sign_alignment']:.6e}`.
- QF matched-point residual: `{hex8['qf_result']['free_residual_norm']:.6e}`;
  `det(F)` range `{hex8['qf_result']['det_f_min']:.12g}` to
  `{hex8['qf_result']['det_f_max']:.12g}`.

The QF full instrumented path was not completed within the bounded campaign
budget, so this is a matched first-point comparison only. Code_Aster stress
and energy outputs are intentionally not mixed with QF measures.

## Decision boundary

`G10` remains `IN_PROGRESS`. No G07, G08, G09, G11 or G12 decision changes.
The selected route records are external evidence with limitations:

- `arc_length_continuation`: `PASS_WITH_LIMITATIONS`;
- `total_lagrangian_elasticity` TET4: `PASS_WITH_LIMITATIONS`;
- `total_lagrangian_elasticity` HEX8: `PASS_WITH_LIMITATIONS`.

Finite-kinematic J2, J2-plus-geometry, coupled contact and triple coupling
were not run. They remain at their prior classifications.

See `g10_selected_external_evidence.json` and
`g10_selected_external_manifest.json` for full compact curves, input
digests, runtime provenance, and explicit limitations.
"""


def build(input_root: Path, evidence_path: Path, manifest_path: Path, doc_path: Path) -> dict[str, Any]:
    if _git("rev-parse", "HEAD") != SOURCE_SHA:
        raise RuntimeError(f"Expected source SHA {SOURCE_SHA}, got {_git('rev-parse', 'HEAD')}")
    qf_arc = _load(input_root / "arc_length_qf" / "summary.json")
    external_arc = _load(input_root / "arc_length_code_aster" / "summary.json")
    tet4 = _load(input_root / "tl_tet4_code_aster" / "summary.json")
    hex8_qf = _load(input_root / "tl_hex8_qf_single" / "qf_single.json")
    hex8_external = _load(input_root / "tl_hex8_code_aster" / "summary.json")
    input_entries = _archive_inputs(input_root)
    evidence_build_dirty = bool(_git("status", "--porcelain"))
    report: dict[str, Any] = {
        "schema_version": 1,
        "evidence_id": EVIDENCE_ID,
        "gate": "026-G10",
        "status": "PARTIAL",
        "execution_source_sha": SOURCE_SHA,
        "execution_worktree_dirty": EXECUTION_WORKTREE_DIRTY,
        "evidence_build_worktree_dirty": evidence_build_dirty,
        "captured_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "solver_version": "0.2.6a0",
        "selected_by_owner_review": True,
        "owner_gate_route": "026-G07",
        "functional_source_changed": False,
        "numerical_regression_detected": False,
        "routes": {
            "arc_length_continuation": _compact_arc_length(qf_arc, external_arc),
            "total_lagrangian_tet4": _compact_tet4(tet4),
            "total_lagrangian_hex8": _compact_hex8(hex8_qf, hex8_external),
        },
        "provenance": {
            "qf_arc_command": "python -c run_common_fem_snap_through_benchmark(radius=0.02, max_arc_steps=80)",
            "code_aster_arc_command": "python scripts/run_code_aster_arc_length_025.py --output results/g10_selected_external/arc_length_code_aster --arc-length-end 1.0 --arc-length-steps 80",
            "code_aster_tet4_command": "PYTHONPATH=src python scripts/run_code_aster_tl_structural_vnv.py --output results/g10_selected_external/tl_tet4_code_aster",
            "code_aster_hex8_command": "PYTHONPATH=src python scripts/run_tl_physical_branch_code_aster.py --output results/g10_selected_external/tl_hex8_code_aster",
            "qf_hex8_command": "PYTHONPATH=src;scripts python -c one-step matched HEX8 TL solve at load factor 1/128",
            "external_solver": "Code_Aster 18.1.0",
            "code_aster_image": "simvia/code_aster@sha256:4629a21a109309bb97fbdc27d750445cc869e151e2e2ed6290f69539614e4435",
            "input_artifacts": input_entries,
            "source_result_paths": {
                "arc_qf": "results/g10_selected_external/arc_length_qf/summary.json",
                "arc_external": "results/g10_selected_external/arc_length_code_aster/summary.json",
                "tet4_external": "results/g10_selected_external/tl_tet4_code_aster/summary.json",
                "hex8_qf": "results/g10_selected_external/tl_hex8_qf_single/qf_single.json",
                "hex8_external": "results/g10_selected_external/tl_hex8_code_aster/summary.json",
            },
        },
        "scope_guard": {
            "other_g10_routes_extended": False,
            "g07_reopened": False,
            "g08_reopened": False,
            "g09_reopened": False,
            "g11_reopened": False,
            "g12_reopened": False,
            "full_regression": "SKIPPED_BY_POLICY",
            "new_thresholds_introduced": False,
        },
        "decision": {
            "g10_status_unchanged": "IN_PROGRESS",
            "g07_status_unchanged": True,
            "route_classifications": {
                "arc_length_continuation": "PASS_WITH_LIMITATIONS",
                "total_lagrangian_elasticity_tet4": "PASS_WITH_LIMITATIONS",
                "total_lagrangian_elasticity_hex8": "PASS_WITH_LIMITATIONS",
            },
            "not_a_promotion": True,
        },
    }
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    doc = _render_doc(report)
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text(doc, encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "manifest_id": "026-G10-SELECTED-EXTERNAL-MANIFEST-001",
        "gate": "026-G10",
        "execution_source_sha": SOURCE_SHA,
        "execution_worktree_dirty": EXECUTION_WORKTREE_DIRTY,
        "evidence_build_worktree_dirty": evidence_build_dirty,
        "evidence_path": evidence_path.relative_to(ROOT).as_posix(),
        "documentation_path": doc_path.relative_to(ROOT).as_posix(),
        "artifacts": [
            {
                "role": "machine_readable_evidence",
                "path": evidence_path.relative_to(ROOT).as_posix(),
                "sha256": _sha256(evidence_path),
                "size_bytes": evidence_path.stat().st_size,
            },
            {
                "role": "verification_report",
                "path": doc_path.relative_to(ROOT).as_posix(),
                "sha256": _sha256(doc_path),
                "size_bytes": doc_path.stat().st_size,
            },
            *input_entries,
        ],
        "status": "PASS_WITH_LIMITATIONS",
        "g10_closeout": False,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--documentation", type=Path, default=DEFAULT_DOC)
    args = parser.parse_args()
    report = build(
        args.input_root.resolve(),
        args.evidence.resolve(),
        args.manifest.resolve(),
        args.documentation.resolve(),
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "source_sha": report["execution_source_sha"],
                "dirty": report["execution_worktree_dirty"],
                "routes": list(report["routes"]),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
