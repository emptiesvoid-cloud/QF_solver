from __future__ import annotations

import copy
import json
import math
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from scipy.linalg import eigh

from solveur.api import solve_model
from solveur.core.analyses.excitation_channels import (
    ExcitationChannel,
    ExcitationChannelSet,
    SpatialDofWeight,
    TimeSample,
)
from solveur.core.analyses.modal_basis import ModalBasis
from solveur.core.analyses.modal_newmark import ModalNewmarkTransientSolver
from solveur.core.analyses.prepared_dynamic_system import PreparedDynamicSystem
from solveur.core.errors import InputValidationError
from solveur.core.model import FiniteElementModel
from solveur.core.qualification import model_maturity
from solveur.core.results import ModalNewmarkResult


_SOURCE_SHA = "a" * 40


def _model(
    *,
    family: str = "BEAM2",
    dt: float = 0.001,
    steps: int = 100,
    load: float | None = None,
    mode_count: int | None = 1,
    extra_parameters: dict[str, object] | None = None,
) -> FiniteElementModel:
    if family == "BEAM2":
        nodes = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]
        connectivity = [0, 1]
        fixed = [
            {"node": 0, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]},
            {"node": 1, "dofs": ["UY", "UZ", "RX", "RY", "RZ"]},
        ]
        material = {
            "type": "beam_isotropic",
            "E": 1000.0,
            "nu": 0.25,
            "A": 1.0,
            "Iy": 0.1,
            "Iz": 0.1,
            "J": 0.2,
            "density": 1.0,
        }
        load_node = 1
    elif family == "TET4":
        nodes = [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]]
        connectivity = list(range(4))
        fixed = [{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in [0, 2, 3]]
        material = {"type": "isotropic_3d", "E": 1000.0, "nu": 0.25, "density": 1.0}
        load_node = 1
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
        fixed = [{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in [0, 2, 3, 6, 7, 9]]
        material = {"type": "isotropic_3d", "E": 1000.0, "nu": 0.25, "density": 1.0}
        load_node = 1
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
            nodes = np.vstack([corners, [(corners[a] + corners[b]) / 2 for a, b in edges]]).tolist()
            connectivity = list(range(20))
            fixed_nodes = [0, 3, 4, 7, 9, 10, 15, 17]
        fixed = [{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in fixed_nodes]
        material = {"type": "isotropic_3d", "E": 1000.0, "nu": 0.25, "density": 1.0}
        load_node = 1
    else:
        raise AssertionError(family)

    parameters: dict[str, object] = {
        "time_step": dt,
        "steps": steps,
        "newmark_beta": 0.25,
        "newmark_gamma": 0.5,
        "modal_extraction_method": "dense",
        "modal_dense_limit": 256,
        "rayleigh_alpha": 0.0,
        "rayleigh_beta": 0.0,
        "record_time_history": False,
    }
    if mode_count is not None:
        parameters["modal_mode_count"] = mode_count
    parameters.update(extra_parameters or {})
    return FiniteElementModel.from_raw(
        analysis={"type": "transient_dynamic", "method": "modal_newmark", **parameters},
        nodes=nodes,
        elements=[{"type": family, "nodes": connectivity, "material": "mat"}],
        materials={"mat": material},
        fixed_dofs=fixed,
        loads=[] if load is None else [{"node": load_node, "dof": "UX", "value": load}],
    )


def _prepared_basis(model: FiniteElementModel) -> tuple[PreparedDynamicSystem, ModalBasis]:
    prepared = PreparedDynamicSystem.prepare(model, source_sha=_SOURCE_SHA)
    count = model.analysis.parameters.get("modal_mode_count")
    if count is None:
        count = prepared.reduced_size
    basis = ModalBasis.from_prepared(
        prepared,
        mode_count=int(count),
        method="dense",
        dense_limit=256,
    )
    return prepared, basis


def _channel(
    channel_id: str, node: int, amplitude: float, *, history: tuple[TimeSample, ...] = ()
) -> ExcitationChannel:
    return ExcitationChannel(
        channel_id=channel_id,
        spatial_distribution=(SpatialDofWeight(node, "UX", 1.0),),
        spatial_units="N",
        amplitude_units="N",
        result_units="N",
        frame_convention="global_model_frame",
        sign_convention="positive_along_named_global_dof",
        constant_amplitude=amplitude if not history else None,
        time_history=history,
        provenance=(("fixture", "wp06-unit-test"),),
    )


def _run(model: FiniteElementModel, **kwargs: object) -> ModalNewmarkResult:
    return ModalNewmarkTransientSolver().solve(model, source_sha=_SOURCE_SHA, **kwargs)


def test_sdof_free_undamped_matches_analytic_solution_and_initial_projection() -> None:
    amplitude = 2.0e-3
    model = _model(
        steps=80,
        dt=0.00005,
        extra_parameters={
            "initial_displacements": [{"node": 1, "dof": "UX", "value": amplitude}],
            "initial_velocities": [{"node": 1, "dof": "UX", "value": 0.0}],
            "store_modal_history": True,
        },
    )
    prepared, basis = _prepared_basis(model)
    mass = float(prepared.mass[0, 0])
    stiffness = float(prepared.stiffness[0, 0])
    omega = math.sqrt(stiffness / mass)
    result = _run(model, prepared=prepared, basis=basis)
    index = model.dof_manager().index(1, "UX")
    exact = amplitude * math.cos(omega * result.times[-1])
    assert result.displacements[index] == pytest.approx(exact, rel=2.0e-4, abs=1.0e-9)
    assert result.solver["integration"]["initial_projection"]["displacement_relative_mass_error"] < 1.0e-12
    assert result.solver["reduced_equilibrium_diagnostics"]["maximum_relative_error"] < 1.0e-7
    assert result.modal_history[0]["qddot"][0] == pytest.approx(-(omega**2) * result.modal_history[0]["q"][0])
    assert result.maturity == "EXPERIMENTAL"


def test_sdof_free_damped_matches_under_damped_analytic_solution() -> None:
    amplitude = 1.0e-3
    alpha = 0.4
    model = _model(
        dt=0.00005,
        steps=800,
        extra_parameters={
            "rayleigh_alpha": alpha,
            "initial_displacements": [{"node": 1, "dof": "UX", "value": amplitude}],
            "initial_velocities": [{"node": 1, "dof": "UX", "value": 0.0}],
        },
    )
    prepared, basis = _prepared_basis(model)
    mass = float(prepared.mass[0, 0])
    stiffness = float(prepared.stiffness[0, 0])
    omega_n = math.sqrt(stiffness / mass)
    zeta = alpha / (2.0 * omega_n)
    omega_d = omega_n * math.sqrt(1.0 - zeta**2)
    result = _run(model, prepared=prepared, basis=basis)
    index = model.dof_manager().index(1, "UX")
    time = result.times[-1]
    exact = (
        amplitude
        * math.exp(-zeta * omega_n * time)
        * (math.cos(omega_d * time) + zeta * omega_n / omega_d * math.sin(omega_d * time))
    )
    assert result.displacements[index] == pytest.approx(exact, rel=2.0e-4, abs=1.0e-9)
    assert result.solver["damping"]["physical_full_space_C"] is True


def test_constant_force_transient_matches_sdof_analytic_solution() -> None:
    force = 0.5
    model = _model(load=force, dt=0.0005, steps=80)
    prepared, basis = _prepared_basis(model)
    mass = float(prepared.mass[0, 0])
    stiffness = float(prepared.stiffness[0, 0])
    omega = math.sqrt(stiffness / mass)
    result = _run(model, prepared=prepared, basis=basis)
    index = model.dof_manager().index(1, "UX")
    exact = force / stiffness * (1.0 - math.cos(omega * result.times[-1]))
    assert result.displacements[index] == pytest.approx(exact, rel=3.0e-4, abs=1.0e-9)
    assert result.solver["operators"]["factorization_count"] == 1
    assert result.solver["operators"]["factorization_solve_count"] == model.analysis.parameters["steps"]


def test_sinusoidal_force_matches_independent_sdof_transient_reference() -> None:
    force = 0.5
    frequency_hz = 5.0
    model = _model(
        dt=0.00005,
        steps=800,
        load=force,
        extra_parameters={"load_function": "sine", "load_frequency_hz": frequency_hz},
    )
    prepared, basis = _prepared_basis(model)
    mass = float(prepared.mass[0, 0])
    stiffness = float(prepared.stiffness[0, 0])
    omega_n = math.sqrt(stiffness / mass)
    omega_f = 2.0 * math.pi * frequency_hz
    result = _run(model, prepared=prepared, basis=basis)
    time = result.times[-1]
    exact = (
        force
        / (mass * (omega_n**2 - omega_f**2))
        * (math.sin(omega_f * time) - omega_f / omega_n * math.sin(omega_n * time))
    )
    index = model.dof_manager().index(1, "UX")
    assert result.displacements[index] == pytest.approx(exact, rel=5e-4, abs=1e-9)


def test_full_basis_matches_direct_newmark_when_damping_and_excitation_match() -> None:
    model = _model(family="TET4", mode_count=None, load=0.25, dt=0.002, steps=8)
    model.analysis.parameters["rayleigh_alpha"] = 0.02
    prepared, basis = _prepared_basis(model)
    modal = _run(model, prepared=prepared, basis=basis)
    direct_model = copy.deepcopy(model)
    direct_model.analysis = replace(direct_model.analysis, method="newmark")
    direct = solve_model(direct_model)
    assert basis.is_full_basis
    np.testing.assert_allclose(modal.displacements, direct.displacements, rtol=1e-8, atol=1e-10)
    np.testing.assert_allclose(modal.velocities, direct.velocities, rtol=1e-8, atol=1e-10)
    np.testing.assert_allclose(modal.accelerations, direct.accelerations, rtol=1e-8, atol=1e-10)
    assert modal.solver["physical_free_relative_error"] <= 1e-7


def test_coupled_tet4_full_basis_matches_independent_eigen_expansion() -> None:
    model = _model(
        family="TET4",
        mode_count=None,
        dt=1.0e-5,
        steps=1500,
        extra_parameters={
            "initial_displacements": [{"node": 1, "dof": "UX", "value": 1.0e-4}],
            "initial_velocities": [{"node": 1, "dof": "UY", "value": -2.0e-4}],
        },
    )
    prepared, basis = _prepared_basis(model)
    mass = prepared.mass.toarray()
    stiffness = prepared.stiffness.toarray()
    eigenvalues, vectors = eigh(stiffness, mass)
    np.testing.assert_allclose(eigenvalues, basis.eigenvalues, rtol=1e-10, atol=1e-10)
    u0_full = np.zeros(model.dof_manager().ndof)
    v0_full = np.zeros_like(u0_full)
    u0_full[model.dof_manager().index(1, "UX")] = 1.0e-4
    v0_full[model.dof_manager().index(1, "UY")] = -2.0e-4
    u0 = prepared.reduce_state(u0_full)
    v0 = prepared.reduce_state(v0_full)
    q0 = vectors.T @ mass @ u0
    qdot0 = vectors.T @ mass @ v0
    t = model.analysis.parameters["time_step"] * model.analysis.parameters["steps"]
    omega = np.sqrt(eigenvalues)
    expected = vectors @ (q0 * np.cos(omega * t) + qdot0 / omega * np.sin(omega * t))
    result = _run(model, prepared=prepared, basis=basis)
    np.testing.assert_allclose(prepared.reduce_state(result.displacements), expected, rtol=3e-4, atol=1e-9)


def test_initial_state_outside_truncated_subspace_is_reported_and_can_be_rejected() -> None:
    model = _model(
        family="TET4",
        mode_count=2,
        steps=2,
        extra_parameters={
            "initial_displacements": [{"node": 1, "dof": "UY", "value": 1.0e-3}],
        },
    )
    prepared, basis = _prepared_basis(model)
    result = _run(model, prepared=prepared, basis=basis)
    projection_error = result.solver["integration"]["initial_projection"]["displacement_relative_mass_error"]
    assert projection_error >= 0.0
    assert result.solver["integration"]["initial_projection"]["exact_reconstruction_claim"] is False

    rejecting = copy.deepcopy(model)
    rejecting.analysis.parameters["modal_initial_projection_policy"] = "reject_incompatible"
    reject_prepared, reject_basis = _prepared_basis(rejecting)
    if projection_error > 1.0e-10:
        with pytest.raises(InputValidationError, match="component outside"):
            _run(rejecting, prepared=reject_prepared, basis=reject_basis)


def test_explicit_multichannel_histories_superpose_and_phasors_are_not_coerced() -> None:
    model = _model(load=None, steps=4, dt=0.01)
    prepared, basis = _prepared_basis(model)
    channels = ExcitationChannelSet(
        (
            _channel("load-a", 1, 1.5),
            _channel("load-b", 1, -0.5),
            _channel("history", 1, 0.0, history=(TimeSample(0.0, 0.0), TimeSample(0.04, 2.0))),
        )
    )
    bound = channels.bind(prepared)
    full_dofs = model.dof_manager()
    force_index = full_dofs.index(1, "UX")
    force_at_start = bound.full_real_rhs(prepared, time_s=0.0, dt=0.01)
    force_at_midpoint = bound.full_real_rhs(prepared, time_s=0.02, dt=0.01)
    assert force_at_start[force_index] == pytest.approx(1.0)
    assert force_at_midpoint[force_index] == pytest.approx(2.0)
    result = _run(model, prepared=prepared, basis=basis, excitation_channels=channels)
    assert np.any(result.displacements != 0.0)

    from solveur.core.analyses.excitation_channels import ComplexPhasor, HarmonicAmplitude

    harmonic = ExcitationChannel(
        channel_id="phasor",
        spatial_distribution=(SpatialDofWeight(1, "UX", 1.0),),
        spatial_units="N",
        amplitude_units="N",
        result_units="N",
        frame_convention="global_model_frame",
        sign_convention="positive_along_named_global_dof",
        constant_amplitude=None,
        harmonic=HarmonicAmplitude(1.0, ComplexPhasor(0.0, 1.0)),
    )
    with pytest.raises(InputValidationError, match="Harmonic phasors"):
        _run(model, prepared=prepared, basis=basis, excitation_channels=ExcitationChannelSet((harmonic,)))


def test_changing_excitation_reuses_same_prepared_operators_and_basis() -> None:
    model = _model(load=None, dt=0.001, steps=20)
    prepared, basis = _prepared_basis(model)
    first = ExcitationChannelSet((_channel("drive", 1, 1.0),))
    second = ExcitationChannelSet((_channel("drive", 1, 2.0),))
    first_result = _run(model, prepared=prepared, basis=basis, excitation_channels=first)
    second_result = _run(model, prepared=prepared, basis=basis, excitation_channels=second)
    assert first_result.execution_identity["operator_identity"] == second_result.execution_identity["operator_identity"]
    assert first_result.execution_identity["basis_identity"] == second_result.execution_identity["basis_identity"]
    assert (
        first_result.execution_identity["excitation_identity"]
        != second_result.execution_identity["excitation_identity"]
    )
    assert not np.array_equal(first_result.displacements, second_result.displacements)


def test_prescribed_modal_damping_never_claims_physical_reactions() -> None:
    model = _model(
        extra_parameters={
            "reduced_damping_model": "prescribed_modal",
            "modal_damping_ratios": [0.02],
        }
    )
    model.analysis.parameters.pop("rayleigh_alpha")
    model.analysis.parameters.pop("rayleigh_beta")
    result = _run(model)
    assert result.reactions is None
    assert result.result_availability["physical_reactions"]["status"] == "UNAVAILABLE"
    assert result.solver["damping"]["physical_full_space_C"] is False


def test_restart_matches_continuous_run_and_refuses_corrupt_or_incompatible_checkpoint(tmp_path) -> None:
    checkpoint = tmp_path / "modal-state.npz"
    model = _model(
        load=0.1,
        steps=12,
        extra_parameters={
            "checkpoint_path": str(checkpoint),
            "checkpoint_interval": 4,
            "checkpoint_keep_steps": True,
            "record_time_history": True,
        },
    )
    complete = _run(model)
    intermediate = tmp_path / "modal-state.step00000004.npz"
    assert intermediate.is_file()
    restarted_model = _model(
        load=0.1,
        steps=12,
        extra_parameters={
            "restart_from": str(intermediate),
            "record_time_history": True,
        },
    )
    restarted = _run(restarted_model)
    np.testing.assert_allclose(restarted.displacements, complete.displacements, rtol=1e-12, atol=1e-14)
    np.testing.assert_allclose(restarted.velocities, complete.velocities, rtol=1e-12, atol=1e-14)
    np.testing.assert_allclose(restarted.accelerations, complete.accelerations, rtol=1e-12, atol=1e-14)
    assert restarted.solver["restart"]["used"] is True

    changed = _model(load=0.1, steps=12, extra_parameters={"restart_from": str(intermediate)})
    changed.materials["mat"]["density"] = 2.0
    with pytest.raises(InputValidationError, match="restart is refused"):
        _run(changed)

    corrupt = tmp_path / "corrupt.npz"
    corrupt.write_bytes(b"not an npz")
    corrupt_model = _model(load=0.1, steps=12, extra_parameters={"restart_from": str(corrupt)})
    with pytest.raises(InputValidationError, match="corrupted NPZ"):
        _run(corrupt_model)

    with np.load(intermediate, allow_pickle=False) as saved:
        payload = {name: saved[name] for name in saved.files}
    payload["coordinates"] = payload["coordinates"] + 1.0
    tampered = tmp_path / "tampered.npz"
    np.savez_compressed(tampered, **payload)
    tampered_model = _model(load=0.1, steps=12, extra_parameters={"restart_from": str(tampered)})
    with pytest.raises(InputValidationError, match="content hash"):
        _run(tampered_model)


def test_result_round_trip_experimental_maturity_and_bounded_history_availability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("QF_SOURCE_SHA", _SOURCE_SHA)
    model = _model(
        load=0.2,
        steps=5,
        extra_parameters={
            "record_time_history": True,
            "history_probes": [{"node": 1, "dof": "UX", "label": "tip"}],
            "store_modal_history": True,
        },
    )
    result = solve_model(model)
    assert isinstance(result, ModalNewmarkResult)
    restored = ModalNewmarkResult.from_dict(result.to_dict())
    assert restored.maturity == "EXPERIMENTAL"
    assert restored.method == "modal_newmark"
    np.testing.assert_array_equal(restored.displacements, result.displacements)
    np.testing.assert_array_equal(restored.modal_accelerations, result.modal_accelerations)
    assert restored.result_availability["full_physical_state_history"]["status"] == "UNAVAILABLE"
    assert restored.result_availability["requested_probe_history"]["status"] == "AVAILABLE"
    assert len(restored.time_history) == 6
    assert len(restored.modal_history) == 6


@pytest.mark.parametrize("family", ["TET4", "TET10", "HEX8", "HEX20", "BEAM2"])
def test_modal_newmark_integrates_each_wp00_family_in_bounded_full_basis(family: str) -> None:
    model = _model(family=family, mode_count=None, load=0.01, dt=1e-5, steps=1)
    prepared, basis = _prepared_basis(model)
    result = _run(model, prepared=prepared, basis=basis)
    assert basis.is_full_basis
    assert result.solver["operators"]["Mr_shape"] == [basis.mode_count, basis.mode_count]
    assert result.solver["timing_seconds"]["integration"] >= 0.0
    assert result.ndof == model.dof_manager().ndof


def test_modal_method_identity_is_additive_and_direct_default_is_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QF_SOURCE_SHA", _SOURCE_SHA)
    model = _model(load=0.1, steps=2)
    assert model.analysis.method == "modal_newmark"
    direct = copy.deepcopy(model)
    direct.analysis = replace(direct.analysis, method="newmark")
    assert solve_model(direct).solver["method"] == "newmark"
    modal = solve_model(model)
    assert modal.method == "modal_newmark"
    assert modal.maturity == "EXPERIMENTAL"
    assert modal.qualification_scope_id != ""
    assert model_maturity(model)["method"] == "experimental"
    assert modal.to_dict()["qualification_decision"] == "NOT_ASSESSED"


def test_zero_excitation_keeps_zero_response_and_reduced_outputs_are_not_overclaimed() -> None:
    model = _model(load=None, steps=4)
    result = _run(model)
    np.testing.assert_array_equal(result.displacements, np.zeros(result.ndof))
    np.testing.assert_array_equal(result.velocities, np.zeros(result.ndof))
    np.testing.assert_array_equal(result.accelerations, np.zeros(result.ndof))
    assert result.result_availability["physical_truncation_error"]["status"] == "UNAVAILABLE"
    assert result.result_availability["full_physical_state_history"]["status"] == "UNAVAILABLE"


def test_second_order_time_refinement_for_smooth_free_vibration() -> None:
    q0 = 1.0e-3
    errors: list[float] = []
    for dt in (0.002, 0.001, 0.0005):
        model = _model(
            dt=dt,
            steps=40,
            extra_parameters={
                "initial_displacements": [{"node": 1, "dof": "UX", "value": q0}],
            },
        )
        prepared, basis = _prepared_basis(model)
        result = _run(model, prepared=prepared, basis=basis)
        omega = math.sqrt(float(prepared.stiffness[0, 0] / prepared.mass[0, 0]))
        exact = q0 * math.cos(omega * result.times[-1])
        index = model.dof_manager().index(1, "UX")
        errors.append(abs(result.displacements[index] - exact))
    observed_order = math.log(errors[0] / errors[1], 2.0)
    assert observed_order >= 1.8
    assert errors[2] < errors[1] < errors[0]


def test_modal_newmark_rejects_unsupported_base_motion_and_conflicting_legacy_loads() -> None:
    base_motion = _model(extra_parameters={"base_acceleration": [0.0, 1.0]})
    with pytest.raises(InputValidationError, match="base or moving-support"):
        _run(base_motion)

    model = _model(load=1.0)
    prepared, basis = _prepared_basis(model)
    explicit = ExcitationChannelSet((_channel("new", 1, 1.0),))
    with pytest.raises(InputValidationError, match="cannot be combined"):
        _run(model, prepared=prepared, basis=basis, excitation_channels=explicit)


def test_modal_newmark_rejects_stale_prepared_system_or_basis() -> None:
    model = _model()
    prepared, basis = _prepared_basis(model)
    changed = copy.deepcopy(model)
    changed.materials["mat"]["E"] *= 1.01
    with pytest.raises(InputValidationError, match="do not match the current physical model"):
        _run(changed, prepared=prepared, basis=basis)


def test_damping_modal_history_and_energy_diagnostics_are_explicit() -> None:
    model = _model(
        steps=8,
        extra_parameters={
            "initial_displacements": [{"node": 1, "dof": "UX", "value": 0.001}],
            "record_time_history": True,
        },
    )
    result = _run(model)
    energies = [row["total_energy"] for row in result.time_history]
    assert max(energies) - min(energies) < 1e-10
    assert result.solver["truncation"]["low_reduced_residual_is_physical_accuracy_claim"] is False


def test_damped_unforced_energy_does_not_increase() -> None:
    model = _model(
        steps=100,
        dt=0.0005,
        extra_parameters={
            "rayleigh_alpha": 0.5,
            "initial_displacements": [{"node": 1, "dof": "UX", "value": 0.001}],
            "record_time_history": True,
        },
    )
    result = _run(model)
    energies = np.asarray([row["total_energy"] for row in result.time_history])
    assert np.all(np.diff(energies) <= 1e-12)


def test_wp06_numerical_thresholds_are_preregistered_and_not_relaxed() -> None:
    contract_path = Path(__file__).parents[2] / "qualification" / "0_2_12" / "wp06_modal_newmark_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    thresholds = contract["preregistered_tolerances"]
    assert contract["status"] == "THRESHOLDS_FROZEN_BEFORE_FINAL_QUALIFICATION_CAMPAIGN"
    assert thresholds["post_observation_relaxation"] is False
    assert thresholds["dt_refinement_observed_order_minimum"] == 1.8
    assert thresholds["full_basis_direct_final_state_relative_difference_max"] == 1e-8


def test_result_rejects_complex_values_in_real_time_state() -> None:
    from dataclasses import replace

    model = _model(steps=1)
    result = _run(model)
    complex_state = result.displacements.astype(np.complex128) + 1j
    with pytest.raises(ValueError, match="must not contain complex values"):
        replace(result, displacements=complex_state)
