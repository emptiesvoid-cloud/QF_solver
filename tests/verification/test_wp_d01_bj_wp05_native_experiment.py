"""Owner-gated native WP05 characterization; never a C4 qualification test.

This module is deliberately classified NATIVE_AUTH_REQUIRED by tests/conftest.py.
Collection imports only pytest and standard-library modules.  The FEM model,
assembly and numerical imports occur inside the test body, which ordinary
pytest policy always skips for this tier.
"""

from __future__ import annotations

import math
import os

import pytest


pytestmark = [
    pytest.mark.native_vv,
    pytest.mark.scientific_vv,
]

_MESHES = (
    pytest.param("M1", 8, 48, id="M1"),
    pytest.param("M2", 16, 96, id="M2"),
    pytest.param("M3", 32, 192, id="M3"),
)
_MODE_COUNTS = (2, 4)
_FREQUENCY_RATIOS = (0.0, 0.05, 0.10, 0.199, 0.20, 0.201)
_RAYLEIGH_ALPHA_PER_S = 0.2
_RAYLEIGH_BETA_S = 2.0e-5
_FORCE_N = 1000.0 + 0.0j


def _beam_model(elements: int, frequencies_hz: list[float], mode_count: int, *, correction: bool):
    """Recreate the frozen AS Timoshenko beam inputs without Docker helpers."""
    from solveur.core.model import FiniteElementModel

    length_m = 1.0
    radius_m = 0.01
    area_m2 = math.pi * radius_m**2
    inertia_m4 = math.pi * radius_m**4 / 4.0
    polar_inertia_m4 = 2.0 * inertia_m4
    nodes = [[length_m * index / elements, 0.0, 0.0] for index in range(elements + 1)]
    element_data = [
        {"type": "BEAM2", "nodes": [index, index + 1], "material": "beam"}
        for index in range(elements)
    ]
    analysis = {
        "type": "harmonic_response",
        "method": "modal_superposition",
        "frequencies_hz": list(frequencies_hz),
        "modal_mode_count": mode_count,
        "modal_extraction_method": "eigsh",
        "modal_dense_limit": 16,
        "rayleigh_alpha": _RAYLEIGH_ALPHA_PER_S,
        "rayleigh_beta": _RAYLEIGH_BETA_S,
        "reduced_damping_projection": "rayleigh_structured",
        "residual_flexibility": {
            "schema": "qf-harmonic-residual-flexibility-config/v1",
            "enabled": correction,
            "method": "mode_acceleration",
        },
    }
    return FiniteElementModel.from_raw(
        nodes=nodes,
        elements=element_data,
        materials={
            "beam": {
                "type": "beam_isotropic",
                "E": 210.0e9,
                "nu": 0.3,
                "G": 80_769_230_769.23077,
                "A": area_m2,
                "Iy": inertia_m4,
                "Iz": inertia_m4,
                "J": polar_inertia_m4,
                "density": 7850.0,
                "kappa_y": 5.0 / 6.0,
                "kappa_z": 5.0 / 6.0,
                "reference_vector": [0.0, 1.0, 0.0],
            }
        },
        fixed_dofs=[{"node": 0, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]}],
        analysis=analysis,
        units={"system": "SI", "length": "m", "force": "N", "mass": "kg", "time": "s"},
    )


def _channel_map(elements: int, frequencies_hz: list[float]):
    from solveur.core.analyses.excitation_channels import (
        ComplexPhasor,
        ExcitationChannel,
        ExcitationChannelSet,
        HarmonicAmplitude,
        SpatialDofWeight,
    )

    return {
        frequency: ExcitationChannelSet(
            (
                ExcitationChannel(
                    channel_id="tip-transverse-force",
                    spatial_distribution=(SpatialDofWeight(node=elements, dof="UY", value=1.0),),
                    spatial_units="dimensionless",
                    amplitude_units="N",
                    result_units="N",
                    frame_convention="GLOBAL",
                    sign_convention="POSITIVE_GLOBAL",
                    constant_amplitude=None,
                    harmonic=HarmonicAmplitude(frequency, ComplexPhasor(_FORCE_N.real, _FORCE_N.imag)),
                    provenance=(("experiment", "WP-D01-BJ"),),
                ),
            )
        )
        for frequency in frequencies_hz
    }


