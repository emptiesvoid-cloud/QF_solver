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

from solveur.core.analyses.excitation_channels import (
    ComplexPhasor,
    ExcitationChannel,
    ExcitationChannelSet,
    HarmonicAmplitude,
    SpatialDofWeight,
)
from solveur.core.analyses.modal_basis import ModalBasis
from solveur.core.analyses.modal_newmark import ModalNewmarkTransientSolver
from solveur.core.analyses.prepared_dynamic_system import PreparedDynamicSystem
from solveur.core.analyses.reduced_harmonic import ReducedHarmonicResponseSolver
from solveur.core.analyses.harmonic import HarmonicResponseSolver
from solveur.core.analyses.uniform_base_acceleration import (
    UniformBaseAcceleration,
    prepare_base_acceleration,
)
from solveur.core.errors import InputValidationError
from solveur.core.model import FiniteElementModel, NodalLoad
from solveur.core.results import ModalNewmarkResult, ReducedHarmonicResult
from solveur.core.router import AnalysisRouter


_SOURCE_SHA = "c" * 40
_BASE_COMMON = {
    "schema": "qf-uniform-base-acceleration/v1",
    "direction_frame": "global_model_axes",
    "acceleration_unit": "m/s^2",
    "support_policy": "all_homogeneous_fixed_supports_comoving",
}


def _beam_model(
    route: str,
    *,
    direction: tuple[float, float, float] = (1.0, 0.0, 0.0),
    free_dof: str = "UX",
    frequency_hz: float = 1.25,
    acceleration: complex = 0.0j,
    history: list[dict[str, float]] | None = None,
    extra_parameters: dict[str, object] | None = None,
    grounded_spring_policy: str | None = None,
    grounded_spring: bool = False,
) -> FiniteElementModel:
    if route == "harmonic":
        analysis_type, method = "harmonic_response", "modal_superposition"
        signal: dict[str, object] = {
            "harmonic_phasors": [{"frequency_hz": frequency_hz, "real": acceleration.real, "imag": acceleration.imag}]
        }
        method_parameters: dict[str, object] = {
            "frequencies_hz": [frequency_hz],
            "modal_mode_count": 1,
            "modal_extraction_method": "dense",
            "modal_dense_limit": 64,
            "rayleigh_alpha": 0.0,
            "rayleigh_beta": 0.0,
        }
    else:
        analysis_type, method = "transient_dynamic", "modal_newmark"
        signal = {
            "time_history": {
                "time_unit": "s",
                "interpolation": "linear_endpoint_hold",
                "samples": history or [{"time_s": 0.0, "value": 0.0}, {"time_s": 0.01, "value": 0.0}],
            }
        }
        method_parameters = {
            "time_step": 0.001,
            "steps": 10,
            "newmark_beta": 0.25,
            "newmark_gamma": 0.5,
            "modal_mode_count": 1,
            "modal_extraction_method": "dense",
            "modal_dense_limit": 64,
            "rayleigh_alpha": 0.0,
            "rayleigh_beta": 0.0,
            "record_time_history": True,
            "history_probes": [{"node": 1, "dof": free_dof, "label": "tip"}],
            "store_modal_history": True,
        }
    base = {**_BASE_COMMON, "direction": list(direction), **signal}
    if grounded_spring_policy is not None:
        base["grounded_spring_policy"] = grounded_spring_policy
    method_parameters["uniform_base_acceleration"] = base
    method_parameters.update(extra_parameters or {})
    fixed = [
        {"node": 0, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]},
        {"node": 1, "dofs": [dof for dof in ("UX", "UY", "UZ", "RX", "RY", "RZ") if dof != free_dof]},
    ]
    springs = [{"node_a": 1, "dofs": [free_dof], "stiffness": [[10.0]]}] if grounded_spring else []
    return FiniteElementModel.from_raw(
        analysis={"type": analysis_type, "method": method, **method_parameters},
        nodes=[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
        elements=[{"type": "BEAM2", "nodes": [0, 1], "material": "beam"}],
        materials={
            "beam": {
                "type": "beam_isotropic",
                "E": 1000.0,
                "nu": 0.25,
                "A": 1.0,
                "Iy": 0.1,
                "Iz": 0.1,
                "J": 0.2,
                "density": 1.0,
            }
        },
        fixed_dofs=fixed,
        springs=springs,
    )


def _prepare(model: FiniteElementModel) -> tuple[PreparedDynamicSystem, ModalBasis]:
    prepared = PreparedDynamicSystem.prepare(model, source_sha=_SOURCE_SHA)
    basis = ModalBasis.from_prepared(
        prepared,
        mode_count=prepared.reduced_size,
        method="dense",
        dense_limit=64,
    )
    return prepared, basis


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
        raise RuntimeError("The exact WP12 attempt manifest is not explicitly Owner-authorized.")
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


def _tet4_harmonic_model() -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        analysis={
            "type": "harmonic_response",
            "method": "modal_superposition",
            "frequencies_hz": [1.0],
            "modal_mode_count": 3,
            "modal_extraction_method": "dense",
            "modal_dense_limit": 32,
            "rayleigh_alpha": 0.0,
            "rayleigh_beta": 0.0,
            "uniform_base_acceleration": {
                **_BASE_COMMON,
                "direction": [1.0, 0.0, 0.0],
                "harmonic_phasors": [{"frequency_hz": 1.0, "real": 1.0, "imag": 0.0}],
            },
        },
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "E": 1000.0, "nu": 0.25, "density": 1.0}},
        fixed_dofs=[{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in (0, 2, 3)],
    )


