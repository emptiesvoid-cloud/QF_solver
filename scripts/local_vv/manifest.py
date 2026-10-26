"""Manifest, identity, environment and Owner-decision checks for local V&V."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import re
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

MANIFEST_SCHEMA = "qf-local-vv-campaign-v1"
DECISION_SCHEMA = "qf-local-vv-owner-execution-decision-v1"
NODEID_PATTERN = re.compile(r"^tests/unit/[A-Za-z0-9_./-]+\.py::test_[A-Za-z0-9_]+$")
IDENTITY_PATTERN = re.compile(r"^[0-9a-f]{40}$")
HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
RESULT_MARKER = "QF_VV_NUMERIC_RESULT="


class LocalVVError(RuntimeError):
    """A preflight or local-runner failure that must fail closed."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    if not isinstance(value, dict):
        raise LocalVVError(f"expected a JSON object: {path}")
    return value, raw


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_manifest_shape(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if manifest.get("schema") != MANIFEST_SCHEMA:
        errors.append("unsupported local V&V manifest schema")
    if manifest.get("policy") != "QUALIFICATION_LOCAL_VV":
        errors.append("manifest is not governed by QUALIFICATION_LOCAL_VV")
    if manifest.get("status") != "PREPARED_NOT_AUTHORIZED":
        errors.append("campaign manifest must remain PREPARED_NOT_AUTHORIZED")
    campaign_id = manifest.get("campaign_id")
    if not isinstance(campaign_id, str) or not re.fullmatch(r"[A-Z0-9][A-Z0-9._-]{2,79}", campaign_id):
        errors.append("campaign_id is invalid")

    identities = manifest.get("identities")
    if not isinstance(identities, dict):
        errors.append("identities object is required")
        identities = {}
    for key in ("science", "runner", "tests"):
        identity = identities.get(key)
        if not isinstance(identity, dict):
            errors.append(f"identities.{key} is required")
            continue
        if not isinstance(identity.get("path"), str) or not Path(identity["path"]).is_absolute():
            errors.append(f"identities.{key}.path must be absolute")
        for field in ("commit", "tree"):
            if not isinstance(identity.get(field), str) or not IDENTITY_PATTERN.fullmatch(identity[field]):
                errors.append(f"identities.{key}.{field} must be a full lowercase Git OID")

    environment = manifest.get("environment")
    if not isinstance(environment, dict):
        errors.append("environment object is required")
        environment = {}
    python = environment.get("python")
    if not isinstance(python, dict):
        errors.append("environment.python is required")
    else:
        if not isinstance(python.get("executable"), str) or not Path(python["executable"]).is_absolute():
            errors.append("environment.python.executable must be absolute")
        if not isinstance(python.get("version"), str):
            errors.append("environment.python.version is required")
    packages = environment.get("packages")
    if not isinstance(packages, dict) or not packages:
        errors.append("environment.packages must list exact package versions")
    thread_environment = environment.get("thread_environment")
    if not isinstance(thread_environment, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in thread_environment.items()
    ):
        errors.append("environment.thread_environment must contain string values")

    evidence_root = manifest.get("evidence_root")
    if not isinstance(evidence_root, str) or not Path(evidence_root).is_absolute():
        errors.append("evidence_root must be an absolute path")

    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        errors.append("cases must be a non-empty list")
        cases = []
    seen_case_ids: set[str] = set()
    for index, case in enumerate(cases):
        prefix = f"cases[{index}]"
        if not isinstance(case, dict):
            errors.append(f"{prefix} must be an object")
            continue
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not re.fullmatch(r"[A-Z0-9][A-Z0-9._-]{2,79}", case_id):
            errors.append(f"{prefix}.case_id is invalid")
        elif case_id in seen_case_ids:
            errors.append(f"duplicate case_id: {case_id}")
        else:
            seen_case_ids.add(case_id)
        nodeid = case.get("nodeid")
        if not isinstance(nodeid, str) or not NODEID_PATTERN.fullmatch(nodeid):
            errors.append(f"{prefix}.nodeid must be one exact, non-parameterized unit-test nodeid")
        else:
            node_path = PurePosixPath(nodeid.split("::", maxsplit=1)[0])
            if ".." in node_path.parts or node_path.is_absolute() or "*" in nodeid:
                errors.append(f"{prefix}.nodeid contains a forbidden path or selector")
        if case.get("status") != "PREPARED_NOT_AUTHORIZED":
            errors.append(f"{prefix}.status must be PREPARED_NOT_AUTHORIZED")
        test_checkout = case.get("test_checkout", "tests")
        if not isinstance(test_checkout, str) or test_checkout not in {"science", "runner", "tests"}:
            errors.append(f"{prefix}.test_checkout is invalid")
        timeout = case.get("timeout_seconds")
        if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0:
            errors.append(f"{prefix}.timeout_seconds must be a positive integer")
        output_limit = case.get("output_limit_bytes")
        if not isinstance(output_limit, int) or isinstance(output_limit, bool) or output_limit <= 0:
            errors.append(f"{prefix}.output_limit_bytes must be a positive integer")
        if case.get("max_attempts") != 1:
            errors.append(f"{prefix}.max_attempts must be exactly one")
        inventory = case.get("file_inventory")
        if not isinstance(inventory, list) or not inventory:
            errors.append(f"{prefix}.file_inventory must be non-empty")
        else:
            node_path_text = nodeid.split("::", maxsplit=1)[0] if isinstance(nodeid, str) else ""
            test_checkout = case.get("test_checkout", "tests")
            if not any(
                isinstance(item, dict) and item.get("checkout") == test_checkout and item.get("path") == node_path_text
                for item in inventory
            ):
                errors.append(f"{prefix}.file_inventory must include the exact nodeid source file")
            for file_index, item in enumerate(inventory):
                if not isinstance(item, dict):
                    errors.append(f"{prefix}.file_inventory[{file_index}] must be an object")
                    continue
                if item.get("checkout") not in {"science", "runner", "tests"}:
                    errors.append(f"{prefix}.file_inventory[{file_index}].checkout is invalid")
                relative = item.get("path")
                if not isinstance(relative, str):
                    errors.append(f"{prefix}.file_inventory[{file_index}].path is required")
                else:
                    candidate = PurePosixPath(relative)
                    if candidate.is_absolute() or ".." in candidate.parts or "*" in relative:
                        errors.append(f"{prefix}.file_inventory[{file_index}].path must stay within its checkout")
                if not isinstance(item.get("sha256"), str) or not HASH_PATTERN.fullmatch(item["sha256"]):
                    errors.append(f"{prefix}.file_inventory[{file_index}].sha256 must be a SHA-256 hex digest")
                if not isinstance(item.get("git_blob_oid"), str) or not IDENTITY_PATTERN.fullmatch(
                    item["git_blob_oid"]
                ):
                    errors.append(f"{prefix}.file_inventory[{file_index}].git_blob_oid must be a full Git blob OID")
    return errors


def _checkout_path(manifest: dict[str, Any], key: str) -> Path:
    return Path(manifest["identities"][key]["path"]).resolve()


def _relative_file(root: Path, relative: str) -> Path:
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts:
        raise LocalVVError(f"unsafe relative file path: {relative}")
    candidate = root.joinpath(*pure.parts).resolve(strict=True)
    if not candidate.is_relative_to(root.resolve()):
        raise LocalVVError(f"file escapes its declared checkout: {relative}")
    _reject_reparse_components(candidate, root.resolve())
    return candidate


def _reject_reparse_components(path: Path, root: Path) -> None:
    current = root
    relative = path.relative_to(root)
    for part in relative.parts:
        current = current / part
        if not current.exists():
            continue
        attributes = getattr(current.stat(), "st_file_attributes", 0)
        reparse_point = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        if current.is_symlink() or attributes & reparse_point:
            raise LocalVVError(f"reparse point/symlink is not permitted in a checked path: {current}")


def _git_value(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=15,
    )
    if result.returncode:
        raise LocalVVError(f"git {args[0]} failed in {root}: {result.stderr.strip()}")
    return result.stdout.strip()


def inspect_checkout(identity: dict[str, Any]) -> dict[str, str]:
    root = Path(identity["path"]).resolve(strict=True)
    git_root = Path(_git_value(root, "rev-parse", "--show-toplevel")).resolve(strict=True)
    if git_root != root:
        raise LocalVVError(f"declared path is not the canonical Git root: {root}")
    commit = _git_value(root, "rev-parse", "HEAD")
    tree = _git_value(root, "rev-parse", "HEAD^{tree}")
    dirty = _git_value(root, "status", "--porcelain", "--untracked-files=all")
    if commit != identity["commit"] or tree != identity["tree"]:
        raise LocalVVError(f"Git identity mismatch at {root}")
    if dirty:
        raise LocalVVError(f"checkout is not clean: {root}")
    return {"path": str(root), "commit": commit, "tree": tree, "status": "CLEAN"}


def verify_runner_entrypoint(manifest: dict[str, Any]) -> str:
    """Require this CLI file to be executed from the manifest-bound runner tree."""
    expected = (_checkout_path(manifest, "runner") / "scripts" / "run_local_vv.py").resolve(strict=True)
    actual = Path(sys.argv[0]).resolve(strict=True)
    if actual != expected:
        raise LocalVVError(f"runner entrypoint path mismatch: expected {expected}, executing {actual}")
    return str(actual)


def verify_file_inventory(manifest: dict[str, Any], case: dict[str, Any]) -> list[dict[str, str]]:
    observed: list[dict[str, str]] = []
    for item in case["file_inventory"]:
        root = _checkout_path(manifest, item["checkout"])
        file_path = _relative_file(root, item["path"])
        digest = sha256_file(file_path)
        if digest != item["sha256"]:
            raise LocalVVError(f"file hash mismatch: {item['checkout']}:{item['path']}")
        blob_oid = _git_value(root, "rev-parse", f"HEAD:{item['path']}")
        if blob_oid != item["git_blob_oid"]:
            raise LocalVVError(f"Git blob OID mismatch: {item['checkout']}:{item['path']}")
        observed.append(
            {
                "checkout": item["checkout"],
                "path": item["path"],
                "sha256": digest,
                "git_blob_oid": blob_oid,
            }
        )
    return observed


def verify_environment(manifest: dict[str, Any]) -> dict[str, Any]:
    expected = manifest["environment"]
    python = expected["python"]
    if os.path.normcase(os.path.realpath(sys.executable)) != os.path.normcase(os.path.realpath(python["executable"])):
        raise LocalVVError("runner is using a different Python executable than the manifest")
    observed_version = platform.python_version()
    if observed_version != python["version"]:
        raise LocalVVError(f"Python version mismatch: expected {python['version']}, got {observed_version}")
    package_versions: dict[str, str | None] = {}
    package_locations: dict[str, str | None] = {}
    for name, required_version in expected["packages"].items():
        try:
            distribution = importlib.metadata.distribution(name)
            version = distribution.version
            package_locations[name] = str(distribution.locate_file("").resolve())
        except importlib.metadata.PackageNotFoundError:
            version = None
            package_locations[name] = None
        package_versions[name] = version
        if version != required_version:
            raise LocalVVError(f"package version mismatch for {name}: expected {required_version}, got {version}")
    return {
        "python_executable": sys.executable,
        "python_version": observed_version,
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "packages": package_versions,
        "package_locations": package_locations,
        "declared_thread_environment": dict(expected["thread_environment"]),
        "observed_parent_thread_environment": {key: os.environ.get(key) for key in expected["thread_environment"]},
        "venv_prefix": str(Path(sys.prefix).resolve()),
        "base_prefix": str(Path(sys.base_prefix).resolve()),
        "installed_solver_distribution": package_versions.get("qf-solver"),
    }


def _execution_environment(
    manifest: dict[str, Any], run_dir: Path | None = None, *, expected_nodeid: str = ""
) -> dict[str, str]:
    inherited_names = (
        "PATH",
        "SystemRoot",
        "WINDIR",
        "COMSPEC",
        "PATHEXT",
        "SYSTEMDRIVE",
        "USERPROFILE",
        "HOMEDRIVE",
        "HOMEPATH",
        "APPDATA",
        "LOCALAPPDATA",
    )
    result = {name: os.environ[name] for name in inherited_names if name in os.environ}
    source_root = _checkout_path(manifest, "science") / "src"
    runner_scripts = _checkout_path(manifest, "runner") / "scripts"
    result["VIRTUAL_ENV"] = manifest["environment"]["python"].get("venv", "")
    result.update(manifest["environment"]["thread_environment"])
    result.update(
        {
            "PYTHONPATH": os.pathsep.join((str(source_root), str(runner_scripts))),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONSAFEPATH": "1",
            "PYTHONHASHSEED": "0",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "QF_LOCAL_VV_EXPECTED_NODEID": expected_nodeid,
            "QF_LOCAL_VV_EXPECTED_SOURCE_ROOT": str(source_root),
        }
    )
    if run_dir is not None:
        result["QF_LOCAL_VV_SELECTION_PATH"] = str(run_dir / "selection.json")
        result["TMP"] = str(run_dir / "tmp")
        result["TEMP"] = str(run_dir / "tmp")
    else:
        result.pop("QF_LOCAL_VV_SELECTION_PATH", None)
    return result


def probe_import_origin(manifest: dict[str, Any], environment: dict[str, str]) -> dict[str, Any]:
    python = manifest["environment"]["python"]["executable"]
    source_root = _checkout_path(manifest, "science")
    probe_code = (
        "import importlib.metadata as m, json, solveur, sys; "
        "import numpy, scipy; from threadpoolctl import threadpool_info; "
        "d=next((x.version for x in m.distributions() if (x.metadata.get('Name') or '').lower()=='qf-solver'), None); "
        "print(json.dumps({'file':solveur.__file__,'version':solveur.__version__,'distribution':d,'python':sys.executable,"
        "'numpy':numpy.__version__,'scipy':scipy.__version__,'native_libraries':threadpool_info()}))"
    )
    probe_env = dict(environment)
    probe_env["PYTHONPATH"] = str(source_root / "src")
    result = subprocess.run(
        [python, "-c", probe_code],
        cwd=source_root,
        env=probe_env,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
    )
    if result.returncode:
        raise LocalVVError(f"non-numerical source-import probe failed: {result.stderr[-1000:]}")
    try:
        observed = json.loads(result.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        raise LocalVVError("source-import probe did not return valid JSON") from exc
    expected_file = (source_root / "src" / "solveur" / "__init__.py").resolve()
    if Path(observed.get("file", "")).resolve() != expected_file:
        raise LocalVVError(f"solveur import origin mismatch: {observed.get('file')}")
    python_expected = manifest["environment"]["python"]
    if observed.get("version") != python_expected["solveur_version"]:
        raise LocalVVError("solveur source version mismatch")
    if observed.get("distribution") != python_expected.get("distribution_version"):
        raise LocalVVError("installed qf-solver distribution does not match the manifest")
    for package_name in ("numpy", "scipy"):
        expected_version = manifest["environment"]["packages"].get(package_name)
        if expected_version is not None and observed.get(package_name) != expected_version:
            raise LocalVVError(f"{package_name} import version does not match the manifest")
    return {
        "solveur_file": observed["file"],
        "solveur_version": observed["version"],
        "installed_distribution_version": observed["distribution"],
        "python_executable": observed["python"],
        "numpy_version": observed["numpy"],
        "scipy_version": observed["scipy"],
        "native_libraries": observed["native_libraries"],
    }


def validate_owner_decision(
    manifest: dict[str, Any],
    case: dict[str, Any],
    decision: dict[str, Any],
    manifest_sha256: str,
) -> list[str]:
    """Check the decision record's bindings, not the real-world identity of its author.

    QUALIFICATION_LOCAL_VV is explicitly non-attested. Authenticity remains an
    Owner/operator process requirement and is not proven by this JSON file.
    """
    errors: list[str] = []
    if decision.get("schema") != DECISION_SCHEMA:
        errors.append("unsupported Owner execution-decision schema")
    if decision.get("decision_status") != "APPROVED_FOR_EXECUTION":
        errors.append("separate Owner execution decision is not APPROVED_FOR_EXECUTION")
    if decision.get("campaign_id") != manifest.get("campaign_id"):
        errors.append("Owner decision campaign_id mismatch")
    if decision.get("manifest_sha256") != manifest_sha256:
        errors.append("Owner decision does not bind the exact manifest SHA-256")
    if decision.get("case_id") != case.get("case_id") or decision.get("nodeid") != case.get("nodeid"):
        errors.append("Owner decision does not bind the selected case and exact nodeid")
    if decision.get("oracle_id") != case.get("oracle_id"):
        errors.append("Owner decision does not bind the case oracle")
    if decision.get("acceptance_ref") != case.get("acceptance_ref"):
        errors.append("Owner decision does not bind the case acceptance criteria")
    for key in ("science", "runner", "tests"):
        authorized = decision.get(f"{key}_identity")
        expected = manifest.get("identities", {}).get(key, {})
        if not isinstance(authorized, dict) or any(
            authorized.get(field) != expected.get(field) for field in ("commit", "tree")
        ):
            errors.append(f"Owner decision {key} identity mismatch")
    if decision.get("python_executable") != manifest.get("environment", {}).get("python", {}).get("executable"):
        errors.append("Owner decision Python executable mismatch")
    if decision.get("evidence_root") != manifest.get("evidence_root"):
        errors.append("Owner decision evidence root mismatch")
    if decision.get("max_attempts") != 1 or decision.get("attempt_number") != 1:
        errors.append("Owner decision must authorize exactly one attempt")
    for field in ("timeout_seconds", "output_limit_bytes"):
        if decision.get(field) != case.get(field):
            errors.append(f"Owner decision {field} mismatch")
    if not isinstance(decision.get("decision_id"), str) or not decision["decision_id"].strip():
        errors.append("Owner decision_id is required")
    if not isinstance(decision.get("approved_by"), str) or not decision["approved_by"].strip():
        errors.append("Owner identity is required")
    if not isinstance(decision.get("approved_at_utc"), str) or not decision["approved_at_utc"].endswith("Z"):
        errors.append("approved_at_utc must be an explicit UTC timestamp ending in Z")
    valid_until = decision.get("valid_until_utc")
    if not isinstance(valid_until, str) or not valid_until.endswith("Z"):
        errors.append("valid_until_utc must be an explicit UTC timestamp ending in Z")
    else:
        try:
            expires_at = datetime.fromisoformat(valid_until.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) >= expires_at:
                errors.append("Owner execution decision has expired")
        except ValueError:
            errors.append("valid_until_utc is not a valid ISO-8601 UTC timestamp")
    approved_at = decision.get("approved_at_utc")
    if isinstance(approved_at, str) and approved_at.endswith("Z"):
        try:
            if datetime.fromisoformat(approved_at.replace("Z", "+00:00")) > datetime.now(timezone.utc):
                errors.append("Owner execution decision approval time is in the future")
        except ValueError:
            errors.append("approved_at_utc is not a valid ISO-8601 UTC timestamp")
    return errors
