"""Bounded WP-D02 dynamic stress recovery references and refusal contracts."""

from __future__ import annotations

from fractions import Fraction
import json

import numpy as np
import pytest

from solveur.contact.entities import FrictionlessContact
from solveur.core.analyses.modal_basis import ModalBasis
from solveur.core.analyses.modal_newmark import ModalNewmarkResult
from solveur.core.analyses.modal_newmark import ModalNewmarkTransientSolver
from solveur.core.analyses.prepared_dynamic_system import PreparedDynamicSystem
from solveur.core.model import ElementDefinition, FiniteElementModel
from solveur.core.results import ReducedHarmonicResult
from solveur.elements.solid.hex20 import Hex20Element
from solveur.elements.solid.hex8 import Hex8Element
from solveur.post.dynamic_stress import (
    HARMONIC_PHASE_CONVENTION,
    _decimal_matvec,
    _matvec_roundoff_limited,
    recover_harmonic_stress,
    recover_modal_transient_stress,
    recover_solid_stress_field,
)


SOURCE_SHA = "a" * 40
YOUNG_MODULUS = 210.0e9
POISSON_RATIO = 0.3


@pytest.mark.parametrize("family", ["TET4", "TET10", "HEX8", "HEX20"])
def test_uniaxial_reference_checks_sign_scaling_units_and_rigid_translation(family: str) -> None:
    model = _model(family)
    epsilon = -1.2e-4
    field = _affine_field(model, np.diag([epsilon, -POISSON_RATIO * epsilon, -POISSON_RATIO * epsilon]))

    recovered = recover_solid_stress_field(model, field)
    points = _all_points(recovered)
    expected = np.asarray([YOUNG_MODULUS * epsilon, 0.0, 0.0, 0.0, 0.0, 0.0])
    expected_point_counts = {"TET4": 1, "TET10": 4, "HEX8": 8, "HEX20": 27}
    assert points
    assert recovered["element_coverage"] == [family]
    assert len(points) == expected_point_counts[family]
    assert [point["integration_point_index"] for point in points] == list(range(expected_point_counts[family]))
    assert all(point["integration_point_id_basis"] == "zero_based_element_rule_order" for point in points)
    for point in points:
        assert point["stress_components"]["values"] == pytest.approx(expected, rel=2.0e-12, abs=1.0e-8)
        assert point["von_mises"] == pytest.approx(abs(YOUNG_MODULUS * epsilon), rel=2.0e-12)
    assert recovered["units"]["stress"] == "Pa"
    assert recovered["coordinate_frame"] == "GLOBAL_CARTESIAN"

    translation = np.tile(np.asarray([0.7, -1.3, 2.1]), model.node_count)
    rigid = recover_solid_stress_field(model, translation)
    for point in _all_points(rigid):
        assert point["stress_components"]["values"] == pytest.approx(np.zeros(6), abs=1.0e-6)
        assert point["von_mises"] == pytest.approx(0.0, abs=1.0e-6)


def test_tet4_complex_harmonic_stress_matches_independent_affine_reference() -> None:
    model = _model(
        "TET4",
        analysis={"type": "harmonic_response", "method": "modal_superposition", "parameters": {}},
        fixed_support=True,
    )
    prepared = PreparedDynamicSystem.prepare(model, source_sha=SOURCE_SHA)
    basis = ModalBasis.from_prepared(prepared, mode_count=prepared.reduced_size, method="dense")
    modal_coordinates = np.asarray([0.2 + 0.35j, 0.0 + 0.0j, 0.0 + 0.0j])
    displacement = prepared.expand_complex_state(basis.modes @ modal_coordinates)
    result = _harmonic_result(model, prepared, basis, displacement, modal_coordinates)

    recovered = recover_harmonic_stress(
        model,
        result,
        prepared=prepared,
        basis=basis,
        selected_frequencies_hz=[5.0],
    )
    point = _all_points(recovered["frequency_responses"][0])[0]
    expected = _independent_tet4_stress(model, displacement)
    assert point["stress_components"]["real"] == pytest.approx(expected.real, rel=2.0e-11, abs=1.0e-8)
    assert point["stress_components"]["imag"] == pytest.approx(expected.imag, rel=2.0e-11, abs=1.0e-8)
    assert point["von_mises_phase_peak"] == pytest.approx(_sampled_harmonic_peak(expected), rel=2.0e-8)
    phase = 0.71
    instantaneous_displacement = np.real(displacement * np.exp(1j * phase))
    instantaneous = recover_solid_stress_field(model, instantaneous_displacement)
    instantaneous_expected = np.real(expected * np.exp(1j * phase))
    assert _all_points(instantaneous)[0]["stress_components"]["values"] == pytest.approx(
        instantaneous_expected, rel=2.0e-11, abs=1.0e-8
    )
    assert recovered["phase_convention"] == HARMONIC_PHASE_CONVENTION


