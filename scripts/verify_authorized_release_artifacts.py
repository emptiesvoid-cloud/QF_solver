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


OWNER_REAUTHORIZATION_PATH = "qualification/0_2_10/owner_publication_reauthorization_b453265d.json"
OWNER_REAUTHORIZATION_COMMIT = "e350ef870dfa5182a4e25c79c07ce04b974d5568"
OWNER_REAUTHORIZATION_SHA256 = "8d684c17345f827ea70ab647c2e38cd4b3b711e0e8925207c09881f3582b20a7"
OWNER_REAUTHORIZATION_ID = "QF-0210-OWNER-PUBLICATION-REAUTHORIZATION-B453265D"
AUTHORIZED_SOURCE_SHA = "b453265d5e61acd5f91cfc3aa236ee8b85344033"
AUTHORIZED_TAG = "v0.2.10"
AUTHORIZED_ARTIFACTS = {
    "wheel": {
        "filename": "qf_solver-0.2.10-py3-none-any.whl",
        "bytes": 1509431,
        "sha256": "5c97d11cdc199512658ca3067b16beb7d72a2f6a183a171db5e921884709ca10",
    },
    "sdist": {
        "filename": "qf_solver-0.2.10.tar.gz",
        "bytes": 1114202,
        "sha256": "35ce10458e84425558396f1246b55e217734e0fa0189df242fbc2242bca9099d",
    },
    "manifest": {
        "filename": "qf_solver-0.2.10-SHA256SUMS.txt",
        "bytes": 190,
        "sha256": "fbe097e7d785d9d0c63cc16f562a32166da3aca300fc0693ef1777ba3bd85d7a",
    },
}
SUPERSEDED_OWNER_RECORD = {
    "path": "qualification/0_2_10/owner_publication_authorization.json",
    "commit_sha": "61e692cddb3e6feb3c6006beec6d2f2b55205f15",
    "sha256": "65999315d3e2950c6a734092d3c1417dd53c332e220bb90257d762fd91c90c99",
    "historical_record_preserved": True,
}


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


