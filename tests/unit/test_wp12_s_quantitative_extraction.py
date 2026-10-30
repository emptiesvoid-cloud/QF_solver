"""Fixed, instrumented WP12-S cases; prepared only, not executed in this revision."""

from __future__ import annotations

import csv
import importlib.util
import json
import math
from fractions import Fraction
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np
import pytest
from scipy.linalg import eigh
from scipy.sparse import csr_matrix

from solveur.core.analyses.modal_basis_numerics import (
    is_exactly_sparse_symmetric,
    project_exact_symmetric_bilinear,
    sparse_symmetry_metrics,
)
from solveur.core.assembler import GlobalAssembler
from solveur.core.router import AnalysisRouter


_RESULT_PREFIX = "QF_VV_NUMERIC_RESULT="


def _emit(case_id: str, **values: Any) -> None:
    payload = {"schema": "qf-wp12-s-observables-v1", "case_id": case_id, "values": values}
    print(_RESULT_PREFIX + json.dumps(payload, allow_nan=False, sort_keys=True, separators=(",", ":")))


def _load_test_module(module_name: str, filename: str) -> ModuleType:
    path = Path(__file__).resolve().with_name(filename)
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load pinned test helper module: {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_wp12_s_alg_proj_001() -> None:
    stiffness = csr_matrix(
        np.asarray(
            [
                [8.0, -1.0, 0.0, 0.5],
                [-1.0, 6.0, 2.0, 0.0],
                [0.0, 2.0, 5.0, -0.25],
                [0.5, 0.0, -0.25, 4.0],
            ]
        )
    )
    modes = np.asarray(
        [[0.5, 0.25], [-0.25, 0.5], [0.75, -0.5], [0.125, 0.375]],
        dtype=np.float64,
    )
    projected = project_exact_symmetric_bilinear(stiffness, modes)
    dense_bilinear = modes.T @ (stiffness @ modes)
    absolute_difference = np.abs(projected - dense_bilinear)
    reference_norm = float(np.linalg.norm(dense_bilinear, ord="fro"))
    relative_frobenius_error = float(np.linalg.norm(projected - dense_bilinear, ord="fro") / reference_norm)
    symmetry_defect = float(np.max(np.abs(projected - projected.T), initial=0.0))

    _emit(
        "ALG-PROJ-QUANT-001",
        projected_structured=projected.tolist(),
        projected_dense=dense_bilinear.tolist(),
        max_absolute_difference=float(np.max(absolute_difference, initial=0.0)),
        relative_frobenius_error=relative_frobenius_error,
        relative_error_normalization="frobenius_difference_over_frobenius_dense_reference",
        dense_reference_frobenius_norm=reference_norm,
        projected_max_symmetry_defect=symmetry_defect,
        existing_rtol=2.0e-16,
        existing_atol=2.0e-16,
        units="NOT_APPLICABLE_ALGEBRAIC_SYNTHETIC_OPERATORS",
    )
    assert is_exactly_sparse_symmetric(stiffness)
    assert sparse_symmetry_metrics(stiffness) == (0.0, True)
    np.testing.assert_array_equal(projected, projected.T)
    np.testing.assert_allclose(projected, dense_bilinear, rtol=2.0e-16, atol=2.0e-16)
    np.testing.assert_array_equal(stiffness.toarray(), stiffness.toarray().T)


def test_wp12_s_modal_discrete_001() -> None:
    test_module = _load_test_module("wp12_s_discrete_test_source", "test_discrete_entities.py")
    model = test_module._spring_mass_model({"type": "modal", "method": "eigh", "parameters": {"modes": 1}})
    result = AnalysisRouter().solve(model)
    dofs = model.dof_manager()
    stiffness = GlobalAssembler().assemble_stiffness(model, dofs)
    mass = GlobalAssembler().assemble_mass(model, dofs)
    ux = dofs.index(0, "UX")
    k_effective = float(stiffness[ux, ux])
    m_effective = float(mass[ux, ux])
    omega_reference = math.sqrt(1000.0 / 10.0)
    frequency_reference = omega_reference / (2.0 * math.pi)
    frequency_computed = float(result.frequencies_hz[0])
    relative_error = abs(frequency_computed - frequency_reference) / abs(frequency_reference)
    relative_residual = float(result.solver["max_relative_residual"])

    _emit(
        "MODAL-DISCRETE-QUANT-001",
        k_effective=k_effective,
        m_effective=m_effective,
        omega_reference_rad_per_consistent_time_unit=omega_reference,
        frequency_reference_cycles_per_consistent_time_unit=frequency_reference,
        frequency_computed_cycles_per_consistent_time_unit=frequency_computed,
        relative_frequency_error=relative_error,
        relative_modal_residual=relative_residual,
        existing_frequency_relative_tolerance=1.0e-12,
        existing_residual_limit=1.0e-12,
        units="UNDECLARED_IN_SOURCE; INPUTS_ONLY_INTERNALLY_CONSISTENT",
    )
    assert frequency_computed == pytest.approx(frequency_reference, rel=1.0e-12)
    assert relative_residual < 1.0e-12


def test_wp12_s_modal_2dof_001() -> None:
    test_module = _load_test_module("wp12_s_modal_basis_test_source", "test_modal_basis_damping.py")
    mass = np.asarray([[2.0, 0.25], [0.25, 1.5]])
    stiffness = np.asarray([[20.0, -2.0], [-2.0, 8.0]])
    expected_values = eigh(stiffness, mass, eigvals_only=True)
    basis = test_module._matrix_basis(stiffness, mass, 2)
    eigenvalues = np.asarray(basis.eigenvalues)
    projected_mass = np.asarray(basis.projected_mass)
    projected_stiffness = np.asarray(basis.projected_stiffness)
    mass_orthogonality = basis.modes.T @ mass @ basis.modes
    reconstructed_stiffness = mass @ basis.modes @ projected_stiffness @ basis.modes.T @ mass
    residuals = []
    for index, eigenvalue in enumerate(eigenvalues):
        mode = basis.modes[:, index]
        k_mode = stiffness @ mode
        m_mode = mass @ mode
        numerator = float(np.linalg.norm(k_mode - eigenvalue * m_mode))
        denominator = float(np.linalg.norm(k_mode) + abs(eigenvalue) * np.linalg.norm(m_mode))
        residuals.append(numerator / denominator)

    _emit(
        "MODAL-2DOF-QUANT-001",
        mass=mass.tolist(),
        stiffness=stiffness.tolist(),
        eigenvalues=eigenvalues.tolist(),
        eigenvalue_reference_scipy_same_backend=expected_values.tolist(),
        frequencies_hz=(np.sqrt(eigenvalues) / (2.0 * math.pi)).tolist(),
        projected_mass=projected_mass.tolist(),
        projected_stiffness=projected_stiffness.tolist(),
        mass_orthogonality_matrix=mass_orthogonality.tolist(),
        mass_orthogonality_frobenius_error=float(np.linalg.norm(mass_orthogonality - np.eye(2), ord="fro")),
        modal_relative_residuals=residuals,
        reconstructed_stiffness_frobenius_error=float(np.linalg.norm(reconstructed_stiffness - stiffness, ord="fro")),
        oracle_classification="SAME_SCIPY_GENERALIZED_EIGENSOLVER_BACKEND",
        existing_eigenvalue_rtol=1.0e-12,
        existing_eigenvalue_atol=1.0e-12,
        existing_projected_operator_rtol=1.0e-11,
        existing_projected_operator_atol=1.0e-11,
        maturity=basis.maturity,
    )
    np.testing.assert_allclose(eigenvalues, expected_values, rtol=1.0e-12, atol=1.0e-12)
    np.testing.assert_allclose(projected_mass, np.eye(2), rtol=0.0, atol=1.0e-12)
    np.testing.assert_allclose(projected_stiffness, np.diag(expected_values), rtol=1.0e-11, atol=1.0e-11)
    np.testing.assert_allclose(mass_orthogonality, np.eye(2), atol=1.0e-12)
    np.testing.assert_allclose(reconstructed_stiffness, stiffness, rtol=1.0e-11, atol=1.0e-11)


def test_wp12_s_dyn_sdof_001() -> None:
    test_module = _load_test_module("wp12_s_modal_newmark_test_source", "test_modal_newmark.py")
    amplitude = 2.0e-3
    model = test_module._model(
        steps=80,
        dt=0.00005,
        extra_parameters={
            "initial_displacements": [{"node": 1, "dof": "UX", "value": amplitude}],
            "initial_velocities": [{"node": 1, "dof": "UX", "value": 0.0}],
            "store_modal_history": True,
            "record_time_history": True,
            "history_probes": [{"node": 1, "dof": "UX", "label": "tip_ux"}],
        },
    )
    prepared, basis = test_module._prepared_basis(model)
    mass = float(prepared.mass[0, 0])
    stiffness = float(prepared.stiffness[0, 0])
    omega = math.sqrt(stiffness / mass)
    result = test_module._run(model, prepared=prepared, basis=basis)
    times = np.asarray([float(row["time_s"]) for row in result.time_history])
    computed = np.asarray([float(row["probes"]["tip_ux"]["displacement"]) for row in result.time_history])
    exact = amplitude * np.cos(omega * times)
    difference = computed - exact
    rms_absolute_error = float(np.sqrt(np.mean(np.square(difference))))
    rms_reference = float(np.sqrt(np.mean(np.square(exact))))
    max_absolute_error = float(np.max(np.abs(difference), initial=0.0))
    relative_energy_drifts = [float(row["relative_energy_drift"]) for row in result.time_history]

    _emit(
        "DYN-SDOF-QUANT-001",
        mass_effective=mass,
        stiffness_effective=stiffness,
        omega_from_prepared_operators_rad_s=omega,
        amplitude_initial=amplitude,
        initial_velocity=0.0,
        dt_s=0.00005,
        steps=80,
        beta=0.25,
        gamma=0.5,
        times_s=times.tolist(),
        displacement_computed_m_or_consistent_length=computed.tolist(),
        displacement_analytic_m_or_consistent_length=exact.tolist(),
        max_absolute_error=float(max_absolute_error),
        rms_absolute_error=rms_absolute_error,
        max_error_over_initial_amplitude=float(max_absolute_error / abs(amplitude)),
        rms_error_over_rms_analytic=float(rms_absolute_error / rms_reference),
        relative_energy_drift_max=float(max(abs(value) for value in relative_energy_drifts)),
        initial_projection_relative_mass_error=float(
            result.solver["integration"]["initial_projection"]["displacement_relative_mass_error"]
        ),
        reduced_equilibrium_max_relative_error=float(
            result.solver["reduced_equilibrium_diagnostics"]["maximum_relative_error"]
        ),
        existing_final_displacement_rtol=2.0e-4,
        existing_final_displacement_atol=1.0e-9,
        analytic_frequency_source="PREPARED_FE_K_AND_M; CONDITIONAL_TIME_INTEGRATION_ORACLE",
        convergence="NOT_ESTABLISHED_SINGLE_DT",
        maturity=result.maturity,
    )
    assert times.size == 81
    assert computed[-1] == pytest.approx(
        float(result.displacements[result.dofs.index(1, "UX")]), rel=1.0e-12, abs=1.0e-12
    )
    assert computed[-1] == pytest.approx(float(exact[-1]), rel=2.0e-4, abs=1.0e-9)
    assert result.solver["integration"]["initial_projection"]["displacement_relative_mass_error"] < 1.0e-12
    assert result.solver["reduced_equilibrium_diagnostics"]["maximum_relative_error"] < 1.0e-7
    assert result.maturity == "EXPERIMENTAL"


def test_wp12_s_modal_2dof_poly_001() -> None:
    test_module = _load_test_module(
        "wp12_s_modal_independent_oracle_test_source", "test_modal_two_dof_independent_oracle.py"
    )
    mass_exact = ((Fraction(2), Fraction(1, 4)), (Fraction(1, 4), Fraction(3, 2)))
    stiffness_exact = ((Fraction(20), Fraction(-2)), (Fraction(-2), Fraction(8)))
    a = mass_exact[0][0] * mass_exact[1][1] - mass_exact[0][1] * mass_exact[1][0]
    b = -(
        stiffness_exact[0][0] * mass_exact[1][1]
        + stiffness_exact[1][1] * mass_exact[0][0]
        - stiffness_exact[0][1] * mass_exact[1][0]
        - stiffness_exact[1][0] * mass_exact[0][1]
    )
    c = stiffness_exact[0][0] * stiffness_exact[1][1] - stiffness_exact[0][1] * stiffness_exact[1][0]
    discriminant = b * b - 4 * a * c
    root = math.sqrt(float(discriminant))
    expected = np.sort(
        np.asarray([float((-float(b) - root) / (2 * float(a))), float((-float(b) + root) / (2 * float(a)))])
    )
    mass = np.asarray([[2.0, 0.25], [0.25, 1.5]])
    stiffness = np.asarray([[20.0, -2.0], [-2.0, 8.0]])
    basis = test_module.ModalBasis._from_operators(
        csr_matrix(stiffness),
        csr_matrix(mass),
        operator_identity="wp04-independent-characteristic-polynomial-v1",
        dof_signature=(),
        requested_modes=2,
        method="dense",
        dense_limit=2,
    )
    eigenvalues = np.asarray(basis.eigenvalues)
    residuals = []
    for index, eigenvalue in enumerate(eigenvalues):
        mode = basis.modes[:, index]
        k_mode = stiffness @ mode
        m_mode = mass @ mode
        residuals.append(
            float(np.linalg.norm(k_mode - eigenvalue * m_mode))
            / float(np.linalg.norm(k_mode) + abs(eigenvalue) * np.linalg.norm(m_mode))
        )
    projected_mass = basis.modes.T @ mass @ basis.modes
    orthogonality_error = float(np.linalg.norm(projected_mass - np.eye(2), ord="fro"))

    _emit(
        "MODAL-2DOF-POLY-001",
        characteristic_coefficients_rational=[str(a), str(b), str(c)],
        discriminant_rational=str(discriminant),
        expected_eigenvalues_from_scalar_polynomial=expected.tolist(),
        computed_eigenvalues=eigenvalues.tolist(),
        relative_eigenvalue_errors=(np.abs(eigenvalues - expected) / np.abs(expected)).tolist(),
        frequencies_hz=(np.sqrt(eigenvalues) / (2.0 * math.pi)).tolist(),
        modal_relative_residuals=residuals,
        mass_orthogonality_frobenius_error=orthogonality_error,
        projected_mass=projected_mass.tolist(),
        eigenvalue_relative_tolerance=1.0e-10,
        residual_limit=1.0e-8,
        mass_orthogonality_limit=1.0e-8,
        independence_scope="SCALAR_EIGENVALUE_ORACLE_ONLY; PRODUCTION_MODAL_BASIS_REMAINS_UNDER_TEST",
        maturity=basis.maturity,
    )
    assert (a, b, c) == (Fraction(47, 16), Fraction(-47), Fraction(156))
    assert discriminant > 0
    np.testing.assert_allclose(eigenvalues, expected, rtol=1.0e-10, atol=0.0)
    np.testing.assert_allclose(projected_mass, np.eye(2), rtol=0.0, atol=1.0e-8)
    np.testing.assert_allclose(basis.projected_stiffness, np.diag(expected), rtol=1.0e-10, atol=0.0)
    assert max(residuals) <= 1.0e-8
    assert orthogonality_error <= 1.0e-8


def _beam2_quantitative(case_id: str, dof: str, inertia_name: str, rotation_dof: str, sign: float) -> None:
    test_module = _load_test_module("wp12_s_beam2_test_source", "test_beam2_element.py")
    force = 1000.0
    result = test_module.LinearStaticSolver().solve(test_module.beam_model(dof, force))
    inertia = float(getattr(test_module, inertia_name))
    kappa = 5.0 / 6.0
    expected_displacement = force * test_module.LENGTH**3 / (
        3.0 * test_module.E * inertia
    ) + force * test_module.LENGTH / (kappa * test_module.G * test_module.A)
    expected_rotation = sign * force * test_module.LENGTH**2 / (2.0 * test_module.E * inertia)
    displacement = float(result.displacements[result.dofs.index(1, dof)])
    rotation = float(result.displacements[result.dofs.index(1, rotation_dof)])
    displacement_abs_error = abs(displacement - expected_displacement)
    rotation_abs_error = abs(rotation - expected_rotation)

    _emit(
        case_id,
        plane=dof,
        rotation_dof=rotation_dof,
        rotation_sign=sign,
        force_n=force,
        length_m=float(test_module.LENGTH),
        young_pa=float(test_module.E),
        poisson=float(test_module.NU),
        area_m2=float(test_module.A),
        inertia_m4=inertia,
        shear_modulus_pa=float(test_module.G),
        shear_factor=kappa,
        displacement_computed_m=displacement,
        displacement_timoshenko_reference_m=float(expected_displacement),
        displacement_absolute_error_m=float(displacement_abs_error),
        displacement_relative_error=float(displacement_abs_error / abs(expected_displacement)),
        rotation_computed_rad=rotation,
        rotation_timoshenko_reference_rad=float(expected_rotation),
        rotation_absolute_error_rad=float(rotation_abs_error),
        rotation_relative_error=float(rotation_abs_error / abs(expected_rotation)),
        existing_rtol=1.0e-12,
        scope="ONE_STRAIGHT_UNIFORM_BEAM2_CANTILEVER; NOT_MESH_CONVERGENCE",
    )
    assert displacement == pytest.approx(expected_displacement, rel=1.0e-12)
    assert rotation == pytest.approx(expected_rotation, rel=1.0e-12)
    assert result.mesh_report.status == "PASS"


def test_wp12_s_stat_beam_uy_001() -> None:
    _beam2_quantitative("STAT-BEAM-UY-001", "UY", "IZ", "RZ", 1.0)


def test_wp12_s_stat_beam_uz_001() -> None:
    _beam2_quantitative("STAT-BEAM-UZ-001", "UZ", "IY", "RY", -1.0)


def test_wp12_s_fem_tet4_h_001(tmp_path: Path) -> None:
    from solveur.verification.tet4_structured_convergence import (
        StructuredTet4ConvergencePlan,
        run_structured_tet4_study,
    )

    output = tmp_path / "FEM-TET4-H-001"
    assert not output.exists()
    plan = StructuredTet4ConvergencePlan(
        base_nx=2,
        base_ny=1,
        base_nz=1,
        refinement_factors=(1, 2, 4),
        decomposition="six",
        load_distribution="tributary",
    )
    expected_levels = ((12, 12, 36), (96, 45, 135), (768, 225, 675))
    observed_levels = tuple((level.element_count, level.node_count, level.ndof) for level in plan.levels)
    assert observed_levels == expected_levels
    summary = run_structured_tet4_study(
        output,
        plan=plan,
        length=4.0,
        width=0.4,
        height=0.4,
        young=70.0e9,
        poisson=0.3,
        total_load=-1.0,
        relative_limit=0.01,
        residual_limit=1.0e-8,
        chunk_size=8192,
        maxiter=10_000,
        solver_backend="matrix_free",
        study_id="FEM-TET4-H-001",
    )
    rows = summary["rows"]
    csv_path = output / "results.csv"
    fieldnames = list(rows[0])
    with csv_path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    _emit(
        "FEM-TET4-H-001",
        result_classification="BOUNDED_REFINEMENT_CHARACTERIZATION_ONLY",
        helper_status=summary["status"],
        helper_status_is_scientific_acceptance=False,
        plan=summary["plan"],
        reference=summary["reference"],
        solver=summary["solver"],
        rows=rows,
        observed_orders=summary["observed_orders"],
        utility_thresholds_are_provisional_diagnostics={"relative_limit": 0.01, "residual_limit": 1.0e-8},
        between_level_displacement_changes=[
            {
                "coarse_factor": int(rows[index]["factor"]),
                "fine_factor": int(rows[index + 1]["factor"]),
                "absolute_change_m": abs(float(rows[index + 1]["tip_uz_m"]) - float(rows[index]["tip_uz_m"])),
            }
            for index in range(len(rows) - 1)
        ],
        output_files=[
            "summary.json",
            "report.md",
            "results.csv",
            "level_1/model.h5",
            "level_2/model.h5",
            "level_4/model.h5",
        ],
        three_dimensional_independent_reference="NOT_AVAILABLE_IN_THIS_CAMPAIGN",
        physical_validation="NOT_ESTABLISHED",
    )
    assert len(rows) == 3
    assert tuple((row["elements"], row["nodes"], row["dofs"]) for row in rows) == expected_levels
    assert all(math.isfinite(float(row["tip_uz_m"])) for row in rows)
    assert all(math.isfinite(float(row["relative_residual"])) for row in rows)