def test_harmonic_recovery_refuses_a_phase_convention_mismatch() -> None:
    model, prepared, basis, result = _harmonic_fixture()
    result.solver["phase_convention"] = "u(t) = Re[U exp(-i*omega*t)]"
    with pytest.raises(ValueError, match="phase convention"):
        recover_harmonic_stress(
            model,
            result,
            prepared=prepared,
            basis=basis,
            selected_frequencies_hz=[5.0],
        )


def test_complete_modal_basis_stress_matches_direct_full_order_displacement() -> None:
    model = _model(
        "TET4",
        analysis={"type": "harmonic_response", "method": "modal_superposition", "parameters": {}},
        fixed_support=True,
    )
    prepared = PreparedDynamicSystem.prepare(model, source_sha=SOURCE_SHA)
    basis = ModalBasis.from_prepared(prepared, mode_count=prepared.reduced_size, method="dense")
    modal_coordinates = np.asarray([0.4 + 0.15j, -0.2 + 0.05j, 0.3 - 0.1j])
    reduced_full_order = basis.modes @ modal_coordinates
    full_order = prepared.expand_complex_state(reduced_full_order)
    result = _harmonic_result(model, prepared, basis, full_order, modal_coordinates)

    direct_stress = recover_solid_stress_field(model, full_order)
    modal_stress = recover_harmonic_stress(
        model,
        result,
        prepared=prepared,
        basis=basis,
        selected_frequencies_hz=[5.0],
    )
    direct_points = _all_points(direct_stress)
    modal_points = _all_points(modal_stress["frequency_responses"][0])
    assert basis.is_full_basis
    assert result.responses[0] == pytest.approx(full_order, rel=2.0e-12, abs=1.0e-12)
    assert len(modal_points) == len(direct_points)
    for modal_point, direct_point in zip(modal_points, direct_points, strict=True):
        assert modal_point["stress_components"]["real"] == pytest.approx(
            direct_point["stress_components"]["real"], rel=2.0e-11, abs=1.0e-8
        )
        assert modal_point["stress_components"]["imag"] == pytest.approx(
            direct_point["stress_components"]["imag"], rel=2.0e-11, abs=1.0e-8
        )


def test_truncated_basis_changes_local_stress_and_does_not_claim_full_order_accuracy() -> None:
    model = _model(
        "TET4",
        analysis={"type": "harmonic_response", "method": "modal_superposition", "parameters": {}},
        fixed_support=True,
    )
    prepared = PreparedDynamicSystem.prepare(model, source_sha=SOURCE_SHA)
    full_basis = ModalBasis.from_prepared(prepared, mode_count=prepared.reduced_size, method="dense")
    cluster_boundaries = [
        count
        for count in range(1, full_basis.mode_count)
        if all(not (cluster[0] <= count < cluster[-1]) for cluster in full_basis.clusters)
    ]
    assert cluster_boundaries, "fixture must expose a truncation boundary between identified modal clusters"
    truncated = ModalBasis.from_prepared(prepared, mode_count=cluster_boundaries[0], method="dense")
    coefficients = np.asarray([1.0, -2.0, 3.0])
    reduced_full = full_basis.modes @ coefficients
    truncated_coordinates = truncated.modes.T @ (prepared.mass @ reduced_full)
    reduced_truncated = truncated.modes @ truncated_coordinates
    direct = prepared.expand_state(reduced_full)
    approximate = prepared.expand_state(reduced_truncated)
    harmonic_approximate = prepared.expand_complex_state(reduced_truncated.astype(np.complex128))
    result = _harmonic_result(
        model,
        prepared,
        truncated,
        harmonic_approximate,
        truncated_coordinates.astype(np.complex128),
    )

    direct_stress = _all_stress_values(recover_solid_stress_field(model, direct))
    truncated_stress = _all_stress_values(recover_solid_stress_field(model, approximate))
    recovered = recover_harmonic_stress(
        model,
        result,
        prepared=prepared,
        basis=truncated,
        selected_frequencies_hz=[5.0],
    )
    dynamic_truncated_stress = _all_stress_values(recovered["frequency_responses"][0])
    displacement_error = np.linalg.norm(direct - approximate) / np.linalg.norm(direct)
    stress_error = np.linalg.norm(direct_stress - truncated_stress) / np.linalg.norm(direct_stress)
    assert displacement_error > 0.0
    assert stress_error > 0.0
    assert not truncated.is_full_basis
    assert dynamic_truncated_stress == pytest.approx(truncated_stress, rel=2.0e-11, abs=1.0e-8)
    assert recovered["modal_basis"]["is_full_basis"] is False
    assert "no stress error bound" in recovered["accuracy_statement"]


