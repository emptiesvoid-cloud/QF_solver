#!/usr/bin/env python3
"""Create identity-bound, preparation-only copies of the 24 convergence manifests.

This utility copies registered case content from the earlier draft set without
changing criteria, source fingerprints, or execution authorization. Controller
provenance is excluded from the stable registration digest because the
controller policy itself binds these digests; final controller identity is
verified separately and recorded in the preflight receipt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any


CONTROLLER_PROVENANCE_FIELDS = frozenset(
    {"controller_code_sha256", "controller_identity", "controller_identity_status"}
)
CONTROLLER_BRANCH = "codex/hex8sri-controller-registration"
CAMPAIGN_SCOPE_ID = "hex8sri-convergence24"
SOURCE_PROTOCOL_ID = "hex8sri"
EXPECTED_FORMULATIONS = {"hex8_standard", "sri_historical", "sri_corrected"}
EXPECTED_NU = {0.3, 0.4999}
EXPECTED_MESHES = {(4, 2, 2), (8, 4, 4), (16, 8, 8), (32, 16, 16)}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def manifest_registration_sha256(manifest: dict[str, Any]) -> str:
    """Hash immutable case content while excluding controller self-identity fields."""
    content = {key: value for key, value in manifest.items() if key not in CONTROLLER_PROVENANCE_FIELDS}
    payload = json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _sha256(payload)


def _atomic_write(path: Path, payload: bytes, *, replace: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not replace:
        raise FileExistsError(f"refusing to overwrite existing preparation artifact: {path}")
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        if replace:
            os.replace(temporary, path)
        else:
            os.link(temporary, path)
            temporary.unlink()
    finally:
        if temporary.exists():
            temporary.unlink()


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _validate_provenance(args: argparse.Namespace) -> dict[str, Any] | None:
    supplied = (args.controller_head, args.runner_sha256, args.plugin_sha256, args.policy_sha256)
    if not any(supplied):
        return None
    if not all(supplied):
        raise ValueError("final controller provenance requires HEAD and all three SHA-256 values")
    if len(args.controller_head) != 40 or any(char not in "0123456789abcdef" for char in args.controller_head):
        raise ValueError("controller HEAD must be a full lowercase Git SHA-1")
    for name, value in (
        ("runner", args.runner_sha256),
        ("pytest plugin", args.plugin_sha256),
        ("policy", args.policy_sha256),
    ):
        if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            raise ValueError(f"controller {name} identity must be a lowercase SHA-256")
    return {
        "controller_code_sha256": {
            "runner": args.runner_sha256,
            "pytest_plugin": args.plugin_sha256,
            "policy": args.policy_sha256,
        },
        "controller_identity": {
            "branch": CONTROLLER_BRANCH,
            "head": args.controller_head,
            "runner_sha256": args.runner_sha256,
            "pytest_plugin_sha256": args.plugin_sha256,
            "policy_sha256": args.policy_sha256,
        },
        "controller_identity_status": "FINAL_CONTROLLER_IDENTITY_BOUND",
    }


def build_manifests(
    draft_dir: Path,
    output_dir: Path,
    *,
    provenance: dict[str, Any] | None = None,
    refresh_pending: bool = False,
) -> dict[str, Any]:
    repo_root = draft_dir.parents[4]
    request_path = draft_dir / "registration_request.json"
    request = json.loads(request_path.read_text(encoding="utf-8"))
    if request.get("execution_authorized") is not False:
        raise ValueError("registration request is not preparation-only")
    nodeids = request.get("exact_nodeids")
    manifest_map = request.get("manifest_map")
    per_node_budgets = request.get("per_node_budgets")
    if not isinstance(nodeids, list) or len(nodeids) != 24 or len(set(nodeids)) != 24:
        raise ValueError("registration request must contain the exact 24 unique nodeids")
    if not isinstance(manifest_map, dict) or set(manifest_map) != set(nodeids):
        raise ValueError("registration manifest map must exactly match its 24 nodeids")
    if not isinstance(per_node_budgets, dict) or set(per_node_budgets) != set(nodeids):
        raise ValueError("registration per-node budgets must exactly match its 24 nodeids")
    if output_dir.exists() and not refresh_pending:
        raise FileExistsError(f"registered-manifest output already exists: {output_dir}")
    if output_dir.exists() and refresh_pending:
        for nodeid in nodeids:
            binding = manifest_map[nodeid]
            output_path = output_dir / Path(binding["path"]).name
            if not output_path.is_file():
                raise ValueError(f"cannot refresh a missing pending manifest: {output_path.name}")
            current = json.loads(output_path.read_text(encoding="utf-8"))
            if current.get("controller_identity_status") != "CONTROLLER_EXTENSION_PENDING":
                raise ValueError(f"refusing to overwrite a non-pending manifest: {output_path.name}")
    else:
        output_dir.mkdir(parents=True)

    expected_cases: set[tuple[str, float, tuple[int, int, int]]] = {
        (formulation, nu, mesh)
        for formulation in EXPECTED_FORMULATIONS
        for nu in EXPECTED_NU
        for mesh in EXPECTED_MESHES
    }
    observed_cases: set[tuple[str, float, tuple[int, int, int]]] = set()
    bindings: dict[str, dict[str, str]] = {}
    manifests: list[tuple[Path, bytes]] = []

    for nodeid in nodeids:
        draft_binding = manifest_map[nodeid]
        relative_draft = Path(draft_binding["path"])
        draft_path = (repo_root / relative_draft).resolve()
        try:
            draft_path.relative_to(draft_dir.resolve())
        except ValueError as exc:
            raise ValueError("draft manifest path escapes its draft directory") from exc
        if _sha256(draft_path.read_bytes()) != draft_binding.get("sha256"):
            raise ValueError(f"draft manifest checksum mismatch: {draft_path.name}")
        manifest = json.loads(draft_path.read_text(encoding="utf-8"))
        if manifest.get("exact_nodeid") != nodeid:
            raise ValueError(f"draft manifest nodeid differs from registration: {draft_path.name}")
        if manifest.get("execution_authorized") is not False or manifest.get("do_not_execute") is not True:
            raise ValueError(f"draft manifest is not execution-locked: {draft_path.name}")
        if manifest.get("frozen_criteria") is not None:
            raise ValueError("frozen criteria must remain unset until a separate Owner decision")
        formulation = manifest.get("formulation", {}).get("id")
        nu = float(manifest.get("poisson_ratio"))
        mesh_list = manifest.get("mesh", {}).get("divisions_xyz")
        mesh = tuple(mesh_list) if isinstance(mesh_list, list) else ()
        key = (formulation, nu, mesh)
        if key not in expected_cases or key in observed_cases:
            raise ValueError(f"unexpected or duplicate formulation/nu/mesh tuple: {key}")
        observed_cases.add(key)
        budget = per_node_budgets[nodeid]
        for field, value in manifest.get("budgets", {}).items():
            if budget.get(field) != value:
                raise ValueError(f"registration budget differs from manifest for {nodeid}: {field}")

        manifest["controller_campaign_scope_id"] = CAMPAIGN_SCOPE_ID
        manifest["controller_registration_id"] = SOURCE_PROTOCOL_ID
        manifest["controller_code_sha256"] = provenance["controller_code_sha256"] if provenance else None
        manifest["controller_identity"] = provenance["controller_identity"] if provenance else None
        manifest["controller_identity_status"] = (
            provenance["controller_identity_status"] if provenance else "CONTROLLER_EXTENSION_PENDING"
        )
        manifest["budgets"] = dict(budget)
        output_path = output_dir / f"manifest_{manifest['case_id']}.json"
        payload = _json_bytes(manifest)
        registration_sha = manifest_registration_sha256(manifest)
        raw_sha = _sha256(payload)
        bindings[nodeid] = {
            "path": output_path.relative_to(repo_root).as_posix(),
            "sha256": registration_sha,
            "raw_sha256": raw_sha,
            "case_id": manifest["case_id"],
        }
        manifests.append((output_path, payload))

    if observed_cases != expected_cases:
        raise ValueError("registration request does not cover the exact 3x2x4 matrix")

    common_source = draft_dir / "common_problem.json"
    common_target = output_dir / "common_problem.json"
    if not common_target.exists():
        _atomic_write(common_target, common_source.read_bytes(), replace=False)
    elif _sha256(common_target.read_bytes()) != _sha256(common_source.read_bytes()):
        raise ValueError("registered common_problem.json differs from the immutable draft copy")

    for path, payload in manifests:
        _atomic_write(path, payload, replace=refresh_pending)
    binding_record = {
        "schema": "qfsolver-hex8sri-convergence24-manifest-bindings-v1",
        "campaign_id": "HEX8-SRI-CONVERGENCE-24-2026-10-27",
        "controller_campaign_scope_id": CAMPAIGN_SCOPE_ID,
        "source_fingerprint_sha256": request["science_source_fingerprint_sha256"],
        "controller_identity_status": "FINAL" if provenance else "PENDING",
        "bindings": bindings,
    }
    binding_path = output_dir / "manifest_bindings.json"
    _atomic_write(binding_path, _json_bytes(binding_record), replace=refresh_pending)
    sum_lines = [f"{_sha256(common_target.read_bytes())}  common_problem.json"]
    sum_lines.extend(f"{digest['raw_sha256']}  {Path(digest['path']).name}" for digest in bindings.values())
    sum_lines.append(f"{_sha256(binding_path.read_bytes())}  manifest_bindings.json")
    sums_path = output_dir / "SHA256SUMS.txt"
    _atomic_write(sums_path, ("\n".join(sorted(sum_lines)) + "\n").encode("ascii"), replace=refresh_pending)
    return {
        "manifest_count": len(bindings),
        "case_count": len(observed_cases),
        "controller_identity_status": binding_record["controller_identity_status"],
        "bindings_path": str(binding_path),
        "sha256sums_path": str(sums_path),
        "bindings": bindings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--draft-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--refresh-pending", action="store_true")
    parser.add_argument("--controller-head")
    parser.add_argument("--runner-sha256")
    parser.add_argument("--plugin-sha256")
    parser.add_argument("--policy-sha256")
    args = parser.parse_args()
    result = build_manifests(
        args.draft_dir.resolve(),
        args.output_dir.resolve(),
        provenance=_validate_provenance(args),
        refresh_pending=args.refresh_pending,
    )
    print(json.dumps({key: value for key, value in result.items() if key != "bindings"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