def _explicit_harmonic_force(frequency_hz: float, phasor: complex) -> ExcitationChannelSet:
    channel = ExcitationChannel(
        channel_id="external-tip-force",
        spatial_distribution=(SpatialDofWeight(1, "UX", 1.0),),
        spatial_units="N",
        amplitude_units="N",
        result_units="N",
        frame_convention="global_model_frame",
        sign_convention="positive_along_named_global_dof",
        constant_amplitude=None,
        harmonic=HarmonicAmplitude(frequency_hz, ComplexPhasor(phasor.real, phasor.imag)),
    )
    return ExcitationChannelSet((channel,))


def test_full_mass_base_load_keeps_free_constrained_coupling_and_beam_rotations() -> None:
    model = _beam_model("harmonic")
    prepared, basis = _prepare(model)
    specification = UniformBaseAcceleration.from_mapping(
        model.analysis.parameters["uniform_base_acceleration"], route="harmonic", model=model
    )
    base = prepare_base_acceleration(specification, model, prepared, basis.modes)
    dofs = model.dof_manager()
    free = int(prepared.free_dof_indices[0])
    full_mass = prepared.mass_full
    full_influence = np.asarray(base.influence_full)

    # The end-node mass couples to the fixed end. M_ff*r_free alone is smaller.
    exact_generalized_mass = float((full_mass @ full_influence)[free])
    reduced_only_approximation = float(prepared.mass[0, 0])
    assert exact_generalized_mass != pytest.approx(reduced_only_approximation)
    assert base.inertial_load_reduced_per_m_s2[0] == pytest.approx(-exact_generalized_mass)
    assert abs(float((prepared.stiffness_full @ full_influence)[free])) <= 1.0e-12
    assert np.all(base.influence_full[[dofs.index(0, "RX"), dofs.index(1, "RX")]] == 0.0)

    transverse = _beam_model("harmonic", direction=(0.0, 1.0, 0.0), free_dof="UY")
    transverse_prepared, transverse_basis = _prepare(transverse)
    transverse_spec = UniformBaseAcceleration.from_mapping(
        transverse.analysis.parameters["uniform_base_acceleration"], route="harmonic", model=transverse
    )
    transverse_base = prepare_base_acceleration(
        transverse_spec, transverse, transverse_prepared, transverse_basis.modes
    )
    rotational_index = transverse.dof_manager().index(1, "RZ")
    assert transverse_base.influence_full[rotational_index] == 0.0
    assert abs((transverse_prepared.mass_full @ transverse_base.influence_full)[rotational_index]) > 0.0


def test_tet4_base_load_uses_full_consistent_mass_before_fixed_dof_reduction() -> None:
    model = _tet4_harmonic_model()
    prepared, basis = _prepare(model)
    specification = UniformBaseAcceleration.from_mapping(
        model.analysis.parameters["uniform_base_acceleration"], route="harmonic", model=model
    )
    base = prepare_base_acceleration(specification, model, prepared, basis.modes)
    free = prepared.free_dof_indices
    full_mass = prepared.mass_full
    exact = -np.asarray((full_mass @ base.influence_full)[free]).reshape(-1)
    reduced_only = -np.asarray(prepared.mass @ base.influence_full[free]).reshape(-1)
    assert np.linalg.norm(exact - reduced_only) > 1.0e-12
    assert np.linalg.norm((prepared.stiffness_full @ base.influence_full)[free]) <= 1.0e-12
    np.testing.assert_allclose(base.inertial_load_reduced_per_m_s2, exact, rtol=0.0, atol=1.0e-14)
    result = ReducedHarmonicResponseSolver().solve(model, source_sha=_SOURCE_SHA, prepared=prepared, basis=basis)
    assert result.numerical_status == "PASS"
    assert result.absolute_responses is not None


def test_harmonic_base_sdof_matches_independent_full_free_equation_and_absolute_frames() -> None:
    frequency = 1.25
    acceleration = 0.0 + 1.7j
    model = _beam_model("harmonic", frequency_hz=frequency, acceleration=acceleration)
    prepared, basis = _prepare(model)
    result = ReducedHarmonicResponseSolver().solve(model, source_sha=_SOURCE_SHA, prepared=prepared, basis=basis)
    dofs = model.dof_manager()
    index = dofs.index(1, "UX")
    omega = 2.0 * math.pi * frequency
    influence = np.zeros(dofs.ndof)
    influence[dofs.index(0, "UX")] = 1.0
    influence[dofs.index(1, "UX")] = 1.0
    mass = prepared.mass_full.toarray()
    stiffness = prepared.stiffness_full.toarray()
    free = int(prepared.free_dof_indices[0])
    expected_relative = -(mass @ influence)[free] * acceleration / (stiffness[free, free] - omega**2 * mass[free, free])
    assert result.responses[0][index] == pytest.approx(expected_relative, rel=1.0e-11, abs=1.0e-13)
    assert result.absolute_responses is not None and result.absolute_velocity_responses is not None
    x_g = -acceleration / omega**2
    expected_absolute = expected_relative + x_g
    assert result.absolute_responses[0] is not None
    assert result.absolute_responses[0][index] == pytest.approx(expected_absolute, rel=1.0e-11, abs=1.0e-13)
    assert result.absolute_velocity_responses[0] is not None
    assert result.absolute_velocity_responses[0][index] == pytest.approx(1j * omega * expected_absolute)
    assert result.relative_velocity_responses is not None
    assert result.relative_velocity_responses[0][index] == pytest.approx(1j * omega * expected_relative)
    assert result.relative_acceleration_responses is not None
    assert result.relative_acceleration_responses[0][index] == pytest.approx(-(omega**2) * expected_relative)
    assert result.absolute_acceleration_responses is not None
    assert result.absolute_acceleration_responses[0][index] == pytest.approx(-(omega**2) * expected_absolute)
    assert result.result_availability["absolute_complex_accelerations"]["status"] == "AVAILABLE"
    assert result.solver["uniform_base_acceleration"]["mass_formed_before_constraint_reduction"] is True
    assert result.maturity == "EXPERIMENTAL"
    restored = ReducedHarmonicResult.from_dict(result.to_dict())
    assert restored.absolute_responses is not None
    np.testing.assert_array_equal(restored.absolute_responses[0], result.absolute_responses[0])
    assert restored.relative_velocity_responses is not None
    np.testing.assert_array_equal(restored.relative_velocity_responses[0], result.relative_velocity_responses[0])
    assert restored.absolute_acceleration_responses is not None
    np.testing.assert_array_equal(
        restored.absolute_acceleration_responses[0], result.absolute_acceleration_responses[0]
    )


