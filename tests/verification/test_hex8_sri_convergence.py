"""Twenty-four exact research nodes for the prepared HEX8-SRI convergence lot.

These nodes assemble and solve FEM systems. They are deliberately not covered
by the current six-node controller registration and must not be run until a
separate controller configuration and Owner decision bind their manifests.
"""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np
import pytest

from experiments.hex8_sri_equilibrium.campaign import atomic_write_json_new, atomic_write_new_bytes
from experiments.hex8_sri_equilibrium.convergence import (
    run_convergence_case,
)
from experiments.hex8_sri_equilibrium.campaign_spec import (
    FORMULATIONS,
    MESH_LEVELS,
    POISSON_RATIOS,
    convergence_case_id,
    convergence_nodeid,
)


ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_DIR = ROOT / "investigations/hex8_sri_equilibrium_20261026/campaign_preparation/first_convergence_24"
CASE_PARAMETERS = tuple(
    pytest.param(
        formulation,
        nu,
        mesh,
        convergence_case_id(formulation, nu, mesh),
        id=convergence_nodeid(formulation, nu, mesh).split("[", maxsplit=1)[1][:-1],
    )
    for formulation in FORMULATIONS
    for nu in POISSON_RATIOS
    for mesh in MESH_LEVELS
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _source_fingerprint(nodeid: str) -> str:
    controller_path = ROOT / "scripts/development_autonomous.py"
    spec = importlib.util.spec_from_file_location("hex8sri_convergence_controller", controller_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the controller source-fingerprint function")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module._worktree_source_fingerprint(ROOT, nodeid)


def _authorized_case(request: pytest.FixtureRequest, case_id: str) -> tuple[Path, dict, str]:
    """Fail closed before any FEM assembly unless controller and manifest agree."""
    nodeid = request.node.nodeid
    manifest_path = Path(os.environ.get("QF_DEV_MANIFEST_PATH", CAMPAIGN_DIR / f"manifest_{case_id}.json"))
    resolved_manifest_path = manifest_path.resolve()
    try:
        resolved_manifest_path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise RuntimeError("HEX8-SRI convergence refused: manifest path escapes the science worktree") from exc
    if not resolved_manifest_path.is_file() or resolved_manifest_path.name != f"manifest_{case_id}.json":
        raise RuntimeError("HEX8-SRI convergence refused: exact case manifest is missing or misnamed")
    manifest_path = resolved_manifest_path
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_sha256 = _sha256(manifest_path)
    expected_environment = {
        "QF_DEVELOPMENT_AUTONOMOUS": "1",
        "QF_DEV_WORKTREE_ID": "hex8sri",
        "QF_DEV_TARGET_NODEID": nodeid,
        "QF_DEV_MANIFEST_SHA256": manifest_sha256,
    }
    mismatches = {
        key: (os.environ.get(key), value) for key, value in expected_environment.items() if os.environ.get(key) != value
    }
    if mismatches:
        raise RuntimeError(f"HEX8-SRI convergence refused before FEM: controller identity mismatch {mismatches}")
    if manifest.get("execution_authorized") is not True or manifest.get("do_not_execute") is not False:
        raise RuntimeError("HEX8-SRI convergence refused: the final manifest is not Owner-authorized")
    if manifest.get("criteria_status") != "OWNER_FROZEN" or manifest.get("exact_nodeid") != nodeid:
        raise RuntimeError("HEX8-SRI convergence refused: criteria or exact node identity is not frozen")
    if manifest.get("case_id") != case_id:
        raise RuntimeError("HEX8-SRI convergence refused: manifest case ID differs from the exact node")
    required_controller = (
        "QF_DEV_CONTROLLER_ROOT",
        "QF_DEV_CONTROLLER_HEAD",
        "QF_DEV_CONTROLLER_RUNNER_SHA256",
        "QF_DEV_CONTROLLER_POLICY_SHA256",
        "QF_DEV_CONTROLLER_PLUGIN_SHA256",
    )
    if any(not os.environ.get(key) for key in required_controller):
        raise RuntimeError("HEX8-SRI convergence refused: controller provenance is incomplete")
    if (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", manifest.get("science_source_commit", ""), "HEAD"],
            cwd=ROOT,
            check=False,
        ).returncode
        != 0
    ):
        raise RuntimeError("HEX8-SRI convergence refused: frozen source commit is not an ancestor of this worktree")

    fingerprint = _source_fingerprint(nodeid)
    if manifest.get("source_fingerprint_sha256") != fingerprint:
        raise RuntimeError("HEX8-SRI convergence refused: science source fingerprint differs from the manifest")
    controller_hashes = manifest.get("controller_code_sha256", {})
    if controller_hashes.get("runner") != os.environ["QF_DEV_CONTROLLER_RUNNER_SHA256"]:
        raise RuntimeError("HEX8-SRI convergence refused: runner SHA-256 differs from the manifest")
    if controller_hashes.get("pytest_plugin") != os.environ["QF_DEV_CONTROLLER_PLUGIN_SHA256"]:
        raise RuntimeError("HEX8-SRI convergence refused: pytest plugin SHA-256 differs from the manifest")
    if controller_hashes.get("policy") != os.environ["QF_DEV_CONTROLLER_POLICY_SHA256"]:
        raise RuntimeError("HEX8-SRI convergence refused: policy SHA-256 differs from the manifest")
    identity = manifest.get("controller_identity", {})
    if identity.get("branch") != "codex/hex8sri-controller-registration":
        raise RuntimeError("HEX8-SRI convergence refused: manifest controller branch is not the registered branch")
    if identity.get("head") != os.environ["QF_DEV_CONTROLLER_HEAD"]:
        raise RuntimeError("HEX8-SRI convergence refused: controller HEAD differs from the manifest")
    if identity.get("runner_sha256") != controller_hashes.get("runner"):
        raise RuntimeError("HEX8-SRI convergence refused: controller runner identity fields disagree")
    if identity.get("pytest_plugin_sha256") != controller_hashes.get("pytest_plugin"):
        raise RuntimeError("HEX8-SRI convergence refused: controller plugin identity fields disagree")
    if identity.get("policy_sha256") != controller_hashes.get("policy"):
        raise RuntimeError("HEX8-SRI convergence refused: controller policy identity fields disagree")
    return manifest_path, manifest, fingerprint


@pytest.mark.parametrize(("formulation", "poisson_ratio", "divisions_xyz", "case_id"), CASE_PARAMETERS)
def test_convergence_case(
    formulation: str,
    poisson_ratio: float,
    divisions_xyz: tuple[int, int, int],
    case_id: str,
    request: pytest.FixtureRequest,
) -> None:
    """Run one approved FEM case, archive it, then apply its frozen local gates."""
    manifest_path, manifest, fingerprint = _authorized_case(request, case_id)
    if (
        manifest.get("formulation", {}).get("id") != formulation
        or float(manifest.get("poisson_ratio", float("nan"))) != poisson_ratio
        or manifest.get("mesh", {}).get("divisions_xyz") != list(divisions_xyz)
    ):
        raise RuntimeError("HEX8-SRI convergence refused: manifest physics do not match the requested case")
    manifest_sha256 = _sha256(manifest_path)
    criteria = manifest["frozen_criteria"]
    artifact_root = Path(manifest["execution_artifact_root"])
    started = time.perf_counter()
    controller_identity = {
        "worktree_id": os.environ["QF_DEV_WORKTREE_ID"],
        "root": os.environ["QF_DEV_CONTROLLER_ROOT"],
        "head": os.environ["QF_DEV_CONTROLLER_HEAD"],
        "runner_sha256": os.environ["QF_DEV_CONTROLLER_RUNNER_SHA256"],
        "policy_sha256": os.environ["QF_DEV_CONTROLLER_POLICY_SHA256"],
        "pytest_plugin_sha256": os.environ["QF_DEV_CONTROLLER_PLUGIN_SHA256"],
    }
    science_identity = {
        "branch": _git("branch", "--show-current"),
        "head": _git("rev-parse", "HEAD"),
        "tree": _git("rev-parse", "HEAD^{tree}"),
        "source_fingerprint_sha256": fingerprint,
    }
    start_path = artifact_root / f"started_{case_id}_attempt-001.json"
    start_record = {
        "schema": "qfsolver-hex8-sri-convergence-attempt-v1",
        "attempt_status": "STARTED",
        "campaign_id": manifest["campaign_id"],
        "case_id": case_id,
        "manifest": {"path": str(manifest_path), "sha256": manifest_sha256},
        "exact_nodeid": request.node.nodeid,
        "attempt_number": 1,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "budget": manifest["budgets"],
        "science_identity": science_identity,
        "controller_identity": controller_identity,
    }
    start_sha256 = atomic_write_json_new(start_path, start_record)
    record: dict | None = None
    state_path: Path | None = None
    sidecar_path: Path | None = None
    sidecar_sha256: str | None = None
    try:
        record, state = run_convergence_case(formulation, poisson_ratio, divisions_xyz, criteria=criteria)

        state_buffer = BytesIO()
        np.savez_compressed(state_buffer, **state)
        state_path = artifact_root / f"state_{case_id}_attempt-001.npz"
        state_sha256 = atomic_write_new_bytes(state_path, state_buffer.getvalue())
        try:
            import psutil

            rss_bytes = int(psutil.Process().memory_info().rss)
        except ImportError:
            rss_bytes = None
        record["resource_observations"] = {
            "process_rss_bytes_at_postprocess": rss_bytes,
            "rss_semantics": "single process snapshot; controller sampled peak RSS is authoritative",
            "state_artifact_bytes": state_path.stat().st_size,
            "elapsed_seconds_before_assertions": time.perf_counter() - started,
        }
        sidecar = {
            "schema": "qfsolver-hex8-sri-convergence-sidecar-v1",
            "campaign_id": manifest["campaign_id"],
            "case_id": case_id,
            "attempt_receipt": {"path": str(start_path), "sha256": start_sha256},
            "manifest": {"path": str(manifest_path), "sha256": manifest_sha256},
            "state_artifact": {"path": str(state_path), "sha256": state_sha256},
            "science_identity": science_identity,
            "controller_identity": controller_identity,
            **record,
        }
        sidecar_path = artifact_root / f"sidecar_{case_id}_attempt-001.json"
        sidecar_sha256 = atomic_write_json_new(sidecar_path, sidecar)
    except Exception as exc:
        failure = {
            "schema": "qfsolver-hex8-sri-convergence-attempt-v1",
            "attempt_status": "FAILED_DURING_EXECUTION_OR_ARCHIVING",
            "campaign_id": manifest["campaign_id"],
            "case_id": case_id,
            "exact_nodeid": request.node.nodeid,
            "attempt_number": 1,
            "manifest": {"path": str(manifest_path), "sha256": manifest_sha256},
            "attempt_receipt": {"path": str(start_path), "sha256": start_sha256},
            "science_identity": science_identity,
            "controller_identity": controller_identity,
            "elapsed_seconds_before_failure": time.perf_counter() - started,
            "failure_type": type(exc).__name__,
            "failure_message": str(exc),
            "state_artifact": (
                {"path": str(state_path), "sha256": _sha256(state_path)}
                if state_path is not None and state_path.is_file()
                else None
            ),
            "sidecar_written": sidecar_path is not None and sidecar_path.is_file(),
            "criteria_verdicts": record.get("criteria_verdicts") if record is not None else None,
        }
        failure_path = artifact_root / f"failure_{case_id}_attempt-001.json"
        atomic_write_json_new(failure_path, failure)
        raise

    # Persist full state and observables before the first assertion.
    assert state_path is not None and state_path.is_file()
    assert sidecar_path is not None and sidecar_path.is_file() and sidecar_sha256 is not None
    assert _sha256(state_path) == sidecar["state_artifact"]["sha256"]
    assert sidecar_path.is_file() and _sha256(sidecar_path) == sidecar_sha256
    assert record is not None
    for criterion_name, verdict in record["criteria_verdicts"].items():
        if criterion_name in {"independent_3d_reference_error", "single_case_convergence"}:
            continue
        assert verdict == "PASS", f"{criterion_name} failed; evidence was preserved"
