from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
from pathlib import Path
import uuid

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
    if manifest_path.parent.name != "wp12_dynamics" or manifest_path.parent.parent.name != "authorizations":
        raise RuntimeError("The execution manifest is outside the registered WP12 dynamics authorization directory.")
    manifest_bytes = manifest_path.read_bytes()
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    if manifest_ref.get("sha256") != manifest_sha256:
        raise RuntimeError("The execution-manifest hash changed after the launcher recorded it.")
    manifest = json.loads(manifest_bytes)

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
    if manifest_path.parent != expected_authorization_dir:
        raise RuntimeError("The execution manifest is outside the policy-configured WP12 evidence root.")
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


def test_wp12_harmonic_sweep_separates_full_basis_route_error_from_truncation() -> None:
    """Emit complex response, phase, and residual observations around retained/omitted modes."""
    seed = _model(frequencies=[1.0])
    prepared, full_basis = _prepare(seed)
    natural_frequencies = np.sqrt(np.asarray(full_basis.eigenvalues, dtype=float)) / (2.0 * math.pi)
    checks: list[tuple[str, bool]] = [
        ("natural-frequency count matches reduced size", bool(natural_frequencies.size == prepared.reduced_size)),
        ("first natural frequency is positive", bool(natural_frequencies.size > 0 and natural_frequencies[0] > 0.0)),
        (
            "last natural frequency exceeds first",
            bool(natural_frequencies.size > 1 and natural_frequencies[-1] > natural_frequencies[0]),
        ),
    ]

    frequency_values = sorted(
        {
            0.0,
            0.5 * float(natural_frequencies[0]),
            0.98 * float(natural_frequencies[0]),
            1.02 * float(natural_frequencies[0]),
            0.98 * float(natural_frequencies[-1]),
            1.02 * float(natural_frequencies[-1]),
        }
    )
    seed.analysis.parameters["frequencies_hz"] = frequency_values
    full_basis_result = ReducedHarmonicResponseSolver().solve(
        seed,
        source_sha=_SOURCE_SHA,
        prepared=prepared,
        basis=full_basis,
    )

    direct_model = copy.deepcopy(seed)
    direct_model.analysis = AnalysisSettings.from_raw(
        {
            "type": "harmonic_response",
            "method": "direct_frequency",
            **direct_model.analysis.parameters,
        }
    )
    direct_result = HarmonicResponseSolver().solve(direct_model)

    truncated_model = copy.deepcopy(seed)
    truncated_model.analysis.parameters["modal_mode_count"] = 2
    truncated_prepared, truncated_basis = _prepare(truncated_model)
    checks.append(
        (
            "truncated and full physical identities match",
            truncated_prepared.physical_identity == prepared.physical_identity,
        )
    )
    truncated_result = ReducedHarmonicResponseSolver().solve(
        truncated_model,
        source_sha=_SOURCE_SHA,
        prepared=truncated_prepared,
        basis=truncated_basis,
    )

    checks.extend(
        [
            ("full modal basis is complete", bool(full_basis.is_full_basis)),
            ("comparison modal basis is truncated", bool(not truncated_basis.is_full_basis)),
            (
                "direct/full/truncated frequency counts match",
                len(full_basis_result.responses) == len(direct_result.responses) == len(truncated_result.responses),
            ),
        ]
    )
    records = full_basis_result.solver["frequency_records"]
    truncated_records = truncated_result.solver["frequency_records"]
    reduced_backward_errors = [float(row["reduced_backward_error"]) for row in records]
    physical_backward_errors = [
        None if row.get("physical_free_backward_error") is None else float(row["physical_free_backward_error"])
        for row in records
    ]
    maximum_reduced_backward_error = max(reduced_backward_errors, default=None)
    maximum_physical_backward_error = (
        max(value for value in physical_backward_errors if value is not None)
        if physical_backward_errors and all(value is not None for value in physical_backward_errors)
        else None
    )
    checks.extend(
        [
            (
                "full-basis reduced backward errors <= 1e-8",
                maximum_reduced_backward_error is not None and maximum_reduced_backward_error <= 1.0e-8,
            ),
            (
                "full-basis physical free backward errors <= 1e-8",
                maximum_physical_backward_error is not None and maximum_physical_backward_error <= 1.0e-8,
            ),
            (
                "frequency-record counts match requested sweep",
                len(records) == len(frequency_values) and len(truncated_records) == len(frequency_values),
            ),
        ]
    )

    observations: list[dict[str, float | str | None]] = []
    response_index = seed.dof_manager().index(1, "UX")
    for frequency_hz, direct, full, truncated, record, truncated_record in zip(
        frequency_values,
        direct_result.responses,
        full_basis_result.responses,
        truncated_result.responses,
        records,
        truncated_records,
    ):
        direct_response = complex(direct[response_index])
        full_response = complex(full[response_index])
        truncated_response = complex(truncated[response_index])
        direct_norm = max(float(np.linalg.norm(direct)), np.finfo(float).tiny)
        observations.append(
            {
                "frequency_hz": float(frequency_hz),
                "direct_probe_amplitude": abs(direct_response),
                "direct_probe_phase_rad": (None if abs(direct_response) == 0.0 else float(np.angle(direct_response))),
                "direct_probe_real_m": direct_response.real,
                "direct_probe_imag_m": direct_response.imag,
                "full_basis_probe_amplitude": abs(full_response),
                "full_basis_probe_phase_rad": (None if abs(full_response) == 0.0 else float(np.angle(full_response))),
                "full_basis_probe_real_m": full_response.real,
                "full_basis_probe_imag_m": full_response.imag,
                "truncated_probe_amplitude": abs(truncated_response),
                "truncated_probe_phase_rad": (
                    None if abs(truncated_response) == 0.0 else float(np.angle(truncated_response))
                ),
                "truncated_probe_real_m": truncated_response.real,
                "truncated_probe_imag_m": truncated_response.imag,
                "full_basis_phase_error_rad": float(np.angle(full_response * np.conjugate(direct_response))),
                "truncated_phase_error_rad": float(np.angle(truncated_response * np.conjugate(direct_response))),
                "full_basis_vector_relative_error": float(np.linalg.norm(full - direct) / direct_norm),
                "truncated_vector_relative_difference": float(np.linalg.norm(truncated - direct) / direct_norm),
                "reduced_backward_error": float(record["reduced_backward_error"]),
                "full_basis_physical_free_backward_error": (
                    None
                    if record["physical_free_backward_error"] is None
                    else float(record["physical_free_backward_error"])
                ),
                "conditioning_indicator": float(record["conditioning_indicator"]),
                "conditioning_status": str(record["conditioning_status"]),
                "truncated_physical_free_backward_error": (
                    None
                    if truncated_record["physical_free_backward_error"] is None
                    else float(truncated_record["physical_free_backward_error"])
                ),
            }
        )

    maximum_full_basis_error = max(
        (item["full_basis_vector_relative_error"] for item in observations),
        default=None,
    )
    checks.append(
        (
            "full-basis vector relative error <= 1e-8",
            maximum_full_basis_error is not None
            and math.isfinite(maximum_full_basis_error)
            and maximum_full_basis_error <= 1.0e-8,
        )
    )
    payload: dict[str, object] = {
        "case": "WP12-HARMONIC-COMPLEX-SWEEP",
        "nodeid": "tests/unit/test_reduced_harmonic.py::test_wp12_harmonic_sweep_separates_full_basis_route_error_from_truncation",
        "units": {
            "frequency": "Hz",
            "probe_displacement": "m",
            "phase": "rad",
            "backward_error": "dimensionless",
            "conditioning_indicator": "dimensionless",
        },
        "probe": "node 1 UX in the global model frame",
        "phasor_time_convention": "exp(+i*omega*t)",
        "natural_frequencies_hz": natural_frequencies.tolist(),
        "frequency_values_hz": frequency_values,
        "maximum_full_basis_vector_relative_error": maximum_full_basis_error,
        "assertion_results": {label: passed for label, passed in checks},
        "observations": observations,
        "interpretation": {
            "full_basis_vs_direct": "route/projection/linear-solve cross-check on shared assembled operators",
            "truncated_vs_direct": "combined omitted-subspace and solve difference; not an error bound",
        },
    }
    artifact = _publish_wp12_observables_before_assertions(
        case_name="wp12-harmonic-complex-sweep-observables",
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
