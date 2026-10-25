"""Manifest, identity, and authorization checks for the WP12 runner.

This module deliberately does not import QF Solver.  Execution authorization is
not available in WP12-R because the repository has no independently trusted
Owner key store or hard process sandbox configured.
"""

from __future__ import annotations

from dataclasses import dataclass
import base64
import binascii
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
from typing import Any, Mapping, Sequence


PREPARED_SCHEMA = "qf-solver-wp12-prepared-manifest-v1"
EXECUTION_SCHEMA = "qf-solver-wp12-execution-manifest-v1"
OWNER_DECISION_SCHEMA = "qf-solver-wp12-owner-decision-v1"
REPOSITORY = "emptiesvoid-cloud/QF_solver"
TARGET_BRANCH = "emptiesvoids-cloud/0.2.12"
OWNER_TRUST_CONFIGURED = False
REAL_EXECUTION_ENABLED = False

_HEX40 = re.compile(r"^[a-f0-9]{40}$")
_HEX64 = re.compile(r"^[a-f0-9]{64}$")
_CAMPAIGN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_NODEID = re.compile(
    r"^tests/(?:unit|integration|verification)/[A-Za-z0-9_./-]+\.py::"
    r"[A-Za-z_][A-Za-z0-9_]*(?:::[A-Za-z_][A-Za-z0-9_]*)?"
    r"(?:\[[^\]\r\n]+\])?$"
)


class ContractError(ValueError):
    """An input does not satisfy the runner's structural contract."""


@dataclass(frozen=True)
class ManifestAssessment:
    manifest_sha256: str
    campaign_id: str | None
    structural_errors: tuple[str, ...]
    execution_blockers: tuple[str, ...]

    @property
    def structurally_valid(self) -> bool:
        return not self.structural_errors

    @property
    def execution_eligible(self) -> bool:
        return self.structurally_valid and not self.execution_blockers


@dataclass(frozen=True)
class GitSnapshot:
    root: Path
    branch: str
    commit: str
    tree: str
    clean: bool
    status_porcelain: str


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> tuple[dict[str, Any], str]:
    if path.is_symlink():
        raise ContractError(f"refusing symlink input: {path}")
    raw = path.read_bytes()
    try:
        payload = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=lambda value: (_ for _ in ()).throw(ContractError(f"invalid JSON constant: {value}")),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"invalid UTF-8 JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ContractError("top-level JSON value must be an object")
    return payload, sha256_bytes(raw)


def is_exact_nodeid(value: Any) -> bool:
    return isinstance(value, str) and _NODEID.fullmatch(value) is not None and "*" not in value


def safe_repo_relative_path(value: Any) -> bool:
    if (
        not isinstance(value, str)
        or not value
        or "\\" in value
        or ":" in value
        or any(ord(character) < 32 for character in value)
    ):
        return False
    return not value.startswith("/") and all(part not in {"", ".", ".."} for part in value.split("/"))


def _has_symlink_component(root: Path, target: Path) -> bool:
    try:
        relative = target.relative_to(root)
    except ValueError:
        return True
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink() or bool(getattr(current, "is_junction", lambda: False)()):
            return True
    return False


