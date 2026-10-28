from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
from dataclasses import replace
from pathlib import Path
import uuid

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
from solveur.elements.discrete import ConcentratedMass, SpringDefinition


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


def _write_wp12_attempt_observables(
    *,
    case_name: str,
    nodeid: str,
    payload: dict[str, object],
) -> dict[str, str]:
    """Atomically publish one JSON sidecar inside this launcher's inventoried output directory."""
    if Path(case_name).name != case_name or not case_name:
        raise ValueError("The observables artifact name must be a plain filename stem.")
    if os.environ.get("QF_DEVELOPMENT_AUTONOMOUS") != "1":
        raise RuntimeError("WP12 numerical observables require the authorized development launcher.")
    if os.environ.get("QF_DEV_WORKTREE_ID") != "wp12_dynamics":
        raise RuntimeError("WP12 numerical observables require the registered wp12_dynamics worktree.")
    raw_temp_dir = os.environ.get("TMP")
    raw_temp_alias = os.environ.get("TEMP")
    if not raw_temp_dir or not raw_temp_alias:
        raise RuntimeError("The development launcher did not provide its attempt-specific temporary directory.")

    temp_dir = Path(raw_temp_dir).resolve(strict=True)
    if Path(raw_temp_alias).resolve(strict=True) != temp_dir or temp_dir.name.casefold() != "tmp":
        raise RuntimeError("The launcher temporary-directory aliases do not identify one attempt.")
    attempt_dir = temp_dir.parent.resolve(strict=True)
    run_path = (attempt_dir / "run.json").resolve(strict=True)
    output_dir = (attempt_dir / "output").resolve(strict=True)
    if output_dir.parent != attempt_dir or run_path.parent != attempt_dir or not run_path.is_file():
        raise RuntimeError("The launcher attempt record/output directory is unavailable or escaped its attempt.")

    run_record = json.loads(run_path.read_text(encoding="utf-8"))
    if (
        run_record.get("state") != "RUNNING"
        or run_record.get("worktree_id") != "wp12_dynamics"
        or run_record.get("target") != [nodeid]
    ):
        raise RuntimeError("The launcher run record does not identify this exact in-progress nodeid.")
    series_id = run_record.get("series_id")
    attempt = run_record.get("attempt")
    local_attempt_match = re.fullmatch(r"attempt-(\d{4})", attempt_dir.name)
    if (
        not isinstance(series_id, str)
        or series_id != attempt_dir.parent.name
        or not isinstance(attempt, int)
        or isinstance(attempt, bool)
        or attempt < 1
        or local_attempt_match is None
        or int(local_attempt_match.group(1)) < 1
    ):
        raise RuntimeError("The launcher attempt directory does not match its unique series/attempt identity.")
    series_attempt = int(local_attempt_match.group(1))
    manifest_ref = run_record.get("execution_manifest")
    if not isinstance(manifest_ref, dict) or not isinstance(manifest_ref.get("path"), str):
        raise RuntimeError("The launcher run record has no exact execution-manifest identity.")
    manifest_path = Path(manifest_ref["path"]).resolve(strict=True)
    identity = run_record.get("identity")
    controller = run_record.get("controller_provenance")
    source_fingerprint = run_record.get("source_fingerprint")
    if not isinstance(identity, dict) or not isinstance(controller, dict) or not isinstance(source_fingerprint, str):
        raise RuntimeError("The exact Newmark attempt manifest is not explicitly Owner-authorized.")
    controller_identity = controller.get("identity")
    controller_hashes = controller.get("sha256")
    if not isinstance(controller_identity, dict) or not isinstance(controller_hashes, dict):
        raise RuntimeError("The launcher run record lacks controller root/hash provenance.")
    controller_root = Path(str(controller_identity.get("root", ""))).resolve(strict=True)
    policy_path = (controller_root / "development_autonomous_policy.json").resolve(strict=True)
    policy_bytes = policy_path.read_bytes()
    policy_sha256 = hashlib.sha256(policy_bytes).hexdigest()
    if policy_sha256 != controller_hashes.get("policy"):
        raise RuntimeError("The WP12 controller policy differs from the run's captured policy identity.")
    controller_policy = json.loads(policy_bytes)
    policy_worktree = controller_policy.get("worktrees", {}).get("wp12_dynamics", {})
    evidence_root = Path(str(policy_worktree.get("evidence_root", ""))).resolve(strict=True)
    expected_authorization_dir = (evidence_root / "authorizations" / "wp12_dynamics").resolve(strict=True)
    try:
        expected_authorization_dir.relative_to(evidence_root)
    except ValueError as exc:
        raise RuntimeError("The policy-configured WP12 authorization directory is outside its evidence root.") from exc
    owner_authorized_dir = expected_authorization_dir / "owner-authorized"
    if owner_authorized_dir.is_symlink():
        raise RuntimeError("The WP12 owner-authorized manifest directory must not be a symlink.")
    allowed_manifest_dirs = {expected_authorization_dir}
    if owner_authorized_dir.exists():
        if not owner_authorized_dir.is_dir():
            raise RuntimeError("The WP12 owner-authorized manifest path is not a directory.")
        resolved_owner_authorized_dir = owner_authorized_dir.resolve(strict=True)
        if resolved_owner_authorized_dir.parent != expected_authorization_dir:
            raise RuntimeError("The WP12 owner-authorized manifest directory escaped its authorization root.")
        allowed_manifest_dirs.add(resolved_owner_authorized_dir)
    if manifest_path.parent not in allowed_manifest_dirs:
        raise RuntimeError("The execution manifest is outside the policy-configured WP12 evidence root.")
    manifest_bytes = manifest_path.read_bytes()
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    if manifest_ref.get("sha256") != manifest_sha256:
        raise RuntimeError("The execution-manifest hash changed after the launcher recorded it.")
    manifest = json.loads(manifest_bytes)
    try:
        attempt_dir.relative_to(evidence_root)
    except ValueError as exc:
        raise RuntimeError("The launcher attempt output is outside the evidence root bound by its manifest.") from exc
    if attempt_dir.parents[2].name != "worktrees" or attempt_dir.parents[1].name != "wp12_dynamics":
        raise RuntimeError("The launcher output path does not match the registered worktree evidence layout.")
    if attempt_dir.parents[3] != evidence_root:
        raise RuntimeError("The launcher attempt and its manifest do not share the same authorized evidence root.")

    case_file = f"{case_name}.json"
    artifact_path = output_dir / case_file
    if artifact_path.exists():
        raise FileExistsError(f"Refusing to overwrite per-attempt observables: {artifact_path}")
    decision = manifest.get("owner_decision")
    if (
        not isinstance(decision, dict)
        or manifest.get("schema") != "qfsolver-wp12-development-execution-v1"
        or manifest.get("state") != "OWNER_AUTHORIZED"
        or manifest.get("worktree_id") != "wp12_dynamics"
        or manifest.get("target") != nodeid
        or manifest.get("authorization_id") != manifest_ref.get("authorization_id")
        or manifest.get("identity") != identity
        or manifest.get("source_fingerprint") != source_fingerprint
        or decision.get("status") != "APPROVED"
        or decision.get("approved_by") != "Owner"
    ):
        raise RuntimeError("The launcher run record lacks source/controller identity fields.")
    complete_payload = {
        **payload,
        "attempt_identity": {
            "worktree_id": run_record["worktree_id"],
            "nodeid": nodeid,
            "series_id": series_id,
            "attempt": attempt,
            "series_attempt": series_attempt,
            "authorization_id": manifest_ref["authorization_id"],
            "manifest_sha256": manifest_sha256,
            "evidence_relative_attempt_path": attempt_dir.relative_to(evidence_root).as_posix(),
            "source_fingerprint": source_fingerprint,
            "source_identity": identity,
            "controller_provenance": controller,
        },
        "artifact_path_relative_to_evidence_root": (output_dir / case_file).relative_to(evidence_root).as_posix(),
    }
    non_finite_values: dict[str, str] = {}
    json_payload = _json_safe_observables(complete_payload, "$", non_finite_values)
    if not isinstance(json_payload, dict):
        raise TypeError("The WP12 observables payload must remain a JSON object.")
    if non_finite_values:
        json_payload["non_finite_values"] = non_finite_values
    encoded = json.dumps(json_payload, sort_keys=True, indent=2, allow_nan=False) + "\n"
    temporary_path = output_dir / f".{case_name}.{series_id}.{attempt}.{uuid.uuid4().hex}.tmp"
    try:
        with temporary_path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        # A same-directory hard link atomically publishes the complete file and fails if it exists.
        os.link(temporary_path, artifact_path)
    finally:
        temporary_path.unlink(missing_ok=True)

    if json.loads(artifact_path.read_text(encoding="utf-8")) != json_payload:
        raise RuntimeError("The published WP12 observables JSON did not round-trip exactly.")
    return {"path": str(artifact_path), "sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest()}


def _json_safe_observables(value: object, path: str, non_finite_values: dict[str, str]) -> object:
    if isinstance(value, np.generic):
        return _json_safe_observables(value.item(), path, non_finite_values)
    if isinstance(value, float) and not math.isfinite(value):
        non_finite_values[path] = repr(value)
        return None
    if isinstance(value, dict):
        return {
            str(key): _json_safe_observables(item, f"{path}.{key}", non_finite_values) for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_json_safe_observables(item, f"{path}[{index}]", non_finite_values) for index, item in enumerate(value)]
    return value


def _publish_wp12_observables_before_assertions(
    *,
    case_name: str,
    nodeid: str,
    payload: dict[str, object],
    checks: list[tuple[str, bool]],
) -> dict[str, str]:
    """Persist computed observations first, then raise for any failed test oracle."""
    artifact = _write_wp12_attempt_observables(case_name=case_name, nodeid=nodeid, payload=payload)
    failed_checks = [label for label, passed in checks if not passed]
    if failed_checks:
        raise AssertionError(
            "WP12 numerical checks failed after observables were archived: " + "; ".join(failed_checks)
        )
    return artifact


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


@pytest.mark.parametrize("physical_change", ["mass", "spring", "material", "boundary"])
def test_modal_restart_refuses_each_changed_physical_operator_input(tmp_path, physical_change: str) -> None:
    checkpoint = tmp_path / f"modal-{physical_change}.npz"
    baseline = _model(
        load=0.1,
        steps=4,
        dt=0.0001,
        extra_parameters={
            "checkpoint_path": str(checkpoint),
            "checkpoint_interval": 2,
            "checkpoint_keep_steps": True,
        },
    )
    _run(baseline)
    intermediate = tmp_path / f"modal-{physical_change}.step00000002.npz"
    assert intermediate.is_file()

    changed = _model(
        load=0.1,
        steps=4,
        dt=0.0001,
        extra_parameters={"restart_from": str(intermediate)},
    )
    if physical_change == "mass":
        changed.concentrated_masses.append(ConcentratedMass(node=1, mass=0.25))
    elif physical_change == "spring":
        changed.springs.append(SpringDefinition(node_a=1, dofs=("UX",), stiffness=((25.0,),)))
    elif physical_change == "material":
        changed.materials["mat"]["density"] *= 1.1
    else:
        changed.fixed_dofs[1] = replace(
            changed.fixed_dofs[1],
            dofs=tuple(dof for dof in changed.fixed_dofs[1].dofs if dof != "UY"),
        )

    with pytest.raises(InputValidationError, match="restart is refused"):
        _run(changed)


def test_modal_restart_rejects_a_direct_newmark_checkpoint(tmp_path) -> None:
    checkpoint = tmp_path / "direct-state.npz"
    direct_model = _model(
        load=0.1,
        steps=4,
        extra_parameters={"checkpoint_path": str(checkpoint), "checkpoint_interval": 2},
    )
    direct_model.analysis = replace(direct_model.analysis, method="newmark")
    solve_model(direct_model)
    assert checkpoint.is_file()

    modal_model = _model(
        load=0.1,
        steps=4,
        extra_parameters={"restart_from": str(checkpoint)},
    )
    with pytest.raises(InputValidationError, match="unsupported, incompatible or corrupted NPZ"):
        _run(modal_model)


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


@pytest.mark.parametrize("family", ["TET4", "TET10", "HEX8", "HEX20", "BEAM2"])
def test_wp07_uniform_base_acceleration_integrates_each_wp00_family(family: str) -> None:
    model = _model(
        family=family,
        mode_count=None,
        load=None,
        dt=1.0e-5,
        steps=1,
        extra_parameters={
            "uniform_base_acceleration": {
                "schema": "qf-uniform-base-acceleration/v1",
                "direction": [1.0, 0.0, 0.0],
                "direction_frame": "global_model_axes",
                "acceleration_unit": "m/s^2",
                "support_policy": "all_homogeneous_fixed_supports_comoving",
                "time_history": {
                    "time_unit": "s",
                    "interpolation": "linear_endpoint_hold",
                    "samples": [
                        {"time_s": 0.0, "value": 0.25},
                        {"time_s": 1.0e-5, "value": 0.25},
                    ],
                },
            }
        },
    )
    prepared, basis = _prepared_basis(model)
    result = _run(model, prepared=prepared, basis=basis)
    assert basis.is_full_basis
    assert result.absolute_accelerations is not None
    assert result.solver["uniform_base_acceleration"]["mass_formed_before_constraint_reduction"] is True
    assert result.maturity == "EXPERIMENTAL"


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
        assert result.solver["integration"]["second_order_claim"] == "NOT_CLAIMED"
        assert result.solver["integration"]["applied_force_regularity_assessed"] is False
        omega = math.sqrt(float(prepared.stiffness[0, 0] / prepared.mass[0, 0]))
        exact = q0 * math.cos(omega * result.times[-1])
        index = model.dof_manager().index(1, "UX")
        errors.append(abs(result.displacements[index] - exact))
    observed_order = math.log(errors[0] / errors[1], 2.0)
    assert observed_order >= 1.8
    assert errors[2] < errors[1] < errors[0]


def test_wp12_newmark_fixed_time_state_refinement_residual_and_energy_observables() -> None:
    """Record u/v/a convergence and equilibrium/energy diagnostics at fixed final time."""
    q0 = 1.0e-3
    final_time = 0.08
    observations: list[dict[str, object]] = []
    resolution_identities: list[dict[str, object]] = []
    assertion_checks: list[tuple[str, bool]] = []

    for dt in (0.002, 0.001, 0.0005):
        steps = round(final_time / dt)
        model = _model(
            dt=dt,
            steps=steps,
            extra_parameters={
                "initial_displacements": [{"node": 1, "dof": "UX", "value": q0}],
                "initial_velocities": [{"node": 1, "dof": "UX", "value": 0.0}],
                "record_time_history": True,
                "history_probes": [{"label": "tip", "node": 1, "dof": "UX"}],
                "newmark_beta": 0.25,
                "newmark_gamma": 0.5,
            },
        )
        prepared, basis = _prepared_basis(model)
        result = _run(model, prepared=prepared, basis=basis)

        omega = math.sqrt(float(prepared.stiffness[0, 0] / prepared.mass[0, 0]))
        times = np.asarray(result.times, dtype=float)
        assertion_checks.extend(
            [
                (f"dt={dt:g}s starts at t=0", bool(times[0] == pytest.approx(0.0))),
                (f"dt={dt:g}s ends at fixed final time", bool(times[-1] == pytest.approx(final_time))),
                (f"dt={dt:g}s has steps+1 samples", bool(times.size == steps + 1)),
            ]
        )
        exact = {
            "displacement": q0 * np.cos(omega * times),
            "velocity": -q0 * omega * np.sin(omega * times),
            "acceleration": -q0 * omega**2 * np.cos(omega * times),
        }
        actual = {
            field: np.asarray([row["probes"]["tip"][field] for row in result.time_history], dtype=float)
            for field in exact
        }
        errors = {field: float(np.max(np.abs(actual[field] - exact[field]))) for field in exact}
        relative_errors = {field: errors[field] / float(np.max(np.abs(exact[field]))) for field in exact}
        integration = result.execution_identity["integration"]
        assertion_checks.extend(
            [
                (f"dt={dt:g}s beta remains 0.25", bool(integration["beta"] == 0.25)),
                (f"dt={dt:g}s gamma remains 0.5", bool(integration["gamma"] == 0.5)),
                (f"dt={dt:g}s execution step matches input", bool(integration["time_step_s"] == dt)),
                (
                    f"dt={dt:g}s execution duration matches fixed final time",
                    bool(integration["duration_s"] == pytest.approx(final_time)),
                ),
            ]
        )

        residual_max = max(row["reduced_equilibrium_relative_error"] for row in result.time_history)
        energy_drift_max = max(abs(row["relative_energy_drift"]) for row in result.time_history)
        initial_energy = float(result.time_history[0]["total_energy"])
        sample_observables: list[dict[str, object]] = []
        for index, (time_s, row) in enumerate(zip(times, result.time_history)):
            state_errors: dict[str, dict[str, float]] = {}
            for field in exact:
                error = float(abs(actual[field][index] - exact[field][index]))
                state_errors[field] = {
                    "numerical": float(actual[field][index]),
                    "analytic": float(exact[field][index]),
                    "absolute_error": error,
                    "relative_error": error / float(np.max(np.abs(exact[field]))),
                }
            total_energy = float(row["total_energy"])
            sample_observables.append(
                {
                    "time_s": float(time_s),
                    "state": state_errors,
                    "residuals": {
                        "reduced_equilibrium_residual_norm": float(row["reduced_equilibrium_residual_norm"]),
                        "reduced_equilibrium_relative_error": float(row["reduced_equilibrium_relative_error"]),
                    },
                    "energy_balance": {
                        "strain_energy_J": float(row["strain_energy"]),
                        "kinetic_energy_J": float(row["kinetic_energy"]),
                        "total_energy_J": total_energy,
                        "initial_total_energy_J": initial_energy,
                        "change_from_initial_J": total_energy - initial_energy,
                        "relative_total_energy_drift": float(row["relative_energy_drift"]),
                        "reduced_damping_power_W": float(row["damping_power_reduced"]),
                    },
                }
            )
        resolution_identity = {
            "dt_s": dt,
            "source_sha": prepared.source_sha,
            "physical_identity": prepared.physical_identity,
            "operator_identity": prepared.operator_identity,
            "basis_identity": basis.basis_identity,
            "solver_execution_identity": result.execution_identity,
        }
        resolution_identities.append(resolution_identity)
        observations.append(
            {
                "dt_s": dt,
                "steps": steps,
                "final_time_s": final_time,
                "beta": float(integration["beta"]),
                "gamma": float(integration["gamma"]),
                "displacement_max_abs_error": errors["displacement"],
                "velocity_max_abs_error": errors["velocity"],
                "acceleration_max_abs_error": errors["acceleration"],
                "displacement_max_relative_error": relative_errors["displacement"],
                "velocity_max_relative_error": relative_errors["velocity"],
                "acceleration_max_relative_error": relative_errors["acceleration"],
                "max_reduced_equilibrium_relative_error": float(residual_max),
                "max_relative_energy_drift": float(energy_drift_max),
                "sample_observables": sample_observables,
            }
        )
        assertion_checks.extend(
            [
                (f"dt={dt:g}s reduced residual is finite", math.isfinite(residual_max)),
                (f"dt={dt:g}s reduced residual <= 1e-7", residual_max <= 1.0e-7),
                (f"dt={dt:g}s energy drift is finite", math.isfinite(energy_drift_max)),
                (f"dt={dt:g}s energy drift <= 1e-10", energy_drift_max <= 1.0e-10),
            ]
        )

    observed_orders = {
        field: [math.log(errors[index] / errors[index + 1], 2.0) for index in range(2)]
        for field, errors in {
            "displacement": [item["displacement_max_relative_error"] for item in observations],
            "velocity": [item["velocity_max_relative_error"] for item in observations],
            "acceleration": [item["acceleration_max_relative_error"] for item in observations],
        }.items()
    }
    assertion_checks.append(
        ("minimum displacement convergence order >= 1.8", min(observed_orders["displacement"]) >= 1.8)
    )
    payload: dict[str, object] = {
        "schema": "qfsolver-wp12-newmark-observables-v1",
        "case": "WP12-NEWMARK-SDOF-FIXED-TIME",
        "case_identity": {
            "nodeid": "tests/unit/test_modal_newmark.py::test_wp12_newmark_fixed_time_state_refinement_residual_and_energy_observables",
            "fixture": "single-free-axial-translation BEAM2, straight 1 m span",
            "response_dof": "node 1 UX in global model axes; positive sign is +global X",
            "unit_system": "SI",
            "resolution_identities": resolution_identities,
        },
        "units": {
            "time_step": "s",
            "time": "s",
            "displacement": "m",
            "velocity": "m/s",
            "acceleration": "m/s^2",
            "relative_error": "dimensionless",
            "reduced_equilibrium_residual_norm": "basis-dependent modal generalized force",
            "reduced_equilibrium_relative_error": "dimensionless",
            "strain_energy": "J",
            "kinetic_energy": "J",
            "total_energy": "J",
            "energy_change": "J",
            "reduced_damping_power": "W",
            "relative_total_energy_drift": "dimensionless",
            "observed_order": "dimensionless",
        },
        "parameters": {
            "initial_displacement_m": q0,
            "initial_velocity_m_s": 0.0,
            "final_time_s": final_time,
            "time_steps_s": [float(item["dt_s"]) for item in observations],
            "newmark_scheme": "Newmark-implicit-constant-step",
            "beta": 0.25,
            "gamma": 0.5,
        },
        "error_definition": {
            "absolute": "max_i(abs(computed(t_i) - exact(t_i))) over all recorded samples",
            "relative": "absolute_error / max_i(abs(exact(t_i))) on the same fixed-time sample grid",
            "sample_relative_error": "abs(computed(t_i) - exact(t_i)) / max_j(abs(exact(t_j))) on the same fixed-time sample grid",
            "observed_order": "log2(relative_error(dt) / relative_error(dt/2))",
        },
        "residual_unit_note": "The reduced residual norm is expressed in modal generalized coordinates and depends on basis normalization; the normalized equilibrium residual is dimensionless.",
        "energy_balance_definition": (
            "Per sample, total energy is strain plus kinetic energy; change_from_initial_J is "
            "total_energy(t)-total_energy(0). The fixture has zero applied load and zero Rayleigh "
            "damping, so this is a conservative free-vibration balance diagnostic."
        ),
        "observations": observations,
        "observed_orders": observed_orders,
        "assertion_results": {label: passed for label, passed in assertion_checks},
        "acceptance_criteria": {
            "minimum_displacement_order": 1.8,
            "maximum_reduced_equilibrium_relative_error": 1.0e-7,
            "maximum_relative_energy_drift": 1.0e-10,
            "velocity_and_acceleration_error_thresholds": "none; measured and reported only",
        },
        "oracle_scope": "closed-form SDOF integration conditional on the prepared scalar K/M operators",
    }
    artifact = _publish_wp12_observables_before_assertions(
        case_name="wp12-newmark-fixed-time-observables",
        nodeid=str(payload["case_identity"]["nodeid"]),
        payload=payload,
        checks=assertion_checks,
    )
    print(
        json.dumps(
            {"artifact": artifact},
            sort_keys=True,
            allow_nan=False,
        )
    )


def test_mode_count_refinement_converges_to_full_basis_direct_reference() -> None:
    seed = _model(family="TET4", mode_count=None, load=None, dt=1.0e-5, steps=12)
    prepared, full_basis = _prepared_basis(seed)
    omitted_mode = prepared.expand_state(full_basis.modes[:, -1])
    amplitude = 1.0e-3 / float(np.max(np.abs(omitted_mode)))
    dofs = seed.dof_manager()
    # Build the sparse physical initial state in the model's canonical DDL order.
    initial_state = []
    offset = 0
    for node, names in sorted(dofs.node_dofs.items()):
        for dof in names:
            value = float(amplitude * omitted_mode[offset])
            if abs(value) > 1.0e-14:
                initial_state.append({"node": node, "dof": dof, "value": value})
            offset += 1

    parameters = {"initial_displacements": initial_state}
    partial_model = _model(family="TET4", mode_count=2, load=None, dt=1.0e-5, steps=12, extra_parameters=parameters)
    full_model = _model(family="TET4", mode_count=None, load=None, dt=1.0e-5, steps=12, extra_parameters=parameters)
    direct_model = copy.deepcopy(full_model)
    direct_model.analysis = replace(direct_model.analysis, method="newmark")

    partial = _run(partial_model)
    full = _run(full_model, prepared=prepared, basis=full_basis)
    direct = solve_model(direct_model)
    partial_error = float(np.linalg.norm(partial.accelerations - direct.accelerations))
    full_error = float(np.linalg.norm(full.accelerations - direct.accelerations))
    assert np.isfinite(partial_error) and partial_error > 0.0
    assert full_error < 1.0e-8 * partial_error
    assert full.result_availability["physical_truncation_error"]["status"] == "UNAVAILABLE"


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
