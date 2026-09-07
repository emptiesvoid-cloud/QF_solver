"""Small, reusable WP13 campaign helpers built on existing evidence conventions."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from solveur.io.manifest import sha256


CONTRACT_FIELDS = (
    "scope",
    "oracle",
    "tolerances",
    "required_metrics",
    "replay_count",
    "owner_gate",
    "abort_criteria",
    "claim_limitations",
    "source_sha",
    "environment",
)


def canonical_json(value: Any) -> str:
    """Serialize structured evidence deterministically for replay/digest checks."""

    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def payload_digest(value: Any) -> str:
    """Return a SHA-256 digest for a structured payload."""

    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def validate_vnv_contract(contract: Mapping[str, Any]) -> list[str]:
    """Validate a concrete pre-declared WP13 contract without executing it."""

    errors: list[str] = []
    for field in CONTRACT_FIELDS:
        if field not in contract:
            errors.append(f"missing contract field: {field}")
    scope = contract.get("scope")
    if not isinstance(scope, Mapping) or not scope.get("capability") or not scope.get("analysis"):
        errors.append("scope must declare capability and analysis")
    oracle = contract.get("oracle")
    if not isinstance(oracle, Mapping) or not oracle.get("reference"):
        errors.append("oracle must declare a reference")
    tolerances = contract.get("tolerances")
    if not isinstance(tolerances, Mapping) or tolerances.get("predeclared") is not True:
        errors.append("tolerances.predeclared must be true")
    elif not isinstance(tolerances.get("gates"), list) or not tolerances["gates"]:
        errors.append("tolerances.gates must be non-empty")
    metrics = contract.get("required_metrics")
    if not isinstance(metrics, list) or not metrics:
        errors.append("required_metrics must be non-empty")
    replay_count = contract.get("replay_count")
    if isinstance(replay_count, bool) or not isinstance(replay_count, int) or replay_count < 2:
        errors.append("replay_count must be an integer >= 2")
    for field in ("abort_criteria", "claim_limitations"):
        if not isinstance(contract.get(field), list) or not contract[field]:
            errors.append(f"{field} must be non-empty")
    source_sha = contract.get("source_sha")
    if not isinstance(source_sha, str) or len(source_sha) != 40:
        errors.append("source_sha must be a 40-character Git SHA")
    environment = contract.get("environment")
    if not isinstance(environment, Mapping) or not environment:
        errors.append("environment must be captured")
    return errors


def build_evidence_pack(
    contract: Mapping[str, Any],
    *,
    source: Mapping[str, Any],
    environment: Mapping[str, Any],
    inputs: list[Mapping[str, Any]],
    commands: list[str],
    outputs: list[Mapping[str, Any]],
    metrics: Mapping[str, Any],
    replays: list[Mapping[str, Any]],
    owner_decision: Mapping[str, Any] | None = None,
    status: str = "PENDING",
) -> dict[str, Any]:
    """Build the common evidence envelope; no solver execution is performed."""

    errors = validate_vnv_contract(contract)
    if errors:
        raise ValueError("Invalid WP13 contract: " + "; ".join(errors))
    return {
        "schema_version": 1,
        "contract_id": contract.get("contract_id", ""),
        "status": status,
        "source": dict(source),
        "environment": dict(environment),
        "inputs": [dict(item) for item in inputs],
        "commands": list(commands),
        "outputs": [dict(item) for item in outputs],
        "metrics": dict(metrics),
        "replays": [dict(item) for item in replays],
        "digests": {
            "contract": payload_digest(contract),
            "inputs": payload_digest(inputs),
            "outputs": payload_digest(outputs),
            "metrics": payload_digest(metrics),
        },
        "owner_decision": dict(owner_decision or {"status": "PENDING"}),
    }


def compare_replays(first: Mapping[str, Any], second: Mapping[str, Any]) -> dict[str, Any]:
    """Compare two serialized replay payloads without ignoring physical differences."""

    differences = sorted(
        key for key in set(first).union(second) if canonical_json(first.get(key)) != canonical_json(second.get(key))
    )
    return {
        "status": "PASS" if not differences else "FAIL",
        "equal": not differences,
        "differences": differences,
        "first_digest": payload_digest(first),
        "second_digest": payload_digest(second),
    }


def evaluate_tolerance(value: float, *, operator: str, limit: float, tolerance_id: str) -> dict[str, Any]:
    """Evaluate one already-declared scalar gate."""

    if operator == "<=":
        passed = value <= limit
    elif operator == "<":
        passed = value < limit
    elif operator == ">=":
        passed = value >= limit
    elif operator == ">":
        passed = value > limit
    else:
        raise ValueError(f"Unsupported tolerance operator: {operator}")
    return {
        "tolerance_id": tolerance_id,
        "value": float(value),
        "operator": operator,
        "limit": float(limit),
        "status": "PASS" if passed else "FAIL",
    }


def file_digest_entry(path: str | Path, *, role: str, root: str | Path) -> dict[str, Any]:
    """Create an existing-manifest-compatible artifact entry."""

    candidate = Path(path).resolve()
    base = Path(root).resolve()
    return {
        "path": candidate.relative_to(base).as_posix(),
        "role": role,
        "size_bytes": candidate.stat().st_size,
        "sha256": sha256(candidate),
    }
