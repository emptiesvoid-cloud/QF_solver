"""Bounded installed-artifact smoke runner for the WP13 P0 candidate.

The runner is intentionally bound to the v6 wheel/sdist, three named input
examples, and one attempt per artifact/case pair. It is not a qualification
runner and cannot grant authorization. The run command requires a separate
Owner decision that matches the exact manifest and preflight report hashes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA = "qf-wp13-package-smoke-manifest-v1"
OWNER_SCHEMA = "qf-wp13-package-smoke-owner-decision-v1"
PACKAGE_SOURCE_SHA = "2865587a44f9e461a0b4e4286c912c17e4f04be5"
RELEASE_BASELINE_SHA = "ab137051d920d7fa9aae9a3012a48b2b26e2198b"
V6_CONTRACT_SHA = "f33a72b182439774828f8e604d6ab234bbf206c697c0f1082d7bc0ef81003db9"
ARTIFACT_SHA256 = {
    "wheel": "ae5211136a2eab912cdb73222937a84b1cec75f7af0a425f1162b288b39c287a",
    "sdist": "15c838af12c8401b61c561f5f079debc702e072241e9ee8c17cd5861cbf082e5",
}
INPUT_SHA256 = {
    "STATIC-01": "5296102b955ae4ac83b341178a8a555feb87faa0e9a30abe9f77c29df21988b8",
    "MODAL-01": "0d40df125888b467017d053795336cb8960f643c95a209c3c96379a50c689750",
    "DYNAMIC-01": "b40d7188143e4bcc73ee63407f426633490921075990bcad47bd25c9a188480b",
}
ORACLE_SOURCE_SHA256 = {
    "src/solveur/verification/analytical_references.py": "38ae37e1ff40844eedf7c2ca5b95d9d03f3fe660670036b05895c5043c96fb6c",
    "src/solveur/verification/campaign.py": "ea06968dc65927791549d698d19eeae33b6a3ad3e466ed2da0b87ae45e8952f1",
    "qualification/campaign.json": "8750d29a9d52498ec5051f4850c600232b0e7a4515905a8354f4a34771fd92cf",
}
CONTROLLED_THREAD_ENV = {
    "OMP_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
    "VECLIB_MAXIMUM_THREADS": "1",
    "OMP_DYNAMIC": "FALSE",
    "MKL_DYNAMIC": "FALSE",
}
CASE_INPUT = {
    "STATIC-01": "tet4_static.json",
    "MODAL-01": "tet4_modal_unit.json",
    "DYNAMIC-01": "tet4_dynamic_sdof_free_vibration.json",
}
EXPECTED_ORACLES: dict[str, dict[str, Any]] = {
    "STATIC-01": {
        "ux_m": 2.1224489795918369e-8,
        "ux_relative_tolerance": 1e-12,
        "von_mises_pa": 3428.5714285714284,
        "stress_relative_tolerance": 1e-12,
        "free_relative_residual_max": 1e-9,
        "reaction_resultant_x_n": -1000.0,
        "reaction_absolute_tolerance_n": 1e-10,
        "force_balance_relative_error_max": 1e-12,
        "linear_energy_identity_relative_error_max": 1e-9,
    },
    "MODAL-01": {
        "first_frequency_hz": 1619.5553821068941,
        "frequency_relative_tolerance": 1e-12,
        "max_relative_eigen_residual": 1e-10,
        "mass_orthogonality_error_max": 1e-10,
        "stiffness_diagonal_error_max": 1e-10,
    },
    "DYNAMIC-01": {
        "stiffness_n_per_m": 200.0,
        "mass_kg": 1.0 / 6.0,
        "initial_displacement_m": 0.001,
        "initial_velocity_m_s": 0.0,
        "expected_energy_j": 0.0001,
        "energy_relative_tolerance": 1e-10,
        "first_record_time_s": 0.001,
        "history_index": 39,
        "history_step": 40,
        "final_time_s": 0.04,
        "history_energy_consistency_absolute_tolerance_j": 1e-14,
        "relative_energy_drift_absolute_tolerance": 1e-10,
        "dynamic_residual_norm_max": 1e-10,
        "free_relative_residual_max": 1e-10,
    },
}
PAIR_ORDER = [
    {"artifact": artifact, "case": case}
    for artifact in ("wheel", "sdist")
    for case in ("STATIC-01", "MODAL-01", "DYNAMIC-01")
]
SYNTHETIC_MARKER = "WP13_SYNTHETIC_NO_FEM_ROUTE_PASS"


class ContractError(RuntimeError):
    """Raised when the frozen execution contract is incomplete or mismatched."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def load_manifest(path: Path, expected_sha256: str) -> tuple[dict[str, Any], str]:
    if not _is_sha256(expected_sha256):
        raise ContractError("expected manifest SHA-256 is malformed")
    raw = path.read_bytes()
    actual_sha256 = hashlib.sha256(raw).hexdigest()
    if actual_sha256 != expected_sha256:
        raise ContractError("manifest SHA-256 differs from the approved identity")
    try:
        manifest = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("manifest is not valid UTF-8 JSON") from exc
    _validate_manifest(manifest)
    controller_path = Path(__file__).resolve()
    if sha256_file(controller_path) != manifest["controller"]["sha256"]:
        raise ContractError("controller file SHA-256 differs from the frozen manifest")
    return manifest, actual_sha256


