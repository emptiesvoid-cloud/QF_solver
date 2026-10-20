from __future__ import annotations

import copy
import math

import numpy as np
import pytest

from solveur.api import solve_model
from solveur.compatibility.preflight import preflight_model
from solveur.core.analyses.excitation_channels import (
    ComplexPhasor,
    ExcitationChannel,
    ExcitationChannelSet,
    HarmonicAmplitude,
    SpatialDofWeight,
)
from solveur.core.analyses.harmonic import HarmonicResponseSolver
from solveur.core.analyses.modal_basis import ModalBasis
from solveur.core.analyses.prepared_dynamic_system import PreparedDynamicSystem
from solveur.core.analyses.reduced_harmonic import (
    ReducedHarmonicResponseSolver,
    _solve_reduced_impedance,
)
from solveur.core.analyses.settings import AnalysisSettings
from solveur.core.errors import InputValidationError, NumericalConvergenceError
from solveur.core.model import FiniteElementModel
from solveur.core.qualification import model_maturity
from solveur.core.results import ReducedHarmonicResult
from solveur.core.solvers.linear import LinearSystemSolver


_SOURCE_SHA = "a" * 40


def _model(
    *,
    frequencies: list[float] | None = None,
    legacy_load: bool = True,
    extra_parameters: dict[str, object] | None = None,
) -> FiniteElementModel:
    parameters: dict[str, object] = {
        "frequencies_hz": frequencies or [1.0, 3.0],
        "modal_mode_count": 3,
        "modal_extraction_method": "dense",
        "modal_dense_limit": 64,
        "rayleigh_alpha": 0.02,
        "rayleigh_beta": 0.0001,
    }
    parameters.update(extra_parameters or {})
    return FiniteElementModel.from_raw(
        analysis={"type": "harmonic_response", "method": "modal_superposition", **parameters},
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "steel"}],
        materials={"steel": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3, "density": 7800.0}},
        fixed_dofs=[
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 2, "dofs": ["UX", "UY", "UZ"]},
            {"node": 3, "dofs": ["UX", "UY", "UZ"]},
        ],
        loads=[{"node": 1, "dof": "UX", "value": 1.0}] if legacy_load else [],
    )


def _prepare(model: FiniteElementModel) -> tuple[PreparedDynamicSystem, ModalBasis]:
    prepared = PreparedDynamicSystem.prepare(model, source_sha=_SOURCE_SHA)
    basis = ModalBasis.from_prepared(
        prepared,
        mode_count=int(model.analysis.parameters["modal_mode_count"]),
        method="dense",
        dense_limit=64,
    )
    return prepared, basis


def _channel(channel_id: str, frequency_hz: float, real: float, imag: float) -> ExcitationChannel:
    return ExcitationChannel(
        channel_id=channel_id,
        spatial_distribution=(SpatialDofWeight(1, "UX", 1.0),),
        spatial_units="N",
        amplitude_units="N",
        result_units="N",
        frame_convention="global_model_frame",
        sign_convention="positive_along_named_global_dof",
        constant_amplitude=None,
        harmonic=HarmonicAmplitude(frequency_hz, ComplexPhasor(real, imag)),
    )


def test_reduced_impedance_matches_independent_analytical_sdof_amplitude_and_phase() -> None:
    mass = 2.0
    stiffness = 20.0
    damping = 0.8
    force = 3.0 - 2.0j
    frequency_hz = 0.7
    omega = 2.0 * math.pi * frequency_hz
    impedance = np.asarray([[stiffness + 1j * omega * damping - omega**2 * mass]], dtype=complex)

    response, _, diagnostic = _solve_reduced_impedance(
        impedance,
        np.asarray([force]),
        np.asarray([[stiffness]]),
        LinearSystemSolver(),
        {},
    )

    expected = force / (stiffness + 1j * omega * damping - omega**2 * mass)
    assert response[0] == pytest.approx(expected, rel=1e-12, abs=1e-13)
    assert abs(response[0]) == pytest.approx(abs(expected), rel=1e-12)
    assert np.angle(response[0]) == pytest.approx(np.angle(expected), abs=1e-12)
    assert diagnostic["conditioning_status"] == "ACCEPTED"


