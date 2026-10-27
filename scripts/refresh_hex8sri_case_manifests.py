#!/usr/bin/env python3
"""Prepare new source-bound, non-authorized HEX8-SRI case-manifest copies.

This utility never creates an execution authorization, reserves an attempt, or
launches pytest. It versions the case descriptions under a new directory and
keeps their mechanical and acceptance content byte-for-byte equivalent after
canonical JSON parsing. Controller self-identity fields are excluded from the
stable registration digest, as required by development_autonomous.py.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any

try:
    import development_autonomous as controller
except ModuleNotFoundError:
    from scripts import development_autonomous as controller


CAMPAIGN_RELATIVE = Path("investigations/hex8_sri_equilibrium_20261026/campaign_preparation/first_convergence_24")
SOURCE_DIRNAME = "registered_manifests_execution_gate"
REFRESH_DIRNAME = "registered_manifests_source_refresh_c93d539d"
HISTORICAL_SOURCE_HEAD = "8b61f5d37b9557e6d04cbcf8d787b4208af49486"
HISTORICAL_SOURCE_FINGERPRINT = "c93d539d6b67417f067a190066629d41f84c1a04f61a86b50034c3cfda917d04"
HISTORICAL_SUMS_SHA256 = "aa16aa90850d48a8a3765e5b6611d5361db5db597302a6b43b2215263fbed632"
PREPARATION_STATUS = "NOT_RUN_AT_MANIFEST_CREATION; RECEIPT_STORED_SEPARATELY"
CONTROLLER_FIELDS = {
    "controller_code_sha256",
    "controller_identity",
    "controller_identity_status",
}
MUTABLE_CASE_FIELDS = CONTROLLER_FIELDS | {
    "source_fingerprint_sha256",
    "science_source_commit",
    "source_files_sha256",
    "preflight_status",
    "common_problem",
    "criteria_contract",
    "criteria_status",
    "frozen_criteria",
}
COMMON_MUTABLE_FIELDS = {"source_identity", "controller_identity", "preflight_status"}
BUDGET_SEMANTICS = {
    "captured_output": "controller-enforced byte caps",
    "rss_process_temporary_archive": "sampled soft observations, not OS quotas",
    "wall_timeout": "watchdog process-tree termination, best effort",
}
EXPECTED_FORMULATIONS = {
    "hex8_standard": {
        "element_type": "Hex8Element",
        "id": "hex8_standard",
        "operator": "complete 2x2x2 Gauss integration",
    },
    "sri_historical": {
        "element_type": "HistoricalHex8SRIElement",
        "historical_source_commit": "2aa994f34900f39bef8df9db5fb025157fb694bb",
        "id": "sri_historical",
        "operator": "frozen parent-source central volumetric expression without weight 8",
    },
    "sri_corrected": {
        "element_type": "Hex8SRIElement",
        "id": "sri_corrected",
        "operator": "corrected central volumetric integration with weight 8",
    },
}
EXPECTED_COMMON_PHYSICS = {
    "model": {
        "dimensions_L_y_z_m": [20.0, 1.0, 1.0],
        "fixed_face": "x=0, all translations",
        "loaded_area_m2": 1.0,
        "loaded_face": "x=20 m",
        "mean_loaded_face_uz": "Q1 consistent surface-area integral / area; not arithmetic node mean",
        "poisson_ratios": [0.3, 0.4999],
        "resultant_force_n": [0.0, 0.0, -1.0],
        "resultant_moment_about_origin_nm": [-0.5, 20.0, 0.0],
        "traction_pa": [0.0, 0.0, -1.0],
        "young_modulus_pa": 1_000_000.0,
    },
    "formulations": ["hex8_standard", "sri_historical", "sri_corrected"],
    "meshes_xyz": [[4, 2, 2], [8, 4, 4], [16, 8, 8], [32, 16, 16]],
    "independent_3d_reference": {
        "environment": "backend absent from current interpreter; source/version/container not frozen",
        "proposed_family": "mixed displacement-pressure P2/P1 tetrahedral linear elasticity in an independent FEM code",
        "status": "NOT_IMPLEMENTED_OR_QUALIFIED",
        "uncertainty_target_relative": 0.005,
    },
    "timoshenko_reference": {
        "cowper_rectangular_factor_abs_tip_deflection_mm": {"0.3": 32.0612, "0.4999": 32.0699956},
        "shear_factor_5_over_6_abs_tip_deflection_mm": {"0.3": 32.0624, "0.4999": 32.0719952},
        "use": "scale/sign/trend only; not a 3-D error gate",
    },
    "proposed_criteria": {
        "energy_identity_relative_max": 1e-8,
        "finest_level_independent_3d_energy_relative_error_max": 0.05,
        "finest_level_independent_3d_mean_UZ_relative_error_max": 0.05,
        "force_closure_relative_max": 1e-6,
        "free_residual_relative_max": 1e-7,
        "last_two_levels_energy_relative_change_max": 0.02,
        "last_two_levels_mean_UZ_relative_change_max": 0.02,
        "moment_closure_relative_max": 1e-6,
    },
}
EXPECTED_CASE_LOADING = {
    "consistent_q1_surface_weights": True,
    "face_area_m2": 1.0,
    "loaded_face": "x=20 m",
    "resultant_force_n": [0.0, 0.0, -1.0],
    "resultant_moment_about_origin_nm": [-0.5, 20.0, 0.0],
    "uniform_traction_pa": [0.0, 0.0, -1.0],
}
EXPECTED_BOUNDARY_CONDITIONS = {"fixed_components": ["UX", "UY", "UZ"], "fixed_face": "x=0"}
EXPECTED_CASE_ORACLE = {
    "independent_3d_reference": "NOT_IMPLEMENTED_OR_QUALIFIED",
    "precision_gate_enabled": False,
    "timoshenko_trend_only": True,
}


def _criteria_contract_proposal() -> dict[str, Any]:
    dispositions = {}
    for criterion, disposition in controller.HEX8SRI_CRITERIA_DISPOSITIONS.items():
        status = (
            "OWNER_FREEZE_REQUIRED"
            if disposition["classification"] == "CASE_GATE"
            else disposition["status"]
        )
        dispositions[criterion] = {"classification": disposition["classification"], "status": status}
    return {
        "schema": controller.HEX8SRI_CRITERIA_CONTRACT_SCHEMA,
        "revision": controller.HEX8SRI_CRITERIA_CONTRACT_REVISION,
        "dispositions": dispositions,
    }


EXPECTED_CRITERIA_CONTRACT_PROPOSAL = _criteria_contract_proposal()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _registration_sha256(manifest: dict[str, Any]) -> str:
    content = {key: value for key, value in manifest.items() if key not in CONTROLLER_FIELDS}
    payload = json.dumps(content, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return _sha256(payload)


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise ValueError(f"git {' '.join(args)} failed in {root}: {result.stderr.strip()}")
    return result.stdout.strip()


def _source_file_hashes(root: Path, target: str) -> dict[str, str]:
    result = subprocess.run(
        [
            "git",
            "ls-files",
            "-z",
            "--cached",
            "--others",
            "--exclude-standard",
            "--",
            "src/solveur",
            "experiments",
            "tests",
            "pyproject.toml",
            "pytest.ini",
        ],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError("cannot inventory science source files")
    target_module = target.split("::", maxsplit=1)[0]
    files: set[str] = set()
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        relative = Path(os.fsdecode(raw).replace("\\", "/"))
        relative_text = relative.as_posix()
        if (
            relative_text.startswith("src/solveur/")
            and relative.suffix == ".py"
            or relative_text.startswith("experiments/")
            and relative.suffix == ".py"
            or relative_text == target_module
            or relative_text in {"tests/conftest.py", "tests/unit/conftest.py", "pyproject.toml", "pytest.ini"}
        ):
            files.add(relative_text)
    if target_module not in files:
        raise ValueError("exact science test module is absent from the source inventory")
    hashes: dict[str, str] = {}
    for name in sorted(files):
        path = (root / Path(name)).resolve()
        try:
            path.relative_to(root.resolve())
        except ValueError as exc:
            raise ValueError(f"source file escapes the science root: {name}") from exc
        if not path.is_file():
            raise ValueError(f"source file is missing: {name}")
        hashes[name] = _sha256(path.read_bytes())
    return hashes


def _controller_fields(provenance: dict[str, Any] | None) -> dict[str, Any]:
    if provenance is None:
        return {
            "controller_code_sha256": None,
            "controller_identity": None,
            "controller_identity_status": "CONTROLLER_REFRESH_PENDING",
        }
    identity = provenance["identity"]
    hashes = provenance["sha256"]
    if identity.get("status_short") != "":
        raise ValueError("controller worktree must be clean before final manifest preparation")
    return {
        "controller_code_sha256": {
            "runner": hashes["runner"],
            "pytest_plugin": hashes["pytest_plugin"],
            "policy": hashes["policy"],
        },
        "controller_identity": {
            "branch": identity["branch"],
            "head": identity["head"],
            "runner_sha256": hashes["runner"],
            "pytest_plugin_sha256": hashes["pytest_plugin"],
            "policy_sha256": hashes["policy"],
        },
        "controller_identity_status": "FINAL_CONTROLLER_IDENTITY_BOUND",
    }


def _expected_case_mesh(mesh_token: str) -> dict[str, Any]:
    nx, ny, nz = (int(part) for part in mesh_token.split("x"))
    dof_count = 3 * (nx + 1) * (ny + 1) * (nz + 1)
    fixed_dof_count = 3 * (ny + 1) * (nz + 1)
    return {
        "dimensions_L_y_z_m": [20.0, 1.0, 1.0],
        "divisions_xyz": [nx, ny, nz],
        "element_aspect_ratio_xyz": [10.0, 1.0, 1.0],
        "element_count": nx * ny * nz,
        "node_count": (nx + 1) * (ny + 1) * (nz + 1),
        "dof_count": dof_count,
        "fixed_dof_count": fixed_dof_count,
        "free_dof_count": dof_count - fixed_dof_count,
    }


def _validate_common_physics(common_problem: dict[str, Any]) -> None:
    for key, expected in EXPECTED_COMMON_PHYSICS.items():
        if common_problem.get(key) != expected:
            raise ValueError(f"common-problem model, oracle, or criteria differs from the reviewed baseline at {key}")


def _read_case_inventory(directory: Path, targets: tuple[str, ...]) -> dict[str, dict[str, Any]]:
    """Validate the typed index, exact case filenames, and the historical SHA-256 sidecar."""
    index_path = directory / "manifest_bindings.json"
    try:
        if _sha256((directory / "SHA256SUMS.txt").read_bytes()) != HISTORICAL_SUMS_SHA256:
            raise ValueError("historical SHA-256 sidecar differs from its registered digest")
        index = controller._read_strict_json(index_path)
        lines = (directory / "SHA256SUMS.txt").read_text(encoding="ascii").splitlines()
    except (OSError, ValueError) as exc:
        raise ValueError(f"case inventory or SHA-256 sidecar is unavailable: {exc}") from exc
    bindings = index.get("bindings") if isinstance(index, dict) else None
    if not isinstance(index, dict) or index.get("schema") != "qfsolver-hex8sri-convergence24-manifest-bindings-v1" or not isinstance(bindings, dict) or set(bindings) != set(targets):
        raise ValueError("typed manifest index must enumerate exactly the 24 registered nodeids")
    expected = {}
    for nodeid in targets:
        case = controller._hex8sri_convergence24_case(nodeid)
        if case is None:
            raise ValueError("unregistered case in manifest index")
        case_id = f"{case[0]}_nu_{case[1]}_{case[2]}"
        expected[nodeid] = f"manifest_{case_id}.json"
    actual = {p.name for p in directory.glob("manifest_*.json")} - {"manifest_bindings.json"}
    if actual != set(expected.values()):
        raise ValueError("case manifest filenames are missing, extra, or ambiguous")
    checksums = {}
    for line in lines:
        parts = line.split("  ", 1)
        if len(parts) != 2 or len(parts[0]) != 64 or any(c not in "0123456789abcdef" for c in parts[0]) or parts[1] in checksums or Path(parts[1]).name != parts[1]:
            raise ValueError("SHA-256 sidecar contains an invalid or duplicate entry")
        checksums[parts[1]] = parts[0]
    if set(checksums) != set(expected.values()) | {"manifest_bindings.json", "common_problem.json"}:
        raise ValueError("SHA-256 sidecar does not enumerate the exact input pieces")
    for name, sha in checksums.items():
        if not (directory / name).is_file() or _sha256((directory / name).read_bytes()) != sha:
            raise ValueError(f"SHA-256 mismatch for input piece: {name}")
    result = {}
    for nodeid, name in expected.items():
        binding = bindings[nodeid]
        manifest = controller._read_strict_json(directory / name)
        if not isinstance(binding, dict) or not isinstance(manifest, dict) or manifest.get("schema") != "qfsolver-hex8-sri-structural-case-v2" or manifest.get("exact_nodeid") != nodeid or Path(str(binding.get("path", ""))).name != name or binding.get("raw_sha256") != checksums[name] or binding.get("sha256") != _registration_sha256(manifest) or binding.get("case_id") != manifest.get("case_id"):
            raise ValueError(f"typed manifest binding or schema mismatch: {name}")
        result[nodeid] = manifest
    return result


def build_refresh_plan(
    science_root: Path,
    source_manifest_dir: Path,
    output_dir: Path,
    *,
    expected_science_head: str,
    expected_source_fingerprint: str,
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    science_root = science_root.resolve(strict=True)
    source_manifest_dir = source_manifest_dir.resolve(strict=True)
    output_dir = output_dir.resolve()
    if Path(_git(science_root, "rev-parse", "--show-toplevel")).resolve() != science_root:
        raise ValueError("science root is not the exact Git worktree root")
    if _git(science_root, "branch", "--show-current") != "research/hex8-sri-equilibrium":
        raise ValueError("science worktree is not on the registered HEX8-SRI branch")
    if _git(science_root, "rev-parse", "HEAD") != expected_science_head:
        raise ValueError("science HEAD differs from the Owner-supplied source identity")
    if _git(science_root, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("science worktree must be clean before manifest refresh")
    try:
        output_dir.relative_to(science_root)
    except ValueError as exc:
        raise ValueError("new manifests must be stored inside the registered science worktree") from exc
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite a prior manifest refresh: {output_dir}")

    targets = controller._hex8sri_convergence24_nodeids()
    old_by_target = _read_case_inventory(source_manifest_dir, targets)

    source_hashes_by_target: dict[str, dict[str, str]] = {}
    for target in targets:
        fingerprint = controller._worktree_source_fingerprint(science_root, target)
        if fingerprint != expected_source_fingerprint:
            raise ValueError(f"live source fingerprint differs for {target}")
        source_hashes_by_target[target] = _source_file_hashes(science_root, target)

    first = old_by_target[targets[0]]
    common_reference = first.get("common_problem")
    if not isinstance(common_reference, dict) or common_reference.get("path") != "common_problem.json":
        raise ValueError("registered case manifest has no canonical common-problem reference")
    old_common_path = source_manifest_dir / "common_problem.json"
    if not old_common_path.is_file() or _sha256(old_common_path.read_bytes()) != common_reference.get("sha256"):
        raise ValueError("source common-problem file does not match its registered SHA-256")
    common_problem = json.loads(old_common_path.read_text(encoding="utf-8"))
    _validate_common_physics(common_problem)
    common_source_identity = common_problem.get("source_identity")
    if not isinstance(common_source_identity, dict):
        raise ValueError("common-problem source identity is missing")
    expected_file_set = set(source_hashes_by_target[targets[0]])
    if any(set(hashes) != expected_file_set for hashes in source_hashes_by_target.values()):
        raise ValueError("source file inventory differs between registered nodeids")

    first_hashes = source_hashes_by_target[targets[0]]
    entry = controller.load_policy()["worktrees"][controller.HEX8SRI_CONVERGENCE24_WORKTREE_ID]
    identity = controller._git_identity(science_root, expected_branch=entry["branch"], baseline_commit=entry["baseline_commit"])
    controller._validate_hex8sri_registered_source_identity(
        science_root, entry, identity, targets[0], first_hashes, expected_source_fingerprint
    )
    historical_hashes = common_source_identity.get("source_files_sha256")
    if (
        common_source_identity.get("source_commit") != HISTORICAL_SOURCE_HEAD
        or common_source_identity.get("source_fingerprint_sha256") != HISTORICAL_SOURCE_FINGERPRINT
        or not isinstance(historical_hashes, dict)
        or controller._source_inventory_fingerprint(historical_hashes) != HISTORICAL_SOURCE_FINGERPRINT
    ):
        raise ValueError("historical science inventory is missing, altered or unregistered")

    refreshed_common = dict(common_problem)
    refreshed_common["source_identity"] = {
        "branch": "research/hex8-sri-equilibrium",
        "source_commit": expected_science_head,
        "source_files_sha256": first_hashes,
        "source_fingerprint_sha256": expected_source_fingerprint,
    }
    # Controller identity belongs to each case manifest and preflight receipt.
    refreshed_common["controller_identity"] = None
    refreshed_common["preflight_status"] = "COLLECT_ONLY_RECEIPT_STORED_SEPARATELY"
    for key, value in common_problem.items():
        if key not in COMMON_MUTABLE_FIELDS and refreshed_common.get(key) != value:
            raise ValueError(f"common-problem physical/criteria content drifted at {key}")
    common_payload = _json_bytes(refreshed_common)
    common_sha256 = _sha256(common_payload)
    provenance_fields = _controller_fields(provenance)

    rows: dict[str, dict[str, str]] = {}
    payloads: dict[str, bytes] = {"common_problem.json": common_payload}
    for target in targets:
        old = old_by_target[target]
        if old.get("execution_authorized") is not False or old.get("do_not_execute") is not True:
            raise ValueError(f"source case is not execution-locked: {target}")
        if old.get("execution_state") != "PREPARED_NOT_AUTHORIZED" or old.get("frozen_criteria") is not None:
            raise ValueError(f"source case is authorized or has frozen criteria: {target}")
        if old.get("science_branch") != "research/hex8-sri-equilibrium":
            raise ValueError(f"source case names a different science branch: {target}")
        if old.get("source_files_sha256") != historical_hashes or old.get("science_source_commit") != HISTORICAL_SOURCE_HEAD or old.get("source_fingerprint_sha256") != HISTORICAL_SOURCE_FINGERPRINT:
            raise ValueError(f"case historical source identity differs from its verified inventory: {target}")
        case = controller._hex8sri_convergence24_case(target)
        if case is None:
            raise ValueError(f"nodeid no longer maps to a registered case: {target}")
        formulation, nu_token, mesh_token = case
        expected_case_id = f"{formulation}_nu_{nu_token}_{mesh_token}"
        expected_nu = controller.HEX8SRI_CONVERGENCE24_NU_TOKENS[nu_token]
        if (
            old.get("case_id") != expected_case_id
            or old.get("formulation") != EXPECTED_FORMULATIONS[formulation]
            or old.get("poisson_ratio") != expected_nu
            or old.get("material") != {"young_modulus_pa": 1_000_000.0, "poisson_ratio": expected_nu}
            or old.get("boundary_conditions") != EXPECTED_BOUNDARY_CONDITIONS
            or old.get("loading") != EXPECTED_CASE_LOADING
            or old.get("oracle") != EXPECTED_CASE_ORACLE
            or old.get("proposed_criteria") != EXPECTED_COMMON_PHYSICS["proposed_criteria"]
            or old.get("campaign_id") != controller.HEX8SRI_CONVERGENCE24_CAMPAIGN_ID
            or old.get("controller_campaign_scope_id") != controller.HEX8SRI_CONVERGENCE24_WORKTREE_ID
            or old.get("controller_registration_id") != controller.HEX8SRI_CONVERGENCE24_WORKTREE_ID
        ):
            raise ValueError(f"case identity differs from its exact registered nodeid: {target}")
        contract = controller._hex8sri_convergence24_case_contract(old)
        if "x".join(map(str, contract["divisions_xyz"])) != mesh_token or old.get("mesh") != _expected_case_mesh(
            mesh_token
        ):
            raise ValueError(f"mesh data differs from the nodeid for {target}")
        if old.get("common_problem") != common_reference:
            raise ValueError(f"case manifest does not share the registered common-problem identity: {target}")
        expected_budget = {
            **controller._hex8sri_convergence24_budget(target),
            "attempts_per_nodeid": 1,
            "initial_campaign_max_attempts": 24,
            "blas_thread_environment": {
                "OMP_NUM_THREADS": "1",
                "MKL_NUM_THREADS": "1",
                "OPENBLAS_NUM_THREADS": "1",
            },
            "budget_semantics": BUDGET_SEMANTICS,
        }
        if old.get("budgets") != expected_budget:
            raise ValueError(f"resource envelope differs from the registered budget for {target}")

        refreshed = dict(old)
        refreshed.update(
            source_fingerprint_sha256=expected_source_fingerprint,
            science_source_commit=expected_science_head,
            source_files_sha256=source_hashes_by_target[target],
            preflight_status=PREPARATION_STATUS,
            common_problem={"path": "common_problem.json", "sha256": common_sha256},
            criteria_status="OWNER_FREEZE_REQUIRED",
            criteria_contract=EXPECTED_CRITERIA_CONTRACT_PROPOSAL,
            frozen_criteria=None,
            **provenance_fields,
        )
        for key, value in old.items():
            if key not in MUTABLE_CASE_FIELDS and refreshed.get(key) != value:
                raise ValueError(f"case physics, mesh, budget, oracle, or criteria changed at {key}: {target}")
        filename = f"manifest_{expected_case_id}.json"
        payload = _json_bytes(refreshed)
        registration_sha = _registration_sha256(refreshed)
        raw_sha = _sha256(payload)
        rows[target] = {
            "path": (output_dir / filename).relative_to(science_root).as_posix(),
            "sha256": registration_sha,
            "raw_sha256": raw_sha,
            "case_id": expected_case_id,
        }
        payloads[filename] = payload

    binding_record = {
        "schema": "qfsolver-hex8sri-convergence24-manifest-bindings-v1",
        "campaign_id": controller.HEX8SRI_CONVERGENCE24_CAMPAIGN_ID,
        "controller_campaign_scope_id": controller.HEX8SRI_CONVERGENCE24_WORKTREE_ID,
        "source_fingerprint_sha256": expected_source_fingerprint,
        "science_source_commit": expected_science_head,
        "controller_identity_status": "FINAL" if provenance else "PENDING",
        "bindings": rows,
    }
    binding_payload = _json_bytes(binding_record)
    payloads["manifest_bindings.json"] = binding_payload
    sums = [f"{_sha256(payloads[name])}  {name}" for name in sorted(payloads)]
    sums_payload = ("\n".join(sums) + "\n").encode("ascii")
    payloads["SHA256SUMS.txt"] = sums_payload
    return {
        "manifest_count": len(rows),
        "science_head": expected_science_head,
        "source_fingerprint_sha256": expected_source_fingerprint,
        "controller_identity_status": binding_record["controller_identity_status"],
        "output_dir": str(output_dir),
        "bindings": rows,
        "payloads": payloads,
    }


def write_plan(plan: dict[str, Any]) -> None:
    output_dir = Path(plan["output_dir"])
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite prior output: {output_dir}")
    output_dir.mkdir(parents=True)
    try:
        for name, payload in plan["payloads"].items():
            destination = output_dir / name
            with destination.open("xb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
    except Exception:
        # Leave partial new output visible for forensic recovery; never erase it.
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--science-root", type=Path, required=True)
    parser.add_argument("--source-manifest-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=CAMPAIGN_RELATIVE / REFRESH_DIRNAME)
    parser.add_argument("--science-head", required=True)
    parser.add_argument("--source-fingerprint", required=True)
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()
    science_root = args.science_root.resolve(strict=True)
    source_dir = args.source_manifest_dir
    if not source_dir.is_absolute():
        source_dir = science_root / source_dir
    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = science_root / output_dir
    provenance = None if args.plan_only else controller._controller_provenance()
    if provenance is not None:
        identity = provenance["identity"]
        if identity["status_short"] != "":
            raise ValueError("controller worktree must be clean before final case-manifest generation")
    plan = build_refresh_plan(
        science_root,
        source_dir,
        output_dir,
        expected_science_head=args.science_head,
        expected_source_fingerprint=args.source_fingerprint,
        provenance=provenance,
    )
    if not args.plan_only:
        write_plan(plan)
    report = {key: value for key, value in plan.items() if key != "payloads"}
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