def _validate_manifest(manifest: object) -> None:
    if not isinstance(manifest, dict) or manifest.get("schema") != SCHEMA:
        raise ContractError("unsupported package-smoke manifest schema")
    candidate = manifest.get("candidate")
    if not isinstance(candidate, dict):
        raise ContractError("manifest candidate identity is missing")
    if candidate.get("package_source_sha") != PACKAGE_SOURCE_SHA:
        raise ContractError("manifest package source differs from the v6 source")
    if candidate.get("build_contract_sha256") != V6_CONTRACT_SHA:
        raise ContractError("manifest build-contract digest differs from v6")
    if candidate.get("release_baseline_sha") != RELEASE_BASELINE_SHA or candidate.get("pr_number") != 114:
        raise ContractError("release baseline or PR identity differs from the reviewed candidate")
    if manifest.get("oracle_sources") != ORACLE_SOURCE_SHA256:
        raise ContractError("independent oracle sources differ from the frozen v6 source identities")
    controller = manifest.get("controller")
    if not isinstance(controller, dict) or controller.get("path") != "scripts/wp13_package_smoke.py":
        raise ContractError("manifest controller path is not the frozen WP13 controller")
    if not _is_sha256(controller.get("sha256")):
        raise ContractError("controller SHA-256 is malformed")
    repo_root = Path(__file__).resolve().parents[1]

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != set(ARTIFACT_SHA256):
        raise ContractError("manifest must identify exactly the v6 wheel and sdist")
    for artifact_name, expected_hash in ARTIFACT_SHA256.items():
        artifact = artifacts[artifact_name]
        if not isinstance(artifact, dict) or artifact.get("archive_sha256") != expected_hash:
            raise ContractError(f"{artifact_name} archive does not match the frozen v6 hash")
        if not _is_sha256(artifact.get("install_report_sha256")):
            raise ContractError(f"{artifact_name} install report SHA-256 is malformed")
        for key in ("environment_root", "archive_path", "install_report_path", "examples_root"):
            if not isinstance(artifact.get(key), str) or not Path(artifact[key]).is_absolute():
                raise ContractError(f"{artifact_name} {key} must be an absolute path")
            if _is_relative_to(Path(artifact[key]).resolve(), repo_root):
                raise ContractError(f"{artifact_name} {key} must resolve outside the source checkout")

    cases = manifest.get("cases")
    if (
        not isinstance(cases, list)
        or len(cases) != len(CASE_INPUT)
        or not all(isinstance(item, dict) for item in cases)
        or {item.get("case_id") for item in cases} != set(CASE_INPUT)
    ):
        raise ContractError("manifest must contain exactly STATIC-01, MODAL-01, and DYNAMIC-01")
    for case in cases:
        case_id = case["case_id"]
        if case.get("input_name") != CASE_INPUT[case_id] or case.get("input_sha256") != INPUT_SHA256[case_id]:
            raise ContractError(f"{case_id} input identity differs from the frozen example")
        if case.get("oracles") != EXPECTED_ORACLES[case_id]:
            raise ContractError(f"{case_id} oracle values or tolerances differ from the frozen decision dossier")

    execution = manifest.get("execution")
    if not isinstance(execution, dict):
        raise ContractError("execution envelope is missing")
    if execution.get("pairs") != PAIR_ORDER:
        raise ContractError("execution pair order differs from the frozen six-case order")
    exact_limits = {
        "attempts_per_pair": 1,
        "serial": True,
        "stop_on_first_failure": True,
        "timeout_seconds": 30,
        "stdout_max_bytes": 1_048_576,
        "stderr_max_bytes": 1_048_576,
        "rss_soft_limit_mib": 512,
        "max_nodes": 4,
        "max_free_dofs": 3,
    }
    if any(type(execution.get(key)) is not type(value) or execution.get(key) != value for key, value in exact_limits.items()):
        raise ContractError("execution limits differ from the reviewed bounded smoke envelope")
    if execution.get("retry_policy") != "PROHIBITED" or execution.get("qualification_claim") != "NOT_CLAIMED":
        raise ContractError("manifest must prohibit retries and qualification claims")
    for key in ("evidence_root", "attempt_ledger_path", "preflight_report_path"):
        if not isinstance(manifest.get(key), str) or not Path(manifest[key]).is_absolute():
            raise ContractError(f"manifest {key} is missing")
    evidence_root = Path(manifest["evidence_root"]).resolve()
    ledger_path = Path(manifest["attempt_ledger_path"]).resolve()
    preflight_path = Path(manifest["preflight_report_path"]).resolve()
    if any(_is_relative_to(path, repo_root) for path in (evidence_root, ledger_path, preflight_path)):
        raise ContractError("evidence, ledger, and preflight paths must stay outside the source checkout")
    if _is_relative_to(preflight_path, evidence_root):
        raise ContractError("preflight report must be separate from the evidence root")
    if ledger_path.exists():
        raise ContractError("attempt ledger already exists; this manifest is single-use")


def preflight(
    manifest: dict[str, Any], manifest_sha256: str, *, allow_existing_report: bool = False
) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[1]
    evidence_root = Path(manifest["evidence_root"]).resolve()
    preflight_path = Path(manifest["preflight_report_path"]).resolve()
    if preflight_path.exists() != allow_existing_report:
        raise ContractError("preflight report state does not match the requested CLI stage")
    if evidence_root.exists() and any(evidence_root.iterdir()):
        raise ContractError("evidence root is not empty; refusing to reuse or overwrite it")
    if _git_output(root, "status", "--porcelain"):
        raise ContractError("controller checkout is not clean")
    observed_oracle_sources = _oracle_source_hashes(root)
    if observed_oracle_sources != ORACLE_SOURCE_SHA256:
        raise ContractError("candidate oracle source hashes differ from the frozen v6 identities")

    artifact_results: dict[str, Any] = {}
    for name, artifact in manifest["artifacts"].items():
        archive = Path(artifact["archive_path"]).resolve(strict=True)
        install_report = Path(artifact["install_report_path"]).resolve(strict=True)
        if sha256_file(archive) != artifact["archive_sha256"]:
            raise ContractError(f"{name} artifact file hash mismatch")
        if sha256_file(install_report) != artifact["install_report_sha256"]:
            raise ContractError(f"{name} installation report hash mismatch")
        environment = _probe_environment(Path(artifact["environment_root"]).resolve(strict=True), evidence_root)
        artifact_results[name] = {
            "archive_path": str(archive),
            "archive_sha256": artifact["archive_sha256"],
            "install_report_path": str(install_report),
            "install_report_sha256": artifact["install_report_sha256"],
            "environment": environment,
        }

    input_results: dict[str, dict[str, str]] = {}
    for artifact_name, artifact in manifest["artifacts"].items():
        examples_root = Path(artifact["examples_root"]).resolve(strict=True)
        input_results[artifact_name] = {}
        for case_id, input_name in CASE_INPUT.items():
            input_path = (examples_root / input_name).resolve(strict=True)
            if not _is_relative_to(input_path, examples_root):
                raise ContractError(f"{case_id} input escaped the installed examples directory")
            observed_hash = sha256_file(input_path)
            if observed_hash != INPUT_SHA256[case_id]:
                raise ContractError(f"{artifact_name}/{case_id} installed input hash mismatch")
            input_results[artifact_name][case_id] = observed_hash

    evidence_root.mkdir(parents=True, exist_ok=True)
    controlled_environment = _controlled_environment()

    return {
        "schema": "qf-wp13-package-smoke-preflight-v1",
        "status": "PASS_NO_FEM_PREFLIGHT",
        "manifest_sha256": manifest_sha256,
        "controller_sha256": manifest["controller"]["sha256"],
        "package_source_sha": PACKAGE_SOURCE_SHA,
        "oracle_sources": observed_oracle_sources,
        "observed_git_head": _git_output(root, "rev-parse", "HEAD"),
        "observed_branch": _git_output(root, "branch", "--show-current"),
        "observed_git_status": "CLEAN",
        "host_os": platform.platform(),
        "host_python": sys.version,
        "host_python_executable": str(Path(sys.executable).resolve()),
        "psutil_version": _psutil_version(),
        "controlled_thread_environment": {key: controlled_environment[key] for key in CONTROLLED_THREAD_ENV},
        "artifacts": artifact_results,
        "installed_inputs": input_results,
        "execution_authorized": False,
        "actual_attempt_reservations": 0,
        "fem_executed": False,
        "created_utc": _utc_now(),
    }