def test_coupled_two_dof_complex_response_uses_full_projected_operators() -> None:
    mass = np.asarray([[2.0, 0.25], [0.25, 1.5]])
    stiffness = np.asarray([[20.0, -2.0], [-2.0, 8.0]])
    alpha, beta = 0.03, 0.002
    damping = alpha * mass + beta * stiffness
    force = np.asarray([1.0 + 2.0j, -0.5 + 0.25j])
    frequency_hz = 0.85
    omega = 2.0 * math.pi * frequency_hz
    impedance = stiffness + 1j * omega * damping - omega**2 * mass

    actual, _, _ = _solve_reduced_impedance(
        impedance,
        force,
        stiffness,
        LinearSystemSolver(),
        {},
    )
    expected = np.linalg.solve(impedance, force)
    np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-13)


def test_zero_excitation_is_explicit_and_does_not_create_a_nonzero_response() -> None:
    model = _model(frequencies=[0.0, 2.0], legacy_load=False)
    prepared, basis = _prepare(model)
    result = ReducedHarmonicResponseSolver().solve(
        model,
        source_sha=_SOURCE_SHA,
        prepared=prepared,
        basis=basis,
        excitation_channels=ExcitationChannelSet(),
    )
    for response in result.responses:
        np.testing.assert_array_equal(response, np.zeros(response.size, dtype=complex))
    assert all(row["reduced_backward_error"] == 0.0 for row in result.solver["frequency_records"])


def test_truncated_basis_records_observable_differences_without_claiming_error_bound() -> None:
    model = _model(frequencies=[5.0])
    prepared = PreparedDynamicSystem.prepare(model, source_sha=_SOURCE_SHA)
    observations: dict[int, complex] = {}
    solver = ReducedHarmonicResponseSolver()
    model.analysis.parameters["modal_mode_count"] = 1
    with pytest.raises(InputValidationError, match="cuts an identified modal cluster"):
        ModalBasis.from_prepared(prepared, mode_count=1, method="dense", dense_limit=64)
    for count in (2, prepared.reduced_size):
        model.analysis.parameters["modal_mode_count"] = count
        basis = ModalBasis.from_prepared(prepared, mode_count=count, method="dense", dense_limit=64)
        result = solver.solve(model, source_sha=_SOURCE_SHA, prepared=prepared, basis=basis)
        response_index = model.dof_manager().index(1, "UX")
        observations[count] = result.responses[0][response_index]
        assert result.solver["truncation"]["response_error_estimate"] == "NOT_PROVIDED"
        assert result.solver["truncation"]["residual_flexibility"] == (
            "NOT_ENABLED; WP05 default path is unchanged"
        )
    full = observations[prepared.reduced_size]
    differences = {
        count: float(abs(value - full) / max(abs(full), np.finfo(float).tiny)) for count, value in observations.items()
    }
    assert differences[prepared.reduced_size] == 0.0
    assert all(math.isfinite(value) for value in differences.values())


def test_reduced_impedance_detects_exact_and_near_resonance_before_solving() -> None:
    mass = 2.0
    stiffness = 20.0
    natural_frequency = math.sqrt(stiffness / mass) / (2.0 * math.pi)
    omega = 2.0 * math.pi * natural_frequency
    exact = np.asarray([[stiffness - omega**2 * mass]], dtype=complex)
    with pytest.raises(NumericalConvergenceError, match="conditioning limit"):
        _solve_reduced_impedance(
            exact,
            np.asarray([1.0 + 0.0j]),
            np.asarray([[stiffness]]),
            LinearSystemSolver(),
            {},
        )

    near_omega = 2.0 * math.pi * natural_frequency * (1.0 + 2.0e-9)
    near = np.asarray([[stiffness - near_omega**2 * mass]], dtype=complex)
    _, _, diagnostic = _solve_reduced_impedance(
        near,
        np.asarray([1.0 + 0.0j]),
        np.asarray([[stiffness]]),
        LinearSystemSolver(),
        {},
    )
    assert diagnostic["conditioning_status"] == "NEAR_SINGULAR_WARNING"


