from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Callable

import pytest

from test_modal_newmark import (
    _publish_wp12_observables_before_assertions as publish_newmark,
    _write_wp12_attempt_observables as write_newmark,
)
from test_reduced_harmonic import (
    _publish_wp12_observables_before_assertions as publish_harmonic,
    _write_wp12_attempt_observables as write_harmonic,
)
from test_wp07_uniform_base_acceleration import (
    _publish_wp12_observables_before_assertions as publish_base_acceleration,
    _write_wp12_attempt_observables as write_base_acceleration,
)


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
) -> tuple[Path, str, dict[str, object]]:
    evidence_root = tmp_path / "evidence"
    manifest_dir = evidence_root / "authorizations" / "wp12_dynamics"
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
        "attempt": 1,
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


@pytest.mark.parametrize(("writer", "publish", "nodeid", "case"), WRITER_CASES)
def test_synthetic_sidecar_pass_and_no_overwrite(
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
    assert archived["attempt_identity"]["attempt"] == 1
    assert not list(output_dir.glob("*.tmp"))

    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        writer(case_name=case_name, nodeid=nodeid, payload={"case": "replacement"})
    assert artifact_path.read_bytes() == original_bytes


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
    assert archived["attempt_identity"]["attempt"] == 1
    assert not list(output_dir.glob("*.tmp"))
