"""Synthetic child-gate contracts for the optimized TET4-L3 diagnostic scope."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from experiments.wp12_vv3d_adaptive import case_harness
from tests.unit.test_wp12_vv3d_adaptive_prepared import _synthetic_runner_manifest


def _write_json(path: Path, value: dict) -> bytes:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    path.write_bytes(raw)
    return raw


def _synthetic_scope_binding(tmp_path: Path, monkeypatch, *, scope: str, timeout: int,
                             ledger_name: str, case_id: str = "VV3D-TET4-L3") -> tuple[dict, dict, Path, Path]:
    """Bind temporary manifest, preflight receipt and reservation receipt; never reserve."""
    manifest, env = _synthetic_runner_manifest(tmp_path, case_id)
    manifest["scope_id"] = scope
    manifest["timeout_seconds"] = timeout
    manifest_path = Path(env["QF_DEV_MANIFEST_PATH"])
    manifest_raw = _write_json(manifest_path, manifest)
    env["QF_DEV_MANIFEST_SHA256"] = hashlib.sha256(manifest_raw).hexdigest()

    receipt_path = Path(env["QF_DEV_VV3D_RUNNER_RECEIPT_PATH"])
    receipt = json.loads(receipt_path.read_bytes())
    receipt.update({
        "manifest_sha256": env["QF_DEV_MANIFEST_SHA256"],
        "ledger_scope_id": scope,
        "ledger_path": str(tmp_path / ledger_name),
        "timeout_seconds": timeout,
        "campaign_seconds_reserved_after": max(timeout, receipt["campaign_seconds_reserved_after"]),
    })
    receipt_raw = _write_json(receipt_path, receipt)
    env["QF_DEV_VV3D_RUNNER_RECEIPT_SHA256"] = hashlib.sha256(receipt_raw).hexdigest()
    env["QF_DEV_WORKTREE_ID"] = scope
    env["QF_VV3D_PERFORMANCE_TRACE"] = "1"
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    return manifest, receipt, manifest_path, receipt_path


@pytest.mark.parametrize(
    ("scope", "timeout", "ledger_name"),
    [
        (case_harness.TET4_L3_DIAGNOSTIC_SCOPE,
         case_harness.TET4_L3_DIAGNOSTIC_TIMEOUT_SECONDS,
         case_harness.TET4_L3_DIAGNOSTIC_LEDGER),
        (case_harness.TET4_L3_OPTIMIZED_DIAGNOSTIC_SCOPE,
         case_harness.TET4_L3_OPTIMIZED_DIAGNOSTIC_TIMEOUT_SECONDS,
         case_harness.TET4_L3_OPTIMIZED_DIAGNOSTIC_LEDGER),
    ],
)
def test_diagnostic_gate_binds_manifest_preflight_and_reservation_receipt(
    tmp_path: Path, monkeypatch, scope: str, timeout: int, ledger_name: str,
) -> None:
    _, receipt, _, _ = _synthetic_scope_binding(
        tmp_path, monkeypatch, scope=scope, timeout=timeout, ledger_name=ledger_name,
    )

    context = case_harness.require_authorized_execution("VV3D-TET4-L3")

    assert context["campaign_id"] == "WP12-VV3D-RECOVERY-20261030-R2"
    assert context["nodeid"] == "tests/unit/test_wp12_vv3d_adaptive_prepared.py::test_prepared_fem_case[VV3D-TET4-L3]"
    assert receipt["ledger_scope_id"] == scope
    assert Path(receipt["ledger_path"]).name == ledger_name
    assert receipt["timeout_seconds"] == timeout


def test_optimized_diagnostic_gate_rejects_wrong_manifest_scope(tmp_path: Path, monkeypatch) -> None:
    manifest, receipt, manifest_path, receipt_path = _synthetic_scope_binding(
        tmp_path, monkeypatch,
        scope=case_harness.TET4_L3_OPTIMIZED_DIAGNOSTIC_SCOPE,
        timeout=case_harness.TET4_L3_OPTIMIZED_DIAGNOSTIC_TIMEOUT_SECONDS,
        ledger_name=case_harness.TET4_L3_OPTIMIZED_DIAGNOSTIC_LEDGER,
    )
    manifest["scope_id"] = case_harness.TET4_L3_DIAGNOSTIC_SCOPE
    manifest_raw = _write_json(manifest_path, manifest)
    monkeypatch.setenv("QF_DEV_MANIFEST_SHA256", hashlib.sha256(manifest_raw).hexdigest())
    receipt["manifest_sha256"] = hashlib.sha256(manifest_raw).hexdigest()
    receipt_raw = _write_json(receipt_path, receipt)
    monkeypatch.setenv("QF_DEV_VV3D_RUNNER_RECEIPT_SHA256", hashlib.sha256(receipt_raw).hexdigest())

    with pytest.raises(PermissionError, match="manifest does not bind"):
        case_harness.require_authorized_execution("VV3D-TET4-L3")


@pytest.mark.parametrize("field", ["ledger_scope_id", "ledger_path"])
def test_optimized_diagnostic_gate_rejects_wrong_ledger_binding(
    tmp_path: Path, monkeypatch, field: str,
) -> None:
    _, receipt, _, receipt_path = _synthetic_scope_binding(
        tmp_path, monkeypatch,
        scope=case_harness.TET4_L3_OPTIMIZED_DIAGNOSTIC_SCOPE,
        timeout=case_harness.TET4_L3_OPTIMIZED_DIAGNOSTIC_TIMEOUT_SECONDS,
        ledger_name=case_harness.TET4_L3_OPTIMIZED_DIAGNOSTIC_LEDGER,
    )
    receipt[field] = (
        "wp12_vv3d_recovery_r2" if field == "ledger_scope_id"
        else str(tmp_path / case_harness.VV3D_LEDGER_FILENAME)
    )
    receipt_raw = _write_json(receipt_path, receipt)
    monkeypatch.setenv("QF_DEV_VV3D_RUNNER_RECEIPT_SHA256", hashlib.sha256(receipt_raw).hexdigest())

    with pytest.raises(PermissionError, match="runner receipt does not bind"):
        case_harness.require_authorized_execution("VV3D-TET4-L3")


@pytest.mark.parametrize("target", ["manifest", "receipt"])
def test_optimized_diagnostic_gate_rejects_wrong_timeout(
    tmp_path: Path, monkeypatch, target: str,
) -> None:
    manifest, receipt, manifest_path, receipt_path = _synthetic_scope_binding(
        tmp_path, monkeypatch,
        scope=case_harness.TET4_L3_OPTIMIZED_DIAGNOSTIC_SCOPE,
        timeout=case_harness.TET4_L3_OPTIMIZED_DIAGNOSTIC_TIMEOUT_SECONDS,
        ledger_name=case_harness.TET4_L3_OPTIMIZED_DIAGNOSTIC_LEDGER,
    )
    if target == "manifest":
        manifest["timeout_seconds"] += 1
        manifest_raw = _write_json(manifest_path, manifest)
        monkeypatch.setenv("QF_DEV_MANIFEST_SHA256", hashlib.sha256(manifest_raw).hexdigest())
        receipt["manifest_sha256"] = hashlib.sha256(manifest_raw).hexdigest()
    else:
        receipt["timeout_seconds"] += 1
    receipt_raw = _write_json(receipt_path, receipt)
    monkeypatch.setenv("QF_DEV_VV3D_RUNNER_RECEIPT_SHA256", hashlib.sha256(receipt_raw).hexdigest())

    with pytest.raises(PermissionError):
        case_harness.require_authorized_execution("VV3D-TET4-L3")


def test_optimized_diagnostic_gate_rejects_other_case(tmp_path: Path, monkeypatch) -> None:
    _synthetic_scope_binding(
        tmp_path, monkeypatch,
        scope=case_harness.TET4_L3_OPTIMIZED_DIAGNOSTIC_SCOPE,
        timeout=case_harness.TET4_L3_OPTIMIZED_DIAGNOSTIC_TIMEOUT_SECONDS,
        ledger_name=case_harness.TET4_L3_OPTIMIZED_DIAGNOSTIC_LEDGER,
    )

    with pytest.raises(PermissionError, match="exact case and active tracing"):
        case_harness.require_authorized_execution("VV3D-TET4-L2")


def test_optimized_diagnostic_gate_requires_trace_flag(tmp_path: Path, monkeypatch) -> None:
    _synthetic_scope_binding(
        tmp_path, monkeypatch,
        scope=case_harness.TET4_L3_OPTIMIZED_DIAGNOSTIC_SCOPE,
        timeout=case_harness.TET4_L3_OPTIMIZED_DIAGNOSTIC_TIMEOUT_SECONDS,
        ledger_name=case_harness.TET4_L3_OPTIMIZED_DIAGNOSTIC_LEDGER,
    )
    monkeypatch.delenv("QF_VV3D_PERFORMANCE_TRACE")

    with pytest.raises(PermissionError, match="exact case and active tracing"):
        case_harness.require_authorized_execution("VV3D-TET4-L3")


def test_optimized_diagnostic_gate_rejects_unrecognized_scope(tmp_path: Path, monkeypatch) -> None:
    _synthetic_scope_binding(
        tmp_path, monkeypatch,
        scope=case_harness.TET4_L3_OPTIMIZED_DIAGNOSTIC_SCOPE,
        timeout=case_harness.TET4_L3_OPTIMIZED_DIAGNOSTIC_TIMEOUT_SECONDS,
        ledger_name=case_harness.TET4_L3_OPTIMIZED_DIAGNOSTIC_LEDGER,
    )
    monkeypatch.setenv("QF_DEV_WORKTREE_ID", "wp12_vv3d_tet4_l3_optimized_diagnostic_typo")

    with pytest.raises(PermissionError):
        case_harness.require_authorized_execution("VV3D-TET4-L3")
