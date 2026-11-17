"""Bounded replay of archived NAFEMS 13H complex systems, without FEM assembly."""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import subprocess
import sys
import time
import warnings
from pathlib import Path
from decimal import Decimal, localcontext
from fractions import Fraction
from typing import Any

import matplotlib
import numpy as np
import scipy
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import MatrixRankWarning, spsolve

from solveur.core.assembly.assembler import GlobalAssembler
from solveur.core.errors import NumericalConvergenceError
from solveur.core.solvers.linear import (
    LinearSystemSolver,
    _sparse_matvec_roundoff_bound,
    relative_residual_ratio,
    stable_l2_norm,
)
from solveur.verification.mitc4_harmonic_nafems import (
    _center_node,
    build_nafems_13h_model,
)
from solveur.verification.external_correlation import load_abaqus_nafems_13h_reference
from research.j17.exact_residual import evaluate_exact_residual, exact_fraction

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "research" / "j18" / "contracts" / "resonance_replay_001.json"
INPUT_ROOT = ROOT / "research" / "j17" / "inputs" / "guard_resolution_001"
OUTPUT = ROOT / "research" / "j18" / "results" / "resonance_replay_001"
FREQUENCY_FILES = (
    ("2.375818178440047", "guard_frequency_2p375818178.npz"),
    ("2.417", "guard_frequency_2p417000000.npz"),
    ("2.418", "guard_frequency_2p418000000.npz"),
)
TOLERANCE = 1.0e-7


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _exact_result_dict(result: Any) -> dict[str, Any]:
    return {
        "status": result.status,
        "reason": result.reason,
        "dimension": result.dimension,
        "nonzero_entries": result.nonzero_entries,
        "stored_entries": result.stored_entries,
        "residual_squared": exact_fraction(result.residual_squared)
        if result.residual_squared is not None
        else None,
        "reference_squared": exact_fraction(result.reference_squared)
        if result.reference_squared is not None
        else None,
        "relative_residual_squared": exact_fraction(result.relative_residual_squared)
        if result.relative_residual_squared is not None
        else None,
        "threshold_binary64": exact_fraction(result.threshold_binary64)
        if result.threshold_binary64 is not None
        else None,
        "residual_l2_display_only": result.residual_l2_display,
        "relative_residual_display_only": result.relative_residual_display,
    }


def _q(value: float | np.floating) -> Fraction:
    return Fraction.from_float(float(value))


def _display_sqrt(value: Fraction) -> str:
    with localcontext() as context:
        context.prec = 40
        return str((Decimal(value.numerator) / Decimal(value.denominator)).sqrt())