def validate_owner_artifact_scope(contract: dict[str, Any], owner_record: dict[str, Any]) -> None:
    """Require a prospective release to stay inside the Owner's exact source and byte authorization."""
    approved_source = owner_record.get("authorized_source_sha")
    if (
        owner_record.get("record_id") != OWNER_REAUTHORIZATION_ID
        or owner_record.get("decision") != "AUTHORIZE_V0_2_10_PUBLICATION"
        or owner_record.get("version") != "0.2.10"
        or approved_source != AUTHORIZED_SOURCE_SHA
        or contract.get("source_sha") != AUTHORIZED_SOURCE_SHA
        or contract.get("tag_target_sha") != approved_source
        or owner_record.get("authorized_tag_target_sha") != approved_source
        or owner_record.get("authorized_tag") != AUTHORIZED_TAG
        or contract.get("release_tag") != AUTHORIZED_TAG
    ):
        raise ValueError("The candidate source differs from the exact source accepted by the Owner.")

    artifacts = contract.get("audited_artifacts")
    approved_artifacts = owner_record.get("authorized_artifacts")
    if not isinstance(artifacts, dict) or not isinstance(approved_artifacts, dict):
        raise ValueError("The prospective release does not bind the Owner-authorized package bytes.")
    for kind in ("wheel", "sdist", "manifest"):
        approved = approved_artifacts.get(kind)
        candidate = contract.get("sha256_manifest") if kind == "manifest" else artifacts.get(kind)
        if not isinstance(approved, dict) or not isinstance(candidate, dict) or approved != AUTHORIZED_ARTIFACTS[kind]:
            raise ValueError(f"The Owner authorization lacks the exact {kind} artifact binding.")
        if (
            candidate.get("filename") != approved.get("filename")
            or candidate.get("bytes") != approved.get("bytes")
            or candidate.get("sha256") != approved.get("sha256")
        ):
            raise ValueError(f"The candidate {kind} bytes differ from the exact artifact accepted by the Owner.")

    required_authorization = {
        "selected_package_publication_allowed": True,
        "tag_creation_allowed": True,
        "pypi_publication_allowed": True,
        "github_release_allowed": True,
        "zenodo_selected_artifact_publication_allowed": True,
        "whole_repository_archive_cleared": False,
        "whole_repository_archive_publication_allowed": False,
        "ledger_update_allowed": False,
        "wp14_promotion_allowed": False,
        "numeric_maturity_promotion_allowed": False,
        "historical_result_reclassification_allowed": False,
        "certification_or_universal_validation_claims_allowed": False,
    }
    if owner_record.get("authorization") != required_authorization:
        raise ValueError("The Owner authorization permissions broaden or weaken the selected-release boundary.")
    required_top_level_flags = {
        "selected_package_publication_allowed": True,
        "tag_creation_allowed": True,
        "pypi_publication_allowed": True,
        "github_release_allowed": True,
        "zenodo_selected_artifact_publication_allowed": True,
        "whole_repository_archive_cleared": False,
        "whole_repository_archive_publication_allowed": False,
        "wp14_promotion_allowed": False,
        "numeric_maturity_promotion_allowed": False,
        "historical_result_reclassification_allowed": False,
        "ledger_update_allowed": False,
        "certification_or_universal_validation_claims_allowed": False,
    }
    if any(owner_record.get(key) is not expected for key, expected in required_top_level_flags.items()):
        raise ValueError("The Owner record's direct permissions broaden or weaken the selected-release boundary.")
    required_hashes = {
        "authorized_wheel_sha256": approved_artifacts["wheel"].get("sha256"),
        "authorized_sdist_sha256": approved_artifacts["sdist"].get("sha256"),
        "authorized_manifest_sha256": approved_artifacts["manifest"].get("sha256"),
    }
    if any(owner_record.get(key) != expected for key, expected in required_hashes.items()):
        raise ValueError("The Owner record's direct artifact hashes differ from its exact artifact bindings.")
    required_preserved = {
        "g03_status": "FAIL_PRESERVED",
        "whole_repository_archive_cleared": False,
        "wp14_status": "HOLD_NOT_PROMOTED",
        "numeric_maturity_promotion_allowed": False,
        "historical_result_reclassification_allowed": False,
        "ledger_update_allowed": False,
    }
    if any(owner_record.get(key) != expected for key, expected in required_preserved.items()):
        raise ValueError("The Owner record changes the preserved release boundary.")
    if owner_record.get("whole_repository_archive_publication_allowed") is not False:
        raise ValueError("The Owner record permits whole-repository archive publication despite G03.")
    expected_gate_summary = {
        "g03_status": "FAIL_PRESERVED",
        "whole_repository_archive_cleared": False,
        "wp14_status": "HOLD_NOT_PROMOTED",
    }
    if owner_record.get("preserved_gates") != expected_gate_summary:
        raise ValueError("The Owner record's preserved gate summary is inconsistent.")