def test_modal_transient_selected_times_match_direct_displacement_recovery() -> None:
    model = _model(
        "TET4",
        analysis={"type": "transient_dynamic", "method": "modal_newmark", "parameters": {}},
        fixed_support=True,
    )
    prepared = PreparedDynamicSystem.prepare(model, source_sha=SOURCE_SHA)
    basis = ModalBasis.from_prepared(prepared, mode_count=prepared.reduced_size, method="dense")
    modal_rows = [
        {"step": 0, "time_s": 0.0, "q": [0.0, 0.0, 0.0], "qdot": [0.0, 0.0, 0.0], "qddot": [0.0, 0.0, 0.0]},
        {"step": 1, "time_s": 0.01, "q": [0.2, -0.1, 0.05], "qdot": [0.0, 0.0, 0.0], "qddot": [0.0, 0.0, 0.0]},
        {"step": 2, "time_s": 0.02, "q": [-0.1, 0.15, 0.2], "qdot": [0.0, 0.0, 0.0], "qddot": [0.0, 0.0, 0.0]},
    ]
    final_state = prepared.expand_state(basis.modes @ np.asarray(modal_rows[-1]["q"]))
    provenance = {
        "source_sha": prepared.source_sha,
        "physical_identity": prepared.physical_identity,
        "operator_identity": prepared.operator_identity,
        "basis_identity": basis.basis_identity,
    }
    result = ModalNewmarkResult(
        numerical_status="PASS",
        times=np.asarray([0.0, 0.01, 0.02]),
        displacements=final_state,
        velocities=np.zeros_like(final_state),
        accelerations=np.zeros_like(final_state),
        modal_displacements=np.asarray(modal_rows[-1]["q"], dtype=float),
        modal_velocities=np.zeros(basis.mode_count),
        modal_accelerations=np.zeros(basis.mode_count),
        dofs=model.dof_manager(),
        node_count=model.node_count,
        element_count=len(model.elements),
        solver={"contract": "qf-modal-newmark/v1"},
        provenance=provenance,
        result_availability={"modal_state_history": {"status": "AVAILABLE"}},
        execution_identity={},
        execution_key="test-modal-newmark-key",
        qualification_scope_id="test-wp-d02-scope",
        mesh_report={},
        modal_history=tuple(modal_rows),
    )

    recovered = recover_modal_transient_stress(
        model,
        result,
        prepared=prepared,
        basis=basis,
        selected_times_s=[0.0, 0.02],
    )
    assert [row["time_s"] for row in recovered["time_responses"]] == [0.0, 0.02]
    assert [row["step"] for row in recovered["time_responses"]] == [0, 2]
    for row, modal_row in zip(recovered["time_responses"], (modal_rows[0], modal_rows[2]), strict=True):
        direct = prepared.expand_state(basis.modes @ np.asarray(modal_row["q"], dtype=float))
        expected = recover_solid_stress_field(model, direct)
        assert _all_stress_values(row) == pytest.approx(_all_stress_values(expected), rel=2.0e-11, abs=1.0e-8)


def test_dynamic_recovery_fails_closed_for_invalid_sources_and_incomplete_fields() -> None:
    model = _model("TET4")
    with pytest.raises(ValueError, match="Unsupported stress convention"):
        recover_solid_stress_field(model, np.zeros(model.dof_manager().ndof), stress_convention="LOCAL_ENGINEERING")
    with pytest.raises(ValueError, match="complete one-dimensional"):
        recover_solid_stress_field(model, np.zeros(model.dof_manager().ndof - 1))

    nonlinear = _model("TET4", material_type="nonlinear_isotropic_3d")
    with pytest.raises(ValueError, match="linear isotropic_3d"):
        recover_solid_stress_field(nonlinear, np.zeros(nonlinear.dof_manager().ndof))

    contact = _model("TET4")
    contact.contacts.append(FrictionlessContact(slave_node=3, master_nodes=(0, 1, 2)))
    with pytest.raises(ValueError, match="Contact configurations"):
        recover_solid_stress_field(contact, np.zeros(contact.dof_manager().ndof))

    unsupported = _model("TET4")
    original = unsupported.elements[0]
    unsupported.elements[0] = ElementDefinition(type="BEAM2", nodes=original.nodes, material=original.material)
    with pytest.raises(ValueError, match="only TET4, TET10, HEX8 and HEX20"):
        recover_solid_stress_field(unsupported, np.zeros(unsupported.dof_manager().ndof))