def test_wp12_base_acceleration_complex_sweep_checks_frames_sign_and_serialization() -> None:
    """Compare harmonic base response to the free equation over a resonance-adjacent sweep."""
    model = _beam_model("harmonic", frequency_hz=1.0, acceleration=0.7 - 0.4j)
    prepared, basis = _prepare(model)
    dofs = model.dof_manager()
    response_index = dofs.index(1, "UX")
    free = int(prepared.free_dof_indices[0])
    mass_full = prepared.mass_full.toarray()
    stiffness_full = prepared.stiffness_full.toarray()
    omega_n = math.sqrt(float(stiffness_full[free, free] / mass_full[free, free]))
    natural_frequency_hz = omega_n / (2.0 * math.pi)
    frequencies_hz = [0.0, 0.5 * natural_frequency_hz, 0.98 * natural_frequency_hz, 1.02 * natural_frequency_hz]
    acceleration = 0.7 - 0.4j

    model.analysis.parameters["frequencies_hz"] = frequencies_hz
    base_input = model.analysis.parameters["uniform_base_acceleration"]
    base_input["harmonic_phasors"] = [
        {
            "frequency_hz": frequency,
            "real": 0.0 if frequency == 0.0 else acceleration.real,
            "imag": 0.0 if frequency == 0.0 else acceleration.imag,
        }
        for frequency in frequencies_hz
    ]
    result = ReducedHarmonicResponseSolver().solve(
        model,
        source_sha=_SOURCE_SHA,
        prepared=prepared,
        basis=basis,
    )
    checks: list[tuple[str, bool]] = [("full modal basis is complete", bool(basis.is_full_basis))]
    checks.extend(
        [
            ("relative velocity responses are available", result.relative_velocity_responses is not None),
            ("relative acceleration responses are available", result.relative_acceleration_responses is not None),
            ("absolute displacement responses are available", result.absolute_responses is not None),
            ("absolute velocity responses are available", result.absolute_velocity_responses is not None),
            ("absolute acceleration responses are available", result.absolute_acceleration_responses is not None),
        ]
    )

    influence = np.zeros(dofs.ndof)
    for node, names in dofs.node_dofs.items():
        if "UX" in names:
            influence[dofs.index(node, "UX")] = 1.0
    inertial_coupling = float((mass_full @ influence)[free])

    def phasor_metrics(prefix: str, value: complex | None) -> dict[str, float | None]:
        if value is None:
            return {
                f"{prefix}_real": None,
                f"{prefix}_imag": None,
                f"{prefix}_amplitude": None,
                f"{prefix}_phase_rad": None,
            }
        amplitude = abs(value)
        return {
            f"{prefix}_real": value.real,
            f"{prefix}_imag": value.imag,
            f"{prefix}_amplitude": amplitude,
            f"{prefix}_phase_rad": None if amplitude == 0.0 else float(np.angle(value)),
        }

    observations: list[dict[str, object]] = []
    records = result.solver["frequency_records"]

    def response_value(values: object, index: int) -> complex | None:
        if values is None:
            return None
        try:
            vector = values[index]  # type: ignore[index]
            if vector is None:
                return None
            return complex(vector[response_index])
        except (IndexError, TypeError):
            return None

    for index, frequency_hz in enumerate(frequencies_hz):
        omega = 2.0 * math.pi * frequency_hz
        base_phasor = 0.0j if frequency_hz == 0.0 else acceleration
        impedance = complex(stiffness_full[free, free] - omega**2 * mass_full[free, free])
        expected_rhs = -inertial_coupling * base_phasor
        expected_relative = expected_rhs / impedance
        actual_relative = response_value(result.responses, index)
        actual_relative_velocity = response_value(result.relative_velocity_responses, index)
        actual_relative_acceleration = response_value(result.relative_acceleration_responses, index)
        checks.extend(
            [
                (
                    f"{frequency_hz:g} Hz relative displacement matches full free equation",
                    actual_relative is not None
                    and bool(actual_relative == pytest.approx(expected_relative, rel=1.0e-11, abs=1.0e-13)),
                ),
                (
                    f"{frequency_hz:g} Hz relative velocity follows i omega U",
                    actual_relative_velocity is not None
                    and bool(
                        actual_relative_velocity
                        == pytest.approx(1j * omega * expected_relative, rel=1.0e-11, abs=1.0e-13)
                    ),
                ),
                (
                    f"{frequency_hz:g} Hz relative acceleration follows -omega squared U",
                    actual_relative_acceleration is not None
                    and bool(
                        actual_relative_acceleration
                        == pytest.approx(-(omega**2) * expected_relative, rel=1.0e-11, abs=1.0e-13)
                    ),
                ),
            ]
        )

        expected_absolute: complex | None = None
        expected_absolute_velocity: complex | None = None
        if frequency_hz > 0.0:
            expected_ground_displacement = -base_phasor / omega**2
            expected_absolute = expected_relative + expected_ground_displacement
            expected_absolute_velocity = 1j * omega * expected_absolute
            actual_absolute = response_value(result.absolute_responses, index)
            actual_absolute_velocity = response_value(result.absolute_velocity_responses, index)
            checks.extend(
                [
                    (f"{frequency_hz:g} Hz absolute displacement is available", actual_absolute is not None),
                    (f"{frequency_hz:g} Hz absolute velocity is available", actual_absolute_velocity is not None),
                    (
                        f"{frequency_hz:g} Hz absolute displacement includes ground motion",
                        actual_absolute is not None
                        and bool(actual_absolute == pytest.approx(expected_absolute, rel=1.0e-11, abs=1.0e-13)),
                    ),
                    (
                        f"{frequency_hz:g} Hz absolute velocity follows i omega U",
                        actual_absolute_velocity is not None
                        and bool(
                            actual_absolute_velocity
                            == pytest.approx(expected_absolute_velocity, rel=1.0e-11, abs=1.0e-13)
                        ),
                    ),
                ]
            )
        else:
            checks.extend(
                [
                    (
                        "DC absolute displacement remains unavailable",
                        response_value(result.absolute_responses, index) is None,
                    ),
                    (
                        "DC absolute velocity remains unavailable",
                        response_value(result.absolute_velocity_responses, index) is None,
                    ),
                ]
            )

        expected_absolute_acceleration = -(omega**2) * expected_relative + base_phasor
        actual_absolute_acceleration = response_value(result.absolute_acceleration_responses, index)
        checks.extend(
            [
                (f"{frequency_hz:g} Hz absolute acceleration is available", actual_absolute_acceleration is not None),
                (
                    f"{frequency_hz:g} Hz absolute acceleration includes base acceleration",
                    actual_absolute_acceleration is not None
                    and bool(
                        actual_absolute_acceleration
                        == pytest.approx(expected_absolute_acceleration, rel=1.0e-11, abs=1.0e-13)
                    ),
                ),
            ]
        )
        record = records[index] if index < len(records) else {}
        actual_absolute_displacement = response_value(result.absolute_responses, index)
        actual_absolute_velocity = response_value(result.absolute_velocity_responses, index)
        observations.append(
            {
                "frequency_hz": frequency_hz,
                "base_acceleration_real_m_s2": base_phasor.real,
                "base_acceleration_imag_m_s2": base_phasor.imag,
                **phasor_metrics("relative_displacement_m", actual_relative),
                **phasor_metrics("relative_velocity_m_s", actual_relative_velocity),
                **phasor_metrics("relative_acceleration_m_s2", actual_relative_acceleration),
                **phasor_metrics("absolute_displacement_m", actual_absolute_displacement),
                **phasor_metrics("absolute_velocity_m_s", actual_absolute_velocity),
                **phasor_metrics("absolute_acceleration_m_s2", actual_absolute_acceleration),
                "reduced_backward_error": (
                    None if record.get("reduced_backward_error") is None else float(record["reduced_backward_error"])
                ),
                "physical_free_backward_error": (
                    None
                    if record.get("physical_free_backward_error") is None
                    else float(record["physical_free_backward_error"])
                ),
            }
        )

    serialization_fields = (
        "responses",
        "relative_velocity_responses",
        "relative_acceleration_responses",
        "absolute_responses",
        "absolute_velocity_responses",
        "absolute_acceleration_responses",
    )
    serialization_results: dict[str, bool] = {field: False for field in serialization_fields}
    serialization_error: str | None = None
    execution_key_preserved = False
    try:
        restored = ReducedHarmonicResult.from_dict(result.to_dict())
        for field in serialization_fields:
            actual_values = getattr(restored, field)
            expected_values = getattr(result, field)
            field_matches = actual_values is not None and expected_values is not None
            if field_matches:
                field_matches = len(actual_values) == len(expected_values)
                if field_matches:
                    for actual, expected in zip(actual_values, expected_values):
                        if actual is None:
                            field_matches = expected is None
                        elif expected is None or not np.array_equal(actual, expected, equal_nan=True):
                            field_matches = False
                        if not field_matches:
                            break
            serialization_results[field] = bool(field_matches)
        execution_key_preserved = restored.execution_key == result.execution_key
    except Exception as exc:
        serialization_error = f"{type(exc).__name__}: {exc}"
    checks.extend(
        [
            (f"serialized {field} responses round-trip exactly", matched)
            for field, matched in serialization_results.items()
        ]
    )
    checks.append(("serialized execution key is preserved", execution_key_preserved))
    checks.append(("frequency records cover the full sweep", len(records) == len(frequencies_hz)))
    payload: dict[str, object] = {
        "case": "WP12-WP07-COMPLEX-BASE-SWEEP",
        "nodeid": "tests/unit/test_wp07_uniform_base_acceleration.py::test_wp12_base_acceleration_complex_sweep_checks_frames_sign_and_serialization",
        "units": {
            "frequency": "Hz",
            "base_acceleration": "m/s^2",
            "displacement": "m",
            "velocity": "m/s",
            "acceleration": "m/s^2",
            "phase": "rad",
            "backward_error": "dimensionless",
        },
        "natural_frequency_hz": natural_frequency_hz,
        "input_base_acceleration_m_s2": {"real": acceleration.real, "imag": acceleration.imag},
        "assertion_results": {label: passed for label, passed in checks},
        "serialization": {
            "field_round_trip_exact": serialization_results,
            "execution_key_preserved": execution_key_preserved,
            "error": serialization_error,
        },
        "observations": observations,
        "frame_contract": {
            "base_direction_frame": "global_model_axes",
            "base_direction_vector": [1.0, 0.0, 0.0],
            "probe_dof": "node 1 UX in the global model frame",
            "relative_acceleration": "-omega^2 * U_relative",
            "absolute_acceleration": "relative_acceleration + A_g",
            "dc_absolute_displacement_velocity": "UNAVAILABLE",
            "phasor_time_convention": "exp(+i*omega*t)",
        },
    }
    artifact = _publish_wp12_observables_before_assertions(
        case_name="wp12-base-acceleration-complex-sweep-observables",
        nodeid=str(payload["nodeid"]),
        payload=payload,
        checks=checks,
    )
    print(
        json.dumps(
            {"artifact": artifact},
            sort_keys=True,
            allow_nan=False,
        )
    )


