from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Callable

import numpy as np
import pytest

from test_modal_newmark import (
    _publish_wp12_observables_before_assertions as publish_newmark,
    _write_wp12_attempt_observables as write_newmark,
)
from test_reduced_harmonic import (
    _wp12_complex_array,
    _wp12_harmonic_vector_observation,
    _wp12_modal_observation,
    _wp12_phase_error,
    _publish_wp12_observables_before_assertions as publish_harmonic,
    _write_wp12_attempt_observables as write_harmonic,
)
from test_wp07_uniform_base_acceleration import (
    _publish_wp12_observables_before_assertions as publish_base_acceleration,
    _write_wp12_attempt_observables as write_base_acceleration,
)


def test_synthetic_harmonic_vector_observation_preserves_complex_residuals() -> None:
    # Fixed synthetic arrays only: this does not assemble or solve a FEM model.
    stiffness = np.diag([2.0, 4.0])
    mass = np.zeros((2, 2))
    damping = np.zeros((2, 2))
    direct = np.array([1.0 + 2.0j, 0.0j])
    full = np.array([1.25 + 2.0j, 0.0j])
    force = np.array([2.0 + 4.0j, 0.0j])
    result = _wp12_harmonic_vector_observation(
        3.0, stiffness, mass, damping, force, np.array([0]), direct, full, direct
    )
    assert result["omega_rad_s"] == pytest.approx(6.0 * math.pi)
    assert result["full_minus_direct_m"] == {"shape": [2], "real": [0.25, 0.0], "imag": [0.0, 0.0]}
    assert result["physical_free_residual_N"]["direct"] == {"shape": [1], "real": [0.0], "imag": [0.0]}
    assert result["physical_free_residual_N"]["full_basis"] == {"shape": [1], "real": [0.5], "imag": [0.0]}
    assert result["full_minus_direct_absolute_norm_m"] == pytest.approx(0.25)
    assert result["full_minus_direct_relative_norm"] == pytest.approx(0.25 / math.sqrt(5.0))
    assert _wp12_complex_array(np.array([[1 + 2j, -3j]])) == {
        "shape": [1, 2], "real": [[1.0, 0.0]], "imag": [[2.0, -3.0]]
    }


def test_synthetic_harmonic_vector_observation_zero_reference_and_invalid_inputs() -> None:
    matrix = np.eye(2)
    zero = np.zeros(2, dtype=complex)
    result = _wp12_harmonic_vector_observation(0.0, matrix, matrix, matrix, zero, np.array([0]), zero, zero, zero)
    assert result["relative_error_defined"] is False
    assert result["full_minus_direct_relative_norm"] is None
    near_zero = np.array([1e-320, 0.0], dtype=complex)
    near_result = _wp12_harmonic_vector_observation(
        0.0, matrix, matrix, matrix, zero, np.array([0]), near_zero, zero, zero
    )
    assert near_result["relative_error_defined"] is False
    assert near_result["full_minus_direct_relative_norm"] is None
    with pytest.raises(ValueError, match="Frequency"):
        _wp12_harmonic_vector_observation(float("nan"), matrix, matrix, matrix, zero, np.array([0]), zero, zero, zero)
    with pytest.raises(ValueError, match="dimensions"):
        _wp12_harmonic_vector_observation(1.0, np.eye(3), matrix, matrix, zero, np.array([0]), zero, zero, zero)


def test_synthetic_modal_residual_and_reconstruction_are_independent_observables() -> None:
    # Explicit small arrays, with no solver or FEM assembly.
    modes = np.array([[1.0], [0.0]])
    q = np.array([2.0 + 1.0j])
    free = np.array([2.0 + 1.0j, 0.5j])
    force = np.array([4.0 + 2.0j, 0.0])
    result = _wp12_modal_observation(0.0, modes, np.eye(1), 2.0 * np.eye(1), np.eye(1), q, free, force)
    assert result["projected_force"] == {"shape": [1], "real": [4.0], "imag": [2.0]}
    assert result["modal_residual"] == {"shape": [1], "real": [0.0], "imag": [0.0]}
    assert result["reconstruction_absolute_norm_m"] == pytest.approx(0.5)