def test_dynamic_recovery_refuses_stale_operators_and_basis() -> None:
    model, prepared, basis, result = _harmonic_fixture()
    stale_model = _model(
        "TET4",
        analysis={"type": "harmonic_response", "method": "modal_superposition", "parameters": {}},
        fixed_support=True,
        young_modulus=2.0 * YOUNG_MODULUS,
    )
    stale_prepared = PreparedDynamicSystem.prepare(stale_model, source_sha=SOURCE_SHA)
    stale_basis = ModalBasis.from_prepared(stale_prepared, mode_count=stale_prepared.reduced_size, method="dense")
    with pytest.raises(ValueError, match="Prepared dynamic operators do not match"):
        recover_harmonic_stress(
            model,
            result,
            prepared=stale_prepared,
            basis=stale_basis,
            selected_frequencies_hz=[5.0],
        )
    with pytest.raises(ValueError, match="Modal basis is stale"):
        recover_harmonic_stress(
            model,
            result,
            prepared=prepared,
            basis=stale_basis,
            selected_frequencies_hz=[5.0],
        )
    assert prepared is not stale_prepared
    assert basis is not stale_basis


def _assert_hex20_fraction_oracle_uses_tensor_shear_voigt_order() -> None:
    """Keep the independent oracle's six-component mapping explicit."""
    model = _model("HEX20", young_modulus=float(2**30), poisson_ratio=0.25)
    coords = np.asarray(model.nodes, dtype=np.float64)
    gradient = np.asarray([
        [1 / 64, 1 / 128, 1 / 256],
        [3 / 512, 1 / 32, 5 / 1024],
        [-1 / 1024, 7 / 2048, 1 / 16],
    ], dtype=np.float64)
    strain = [[
        (Fraction.from_float(float(gradient[i, j])) + Fraction.from_float(float(gradient[j, i]))) / 2
        for j in range(3)
    ] for i in range(3)]
    young, poisson = Fraction(2**30), Fraction(1, 4)
    lam = poisson * young / ((1 + poisson) * (1 - 2 * poisson))
    mu = young / (2 * (1 + poisson))
    trace = sum((strain[index][index] for index in range(3)), Fraction(0))
    sigma = [[lam * trace * Fraction(int(i == j)) + 2 * mu * strain[i][j]
              for j in range(3)] for i in range(3)]
    expected = np.asarray([
        float(sigma[0][0]), float(sigma[1][1]), float(sigma[2][2]),
        float(sigma[0][1]), float(sigma[1][2]), float(sigma[2][0]),
    ])
    actual = _fraction_affine_isotropic_stress(coords, coords @ gradient.T)
    assert len(set(expected.tolist())) == 6
    assert np.array_equal(actual, expected)


def _assert_decimal_cancellation_against_fraction_reference() -> None:
    matrix = np.asarray([[1.0e16, 1.0, -1.0e16]], dtype=np.float64)
    vector = np.ones(3, dtype=np.float64)
    reference = sum(
        (Fraction.from_float(float(a)) * Fraction.from_float(float(b)) for a, b in zip(matrix[0], vector, strict=True)),
        Fraction(0),
    )
    binary64 = matrix @ vector
    guarded = _decimal_matvec(matrix, vector)
    assert reference == 1
    assert binary64[0] == 0.0
    assert _matvec_roundoff_limited(matrix, vector, binary64)
    assert guarded[0] == float(reference)


