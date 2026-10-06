"""Generate structured WP06 GYRO-05/06 Campbell evidence from the frozen contract."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import scipy
from scipy.linalg import eig

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for candidate in (PROJECT_ROOT / "src", PROJECT_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from solveur.core.analyses.campbell import CampbellSolver  # noqa: E402
from solveur.core.analyses.modal_tracking import track_modal_sweep  # noqa: E402
from solveur.core.analyses.settings import AnalysisSettings  # noqa: E402
from solveur.core.dofs import DOF_ORDER  # noqa: E402
from solveur.core.model import BoundaryCondition, ElementDefinition, FiniteElementModel  # noqa: E402
from solveur.elements.discrete import RotatingDisk  # noqa: E402
from solveur.post.campbell import save_campbell_plot  # noqa: E402
from solveur.version import __version__  # noqa: E402


CONTRACT_PATH = PROJECT_ROOT / "qualification/0_2_11/wp06_campbell_contract.json"
WP05_CONTRACT_PATH = PROJECT_ROOT / "qualification/0_2_11/wp05_gyroscopic_contract.json"
TRACKING_POLICY = "QF0211-COMPLEX-MAC-GLOBAL-v1"
QEP_CONTRACT = "wp05-frozen-qep-v1"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_sha() -> str:
    completed = subprocess.run(
        ["git", "-C", str(PROJECT_ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    )
    return completed.stdout.strip()


def _metric(name: str, expected: float, observed: float, threshold: float, *, absolute: bool = False) -> dict[str, Any]:
    error = abs(observed - expected)
    relative = error / max(abs(expected), abs(observed), 1.0) if not absolute else error
    value = error if absolute else relative
    return {
        "metric": name,
        "expected_value": expected,
        "observed_value": observed,
        "absolute_error": error,
        "relative_error": relative,
        "threshold": threshold,
        "comparison_error": value,
        "status": "PASS" if value <= threshold else "FAIL",
    }


def _qep_snapshot(omega: float, *, mass: float, diametral: float, polar: float, stiffness: float) -> SimpleNamespace:
    """Independent two-coordinate companion solve; does not call WP05 QEP/G assembly."""

    matrix_m = diametral * np.eye(2)
    matrix_k = stiffness * np.eye(2)
    matrix_g = np.asarray([[0.0, polar], [-polar, 0.0]])
    zero = np.zeros((2, 2))
    identity = np.eye(2)
    pencil_a = np.block([[zero, identity], [-matrix_k, -omega * matrix_g]])
    pencil_b = np.block([[identity, zero], [zero, matrix_m]])
    roots, vectors = eig(pencil_a, pencil_b, check_finite=True)
    physical = np.flatnonzero(roots.imag > 64.0 * np.finfo(float).eps * max(1.0, float(np.max(abs(roots)))))
    frequencies = np.abs(roots[physical].imag) / (2.0 * np.pi)
    order = np.argsort(frequencies, kind="stable")
    roots = roots[physical][order]
    frequencies = frequencies[order]
    modes = vectors[:2, physical][:, order].astype(np.complex128)
    residuals = []
    for index, root in enumerate(roots):
        vector = modes[:, index]
        norm = float(np.vdot(vector, matrix_m @ vector).real)
        if not np.isfinite(norm) or norm <= np.finfo(float).tiny:
            raise RuntimeError("Independent analytical fixture produced a non-positive mass norm.")
        modes[:, index] /= np.sqrt(norm)
        vector = modes[:, index]
        residual = (root**2 * matrix_m + root * omega * matrix_g + matrix_k) @ vector
        denominator = (
            np.linalg.norm(matrix_k @ vector)
            + abs(root * omega) * np.linalg.norm(matrix_g @ vector)
            + abs(root) ** 2 * np.linalg.norm(matrix_m @ vector)
        )
        residuals.append(float(np.linalg.norm(residual) / denominator))
    return SimpleNamespace(
        spin_speed_rad_s=float(omega),
        axis_global=(1.0, 0.0, 0.0),
        modes=modes,
        eigenvalues=roots,
        frequencies_hz=frequencies,
        qep_residuals=np.asarray(residuals),
        selected_mode_indices=tuple(range(len(frequencies))),
        dofs=SimpleNamespace(node_dofs={}),
    )


def _branch_signature(branches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "branch_id": branch["branch_id"],
            "parent_branch_ids": branch["parent_branch_ids"],
            "child_branch_ids": branch["child_branch_ids"],
            "samples": [
                None
                if sample is None
                else {
                    "spin_speed_rad_s": sample["spin_speed_rad_s"],
                    "frequencies_hz": sample["frequencies_hz"],
                    "ambiguity_status": sample["ambiguity_status"],
                }
                for sample in branch["samples"]
            ],
        }
        for branch in sorted(branches, key=lambda item: item["branch_id"])
    ]


def run_gyro05() -> dict[str, Any]:
    wp06 = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    frozen = wp06["verification_cases"]["GYRO-05"]
    fixture = frozen["oracle"]["parameters"]
    mass = float(fixture["diametral_inertia_kg_m2"])
    diametral = mass
    polar = float(fixture["polar_inertia_kg_m2"])
    stiffness = float(fixture["rotational_stiffness_Nm_per_rad"])
    speeds = [float(item) for item in frozen["oracle"]["speeds_rad_s_strictly_increasing"]]
    omega0 = float(np.sqrt(stiffness / diametral))
    snapshots = [
        _qep_snapshot(speed, mass=mass, diametral=diametral, polar=polar, stiffness=stiffness)
        for speed in speeds
    ]
    frequency_rows: list[dict[str, Any]] = []
    all_residuals = []
    for speed, snapshot in zip(speeds, snapshots):
        signed_s = speed * polar / diametral
        split_rad_s = np.sqrt(omega0**2 + (signed_s / 2.0) ** 2)
        expected = sorted((split_rad_s - abs(signed_s) / 2.0, split_rad_s + abs(signed_s) / 2.0))
        expected_hz = [float(value / (2.0 * np.pi)) for value in expected]
        observed_hz = [float(value) for value in snapshot.frequencies_hz]
        for position, (expected_value, observed_value) in enumerate(zip(expected_hz, observed_hz)):
            frequency_rows.append(
                {
                    "spin_speed_rad_s": speed,
                    "branch_frequency_rank": position,
                    **_metric(
                        "analytical_branch_frequency_hz",
                        expected_value,
                        observed_value,
                        float(frozen["oracle"]["frequency_error_relative_max"]),
                    ),
                }
            )
        all_residuals.extend(float(value) for value in snapshot.qep_residuals)

    branches, tracking = track_modal_sweep(snapshots, np.eye(2) * diametral)
    phased_permuted = []
    for snapshot in snapshots:
        permutation = np.arange(len(snapshot.selected_mode_indices))[::-1]
        phases = np.exp(1j * np.arange(1, len(permutation) + 1) * 0.731)
        phased_permuted.append(
            SimpleNamespace(
                **{
                    **snapshot.__dict__,
                    "modes": snapshot.modes[:, permutation] * phases[None, :],
                    "eigenvalues": snapshot.eigenvalues[permutation],
                    "frequencies_hz": snapshot.frequencies_hz[permutation],
                    "qep_residuals": snapshot.qep_residuals[permutation],
                    "selected_mode_indices": tuple(range(len(permutation))),
                }
            )
        )
    phased_branches, _ = track_modal_sweep(phased_permuted, np.eye(2) * diametral)

    zero = next(item for item in snapshots if item.spin_speed_rad_s == 0.0)
    zero_groups = len(zero.frequencies_hz) == 2 and abs(float(zero.frequencies_hz[0] - zero.frequencies_hz[1])) <= 1.0e-8 * max(float(zero.frequencies_hz[0]), 1.0)
    split_events = [item for item in tracking if item.get("event") == "CLUSTER_SPLIT"]
    ambiguity_modes = np.eye(2, dtype=np.complex128)
    angle = np.pi / 4.0
    ambiguity_rotation = np.asarray(
        [[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]], dtype=np.complex128
    )
    ambiguous_branches, ambiguity_records = track_modal_sweep(
        [
            SimpleNamespace(**{**zero.__dict__, "spin_speed_rad_s": 1.0, "frequencies_hz": np.asarray([10.0, 10.0]), "modes": ambiguity_modes}),
            SimpleNamespace(**{**zero.__dict__, "spin_speed_rad_s": 2.0, "frequencies_hz": np.asarray([10.0, 10.0]), "modes": ambiguity_rotation}),
        ],
        np.eye(2),
    )
    ambiguity_detected = bool(
        len(ambiguous_branches) == 1
        and ambiguous_branches[0]["samples"][1]["ambiguity_status"] == "DEGENERATE_CLUSTER"
        and any(item.get("individual_association_status") == "MULTIPLE_CANDIDATES" for item in ambiguity_records)
        and all(not item.get("individual_edges_committed", True) for item in ambiguity_records)
    )
    qep_threshold = 1.0e-10
    qep_metric = {
        "metric": "maximum_independent_qep_relative_residual",
        "expected_value": 0.0,
        "observed_value": max(all_residuals, default=float("inf")),
        "absolute_error": max(all_residuals, default=float("inf")),
        "relative_error": max(all_residuals, default=float("inf")),
        "threshold": qep_threshold,
        "status": "PASS" if max(all_residuals, default=float("inf")) <= qep_threshold else "FAIL",
    }
    invariant_metric = {
        "metric": "phase_and_eigenpair_ordering_invariance",
        "expected_value": True,
        "observed_value": _branch_signature(phased_branches) == _branch_signature(branches),
        "threshold": "exact branch/lineage/frequency/status signature equality",
        "status": "PASS" if _branch_signature(phased_branches) == _branch_signature(branches) else "FAIL",
    }
    degeneracy_metric = {
        "metric": "zero_speed_degenerate_cluster_identified",
        "expected_value": True,
        "observed_value": zero_groups
        and any(
            sample is not None
            and sample["spin_speed_rad_s"] == 0.0
            and sample["ambiguity_status"] == "DEGENERATE_CLUSTER"
            for branch in branches
            for sample in branch["samples"]
        ),
        "threshold": "two coincident frequencies grouped as one degenerate cluster",
        "status": "PASS"
        if zero_groups
        and any(
            sample is not None
            and sample["spin_speed_rad_s"] == 0.0
            and sample["ambiguity_status"] == "DEGENERATE_CLUSTER"
            for branch in branches
            for sample in branch["samples"]
        )
        else "FAIL",
    }
    split_metric = {
        "metric": "degenerate_cluster_split_lineage_count",
        "expected_value": 2,
        "observed_value": len(split_events),
        "threshold": "both child branches explicitly reference the parent cluster",
        "status": "PASS" if len(split_events) == 2 else "FAIL",
    }
    ambiguity_metric = {
        "metric": "controlled_ambiguity_detected_without_forced_continuity",
        "expected_value": True,
        "observed_value": ambiguity_detected,
        "threshold": "DEGENERATE_CLUSTER plus MULTIPLE_CANDIDATES; no individual edge",
        "status": "PASS" if ambiguity_detected else "FAIL",
    }
    metrics = [*frequency_rows, qep_metric, invariant_metric, degeneracy_metric, split_metric, ambiguity_metric]
    source_sha = _source_sha()
    identity = {
        "schema_version": 2,
        "case_contract_version": "0.2.11-wp06-gyro05-v1",
        "case_definition": {
            "fixture": fixture,
            "spin_speeds_rad_s": speeds,
            "oracle": frozen["oracle"]["formula"],
            "tracking_policy": TRACKING_POLICY,
            "controlled_ambiguity_fixture": frozen["controlled_ambiguity_fixture"],
        },
        "reference_identity": {"id": "QF0211-WP06-GYRO05-CLOSED-FORM-ORACLE", "role": "independent analytical frequency oracle"},
        "tolerance_policy": {
            "frequency_relative_error_max": frozen["oracle"]["frequency_error_relative_max"],
            "qep_relative_residual_max": qep_threshold,
            "complex_mac_minimum": 0.8,
            "normalized_frequency_distance_maximum": 0.25,
            "ambiguity_margin_minimum": 0.05,
        },
        "source_sha": source_sha,
        "software_versions": {
            "qf_solver": __version__,
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "platform": platform.platform(),
        },
        "implementation_sha256": {
            "scripts/run_wp06_verification.py": _sha256_file(Path(__file__).resolve()),
            "src/solveur/core/analyses/modal_tracking.py": _sha256_file(PROJECT_ROOT / "src/solveur/core/analyses/modal_tracking.py"),
            "qualification/0_2_11/wp06_campbell_contract.json": _sha256_file(CONTRACT_PATH),
            "qualification/0_2_11/wp05_gyroscopic_contract.json": _sha256_file(WP05_CONTRACT_PATH),
        },
    }
    execution_key = _sha256_bytes(_canonical_bytes(identity))
    return {
        "schema_version": 2,
        "record_schema": "qf.wp03.execution.v2",
        "case_id": "GYRO-05",
        "work_package": "WP06",
        "source_sha": source_sha,
        "execution_identity": identity,
        "execution_key": execution_key,
        "evidence_availability": "AVAILABLE_AND_REPRODUCIBLE",
        "numerical_status": "PASS" if all(item["status"] == "PASS" for item in metrics) else "FAIL",
        "maturity": "EXPERIMENTAL",
        "maturity_promotion": "NONE",
        "metrics": metrics,
        "frequency_comparisons": frequency_rows,
        "tracking": {
            "branches": branches,
            "diagnostics": tracking,
            "phase_order_invariance": invariant_metric,
            "zero_speed_degeneracy": degeneracy_metric,
            "cluster_split": split_metric,
            "controlled_ambiguity": ambiguity_metric,
        },
        "maximum_qep_residual": qep_metric["observed_value"],
        "independent_qep_backend": "scipy.linalg.eig on a locally constructed companion pencil; production G assembler and QEP solver not called",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def _beam_model(element_count: int) -> FiniteElementModel:
    radius = 0.05
    area = float(np.pi * radius**2)
    inertia = float(area**2 / (4.0 * np.pi))
    material = {
        "type": "beam_isotropic",
        "E": 210.0e9,
        "nu": 0.3,
        "A": area,
        "Iy": inertia,
        "Iz": inertia,
        "J": 2.0 * inertia,
        "density": 7800.0,
    }
    nodes = np.column_stack((np.linspace(0.0, 1.0, element_count + 1), np.zeros(element_count + 1), np.zeros(element_count + 1)))
    elements = [ElementDefinition("BEAM2", (index, index + 1), "shaft") for index in range(element_count)]
    analysis = AnalysisSettings.from_raw(
        {
            "type": "campbell",
            "method": "complex_mac_hungarian",
            "parameters": {
                "rotation": {
                    "axis_global": [1.0, 0.0, 0.0],
                    "frame_convention": "global_fixed_right_hand_rule",
                },
                "spin_speeds_rad_s": [0.0, 100.0, 250.0],
                "modes": 4,
                "qep_settings": {"contract": QEP_CONTRACT},
                "tracking_policy": TRACKING_POLICY,
            },
        }
    )
    return FiniteElementModel(
        nodes=nodes,
        elements=elements,
        materials={"shaft": material},
        fixed_dofs=[BoundaryCondition(0, DOF_ORDER)],
        concentrated_masses=[RotatingDisk(element_count, 1.0, 0.01, 0.02, (1.0, 0.0, 0.0))],
        analysis=analysis,
    )


def _tracked_branch_frequencies(result: Any, speed_index: int) -> dict[str, tuple[float, ...]]:
    """Return only frequencies with an explicit tracked/cluster identity at one speed."""

    accepted_statuses = {"CLEAR_MATCH", "DEGENERATE_CLUSTER"}
    tracked: dict[str, tuple[float, ...]] = {}
    for branch in result.branches:
        sample = branch["samples"][speed_index]
        if sample is None or sample["ambiguity_status"] not in accepted_statuses:
            continue
        tracked[str(branch["branch_id"])] = tuple(sorted(float(value) for value in sample["frequencies_hz"]))
    return tracked


def run_gyro06() -> tuple[dict[str, Any], Any]:
    wp06 = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    frozen = wp06["verification_cases"]["GYRO-06"]
    mesh_counts = [int(item) for item in frozen["fixture"]["mesh_element_counts"]]
    solver = CampbellSolver()
    results = []
    for count in mesh_counts:
        results.append(solver.solve(_beam_model(count)))

    residual_values = [
        float(value)
        for result in results
        for source in result.source_results
        for value in source.qep_residuals[list(source.selected_mode_indices)]
    ]
    mesh_comparisons: list[dict[str, Any]] = []
    previous, final = results[-2], results[-1]
    for speed_index, (source_previous, source_final) in enumerate(
        zip(previous.source_results, final.source_results)
    ):
        coarse_branches = _tracked_branch_frequencies(previous, speed_index)
        fine_branches = _tracked_branch_frequencies(final, speed_index)
        common_branch_ids = sorted(set(coarse_branches) & set(fine_branches))
        compared_modes = 0
        for branch_id in common_branch_ids:
            coarse_frequencies = coarse_branches[branch_id]
            fine_frequencies = fine_branches[branch_id]
            if len(coarse_frequencies) != len(fine_frequencies):
                mesh_comparisons.append(
                    {
                        "spin_speed_rad_s": source_final.spin_speed_rad_s,
                        "branch_id": branch_id,
                        "expected_value": "same tracked branch multiplicity",
                        "observed_value": [len(coarse_frequencies), len(fine_frequencies)],
                        "threshold": "identical multiplicity",
                        "status": "FAIL",
                    }
                )
                continue
            for mode_index, (observed_coarse, observed_fine) in enumerate(zip(coarse_frequencies, fine_frequencies)):
                compared_modes += 1
                delta = abs(observed_fine - observed_coarse) / max(abs(observed_fine), abs(observed_coarse), 1.0)
                mesh_comparisons.append(
                    {
                        "spin_speed_rad_s": source_final.spin_speed_rad_s,
                        "branch_id": branch_id,
                        "mode_position_in_branch": mode_index,
                        "coarse_mesh_elements": mesh_counts[-2],
                        "fine_mesh_elements": mesh_counts[-1],
                        "expected_value": 0.0,
                        "coarse_frequency_hz": observed_coarse,
                        "observed_value": delta,
                        "fine_frequency_hz": observed_fine,
                        "absolute_error": delta,
                        "relative_error": delta,
                        "threshold": float(frozen["metrics"]["final_adjacent_mesh_relative_frequency_delta_max"]),
                        "status": "PASS"
                        if delta <= float(frozen["metrics"]["final_adjacent_mesh_relative_frequency_delta_max"])
                        else "FAIL",
                    }
                )
        expected_modes = int(frozen["fixture"]["requested_positive_frequency_modes"])
        if compared_modes != expected_modes:
            mesh_comparisons.append(
                {
                    "spin_speed_rad_s": source_final.spin_speed_rad_s,
                    "metric": "tracked_branch_frequency_coverage",
                    "expected_value": expected_modes,
                    "observed_value": compared_modes,
                    "common_tracked_branch_ids": common_branch_ids,
                    "unmatched_or_ambiguous_32_element_branch_ids": sorted(set(fine_branches) - set(coarse_branches)),
                    "unmatched_or_ambiguous_16_element_branch_ids": sorted(set(coarse_branches) - set(fine_branches)),
                    "threshold": f"exactly {expected_modes} retained tracked frequencies at each speed",
                    "status": "FAIL",
                }
            )
    qep_threshold = float(frozen["metrics"]["qep_relative_residual_max"])
    residual_metric = {
        "metric": "maximum_qep_relative_residual_over_all_meshes_speeds_modes",
        "expected_value": 0.0,
        "observed_value": max(residual_values, default=float("inf")),
        "absolute_error": max(residual_values, default=float("inf")),
        "relative_error": max(residual_values, default=float("inf")),
        "threshold": qep_threshold,
        "status": "PASS" if max(residual_values, default=float("inf")) <= qep_threshold else "FAIL",
    }
    mesh_metric = {
        "metric": "maximum_16_to_32_element_tracked_branch_frequency_delta",
        "expected_value": 0.0,
        "observed_value": max((item["observed_value"] for item in mesh_comparisons), default=float("inf")),
        "absolute_error": max((item["observed_value"] for item in mesh_comparisons), default=float("inf")),
        "relative_error": max((item["observed_value"] for item in mesh_comparisons), default=float("inf")),
        "threshold": float(frozen["metrics"]["final_adjacent_mesh_relative_frequency_delta_max"]),
        "status": "PASS" if mesh_comparisons and all(item["status"] == "PASS" for item in mesh_comparisons) else "FAIL",
    }
    tracking_rows = [
        {
            "mesh_elements": element_count,
            "execution_key": result.execution_key,
            "tracking_diagnostics": result.tracking_diagnostics,
        }
        for element_count, result in zip(mesh_counts, results)
    ]
    all_statuses = [
        item["status"]
        for result in results
        for item in result.tracking_diagnostics
    ]
    no_silent_ambiguous_edges = all(
        item.get("status") not in {"MULTIPLE_CANDIDATES", "LOW_MAC", "FREQUENCY_JUMP", "POLARIZATION_CONFLICT"}
        or not item.get("individual_edges_committed", True)
        for result in results
        for item in result.tracking_diagnostics
    )
    ambiguity_metric = {
        "metric": "no_forced_continuity_for_reported_ambiguities",
        "expected_value": True,
        "observed_value": no_silent_ambiguous_edges,
        "threshold": "ambiguous/untracked edges remain absent from individual branch associations",
        "status": "PASS" if no_silent_ambiguous_edges else "FAIL",
        "observed_statuses": all_statuses,
    }
    metrics = [residual_metric, mesh_metric, ambiguity_metric]
    source_sha = _source_sha()
    fixture_spec = {
        "geometry": frozen["fixture"]["geometry"],
        "mesh_element_counts": mesh_counts,
        "speed_sweep_rad_s": frozen["fixture"]["spin_speeds_rad_s"],
        "material": {key: value for key, value in frozen["fixture"].items() if key not in {"geometry", "mesh_element_counts", "spin_speeds_rad_s", "requested_positive_frequency_modes"}},
    }
    fixture_bytes = _canonical_bytes(fixture_spec)
    input_file = {
        "logical_role": "generated_model_fixture_specification",
        "public_identifier": "qualification/0_2_11/wp06_campbell_contract.json#/verification_cases/GYRO-06/fixture",
        "sha256": _sha256_bytes(fixture_bytes),
        "size_bytes": len(fixture_bytes),
        "provenance": "GENERATED_FROM_FROZEN_CONTRACT",
        "availability_status": "AVAILABLE_AND_REPRODUCIBLE",
    }
    return (
        {
            "schema_version": 2,
            "record_schema": "qf.wp03.execution.v2",
            "case_id": "GYRO-06",
            "work_package": "WP06",
            "source_sha": source_sha,
            "evidence_availability": "AVAILABLE_AND_REPRODUCIBLE",
            "numerical_status": "PASS" if all(item["status"] == "PASS" for item in metrics) else "FAIL",
            "maturity": "EXPERIMENTAL",
            "maturity_promotion": "NONE",
            "interpretation": frozen["interpretation"],
            "input_files": [input_file],
            "mesh_element_counts": mesh_counts,
            "speed_sweep_rad_s": [float(value) for value in frozen["fixture"]["spin_speeds_rad_s"]],
            "mesh_level_execution_keys": [result.execution_key for result in results],
            "mesh_level_execution_identities": [result.execution_identity for result in results],
            "tracking_metrics": tracking_rows,
            "mesh_convergence_comparisons": mesh_comparisons,
            "metrics": metrics,
            "maximum_qep_relative_residual": residual_metric["observed_value"],
            "final_adjacent_mesh_relative_frequency_delta_max": mesh_metric["observed_value"],
            "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        },
        results[-1],
    )


def _write_record(path: Path, record: dict[str, Any]) -> None:
    record["record_sha256"] = _sha256_bytes(_canonical_bytes(record))
    path.write_text(json.dumps(record, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def _write_report(gyro05: dict[str, Any], gyro06: dict[str, Any]) -> None:
    metric_rows = []
    for record in (gyro05, gyro06):
        for metric in record["metrics"]:
            metric_rows.append(
                f"| {record['case_id']} | {metric['metric']} | {metric['observed_value']} | {metric['threshold']} | {metric['status']} |"
            )
    text = "\n".join(
        [
            "# WP06 — Campbell and modal tracking report",
            "",
            f"Source SHA: `{_source_sha()}`",
            "",
            f"Overall GYRO-05: **{gyro05['numerical_status']}**; GYRO-06: **{gyro06['numerical_status']}**.",
            "Maturity remains **EXPERIMENTAL**. GYRO-06 is internal mesh-convergence evidence, not independent physical validation.",
            "",
            "| Case | Metric | Observed | Frozen threshold | Status |",
            "| --- | --- | ---: | ---: | --- |",
            *metric_rows,
            "",
            "The contracts and complete metric/provenance rows are in `wp06_campbell_contract.json`, `gyro_05_campbell_analytical.json`, and `gyro_06_beam2_convergence.json`. The reproducible figure is `docs/assets/gyro06-campbell.png`.",
            "",
            "WP05 equations, QEP, `RotatingModalResult`, and maturity were not modified by this report generation.",
            "",
        ]
    )
    (PROJECT_ROOT / "qualification/0_2_11/wp06_campbell_report.md").write_text(text, encoding="utf-8")


def main() -> int:
    gyro05 = run_gyro05()
    gyro06, final_result = run_gyro06()
    figure = PROJECT_ROOT / "docs/assets/gyro06-campbell.png"
    save_campbell_plot(final_result, figure, show_one_x=True)
    _write_record(PROJECT_ROOT / "qualification/0_2_11/gyro_05_campbell_analytical.json", gyro05)
    _write_record(PROJECT_ROOT / "qualification/0_2_11/gyro_06_beam2_convergence.json", gyro06)
    _write_report(gyro05, gyro06)
    print(
        json.dumps(
            {
                "source_sha": _source_sha(),
                "gyro05": gyro05["numerical_status"],
                "gyro06": gyro06["numerical_status"],
                "gyro05_max_qep_residual": gyro05["maximum_qep_residual"],
                "gyro06_qep_residual": gyro06["maximum_qep_relative_residual"],
                "gyro06_final_mesh_delta": gyro06["final_adjacent_mesh_relative_frequency_delta_max"],
                "figure": figure.relative_to(PROJECT_ROOT).as_posix(),
            },
            indent=2,
        )
    )
    return 0 if gyro05["numerical_status"] == "PASS" and gyro06["numerical_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