def test_full_basis_reduced_harmonic_matches_direct_rayleigh_route_and_zero_hz() -> None:
    reduced_model = _model(frequencies=[0.0, 1.0, 3.0])
    prepared, basis = _prepare(reduced_model)
    reduced = ReducedHarmonicResponseSolver().solve(
        reduced_model,
        source_sha=_SOURCE_SHA,
        prepared=prepared,
        basis=basis,
    )

    direct_model = copy.deepcopy(reduced_model)
    direct_model.analysis = AnalysisSettings.from_raw(
        {
            "type": "harmonic_response",
            "method": "direct_frequency",
            **direct_model.analysis.parameters,
        }
    )
    direct = HarmonicResponseSolver().solve(direct_model)
    assert basis.is_full_basis
    assert reduced.numerical_status == "PASS"
    assert reduced.maturity == "EXPERIMENTAL"
    assert reduced.run_verdict.value == "WARNING"
    assert reduced.solver["damping"]["source"] == "RAYLEIGH_PHYSICAL_PROJECTED"
    assert reduced.result_availability["physical_free_equation_residual"]["status"] == "AVAILABLE"
    assert max(row["reduced_backward_error"] for row in reduced.solver["frequency_records"]) <= 1e-8
    assert max(row["physical_free_backward_error"] for row in reduced.solver["frequency_records"]) <= 1e-8
    for actual, expected in zip(reduced.responses, direct.responses, strict=True):
        np.testing.assert_allclose(actual, expected, rtol=1e-8, atol=1e-11)
    assert reduced.solver["frequency_records"][0]["omega_rad_s"] == 0.0


def test_multichannel_phasor_phase_superposition_and_exact_cancellation() -> None:
    model = _model(frequencies=[2.0], legacy_load=False)
    prepared, basis = _prepare(model)
    solver = ReducedHarmonicResponseSolver()

    phase_results = []
    for real, imag in ((1.0, 0.0), (0.0, 1.0), (-1.0, 0.0)):
        channels = ExcitationChannelSet([_channel("force", 2.0, real, imag)])
        result = solver.solve(
            model,
            source_sha=_SOURCE_SHA,
            prepared=prepared,
            basis=basis,
            excitation_channels=channels,
        )
        phase_results.append(result.responses[0])

    np.testing.assert_allclose(phase_results[1], 1j * phase_results[0], rtol=1e-12, atol=1e-14)
    np.testing.assert_allclose(phase_results[2], -phase_results[0], rtol=1e-12, atol=1e-14)
    assert np.any(np.abs(phase_results[0].imag) > 0.0)

    cancelling = ExcitationChannelSet([_channel("positive", 2.0, 1.0, 0.0), _channel("negative", 2.0, -1.0, 0.0)])
    cancelled = solver.solve(
        model,
        source_sha=_SOURCE_SHA,
        prepared=prepared,
        basis=basis,
        excitation_channels=cancelling,
    )
    full_dof_count = sum(len(names) for _, names in prepared.dof_signature)
    np.testing.assert_array_equal(cancelled.responses[0], np.zeros(full_dof_count))
    assert cancelled.solver["frequency_records"][0]["reduced_backward_error"] == 0.0


def test_frequency_specific_channel_sets_support_sweeps_without_operator_reassembly() -> None:
    model = _model(frequencies=[1.0, 3.0], legacy_load=False)
    prepared, basis = _prepare(model)
    first = ExcitationChannelSet([_channel("excitation", 1.0, 1.0, 0.25)])
    second = ExcitationChannelSet([_channel("excitation", 3.0, -0.5, 0.75)])
    result = ReducedHarmonicResponseSolver().solve(
        model,
        source_sha=_SOURCE_SHA,
        prepared=prepared,
        basis=basis,
        excitation_channels={1.0: first, 3.0: second},
    )
    assert result.frequencies_hz.tolist() == [1.0, 3.0]
    assert result.solver["operator_identity"] == prepared.operator_identity
    assert [item["identity"] for item in result.solver["excitation_identity_by_frequency"]] == [
        first.identity,
        second.identity,
    ]
    assert first.identity != second.identity