def test_harmonic_base_and_wp03_force_superpose_without_losing_phasor_phase() -> None:
    frequency = 1.25
    model = _beam_model("harmonic", frequency_hz=frequency, acceleration=2.0j)
    prepared, basis = _prepare(model)
    force = _explicit_harmonic_force(frequency, 0.0 + 3.0j)
    result = ReducedHarmonicResponseSolver().solve(
        model,
        source_sha=_SOURCE_SHA,
        prepared=prepared,
        basis=basis,
        excitation_channels=force,
    )
    dofs = model.dof_manager()
    free = int(prepared.free_dof_indices[0])
    index = dofs.index(1, "UX")
    force_full = force.bind(prepared).full_harmonic_rhs(prepared, frequency_hz=frequency)
    direction = np.zeros(dofs.ndof)
    direction[dofs.index(0, "UX")] = 1.0
    direction[dofs.index(1, "UX")] = 1.0
    expected_rhs = force_full[free] - (prepared.mass_full @ direction)[free] * 2.0j
    omega = 2.0 * math.pi * frequency
    z = prepared.stiffness_full[free, free] - omega**2 * prepared.mass_full[free, free]
    assert result.responses[0][index] == pytest.approx(expected_rhs / z, rel=1.0e-11, abs=1.0e-13)
    assert result.execution_identity["uniform_base_acceleration_identity"]
    assert result.solver["frequency_records"][0]["base_acceleration_phasor_m_s2"] == {
        "real": 0.0,
        "imag": 2.0,
    }