def _probe_environment(environment_root: Path, cwd: Path) -> dict[str, Any]:
    python = (environment_root / "Scripts" / "python.exe").resolve(strict=True)
    cli = (environment_root / "Scripts" / "qf-solver.exe").resolve(strict=True)
    if not python.is_file() or not cli.is_file():
        raise ContractError(f"installed environment is missing Python or qf-solver: {environment_root}")
    probe_code = (
        "import importlib.metadata,json,platform,solveur,sys; "
        "print(json.dumps({'version':importlib.metadata.version('qf-solver'),"
        "'python':platform.python_version(),'system':platform.system(),"
        "'solveur_file':str(solveur.__file__),'prefix':sys.prefix}))"
    )
    probe = subprocess.run(
        [str(python), "-I", "-c", probe_code],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
        env=_controlled_environment(),
    )
    if probe.returncode != 0:
        raise ContractError(f"installed import probe failed: {probe.stderr[-1000:]}")
    try:
        report = json.loads(probe.stdout)
    except json.JSONDecodeError as exc:
        raise ContractError("installed import probe did not return JSON") from exc
    package_file = Path(report["solveur_file"]).resolve(strict=True)
    site_packages = (environment_root / "Lib" / "site-packages").resolve(strict=True)
    if not _is_relative_to(package_file, site_packages):
        raise ContractError("solveur import did not resolve from the selected installed environment")
    if not _is_relative_to(python, environment_root) or not _is_relative_to(cli, environment_root):
        raise ContractError("Python or CLI executable resolves outside the selected installed environment")
    if report["version"] != "0.2.12" or report["python"] != "3.13.1" or report["system"] != "Windows":
        raise ContractError("installed environment version, Python, or OS differs from the reviewed matrix")
    version_probe = subprocess.run(
        [str(cli), "--version"],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
        env=_controlled_environment(),
    )
    if version_probe.returncode != 0 or "0.2.12" not in version_probe.stdout:
        raise ContractError("installed qf-solver --version probe failed")
    return {
        "python_executable": str(python),
        "python_version": report["python"],
        "system": report["system"],
        "package_version": report["version"],
        "solveur_file": str(package_file),
        "site_packages": str(site_packages),
        "cli_path": str(cli),
        "cli_version_output": version_probe.stdout.strip(),
    }


def _psutil_version() -> str:
    try:
        import psutil
    except ImportError as exc:
        raise ContractError("host Python must provide psutil for monitored process-tree/RSS observations") from exc
    return psutil.__version__


def _controlled_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for name in ("PYTHONHOME", "PYTHONPATH", "PYTHONUSERBASE", "PYTHONSTARTUP", "PYTHONEXECUTABLE"):
        environment.pop(name, None)
    environment["PYTHONNOUSERSITE"] = "1"
    environment.update(CONTROLLED_THREAD_ENV)
    return environment