def _contains_unresolved(value: Any) -> bool:
    if isinstance(value, str):
        markers = (
            "PROPOSED — OWNER_APPROVAL_REQUIRED",
            "Required at freeze",
            "Compute for extracted bytes",
            "FUTURE_WP12_RUNNER_NOT_IMPLEMENTED",
            "<one exact nodeid>",
        )
        return any(marker in value for marker in markers)
    if isinstance(value, Mapping):
        return any(_contains_unresolved(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_unresolved(item) for item in value)
    return False


def _validate_prepared_structure(document: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "schema",
        "campaign_id",
        "status",
        "mode",
        "numerical_execution_performed",
        "wp12_status",
        "authorization",
        "repository",
        "target",
        "scope",
        "source_and_test_identity",
        "fixtures",
        "tests",
        "oracles_and_acceptance",
        "environment",
        "resource_limits",
        "attempt_policy",
        "evidence",
        "execution_status_label",
        "preparation_status_label",
        "wp12_status_label",
    }
    missing = sorted(required.difference(document))
    if missing:
        errors.append("missing top-level fields: " + ", ".join(missing))
    if document.get("schema") != PREPARED_SCHEMA:
        errors.append("unsupported manifest schema")
    if document.get("repository") != REPOSITORY:
        errors.append("repository identity mismatch")
    campaign_id = document.get("campaign_id")
    if not isinstance(campaign_id, str) or not _CAMPAIGN_ID.fullmatch(campaign_id):
        errors.append("invalid campaign_id")
    if document.get("status") != "PREPARED_NOT_AUTHORIZED":
        errors.append("WP12-0 manifest status must remain PREPARED_NOT_AUTHORIZED")
    if document.get("mode") != "PREPARATION_ONLY":
        errors.append("WP12-0 manifest must remain PREPARATION_ONLY")
    if document.get("numerical_execution_performed") is not False:
        errors.append("manifest must state numerical_execution_performed=false")
    if document.get("wp12_status") != "OPEN":
        errors.append("manifest must preserve WP12=OPEN")
    if document.get("execution_status_label") != "NUMERICAL_EXECUTION_NOT_PERFORMED":
        errors.append("manifest execution status label is invalid")
    if document.get("preparation_status_label") != "PREPARATION_ONLY":
        errors.append("manifest preparation status label is invalid")
    if document.get("wp12_status_label") != "WP12_STATUS=OPEN":
        errors.append("manifest WP12 status label is invalid")

    target = document.get("target")
    if not isinstance(target, Mapping):
        errors.append("target must be an object")
    else:
        if target.get("branch") != TARGET_BRANCH:
            errors.append("target branch mismatch")
        if not isinstance(target.get("commit"), str) or not _HEX40.fullmatch(target["commit"]):
            errors.append("target commit must be a full Git object ID")
        if not isinstance(target.get("git_tree"), str) or not _HEX40.fullmatch(target["git_tree"]):
            errors.append("target Git tree must be a full Git object ID")
        if target.get("worktree_must_be_clean") is not True:
            errors.append("target must require a clean worktree")

    tests = document.get("tests")
    nodeids = tests.get("exact_nodeids") if isinstance(tests, Mapping) else None
    if not isinstance(nodeids, list) or not nodeids:
        errors.append("tests.exact_nodeids must be a non-empty list")
    else:
        if all(isinstance(nodeid, str) for nodeid in nodeids) and len(nodeids) != len(set(nodeids)):
            errors.append("tests.exact_nodeids must be unique")
        for nodeid in nodeids:
            if not is_exact_nodeid(nodeid):
                errors.append(f"invalid or broad pytest selector: {nodeid!r}")

    source_identity = document.get("source_and_test_identity")
    if not isinstance(source_identity, Mapping):
        errors.append("source_and_test_identity must be an object")
    else:
        for list_name in ("tracked_source_files", "tracked_test_files"):
            paths = source_identity.get(list_name)
            if not isinstance(paths, list) or not paths:
                errors.append(f"source_and_test_identity.{list_name} must be non-empty")
                continue
            for path in paths:
                if not safe_repo_relative_path(path):
                    errors.append(f"unsafe repository-relative path: {path!r}")
        blob_oids = source_identity.get("git_blob_oids")
        if not isinstance(blob_oids, Mapping):
            errors.append("source_and_test_identity.git_blob_oids must be an object")
        else:
            for path, oid in blob_oids.items():
                if not safe_repo_relative_path(path) or not isinstance(oid, str) or not _HEX40.fullmatch(oid):
                    errors.append(f"invalid Git blob identity for {path!r}")

    fixtures = document.get("fixtures")
    entries = fixtures.get("entries") if isinstance(fixtures, Mapping) else None
    if not isinstance(entries, list):
        errors.append("fixtures.entries must be a list")
    else:
        for entry in entries:
            if not isinstance(entry, Mapping):
                errors.append("fixture entries must be objects")
                continue
            path = entry.get("path")
            if path is not None and not safe_repo_relative_path(path):
                errors.append(f"unsafe fixture path: {path!r}")

    if not isinstance(document.get("authorization"), Mapping):
        errors.append("authorization must be an object")
    if not isinstance(document.get("resource_limits"), Mapping):
        errors.append("resource_limits must be an object")
    if not isinstance(document.get("environment"), Mapping):
        errors.append("environment must be an object")
    if not isinstance(document.get("attempt_policy"), Mapping):
        errors.append("attempt_policy must be an object")
    return errors


def assess_prepared_manifest(document: Mapping[str, Any], manifest_sha256: str) -> ManifestAssessment:
    errors = _validate_prepared_structure(document)
    blockers = [
        "MANIFEST_PREPARED_NOT_AUTHORIZED",
        "SEPARATE_OWNER_DECISION_REQUIRED",
        "OWNER_TRUST_ROOT_NOT_CONFIGURED",
        "REAL_EXECUTION_DISABLED_IN_WP12_R",
    ]
    if _contains_unresolved(document):
        blockers.append("MANIFEST_HAS_UNRESOLVED_PROPOSED_VALUES")
    authorization = document.get("authorization")
    if isinstance(authorization, Mapping) and authorization.get("execution_authorized") is not False:
        blockers.append("MANIFEST_AUTHORIZATION_FIELD_IS_NOT_FALSE")
    return ManifestAssessment(
        manifest_sha256=manifest_sha256,
        campaign_id=document.get("campaign_id") if isinstance(document.get("campaign_id"), str) else None,
        structural_errors=tuple(errors),
        execution_blockers=tuple(dict.fromkeys(blockers)),
    )


def assess_execution_manifest(document: Mapping[str, Any], manifest_sha256: str) -> ManifestAssessment:
    errors: list[str] = []
    required = {
        "schema",
        "campaign_id",
        "unit_id",
        "status",
        "repository",
        "target",
        "scope",
        "code_identity",
        "tests",
        "fixtures",
        "environment",
        "resource_limits",
        "attempt_policy",
        "destination",
        "oracle",
        "prepared_at",
        "authorization_reference",
    }
    missing = sorted(required.difference(document))
    if missing:
        errors.append("missing execution-manifest fields: " + ", ".join(missing))
    if document.get("schema") != EXECUTION_SCHEMA:
        errors.append("unsupported execution-manifest schema")
    if document.get("status") != "FROZEN_NOT_AUTHORIZED":
        errors.append("frozen execution manifest must start FROZEN_NOT_AUTHORIZED")
    if document.get("repository") != REPOSITORY:
        errors.append("repository identity mismatch")
    for key in ("campaign_id", "unit_id"):
        value = document.get(key)
        if not isinstance(value, str) or not _CAMPAIGN_ID.fullmatch(value):
            errors.append(f"invalid {key}")
    target = document.get("target")
    if not isinstance(target, Mapping) or target.get("branch") != TARGET_BRANCH:
        errors.append("invalid target branch")
    elif not all(isinstance(target.get(key), str) and _HEX40.fullmatch(target[key]) for key in ("commit", "git_tree")):
        errors.append("target commit/tree must be full Git object IDs")
    if not isinstance(target, Mapping) or target.get("require_clean_checkout") is not True:
        errors.append("target must require a clean checkout")
    if not isinstance(target, Mapping) or not isinstance(target.get("allow_detached_at_exact_commit"), bool):
        errors.append("target must explicitly state detached-checkout policy")
    scope = document.get("scope")
    if not isinstance(scope, Mapping) or scope.get("operation") != "EXECUTE_ONE_TEST_NODE":
        errors.append("scope must authorize only one exact test node")
    tests = document.get("tests")
    if not isinstance(tests, Mapping):
        errors.append("tests must be an object")
    else:
        nodeid = tests.get("nodeid")
        argv = tests.get("argv")
        if not is_exact_nodeid(nodeid):
            errors.append("execution manifest must contain one exact nodeid")
        if (
            not isinstance(argv, list)
            or len(argv) != 5
            or not all(isinstance(argument, str) and argument for argument in argv)
            or argv[1:4] != ["-m", "pytest", "-q"]
            or argv[4] != nodeid
        ):
            errors.append("argv must be the exact one-node pytest command; no broad selectors or extra flags")
        if isinstance(argv, list) and argv and not isinstance(argv[0], str):
            errors.append("argv[0] must name the approved Python executable")
    code_identity = document.get("code_identity")
    if not isinstance(code_identity, Mapping):
        errors.append("code_identity must be an object")
    else:
        for field in ("source_files_sha256", "test_files_sha256", "fixture_files_sha256"):
            inventory = code_identity.get(field)
            if not isinstance(inventory, Mapping) or not inventory:
                errors.append(f"code_identity.{field} must be a non-empty SHA-256 map")
            else:
                for path, digest in inventory.items():
                    if not safe_repo_relative_path(path) or not isinstance(digest, str) or not _HEX64.fullmatch(digest):
                        errors.append(f"invalid file hash identity in {field}: {path!r}")
    environment = document.get("environment")
    if not isinstance(environment, Mapping):
        errors.append("environment must be an object")
    elif _contains_unresolved(environment):
        errors.append("environment contains unresolved proposed values")
    resources = document.get("resource_limits")
    if not isinstance(resources, Mapping) or _contains_unresolved(resources):
        errors.append("resource limits are absent or unresolved")
    elif any(
        isinstance(value, bool) or not isinstance(value, int) or value < 1
        for key, value in resources.items()
        if key != "enforcement"
    ):
        errors.append("resource limits must be positive integers")
    attempts = document.get("attempt_policy")
    if (
        not isinstance(attempts, Mapping)
        or attempts.get("maximum_attempts") != 1
        or attempts.get("automatic_retry") is not False
    ):
        errors.append("execution unit must be one-shot with automatic retries disabled")
    destination = document.get("destination")
    if not isinstance(destination, str) or not destination.startswith("qualification/0_2_12/wp12_evidence/"):
        errors.append("destination must be under the WP12 evidence root")
    if not safe_repo_relative_path(destination):
        errors.append("destination is unsafe or traversal-bearing")
    blockers = [
        "SEPARATE_OWNER_DECISION_REQUIRED",
        "OWNER_TRUST_ROOT_NOT_CONFIGURED",
        "REAL_EXECUTION_DISABLED_IN_WP12_R",
    ]
    if _contains_unresolved(document):
        blockers.append("MANIFEST_HAS_UNRESOLVED_PROPOSED_VALUES")
    return ManifestAssessment(
        manifest_sha256=manifest_sha256,
        campaign_id=document.get("campaign_id") if isinstance(document.get("campaign_id"), str) else None,
        structural_errors=tuple(errors),
        execution_blockers=tuple(blockers),
    )


def assess_manifest(document: Mapping[str, Any], manifest_sha256: str) -> ManifestAssessment:
    if document.get("schema") == PREPARED_SCHEMA:
        return assess_prepared_manifest(document, manifest_sha256)
    if document.get("schema") == EXECUTION_SCHEMA:
        return assess_execution_manifest(document, manifest_sha256)
    return ManifestAssessment(
        manifest_sha256=manifest_sha256,
        campaign_id=None,
        structural_errors=("unsupported manifest schema",),
        execution_blockers=("REAL_EXECUTION_DISABLED_IN_WP12_R",),
    )


def validate_manifest_schema(document: Mapping[str, Any]) -> tuple[str, ...]:
    """Validate against the checked-in JSON Schema without resolving remote refs."""
    schema_name = {
        PREPARED_SCHEMA: "wp12_prepared_manifest.schema.json",
        EXECUTION_SCHEMA: "wp12_execution_manifest.schema.json",
        OWNER_DECISION_SCHEMA: "wp12_owner_decision.schema.json",
    }.get(document.get("schema"))
    if schema_name is None:
        return ("unsupported manifest schema",)
    schema_path = Path(__file__).resolve().parents[2] / "qualification" / "0_2_12" / "wp12_preparation" / schema_name
    if not schema_path.is_file():
        return (f"schema file is missing: {schema_name}",)
    try:
        import jsonschema
    except ImportError as exc:
        return (f"schema validation unavailable: {type(exc).__name__}",)
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)
        validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
        errors = sorted(
            validator.iter_errors(dict(document)), key=lambda error: tuple(str(part) for part in error.absolute_path)
        )
    except (OSError, json.JSONDecodeError, jsonschema.SchemaError) as exc:
        return (f"schema validation unavailable: {type(exc).__name__}",)
    return tuple(
        f"schema violation at {'/'.join(str(part) for part in error.absolute_path) or '<root>'}: {error.message}"
        for error in errors
    )


