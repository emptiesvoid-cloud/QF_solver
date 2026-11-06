from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from scipy.sparse import csr_matrix, eye

from solveur.core.analyses.excitation_channels import (
    ComplexPhasor,
    ExcitationChannel,
    ExcitationChannelSet,
    HarmonicAmplitude,
    SpatialDofWeight,
)
from solveur.core.analyses.modal import ModalAnalysisSolver
from solveur.core.analyses.modal_basis import ModalBasis
from solveur.core.analyses.modal_newmark import ModalNewmarkTransientSolver
from solveur.core.analyses.modal_newmark_checkpoint import NpzModalNewmarkCheckpointStore
from solveur.core.analyses.prepared_dynamic_system import PreparedDynamicSystem
from solveur.core.analyses.reduced_harmonic import ReducedHarmonicResponseSolver
from solveur.core.analyses.settings import AnalysisSettings
from solveur.core.dofs import DofManager
from solveur.core.errors import InputValidationError, ModalResidualValidationError
from solveur.core.model import FiniteElementModel
from solveur.core.results import ModalNewmarkResult, ReducedHarmonicResult
from solveur.mesh.validation import MeshReport


_SOURCE_SHA = "a" * 40


class _IdentityReducer:
    def __init__(self, stiffness: csr_matrix, mass: csr_matrix) -> None:
        self.stiffness = stiffness
        self.mass = mass
        self.full_size = int(stiffness.shape[0])
        self.free = np.arange(self.full_size, dtype=int)
        self.transform = eye(self.full_size, format="csr", dtype=np.float64)

    @property
    def reduced_size(self) -> int:
        return self.full_size

    def reduce_state(self, vector: np.ndarray) -> np.ndarray:
        return np.asarray(vector, dtype=np.float64).copy()

    def reduce_load(self, vector: np.ndarray) -> np.ndarray:
        return np.asarray(vector).copy()

    def expand_state(self, vector: np.ndarray, full_load: np.ndarray | None = None) -> np.ndarray:
        del full_load
        return np.asarray(vector, dtype=np.float64).copy()

    def expand_complex_state(
        self,
        vector: np.ndarray,
        full_load: np.ndarray | None = None,
        *,
        stiffness_factor: complex = 1.0 + 0.0j,
    ) -> np.ndarray:
        del full_load, stiffness_factor
        return np.asarray(vector, dtype=np.complex128).copy()


class _RecordingCheckpointStore(NpzModalNewmarkCheckpointStore):
    def __init__(self) -> None:
        self.signature_payload: dict[str, object] | None = None

    def signature(self, payload: dict[str, object]) -> str:
        self.signature_payload = dict(payload)
        return super().signature(payload)


def _banded_spd(size: int, *, scale: float, off1: float, off2: float) -> csr_matrix:
    diagonal = scale * (1.0 + np.arange(size, dtype=np.float64) / (size * 10.0))
    matrix = np.diag(diagonal)
    for offset, value in ((1, off1), (2, off2)):
        indices = np.arange(size - offset)
        matrix[indices, indices + offset] = value
        matrix[indices + offset, indices] = value
    return csr_matrix(matrix)