def test_prescribed_modal_damping_is_reduced_only_and_reactions_are_unavailable() -> None:
    model = _model(
        frequencies=[2.0],
        legacy_load=True,
        extra_parameters={
            "reduced_damping_model": "prescribed_modal",
            "modal_damping_ratios": [0.02, 0.02, 0.02],
        },
    )
    model.analysis.parameters.pop("rayleigh_alpha")
    model.analysis.parameters.pop("rayleigh_beta")
    prepared, basis = _prepare(model)
    result = ReducedHarmonicResponseSolver().solve(
        model,
        source_sha=_SOURCE_SHA,
        prepared=prepared,
        basis=basis,
    )
    assert result.solver["damping"]["source"] == "PRESCRIBED_MODAL_REDUCED_MODEL"
    assert result.solver["damping"]["reaction_availability"] == "UNAVAILABLE"
    assert result.result_availability["physical_reactions"]["status"] == "UNAVAILABLE"
    assert result.result_availability["physical_free_equation_residual"]["status"] == "UNAVAILABLE"
    assert result.result_availability["physical_free_equation_residual"]["reason"]


def test_probe_outputs_are_sparse_in_frequency_and_result_serialization_preserves_complex_values() -> None:
    model = _model(
        frequencies=[1.0, 2.0, 3.0],
        extra_parameters={"response_probes": [{"node": 1, "dof": "UX"}]},
    )
    result = ReducedHarmonicResponseSolver().solve(model, source_sha=_SOURCE_SHA)
    assert all(response.shape == (1,) for response in result.responses)
    assert result.result_availability["complex_displacements"]["status"] == "PARTIALLY_AVAILABLE"
    serialized = result.to_dict()
    restored = ReducedHarmonicResult.from_dict(serialized)
    assert restored.method == "modal_superposition"
    assert restored.execution_key == result.execution_key
    for actual, expected in zip(restored.responses, result.responses, strict=True):
        np.testing.assert_array_equal(actual, expected)
    for row in serialized["raw_complex_response_vectors"]:
        assert set(row) == {"real", "imag"}


def test_basis_reuse_after_load_change_and_stale_operator_rejection() -> None:
    model = _model(frequencies=[1.0], legacy_load=False)
    prepared, basis = _prepare(model)
    solver = ReducedHarmonicResponseSolver()
    first = ExcitationChannelSet([_channel("load", 1.0, 1.0, 0.0)])
    second = ExcitationChannelSet([_channel("load", 1.0, 0.0, 1.0)])
    first_result = solver.solve(
        model,
        source_sha=_SOURCE_SHA,
        prepared=prepared,
        basis=basis,
        excitation_channels=first,
    )
    second_result = solver.solve(
        model,
        source_sha=_SOURCE_SHA,
        prepared=prepared,
        basis=basis,
        excitation_channels=second,
    )
    assert first_result.solver["operator_identity"] == second_result.solver["operator_identity"]
    assert first_result.solver["basis_identity"] == second_result.solver["basis_identity"]
    assert first_result.execution_key != second_result.execution_key

    changed = copy.deepcopy(model)
    changed.nodes[1, 0] += 0.01
    with pytest.raises(InputValidationError, match="do not match"):
        solver.solve(
            changed,
            source_sha=_SOURCE_SHA,
            prepared=prepared,
            basis=basis,
            excitation_channels=first,
        )


@pytest.mark.parametrize("family", ["TET4", "TET10", "HEX8", "HEX20", "BEAM2"])
def test_new_method_runs_on_each_bounded_element_family(family: str) -> None:
    model = _family_model(family)
    prepared = PreparedDynamicSystem.prepare(model, source_sha=_SOURCE_SHA)
    model.analysis.parameters["modal_mode_count"] = prepared.reduced_size
    model.analysis.parameters["modal_extraction_method"] = "dense"
    model.analysis.parameters["modal_dense_limit"] = 128
    result = ReducedHarmonicResponseSolver().solve(
        model,
        source_sha=_SOURCE_SHA,
        prepared=prepared,
    )
    assert result.status == "PASS"
    assert result.solver["modal_mode_count"] == prepared.reduced_size
    assert result.solver["truncation"]["is_full_basis"] is True