def test_harmonic_rayleigh_damping_acts_on_relative_velocity_only() -> None:
    frequency = 1.25
    acceleration = 0.7 - 0.4j
    model = _beam_model("harmonic", frequency_hz=frequency, acceleration=acceleration)
    model.analysis.parameters["rayleigh_alpha"] = 0.3
    prepared, basis = _prepare(model)
    result = ReducedHarmonicResponseSolver().solve(model, source_sha=_SOURCE_SHA, prepared=prepared, basis=basis)

    dofs = model.dof_manager()
    free = int(prepared.free_dof_indices[0])
    influence = np.zeros(dofs.ndof)
    influence[dofs.index(0, "UX")] = 1.0
    influence[dofs.index(1, "UX")] = 1.0
    mass = prepared.mass_full
    stiffness = prepared.stiffness_full
    damping = 0.3 * mass
    omega = 2.0 * math.pi * frequency
    equivalent_force = -(mass @ influence)[free] * acceleration
    impedance = stiffness[free, free] + 1j * omega * damping[free, free] - omega**2 * mass[free, free]
    tip = dofs.index(1, "UX")
    assert result.responses[0][tip] == pytest.approx(equivalent_force / impedance, rel=1.0e-11, abs=1.0e-13)
    assert result.solver["uniform_base_acceleration"]["stiffness_and_damping"].startswith(
        "relative structural operators"
    )