def synthetic_preflight(manifest: dict[str, Any], manifest_sha256: str) -> dict[str, Any]:
    """Exercise preflight -> manifest -> one-shot reservation using a fake child only."""
    report = preflight(manifest, manifest_sha256, allow_existing_report=True)
    prior_preflight = json.loads(Path(manifest["preflight_report_path"]).read_text(encoding="utf-8"))
    for key in (
        "status",
        "manifest_sha256",
        "controller_sha256",
        "observed_git_head",
        "observed_branch",
        "artifacts",
        "installed_inputs",
        "oracle_sources",
    ):
        if report.get(key) != prior_preflight.get(key):
            raise ContractError("fresh no-FEM preflight differs from the persisted preflight report")
    evidence_root = Path(manifest["evidence_root"]).resolve()
    synthetic_root = evidence_root / "synthetic_preflight"
    synthetic_root.mkdir(exist_ok=False)
    ledger = synthetic_root / "synthetic_attempt_ledger.jsonl"
    key = hashlib.sha256((manifest_sha256 + ":SYNTHETIC-NO-FEM").encode("ascii")).hexdigest()
    reservation = {
        "event": "RESERVED",
        "reservation_key": key,
        "manifest_sha256": manifest_sha256,
        "controller_sha256": manifest["controller"]["sha256"],
        "case_id": "SYNTHETIC-NO-FEM",
        "artifact_id": "synthetic-child",
        "created_utc": _utc_now(),
        "fem_executed": False,
    }
    append_reservation(ledger, reservation)
    child = _bounded_child(
        [sys.executable, "-I", "-c", f"print('{SYNTHETIC_MARKER}')"],
        cwd=synthetic_root,
        timeout_seconds=5,
        stdout_max_bytes=4096,
        stderr_max_bytes=4096,
        rss_soft_limit_mib=512,
        env=_controlled_environment(),
    )
    if (
        child["stop_reason"] is not None
        or child["returncode"] != 0
        or child["stdout"].decode("utf-8", "replace").strip() != SYNTHETIC_MARKER
    ):
        raise ContractError("synthetic no-FEM child failed after its test reservation")
    append_record(
        ledger,
        {
            "event": "TERMINAL",
            "reservation_key": key,
            "status": "SYNTHETIC_ROUTE_PASS",
            "duration_seconds": child["duration_seconds"],
            "created_utc": _utc_now(),
            "fem_executed": False,
        },
    )
    report["synthetic_route"] = {
        "status": "PASS_NO_FEM",
        "route": "CLI -> preflight -> manifest -> synthetic reservation -> fixed fake child -> terminal ledger record",
        "ledger_path": str(ledger),
        "ledger_sha256": sha256_file(ledger),
        "child_stdout": child["stdout"].decode("utf-8", "replace").strip(),
        "child_stderr_bytes": len(child["stderr"]),
        "child_returncode": child["returncode"],
        "fem_executed": False,
    }
    report_path = synthetic_root / "synthetic_preflight_report.json"
    write_create_new(report_path, canonical_json_bytes(report))
    report["synthetic_report_path"] = str(report_path)
    report["synthetic_report_sha256"] = sha256_file(report_path)
    return report


def append_reservation(ledger_path: Path, record: dict[str, Any]) -> None:
    if ledger_path.exists():
        for line in ledger_path.read_text(encoding="utf-8").splitlines():
            try:
                prior = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ContractError("attempt ledger has a malformed existing line") from exc
            if prior.get("event") == "RESERVED" and prior.get("reservation_key") == record.get("reservation_key"):
                raise ContractError("attempt pair already has a reservation; retries are prohibited")
    append_record(ledger_path, record)