def test_synthetic_zero_phasor_does_not_claim_a_phase_error() -> None:
    assert _wp12_phase_error(complex(-0.0, 0.0), -1.0 + 0.0j) is None
    assert _wp12_phase_error(1.0 + 0.0j, 0.0j) is None
    assert _wp12_phase_error(1.0j, 1.0 + 0.0j) == pytest.approx(math.pi / 2.0)
NEWMARK_NODEID = (
    "tests/unit/test_modal_newmark.py::test_wp12_newmark_fixed_time_state_refinement_residual_and_energy_observables"
)
HARMONIC_NODEID = (
    "tests/unit/test_reduced_harmonic.py::test_wp12_harmonic_sweep_separates_full_basis_route_error_from_truncation"
)
BASE_ACCELERATION_NODEID = (
    "tests/unit/test_wp07_uniform_base_acceleration.py::"
    "test_wp12_base_acceleration_complex_sweep_checks_frames_sign_and_serialization"
)

WRITER_CASES = (
    pytest.param(write_newmark, publish_newmark, NEWMARK_NODEID, "newmark", id="newmark"),
    pytest.param(write_harmonic, publish_harmonic, HARMONIC_NODEID, "harmonic", id="harmonic"),
    pytest.param(
        write_base_acceleration,
        publish_base_acceleration,
        BASE_ACCELERATION_NODEID,
        "base-acceleration",
        id="base-acceleration",
    ),
)


def _synthetic_attempt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    nodeid: str,
    series_id: str,
    owner_authorized: bool = False,
) -> tuple[Path, str, dict[str, object]]:
    evidence_root = tmp_path / "evidence"
    manifest_dir = evidence_root / "authorizations" / "wp12_dynamics"
    if owner_authorized:
        manifest_dir = manifest_dir / "owner-authorized"
    attempt_dir = evidence_root / "worktrees" / "wp12_dynamics" / series_id / "attempt-0001"
    temp_dir = attempt_dir / "tmp"
    output_dir = attempt_dir / "output"
    controller_root = tmp_path / "controller"
    manifest_dir.mkdir(parents=True)
    temp_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True)
    controller_root.mkdir()

    policy_path = controller_root / "development_autonomous_policy.json"
    policy_bytes = json.dumps(
        {"worktrees": {"wp12_dynamics": {"evidence_root": str(evidence_root)}}},
        sort_keys=True,
    ).encode("utf-8")
    policy_path.write_bytes(policy_bytes)
    policy_sha256 = hashlib.sha256(policy_bytes).hexdigest()

    identity: dict[str, object] = {
        "branch": "codex/wp12-dynamic-harmonic-verification",
        "head": "synthetic-head",
        "root": "synthetic-worktree-root",
        "status_short": "",
        "tree": "synthetic-tree",
    }
    source_fingerprint = "1" * 64
    authorization_id = f"synthetic-{series_id}"
    manifest_path = manifest_dir / f"{authorization_id}.json"
    manifest = {
        "schema": "qfsolver-wp12-development-execution-v1",
        "state": "OWNER_AUTHORIZED",
        "authorization_id": authorization_id,
        "worktree_id": "wp12_dynamics",
        "target": nodeid,
        "identity": identity,
        "source_fingerprint": source_fingerprint,
        "controller_fingerprint": "2" * 64,
        "limits": {},
        "owner_decision": {"status": "APPROVED", "approved_by": "Owner"},
    }
    manifest_bytes = json.dumps(manifest, sort_keys=True).encode("utf-8")
    manifest_path.write_bytes(manifest_bytes)
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()

    run_record: dict[str, object] = {
        "state": "RUNNING",
        "worktree_id": "wp12_dynamics",
        "target": [nodeid],
        "series_id": series_id,
        "attempt": 2,
        "execution_manifest": {
            "path": str(manifest_path),
            "sha256": manifest_sha256,
            "authorization_id": authorization_id,
        },
        "identity": identity,
        "source_fingerprint": source_fingerprint,
        "controller_provenance": {
            "identity": {"root": str(controller_root)},
            "sha256": {"policy": policy_sha256},
        },
    }
    (attempt_dir / "run.json").write_text(json.dumps(run_record), encoding="utf-8")
    monkeypatch.setenv("QF_DEVELOPMENT_AUTONOMOUS", "1")
    monkeypatch.setenv("QF_DEV_WORKTREE_ID", "wp12_dynamics")
    monkeypatch.setenv("TMP", str(temp_dir))
    monkeypatch.setenv("TEMP", str(temp_dir))
    return output_dir, authorization_id, run_record