def test_full_basis_harmonic_matches_direct_route_with_equivalent_complex_nodal_forces() -> None:
    frequency = 1.25
    acceleration = 0.7 - 0.4j
    model = _beam_model("harmonic", frequency_hz=frequency, acceleration=acceleration)
    model.analysis.parameters["rayleigh_alpha"] = 0.3
    prepared, basis = _prepare(model)
    reduced = ReducedHarmonicResponseSolver().solve(model, source_sha=_SOURCE_SHA, prepared=prepared, basis=basis)

    influence = np.zeros(prepared.mass_full.shape[0])
    dofs = model.dof_manager()
    for node, names in dofs.node_dofs.items():
        for component, dof in enumerate(("UX", "UY", "UZ")):
            if dof in names:
                influence[dofs.index(node, dof)] = (1.0, 0.0, 0.0)[component]
    equivalent_force = -(prepared.mass_full @ influence) * acceleration

    def direct_component(values: np.ndarray) -> np.ndarray:
        direct = copy.deepcopy(model)
        direct.analysis = replace(direct.analysis, method="direct_frequency")
        direct.analysis.parameters.pop("uniform_base_acceleration")
        direct.loads = [
            NodalLoad(node=node, dof=dof, value=float(values[dofs.index(node, dof)]))
            for node, names in dofs.node_dofs.items()
            for dof in names
            if abs(float(values[dofs.index(node, dof)])) > 0.0
        ]
        return HarmonicResponseSolver().solve(direct).responses[0]

    direct_complex = direct_component(equivalent_force.real) + 1j * direct_component(equivalent_force.imag)
    np.testing.assert_allclose(reduced.responses[0], direct_complex, rtol=1.0e-11, atol=1.0e-13)


def test_transient_base_acceleration_initial_equilibrium_absolute_acceleration_and_serialization() -> None:
    model = _beam_model(
        "transient",
        history=[{"time_s": 0.0, "value": 2.0}, {"time_s": 0.01, "value": 2.0}],
    )
    prepared, basis = _prepare(model)
    result = ModalNewmarkTransientSolver().solve(model, source_sha=_SOURCE_SHA, prepared=prepared, basis=basis)
    dofs = model.dof_manager()
    tip = dofs.index(1, "UX")
    support = dofs.index(0, "UX")
    load_per_acceleration = float(
        prepare_base_acceleration(
            UniformBaseAcceleration.from_mapping(
                model.analysis.parameters["uniform_base_acceleration"], route="transient", model=model
            ),
            model,
            prepared,
            basis.modes,
        ).inertial_load_reduced_per_m_s2[0]
    )
    expected_relative_a0 = load_per_acceleration * 2.0 / float(prepared.mass[0, 0])
    assert result.time_history[0]["probes"]["tip"]["acceleration"] == pytest.approx(expected_relative_a0)
    assert result.time_history[0]["probes"]["tip"]["absolute_acceleration"] == pytest.approx(expected_relative_a0 + 2.0)
    assert result.absolute_accelerations is not None
    assert result.absolute_accelerations[support] == pytest.approx(2.0)
    assert result.absolute_accelerations[tip] == pytest.approx(result.accelerations[tip] + 2.0)
    assert result.to_dict()["final_state"]["response_frames"] == {
        "displacement": "RELATIVE_RESPONSE",
        "velocity": "RELATIVE_RESPONSE",
        "acceleration": "RELATIVE_RESPONSE",
        "absolute_acceleration": "ABSOLUTE_RESPONSE",
    }
    assert result.time_history[0]["response_frames"]["absolute_acceleration"] == "ABSOLUTE_RESPONSE"
    assert result.result_availability["absolute_displacement"]["status"] == "UNAVAILABLE"
    assert result.result_availability["absolute_velocity"]["status"] == "UNAVAILABLE"
    assert result.result_availability["absolute_acceleration"]["status"] == "AVAILABLE"
    assert result.result_availability["physical_reactions"]["status"] == "AVAILABLE"
    restored = ModalNewmarkResult.from_dict(result.to_dict())
    np.testing.assert_array_equal(restored.absolute_accelerations, result.absolute_accelerations)
    assert restored.maturity == "EXPERIMENTAL"


def test_transient_base_sdof_matches_independent_constant_acceleration_solution() -> None:
    acceleration = 2.0
    dt = 1.0e-4
    steps = 100
    final_time = dt * steps
    model = _beam_model(
        "transient",
        history=[{"time_s": 0.0, "value": acceleration}, {"time_s": final_time, "value": acceleration}],
        extra_parameters={"time_step": dt, "steps": steps},
    )
    prepared, basis = _prepare(model)
    result = ModalNewmarkTransientSolver().solve(model, source_sha=_SOURCE_SHA, prepared=prepared, basis=basis)

    # Independent closed-form oscillator response with the inertial coefficient
    # formed directly from M_full and the explicit global influence vector.
    dofs = model.dof_manager()
    influence = np.zeros(dofs.ndof)
    for node, names in dofs.node_dofs.items():
        if "UX" in names:
            influence[dofs.index(node, "UX")] = 1.0
    free = int(prepared.free_dof_indices[0])
    base_force_per_acceleration = -float((prepared.mass_full @ influence)[free])
    modal_mass = float(prepared.mass[0, 0])
    stiffness = float(prepared.stiffness[0, 0])
    omega_n = math.sqrt(stiffness / modal_mass)
    constant_rhs_acceleration = base_force_per_acceleration * acceleration / modal_mass

    times = np.asarray([row["time_s"] for row in result.time_history])
    expected_displacement = constant_rhs_acceleration / omega_n**2 * (1.0 - np.cos(omega_n * times))
    expected_velocity = constant_rhs_acceleration / omega_n * np.sin(omega_n * times)
    expected_acceleration = constant_rhs_acceleration * np.cos(omega_n * times)
    actual_displacement = np.asarray([row["probes"]["tip"]["displacement"] for row in result.time_history])
    actual_velocity = np.asarray([row["probes"]["tip"]["velocity"] for row in result.time_history])
    actual_acceleration = np.asarray([row["probes"]["tip"]["acceleration"] for row in result.time_history])
    np.testing.assert_allclose(actual_displacement, expected_displacement, rtol=1.0e-5, atol=1.0e-12)
    np.testing.assert_allclose(actual_velocity, expected_velocity, rtol=1.0e-5, atol=1.0e-11)
    np.testing.assert_allclose(actual_acceleration, expected_acceleration, rtol=1.0e-5, atol=5.0e-6)


