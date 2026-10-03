"""Audit exact prebuilt release files against a prospective authorization contract."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__:
    from scripts.git_tools import git_run
    from scripts.verify_public_package import (
        digest,
        frozen_inputs,
        installed_probe_command,
        run_command,
        verify_archives,
        write_record,
    )
else:
    from git_tools import git_run
    from verify_public_package import (
        digest,
        frozen_inputs,
        installed_probe_command,
        run_command,
        verify_archives,
        write_record,
    )


def _relative_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("Contract paths must use non-empty canonical POSIX paths.")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts) or value.startswith("/"):
        raise ValueError("Contract paths must not contain aliases or traversal.")
    return value


def _committed_bytes(root: Path, head: str, relative: str) -> bytes:
    path = root / _relative_path(relative)
    committed = git_run(["show", f"{head}:{relative}"], cwd=root, check=True).stdout
    current = path.read_bytes()
    if current != committed and current.replace(b"\r\n", b"\n") != committed:
        raise ValueError(f"Committed contract input differs from its worktree bytes: {relative}")
    return committed


def _check_tool_bindings(root: Path, head: str, bindings: Any) -> None:
    if not isinstance(bindings, dict) or not bindings:
        raise ValueError("The release contract must bind its release verification tools.")
    for relative, expected in bindings.items():
        observed = hashlib.sha256(_committed_bytes(root, head, relative)).hexdigest()
        if observed != expected:
            raise ValueError(f"Release tool binding mismatch: {relative}")


def verify_artifact_set(dist: Path, contract: dict[str, Any]) -> dict[str, Any]:
    """Require exactly the two frozen packages and their exact SHA-256 manifest."""
    artifacts = contract.get("audited_artifacts")
    manifest = contract.get("sha256_manifest")
    if not isinstance(artifacts, dict) or set(artifacts) != {"wheel", "sdist"}:
        raise ValueError("The release contract must bind exactly one wheel and one sdist.")
    if not isinstance(manifest, dict) or set(manifest) != {"filename", "bytes", "sha256"}:
        raise ValueError("The release contract must bind one SHA-256 manifest.")

    expected: dict[str, dict[str, Any]] = {}
    for kind in ("wheel", "sdist"):
        binding = artifacts[kind]
        if not isinstance(binding, dict) or set(binding) != {"filename", "bytes", "sha256"}:
            raise ValueError(f"The frozen {kind} artifact binding is malformed.")
        filename = binding["filename"]
        _relative_path(filename)
        if Path(filename).name != filename or not filename.endswith(".whl" if kind == "wheel" else ".tar.gz"):
            raise ValueError(f"The frozen {kind} artifact filename is invalid.")
        if (
            not isinstance(binding["bytes"], int)
            or isinstance(binding["bytes"], bool)
            or binding["bytes"] <= 0
            or not isinstance(binding["sha256"], str)
            or len(binding["sha256"]) != 64
            or any(character not in "0123456789abcdef" for character in binding["sha256"])
        ):
            raise ValueError(f"The frozen {kind} artifact binding is malformed.")
        expected[filename] = binding

    manifest_name = manifest["filename"]
    _relative_path(manifest_name)
    if Path(manifest_name).name != manifest_name or not manifest_name.endswith("-SHA256SUMS.txt"):
        raise ValueError("The frozen SHA-256 manifest filename is invalid.")
    if (
        not isinstance(manifest["bytes"], int)
        or isinstance(manifest["bytes"], bool)
        or manifest["bytes"] <= 0
        or not isinstance(manifest["sha256"], str)
        or len(manifest["sha256"]) != 64
        or any(character not in "0123456789abcdef" for character in manifest["sha256"])
    ):
        raise ValueError("The frozen SHA-256 manifest binding is malformed.")
    expected[manifest_name] = manifest

    entries = list(dist.iterdir())
    if any(entry.is_symlink() or not entry.is_file() for entry in entries):
        raise ValueError("Release assets must be regular files without symlinks.")
    if {entry.name for entry in entries} != set(expected) or len(entries) != len(expected):
        raise ValueError("Release assets must contain only the two selected packages and SHA-256 manifest.")

    observed: dict[str, dict[str, Any]] = {}
    for name, binding in expected.items():
        path = dist / name
        payload = path.read_bytes()
        current = {"filename": name, "bytes": len(payload), "sha256": digest(payload)}
        if current != binding:
            raise ValueError(f"Release asset differs from the authorized contract: {name}")
        observed[name] = current

    wheel = artifacts["wheel"]
    sdist = artifacts["sdist"]
    manifest_text = (
        f"{wheel['sha256']}  {wheel['filename']}\n"
        f"{sdist['sha256']}  {sdist['filename']}\n"
    ).encode("ascii")
    if (dist / manifest_name).read_bytes() != manifest_text:
        raise ValueError("The SHA-256 manifest does not exactly describe the selected package bytes.")
    return {"status": "PASS_EXACT_RELEASE_ASSETS", "files": list(observed.values())}


def _validate_contract(root: Path, contract_path: Path, candidate_path: Path) -> tuple[
    dict[str, Any], dict[str, Any], dict[str, bytes], list[dict[str, Any]], str
]:
    root = root.resolve(strict=True)
    contract_path = contract_path.resolve(strict=True)
    candidate_path = candidate_path.resolve(strict=True)
    if not contract_path.is_relative_to(root) or not candidate_path.is_relative_to(root):
        raise ValueError("Release contracts must be committed inside the repository.")
    head = git_run(["rev-parse", "HEAD"], cwd=root, check=True, text=True).stdout.strip()
    if git_run(["status", "--porcelain", "--untracked-files=all"], cwd=root, check=True).stdout.strip():
        raise ValueError("The release verification checkout must be clean.")

    relative_contract = contract_path.relative_to(root).as_posix()
    relative_candidate = candidate_path.relative_to(root).as_posix()
    release_contract = json.loads(_committed_bytes(root, head, relative_contract))
    source_contract = release_contract.get("source_contract", {})
    if source_contract.get("path") != relative_candidate:
        raise ValueError("The supplied frozen package contract path differs from the authorized release contract.")
    candidate_contract, payloads, mapping, execution_head = frozen_inputs(root, candidate_path)
    if execution_head != head:
        raise ValueError("Release contract validation observed inconsistent execution commits.")
    if release_contract.get("status") != "OWNER_AUTHORIZED_SELECTED_PACKAGE_RELEASE":
        raise ValueError("The release contract does not record an Owner-authorized selected release.")
    source_sha = release_contract.get("source_sha")
    if source_sha != candidate_contract.get("source_sha") or source_sha != release_contract.get("tag_target_sha"):
        raise ValueError("The authorized release source, frozen package source and tag target must be identical.")
    if git_run(["merge-base", "--is-ancestor", source_sha, head], cwd=root).returncode:
        raise ValueError("The audited package source is not an ancestor of the release-contract commit.")
    if candidate_contract.get("publication_allowed") is not False:
        raise ValueError("The prior candidate contract must remain unchanged and non-authorizing.")
    if candidate_contract.get("source_sha") != source_sha:
        raise ValueError("The selected package contract and authorization source differ.")

    candidate_commit = release_contract.get("source_contract", {}).get("commit_sha")
    candidate_digest = hashlib.sha256(_committed_bytes(root, head, relative_candidate)).hexdigest()
    if (
        not isinstance(candidate_commit, str)
        or candidate_digest != source_contract.get("sha256")
        or git_run(["merge-base", "--is-ancestor", candidate_commit, head], cwd=root).returncode
        or git_run(["merge-base", "--is-ancestor", source_sha, candidate_commit], cwd=root).returncode
        or hashlib.sha256(git_run(["show", f"{candidate_commit}:{relative_candidate}"], cwd=root, check=True).stdout).hexdigest()
        != candidate_digest
    ):
        raise ValueError("The prospective source contract commit or bytes do not match the release contract.")

    owner = release_contract.get("owner_authorization", {})
    owner_path = _relative_path(owner.get("path", ""))
    owner_commit = owner.get("commit_sha")
    owner_bytes = _committed_bytes(root, head, owner_path)
    owner_record = json.loads(owner_bytes)
    recorded_owner_bytes = git_run(["show", f"{owner_commit}:{owner_path}"], cwd=root, check=True).stdout
    if (
        hashlib.sha256(owner_bytes).hexdigest() != owner.get("sha256")
        or hashlib.sha256(recorded_owner_bytes).hexdigest() != owner.get("sha256")
        or git_run(["merge-base", "--is-ancestor", owner_commit, source_sha], cwd=root).returncode
        or owner_record.get("decision") != "AUTHORIZE_V0_2_10_PUBLICATION"
    ):
        raise ValueError("The original Owner authorization record is missing, changed, or not an ancestor of the source.")
    allowed = owner_record.get("authorization", {})
    for key in (
        "selected_package_publication_allowed", "tag_creation_allowed", "pypi_publication_allowed",
        "github_release_allowed", "zenodo_selected_artifact_publication_allowed",
    ):
        if allowed.get(key) is not True:
            raise ValueError(f"The Owner record does not authorize {key}.")

    required_authority = {
        "selected_package_publication_allowed": True,
        "tag_creation_allowed": True,
        "pypi_publication_allowed": True,
        "github_release_allowed": True,
        "zenodo_selected_artifact_publication_allowed": True,
        "whole_repository_archive_cleared": False,
        "ledger_update_allowed": False,
        "wp14_promotion_allowed": False,
        "numeric_maturity_promotion_allowed": False,
        "historical_result_reclassification_allowed": False,
    }
    if release_contract.get("authorization") != required_authority:
        raise ValueError("The prospective release contract broadens or weakens the Owner's bounded authority.")
    if (
        release_contract.get("g03_status") != "FAIL_PRESERVED"
        or release_contract.get("whole_repository_archive_cleared") is not False
        or release_contract.get("wp14_status") != "HOLD_NOT_PROMOTED"
    ):
        raise ValueError("G03 and WP14 must remain explicitly uncleared and unpromoted.")

    bindings = release_contract.get("tool_bindings")
    _check_tool_bindings(root, head, bindings)
    manifest_path = _relative_path(release_contract.get("manifest_repository_path", ""))
    manifest_bytes = _committed_bytes(root, head, manifest_path)
    manifest_binding = release_contract["sha256_manifest"]
    if (
        len(manifest_bytes) != manifest_binding.get("bytes")
        or hashlib.sha256(manifest_bytes).hexdigest() != manifest_binding.get("sha256")
    ):
        raise ValueError("Committed SHA-256 manifest bytes do not match the release contract.")
    selected_scope = release_contract.get("selected_scope")
    if not isinstance(selected_scope, dict) or len(payloads) != selected_scope.get("package_source_files"):
        raise ValueError("The selected package file count differs from the prospective release contract.")
    if release_contract.get("package_version") != candidate_contract.get("package_version"):
        raise ValueError("The authorized package version differs from the frozen package contract.")
    return release_contract, candidate_contract, payloads, mapping, head


def verify_authorized_release(
    root: Path, contract_path: Path, candidate_path: Path, dist: Path, output: Path,
) -> dict[str, Any]:
    root = root.resolve(strict=True)
    dist = dist.resolve(strict=True)
    output = output.resolve()
    if output.is_relative_to(root) or root.is_relative_to(output) or output.exists():
        raise ValueError("Use a new external evidence directory; existing outputs are never overwritten.")
    if dist.is_relative_to(root) or root.is_relative_to(dist):
        raise ValueError("The release asset directory must be external to the repository.")

    contract, candidate, payloads, mapping, head = _validate_contract(root, contract_path, candidate_path)
    assets = verify_artifact_set(dist, contract)
    output.mkdir(parents=True, exist_ok=False)
    neutral = output / "outside_checkout"
    logs = output / "logs"
    published_dist = output / "dist"
    for path in (neutral, logs, published_dist):
        path.mkdir()
    for kind in ("wheel", "sdist"):
        name = contract["audited_artifacts"][kind]["filename"]
        shutil.copyfile(dist / name, published_dist / name)

    package_check = verify_archives(published_dist, payloads, contract["package_version"])
    observed = {item["path"]: item for item in package_check["binaries"]}
    for kind in ("wheel", "sdist"):
        actual = observed.get(contract["audited_artifacts"][kind]["filename"])
        expected = contract["audited_artifacts"][kind]
        if actual != {
            "path": expected["filename"],
            "bytes": expected["bytes"],
            "sha256": expected["sha256"],
        }:
            raise ValueError(f"Exact {kind} bytes differ from the authorized artifact binding.")
    write_record(output / "source_mapping.json", mapping)
    write_record(output / "package_check.json", package_check)
    write_record(output / "asset_check.json", assets)

    records: list[dict[str, Any]] = []
    run_command(
        [sys.executable, "-m", "twine", "check",
         str(published_dist / package_check["wheel"]), str(published_dist / package_check["sdist"])],
        neutral, logs, records,
    )
    run_command(
        [sys.executable, str(root / "scripts" / "check_distribution.py"),
         str(published_dist / package_check["wheel"]), str(published_dist / package_check["sdist"])],
        neutral, logs, records,
    )
    environment = output / "installed_env"
    run_command([sys.executable, "-m", "venv", "--system-site-packages", str(environment)], neutral, logs, records)
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    run_command(
        [str(python), "-I", "-m", "pip", "install", "--no-deps", "--no-index",
         str(published_dist / package_check["wheel"])],
        neutral, logs, records,
    )
    console = environment / ("Scripts" if os.name == "nt" else "bin")
    for name in ("qf-solver", "solveur-ef", "mitc4-solver"):
        launcher = console / (name + ".exe" if os.name == "nt" else name)
        run_command([str(launcher), "--version"], neutral, logs, records)
    qf = console / ("qf-solver.exe" if os.name == "nt" else "qf-solver")
    run_command([str(qf), "--help"], neutral, logs, records)
    probe = root / "scripts" / "probe_installed_package.py"
    probes = []
    for label, cwd in (("outside_checkout", neutral), ("inside_checkout", root)):
        report = output / f"{label}_probe.json"
        run_command(
            installed_probe_command(python, probe, output / "source_mapping.json",
                                    contract["package_version"], report),
            cwd, logs, records,
        )
        probes.append(json.loads(report.read_text(encoding="utf-8")))

    result = {
        "status": "PASS_AUTHORIZED_SELECTED_ARTIFACTS_ONLY",
        "release_tag": contract["release_tag"],
        "package_version": contract["package_version"],
        "source_sha": contract["source_sha"],
        "execution_sha": head,
        "release_contract_commit_sha": git_run(
            ["log", "-1", "--format=%H", head, "--", contract_path.resolve().relative_to(root).as_posix()],
            cwd=root, check=True, text=True,
        ).stdout.strip(),
        "release_contract_sha256": hashlib.sha256(
            git_run(["show", f"{head}:{contract_path.resolve().relative_to(root).as_posix()}"], cwd=root, check=True).stdout
        ).hexdigest(),
        "source_contract_sha256": candidate["contract_sha256"],
        "owner_authorization_commit_sha": contract["owner_authorization"]["commit_sha"],
        "package_check": package_check,
        "release_asset_check": assets,
        "installed_probes": probes,
        "artifact_audit_runtime": {
            "python": sys.version,
            "executable": sys.executable,
            "setuptools": importlib.metadata.version("setuptools"),
            "twine": importlib.metadata.version("twine"),
        },
        "build_policy": contract["build_provenance"],
        "publication_performed": False,
        "g03_status": "FAIL_PRESERVED",
        "whole_repository_archive_cleared": False,
        "wp14_status": "HOLD_NOT_PROMOTED",
        "ledger_changed": False,
        "structural_solves_run": False,
        "numeric_maturity_changed": False,
    }
    write_record(output / "commands.json", records)
    write_record(output / "result.json", result)
    files = sorted(path for path in output.rglob("*") if path.is_file())
    write_record(output / "manifest.json", {
        "files": [
            {"path": path.relative_to(output).as_posix(), "bytes": path.stat().st_size,
             "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            for path in files
        ],
        "includes_prebuilt_selected_artifacts_and_install_logs": True,
        "rebuild_performed": False,
    })
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--source-contract", type=Path, required=True)
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(
            verify_authorized_release(args.root, args.contract, args.source_contract, args.dist, args.output),
            indent=2,
        ))
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        parser.exit(1, f"FAIL_CLOSED: {type(exc).__name__}: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