def _rewrite_run_record(output_dir: Path, run_record: dict[str, object]) -> None:
    (output_dir.parent / "run.json").write_text(json.dumps(run_record), encoding="utf-8")


def test_synthetic_complex_diagnostics_are_archived_with_nonfinite_markers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_dir, _, _ = _synthetic_attempt(tmp_path, monkeypatch, nodeid=HARMONIC_NODEID, series_id="complex-data")
    encoded = _wp12_complex_array(np.array([complex(float("nan"), 2.0)]))
    artifact = write_harmonic(case_name="complex-data", nodeid=HARMONIC_NODEID, payload={"values": encoded})
    path = Path(artifact["path"])
    content = path.read_bytes()
    archived = json.loads(content)
    assert path.parent == output_dir
    assert archived["values"] == {"shape": [1], "real": [None], "imag": [2.0]}
    assert archived["non_finite_values"]["$.values.real[0]"] == "nan"
    assert artifact["sha256"] == hashlib.sha256(content).hexdigest()


@pytest.mark.parametrize(("writer", "publish", "nodeid", "case"), WRITER_CASES)
def test_synthetic_global_attempt_two_archives_local_series_attempt_one(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    writer: Callable[..., dict[str, str]],
    publish: Callable[..., dict[str, str]],
    nodeid: str,
    case: str,
) -> None:
    short_case = {"newmark": "nm", "harmonic": "ha", "base-acceleration": "ba"}[case]
    output_dir, _, _ = _synthetic_attempt(
        tmp_path,
        monkeypatch,
        nodeid=nodeid,
        series_id=f"sp-{short_case}",
    )
    case_name = f"pass-{short_case}"
    payload: dict[str, object] = {"case": case, "assertion_results": {"controlled-pass": True}}
    artifact = publish(
        case_name=case_name,
        nodeid=nodeid,
        payload=payload,
        checks=[("controlled synthetic acceptance", True)],
    )
    artifact_path = Path(artifact["path"])
    original_bytes = artifact_path.read_bytes()
    archived = json.loads(original_bytes)
    assert artifact_path.parent == output_dir
    assert hashlib.sha256(original_bytes).hexdigest() == artifact["sha256"]
    assert archived["case"] == case
    assert archived["attempt_identity"]["series_id"] == f"sp-{short_case}"
    assert archived["attempt_identity"]["attempt"] == 2
    assert archived["attempt_identity"]["series_attempt"] == 1
    assert not list(output_dir.glob("*.tmp"))

    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        writer(case_name=case_name, nodeid=nodeid, payload={"case": "replacement"})
    assert artifact_path.read_bytes() == original_bytes


@pytest.mark.parametrize(("writer", "publish", "nodeid", "case"), WRITER_CASES)
def test_synthetic_writer_accepts_owner_authorized_manifest_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    writer: Callable[..., dict[str, str]],
    publish: Callable[..., dict[str, str]],
    nodeid: str,
    case: str,
) -> None:
    short_case = {"newmark": "nm", "harmonic": "ha", "base-acceleration": "ba"}[case]
    output_dir, authorization_id, _run_record = _synthetic_attempt(
        tmp_path,
        monkeypatch,
        nodeid=nodeid,
        series_id=f"oa-{short_case}",
        owner_authorized=True,
    )

    artifact = writer(case_name=f"oa-{short_case}", nodeid=nodeid, payload={"case": case})

    artifact_path = Path(artifact["path"])
    assert artifact_path.parent == output_dir
    assert hashlib.sha256(artifact_path.read_bytes()).hexdigest() == artifact["sha256"]
    archived = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert archived["attempt_identity"]["authorization_id"] == authorization_id
    assert archived["case"] == case
    assert not list(output_dir.glob("*.tmp"))