def test_transient_tet4_free_vibration_matches_modal_oracle_and_independent_stress() -> None:
    """Separate time-integration error from affine stress-recovery error."""
    # The V diagnostic held the physical duration at 0.4 ms and showed a
    # second-order reduction in modal phase error as dt was halved.  At 2.5 us
    # the observed normalized error was 1.8542e-4, below the frozen 5e-4 limit.
    dt = 2.5e-6
    steps = 160
    analysis = {
        "type": "transient_dynamic",
        "method": "modal_newmark",
        "parameters": {
            "time_step": dt,
            "steps": steps,
            "modal_mode_count": 3,
            "modal_extraction_method": "dense",
            "modal_dense_limit": 256,
            "rayleigh_alpha": 0.0,
            "rayleigh_beta": 0.0,
            "record_time_history": True,
            "store_modal_history": True,
            "initial_displacements": [
                {"node": 3, "dof": "UX", "value": 1.0e-8},
                {"node": 3, "dof": "UY", "value": -0.7e-8},
                {"node": 3, "dof": "UZ", "value": 0.4e-8},
            ],
        },
    }
    model = _model("TET4", analysis=analysis, fixed_support=True)
    prepared = PreparedDynamicSystem.prepare(model, source_sha=SOURCE_SHA)
    basis = ModalBasis.from_prepared(prepared, mode_count=prepared.reduced_size, method="dense")
    assert np.all(np.isfinite(basis.eigenvalues))
    assert np.all(np.asarray(basis.eigenvalues) > 0.0)
    result = ModalNewmarkTransientSolver().solve(
        model, source_sha=SOURCE_SHA, prepared=prepared, basis=basis,
    )
    assert result.numerical_status == "PASS"
    assert len(result.modal_history) == steps + 1

    # The dynamic oracle is the closed-form free response of each computed
    # uncoupled modal oscillator. It isolates integration error, not eigenpair
    # extraction error; the stress oracle below does not use modal or B data.
    q0 = np.asarray(result.modal_history[0]["q"], dtype=np.float64)
    specified_initial = np.zeros(model.dof_manager().ndof, dtype=np.float64)
    specified_initial[model.dof_manager().node_indices(3, ("UX", "UY", "UZ"))] = [1.0e-8, -0.7e-8, 0.4e-8]
    expected_initial = np.linalg.solve(
        basis.projected_mass,
        basis.modes.T @ (prepared.mass @ prepared.reduce_state(specified_initial)),
    )
    initial_projection_abs_error = float(np.max(np.abs(q0 - expected_initial)))
    initial_projection_rel_error = initial_projection_abs_error / max(float(np.max(np.abs(expected_initial))), 1.0e-30)
    angular_frequencies = np.sqrt(np.asarray(basis.eigenvalues, dtype=np.float64))
    max_modal_abs_error = 0.0
    worst_modal = None
    dof_owners = {}
    dof_manager = model.dof_manager()
    for node, names in dof_manager.node_dofs.items():
        for index, name in zip(dof_manager.node_indices(node, names), names, strict=True):
            dof_owners[int(index)] = {"node": int(node), "dof": str(name)}
    for row in result.modal_history:
        time_s = float(row["time_s"])
        actual = np.asarray(row["q"], dtype=np.float64)
        exact = expected_initial * np.cos(angular_frequencies * time_s)
        errors = np.abs(actual - exact)
        local_index = int(np.argmax(errors))
        local_error = float(errors[local_index])
        if local_error > max_modal_abs_error:
            max_modal_abs_error = local_error
            full_error = prepared.expand_state(basis.modes @ (actual - exact))
            worst_dof_index = int(np.argmax(np.abs(full_error)))
            worst_modal = {
                "time_s": time_s,
                "modal_coordinate_index": local_index,
                "numerical_m": float(actual[local_index]),
                "reference_m": float(exact[local_index]),
                "absolute_error_m": local_error,
                "worst_reconstructed_DDL_index": worst_dof_index,
                "worst_reconstructed_DDL": dof_owners.get(worst_dof_index),
                "worst_reconstructed_DDL_absolute_error_m": float(abs(full_error[worst_dof_index])),
            }

    selected_times = [0.0, 40.0 * dt, 80.0 * dt, 160.0 * dt]
    recovered = recover_modal_transient_stress(
        model, result, prepared=prepared, basis=basis, selected_times_s=selected_times,
    )
    # The acceptance metric is the maximum absolute stress-component error
    # over all selected times, integration points, and Voigt components.
    # Reduce each (integration point, component) array to that scalar L-infinity
    # error before comparing it with the scalar Pa threshold.
    max_stress_abs_error = 0.0
    max_stress_relative_error = 0.0
    worst_stress = None
    stress_diagnostics = []
    for response in recovered["time_responses"]:
        step = int(response["step"])
        time_s = float(response["time_s"])
        modal_state = np.asarray(result.modal_history[step]["q"], dtype=np.float64)
        full_displacement = prepared.expand_state(basis.modes @ modal_state)
        oracle = _fraction_affine_isotropic_stress(model.nodes, full_displacement.reshape((4, 3)))
        point_values = []
        for point in _all_points(response):
            point_values.append(np.asarray(point["stress_components"]["values"], dtype=np.float64))
        recovered_values = np.asarray(point_values, dtype=np.float64)
        point_errors = np.abs(recovered_values - oracle[None, :])
        reference_scale = max(float(np.max(np.abs(oracle))), 1.0e-30)
        max_stress_abs_error = max(max_stress_abs_error, float(np.max(point_errors)))
        max_stress_relative_error = max(
            max_stress_relative_error,
            float(np.max(point_errors / reference_scale)),
        )
        for point_index in range(recovered_values.shape[0]):
            for component_index, component in enumerate(("XX", "YY", "ZZ", "XY", "YZ", "ZX")):
                stress_diagnostics.append({
                    "time_s": time_s,
                    "step": step,
                    "element_index": 0,
                    "integration_point_index": point_index,
                    "component": component,
                    "numerical_Pa": float(recovered_values[point_index, component_index]),
                    "reference_Pa": float(oracle[component_index]),
                    "absolute_error_Pa": float(point_errors[point_index, component_index]),
                    "relative_error": float(point_errors[point_index, component_index] / reference_scale),
                    "limit_Pa": 1.0e-7,
                })
        point_index, component_index = np.unravel_index(int(np.argmax(point_errors)), point_errors.shape)
        candidate = {
            "time_s": time_s,
            "step": step,
            "element_index": 0,
            "integration_point_index": int(point_index),
            "component": ["XX", "YY", "ZZ", "XY", "YZ", "ZX"][component_index],
            "numerical_Pa": float(recovered_values[point_index, component_index]),
            "reference_Pa": float(oracle[component_index]),
            "absolute_error_Pa": float(point_errors[point_index, component_index]),
            "relative_error": float(point_errors[point_index, component_index] / reference_scale),
        }
        if worst_stress is None or candidate["absolute_error_Pa"] > worst_stress["absolute_error_Pa"]:
            worst_stress = candidate
    modal_relative_error = max_modal_abs_error / max(float(np.max(np.abs(q0))), 1.0e-30)
    print(json.dumps({
        "case": "TET4 modal free vibration",
        "time_step_s": dt,
        "steps": steps,
        "duration_s": dt * steps,
        "initial_modal_projection_abs_error_m": initial_projection_abs_error,
        "initial_modal_projection_relative_error": initial_projection_rel_error,
        "initial_projection_limit": 1.0e-12,
        "max_modal_coordinate_abs_error_m": max_modal_abs_error,
        "max_modal_coordinate_relative_error": modal_relative_error,
        "modal_limit": 5.0e-4,
        "worst_modal_sample": worst_modal,
        "max_stress_abs_error_Pa": max_stress_abs_error,
        "max_stress_relative_error": max_stress_relative_error,
        "stress_limit_Pa": 1.0e-7,
        "worst_stress_sample": worst_stress,
        "stress_samples": stress_diagnostics,
        "stress_reference": "Fraction affine fit of nodal coordinates/displacements + isotropic Lamé law",
        "stress_components": ["XX", "YY", "ZZ", "XY", "YZ", "ZX"],
        "shear": "tensor shear stress",
        "modal_reference_scope": "computed eigenpairs; isolates Newmark integration, not eigenpair extraction",
    }, sort_keys=True))
    # Thresholds are frozen; the time step was selected from the measured
    # second-order convergence trend, with the physical interval unchanged.
    assert initial_projection_rel_error <= 1.0e-12
    assert modal_relative_error <= 5.0e-4
    assert max_stress_abs_error <= 1.0e-7