def _synthetic_system(
    size: int,
    analysis_type: str,
    method: str,
    parameters: dict[str, object],
    *,
    banded: bool = False,
) -> tuple[FiniteElementModel, PreparedDynamicSystem, csr_matrix, csr_matrix]:
    if banded:
        stiffness = _banded_spd(size, scale=8.0, off1=0.02, off2=-0.007)
        mass = _banded_spd(size, scale=1.0, off1=0.001, off2=-0.0003)
    else:
        values = np.arange(size, dtype=np.float64)
        stiffness = csr_matrix(np.diag(4.0 + values * 0.25))
        mass = eye(size, format="csr", dtype=np.float64)
        if size == 2:
            stiffness = csr_matrix([[4.0, 0.5], [0.5, 7.0]])
            mass = csr_matrix([[1.0, 0.1], [0.1, 2.0]])

    analysis = AnalysisSettings.from_raw(
        {"type": analysis_type, "method": method, **parameters}
    )
    nodes = np.column_stack(
        (np.arange(size, dtype=np.float64), np.zeros(size, dtype=np.float64), np.zeros(size, dtype=np.float64))
    )
    model = FiniteElementModel(nodes=nodes, elements=[], materials={}, analysis=analysis)
    dofs = DofManager.from_node_requirements({index: {"UX"} for index in range(size)})
    reducer = _IdentityReducer(stiffness, mass)
    prepared = PreparedDynamicSystem(
        model_snapshot=model,
        dofs=dofs,
        plan=SimpleNamespace(fingerprint=f"synthetic-plan-{size}", chunk_size=256),
        reducer=reducer,  # type: ignore[arg-type]
        source_sha=_SOURCE_SHA,
        assembler_default_chunk_size=256,
        stiffness_full=stiffness,
        mass_full=mass,
        physical_identity=f"synthetic-physical-{size}",
        operator_identity=f"synthetic-operator-{size}",
        excitation_identity=f"synthetic-excitation-{size}",
        identity_document="{}",
        assembly_diagnostics={"source": "algebraic-test-fixture", "assembly_performed": False},
    )
    prepared.require_compatible = lambda candidate: None  # type: ignore[method-assign]
    return model, prepared, stiffness, mass


def _basis(
    prepared: PreparedDynamicSystem,
    *,
    count: int,
    policy: str,
) -> ModalBasis:
    return ModalBasis.from_prepared(
        prepared,
        mode_count=count,
        method="dense",
        dense_limit=max(200, prepared.reduced_size),
        validation_policy=policy,
    )


def _harmonic_channel(frequency_hz: float = 0.07) -> ExcitationChannelSet:
    channel = ExcitationChannel(
        channel_id="synthetic-harmonic-force",
        spatial_distribution=(SpatialDofWeight(0, "UX", 1.0),),
        spatial_units="N",
        amplitude_units="N",
        result_units="N",
        frame_convention="global_model_frame",
        sign_convention="positive_along_named_global_dof",
        constant_amplitude=None,
        harmonic=HarmonicAmplitude(frequency_hz, ComplexPhasor(1.0, 0.25)),
    )
    return ExcitationChannelSet((channel,))


def _mesh_pass(solver: object) -> None:
    solver.mesh_validator.validate = lambda model: MeshReport("PASS")  # type: ignore[attr-defined]