@pytest.mark.parametrize(("writer", "publish", "nodeid", "case"), WRITER_CASES)
def test_synthetic_writer_rejects_nested_manifest_outside_exact_authorization_directories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    writer: Callable[..., dict[str, str]],
    publish: Callable[..., dict[str, str]],
    nodeid: str,
    case: str,
) -> None:
    short_case = {"newmark": "nm", "harmonic": "ha", "base-acceleration": "ba"}[case]
    output_dir, _authorization_id, run_record = _synthetic_attempt(
        tmp_path,
        monkeypatch,
        nodeid=nodeid,
        series_id=f"nm-{short_case}",
        owner_authorized=True,
    )
    manifest_ref = run_record["execution_manifest"]
    assert isinstance(manifest_ref, dict)
    authorized_manifest = Path(str(manifest_ref["path"]))
    nested_manifest = authorized_manifest.parent / "nested" / authorized_manifest.name
    nested_manifest.parent.mkdir()
    nested_manifest.write_bytes(authorized_manifest.read_bytes())
    manifest_ref["path"] = str(nested_manifest)
    _rewrite_run_record(output_dir, run_record)

    with pytest.raises(RuntimeError, match="outside the policy-configured WP12 evidence root"):
        writer(case_name=f"nm-{short_case}", nodeid=nodeid, payload={"case": case})

    assert not (output_dir / f"nm-{short_case}.json").exists()
    assert not list(output_dir.glob("*.tmp"))


@pytest.mark.parametrize(("writer", "publish", "nodeid", "case"), WRITER_CASES)
def test_synthetic_sidecar_survives_assertion_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    writer: Callable[..., dict[str, str]],
    publish: Callable[..., dict[str, str]],
    nodeid: str,
    case: str,
) -> None:
    short_case = {"newmark": "nm", "harmonic": "ha", "base-acceleration": "ba"}[case]
    output_dir, _, _ = _synthetic_attempt(
        tmp_path,
        monkeypatch,
        nodeid=nodeid,
        series_id=f"sf-{short_case}",
    )
    case_name = f"fail-{short_case}"
    payload: dict[str, object] = {
        "case": case,
        "assertion_results": {"controlled-failure": False},
        "synthetic_observable": math.nan,
    }
    with pytest.raises(AssertionError, match="after observables were archived"):
        publish(
            case_name=case_name,
            nodeid=nodeid,
            payload=payload,
            checks=[("controlled synthetic failure", False)],
        )

    artifact_path = output_dir / f"{case_name}.json"
    archived = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert archived["case"] == case
    assert archived["synthetic_observable"] is None
    assert archived["non_finite_values"]["$.synthetic_observable"] == "nan"
    assert archived["assertion_results"] == {"controlled-failure": False}
    assert archived["attempt_identity"]["series_id"] == f"sf-{short_case}"
    assert archived["attempt_identity"]["attempt"] == 2
    assert archived["attempt_identity"]["series_attempt"] == 1
    assert not list(output_dir.glob("*.tmp"))


@pytest.mark.parametrize(("writer", "publish", "nodeid", "case"), WRITER_CASES)
def test_synthetic_writer_rejects_wrong_series(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    writer: Callable[..., dict[str, str]],
    publish: Callable[..., dict[str, str]],
    nodeid: str,
    case: str,
) -> None:
    output_dir, _, run_record = _synthetic_attempt(
        tmp_path, monkeypatch, nodeid=nodeid, series_id=f"wrong-series-{case}"
    )
    run_record["series_id"] = f"different-series-{case}"
    _rewrite_run_record(output_dir, run_record)

    with pytest.raises(RuntimeError, match="series/attempt identity"):
        writer(case_name=f"wrong-series-{case}", nodeid=nodeid, payload={"case": case})

    assert not (output_dir / f"wrong-series-{case}.json").exists()
    assert not list(output_dir.glob("*.tmp"))