@pytest.mark.parametrize("geometry", ["regular", "moderately_distorted"])
def test_hex20_multiaxial_affine_stress_and_translation_on_valid_geometries(geometry: str) -> None:
    if geometry == "regular":
        _assert_hex20_fraction_oracle_uses_tensor_shear_voigt_order()
        _assert_decimal_cancellation_against_fraction_reference()
    model = _model("HEX20", young_modulus=float(2**30), poisson_ratio=0.25)
    if geometry == "moderately_distorted":
        model.nodes[6] += np.asarray([0.125, -0.0625, 0.0625])
        model.nodes[18] += np.asarray([0.0, 0.0625, 0.0])
    coords = np.asarray(model.nodes, dtype=np.float64)
    Hex20Element.validate_geometry(coords)
    gauss_determinants = [
        float(item[3]) for item in Hex20Element.integration_data(coords)
    ]
    assert len(gauss_determinants) == 27
    assert min(gauss_determinants) > 0.9
    # A deterministic 7^3 reference lattice is a sampled validity check,
    # not a proof of positivity between sample points.
    dense_determinants = [
        float(Hex20Element.jacobian_determinant(coords, (x, y, z)))
        for x in np.linspace(-1.0, 1.0, 7)
        for y in np.linspace(-1.0, 1.0, 7)
        for z in np.linspace(-1.0, 1.0, 7)
    ]
    assert min(dense_determinants) > 0.9

    gradient = np.asarray([
        [2.0**-13, 2.0**-15, -2.0**-16],
        [2.0**-15, -2.0**-14, 2.0**-17],
        [-2.0**-16, 2.0**-17, 2.0**-12],
    ])
    displacement = coords @ gradient.T
    oracle = _fraction_affine_isotropic_stress(coords, displacement)
    recovered = recover_solid_stress_field(model, displacement.reshape(-1))
    values = np.asarray([point["stress_components"]["values"] for point in _all_points(recovered)])
    max_abs_error = float(np.max(np.abs(values - oracle[None, :])))
    worst_point, worst_component = np.unravel_index(int(np.argmax(np.abs(values - oracle[None, :]))), values.shape)
    print(json.dumps({
        "case": "HEX20 affine multiaxial",
        "geometry": geometry,
        "gauss_jacobian_min": min(gauss_determinants),
        "gauss_jacobian_max": max(gauss_determinants),
        "sampled_7x7x7_jacobian_min": min(dense_determinants),
        "sampled_7x7x7_jacobian_max": max(dense_determinants),
        "integration_points": len(values),
        "max_abs_stress_error_Pa": max_abs_error,
        "error_limit_Pa": 1.0e-8,
        "worst_sample": {
            "integration_point_index": int(worst_point),
            "component": ["XX", "YY", "ZZ", "XY", "YZ", "ZX"][worst_component],
            "numerical_Pa": float(values[worst_point, worst_component]),
            "reference_Pa": float(oracle[worst_component]),
        },
        "stress_reference": "Fraction affine fit of actual nodal geometry/displacement + Lamé law",
    }, sort_keys=True))
    assert values.shape == (27, 6)
    assert max_abs_error <= 1.0e-8

    translation = np.asarray([0.7, -1.3, 2.1])
    translated = recover_solid_stress_field(model, (displacement + translation).reshape(-1))
    translated_values = np.asarray([
        point["stress_components"]["values"] for point in _all_points(translated)
    ])
    translation_delta = float(np.max(np.abs(translated_values - values)))
    assert translation_delta <= 1.0e-6
    print(json.dumps({"translation_invariance_delta_Pa": translation_delta}, sort_keys=True))