def _exact_observed_residual_roundoff(
    matrix: csr_matrix,
    rhs: np.ndarray,
    solution: np.ndarray,
    product: np.ndarray,
) -> dict[str, Any]:
    """Compare the measured CSR product/subtraction error to its row bounds."""
    computed_residual = product - rhs
    row_bounds = _sparse_matvec_roundoff_bound(matrix, rhs, solution, product)
    exact_error_squared = Fraction(0)
    bound_squared = Fraction(0)
    pointwise_violations = 0
    for row in range(matrix.shape[0]):
        exact_product_real = Fraction(0)
        exact_product_imag = Fraction(0)
        start, stop = int(matrix.indptr[row]), int(matrix.indptr[row + 1])
        for position in range(start, stop):
            coefficient = complex(matrix.data[position])
            value = complex(solution[int(matrix.indices[position])])
            ar, ai = _q(coefficient.real), _q(coefficient.imag)
            xr, xi = _q(value.real), _q(value.imag)
            exact_product_real += ar * xr - ai * xi
            exact_product_imag += ar * xi + ai * xr
        exact_residual_real = exact_product_real - _q(rhs[row].real)
        exact_residual_imag = exact_product_imag - _q(rhs[row].imag)
        error_real = _q(computed_residual[row].real) - exact_residual_real
        error_imag = _q(computed_residual[row].imag) - exact_residual_imag
        error_squared = error_real * error_real + error_imag * error_imag
        exact_error_squared += error_squared
        bound = float(row_bounds[row])
        if not np.isfinite(bound) or bound < 0.0:
            return {
                "status": "INCONCLUSIVE",
                "reason": "a rowwise bound was non-finite or negative",
                "pointwise_violations": None,
            }
        bound_q = _q(bound)
        row_bound_squared = bound_q * bound_q
        bound_squared += row_bound_squared
        if error_squared > row_bound_squared:
            pointwise_violations += 1
    return {
        "status": "OBSERVED_ERROR_WITHIN_BOUND"
        if pointwise_violations == 0
        else "OBSERVED_ERROR_EXCEEDS_BOUND",
        "scope": "exact comparison of the binary64 CSR product and subtraction with exact A*x-b for this stored matrix/vector",
        "pointwise_violations": pointwise_violations,
        "exact_observed_error_l2_display_only": _display_sqrt(exact_error_squared),
        "row_bound_l2_display_only": _display_sqrt(bound_squared),
        "exact_error_squared": exact_fraction(exact_error_squared),
        "row_bound_squared_sum": exact_fraction(bound_squared),
        "covers_observed_residual_error": pointwise_violations == 0,
    }


def _center_reduced_index() -> tuple[int, int, int, int]:
    model, _ = build_nafems_13h_model(mesh_size=8)
    dofs = model.dof_manager()
    fixed = GlobalAssembler().fixed_indices(model, dofs)
    free = np.setdiff1d(np.arange(dofs.ndof, dtype=int), fixed)
    center_node = _center_node(np.asarray(model.nodes, dtype=float))
    center_global_dof = dofs.index(center_node, "UZ")
    positions = np.flatnonzero(free == center_global_dof)
    if positions.size != 1:
        raise RuntimeError("center UZ is not a unique free degree of freedom")
    return int(center_node), int(center_global_dof), int(positions[0]), int(free.size)