def test_method_maturity_and_preflight_are_experimental_without_changing_direct_default() -> None:
    assert AnalysisSettings.from_raw({"type": "harmonic_response"}).method == "direct_frequency"
    reduced = _model(frequencies=[1.0])
    maturity = model_maturity(reduced)
    assert maturity["method"] == "experimental"
    assert maturity["overall"] == "experimental"
    report = preflight_model(reduced)
    assert report.status == "EXPERIMENTAL_ROUTE"
    assert all(row.formulation_or_route == "modal_superposition" for row in report.results)


def test_public_router_dispatches_modal_superposition_to_experimental_result(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QF_SOURCE_SHA", _SOURCE_SHA)
    model = _model(frequencies=[1.0])
    result = solve_model(model)

    assert isinstance(result, ReducedHarmonicResult)
    assert result.method == "modal_superposition"
    assert result.maturity == "EXPERIMENTAL"
    assert result.numerical_status == "PASS"
    assert result.run_verdict.value == "WARNING"


def test_explicit_phasors_reject_legacy_loads_and_direct_method_remains_available() -> None:
    mixed = _model(frequencies=[1.0], legacy_load=True)
    prepared, basis = _prepare(mixed)
    with pytest.raises(InputValidationError, match="cannot be combined"):
        ReducedHarmonicResponseSolver().solve(
            mixed,
            source_sha=_SOURCE_SHA,
            prepared=prepared,
            basis=basis,
            excitation_channels=ExcitationChannelSet([_channel("new", 1.0, 1.0, 0.0)]),
        )

    direct = copy.deepcopy(mixed)
    direct.analysis = AnalysisSettings.from_raw({"type": "harmonic_response", "frequencies_hz": [1.0]})
    result = solve_model(direct)
    assert result.method == "direct_frequency"
    assert result.status == "PASS"


def _family_model(family: str) -> FiniteElementModel:
    if family == "TET4":
        nodes = [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]]
        connectivity = list(range(4))
        fixed_nodes = [0, 2, 3]
    elif family == "TET10":
        nodes = [
            [0, 0, 0],
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 1],
            [0.5, 0, 0],
            [0.5, 0.5, 0],
            [0, 0.5, 0],
            [0, 0, 0.5],
            [0.5, 0, 0.5],
            [0, 0.5, 0.5],
        ]
        connectivity = list(range(10))
        fixed_nodes = [0, 2, 3, 6, 7, 9]
    elif family in {"HEX8", "HEX20"}:
        corners = np.asarray(
            [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]],
            dtype=float,
        )
        if family == "HEX8":
            nodes = corners.tolist()
            connectivity = list(range(8))
            fixed_nodes = [0, 3, 4, 7]
        else:
            edges = (
                (0, 1),
                (0, 3),
                (0, 4),
                (1, 2),
                (1, 5),
                (2, 3),
                (2, 6),
                (3, 7),
                (4, 5),
                (4, 7),
                (5, 6),
                (6, 7),
            )
            nodes = np.vstack([corners, [(corners[a] + corners[b]) / 2.0 for a, b in edges]]).tolist()
            connectivity = list(range(20))
            fixed_nodes = [0, 3, 4, 7, 9, 10, 15, 17]
    elif family == "BEAM2":
        nodes = [[0, 0, 0], [1, 0, 0]]
        connectivity = [0, 1]
        fixed_nodes = [0]
    else:
        raise AssertionError(family)

    beam = family == "BEAM2"
    material = (
        {
            "type": "beam_isotropic",
            "E": 210.0e9,
            "nu": 0.3,
            "A": 0.01,
            "Iy": 1.0e-5,
            "Iz": 1.0e-5,
            "J": 2.0e-5,
            "density": 7800.0,
        }
        if beam
        else {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3, "density": 7800.0}
    )
    fixed_dofs = [
        {"node": node, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"] if beam else ["UX", "UY", "UZ"]}
        for node in fixed_nodes
    ]
    return FiniteElementModel.from_raw(
        analysis={
            "type": "harmonic_response",
            "method": "modal_superposition",
            "frequencies_hz": [0.0],
            "modal_mode_count": 1,
            "modal_extraction_method": "dense",
            "modal_dense_limit": 128,
        },
        nodes=nodes,
        elements=[{"type": family, "nodes": connectivity, "material": "mat"}],
        materials={"mat": material},
        fixed_dofs=fixed_dofs,
    )