def _fraction_affine_isotropic_stress(coords: np.ndarray, nodal_u: np.ndarray) -> np.ndarray:
    """Independent exact-rational affine fit and isotropic constitutive oracle."""
    def exact(value):
        return Fraction.from_float(float(value))
    # TET4 affine fit: rows correspond to (1, x, y, z), columns to ux/uy/uz.
    independent_nodes = (0, 1, 3, 4) if coords.shape[0] == 20 else (0, 1, 2, 3)
    rows = [[Fraction(1), *(exact(value) for value in coords[index])] for index in independent_nodes]
    rhs = [[exact(value) for value in nodal_u[index]] for index in independent_nodes]
    augmented = [rows[index] + rhs[index] for index in range(4)]
    for column in range(4):
        pivot = next(index for index in range(column, 4) if augmented[index][column])
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for index in range(4):
            if index == column:
                continue
            factor = augmented[index][column]
            augmented[index] = [
                left - factor * right for left, right in zip(augmented[index], augmented[column], strict=True)
            ]
    # Gradient rows are displacement components, columns are x/y/z.
    # Augmented row order is [1, x, y, z, ux, uy, uz]; RHS starts at 4.
    # Gradient rows are displacement components, columns are x/y/z.
    gradient = [[augmented[axis + 1][4 + component] for axis in range(3)] for component in range(3)]
    strain = [[(gradient[i][j] + gradient[j][i]) / 2 for j in range(3)] for i in range(3)]
    young = exact(float(2**30)) if coords.shape[0] == 20 else exact(YOUNG_MODULUS)
    poisson = exact(0.25) if coords.shape[0] == 20 else exact(POISSON_RATIO)
    lam = poisson * young / ((1 + poisson) * (1 - 2 * poisson))
    mu = young / (2 * (1 + poisson))
    trace = sum((strain[index][index] for index in range(3)), Fraction(0))
    stress = [[lam * trace * Fraction(int(i == j)) + 2 * mu * strain[i][j] for j in range(3)] for i in range(3)]
    return np.asarray([float(stress[0][0]), float(stress[1][1]), float(stress[2][2]),
                       float(stress[0][1]), float(stress[1][2]), float(stress[2][0])])


def _harmonic_fixture() -> tuple[
    FiniteElementModel,
    PreparedDynamicSystem,
    ModalBasis,
    ReducedHarmonicResult,
]:
    model = _model(
        "TET4",
        analysis={"type": "harmonic_response", "method": "modal_superposition", "parameters": {}},
        fixed_support=True,
    )
    prepared = PreparedDynamicSystem.prepare(model, source_sha=SOURCE_SHA)
    basis = ModalBasis.from_prepared(prepared, mode_count=prepared.reduced_size, method="dense")
    coordinates = np.asarray([0.1 + 0.2j, -0.03 + 0.08j, 0.04 - 0.05j])
    displacement = prepared.expand_complex_state(basis.modes @ coordinates)
    return model, prepared, basis, _harmonic_result(model, prepared, basis, displacement, coordinates)