def run_archived_frequency_replay() -> dict[str, Any]:
    """Solve three frozen archived matrices and record guard/exact outcomes."""
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if contract.get("state") != "FROZEN_BEFORE_EXECUTION":
        raise RuntimeError("replay contract is not frozen")
    for relative, expected_hash in contract["inputs"]["sha256"].items():
        source = ROOT / relative
        if _sha256(source) != expected_hash:
            raise RuntimeError(f"input SHA-256 mismatch: {relative}")

    center_node, center_global_dof, center_reduced_dof, free_dof_count = _center_reduced_index()
    expected_mapping = contract["model"]
    if (
        center_node != expected_mapping["center_node"]
        or center_global_dof != expected_mapping["center_global_uz_dof"]
        or center_reduced_dof != expected_mapping["center_reduced_uz_dof"]
        or free_dof_count != expected_mapping["free_dof_count"]
    ):
        raise RuntimeError("reconstructed center UZ and reduced-DOF map differ from the frozen contract")
    reference = load_abaqus_nafems_13h_reference()
    reference_digest_path = ROOT / "qualification" / "external_reference_digests" / "abaqus_nafems_13h_harmonic.json"
    if _sha256(reference_digest_path) != contract["inputs"]["sha256"][
        "qualification/external_reference_digests/abaqus_nafems_13h_harmonic.json"
    ]:
        raise RuntimeError("published-reference digest SHA-256 mismatch")

    rows: list[dict[str, Any]] = []
    all_started = time.perf_counter()
    for frequency_text, archive_name in FREQUENCY_FILES:
        archive_path = INPUT_ROOT / archive_name
        load_started = time.perf_counter()
        with np.load(archive_path, allow_pickle=False) as archive:
            impedance = np.asarray(archive["impedance_real"], dtype=np.float64) + 1j * np.asarray(
                archive["impedance_imag"], dtype=np.float64
            )
            rhs = np.asarray(archive["rhs_real"], dtype=np.float64) + 1j * np.asarray(
                archive["rhs_imag"], dtype=np.float64
            )
            archived_solution = np.asarray(archive["x_unscaled_real"], dtype=np.float64) + 1j * np.asarray(
                archive["x_unscaled_imag"], dtype=np.float64
            )
        load_seconds = time.perf_counter() - load_started

        csr_started = time.perf_counter()
        matrix = csr_matrix(impedance, dtype=np.complex128)
        if matrix.shape != (175, 175) or matrix.nnz != 3607 or not np.array_equal(matrix.toarray(), impedance):
            raise RuntimeError("archived impedance did not preserve the frozen 175x175 CSR matrix")
        if rhs.shape != (175,) or archived_solution.shape != (175,):
            raise RuntimeError("archived RHS or comparison vector has an unexpected shape")
        if free_dof_count != matrix.shape[0]:
            raise RuntimeError("model free-DOF map does not match archived matrix dimension")
        csr_seconds = time.perf_counter() - csr_started

        solve_started = time.perf_counter()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", MatrixRankWarning)
            solution = np.asarray(spsolve(matrix.tocsc(), rhs), dtype=np.complex128)
        solve_seconds = time.perf_counter() - solve_started
        if not np.all(np.isfinite(solution)):
            raise RuntimeError("archived sparse system solve returned non-finite values")

        guard_started = time.perf_counter()
        guard_outcome = "GUARD_ACCEPTED"
        guard_diagnostics: dict[str, Any] = {}
        try:
            guard_residual, guard_relative = LinearSystemSolver._validated_residual_metrics(
                matrix,
                rhs,
                solution,
                "j18_archived_direct_frequency",
                {"residual_failure_tolerance": TOLERANCE},
            )
            guard_diagnostics = {
                "residual_norm": guard_residual,
                "relative_residual": guard_relative,
                "relative_residual_upper_bound": guard_relative,
                "residual_failure_tolerance": TOLERANCE,
            }
        except NumericalConvergenceError as exc:
            guard_outcome = "GUARD_REJECTED"
            guard_diagnostics = dict(exc.diagnostics or {})
            guard_diagnostics["message"] = str(exc)
        guard_seconds = time.perf_counter() - guard_started

        product = matrix @ solution
        observed_roundoff = _exact_observed_residual_roundoff(matrix, rhs, solution, product)
        exact_started = time.perf_counter()
        exact = evaluate_exact_residual(matrix, rhs, solution, tolerance=TOLERANCE)
        exact_seconds = time.perf_counter() - exact_started
        raw_residual = product - rhs
        raw_relative = relative_residual_ratio(
            stable_l2_norm(raw_residual),
            max(stable_l2_norm(rhs), stable_l2_norm(product)),
        )
        center_uz = complex(solution[center_reduced_dof])
        archived_scale = float(np.max(np.abs(archived_solution), initial=0.0))
        solution_delta_relative_inf = float(
            np.max(np.abs(solution - archived_solution), initial=0.0)
            / max(archived_scale, np.finfo(float).tiny)
        )
        rows.append(
            {
                "frequency_hz": float(frequency_text),
                "input_archive": archive_name,
                "input_sha256": _sha256(archive_path),
                "matrix_shape": list(matrix.shape),
                "csr_stored_entries": int(matrix.nnz),
                "center_node": center_node,
                "center_global_uz_dof": center_global_dof,
                "center_reduced_uz_dof": center_reduced_dof,
                "center_uz_real_mm": float(1000.0 * center_uz.real),
                "center_uz_imag_mm": float(1000.0 * center_uz.imag),
                "center_uz_amplitude_mm": float(1000.0 * abs(center_uz)),
                "center_uz_phase_degrees": float(np.degrees(np.angle(center_uz))),
                "phase_convention": "u(t)=Re(U*exp(i*omega*t))",
                "float64_relative_residual": raw_relative,
                "current_guard_outcome": guard_outcome,
                "current_guard_diagnostics": guard_diagnostics,
                "observed_residual_roundoff": observed_roundoff,
                "exact_represented_system": _exact_result_dict(exact),
                "relative_solution_difference_inf_vs_archived_unscaled": solution_delta_relative_inf,
                "matrix_rank_warnings": [str(item.message) for item in caught],
                "timing_seconds": {
                    "archive_load": load_seconds,
                    "dense_to_csr_and_integrity_check": csr_seconds,
                    "spsolve": solve_seconds,
                    "current_guard_recheck": guard_seconds,
                    "exact_rational_evaluation": exact_seconds,
                },
            }
        )

    if len(rows) != 3:
        raise RuntimeError("replay did not process all three contracted frequencies")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    result = {
        "schema": "qfsolver-j18-archived-harmonic-replay-v1",
        "contract_id": contract["contract_id"],
        "execution_source_commit": _git_head(),
        "classification": "BOUNDED_ARCHIVED_MATRIX_SOLVES_NO_FEM_ASSEMBLY",
        "environment": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "platform": platform.platform(),
        },
        "model_identity": {
            "name": "NAFEMS 13H MITC4 8x8 reduced harmonic systems",
            "free_dof_count": free_dof_count,
            "center_node": center_node,
            "center_global_uz_dof": center_global_dof,
            "center_reduced_uz_dof": center_reduced_dof,
            "matrix_source": "J16 archived complex impedances; no stiffness/mass/load assembly in J18",
        },
        "threshold_binary64": TOLERANCE,
        "frequency_count": len(rows),
        "duration_seconds": time.perf_counter() - all_started,
        "published_reference": {
            "reference_id": reference["reference_id"],
            "evidence_level": "published_external_peak_data_not_locally_executed",
            "nafems_peak": reference["nafems_reference"],
            "abaqus_s4r_peak": next(
                item for item in reference["abaqus_direct_results"] if item["element"] == "S4R"
            ),
            "phase_available": False,
            "pointwise_samples_available": False,
            "comparison_limit": "peak-only values are not pointwise references at the three replay frequencies",
        },
        "historical_status": {
            "j15_run": "PYTEST_FAILED; 152 historical points remain QF_GUARD_REJECTED",
            "j16_replayed_systems": "historical route statuses remain QF_GUARD_REJECTED",
            "j17_exact_archive_check": "15 exact checks passed; no route verdict was promoted",
        },
        "results": rows,
        "limitations": [
            "Only frozen J16 impedance and RHS arrays were used; this did not independently verify QF assembly.",
            "Abaqus was not executed locally; the published reference provides peak values, not phase or pointwise samples at all replay frequencies.",
            "An exact residual PASS concerns the exact mathematical system represented by stored binary CSR entries; it does not bound forward solution error or physical/model error.",
            "The current production guard and the exact sidecar are reported separately; historical guard outcomes are unchanged.",
        ],
    }
    (OUTPUT / "replay.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    with (OUTPUT / "replay.csv").open("w", newline="", encoding="utf-8") as stream:
        fields = (
            "frequency_hz",
            "center_uz_amplitude_mm",
            "center_uz_phase_degrees",
            "float64_relative_residual",
            "current_guard_outcome",
            "current_guard_relative_upper_bound",
            "exact_represented_status",
            "relative_solution_difference_inf_vs_archived_unscaled",
        )
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "frequency_hz": row["frequency_hz"],
                    "center_uz_amplitude_mm": row["center_uz_amplitude_mm"],
                    "center_uz_phase_degrees": row["center_uz_phase_degrees"],
                    "float64_relative_residual": row["float64_relative_residual"],
                    "current_guard_outcome": row["current_guard_outcome"],
                    "current_guard_relative_upper_bound": row["current_guard_diagnostics"].get(
                        "relative_residual_upper_bound", ""
                    ),
                    "exact_represented_status": row["exact_represented_system"]["status"],
                    "relative_solution_difference_inf_vs_archived_unscaled": row[
                        "relative_solution_difference_inf_vs_archived_unscaled"
                    ],
                }
            )
    _plot_replay(rows, reference, OUTPUT / "amplitude_phase.png")
    readme = [
        "# J18 — rejeu limité des systèmes harmoniques archivés",
        "",
        "Rejeu de trois systèmes complexes J16 8×8 dont les matrices/RHS archivés sont vérifiés par SHA-256.",
        "Aucun assemblage FEM, calcul local Abaqus ou changement de verdict historique n’a été effectué.",
        "",
        "Le graphique distingue l’amplitude et la phase calculées des statuts du garde. Les marqueurs NAFEMS/Abaqus sont des pics publiés, pas des références point par point aux trois fréquences.",
        "",
        "Le PASS éventuel du vérificateur exact porte sur le système linéaire mathématique défini par les valeurs binaires stockées. Il ne qualifie pas l’assemblage, l’erreur avant ou la physique.",
        "",
        "Voir replay.json pour les entrées, empreintes, statuts, diagnostics, références et durées par phase; replay.csv fournit le tableau synthétique.",
    ]
    (OUTPUT / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")
    manifest = {
        "schema": "qfsolver-j18-artifact-manifest-v1",
        "contract_id": contract["contract_id"],
        "execution_source_commit": result["execution_source_commit"],
        "files": {
            path.name: {"sha256": _sha256(path), "bytes": path.stat().st_size}
            for path in sorted(OUTPUT.iterdir())
            if path.name != "artifact_manifest.json"
        },
    }
    (OUTPUT / "artifact_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return result


def _plot_replay(rows: list[dict[str, Any]], reference: dict[str, Any], path: Path) -> None:
    frequencies = np.asarray([row["frequency_hz"] for row in rows], dtype=float)
    amplitudes = np.asarray([row["center_uz_amplitude_mm"] for row in rows], dtype=float)
    phases = np.asarray([row["center_uz_phase_degrees"] for row in rows], dtype=float)
    fig, (amplitude_axis, phase_axis) = plt.subplots(2, 1, figsize=(9.5, 7.2), sharex=True)
    labels = [
        f"{row['current_guard_outcome']} / exact {row['exact_represented_system']['status']}"
        for row in rows
    ]
    for index, row in enumerate(rows):
        amplitude_axis.scatter(frequencies[index], amplitudes[index], s=48, label=labels[index])
        phase_axis.scatter(frequencies[index], phases[index], s=48)
    amplitude_axis.scatter(
        [reference["nafems_reference"]["peak_frequency_hz"]],
        [reference["nafems_reference"]["peak_displacement_mm"]],
        marker="x",
        color="black",
        s=68,
        label="NAFEMS published peak",
    )
    s4r = next(item for item in reference["abaqus_direct_results"] if item["element"] == "S4R")
    amplitude_axis.scatter(
        [s4r["peak_frequency_hz"]],
        [s4r["peak_displacement_mm"]],
        marker="+",
        color="black",
        s=68,
        label="Abaqus S4R published peak",
    )
    amplitude_axis.set_ylabel("Amplitude UZ centre (mm)")
    phase_axis.set_ylabel("Phase UZ centre (deg)")
    phase_axis.set_xlabel("Frequency (Hz)")
    amplitude_axis.grid(True, alpha=0.3)
    phase_axis.grid(True, alpha=0.3)
    amplitude_axis.legend(fontsize=8, loc="best")
    fig.suptitle("NAFEMS 13H — three archived 8×8 complex systems re-solved in J18")
    fig.text(
        0.5,
        0.01,
        "Published markers are peak-only references. Guard outcomes and exact residuals do not certify the mechanical model.",
        ha="center",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.96))
    fig.savefig(path, dpi=160)
    plt.close(fig)

