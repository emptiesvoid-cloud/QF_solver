"""Six exact research nodes for the gated HEX8-SRI cantilever campaign."""

from __future__ import annotations

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

from experiments.hex8_sri_equilibrium.campaign import (
    ROOT,
    assemble_and_solve,
    atomic_write_json_new,
    atomic_write_new_bytes,
    make_run_sidecar,
)


CAMPAIGN_DIR = ROOT / "investigations/hex8_sri_equilibrium_20261026/campaign_preparation"
FORMULATION_CASES = (
    pytest.param("hex8_standard", 0.3, "hex8_standard_nu_0p3", id="hex8_standard_nu_0p3"),
    pytest.param("sri_historical", 0.3, "sri_historical_nu_0p3", id="sri_historical_nu_0p3"),
    pytest.param("sri_corrected", 0.3, "sri_corrected_nu_0p3", id="sri_corrected_nu_0p3"),
    pytest.param("hex8_standard", 0.4999, "hex8_standard_nu_0p4999", id="hex8_standard_nu_0p4999"),
    pytest.param("sri_historical", 0.4999, "sri_historical_nu_0p4999", id="sri_historical_nu_0p4999"),
    pytest.param("sri_corrected", 0.4999, "sri_corrected_nu_0p4999", id="sri_corrected_nu_0p4999"),
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _controller_source_fingerprint(nodeid: str) -> str:
    controller_path = ROOT / "scripts/development_autonomous.py"
    spec = importlib.util.spec_from_file_location("hex8sri_campaign_controller", controller_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the frozen controller fingerprint function")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module._worktree_source_fingerprint(ROOT, nodeid)


def _authorized_case(request: pytest.FixtureRequest, case_id: str) -> tuple[Path, dict, str]:
    """Fail closed before assembly unless controller and final manifest agree."""
    nodeid = request.node.nodeid
    manifest_path = CAMPAIGN_DIR / f"manifest_{case_id}.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_sha256 = _sha256(manifest_path)
    expected = {
        "QF_DEVELOPMENT_AUTONOMOUS": "1",
        "QF_DEV_WORKTREE_ID": "hex8sri",
        "QF_DEV_TARGET_NODEID": nodeid,
        "QF_DEV_MANIFEST_SHA256": manifest_sha256,
    }
    mismatches = {key: (os.environ.get(key), value) for key, value in expected.items() if os.environ.get(key) != value}
    if mismatches:
        raise RuntimeError(f"HEX8-SRI execution refused: controller identity mismatch {mismatches}")
    if manifest.get("execution_authorized") is not True or manifest.get("do_not_execute") is not False:
        raise RuntimeError("HEX8-SRI execution refused: the final case manifest is not Owner-authorized")
    if manifest.get("exact_nodeid") != nodeid:
        raise RuntimeError("HEX8-SRI execution refused: case manifest does not bind this exact nodeid")
    required_controller = (
        "QF_DEV_CONTROLLER_ROOT",
        "QF_DEV_CONTROLLER_HEAD",
        "QF_DEV_CONTROLLER_RUNNER_SHA256",
        "QF_DEV_CONTROLLER_POLICY_SHA256",
        "QF_DEV_CONTROLLER_PLUGIN_SHA256",
    )
    if any(not os.environ.get(key) for key in required_controller):
        raise RuntimeError("HEX8-SRI execution refused: controller provenance is incomplete")
    source_head = manifest.get("science_source_commit")
    if not isinstance(source_head, str) or subprocess.run(
        ["git", "merge-base", "--is-ancestor", source_head, "HEAD"], cwd=ROOT, check=False
    ).returncode != 0:
        raise RuntimeError("HEX8-SRI execution refused: frozen source commit is not an ancestor of this worktree")
    fingerprint = _controller_source_fingerprint(nodeid)
    if manifest.get("source_fingerprint_sha256") != fingerprint:
        raise RuntimeError("HEX8-SRI execution refused: science source fingerprint differs from the frozen manifest")
    if manifest.get("controller_code_sha256", {}).get("runner") != os.environ["QF_DEV_CONTROLLER_RUNNER_SHA256"]:
        raise RuntimeError("HEX8-SRI execution refused: controller runner hash differs from the frozen manifest")
    if manifest.get("controller_code_sha256", {}).get("pytest_plugin") != os.environ["QF_DEV_CONTROLLER_PLUGIN_SHA256"]:
        raise RuntimeError("HEX8-SRI execution refused: controller plugin hash differs from the frozen manifest")
    return manifest_path, manifest, fingerprint


@pytest.mark.parametrize(("formulation", "poisson_ratio", "case_id"), FORMULATION_CASES)
def test_hex8_sri_cantilever_campaign(
    formulation: str,
    poisson_ratio: float,
    case_id: str,
    request: pytest.FixtureRequest,
) -> None:
    """Run one approved case, persist all diagnostics, then apply frozen criteria."""
    manifest_path, manifest, source_fingerprint = _authorized_case(request, case_id)
    manifest_sha256 = _sha256(manifest_path)
    run_started = time.perf_counter()
    record, arrays = assemble_and_solve(formulation, poisson_ratio)

    arrays_buffer = BytesIO()
    np.savez_compressed(arrays_buffer, **arrays)
    artifact_root = Path(manifest["execution_artifact_root"])
    state_path = artifact_root / f"state_{case_id}_attempt-001.npz"
    state_sha256 = atomic_write_new_bytes(state_path, arrays_buffer.getvalue())
    try:
        import psutil

        rss_bytes = int(psutil.Process().memory_info().rss)
    except ImportError:
        rss_bytes = None
    record["resource_observations"] = {
        "process_rss_bytes_at_postprocess": rss_bytes,
        "process_rss_semantics": "single in-process snapshot; controller sampled peak RSS is authoritative for the run envelope",
        "state_artifact_bytes": state_path.stat().st_size,
        "test_elapsed_seconds_before_assertions": time.perf_counter() - run_started,
    }
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
        "source_fingerprint_sha256": source_fingerprint,
    }
    sidecar = make_run_sidecar(
        record=record,
        arrays_path=state_path,
        arrays_sha256=state_sha256,
        manifest_path=manifest_path,
        manifest_sha256=manifest_sha256,
        science_identity=science_identity,
        controller_identity=controller_identity,
    )
    sidecar_path = artifact_root / f"sidecar_{case_id}_attempt-001.json"
    sidecar_sha256 = atomic_write_json_new(sidecar_path, sidecar)

    # Evidence is durable before the first criterion assertion.
    assert sidecar_path.is_file() and _sha256(sidecar_path) == sidecar_sha256
    verdicts = record["criteria_verdicts"]
    assert verdicts["all_observed_arrays_finite"] == "PASS"
    assert verdicts["all_center_and_gauss_jacobians_positive"] == "PASS"
    assert verdicts["existing_direct_relative_residual_tolerance_1e-7"] == "PASS"