def _harmonic_result(
    model: FiniteElementModel,
    prepared: PreparedDynamicSystem,
    basis: ModalBasis,
    displacement: np.ndarray,
    coordinates: np.ndarray,
) -> ReducedHarmonicResult:
    provenance = {
        "source_sha": prepared.source_sha,
        "physical_identity": prepared.physical_identity,
        "operator_identity": prepared.operator_identity,
        "basis_identity": basis.basis_identity,
    }
    return ReducedHarmonicResult(
        numerical_status="PASS",
        frequencies_hz=np.asarray([5.0]),
        responses=(np.asarray(displacement, dtype=np.complex128),),
        modal_coordinates=(np.asarray(coordinates, dtype=np.complex128),),
        dof_signature=prepared.dof_signature,
        full_dof_count=sum(len(names) for _, names in prepared.dof_signature),
        node_count=model.node_count,
        element_count=len(model.elements),
        solver={"phase_convention": HARMONIC_PHASE_CONVENTION},
        provenance=provenance,
        result_availability={},
        execution_identity={},
        execution_key="test-reduced-harmonic-key",
        qualification_scope_id="test-wp-d02-scope",
        mesh_report={},
    )


def _model(
    family: str,
    *,
    analysis: str | dict[str, object] = "linear_static",
    fixed_support: bool = False,
    young_modulus: float = YOUNG_MODULUS,
    poisson_ratio: float = POISSON_RATIO,
    material_type: str = "isotropic_3d",
) -> FiniteElementModel:
    if family == "TET4":
        nodes = np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.2, 1.1, 0.0], [0.25, 0.3, 1.4]])
    elif family == "TET10":
        corners = np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.2, 1.1, 0.0], [0.25, 0.3, 1.4]])
        edges = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))
        nodes = np.vstack((corners, [0.5 * (corners[a] + corners[b]) for a, b in edges]))
    elif family == "HEX8":
        nodes = np.asarray(Hex8Element.node_signs, dtype=float)
    elif family == "HEX20":
        corners = np.asarray(Hex20Element.node_signs, dtype=float)
        edge_nodes = []
        for free_axis, fixed_axes, fixed_signs in Hex20Element.edge_data:
            point = np.zeros(3, dtype=float)
            point[list(fixed_axes)] = fixed_signs
            point[free_axis] = 0.0
            edge_nodes.append(point)
        nodes = np.vstack((corners, edge_nodes))
    else:
        raise ValueError(f"Unsupported test family {family!r}.")
    material = {"type": material_type, "E": young_modulus, "nu": poisson_ratio, "density": 7800.0}
    if material_type == "nonlinear_isotropic_3d":
        material["hardening"] = 0.0
    fixed = []
    if fixed_support:
        fixed = [{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in (0, 1, 2)]
    return FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": family, "nodes": list(range(nodes.shape[0])), "material": "steel"}],
        materials={"steel": material},
        fixed_dofs=fixed,
        analysis=analysis,
        units={"system": "test", "length": "m", "stress": "Pa", "time": "s"},
    )


def _affine_field(model: FiniteElementModel, gradient: np.ndarray) -> np.ndarray:
    nodal_values = model.nodes @ np.asarray(gradient).T
    return np.asarray(nodal_values, dtype=np.float64).reshape(-1)


def _all_points(result: dict[str, object]) -> list[dict[str, object]]:
    elements = result["elements"]
    return [point for element in elements for point in element["integration_points"]]


def _all_stress_values(result: dict[str, object]) -> np.ndarray:
    values = []
    for point in _all_points(result):
        payload = point["stress_components"]
        values.extend(payload.get("values", payload.get("real", [])))
    return np.asarray(values, dtype=float)


def _independent_tet4_stress(model: FiniteElementModel, displacement: np.ndarray) -> np.ndarray:
    nodal_displacement = np.asarray(displacement).reshape((4, 3))
    interpolation = np.column_stack((np.ones(4), model.nodes))
    affine_coefficients = np.linalg.solve(interpolation, nodal_displacement)
    gradient = affine_coefficients[1:, :].T
    strain = 0.5 * (gradient + gradient.T)
    lam = POISSON_RATIO * YOUNG_MODULUS / ((1.0 + POISSON_RATIO) * (1.0 - 2.0 * POISSON_RATIO))
    mu = YOUNG_MODULUS / (2.0 * (1.0 + POISSON_RATIO))
    stress = lam * np.trace(strain) * np.eye(3) + 2.0 * mu * strain
    return np.asarray([stress[0, 0], stress[1, 1], stress[2, 2], stress[0, 1], stress[1, 2], stress[2, 0]])


def _sampled_harmonic_peak(stress: np.ndarray) -> float:
    phase = np.linspace(0.0, 2.0 * np.pi, 65_536, endpoint=False)
    instantaneous = stress.real[None, :] * np.cos(phase[:, None]) - stress.imag[None, :] * np.sin(phase[:, None])
    xx, yy, zz, xy, yz, zx = instantaneous.T
    vm_squared = 0.5 * ((xx - yy) ** 2 + (yy - zz) ** 2 + (zz - xx) ** 2) + 3.0 * (xy**2 + yz**2 + zx**2)
    return float(np.sqrt(np.max(vm_squared)))