def _independent_newmark(
    mass: np.ndarray,
    stiffness: np.ndarray,
    displacement: np.ndarray,
    velocity: np.ndarray,
    *,
    dt: float,
    steps: int,
    beta: float,
    gamma: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Small independent textbook Newmark recurrence for the synthetic oracle."""
    q = np.asarray(displacement, dtype=np.float64).copy()
    qdot = np.asarray(velocity, dtype=np.float64).copy()
    qddot = np.linalg.solve(mass, -(stiffness @ q))
    coordinates = [q.copy()]
    velocities = [qdot.copy()]
    accelerations = [qddot.copy()]
    effective = stiffness + mass / (beta * dt * dt)
    for _ in range(steps):
        rhs = mass @ (
            q / (beta * dt * dt)
            + qdot / (beta * dt)
            + (1.0 / (2.0 * beta) - 1.0) * qddot
        )
        next_q = np.linalg.solve(effective, rhs)
        next_qddot = (
            (next_q - q) / (beta * dt * dt)
            - qdot / (beta * dt)
            - (1.0 / (2.0 * beta) - 1.0) * qddot
        )
        next_qdot = qdot + dt * ((1.0 - gamma) * qddot + gamma * next_qddot)
        q, qdot, qddot = next_q, next_qdot, next_qddot
        coordinates.append(q.copy())
        velocities.append(qdot.copy())
        accelerations.append(qddot.copy())
    return np.asarray(coordinates), np.asarray(velocities), np.asarray(accelerations)


def test_reduced_harmonic_certified_and_inconclusive_paths_match_full_algebraic_reference() -> None:
    cases = ((2, 2, "strict", "PASS_CERTIFIED"), (132, 6, "allow_inconclusive", "INCONCLUSIVE"))
    for size, count, policy, expected_validation in cases:
        model, prepared, stiffness, mass = _synthetic_system(
            size,
            "harmonic_response",
            "modal_superposition",
            {
                "frequencies_hz": [0.07],
                "modal_mode_count": count,
                "modal_extraction_method": "dense",
                "modal_validation_policy": policy,
                "rayleigh_alpha": 0.03,
                "rayleigh_beta": 0.002,
            },
        )
        basis = _basis(prepared, count=count, policy=policy)
        assert basis.validation_status == expected_validation
        solver = ReducedHarmonicResponseSolver()
        _mesh_pass(solver)
        channel = _harmonic_channel()
        result = solver.solve(
            model,
            prepared=prepared,
            excitation_channels=channel,
        )

        omega = 2.0 * np.pi * 0.07
        alpha, rayleigh_beta = 0.03, 0.002
        damping = alpha * mass.toarray() + rayleigh_beta * stiffness.toarray()
        operator = stiffness.toarray() - omega**2 * mass.toarray() + 1j * omega * damping
        force = np.zeros(size, dtype=np.complex128)
        force[0] = 1.0 + 0.25j
        reference = np.linalg.solve(operator, force)
        np.testing.assert_allclose(result.responses[0], reference, rtol=2e-10, atol=2e-12)
        expected_result_status = "PASS" if expected_validation == "PASS_CERTIFIED" else "INCONCLUSIVE"
        assert result.numerical_status == expected_result_status
        payload = result.to_dict()
        assert payload["run_verdict"] == "WARNING"
        assert payload["qualification_decision"] == "NOT_ASSESSED"
        assert payload["result_availability"]["modal_basis_validation"]["status"] == expected_validation
        assert payload["result_availability"]["modal_basis_validation"]["usable_as_certified_evidence"] is (
            expected_validation == "PASS_CERTIFIED"
        )
        assert payload["solver"]["modal_basis_validation_status"] == expected_validation
        assert payload["solver"]["modal_basis_use_policy"] == basis.use_policy
        json.dumps(payload, allow_nan=False)
        restored = ReducedHarmonicResult.from_dict(payload)
        assert restored.numerical_status == expected_result_status
        assert restored.to_dict()["result_availability"]["modal_basis_validation"] == payload[
            "result_availability"
        ]["modal_basis_validation"]


def test_reduced_harmonic_refuses_inconclusive_in_strict_mode() -> None:
    model, prepared, _, _ = _synthetic_system(
        132,
        "harmonic_response",
        "modal_superposition",
        {
            "frequencies_hz": [0.07],
            "modal_mode_count": 6,
            "modal_extraction_method": "dense",
            "rayleigh_alpha": 0.03,
            "rayleigh_beta": 0.002,
        },
    )
    basis = _basis(prepared, count=6, policy="allow_inconclusive")
    solver = ReducedHarmonicResponseSolver()
    _mesh_pass(solver)
    with pytest.raises(ModalResidualValidationError) as caught:
        solver.solve(model, prepared=prepared, basis=basis, excitation_channels=_harmonic_channel())
    assert caught.value.validation_status == "INCONCLUSIVE"
    assert caught.value.computed_result is not None


def test_modal_newmark_refuses_inconclusive_in_default_strict_mode() -> None:
    model, prepared, _, _ = _synthetic_system(
        132,
        "transient_dynamic",
        "modal_newmark",
        {
            "time_step": 0.005,
            "steps": 4,
            "newmark_beta": 0.25,
            "newmark_gamma": 0.5,
            "rayleigh_alpha": 0.0,
            "rayleigh_beta": 0.0,
            "modal_mode_count": 6,
            "modal_extraction_method": "dense",
        },
    )
    basis = _basis(prepared, count=6, policy="allow_inconclusive")
    assert model.analysis.parameters.get("modal_validation_policy", "strict") == "strict"
    solver = ModalNewmarkTransientSolver()
    _mesh_pass(solver)
    with pytest.raises(ModalResidualValidationError) as caught:
        solver.solve(model, prepared=prepared, basis=basis, excitation_channels=ExcitationChannelSet())
    assert caught.value.validation_status == "INCONCLUSIVE"
    assert caught.value.computed_result is not None


@pytest.mark.parametrize(
    ("route", "policy"),
    [
        ("harmonic", "strict"),
        ("harmonic", "allow_inconclusive"),
        ("newmark", "strict"),
        ("newmark", "allow_inconclusive"),
    ],
    ids=["harmonic-strict", "harmonic-allow-inconclusive", "newmark-strict", "newmark-allow-inconclusive"],
)
def test_reduced_routes_do_not_swallow_modal_failures(
    route: str, policy: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    if route == "harmonic":
        analysis_type, method = "harmonic_response", "modal_superposition"
        parameters: dict[str, object] = {"frequencies_hz": [0.07], "rayleigh_alpha": 0.03, "rayleigh_beta": 0.002}
    else:
        analysis_type, method = "transient_dynamic", "modal_newmark"
        parameters = {
            "time_step": 0.005,
            "steps": 4,
            "newmark_beta": 0.25,
            "newmark_gamma": 0.5,
            "rayleigh_alpha": 0.0,
            "rayleigh_beta": 0.0,
        }
    parameters.update(
        {"modal_mode_count": 2, "modal_extraction_method": "dense", "modal_validation_policy": policy}
    )
    model, prepared, _, _ = _synthetic_system(2, analysis_type, method, parameters)
    error = ModalResidualValidationError(
        "synthetic exact-eigenpair FAIL",
        validation_status="FAIL",
        diagnostics={"status": "FAIL", "reason": "residual_above_tolerance"},
        computed_result={"candidate_modes_retained": True},
    )

    def fail_basis(*args: object, **kwargs: object) -> ModalBasis:
        del args, kwargs
        raise error

    monkeypatch.setattr(ModalBasis, "from_prepared", classmethod(lambda cls, *a, **kw: fail_basis(*a, **kw)))
    if route == "harmonic":
        solver = ReducedHarmonicResponseSolver()
        _mesh_pass(solver)
        with pytest.raises(ModalResidualValidationError) as caught:
            solver.solve(model, prepared=prepared, excitation_channels=_harmonic_channel())
    else:
        solver = ModalNewmarkTransientSolver()
        _mesh_pass(solver)
        with pytest.raises(ModalResidualValidationError) as caught:
            solver.solve(model, prepared=prepared, excitation_channels=ExcitationChannelSet())
    assert caught.value is error
    assert caught.value.validation_status == "FAIL"


@pytest.mark.parametrize(
    ("size", "count", "policy", "expected_validation", "banded"),
    [(2, 2, "strict", "PASS_CERTIFIED", False), (120, 4, "allow_inconclusive", "INCONCLUSIVE", True)],
    ids=["certified", "120-dof-1188-terms-inconclusive"],
)
def test_modal_newmark_runs_and_matches_independent_recurrence_and_checkpoint(
    size: int,
    count: int,
    policy: str,
    expected_validation: str,
    banded: bool,
    tmp_path: Path,
) -> None:
    dt, steps, beta, gamma = 0.005, 8, 0.25, 0.5
    checkpoint_path = tmp_path / f"modal-{size}.npz"
    model, prepared, stiffness, mass = _synthetic_system(
        size,
        "transient_dynamic",
        "modal_newmark",
        {
            "time_step": dt,
            "steps": steps,
            "newmark_beta": beta,
            "newmark_gamma": gamma,
            "rayleigh_alpha": 0.0,
            "rayleigh_beta": 0.0,
            "modal_mode_count": count,
            "modal_extraction_method": "dense",
            "modal_validation_policy": policy,
            "initial_displacements": [{"node": 0, "dof": "UX", "value": 0.1}],
            "initial_velocities": [{"node": 0, "dof": "UX", "value": 0.2}],
            "record_time_history": True,
            "store_modal_history": True,
            "checkpoint_path": str(checkpoint_path),
            "checkpoint_interval": 4,
        },
        banded=banded,
    )
    if banded:
        assert stiffness.nnz + mass.nnz == 1_188
    basis = _basis(prepared, count=count, policy=policy)
    assert basis.validation_status == expected_validation
    solver = ModalNewmarkTransientSolver()
    _mesh_pass(solver)
    recording_store = _RecordingCheckpointStore()
    solver.checkpoint_store = recording_store
    result = solver.solve(model, prepared=prepared, excitation_channels=ExcitationChannelSet())

    mode_matrix = basis.modes
    projected_mass = basis.projected_mass
    projected_stiffness = basis.projected_stiffness
    initial_u = np.zeros(size)
    initial_v = np.zeros(size)
    initial_u[0], initial_v[0] = 0.1, 0.2
    initial_q = np.linalg.solve(projected_mass, mode_matrix.T @ (mass.toarray() @ initial_u))
    initial_qdot = np.linalg.solve(projected_mass, mode_matrix.T @ (mass.toarray() @ initial_v))
    reference_q, reference_v, reference_a = _independent_newmark(
        projected_mass,
        projected_stiffness,
        initial_q,
        initial_qdot,
        dt=dt,
        steps=steps,
        beta=beta,
        gamma=gamma,
    )
    assert len(result.modal_history) == steps + 1
    np.testing.assert_allclose([row["q"] for row in result.modal_history], reference_q, rtol=2e-10, atol=2e-12)
    np.testing.assert_allclose([row["qdot"] for row in result.modal_history], reference_v, rtol=2e-10, atol=2e-12)
    np.testing.assert_allclose([row["qddot"] for row in result.modal_history], reference_a, rtol=2e-10, atol=2e-12)
    np.testing.assert_allclose(result.times, np.arange(steps + 1) * dt, rtol=0.0, atol=1e-15)
    assert result.numerical_status == ("PASS" if expected_validation == "PASS_CERTIFIED" else "INCONCLUSIVE")
    assert result.execution_identity["modal_basis_validation_status"] == expected_validation
    assert result.execution_identity["modal_basis_use_policy"] == basis.use_policy
    assert result.result_availability["modal_basis_validation"]["usable_as_certified_evidence"] is (
        expected_validation == "PASS_CERTIFIED"
    )
    initial_acceleration = np.linalg.solve(projected_mass, -projected_stiffness @ initial_q)
    np.testing.assert_allclose(result.modal_history[0]["q"], initial_q, rtol=1e-12, atol=1e-14)
    np.testing.assert_allclose(result.modal_history[0]["qdot"], initial_qdot, rtol=1e-12, atol=1e-14)
    np.testing.assert_allclose(result.modal_history[0]["qddot"], initial_acceleration, rtol=1e-12, atol=1e-14)
    energy = np.asarray(
        [
            0.5 * np.asarray(row["qdot"]) @ (projected_mass @ np.asarray(row["qdot"]))
            + 0.5 * np.asarray(row["q"]) @ (projected_stiffness @ np.asarray(row["q"]))
            for row in result.modal_history
        ]
    )
    energy_drift = float(np.max(np.abs(energy - energy[0])) / energy[0])
    assert energy_drift < 2e-10

    payload = result.to_dict()
    assert payload["run_verdict"] == "WARNING"
    assert payload["qualification_decision"] == "NOT_ASSESSED"
    json.dumps(payload, allow_nan=False)
    restored = ModalNewmarkResult.from_dict(payload)
    assert restored.numerical_status == result.numerical_status
    assert restored.execution_identity["modal_basis_validation_status"] == expected_validation
    assert checkpoint_path.is_file()
    with np.load(checkpoint_path, allow_pickle=False) as archive:
        checkpoint_metadata = json.loads(str(archive["metadata_json"].item()))
    assert checkpoint_metadata["run_signature"] == result.execution_key
    assert checkpoint_metadata["basis_identity"] == result.execution_identity["basis_identity"]
    assert recording_store.signature_payload is not None
    assert recording_store.signature_payload["modal_basis_validation_status"] == expected_validation
    assert recording_store.signature_payload["modal_basis_use_policy"] == basis.use_policy

    restart_parameters = dict(model.analysis.parameters)
    restart_parameters["restart_from"] = str(checkpoint_path)
    restart_model, restart_prepared, _, _ = _synthetic_system(
        size,
        "transient_dynamic",
        "modal_newmark",
        restart_parameters,
        banded=banded,
    )
    restart_solver = ModalNewmarkTransientSolver()
    _mesh_pass(restart_solver)
    restarted = restart_solver.solve(
        restart_model,
        prepared=restart_prepared,
        excitation_channels=ExcitationChannelSet(),
    )
    np.testing.assert_allclose(restarted.displacements, result.displacements, rtol=0.0, atol=1e-14)
    assert restarted.numerical_status == result.numerical_status


def test_modal_checkpoint_identity_changes_with_compatibility_policy(tmp_path: Path) -> None:
    params: dict[str, object] = {
        "time_step": 0.005,
        "steps": 4,
        "newmark_beta": 0.25,
        "newmark_gamma": 0.5,
        "rayleigh_alpha": 0.0,
        "rayleigh_beta": 0.0,
        "modal_mode_count": 2,
        "modal_extraction_method": "dense",
        "modal_validation_policy": "strict",
        "checkpoint_path": str(tmp_path / "strict.npz"),
    }
    model, prepared, _, _ = _synthetic_system(2, "transient_dynamic", "modal_newmark", params)
    basis = _basis(prepared, count=2, policy="strict")
    solver = ModalNewmarkTransientSolver()
    _mesh_pass(solver)
    result = solver.solve(model, prepared=prepared, basis=basis, excitation_channels=ExcitationChannelSet())
    changed = dict(params)
    changed["modal_validation_policy"] = "allow_inconclusive"
    changed["restart_from"] = str(tmp_path / "strict.npz")
    changed_model, changed_prepared, _, _ = _synthetic_system(
        2, "transient_dynamic", "modal_newmark", changed
    )
    changed_solver = ModalNewmarkTransientSolver()
    _mesh_pass(changed_solver)
    with pytest.raises(InputValidationError, match="restart is refused"):
        changed_solver.solve(
            changed_model,
            prepared=changed_prepared,
            basis=basis,
            excitation_channels=ExcitationChannelSet(),
        )
    assert result.execution_identity["modal_basis_validation_status"] == "PASS_CERTIFIED"


def test_direct_modal_route_rejects_non_string_policy_before_assembly(monkeypatch: pytest.MonkeyPatch) -> None:
    model, _, _, _ = _synthetic_system(2, "modal", "eigsh", {})
    model.analysis.parameters["modal_validation_policy"] = []
    solver = ModalAnalysisSolver()
    solver.validator.validate = lambda candidate: MeshReport("PASS")
    with pytest.raises(InputValidationError, match="modal_validation_policy"):
        solver.solve(model)


def test_modal_basis_public_policy_arguments_reject_non_boolean_or_non_string_values() -> None:
    _, prepared, _, _ = _synthetic_system(2, "modal", "eigsh", {})
    with pytest.raises(InputValidationError, match="modal_validation_policy"):
        ModalBasis.from_prepared(prepared, mode_count=2, method="dense", validation_policy=[])
    with pytest.raises(InputValidationError, match="modal_validation_policy"):
        ModalBasis._from_operators(
            np.eye(2),
            np.eye(2),
            operator_identity="invalid-policy-synthetic-v1",
            dof_signature=prepared.dof_signature,
            requested_modes=2,
            method="dense",
            dense_limit=2,
            validation_policy=[],
        )
    certified = _basis(prepared, count=2, policy="strict")
    with pytest.raises(InputValidationError, match="allow_inconclusive must be a boolean"):
        certified.assert_compatible(prepared, allow_inconclusive=[])  # type: ignore[arg-type]