@pytest.mark.parametrize(("mesh_id", "elements", "expected_free_dofs"), _MESHES)
def test_wp05_native_modal_and_residual_flexibility_characterization(
    mesh_id: str,
    elements: int,
    expected_free_dofs: int,
    record_property: pytest.FixtureRequest,
) -> None:
    """Record same-operator direct/modal comparisons; metrics are exploratory."""
    import importlib.metadata
    import json
    from collections.abc import Mapping

    import numpy as np
    from scipy.sparse import issparse
    from scipy.sparse.linalg import spsolve

    from experiments.wp_d01_cg_damping_evidence import (
        projected_damping_evidence,
        source_operator_evidence,
    )
    from experiments.wp_d01_bj_experiment_metrics import correction_error_ratio
    from solveur.core.analyses.modal_basis import ModalBasis
    from solveur.core.analyses.modal_basis_numerics import SYMMETRY_TOL
    from solveur.core.analyses.prepared_dynamic_system import PreparedDynamicSystem
    from solveur.core.analyses.reduced_harmonic import ReducedHarmonicResponseSolver
    from solveur.core.analyses.residual_flexibility_results import ResidualFlexibilityHarmonicResult

    source_sha = os.environ.get("QF_WP_D01_BJ_SOURCE_SHA", "")
    if len(source_sha) != 40 or any(char not in "0123456789abcdef" for char in source_sha):
        pytest.fail("The exact frozen source commit must be supplied by the future authorized controller.")

    seed_model = _beam_model(elements, [0.0], 2, correction=True)
    prepared = PreparedDynamicSystem.prepare(seed_model, source_sha=source_sha)
    if prepared.reduced_size != expected_free_dofs:
        pytest.fail(f"{mesh_id}: expected {expected_free_dofs} free DOFs, got {prepared.reduced_size}.")
    if prepared.has_reduction_condensation or len(prepared.free_dof_indices) != expected_free_dofs:
        pytest.fail(f"{mesh_id}: frozen cantilever unexpectedly requires dynamic DOF condensation.")

    reference_basis = ModalBasis.from_prepared(
        prepared,
        mode_count=2,
        method="eigsh",
        dense_limit=16,
        include_first_omitted_evidence=True,
        capture_c4_spectral_evidence=False,
    )
    omitted = reference_basis.first_omitted_eigenpair
    if not isinstance(omitted, dict) or not math.isfinite(float(omitted.get("omega_rad_s", math.nan))):
        pytest.fail(f"{mesh_id}: the baseline two-mode basis lacks a valid first-omitted frequency.")
    baseline_cutoff_rad_s = float(omitted["omega_rad_s"])
    frequencies_hz = [ratio * baseline_cutoff_rad_s / (2.0 * math.pi) for ratio in _FREQUENCY_RATIOS]
    channels = _channel_map(elements, frequencies_hz)

    dofs = seed_model.dof_manager()
    full_force = np.zeros(dofs.ndof, dtype=np.complex128)
    full_force[dofs.index(elements, "UY")] = _FORCE_N
    reduced_force = np.asarray(prepared.reduce_load(full_force), dtype=np.complex128)
    stiffness = prepared.stiffness
    mass = prepared.mass
    if not issparse(stiffness) or not issparse(mass):
        pytest.fail(f"{mesh_id}: prepared FEM operators are not sparse.")
    damping = (_RAYLEIGH_ALPHA_PER_S * mass + _RAYLEIGH_BETA_S * stiffness).tocsr()
    free_indices = np.asarray(prepared.free_dof_indices, dtype=int)
    observation_index = int(np.flatnonzero(free_indices == dofs.index(elements, "UY"))[0])

    direct: list[np.ndarray] = []
    direct_residuals: list[float] = []
    direct_energy: list[dict[str, float | None]] = []
    for frequency_hz in frequencies_hz:
        omega = 2.0 * math.pi * frequency_hz
        impedance = (stiffness.astype(np.complex128) - omega**2 * mass + 1j * omega * damping).tocsr()
        response = np.asarray(spsolve(impedance, reduced_force), dtype=np.complex128)
        if response.shape != (expected_free_dofs,) or not np.all(np.isfinite(response)):
            pytest.fail(f"{mesh_id}: direct same-operator reference is singular or non-finite at {frequency_hz} Hz.")
        residual = np.asarray(impedance @ response - reduced_force)
        residual_denominator = float(np.linalg.norm(impedance.data)) * float(np.linalg.norm(response)) + float(
            np.linalg.norm(reduced_force)
        )
        direct_residuals.append(float(np.linalg.norm(residual) / max(residual_denominator, np.finfo(float).tiny)))
        velocity = 1j * omega * response
        input_power = 0.5 * float(np.real(np.vdot(reduced_force, velocity)))
        dissipated_power = 0.5 * float(np.real(np.vdot(velocity, damping @ velocity)))
        direct_energy.append(
            {
                "average_input_power_W": input_power,
                "average_rayleigh_dissipation_W": dissipated_power,
                "absolute_balance_gap_W": abs(input_power - dissipated_power) if omega > 0.0 else None,
            }
        )
        direct.append(response)

    record_property(
        "wp_d01_cg_source_operands_json",
        source_operator_evidence(
            mesh_id=mesh_id,
            elements=elements,
            free_dofs=expected_free_dofs,
            source_sha=source_sha,
            operator_identity=prepared.operator_identity,
            alpha_per_s=_RAYLEIGH_ALPHA_PER_S,
            beta_s=_RAYLEIGH_BETA_S,
            mass=mass,
            stiffness=stiffness,
            damping=damping,
            frequencies_hz=frequencies_hz,
            reduced_force=reduced_force,
            direct_responses=direct,
            direct_relative_residuals=direct_residuals,
        ),
    )

    mode_results: dict[str, list[dict[str, object]]] = {"uncorrected": [], "corrected": []}
    solver = ReducedHarmonicResponseSolver()
    for mode_count in _MODE_COUNTS:
        basis = ModalBasis.from_prepared(
            prepared,
            mode_count=mode_count,
            method="eigsh",
            dense_limit=16,
            include_first_omitted_evidence=True,
            capture_c4_spectral_evidence=False,
        )
        omitted_for_count = basis.first_omitted_eigenpair
        if not isinstance(omitted_for_count, dict):
            pytest.fail(f"{mesh_id}: {mode_count}-mode basis lacks first-omitted evidence.")
        record_property(
            f"wp_d01_cg_projected_damping_m{mode_count}_json",
            projected_damping_evidence(
                mesh_id=mesh_id,
                mode_count=mode_count,
                source_sha=source_sha,
                basis_identity=basis.basis_identity,
                operator_identity=basis.operator_identity,
                basis_diagnostics=basis.diagnostics,
                modal_clusters_zero_based=basis.clusters_zero_based,
                modes=basis.modes,
                eigenvalues_rad2_s2=basis.eigenvalues,
                mass=mass,
                damping=damping,
                projected_mass=basis.projected_mass,
                projected_stiffness=basis.projected_stiffness,
                alpha_per_s=_RAYLEIGH_ALPHA_PER_S,
                beta_s=_RAYLEIGH_BETA_S,
                symmetry_tolerance=SYMMETRY_TOL,
            ),
        )
        corrected_model = _beam_model(elements, frequencies_hz, mode_count, correction=True)
        uncorrected_model = _beam_model(elements, frequencies_hz, mode_count, correction=False)
        corrected = solver.solve(
            corrected_model,
            source_sha=source_sha,
            prepared=prepared,
            basis=basis,
            excitation_channels=channels,
        )
        uncorrected = solver.solve(
            uncorrected_model,
            source_sha=source_sha,
            prepared=prepared,
            basis=basis,
            excitation_channels=channels,
        )
        if not isinstance(corrected, ResidualFlexibilityHarmonicResult):
            pytest.fail(f"{mesh_id}: corrected WP05 path did not return typed D01 response evidence.")

        corrected_rows = corrected.frequency_results
        uncorrected_rows = uncorrected.responses
        if len(corrected_rows) != len(frequencies_hz) or len(uncorrected_rows) != len(frequencies_hz):
            pytest.fail(f"{mesh_id}: WP05 response frequency count differs from the frozen grid.")
        for index, (frequency_hz, reference, c_row, u_full) in enumerate(
            zip(frequencies_hz, direct, corrected_rows, uncorrected_rows, strict=True)
        ):
            direct_tip = complex(reference[observation_index])
            uncorrected_free = np.asarray(u_full, dtype=np.complex128)[free_indices]
            corrected_free = np.asarray(c_row.corrected, dtype=np.complex128)[free_indices]
            uncorrected_tip = complex(uncorrected_free[observation_index])
            corrected_tip = complex(corrected_free[observation_index])
            scale = max(float(np.linalg.norm(reference)), np.finfo(float).tiny)
            uncorrected_error = float(np.linalg.norm(uncorrected_free - reference) / scale)
            corrected_error = float(np.linalg.norm(corrected_free - reference) / scale)
            error_ratio, error_ratio_status = correction_error_ratio(corrected_error, uncorrected_error)
            omega = 2.0 * math.pi * frequency_hz
            impedance = (stiffness.astype(np.complex128) - omega**2 * mass + 1j * omega * damping).tocsr()
            u_residual = np.asarray(impedance @ uncorrected_free - reduced_force)
            c_residual = np.asarray(impedance @ corrected_free - reduced_force)
            denominator_u = float(np.linalg.norm(impedance.data)) * float(np.linalg.norm(uncorrected_free)) + float(
                np.linalg.norm(reduced_force)
            )
            denominator_c = float(np.linalg.norm(impedance.data)) * float(np.linalg.norm(corrected_free)) + float(
                np.linalg.norm(reduced_force)
            )
            reference_magnitude = abs(direct_tip)
            mode_results["uncorrected"].append(
                {
                    "frequency_hz": frequency_hz,
                    "mode_count": mode_count,
                    "tip_uy_m": {"real": uncorrected_tip.real, "imag": uncorrected_tip.imag},
                    "relative_full_free_displacement_error": uncorrected_error,
                    "relative_tip_amplitude_error": (
                        abs(abs(uncorrected_tip) - reference_magnitude) / reference_magnitude
                        if reference_magnitude > 0.0
                        else None
                    ),
                    "tip_phase_error_rad": (
                        float(np.angle(uncorrected_tip / direct_tip)) if reference_magnitude > 0.0 else None
                    ),
                    "normalized_free_equilibrium_residual": float(
                        np.linalg.norm(u_residual) / max(denominator_u, np.finfo(float).tiny)
                    ),
                    "direct_reference_residual": direct_residuals[index],
                    "energy": direct_energy[index],
                    "wp05_diagnostic": corrected.wp05_result.solver["frequency_records"][index],
                }
            )
            mode_results["corrected"].append(
                {
                    "frequency_hz": frequency_hz,
                    "mode_count": mode_count,
                    "tip_uy_m": {"real": corrected_tip.real, "imag": corrected_tip.imag},
                    "relative_full_free_displacement_error": corrected_error,
                    "relative_tip_amplitude_error": (
                        abs(abs(corrected_tip) - reference_magnitude) / reference_magnitude
                        if reference_magnitude > 0.0
                        else None
                    ),
                    "tip_phase_error_rad": (
                        float(np.angle(corrected_tip / direct_tip)) if reference_magnitude > 0.0 else None
                    ),
                    "normalized_free_equilibrium_residual": float(
                        np.linalg.norm(c_residual) / max(denominator_c, np.finfo(float).tiny)
                    ),
                    "direct_reference_residual": direct_residuals[index],
                    "correction_error_ratio": error_ratio,
                    "correction_error_ratio_status": error_ratio_status,
                    "correction_degraded_error": corrected_error > uncorrected_error,
                    "energy": direct_energy[index],
                    "wp_d01_diagnostics": dict(c_row.diagnostics),
                }
            )

    for treatment, rows in mode_results.items():
        previous_error_by_mode: dict[int, float] = {}
        for row in rows:
            mode_count = int(row["mode_count"])
            error = float(row["relative_full_free_displacement_error"])
            previous = previous_error_by_mode.get(mode_count)
            row["successive_frequency_error_delta"] = None if previous is None else error - previous
            previous_error_by_mode[mode_count] = error
        error_by_frequency_and_mode = {
            (int(row["mode_count"]), float(row["frequency_hz"])): float(
                row["relative_full_free_displacement_error"]
            )
            for row in rows
        }
        for row in rows:
            count = int(row["mode_count"])
            frequency = float(row["frequency_hz"])
            if count != 2:
                row["error_delta_vs_2_modes_same_frequency"] = (
                    float(row["relative_full_free_displacement_error"])
                    - error_by_frequency_and_mode[(2, frequency)]
                )
            else:
                row["error_delta_vs_2_modes_same_frequency"] = 0.0

    def json_safe(value):
        if isinstance(value, np.ndarray):
            if np.iscomplexobj(value):
                return {"real": value.real.tolist(), "imag": value.imag.tolist()}
            return value.tolist()
        if isinstance(value, np.generic):
            return value.item()
        if isinstance(value, complex):
            return {"real": value.real, "imag": value.imag}
        if isinstance(value, Mapping):
            return {str(key): json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [json_safe(item) for item in value]
        return value

    payload = {
        "experiment": "WP-D01-BJ",
        "mesh": {"id": mesh_id, "elements": elements, "free_dofs": expected_free_dofs},
        "source_sha": source_sha,
        "operator_identity": prepared.operator_identity,
        "excitation_identity": prepared.excitation_identity,
        "baseline_modal_cutoff_rad_s": baseline_cutoff_rad_s,
        "frequency_ratios_to_baseline_2_mode_omitted_frequency": list(_FREQUENCY_RATIOS),
        "frequencies_hz": frequencies_hz,
        "retained_mode_counts": list(_MODE_COUNTS),
        "c4_official_status": "NOT_EVALUATED_BY_DESIGN",
        "c4_complete_spectrum_captured": False,
        "qualification": "NOT_CERTIFIED",
        "pre_solver_diagnostic_properties": [
            "wp_d01_cg_source_operands_json",
            "wp_d01_cg_projected_damping_m2_json",
            "wp_d01_cg_projected_damping_m4_json",
        ],
        "direct_reference_scope": "same assembled constrained FEM K/M/C; internal numerical control, not independent FEM oracle",
        "responses": mode_results,
        "runtime": {
            "python": __import__("platform").python_version(),
            "numpy": np.__version__,
            "scipy": importlib.metadata.version("scipy"),
            "reduced_harmonic_maturity": "EXPERIMENTAL",
        },
    }
    record_property(
        "wp_d01_bj_experimental_results_json",
        json.dumps(json_safe(payload), sort_keys=True, separators=(",", ":"), allow_nan=False),
    )
    assert all(math.isfinite(float(row["relative_full_free_displacement_error"])) for group in mode_results.values() for row in group)
