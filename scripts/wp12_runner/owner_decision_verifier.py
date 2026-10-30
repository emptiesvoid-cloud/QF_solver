"""Authenticate one frozen Owner decision for the SYSTEM archive worker.

This verifier does not import QF Solver or run a scientific operation. The
archive worker launches it from a runner checkout protected by administrator
managed ACLs; the user-facing runner independently performs the same checks
before launching a test process.
"""

from __future__ import annotations

import argparse
import json
import hashlib
from pathlib import Path
import sys
from typing import Any, Mapping


def verify_authorized_decision(
    *,
    runner_root: Path,
    decision_path: Path,
    manifest_path: Path,
    campaign_id: str,
    decision_id: str,
    unit_id: str,
    run_id: str,
    manifest_sha256: str,
    nodeid: str,
    attempt_number: int,
    destination: str,
    scientific_identity: Mapping[str, str],
    runner_identity: Mapping[str, str],
    trusted_keys: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Verify the protected decision and exact manifest/attempt binding.

    ``trusted_keys`` exists for unit tests only. The command-line verifier never
    accepts a caller-supplied keyring and loads the machine-pinned trust store.
    """
    from scripts.wp12_runner.contracts import (
        OWNER_DECISION_SCHEMA,
        ContractError,
        load_json,
        owner_decision_binding_errors,
        validate_manifest_schema,
    )
    from scripts.wp12_runner.owner_trust import (
        load_machine_trust_store,
        verify_owner_decision,
    )

    errors: list[str] = []
    try:
        decision, decision_sha256 = load_json(decision_path)
        manifest, actual_manifest_sha256 = load_json(manifest_path)
        if actual_manifest_sha256 != manifest_sha256:
            errors.append("protected manifest SHA-256 differs from the requested identity")
        if campaign_id != manifest.get("campaign_id") or unit_id != manifest.get("unit_id"):
            errors.append("campaign or unit identity differs from the protected manifest")
        if decision_id != decision.get("decision_id"):
            errors.append("decision ID differs from the protected decision")
        manifest_errors = validate_manifest_schema(manifest)
        if manifest_errors:
            errors.extend(manifest_errors)
        if decision.get("schema") != OWNER_DECISION_SCHEMA:
            errors.append("protected worker requires the run-bound Owner decision schema v4")
        if manifest.get("scientific_identity") != dict(scientific_identity):
            errors.append("scientific Git identity differs from the protected manifest")
        if manifest.get("runner_identity") != dict(runner_identity):
            errors.append("runner Git identity differs from the protected manifest")
        if trusted_keys is None:
            trusted_keys, _trust_sha256 = load_machine_trust_store(
                runner_root,
                check_runner_permissions=False,
            )
        verification = verify_owner_decision(
            decision,
            trusted_keys=trusted_keys,
            manifest_sha256=manifest_sha256,
            expected_campaign_id=campaign_id,
            expected_scientific_identity=scientific_identity,
            expected_runner_identity=runner_identity,
        )
        errors.extend(verification.errors)
        errors.extend(owner_decision_binding_errors(decision, manifest, manifest_sha256))
        if decision.get("unit_id") != unit_id:
            errors.append("Owner decision unit ID differs from the reserved unit")
        if decision.get("run_id") != run_id:
            errors.append("Owner decision run ID differs from the reserved attempt")
        if destination.rsplit("/", 1)[-1] != run_id:
            errors.append("reserved run ID differs from the destination component")
        if decision.get("nodeids") != [nodeid]:
            errors.append("Owner decision does not authorize this exact single nodeid")
        if decision.get("attempt_number") != attempt_number or attempt_number != 1:
            errors.append("Owner decision does not authorize the exact first attempt")
        if decision.get("maximum_attempts") != 1:
            errors.append("Owner decision must authorize one attempt only")
        if decision.get("launch_confirmation") != "RUN_EXACT_APPROVED_UNIT":
            errors.append("Owner decision lacks exact-unit launch confirmation")
        if decision.get("destination") != destination or manifest.get("destination") != destination:
            errors.append("Owner decision or manifest destination differs from the reserved output")
        environment = manifest.get("environment")
        execution_context = manifest.get("execution_context")
        archive_context = execution_context.get("archive") if isinstance(execution_context, Mapping) else None
        if not isinstance(archive_context, Mapping) or archive_context.get("manifest_path") != str(
            manifest_path.resolve(strict=True)
        ):
            errors.append("manifest was not loaded from its frozen protected path")
        declared_python = environment.get("python_executable_path") if isinstance(environment, Mapping) else None
        context_python = execution_context.get("python_executable") if isinstance(execution_context, Mapping) else None
        actual_python = Path(sys.executable).resolve(strict=True)
        try:
            executable_sha256 = hashlib.sha256(actual_python.read_bytes()).hexdigest()
        except OSError as exc:
            errors.append(f"cannot hash the verifier interpreter: {type(exc).__name__}")
        else:
            if not isinstance(declared_python, str) or Path(declared_python).resolve(strict=True) != actual_python:
                errors.append("verifier interpreter path differs from the frozen manifest")
            if context_python != str(actual_python):
                errors.append("execution-context Python differs from the verifier interpreter")
            if isinstance(environment, Mapping) and environment.get("python_executable_sha256") != executable_sha256:
                errors.append("verifier interpreter SHA-256 differs from the frozen manifest")
        unique_errors = tuple(dict.fromkeys(errors))
        return {
            "authenticated": not unique_errors,
            "decision_id": decision_id,
            "decision_sha256": decision_sha256,
            "manifest_sha256": actual_manifest_sha256,
            "campaign_id": campaign_id,
            "unit_id": unit_id,
            "run_id": run_id,
            "nodeid": nodeid,
            "attempt_number": attempt_number,
            "scientific_identity": dict(scientific_identity),
            "runner_identity": dict(runner_identity),
            "destination": destination,
            "errors": list(unique_errors),
        }
    except (OSError, ContractError, ValueError, TypeError, KeyError) as exc:
        return {"authenticated": False, "errors": [f"{type(exc).__name__}: {exc}"]}


def _absolute_file(value: str, label: str) -> Path:
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{label} must be an absolute traversal-free file path")
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current = current / part
        if current.exists() and (current.is_symlink() or bool(getattr(current, "is_junction", lambda: False)())):
            raise ValueError(f"{label} path contains a symlink or junction")
    if not path.is_file():
        raise ValueError(f"{label} is absent")
    return path.resolve(strict=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runner-root", required=True)
    parser.add_argument("--decision-path", required=True)
    parser.add_argument("--manifest-path", required=True)
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--decision-id", required=True)
    parser.add_argument("--unit-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--nodeid", required=True)
    parser.add_argument("--attempt-number", required=True, type=int)
    parser.add_argument("--destination", required=True)
    parser.add_argument("--scientific-commit", required=True)
    parser.add_argument("--scientific-tree", required=True)
    parser.add_argument("--runner-commit", required=True)
    parser.add_argument("--runner-tree", required=True)
    args = parser.parse_args(argv)
    try:
        root = Path(args.runner_root).resolve(strict=True)
        decision = _absolute_file(args.decision_path, "Owner decision")
        manifest = _absolute_file(args.manifest_path, "execution manifest")
        report = verify_authorized_decision(
            runner_root=root,
            decision_path=decision,
            manifest_path=manifest,
            campaign_id=args.campaign_id,
            decision_id=args.decision_id,
            unit_id=args.unit_id,
            run_id=args.run_id,
            manifest_sha256=args.manifest_sha256,
            nodeid=args.nodeid,
            attempt_number=args.attempt_number,
            destination=args.destination,
            scientific_identity={"commit": args.scientific_commit, "git_tree": args.scientific_tree},
            runner_identity={"commit": args.runner_commit, "git_tree": args.runner_tree},
        )
    except (OSError, ValueError) as exc:
        report = {"authenticated": False, "errors": [f"{type(exc).__name__}: {exc}"]}
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0 if report.get("authenticated") is True else 2


if __name__ == "__main__":
    runner_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(runner_root))
    raise SystemExit(main())
