"""One-shot, Owner-gated local runner for the WP-C02-AR M4/M5 FEM tests."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
from typing import Any

import psutil


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "qualification/0_2_12/wp_c02_ar_native_execution_manifest.json"
REPORTER = ROOT / "scripts/report_wpc02_ar_native.py"
TEST_PATH = "tests/verification/test_wpc02_ar_native_contact_convergence.py"
GO_TOKEN = "GO-RUN-FEM-NATIF"
MEMORY_POLL_S = 0.5


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def _current_environment(manifest: dict[str, Any]) -> None:
    expected = manifest["environment"]
    actual_python = ".".join(map(str, sys.version_info[:3]))
    if actual_python != expected["python"]:
        raise RuntimeError(f"Python version mismatch: expected {expected['python']}, got {actual_python}.")
    for distribution, version in expected["packages"].items():
        actual = importlib.metadata.version(distribution)
        if actual != version:
            raise RuntimeError(f"Dependency version mismatch for {distribution}: expected {version}, got {actual}.")
    if platform.system() != expected["platform_system"]:
        raise RuntimeError(f"Platform mismatch: expected {expected['platform_system']}, got {platform.system()}.")


SOURCE_SET_CONTRACT = {
    "schema": "wpc02-ar-source-set-sha256-v1",
    "encoding": "UTF-8",
    "path_format": "repository-relative POSIX path",
    "order": "ascending Unicode code-point order",
    "record_format": "path + two ASCII spaces + lowercase SHA-256 hex",
    "record_separator": "LF",
    "final_record_separator": False,
}


def _source_set_sha256(files: dict[str, str]) -> str:
    payload = "\n".join(f"{path}  {files[path]}" for path in sorted(files))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _verify_source_set(
    manifest: dict[str, Any], root: Path = ROOT, require_committed: bool = False
) -> None:
    if manifest.get("source_set_contract") != SOURCE_SET_CONTRACT:
        raise RuntimeError("Unsupported or missing source-set hash contract.")
    files = manifest.get("source_files_sha256")
    if not isinstance(files, dict) or not files:
        raise RuntimeError("Frozen source list is missing or invalid.")
    if manifest.get("source_file_count") != len(files):
        raise RuntimeError("Frozen source-file count does not match its list.")
    aggregate = _source_set_sha256(files)
    if manifest.get("source_set_sha256") != aggregate:
        raise RuntimeError(
            f"Frozen source-set hash mismatch: expected {manifest.get('source_set_sha256')}, got {aggregate}."
        )
    if (root / "tests/verification/conftest.py").exists():
        raise RuntimeError("Unexpected tests/verification/conftest.py would change the frozen pytest execution context.")
    committed_paths = None
    if require_committed:
        committed_paths = set(_git(root, "ls-tree", "-r", "--name-only", "HEAD").splitlines())
    for relative, expected in manifest["source_files_sha256"].items():
        if Path(relative).is_absolute() or ".." in Path(relative).parts or "\\" in relative:
            raise RuntimeError(f"Invalid repository-relative POSIX source path: {relative}.")
        if committed_paths is not None and relative not in committed_paths:
            raise RuntimeError(f"Frozen source is not present in the identified Git commit: {relative}.")
        path = root / relative
        if not path.is_file():
            raise RuntimeError(f"Frozen source is missing: {relative}.")
        actual = _sha256(path)
        if actual != expected:
            raise RuntimeError(f"Frozen source hash mismatch for {relative}: expected {expected}, got {actual}.")


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def _verify_git_identity(manifest: dict[str, Any], root: Path = ROOT) -> None:
    identity = manifest.get("identity", {})
    actual_head = _git(root, "rev-parse", "HEAD")
    actual_tree = _git(root, "rev-parse", "HEAD^{tree}")
    if identity.get("git_head") != actual_head:
        raise RuntimeError(
            f"Frozen Git HEAD mismatch: expected {identity.get('git_head')}, got {actual_head}."
        )
    if identity.get("git_tree_oid") != actual_tree:
        raise RuntimeError(
            f"Frozen Git tree mismatch: expected {identity.get('git_tree_oid')}, got {actual_tree}."
        )


def _verify_external_manifest(manifest_path: Path, root: Path = ROOT) -> None:
    try:
        relative = manifest_path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return
    if _git(root, "ls-tree", "--name-only", "HEAD", "--", relative):
        raise RuntimeError("Execution manifest must remain external to the identified source commit tree.")


def _copy_snapshot(archive: Path, manifest: dict[str, Any], manifest_path: Path) -> None:
    snapshot = archive / "snapshot"
    for relative, expected in manifest["source_files_sha256"].items():
        source = ROOT / relative
        target = snapshot / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        if _sha256(target) != expected:
            raise RuntimeError(f"Snapshot copy hash mismatch for {relative}.")
    shutil.copy2(manifest_path, archive / "wp_c02_ar_native_execution_manifest.json")


def _process_tree_rss(process: psutil.Process) -> int:
    total = 0
    candidates = [process]
    try:
        candidates.extend(process.children(recursive=True))
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    for candidate in candidates:
        try:
            total += candidate.memory_info().rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return total


def _terminate_tree(process: psutil.Process) -> None:
    try:
        children = process.children(recursive=True)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        children = []
    for child in reversed(children):
        try:
            child.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    try:
        process.terminate()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    _, alive = psutil.wait_procs([*children, process], timeout=5.0)
    for item in alive:
        try:
            item.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass


def _launch_one(level: str, archive: Path, limits: dict[str, Any], ledger: dict[str, Any]) -> dict[str, Any]:
    scenario = level.lower()
    result_path = archive / f"{scenario}_diagnostics.json"
    if result_path.exists():
        raise RuntimeError(f"Refusing repeated scenario {level}: {result_path} already exists.")
    attempt = {
        "level": level,
        "attempt_count": 1,
        "state": "LAUNCHING",
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "timeout_s": limits["wall_timeout_s_per_scenario"],
        "rss_limit_bytes": limits["process_tree_rss_limit_bytes"],
    }
    ledger["scenarios"].append(attempt)
    _write_json(archive / "run_ledger.json", ledger)

    log_path = archive / f"{scenario}_pytest.log"
    env = os.environ.copy()
    env.update(
        {
            "WPC02_AR_NATIVE_OWNER_GO_TOKEN": GO_TOKEN,
            "WPC02_AR_NATIVE_OWNER_GO_MANIFEST_SHA256": ledger["manifest_sha256"],
            "WPC02_AR_NATIVE_MANIFEST_PATH": str(ledger["manifest_path"]),
            "WPC02_AR_NATIVE_GIT_HEAD": ledger["git_head"],
            "WPC02_AR_NATIVE_GIT_TREE_OID": ledger["git_tree_oid"],
            "WPC02_AR_NATIVE_OUTPUT_DIR": str(archive),
            "PYTHONHASHSEED": "0",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
            "VECLIB_MAXIMUM_THREADS": "1",
        }
    )
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:rerunfailures",
        "--confcutdir=tests/verification",
        f"{TEST_PATH}::test_wpc02_ar_native_{scenario}",
    ]
    attempt["command"] = command
    attempt["state"] = "RUNNING"
    _write_json(archive / "run_ledger.json", ledger)
    started = time.monotonic()
    maximum_rss = 0
    stop_reason: str | None = None
    with log_path.open("wb") as log:
        child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        process = psutil.Process(child.pid)
        while child.poll() is None:
            rss = _process_tree_rss(process)
            maximum_rss = max(maximum_rss, rss)
            if rss > limits["process_tree_rss_limit_bytes"]:
                stop_reason = "RSS_LIMIT_EXCEEDED"
                _terminate_tree(process)
                break
            if time.monotonic() - started > limits["wall_timeout_s_per_scenario"]:
                stop_reason = "WALL_TIMEOUT_EXCEEDED"
                _terminate_tree(process)
                break
            time.sleep(MEMORY_POLL_S)
        return_code = child.wait()
    elapsed = time.monotonic() - started
    attempt["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    attempt["elapsed_s"] = elapsed
    attempt["max_sampled_process_tree_rss_bytes"] = maximum_rss
    attempt["pytest_return_code"] = return_code
    attempt["log_file"] = log_path.name
    attempt["diagnostic_file_present"] = result_path.is_file()
    if stop_reason:
        attempt["state"] = stop_reason
        attempt["stop_reason"] = "process tree terminated by the local resource supervisor"
    elif not result_path.is_file():
        attempt["state"] = "INFRASTRUCTURE_FAILURE_NO_DIAGNOSTIC"
        attempt["stop_reason"] = "pytest exited without a scenario diagnostic record"
    else:
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if result.get("scenario_state") == "SOLVER_OR_DIAGNOSTIC_EXCEPTION":
            attempt["state"] = "SCIENTIFIC_OR_DIAGNOSTIC_FAILURE"
        elif return_code == 0:
            attempt["state"] = "PASS"
        elif result.get("scenario_state") != "COMPLETED_DIAGNOSTICS":
            attempt["state"] = "INFRASTRUCTURE_FAILURE_INCOMPLETE_DIAGNOSTIC"
            attempt["stop_reason"] = f"incomplete scenario record state={result.get('scenario_state')}"
        else:
            attempt["state"] = "SCIENTIFIC_CRITERION_FAILURE"
    _write_json(archive / "run_ledger.json", ledger)
    return attempt


def _archive_hashes(archive: Path) -> str:
    files = []
    for path in sorted(p for p in archive.rglob("*") if p.is_file() and p.name not in {
        "archive_integrity_manifest.json",
        "archive_integrity_manifest.sha256",
    }):
        relative = path.relative_to(archive).as_posix()
        files.append({"path": relative, "sha256": _sha256(path), "size_bytes": path.stat().st_size})
    integrity = {
        "schema": "wpc02-ar-native-archive-integrity-v1",
        "file_count": len(files),
        "files": files,
    }
    manifest_path = archive / "archive_integrity_manifest.json"
    _write_json(manifest_path, integrity)
    digest = _sha256(manifest_path)
    (archive / "archive_integrity_manifest.sha256").write_text(f"{digest}  archive_integrity_manifest.json\n", encoding="ascii")
    return digest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner-go", required=True, help="Exact Owner authorization token GO-RUN-FEM-NATIF")
    parser.add_argument("--owner-manifest-sha256", required=True, help="SHA-256 of the frozen execution manifest")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="External execution manifest, generated after the source commit")
    args = parser.parse_args()
    if args.owner_go != GO_TOKEN:
        parser.error("--owner-go must be the exact token GO-RUN-FEM-NATIF.")
    manifest_path = args.manifest.resolve()
    manifest_sha = _sha256(manifest_path)
    if args.owner_manifest_sha256.lower() != manifest_sha:
        parser.error(f"Manifest digest does not match this frozen campaign: {manifest_sha}.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _current_environment(manifest)
    _verify_external_manifest(manifest_path)
    _verify_git_identity(manifest)
    _verify_source_set(manifest, require_committed=True)
    archive = (ROOT / manifest["execution"]["archive_relative_path"]).resolve()
    if not archive.is_relative_to(ROOT.resolve()):
        raise RuntimeError("Archive output must remain inside the repository worktree.")
    if archive.exists():
        raise RuntimeError(f"One-shot archive already exists; automatic retry is forbidden: {archive}.")
    archive.mkdir(parents=True, exist_ok=False)
    _copy_snapshot(archive, manifest, manifest_path)
    ledger: dict[str, Any] = {
        "schema": "wpc02-ar-native-one-shot-ledger-v1",
        "campaign": manifest["campaign"],
        "authorization": {"token": GO_TOKEN, "manifest_sha256": manifest_sha},
        "manifest_sha256": manifest_sha,
        "manifest_path": str(manifest_path),
        "git_head": manifest["identity"]["git_head"],
        "git_tree_oid": manifest["identity"]["git_tree_oid"],
        "source_set_sha256": manifest["source_set_sha256"],
        "python": sys.version,
        "platform": platform.platform(),
        "resource_limits": manifest["execution"]["resource_limits"],
        "scenarios": [],
        "campaign_state": "RUNNING",
    }
    _write_json(archive / "run_ledger.json", ledger)

    stop_campaign = False
    for level in ("M4", "M5"):
        if stop_campaign:
            break
        attempt = _launch_one(level, archive, manifest["execution"]["resource_limits"], ledger)
        if attempt["state"] in {
            "RSS_LIMIT_EXCEEDED",
            "WALL_TIMEOUT_EXCEEDED",
            "INFRASTRUCTURE_FAILURE_NO_DIAGNOSTIC",
            "INFRASTRUCTURE_FAILURE_INCOMPLETE_DIAGNOSTIC",
        }:
            stop_campaign = True
    ledger["campaign_state"] = "RESOURCE_OR_INFRASTRUCTURE_INTERRUPTED" if stop_campaign else "SCENARIOS_ATTEMPTED_ONCE"
    _write_json(archive / "run_ledger.json", ledger)

    report = subprocess.run(
        [sys.executable, str(REPORTER), "--archive", str(archive)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    (archive / "reporter.stdout.txt").write_text(report.stdout, encoding="utf-8")
    (archive / "reporter.stderr.txt").write_text(report.stderr, encoding="utf-8")
    ledger["reporter_return_code"] = report.returncode
    if report.returncode != 0:
        ledger["campaign_state"] = "REPORT_GENERATION_FAILURE"
    _write_json(archive / "run_ledger.json", ledger)
    archive_sha = _archive_hashes(archive)
    print(json.dumps({"archive": str(archive), "archive_integrity_manifest_sha256": archive_sha, "campaign_state": ledger["campaign_state"]}, sort_keys=True))
    return 1 if stop_campaign or report.returncode else 0


if __name__ == "__main__":
    raise SystemExit(main())