def validate_owner_decision_structure(decision: Mapping[str, Any]) -> tuple[str, ...]:
    errors = list(validate_manifest_schema(decision))
    if decision.get("schema") != OWNER_DECISION_SCHEMA:
        errors.append("unsupported Owner decision schema")
    if decision.get("status") != "APPROVED":
        errors.append("Owner decision status must be APPROVED")
    for key in ("decision_id", "campaign_id"):
        value = decision.get(key)
        if not isinstance(value, str) or not _CAMPAIGN_ID.fullmatch(value):
            errors.append(f"invalid {key}")
    if not isinstance(decision.get("manifest_sha256"), str) or not _HEX64.fullmatch(decision["manifest_sha256"]):
        errors.append("manifest_sha256 must be a full SHA-256")
    target = decision.get("target")
    if not isinstance(target, Mapping) or target.get("branch") != TARGET_BRANCH:
        errors.append("invalid Owner decision target")
    elif not all(isinstance(target.get(key), str) and _HEX40.fullmatch(target[key]) for key in ("commit", "git_tree")):
        errors.append("Owner decision commit/tree must be full Git object IDs")
    nodeids = decision.get("nodeids")
    if not isinstance(nodeids, list) or not nodeids or any(not is_exact_nodeid(nodeid) for nodeid in nodeids):
        errors.append("Owner decision must list exact nodeids")
    elif len(nodeids) != len(set(nodeids)):
        errors.append("Owner decision nodeids must be unique")
    if decision.get("operations") != ["EXECUTE_ONE_TEST_NODE"]:
        errors.append("Owner decision operation must be the exact single-test operation")
    attempts = decision.get("maximum_attempts")
    if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts < 1:
        errors.append("maximum_attempts must be a positive integer")
    destination = decision.get("destination")
    if not safe_repo_relative_path(destination):
        errors.append("Owner decision destination must be repository-relative and traversal-free")
    signature = decision.get("signature")
    if not isinstance(signature, Mapping):
        errors.append("signature envelope is required")
    else:
        for key in ("key_id", "signature_base64"):
            if not isinstance(signature.get(key), str) or not signature[key]:
                errors.append(f"signature.{key} is required")
        encoded_signature = signature.get("signature_base64")
        if isinstance(encoded_signature, str):
            try:
                if len(base64.b64decode(encoded_signature, validate=True)) != 64:
                    errors.append("signature.signature_base64 must encode a 64-byte Ed25519 signature")
            except (binascii.Error, ValueError):
                errors.append("signature.signature_base64 is not valid base64")
        for key in ("public_key_sha256", "payload_sha256"):
            if not isinstance(signature.get(key), str) or not _HEX64.fullmatch(signature[key]):
                errors.append(f"signature.{key} must be a full SHA-256")
        if signature.get("algorithm") != "ed25519":
            errors.append("signature algorithm must be ed25519")
    owner = decision.get("owner")
    if not isinstance(owner, Mapping) or not owner.get("principal") or not owner.get("display_name"):
        errors.append("owner principal and display_name are required")
    environment = decision.get("environment")
    if not isinstance(environment, Mapping):
        errors.append("environment must be an object")
    else:
        for key in ("platform", "python_version", "venv_executable_sha256"):
            if not isinstance(environment.get(key), str) or not environment[key]:
                errors.append(f"environment.{key} is required")
        if not isinstance(environment.get("packages"), Mapping) or not environment["packages"]:
            errors.append("environment.packages must bind package versions")
        for key in ("native_libraries", "thread_environment"):
            if not isinstance(environment.get(key), Mapping):
                errors.append(f"environment.{key} must be an object")
    decided = decision.get("decided_utc")
    if not isinstance(decided, str):
        errors.append("decided_utc must be an ISO-8601 timestamp")
    else:
        try:
            parsed = datetime.fromisoformat(decided.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                errors.append("decided_utc must include a timezone")
        except ValueError:
            errors.append("decided_utc must be an ISO-8601 timestamp")
    budgets = decision.get("budgets")
    budget_names = (
        "wall_seconds",
        "cpu_seconds",
        "memory_bytes",
        "process_count",
        "thread_count",
        "temporary_storage_bytes",
        "stdout_bytes",
        "stderr_bytes",
    )
    if not isinstance(budgets, Mapping):
        errors.append("budgets must be an object")
    else:
        for name in budget_names:
            value = budgets.get(name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                errors.append(f"budgets.{name} must be a positive integer")
    return tuple(errors)


def owner_decision_binding_errors(
    decision: Mapping[str, Any], manifest: Mapping[str, Any], manifest_sha256: str
) -> tuple[str, ...]:
    errors = list(validate_owner_decision_structure(decision))
    if decision.get("campaign_id") != manifest.get("campaign_id"):
        errors.append("Owner decision campaign_id does not match manifest")
    if decision.get("manifest_sha256") != manifest_sha256:
        errors.append("Owner decision does not bind the exact manifest SHA-256")
    target = decision.get("target")
    manifest_target = manifest.get("target")
    if isinstance(target, Mapping) and isinstance(manifest_target, Mapping):
        for key, manifest_key in (("branch", "branch"), ("commit", "commit"), ("git_tree", "git_tree")):
            if target.get(key) != manifest_target.get(manifest_key):
                errors.append(f"Owner decision target {key} does not match manifest")
    manifest_tests = manifest.get("tests")
    if isinstance(manifest_tests, Mapping) and isinstance(manifest_tests.get("exact_nodeids"), list):
        manifest_nodeids = manifest_tests["exact_nodeids"]
    elif isinstance(manifest_tests, Mapping) and isinstance(manifest_tests.get("nodeid"), str):
        manifest_nodeids = [manifest_tests["nodeid"]]
    else:
        manifest_nodeids = None
    if decision.get("nodeids") != manifest_nodeids:
        errors.append("Owner decision nodeids do not exactly match manifest")
    if manifest.get("schema") == EXECUTION_SCHEMA:
        if decision.get("environment") != manifest.get("environment"):
            errors.append("Owner decision environment does not exactly match manifest")
        manifest_resources = manifest.get("resource_limits")
        decision_budgets = decision.get("budgets")
        if isinstance(manifest_resources, Mapping) and isinstance(decision_budgets, Mapping):
            for key in (
                "wall_seconds",
                "cpu_seconds",
                "memory_bytes",
                "process_count",
                "thread_count",
                "temporary_storage_bytes",
                "stdout_bytes",
                "stderr_bytes",
            ):
                if manifest_resources.get(key) != decision_budgets.get(key):
                    errors.append(f"Owner decision budget {key} does not exactly match manifest")
        if decision.get("destination") != manifest.get("destination"):
            errors.append("Owner decision destination does not exactly match manifest")
        attempts = manifest.get("attempt_policy")
        if isinstance(attempts, Mapping) and decision.get("maximum_attempts") != attempts.get("maximum_attempts"):
            errors.append("Owner decision attempt limit does not exactly match manifest")
    # A structurally valid JSON signature is not authenticated without an
    # independently provisioned trust root; never infer authority from status.
    return tuple(dict.fromkeys(errors))


def inspect_git(root: Path) -> GitSnapshot:
    canonical = root.resolve(strict=True)

    def git(*args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=canonical,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            raise ContractError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
        return result.stdout.strip()

    top = Path(git("rev-parse", "--show-toplevel")).resolve(strict=True)
    if top != canonical:
        raise ContractError("provided root is not the canonical Git root")
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    commit = git("rev-parse", "HEAD")
    tree = git("rev-parse", "HEAD^{tree}")
    status = git("status", "--porcelain=v1", "--untracked-files=all")
    return GitSnapshot(
        root=canonical, branch=branch, commit=commit, tree=tree, clean=not status, status_porcelain=status
    )


def git_identity_issues(target: Mapping[str, Any], snapshot: GitSnapshot) -> tuple[str, ...]:
    issues: list[str] = []
    if snapshot.branch != target.get("branch"):
        issues.append("GIT_BRANCH_MISMATCH")
    if snapshot.commit != target.get("commit"):
        issues.append("GIT_COMMIT_MISMATCH")
    if snapshot.tree != target.get("git_tree"):
        issues.append("GIT_TREE_MISMATCH")
    if target.get("worktree_must_be_clean") is True and not snapshot.clean:
        issues.append("GIT_CHECKOUT_DIRTY")
    return tuple(issues)


def verify_file_hashes(root: Path, expected: Mapping[str, str]) -> tuple[str, ...]:
    errors: list[str] = []
    canonical = root.resolve(strict=True)
    for relative, digest in expected.items():
        if not safe_repo_relative_path(relative):
            errors.append(f"UNSAFE_FILE_PATH:{relative}")
            continue
        path = canonical.joinpath(*PurePosixPath(relative).parts)
        try:
            path.resolve(strict=True).relative_to(canonical)
        except (FileNotFoundError, ValueError):
            errors.append(f"MISSING_OR_ESCAPING_FILE:{relative}")
            continue
        if _has_symlink_component(canonical, path) or not path.is_file():
            errors.append(f"NOT_A_REGULAR_FILE:{relative}")
            continue
        if not isinstance(digest, str) or not _HEX64.fullmatch(digest):
            errors.append(f"INVALID_EXPECTED_SHA256:{relative}")
            continue
        if sha256_file(path) != digest:
            errors.append(f"SHA256_MISMATCH:{relative}")
    return tuple(errors)


def verify_manifest_input_identities(
    root: Path, manifest: Mapping[str, Any]
) -> tuple[tuple[str, ...], tuple[dict[str, str], ...]]:
    """Verify recorded Git blob and byte identities without importing project code."""
    errors: list[str] = []
    records: list[dict[str, str]] = []
    target = manifest.get("target")
    target_commit = target.get("commit") if isinstance(target, Mapping) else None
    identity = manifest.get("source_and_test_identity")
    if isinstance(identity, Mapping):
        blob_map = identity.get("git_blob_oids")
        tracked_paths: set[str] = set()
        for field in ("tracked_source_files", "tracked_test_files"):
            values = identity.get(field)
            if isinstance(values, list):
                tracked_paths.update(path for path in values if isinstance(path, str))
        if isinstance(blob_map, Mapping):
            for relative in sorted(tracked_paths.difference(blob_map)):
                errors.append(f"BLOB_IDENTITY_INVENTORY_INCOMPLETE:{relative}")
    else:
        blob_map = None
        code_identity = manifest.get("code_identity")
        if isinstance(code_identity, Mapping):
            for inventory_name in ("source_files_sha256", "test_files_sha256", "fixture_files_sha256"):
                inventory = code_identity.get(inventory_name)
                if isinstance(inventory, Mapping):
                    errors.extend(verify_file_hashes(root, inventory))
                    records.extend(
                        {
                            "path": relative,
                            "expected_sha256": digest,
                            "identity_group": inventory_name,
                            "state": "HASH_CHECKED",
                        }
                        for relative, digest in sorted(inventory.items())
                    )
    if not isinstance(target_commit, str) or not _HEX40.fullmatch(target_commit):
        return ("TARGET_COMMIT_INVALID",), ()
    if isinstance(blob_map, Mapping):
        for relative, expected_oid in sorted(blob_map.items()):
            if (
                not safe_repo_relative_path(relative)
                or not isinstance(expected_oid, str)
                or not _HEX40.fullmatch(expected_oid)
            ):
                errors.append(f"INVALID_BLOB_IDENTITY:{relative}")
                continue
            result = subprocess.run(
                ["git", "rev-parse", "--verify", f"{target_commit}:{relative}"],
                cwd=root,
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            target_oid = result.stdout.strip() if result.returncode == 0 else ""
            if target_oid != expected_oid:
                errors.append(f"TARGET_BLOB_MISMATCH:{relative}")
            file_path = root.joinpath(*PurePosixPath(relative).parts)
            if _has_symlink_component(root, file_path) or not file_path.is_file():
                errors.append(f"WORKTREE_FILE_MISSING_OR_UNSAFE:{relative}")
                worktree_sha = ""
            else:
                worktree_sha = sha256_file(file_path)
                blob_result = subprocess.run(
                    ["git", "hash-object", "--", relative],
                    cwd=root,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if blob_result.returncode != 0 or blob_result.stdout.strip() != expected_oid:
                    errors.append(f"WORKTREE_BLOB_MISMATCH:{relative}")
            records.append(
                {
                    "path": relative,
                    "expected_git_blob_oid": expected_oid,
                    "target_git_blob_oid": target_oid,
                    "worktree_sha256": worktree_sha,
                }
            )

    fixtures = manifest.get("fixtures")
    entries = fixtures.get("entries") if isinstance(fixtures, Mapping) else None
    if entries is None and isinstance(fixtures, Mapping):
        overlays = fixtures.get("overlays")
        if isinstance(overlays, list):
            entries = [
                {
                    "id": f"overlay-{index + 1}",
                    "path": item.get("path") if isinstance(item, Mapping) else None,
                    "source_commit": item.get("source_commit") if isinstance(item, Mapping) else None,
                    "git_blob_oid": item.get("git_blob_oid") if isinstance(item, Mapping) else None,
                    "byte_sha256": item.get("sha256") if isinstance(item, Mapping) else None,
                }
                for index, item in enumerate(overlays)
            ]
    if isinstance(entries, list):
        for index, entry in enumerate(entries):
            if not isinstance(entry, Mapping):
                errors.append(f"FIXTURE_ENTRY_INVALID:{index}")
                continue
            relative = entry.get("path")
            expected_oid = entry.get("git_blob_oid")
            source_commit = entry.get("source_commit") or target_commit
            expected_sha256 = entry.get("byte_sha256")
            if relative is None:
                fixture_id = str(entry.get("id", index))
                if expected_oid is None:
                    records.append({"fixture": fixture_id, "state": "INLINE_OR_UNFROZEN"})
                elif isinstance(blob_map, Mapping):
                    matching_paths = [path for path, oid in blob_map.items() if oid == expected_oid]
                    if len(matching_paths) == 1:
                        records.append(
                            {
                                "fixture": fixture_id,
                                "path": matching_paths[0],
                                "source_git_blob_oid": str(expected_oid),
                                "state": "EMBEDDED_SOURCE_IDENTIFIED_BYTES_UNFROZEN",
                            }
                        )
                        if not isinstance(expected_sha256, str) or not _HEX64.fullmatch(expected_sha256):
                            errors.append(f"FIXTURE_BYTES_SHA256_UNRESOLVED:{fixture_id}")
                    else:
                        errors.append(f"FIXTURE_SOURCE_FILE_UNRESOLVED:{fixture_id}")
                else:
                    errors.append(f"FIXTURE_SOURCE_FILE_UNRESOLVED:{fixture_id}")
                continue
            if (
                not safe_repo_relative_path(relative)
                or not isinstance(expected_oid, str)
                or not _HEX40.fullmatch(expected_oid)
            ):
                errors.append(f"FIXTURE_IDENTITY_INVALID:{entry.get('id', index)}")
                continue
            if not isinstance(source_commit, str) or not _HEX40.fullmatch(source_commit):
                errors.append(f"FIXTURE_SOURCE_COMMIT_INVALID:{relative}")
                continue
            result = subprocess.run(
                ["git", "rev-parse", "--verify", f"{source_commit}:{relative}"],
                cwd=root,
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            source_oid = result.stdout.strip() if result.returncode == 0 else ""
            if source_oid != expected_oid:
                errors.append(f"FIXTURE_GIT_BLOB_MISMATCH:{relative}")
            file_path = root.joinpath(*PurePosixPath(relative).parts)
            is_overlay = source_commit != target_commit
            if is_overlay and not file_path.exists():
                records.append(
                    {
                        "fixture": str(entry.get("id", index)),
                        "path": relative,
                        "source_git_blob_oid": source_oid,
                        "state": "OVERLAY_IDENTIFIED_NOT_MATERIALIZED",
                    }
                )
                continue
            if _has_symlink_component(root, file_path) or not file_path.is_file():
                errors.append(f"FIXTURE_FILE_MISSING_OR_UNSAFE:{relative}")
                continue
            actual_sha256 = sha256_file(file_path)
            if (
                isinstance(expected_sha256, str)
                and _HEX64.fullmatch(expected_sha256)
                and actual_sha256 != expected_sha256
            ):
                errors.append(f"FIXTURE_SHA256_MISMATCH:{relative}")
            expected_test_sha = entry.get("expected_sha256_in_test")
            if (
                isinstance(expected_test_sha, str)
                and _HEX64.fullmatch(expected_test_sha)
                and actual_sha256 != expected_test_sha
            ):
                errors.append(f"FIXTURE_CONTRACT_DIGEST_MISMATCH:{relative}")
            records.append(
                {
                    "fixture": str(entry.get("id", index)),
                    "path": relative,
                    "source_git_blob_oid": source_oid,
                    "worktree_sha256": actual_sha256,
                    "state": "PRESENT",
                }
            )
    return tuple(errors), tuple(records)


def approved_nodeid(nodeid: str, exact_nodeids: Sequence[str]) -> bool:
    return is_exact_nodeid(nodeid) and nodeid in exact_nodeids


def approved_command(nodeid: str, argv: Sequence[str], execution_units: Sequence[Mapping[str, Any]]) -> bool:
    if not is_exact_nodeid(nodeid) or not argv or any(not isinstance(arg, str) for arg in argv):
        return False
    for unit in execution_units:
        if unit.get("nodeid") == nodeid and unit.get("argv") == list(argv):
            return True
    return False


def attempt_allowed(attempt_number: int, previous_count: int, maximum_attempts: int) -> bool:
    if any(
        isinstance(value, bool) or not isinstance(value, int)
        for value in (attempt_number, previous_count, maximum_attempts)
    ):
        return False
    return maximum_attempts >= 1 and attempt_number == previous_count + 1 and attempt_number <= maximum_attempts


def overlay_errors(
    declaration: Mapping[str, Any] | None, path: str, source_commit: str, blob_oid: str, data: bytes
) -> tuple[str, ...]:
    if declaration is None:
        return ("OVERLAY_NOT_DECLARED",)
    expected = {
        "path": path,
        "source_commit": source_commit,
        "git_blob_oid": blob_oid,
        "sha256": sha256_bytes(data),
    }
    errors = [f"OVERLAY_IDENTITY_MISMATCH:{key}" for key, value in expected.items() if declaration.get(key) != value]
    if not safe_repo_relative_path(path) or not _HEX40.fullmatch(source_commit) or not _HEX40.fullmatch(blob_oid):
        errors.append("OVERLAY_IDENTITY_MALFORMED")
    return tuple(errors)


def execution_gate_blockers(
    *,
    assessment: ManifestAssessment,
    manifest: Mapping[str, Any],
    supplied_manifest_sha256: str | None,
    owner_decision: Mapping[str, Any] | None,
    git_snapshot: GitSnapshot | None,
    nodeid: str | None,
    argv: Sequence[str] | None,
    previous_attempts: int,
    attempt_number: int,
    destination_exists: bool,
) -> tuple[str, ...]:
    blockers = list(assessment.execution_blockers)
    blockers.extend(validate_manifest_schema(manifest))
    blockers.extend(f"MANIFEST_STRUCTURAL_INVALID:{error}" for error in assessment.structural_errors)
    if supplied_manifest_sha256 != assessment.manifest_sha256:
        blockers.append("MANIFEST_SHA256_NOT_APPROVED")
    if owner_decision is None:
        blockers.append("OWNER_DECISION_ABSENT")
    else:
        blockers.extend(owner_decision_binding_errors(owner_decision, manifest, assessment.manifest_sha256))
        blockers.append("OWNER_SIGNATURE_UNVERIFIED_NO_TRUST_ROOT")
    target = manifest.get("target")
    if git_snapshot is None or not isinstance(target, Mapping):
        blockers.append("GIT_IDENTITY_UNAVAILABLE")
    else:
        blockers.extend(git_identity_issues(target, git_snapshot))
    tests = manifest.get("tests")
    if isinstance(tests, Mapping) and isinstance(tests.get("exact_nodeids"), list):
        nodeids = tests["exact_nodeids"]
    elif isinstance(tests, Mapping) and isinstance(tests.get("nodeid"), str):
        nodeids = [tests["nodeid"]]
    else:
        nodeids = []
    if nodeid is None or not approved_nodeid(nodeid, nodeids):
        blockers.append("NODEID_NOT_EXACTLY_APPROVED")
    if isinstance(tests, Mapping) and isinstance(tests.get("nodeid"), str):
        commands = [tests]
    else:
        commands = tests.get("execution_units", []) if isinstance(tests, Mapping) else []
    if argv is None or nodeid is None or not approved_command(nodeid, argv, commands):
        blockers.append("COMMAND_NOT_EXACTLY_APPROVED")
    attempt = manifest.get("attempt_policy")
    max_attempts = None
    if isinstance(attempt, Mapping):
        configured = attempt.get("maximum_attempts_per_unit", attempt.get("maximum_attempts"))
        if isinstance(configured, int) and not isinstance(configured, bool):
            max_attempts = configured
    if max_attempts is None or not attempt_allowed(attempt_number, previous_attempts, max_attempts):
        blockers.append("ATTEMPT_BUDGET_EXCEEDED_OR_UNCONFIGURED")
    if destination_exists:
        blockers.append("DESTINATION_ALREADY_EXISTS")
    blockers.append("REAL_EXECUTION_DISABLED_IN_WP12_R")
    return tuple(dict.fromkeys(blockers))