def test_transient_base_acceleration_superposes_with_legacy_external_force() -> None:
    model = _beam_model(
        "transient",
        history=[{"time_s": 0.0, "value": 2.0}, {"time_s": 0.01, "value": 2.0}],
    )
    model.loads = [NodalLoad(node=1, dof="UX", value=3.0)]
    prepared, basis = _prepare(model)
    result = ModalNewmarkTransientSolver().solve(model, source_sha=_SOURCE_SHA, prepared=prepared, basis=basis)
    channels = ExcitationChannelSet.from_model_inputs(model, prepared).bind(prepared)
    external = channels.full_real_rhs(prepared, time_s=0.0, step=0, steps=10, dt=0.001)
    specification = UniformBaseAcceleration.from_mapping(
        model.analysis.parameters["uniform_base_acceleration"], route="transient", model=model
    )
    base = prepare_base_acceleration(specification, model, prepared, basis.modes)
    combined = prepared.reduce_load(external + 2.0 * base.inertial_load_full_per_m_s2)
    expected = np.linalg.solve(prepared.mass.toarray(), combined)
    assert result.time_history[0]["probes"]["tip"]["acceleration"] == pytest.approx(
        expected[0], rel=1.0e-12, abs=1.0e-13
    )


def test_base_excitation_identity_changes_restart_signature_and_modal_damping_reactions_stay_unavailable(
    tmp_path,
) -> None:
    checkpoint_path = tmp_path / "wp07-state.npz"
    first = _beam_model(
        "transient",
        history=[{"time_s": 0.0, "value": 1.0}, {"time_s": 0.01, "value": 1.0}],
        extra_parameters={
            "steps": 4,
            "checkpoint_path": str(checkpoint_path),
            "checkpoint_interval": 2,
            "checkpoint_keep_steps": True,
        },
    )
    complete = ModalNewmarkTransientSolver().solve(first, source_sha=_SOURCE_SHA)
    restart_file = tmp_path / "wp07-state.step00000002.npz"
    same = _beam_model(
        "transient",
        history=[{"time_s": 0.0, "value": 1.0}, {"time_s": 0.01, "value": 1.0}],
        extra_parameters={"steps": 4, "restart_from": str(restart_file)},
    )
    resumed = ModalNewmarkTransientSolver().solve(same, source_sha=_SOURCE_SHA)
    np.testing.assert_allclose(resumed.displacements, complete.displacements, rtol=1.0e-12, atol=1.0e-14)
    np.testing.assert_allclose(
        resumed.absolute_accelerations, complete.absolute_accelerations, rtol=1.0e-12, atol=1.0e-14
    )
    changed = _beam_model(
        "transient",
        history=[{"time_s": 0.0, "value": 1.0}, {"time_s": 0.01, "value": 1.5}],
        extra_parameters={"steps": 4, "restart_from": str(restart_file)},
    )
    with pytest.raises(InputValidationError, match="restart is refused"):
        ModalNewmarkTransientSolver().solve(changed, source_sha=_SOURCE_SHA)

    prescribed = _beam_model(
        "transient",
        history=[{"time_s": 0.0, "value": 1.0}, {"time_s": 0.01, "value": 1.0}],
        extra_parameters={"reduced_damping_model": "prescribed_modal", "modal_damping_ratios": [0.02]},
    )
    prescribed.analysis.parameters.pop("rayleigh_alpha")
    prescribed.analysis.parameters.pop("rayleigh_beta")
    result = ModalNewmarkTransientSolver().solve(prescribed, source_sha=_SOURCE_SHA)
    assert result.reactions is None
    assert result.result_availability["physical_reactions"]["status"] == "UNAVAILABLE"