@pytest.mark.parametrize(("writer", "publish", "nodeid", "case"), WRITER_CASES)
def test_synthetic_writer_rejects_manifest_bound_to_another_nodeid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    writer: Callable[..., dict[str, str]],
    publish: Callable[..., dict[str, str]],
    nodeid: str,
    case: str,
) -> None:
    output_dir, _, run_record = _synthetic_attempt(
        tmp_path, monkeypatch, nodeid=nodeid, series_id=f"wrong-manifest-{case}"
    )
    manifest_ref = run_record["execution_manifest"]
    assert isinstance(manifest_ref, dict)
    manifest_path = Path(str(manifest_ref["path"]))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["target"] = "tests/unit/test_other.py::test_not_authorized_here"
    manifest_bytes = json.dumps(manifest, sort_keys=True).encode("utf-8")
    manifest_path.write_bytes(manifest_bytes)
    manifest_ref["sha256"] = hashlib.sha256(manifest_bytes).hexdigest()
    _rewrite_run_record(output_dir, run_record)

    with pytest.raises(RuntimeError, match="source/controller identity"):
        writer(case_name=f"wrong-manifest-{case}", nodeid=nodeid, payload={"case": case})

    assert not (output_dir / f"wrong-manifest-{case}.json").exists()
    assert not list(output_dir.glob("*.tmp"))


@pytest.mark.parametrize(("writer", "publish", "nodeid", "case"), WRITER_CASES)
def test_synthetic_writer_rejects_output_outside_evidence_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    writer: Callable[..., dict[str, str]],
    publish: Callable[..., dict[str, str]],
    nodeid: str,
    case: str,
) -> None:
    output_dir, _, run_record = _synthetic_attempt(
        tmp_path, monkeypatch, nodeid=nodeid, series_id=f"wrong-path-{case}"
    )
    series_id = str(run_record["series_id"])
    outside_attempt_dir = tmp_path / "outside-evidence" / "worktrees" / "wp12_dynamics" / series_id / "attempt-0001"
    outside_temp_dir = outside_attempt_dir / "tmp"
    outside_output_dir = outside_attempt_dir / "output"
    outside_temp_dir.mkdir(parents=True)
    outside_output_dir.mkdir()
    (outside_attempt_dir / "run.json").write_text(json.dumps(run_record), encoding="utf-8")
    monkeypatch.setenv("TMP", str(outside_temp_dir))
    monkeypatch.setenv("TEMP", str(outside_temp_dir))

    with pytest.raises(RuntimeError, match="outside the evidence root"):
        writer(case_name=f"wrong-path-{case}", nodeid=nodeid, payload={"case": case})

    assert not (outside_output_dir / f"wrong-path-{case}.json").exists()
    assert not (output_dir / f"wrong-path-{case}.json").exists()
    assert not list(outside_output_dir.glob("*.tmp"))


@pytest.mark.parametrize(("writer", "publish", "nodeid", "case"), WRITER_CASES)
def test_synthetic_writer_rejects_unapproved_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    writer: Callable[..., dict[str, str]],
    publish: Callable[..., dict[str, str]],
    nodeid: str,
    case: str,
) -> None:
    output_dir, _, run_record = _synthetic_attempt(
        tmp_path, monkeypatch, nodeid=nodeid, series_id=f"unauthorized-{case}"
    )
    manifest_ref = run_record["execution_manifest"]
    assert isinstance(manifest_ref, dict)
    manifest_path = Path(str(manifest_ref["path"]))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["state"] = "PREPARED_NOT_AUTHORIZED"
    manifest["owner_decision"] = {"status": "NOT_AUTHORIZED", "approved_by": None}
    manifest_bytes = json.dumps(manifest, sort_keys=True).encode("utf-8")
    manifest_path.write_bytes(manifest_bytes)
    manifest_ref["sha256"] = hashlib.sha256(manifest_bytes).hexdigest()
    _rewrite_run_record(output_dir, run_record)

    with pytest.raises(RuntimeError, match="source/controller identity"):
        writer(case_name=f"unauthorized-{case}", nodeid=nodeid, payload={"case": case})

    assert not (output_dir / f"unauthorized-{case}.json").exists()
    assert not list(output_dir.glob("*.tmp"))