def _validate_superseded_owner_record(
    root: Path, head: str, owner_record: dict[str, Any], contract: dict[str, Any],
) -> None:
    previous = owner_record.get("superseded_record")
    previous_contract = contract.get("superseded_owner_authorization")
    if not isinstance(previous, dict) or not isinstance(previous_contract, dict):
        raise ValueError("The prospective reauthorization must identify the preserved historical Owner record.")
    path = _relative_path(previous.get("path", ""))
    if previous != SUPERSEDED_OWNER_RECORD or previous != previous_contract:
        raise ValueError("The superseded Owner record reference differs from the prospective contract.")
    commit = previous.get("commit_sha")
    if (
        owner_record.get("supersedes_for_release") != "QF-0210-OWNER-PUBLICATION-AUTHORIZATION-2026-10-03"
        or git_run(["merge-base", "--is-ancestor", commit, contract["source_sha"]], cwd=root).returncode
    ):
        raise ValueError("The reauthorization does not supersede the exact historical decision for this release.")
    historical_bytes = git_run(["show", f"{commit}:{path}"], cwd=root, check=True).stdout
    current_bytes = _committed_bytes(root, head, path)
    if (
        hashlib.sha256(historical_bytes).hexdigest() != previous.get("sha256")
        or hashlib.sha256(current_bytes).hexdigest() != previous.get("sha256")
    ):
        raise ValueError("The historical Owner record was changed or does not match its recorded hash.")
    historical = json.loads(historical_bytes)
    if historical.get("record_id") != owner_record.get("supersedes_for_release"):
        raise ValueError("The historical Owner record identity does not match the superseded decision.")
    old_source = historical.get("provenance", {}).get("audited_package_source_sha")
    if old_source == contract.get("source_sha"):
        raise ValueError("The prospective record must bind a distinct later candidate, not rewrite the prior decision.")


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
    if (
        owner_path != OWNER_REAUTHORIZATION_PATH
        or owner_commit != OWNER_REAUTHORIZATION_COMMIT
        or owner.get("sha256") != OWNER_REAUTHORIZATION_SHA256
        or owner.get("record_id") != OWNER_REAUTHORIZATION_ID
    ):
        raise ValueError("The release contract does not bind the exact prospective Owner reauthorization.")
    owner_bytes = _committed_bytes(root, head, owner_path)
    owner_record = json.loads(owner_bytes)
    recorded_owner_bytes = git_run(["show", f"{owner_commit}:{owner_path}"], cwd=root, check=True).stdout
    if (
        hashlib.sha256(owner_bytes).hexdigest() != owner.get("sha256")
        or hashlib.sha256(recorded_owner_bytes).hexdigest() != owner.get("sha256")
        or git_run(["merge-base", "--is-ancestor", owner_commit, head], cwd=root).returncode
        or git_run(["merge-base", "--is-ancestor", source_sha, owner_commit], cwd=root).returncode
    ):
        raise ValueError("The prospective Owner reauthorization is missing, changed, or out of source/governance order.")
    if (
        owner.get("record_id") != owner_record.get("record_id")
        or owner.get("supersedes_for_release") != owner_record.get("supersedes_for_release")
        or owner_record.get("status") != "OWNER_REAUTHORIZED_LATER_AUDITED_RELEASE_CANDIDATE"
    ):
        raise ValueError("The contract does not identify the exact prospective Owner reauthorization.")
    _validate_superseded_owner_record(root, head, owner_record, release_contract)
    validate_owner_artifact_scope(release_contract, owner_record)
    resolution = release_contract.get("authorization_resolution", {})
    resolution_hashes = {
        "owner_approved_wheel_sha256": release_contract["audited_artifacts"]["wheel"]["sha256"],
        "candidate_wheel_sha256": release_contract["audited_artifacts"]["wheel"]["sha256"],
        "owner_approved_sdist_sha256": release_contract["audited_artifacts"]["sdist"]["sha256"],
        "candidate_sdist_sha256": release_contract["audited_artifacts"]["sdist"]["sha256"],
        "owner_approved_manifest_sha256": release_contract["sha256_manifest"]["sha256"],
        "candidate_manifest_sha256": release_contract["sha256_manifest"]["sha256"],
    }
    if (
        resolution.get("status") != "RESOLVED_BY_OWNER_REAUTHORIZATION"
        or resolution.get("owner_approved_source_sha") != source_sha
        or resolution.get("candidate_source_sha") != source_sha
        or any(resolution.get(key) != value for key, value in resolution_hashes.items())
    ):
        raise ValueError("The release contract's Owner reauthorization resolution is stale or inconsistent.")

    required_authority = {
        "selected_package_publication_allowed": True,
        "tag_creation_allowed": True,
        "pypi_publication_allowed": True,
        "github_release_allowed": True,
        "zenodo_selected_artifact_publication_allowed": True,
        "whole_repository_archive_cleared": False,
        "whole_repository_archive_publication_allowed": False,
        "ledger_update_allowed": False,
        "wp14_promotion_allowed": False,
        "numeric_maturity_promotion_allowed": False,
        "historical_result_reclassification_allowed": False,
        "certification_or_universal_validation_claims_allowed": False,
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