def append_record(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = canonical_json_bytes(record)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        with os.fdopen(fd, "ab", closefd=False) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(fd)


def write_create_new(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def validate_owner_decision(
    path: Path, manifest_sha256: str, preflight_sha256: str, synthetic_preflight_sha256: str
) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    decision_sha256 = hashlib.sha256(raw).hexdigest()
    try:
        decision = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("Owner decision is not valid UTF-8 JSON") from exc
    if not isinstance(decision, dict) or decision.get("schema") != OWNER_SCHEMA:
        raise ContractError("Owner decision schema is invalid")
    if decision.get("approval_status") != "APPROVED":
        raise ContractError("Owner decision does not explicitly approve execution")
    if decision.get("authorization_scope") != "SIX_INSTALLED_ARTIFACT_SMOKES_ONLY":
        raise ContractError("Owner decision authorizes a broader or different scope")
    if decision.get("qualification_claim") != "NOT_CLAIMED":
        raise ContractError("Owner decision cannot convert a smoke into a qualification claim")
    if decision.get("manifest_sha256") != manifest_sha256:
        raise ContractError("Owner decision is not bound to this exact manifest")
    if decision.get("preflight_sha256") != preflight_sha256:
        raise ContractError("Owner decision is not bound to this exact preflight")
    if decision.get("synthetic_preflight_sha256") != synthetic_preflight_sha256:
        raise ContractError("Owner decision is not bound to the exact no-FEM synthetic preflight")
    if (
        decision.get("approved_pairs") != PAIR_ORDER
        or not isinstance(decision.get("decision_id"), str)
        or not decision["decision_id"].strip()
    ):
        raise ContractError("Owner decision pair list or decision ID is incomplete")
    return decision, decision_sha256


def run_all(manifest: dict[str, Any], manifest_sha256: str, manifest_path: Path, owner_path: Path) -> dict[str, Any]:
    preflight_path = Path(manifest["preflight_report_path"]).resolve(strict=True)
    preflight_sha256 = sha256_file(preflight_path)
    preflight_report = json.loads(preflight_path.read_text(encoding="utf-8"))
    if (
        preflight_report.get("status") != "PASS_NO_FEM_PREFLIGHT"
        or preflight_report.get("manifest_sha256") != manifest_sha256
        or preflight_report.get("execution_authorized") is not False
        or preflight_report.get("actual_attempt_reservations") != 0
        or preflight_report.get("fem_executed") is not False
    ):
        raise ContractError("current no-FEM preflight does not match the manifest")
    synthetic_report_path = (
        Path(manifest["evidence_root"]).resolve() / "synthetic_preflight" / "synthetic_preflight_report.json"
    )
    synthetic_report = json.loads(synthetic_report_path.read_text(encoding="utf-8"))
    synthetic_preflight_sha256 = sha256_file(synthetic_report_path)
    synthetic_route = synthetic_report.get("synthetic_route", {})
    if (
        synthetic_report.get("status") != "PASS_NO_FEM_PREFLIGHT"
        or synthetic_report.get("manifest_sha256") != manifest_sha256
        or synthetic_report.get("controller_sha256") != manifest["controller"]["sha256"]
        or synthetic_report.get("actual_attempt_reservations") != 0
        or synthetic_report.get("fem_executed") is not False
        or synthetic_route.get("status") != "PASS_NO_FEM"
        or synthetic_route.get("fem_executed") is not False
    ):
        raise ContractError("no-FEM synthetic route has not passed for this exact manifest")
    expected_synthetic_ledger = (
        Path(manifest["evidence_root"]).resolve() / "synthetic_preflight" / "synthetic_attempt_ledger.jsonl"
    )
    synthetic_ledger_path = Path(synthetic_route.get("ledger_path", "")).resolve(strict=True)
    if synthetic_ledger_path != expected_synthetic_ledger.resolve():
        raise ContractError("no-FEM synthetic ledger path differs from the fixed manifest route")
    if sha256_file(synthetic_ledger_path) != synthetic_route.get("ledger_sha256"):
        raise ContractError("no-FEM synthetic attempt ledger hash mismatch")
    synthetic_records = [
        json.loads(line)
        for line in synthetic_ledger_path.read_text(encoding="utf-8").splitlines()
    ]
    if (
        len(synthetic_records) != 2
        or [record.get("event") for record in synthetic_records] != ["RESERVED", "TERMINAL"]
        or synthetic_records[-1].get("status") != "SYNTHETIC_ROUTE_PASS"
        or any(record.get("fem_executed") is not False for record in synthetic_records)
    ):
        raise ContractError("no-FEM synthetic attempt ledger is incomplete or invalid")
    root = Path(__file__).resolve().parents[1]
    if (
        preflight_report.get("controller_sha256") != manifest["controller"]["sha256"]
        or preflight_report.get("observed_branch") != _git_output(root, "branch", "--show-current")
        or preflight_report.get("observed_git_status") != "CLEAN"
        or _git_output(root, "status", "--porcelain")
    ):
        raise ContractError("controller checkout identity or cleanliness changed after preflight")
    if (
        preflight_report.get("host_python_executable") != str(Path(sys.executable).resolve())
        or preflight_report.get("host_python") != sys.version
        or preflight_report.get("host_os") != platform.platform()
        or preflight_report.get("psutil_version") != _psutil_version()
    ):
        raise ContractError("host OS, Python, or monitor runtime changed after preflight")
    if preflight_report.get("controlled_thread_environment") != _controlled_environment_subset():
        raise ContractError("controlled numerical thread environment changed after preflight")
    if _oracle_source_hashes(root) != preflight_report.get("oracle_sources"):
        raise ContractError("independent oracle sources changed after preflight")
    current_artifacts, current_inputs = _verify_installed_artifacts(
        manifest, Path(manifest["evidence_root"]).resolve()
    )
    if current_artifacts != preflight_report.get("artifacts") or current_inputs != preflight_report.get("installed_inputs"):
        raise ContractError("installed artifacts, environments, or inputs changed after preflight")
    decision, decision_sha256 = validate_owner_decision(
        owner_path, manifest_sha256, preflight_sha256, synthetic_preflight_sha256
    )
    evidence_root = Path(manifest["evidence_root"]).resolve(strict=True)
    if {child.name for child in evidence_root.iterdir()} != {"synthetic_preflight"}:
        raise ContractError("evidence root contains unexpected files before the first authorized attempt")
    ledger_path = Path(manifest["attempt_ledger_path"]).resolve()
    if _is_relative_to(ledger_path, Path(__file__).resolve().parents[1]):
        raise ContractError("attempt ledger must be outside the source checkout")
    lock_path = evidence_root / ".wp13-package-smoke.lock"
    lock_fd = os.open(lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.write(lock_fd, canonical_json_bytes({"pid": os.getpid(), "created_utc": _utc_now()}))
    os.fsync(lock_fd)

    case_map = {case["case_id"]: case for case in manifest["cases"]}
    results: list[dict[str, Any]] = []
    try:
        write_create_new(evidence_root / "execution_manifest.json", manifest_path.read_bytes())
        if sha256_file(evidence_root / "execution_manifest.json") != manifest_sha256:
            raise ContractError("preserved execution manifest copy failed its SHA-256 check")
        write_create_new(evidence_root / "preflight_report.json", preflight_path.read_bytes())
        if sha256_file(evidence_root / "preflight_report.json") != preflight_sha256:
            raise ContractError("preserved preflight report copy failed its SHA-256 check")
        write_create_new(evidence_root / "owner_decision.json", owner_path.read_bytes())
        if sha256_file(evidence_root / "owner_decision.json") != decision_sha256:
            raise ContractError("preserved Owner decision copy failed its SHA-256 check")
        for pair in PAIR_ORDER:
            artifact_name = pair["artifact"]
            case_id = pair["case"]
            artifact = manifest["artifacts"][artifact_name]
            case = case_map[case_id]
            attempt_key = hashlib.sha256(
                f"{manifest_sha256}:{artifact_name}:{case_id}".encode("ascii")
            ).hexdigest()
            output_dir = evidence_root / artifact_name / case_id
            output_dir.mkdir(parents=True, exist_ok=False)
            output_path = output_dir / "result.json"
            installed_input = Path(artifact["examples_root"]) / case["input_name"]
            input_path = output_dir / case["input_name"]
            write_create_new(input_path, installed_input.read_bytes())
            if sha256_file(input_path) != case["input_sha256"]:
                raise ContractError("frozen package input copy failed its SHA-256 check")
            cli = (Path(artifact["environment_root"]) / "Scripts" / "qf-solver.exe").resolve(strict=True)
            command = [str(cli), "solve", "--input", str(input_path), "--output", str(output_path)]
            append_reservation(
                ledger_path,
                {
                    "event": "RESERVED",
                    "reservation_key": attempt_key,
                    "manifest_sha256": manifest_sha256,
                    "controller_sha256": manifest["controller"]["sha256"],
                    "owner_decision_sha256": decision_sha256,
                    "decision_id": decision["decision_id"],
                    "artifact_id": artifact_name,
                    "artifact_sha256": artifact["archive_sha256"],
                    "case_id": case_id,
                    "input_sha256": case["input_sha256"],
                    "input_copy_path": str(input_path),
                    "command_argv": command,
                    "working_directory": str(evidence_root),
                    "controlled_thread_environment": _controlled_environment_subset(),
                    "limits": {
                        "timeout_seconds": manifest["execution"]["timeout_seconds"],
                        "stdout_max_bytes": manifest["execution"]["stdout_max_bytes"],
                        "stderr_max_bytes": manifest["execution"]["stderr_max_bytes"],
                        "rss_soft_limit_mib": manifest["execution"]["rss_soft_limit_mib"],
                    },
                    "attempt": 1,
                    "created_utc": _utc_now(),
                },
            )
            child = _bounded_child(
                command,
                cwd=evidence_root,
                timeout_seconds=manifest["execution"]["timeout_seconds"],
                stdout_max_bytes=manifest["execution"]["stdout_max_bytes"],
                stderr_max_bytes=manifest["execution"]["stderr_max_bytes"],
                rss_soft_limit_mib=manifest["execution"]["rss_soft_limit_mib"],
                env=_controlled_environment(),
            )
            write_create_new(output_dir / "stdout.log", child["stdout"])
            write_create_new(output_dir / "stderr.log", child["stderr"])
            execution_status = "EXECUTION_FAIL"
            numerical_oracle_status = "NOT_EVALUATED"
            verdict = "EXECUTION_FAIL"
            oracle: dict[str, Any] = {"status": "NOT_EVALUATED"}
            reason = child["stop_reason"]
            if reason is None and child["returncode"] == 0 and output_path.is_file():
                execution_status = "EXECUTION_PASS"
                try:
                    payload = json.loads(output_path.read_text(encoding="utf-8"))
                    if not isinstance(payload, dict):
                        raise ContractError("solver result JSON is not an object")
                    oracle = evaluate_oracle(case_id, payload, case["oracles"])
                    numerical_oracle_status = "NUMERICAL_ORACLE_PASS" if oracle["passed"] else "NUMERICAL_ORACLE_FAIL"
                    verdict = numerical_oracle_status
                    reason = None if oracle["passed"] else "one or more frozen oracle checks failed"
                except (OSError, json.JSONDecodeError, ContractError, KeyError, TypeError, ValueError) as exc:
                    numerical_oracle_status = "NUMERICAL_ORACLE_FAIL"
                    verdict = numerical_oracle_status
                    reason = f"result parsing or oracle evaluation failed: {exc}"
            elif reason is None:
                reason = f"installed CLI exited {child['returncode']} or produced no result file"
            terminal = {
                "event": "TERMINAL",
                "reservation_key": attempt_key,
                "status": verdict,
                "execution_status": execution_status,
                "numerical_oracle_status": numerical_oracle_status,
                "qualification_status": "NOT_CLAIMED",
                "reason": reason,
                "returncode": child["returncode"],
                "duration_seconds": child["duration_seconds"],
                "max_sampled_rss_bytes": child["max_rss_bytes"],
                "stdout_sha256": hashlib.sha256(child["stdout"]).hexdigest(),
                "stderr_sha256": hashlib.sha256(child["stderr"]).hexdigest(),
                "result_sha256": sha256_file(output_path) if output_path.is_file() else None,
                "oracle": oracle,
                "created_utc": _utc_now(),
            }
            append_record(ledger_path, terminal)
            results.append(terminal)
            if verdict != "NUMERICAL_ORACLE_PASS":
                summary = {
                    "status": "STOP_AFTER_FIRST_FAILURE",
                    "manifest_sha256": manifest_sha256,
                    "owner_decision_sha256": decision_sha256,
                    "qualification_status": "NOT_CLAIMED",
                    "completed_pairs": results,
                    "remaining_pairs_not_run": PAIR_ORDER[len(results) :],
                    "ledger_sha256": sha256_file(ledger_path),
                    "fem_executed": True,
                }
                return _persist_run_summary(evidence_root, summary)
    finally:
        os.close(lock_fd)
        lock_path.unlink(missing_ok=True)
    summary = {
        "status": "SIX_EXECUTION_AND_NUMERICAL_ORACLES_PASS",
        "manifest_sha256": manifest_sha256,
        "owner_decision_sha256": decision_sha256,
        "qualification_status": "NOT_CLAIMED",
        "completed_pairs": results,
        "ledger_sha256": sha256_file(ledger_path),
        "fem_executed": True,
    }
    return _persist_run_summary(evidence_root, summary)


def _persist_run_summary(evidence_root: Path, summary: dict[str, Any]) -> dict[str, Any]:
    summary_path = evidence_root / "execution_summary.json"
    write_create_new(summary_path, canonical_json_bytes(summary))
    return {**summary, "summary_path": str(summary_path), "summary_sha256": sha256_file(summary_path)}


def evaluate_oracle(case_id: str, payload: dict[str, Any], oracle: dict[str, Any]) -> dict[str, Any]:
    _require(payload.get("status") == "PASS", "solver status is not PASS")
    checks: dict[str, dict[str, float | bool]] = {}
    if case_id == "STATIC-01":
        _require(payload.get("analysis") == "linear_static", "analysis route is not linear static")
        displacement = _nodal_value(payload["displacements"], 1, "UX")
        stress = float(payload["element_results"][0]["von_mises"])
        equilibrium = payload["audit"]["equilibrium"]
        checks["ux_m"] = _relative_check(displacement, oracle["ux_m"], oracle["ux_relative_tolerance"])
        checks["von_mises_pa"] = _relative_check(
            stress, oracle["von_mises_pa"], oracle["stress_relative_tolerance"]
        )
        checks["free_relative_residual"] = _upper_check(
            float(equilibrium["free_relative_residual"]), oracle["free_relative_residual_max"]
        )
        checks["reaction_resultant_x_n"] = _absolute_check(
            float(equilibrium["reaction_resultant"][0]),
            oracle["reaction_resultant_x_n"],
            oracle["reaction_absolute_tolerance_n"],
        )
        checks["force_balance_relative_error"] = _upper_check(
            float(equilibrium["force_balance_relative_error"]), oracle["force_balance_relative_error_max"]
        )
        checks["linear_energy_identity_relative_error"] = _upper_check(
            float(equilibrium["linear_energy_identity_relative_error"]),
            oracle["linear_energy_identity_relative_error_max"],
        )
    elif case_id == "MODAL-01":
        _require(payload.get("analysis") == "modal", "analysis route is not modal")
        modes = payload["modes"]
        _require(len(modes) == 3, "modal solve did not return three modes")
        checks["first_frequency_hz"] = _relative_check(
            float(modes[0]["frequency_hz"]), oracle["first_frequency_hz"], oracle["frequency_relative_tolerance"]
        )
        diagnostics = payload["solver"]
        checks["max_relative_eigen_residual"] = _upper_check(
            float(diagnostics["max_relative_residual"]), oracle["max_relative_eigen_residual"]
        )
        checks["mass_orthogonality_error"] = _upper_check(
            float(diagnostics["mass_orthogonality_error"]), oracle["mass_orthogonality_error_max"]
        )
        checks["stiffness_diagonal_error"] = _upper_check(
            float(diagnostics["stiffness_diagonal_error"]), oracle["stiffness_diagonal_error_max"]
        )
    elif case_id == "DYNAMIC-01":
        _require(payload.get("analysis") == "transient_dynamic", "analysis route is not transient dynamic")
        _require(payload.get("method") == "newmark", "dynamic method is not Newmark")
        history = payload["solver"]["time_history"]
        history_index = int(oracle["history_index"])
        _require(len(history) == 40, "dynamic solver did not return exactly 40 states")
        first_row = history[0]
        row = history[history_index]
        _require(
            int(first_row["step"]) == 1
            and math.isclose(
                float(first_row["time"]), oracle["first_record_time_s"], rel_tol=0.0, abs_tol=1e-15
            )
            and int(row["step"]) == oracle["history_step"]
            and math.isclose(float(row["time"]), oracle["final_time_s"], rel_tol=0.0, abs_tol=1e-15),
            "the 40th recorded dynamic state is not the frozen 0.040 s step",
        )
        final_u = _nodal_value(payload["displacements"], 1, "UX")
        final_v = _nodal_value(payload["velocities"], 1, "UX")
        final_energy = 0.5 * oracle["stiffness_n_per_m"] * final_u**2 + 0.5 * oracle["mass_kg"] * final_v**2
        history_energy = float(row["total_energy"])
        initial_energy = (
            0.5 * oracle["stiffness_n_per_m"] * oracle["initial_displacement_m"] ** 2
            + 0.5 * oracle["mass_kg"] * oracle["initial_velocity_m_s"] ** 2
        )
        checks["initial_energy_j"] = _relative_check(
            initial_energy, oracle["expected_energy_j"], oracle["energy_relative_tolerance"]
        )
        checks["first_recorded_energy_j"] = _relative_check(
            float(first_row["total_energy"]), oracle["expected_energy_j"], oracle["energy_relative_tolerance"]
        )
        checks["final_state_energy_j"] = _relative_check(
            final_energy, oracle["expected_energy_j"], oracle["energy_relative_tolerance"]
        )
        checks["history_energy_matches_independent_state_j"] = _absolute_check(
            history_energy, final_energy, oracle["history_energy_consistency_absolute_tolerance_j"]
        )
        checks["relative_energy_drift"] = _absolute_check(
            (final_energy - oracle["expected_energy_j"]) / oracle["expected_energy_j"],
            0.0,
            oracle["relative_energy_drift_absolute_tolerance"],
        )
        checks["dynamic_residual_norm"] = _upper_check(
            float(row["dynamic_residual_norm"]), oracle["dynamic_residual_norm_max"]
        )
        checks["free_relative_residual"] = _upper_check(
            float(payload["audit"]["equilibrium"]["free_relative_residual"]),
            oracle["free_relative_residual_max"],
        )
    else:
        raise ContractError(f"unsupported case ID {case_id!r}")
    return {"passed": all(item["passed"] for item in checks.values()), "checks": checks}


def _bounded_child(
    command: list[str],
    *,
    cwd: Path,
    timeout_seconds: int,
    stdout_max_bytes: int,
    stderr_max_bytes: int,
    rss_soft_limit_mib: int,
    env: dict[str, str],
) -> dict[str, Any]:
    try:
        import psutil
    except ImportError as exc:
        raise ContractError("psutil is required for monitored child execution") from exc
    started = time.monotonic()
    stdout_data = bytearray()
    stderr_data = bytearray()
    exceeded = threading.Event()
    if os.name == "nt":
        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            env=env,
        )
    else:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
            env=env,
        )
    stop_reason: str | None = None

    def drain(stream: Any, output: bytearray, limit: int) -> None:
        while True:
            chunk = stream.read(8192)
            if not chunk:
                break
            if len(output) + len(chunk) > limit:
                output.extend(chunk[: max(limit - len(output), 0)])
                exceeded.set()
            else:
                output.extend(chunk)

    stdout_thread = threading.Thread(target=drain, args=(process.stdout, stdout_data, stdout_max_bytes), daemon=True)
    stderr_thread = threading.Thread(target=drain, args=(process.stderr, stderr_data, stderr_max_bytes), daemon=True)
    stdout_thread.start()
    stderr_thread.start()
    max_rss_bytes = 0
    try:
        ps_process = psutil.Process(process.pid)
    except (OSError, psutil.Error) as exc:
        process.kill()
        raise ContractError("could not attach process monitoring after preflight") from exc
    deadline = started + timeout_seconds
    while process.poll() is None:
        if exceeded.is_set():
            stop_reason = "OUTPUT_LIMIT_EXCEEDED"
            _terminate_tree(process, ps_process)
            break
        if time.monotonic() >= deadline:
            stop_reason = "TIMEOUT"
            _terminate_tree(process, ps_process)
            break
        if ps_process is not None:
            try:
                rss = ps_process.memory_info().rss
                for child in ps_process.children(recursive=True):
                    try:
                        rss += child.memory_info().rss
                    except OSError:
                        continue
                max_rss_bytes = max(max_rss_bytes, rss)
                if rss > rss_soft_limit_mib * 1024 * 1024:
                    stop_reason = "RSS_SOFT_LIMIT_EXCEEDED"
                    _terminate_tree(process, ps_process)
                    break
            except (OSError, psutil.Error):
                pass
        time.sleep(0.05)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        _terminate_tree(process, ps_process)
        process.wait(timeout=5)
    stdout_thread.join(timeout=5)
    stderr_thread.join(timeout=5)
    if exceeded.is_set() and stop_reason is None:
        stop_reason = "OUTPUT_LIMIT_EXCEEDED"
    return {
        "returncode": process.returncode,
        "stdout": bytes(stdout_data),
        "stderr": bytes(stderr_data),
        "duration_seconds": time.monotonic() - started,
        "max_rss_bytes": max_rss_bytes,
        "stop_reason": stop_reason,
    }


def _terminate_tree(process: subprocess.Popen[bytes], ps_process: Any) -> None:
    import psutil

    if ps_process is not None:
        try:
            children = ps_process.children(recursive=True)
            for child in reversed(children):
                try:
                    child.terminate()
                except (OSError, psutil.Error):
                    continue
            ps_process.terminate()
            _, alive = psutil.wait_procs([*children, ps_process], timeout=2)
            for item in alive:
                try:
                    item.kill()
                except (OSError, psutil.Error):
                    continue
        except (OSError, psutil.Error):
            process.kill()
    elif process.poll() is None:
        process.kill()


def _nodal_value(rows: object, node: int, dof: str) -> float:
    if not isinstance(rows, list):
        raise ContractError("serialized nodal state is not a list")
    for row in rows:
        if not isinstance(row, dict):
            raise ContractError("serialized nodal state contains a malformed row")
        if row.get("node") == node:
            return float(row["dofs"][dof])
    raise ContractError(f"result has no node {node} {dof} value")


def _relative_check(actual: float, expected: float, tolerance: float) -> dict[str, float | bool]:
    error = abs(actual - expected) / max(abs(expected), 1.0e-300)
    return {"actual": actual, "expected": expected, "relative_error": error, "tolerance": tolerance, "passed": error <= tolerance}


def _absolute_check(actual: float, expected: float, tolerance: float) -> dict[str, float | bool]:
    error = abs(actual - expected)
    return {"actual": actual, "expected": expected, "absolute_error": error, "tolerance": tolerance, "passed": error <= tolerance}


def _upper_check(actual: float, tolerance: float) -> dict[str, float | bool]:
    return {"actual": actual, "tolerance": tolerance, "passed": math.isfinite(actual) and actual <= tolerance}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def _git_output(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *arguments], capture_output=True, text=True, timeout=10, check=False
    )
    if result.returncode != 0:
        raise ContractError(f"git {' '.join(arguments)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _oracle_source_hashes(root: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for relative_path in ORACLE_SOURCE_SHA256:
        object_spec = f"{PACKAGE_SOURCE_SHA}:{relative_path}"
        result = subprocess.run(
            ["git", "-C", str(root), "cat-file", "blob", object_spec],
            capture_output=True,
            timeout=10,
            check=False,
        )
        if result.returncode != 0:
            raise ContractError(f"frozen oracle source is unavailable: {object_spec}")
        hashes[relative_path] = hashlib.sha256(result.stdout).hexdigest()
    return hashes


def _controlled_environment_subset() -> dict[str, str]:
    environment = _controlled_environment()
    return {key: environment[key] for key in CONTROLLED_THREAD_ENV}


def _verify_installed_artifacts(
    manifest: dict[str, Any], evidence_root: Path
) -> tuple[dict[str, Any], dict[str, dict[str, str]]]:
    artifact_results: dict[str, Any] = {}
    for name, artifact in manifest["artifacts"].items():
        archive = Path(artifact["archive_path"]).resolve(strict=True)
        install_report = Path(artifact["install_report_path"]).resolve(strict=True)
        if sha256_file(archive) != artifact["archive_sha256"]:
            raise ContractError(f"{name} artifact file hash mismatch")
        if sha256_file(install_report) != artifact["install_report_sha256"]:
            raise ContractError(f"{name} installation report hash mismatch")
        environment = _probe_environment(Path(artifact["environment_root"]).resolve(strict=True), evidence_root)
        artifact_results[name] = {
            "archive_path": str(archive),
            "archive_sha256": artifact["archive_sha256"],
            "install_report_path": str(install_report),
            "install_report_sha256": artifact["install_report_sha256"],
            "environment": environment,
        }

    input_results: dict[str, dict[str, str]] = {}
    for artifact_name, artifact in manifest["artifacts"].items():
        examples_root = Path(artifact["examples_root"]).resolve(strict=True)
        input_results[artifact_name] = {}
        for case_id, input_name in CASE_INPUT.items():
            input_path = (examples_root / input_name).resolve(strict=True)
            if not _is_relative_to(input_path, examples_root):
                raise ContractError(f"{case_id} input escaped the installed examples directory")
            observed_hash = sha256_file(input_path)
            if observed_hash != INPUT_SHA256[case_id]:
                raise ContractError(f"{artifact_name}/{case_id} installed input hash mismatch")
            input_results[artifact_name][case_id] = observed_hash
    return artifact_results, input_results


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _is_sha(value: object) -> bool:
    return isinstance(value, str) and len(value) == 40 and all(char in "0123456789abcdef" for char in value)


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bounded v6 wheel/sdist WP13 smoke controller")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("preflight", "synthetic-preflight"):
        command = subparsers.add_parser(name)
        command.add_argument("--manifest", type=Path, required=True)
        command.add_argument("--expected-manifest-sha256", required=True)
    run = subparsers.add_parser("run-all")
    run.add_argument("--manifest", type=Path, required=True)
    run.add_argument("--expected-manifest-sha256", required=True)
    run.add_argument("--owner-decision", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        manifest, manifest_sha256 = load_manifest(args.manifest, args.expected_manifest_sha256)
        if args.command == "preflight":
            report = preflight(manifest, manifest_sha256)
            report_path = Path(manifest["preflight_report_path"])
            write_create_new(report_path, canonical_json_bytes(report))
            print(json.dumps({"status": report["status"], "report": str(report_path), "sha256": sha256_file(report_path)}))
            return 0
        if args.command == "synthetic-preflight":
            report = synthetic_preflight(manifest, manifest_sha256)
            print(json.dumps(report, indent=2))
            return 0
        result = run_all(manifest, manifest_sha256, args.manifest, args.owner_decision)
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "SIX_EXECUTION_AND_NUMERICAL_ORACLES_PASS" else 1
    except (ContractError, OSError, subprocess.SubprocessError) as exc:
        print(f"WP13 PACKAGE SMOKE STOP: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