def test_fail_closed_zero_frequency_support_and_ground_spring_policies() -> None:
    zero_frequency = _beam_model("harmonic", frequency_hz=0.0, acceleration=1.0 + 0.0j)
    prepared, basis = _prepare(zero_frequency)
    with pytest.raises(InputValidationError, match="0 Hz"):
        ReducedHarmonicResponseSolver().solve(zero_frequency, source_sha=_SOURCE_SHA, prepared=prepared, basis=basis)

    zero_dc_component = _beam_model("harmonic", frequency_hz=0.0, acceleration=0.0j)
    zero_dc_result = ReducedHarmonicResponseSolver().solve(zero_dc_component, source_sha=_SOURCE_SHA)
    assert zero_dc_result.absolute_responses == (None,)
    assert zero_dc_result.absolute_velocity_responses == (None,)
    assert zero_dc_result.result_availability["absolute_complex_displacements"]["status"] == "UNAVAILABLE"
    assert zero_dc_result.relative_velocity_responses is not None
    assert zero_dc_result.absolute_acceleration_responses is not None
    assert zero_dc_result.result_availability["absolute_complex_accelerations"]["status"] == "AVAILABLE"
    dc_record = zero_dc_result.solver["frequency_records"][0]
    assert dc_record["base_displacement_phasor_m"] is None
    assert dc_record["absolute_kinematics_status"] == "UNAVAILABLE_ZERO_FREQUENCY_INTEGRATION_CONSTANTS"

    spring_without_policy = _beam_model("transient", grounded_spring=True)
    with pytest.raises(InputValidationError, match="grounded_spring_policy"):
        ModalNewmarkTransientSolver().solve(spring_without_policy, source_sha=_SOURCE_SHA)

    spring_comoving = _beam_model("transient", grounded_spring=True, grounded_spring_policy="COMOVING_WITH_BASE")
    result = ModalNewmarkTransientSolver().solve(spring_comoving, source_sha=_SOURCE_SHA)
    assert result.solver["uniform_base_acceleration"]["contract"]["grounded_spring_policy"] == "COMOVING_WITH_BASE"
    assert result.result_availability["comoving_spring_reference_reactions"]["status"] == "UNAVAILABLE"

    unsupported = copy.deepcopy(spring_comoving.analysis.parameters["uniform_base_acceleration"])
    unsupported["support_policy"] = "fixed_in_absolute_frame"
    invalid = _beam_model("transient")
    invalid.analysis.parameters["uniform_base_acceleration"] = unsupported
    with pytest.raises(InputValidationError, match="support_policy"):
        ModalNewmarkTransientSolver().solve(invalid, source_sha=_SOURCE_SHA)


def test_base_input_is_rejected_by_historical_direct_route_and_nonunit_direction() -> None:
    reduced_model = _beam_model("harmonic")
    direct_model = copy.deepcopy(reduced_model)
    direct_model.analysis = replace(direct_model.analysis, method="direct_frequency")
    with pytest.raises(InputValidationError, match="supported only by"):
        AnalysisRouter().solve(direct_model)

    invalid = _beam_model("harmonic")
    invalid.analysis.parameters["uniform_base_acceleration"]["direction"] = [2.0, 0.0, 0.0]
    with pytest.raises(InputValidationError, match="normalized"):
        ReducedHarmonicResponseSolver().solve(invalid, source_sha=_SOURCE_SHA)


def test_time_history_is_linear_endpoint_held_and_identity_is_order_stable() -> None:
    model = _beam_model(
        "transient",
        history=[{"time_s": 0.0, "value": 0.0}, {"time_s": 0.01, "value": 2.0}],
    )
    specification = UniformBaseAcceleration.from_mapping(
        model.analysis.parameters["uniform_base_acceleration"], route="transient", model=model
    )
    assert specification.acceleration_at(0.005) == pytest.approx(1.0)
    assert specification.acceleration_at(0.02) == pytest.approx(2.0)
    changed_history = _beam_model(
        "transient",
        history=[{"time_s": 0.0, "value": 0.0}, {"time_s": 0.01, "value": 3.0}],
    )
    first_prepared = PreparedDynamicSystem.prepare(model, source_sha=_SOURCE_SHA)
    changed_prepared = PreparedDynamicSystem.prepare(changed_history, source_sha=_SOURCE_SHA)
    assert first_prepared.operator_identity == changed_prepared.operator_identity
    assert first_prepared.physical_identity == changed_prepared.physical_identity
    first_history_spec = UniformBaseAcceleration.from_mapping(
        model.analysis.parameters["uniform_base_acceleration"], route="transient", model=model
    )
    changed_history_spec = UniformBaseAcceleration.from_mapping(
        changed_history.analysis.parameters["uniform_base_acceleration"], route="transient", model=changed_history
    )
    assert first_history_spec.identity != changed_history_spec.identity
    reordered = _beam_model(
        "harmonic",
        frequency_hz=0.0,
        acceleration=0.0j,
        direction=(1.0, 0.0, 0.0),
    )
    ordered_input = copy.deepcopy(reordered.analysis.parameters["uniform_base_acceleration"])
    ordered_input["harmonic_phasors"].append({"frequency_hz": 2.0, "real": 1.0, "imag": -0.5})
    reordered_input = copy.deepcopy(ordered_input)
    reordered_input["harmonic_phasors"] = list(reversed(reordered_input["harmonic_phasors"]))
    first = UniformBaseAcceleration.from_mapping(ordered_input, route="harmonic", model=reordered)
    second = UniformBaseAcceleration.from_mapping(reordered_input, route="harmonic", model=reordered)
    assert first.identity == second.identity
    assert first.phasor_at(0.0) == 0.0j


def test_wp07_contract_freezes_method_maturity_frame_and_historical_statuses() -> None:
    root = Path(__file__).parents[2]
    contract = json.loads(
        (root / "qualification/0_2_12/wp07_uniform_base_acceleration_contract.json").read_text(encoding="utf-8")
    )
    assert contract["routes"]["maturity"] == "EXPERIMENTAL"
    assert contract["routes"]["qualification"] == "NOT_ASSESSED"
    assert contract["routes"]["numerical_pass_implies_qualification"] is False
    assert contract["physical_formulation"]["full_mass_before_constraint_reduction"] is True
    assert contract["preregistered_tolerances"]["post_observation_relaxation"] is False
    assert contract["historical_statuses"] == {
        "HISTORICAL_G03": "FAIL_PRESERVED",
        "HISTORICAL_WP14": "HOLD_NOT_PROMOTED",
        "WHOLE_REPOSITORY_ARCHIVE_CLEARED": "NO",
        "maturity_promotion": "NONE",
    }
