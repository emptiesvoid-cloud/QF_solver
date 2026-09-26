"""Run a source-hash-bound, sequential experimental WP08 surface-stiffness study.

This is a diagnostic runner. Its result is not a formal WP08 qualification and
it cannot update the qualification ledger. Every primary, independent reference
and replay is a separate process; outputs are exclusive and never overwritten.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

KAPPA = 2_666_700.0
PARENT_CONTRACT_DIGEST = "d2d9533c873000996ab3fad992c653dfed37f533ed12d85af97b3696740f179a"
POLICY_DIGEST = "93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac"
PARENT_CONTRACT = ROOT / "qualification/0_2_9/wp08d_structural_reference_contract.json"
SOURCE_DIRS = (ROOT / "src", ROOT / "scripts")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_factor_matrix(load_path: list[dict[str, Any]]) -> Any:
    import numpy as np

    return np.asarray(
        [[float(step["normal_factor"]), float(step["tangential_factor"])] for step in load_path],
        dtype=float,
    )


def _write_json(path: Path, value: object, *, exclusive: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "x" if exclusive else "w"
    with path.open(mode, encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _source_inventory() -> dict[str, str]:
    files = sorted(
        path for directory in SOURCE_DIRS for path in directory.rglob("*.py") if "__pycache__" not in path.parts
    )
    files.append(Path(__file__).resolve())
    return {path.relative_to(ROOT).as_posix(): _sha(path) for path in sorted(set(files))}


def _load_contract(path: Path, expected_sha: str, source_digest: str) -> dict[str, Any]:
    if _sha(path) != expected_sha:
        raise RuntimeError("Diagnostic contract SHA-256 changed after freeze.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "OWNER_AUTHORIZED_EXPERIMENTAL_DIAGNOSTIC_NOT_FORMAL":
        raise RuntimeError("Surface diagnostic contract does not authorize this diagnostic runner.")
    if payload.get("source_bundle_sha256") != source_digest:
        raise RuntimeError("The Python source bundle differs from the contract-bound bytes.")
    inventory_path = path.parent / str(payload.get("source_file_manifest"))
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    if _canonical_sha(inventory) != source_digest or inventory != _source_inventory():
        raise RuntimeError("The detailed source manifest differs from the contract-bound code bytes.")
    if payload.get("parent_contract_sha256") != _sha(PARENT_CONTRACT):
        raise RuntimeError("The parent WP08 contract changed after the diagnostic contract was prepared.")
    physical_law = payload.get("physical_law")
    if not isinstance(physical_law, dict) or physical_law.get("tangential_stiffness_density_N_per_m3") != KAPPA:
        raise RuntimeError("The frozen surface stiffness density differs from this runner.")
    return payload


def _source_snapshot(output: Path) -> tuple[dict[str, str], str]:
    files = _source_inventory()
    _write_json(output / "source_file_manifest.json", files, exclusive=True)
    return files, _canonical_sha(files)


def _make_contract(output: Path) -> tuple[Path, str, str]:
    if not PARENT_CONTRACT.is_file():
        raise FileNotFoundError(PARENT_CONTRACT)
    parent = json.loads(PARENT_CONTRACT.read_text(encoding="utf-8"))
    if _canonical_sha(parent) != PARENT_CONTRACT_DIGEST:
        raise RuntimeError("The parent WP08 contract canonical digest changed.")
    if parent["controlled_provenance"]["governing_policy_digest"] != POLICY_DIGEST:
        raise RuntimeError("The parent WP08 policy digest changed.")
    files, source_digest = _source_snapshot(output)
    kappa = KAPPA
    contract = {
        "schema_version": 1,
        "artifact_id": "QF-029-WP08-SURFACE-TANGENTIAL-DIAGNOSTIC-R1",
        "status": "OWNER_AUTHORIZED_EXPERIMENTAL_DIAGNOSTIC_NOT_FORMAL",
        "created_utc": _utc(),
        "branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip(),
        "git_head_at_freeze": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "working_tree_clean_at_freeze": not bool(
            subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
        ),
        "parent_contract_sha256": _sha(PARENT_CONTRACT),
        "parent_contract_canonical_digest": PARENT_CONTRACT_DIGEST,
        "policy_digest": POLICY_DIGEST,
        "source_bundle_sha256": source_digest,
        "source_file_count": len(files),
        "owner_authorization": {
            "campaign_scope": "experimental sequential M1/M2/M3 production, independent internal references, and deterministic replays",
            "parameter_confirmation": "User explicitly confirmed kappa=2.6667e6 N/m^3 in this conversation.",
            "kappa_derivation": "Historical M1 has four eligible slave nodes with total reference tributary area 1.5 m^2. kappa = (4 * 1e6 N/m) / 1.5 m^2, so each M1 nodal K_i remains 1e6 N/m.",
            "accepted_utc_date": "2026-09-26",
            "formal_points_authorized": False,
            "governing_merge_or_push_authorized": False,
        },
        "physical_law": {
            "mode": "surface",
            "tangential_stiffness_density_N_per_m3": kappa,
            "nodal_rule": "K_i = kappa * sum(reference_T3_area/3) over incident faces",
            "reference_area_only": True,
            "excluded_x0_tributary_area_redistributed": False,
            "normal_contact_law_changed": False,
            "search_route": "frozen initial node-to-triangle",
            "line_stiffness_supported": False,
        },
        "mesh_sequence": ["M1", "M2", "M3"],
        "load_path": parent["friction"]["load_path"],
        "frozen_limits": parent["refinement_contract"]["thresholds"],
        "scope": "Experimental contact stiffness sensitivity on the existing WP08 TET4 benchmark. Results cannot claim WP08 qualification.",
        "execution_order": "For each mesh sequentially: primary production, independent NumPy/KKT reference if primary is readable, deterministic replay if primary converged. Then next mesh.",
        "files_are_hash_bound": True,
        "source_file_manifest": "source_file_manifest.json",
        "formal_qualification": False,
        "ledger_update": False,
        "full_test_suite": False,
    }
    path = output / "diagnostic_contract.json"
    _write_json(path, contract, exclusive=True)
    return path, _sha(path), source_digest


def _worker(args: argparse.Namespace) -> int:
    contract_path = args.contract.resolve()
    source_digest = _canonical_sha(_source_inventory())
    contract = _load_contract(contract_path, args.contract_sha256, source_digest)
    mesh = args.mesh
    case_dir = args.case_dir.resolve()
    if case_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing diagnostic case: {case_dir}")
    if args.role == "reference":
        from scripts.run_wp08d_independent_reference import run

        payload = run(
            mesh,
            args.production_result.resolve(),
            case_dir,
            surface_stiffness_density=KAPPA,
            campaign_contract_sha256=args.contract_sha256,
            source_bundle_sha256=source_digest,
        )
        return 0 if payload.get("status") == "PASS" else 3

    from scripts.wp08d_phase1_common import (
        Phase1Telemetry,
        build_surface_candidate_model,
        extract_observables,
        write_json,
    )
    from solveur.api.public import solve_model
    import numpy as np

    case_dir.mkdir(parents=True, exist_ok=False)
    telemetry = Phase1Telemetry(case_dir / "telemetry.jsonl", analysis_id=f"WP08-SURFACE-{mesh}", mesh=mesh)
    try:
        model = build_surface_candidate_model(mesh, tangential_surface_stiffness=KAPPA)
        result = solve_model(model, enforce_policy=False, telemetry=telemetry._emitter)
        payload = result.to_dict()
        payload["mesh"] = mesh
        payload["tangential_stiffness_mode"] = "surface"
        payload["tangential_stiffness_density_N_per_m3"] = KAPPA
        payload["source_bundle_sha256"] = source_digest
        payload["campaign_contract_sha256"] = args.contract_sha256
        payload["parent_contract_sha256"] = contract["parent_contract_sha256"]
        payload["policy_digest"] = contract["policy_digest"]
        payload["observables"] = extract_observables(result)
        contact = payload.get("solver", {}).get("contact", {})
        payload["contact"] = contact
        converged = payload.get("solver", {}).get("converged") is True
        payload["terminal_classification"] = "PASS" if converged else "FAIL_CLOSED_SOLVER_NOT_CONVERGED"
        payload["qualification_claim"] = "EXPERIMENTAL_SURFACE_STIFFNESS_DIAGNOSTIC_NOT_WP08_QUALIFICATION"
        write_json(case_dir / "result.json", payload)
        contact_rows = contact.get("contacts", []) if isinstance(contact, dict) else []
        states = np.asarray([str(row.get("tangential_state", "open")) for row in contact_rows], dtype=str)
        pressures = np.asarray([float(row.get("pressure", 0.0)) for row in contact_rows], dtype=float)
        forces = np.asarray([row.get("tangential_force", [0.0, 0.0]) for row in contact_rows], dtype=float)
        steps = contact.get("load_steps", []) if isinstance(contact, dict) else []
        digests = [
            hashlib.sha256(json.dumps(item, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            for item in steps
        ]
        np.savez_compressed(
            case_dir / "raw.npz",
            displacement=np.asarray(result.displacements, dtype=float),
            contact_forces=forces,
            contact_pressures=pressures,
            contact_states=states,
            load_factors=_load_factor_matrix(contract["load_path"]),
            accepted_state_digests=np.asarray(digests, dtype=str),
        )
        if args.role == "replay":
            primary = json.loads(args.production_result.resolve().read_text(encoding="utf-8"))
            primary_npz = np.load(args.production_result.resolve().with_name("raw.npz"), allow_pickle=False)
            replay_npz = np.load(case_dir / "raw.npz", allow_pickle=False)
            keys = sorted(primary_npz.files)
            arrays_equal = keys == sorted(replay_npz.files) and all(
                np.array_equal(primary_npz[key], replay_npz[key]) for key in keys
            )
            observable_keys = sorted(primary.get("observables", {}))
            observables_equal = observable_keys == sorted(payload["observables"]) and all(
                np.array_equal(np.asarray(primary["observables"][key]), np.asarray(payload["observables"][key]))
                for key in observable_keys
            )
            comparison = {
                "status": "PASS" if arrays_equal and observables_equal else "FAIL_CLOSED_REPLAY_MISMATCH",
                "raw_arrays_exact_equal": arrays_equal,
                "observables_exact_equal": observables_equal,
                "compared_observables": observable_keys,
                "primary_result_sha256": hashlib.sha256(args.production_result.resolve().read_bytes()).hexdigest(),
            }
            payload["replay_comparison"] = comparison
            write_json(case_dir / "result.json", payload)
            if not arrays_equal or not observables_equal:
                converged = False
        telemetry.close()
        manifest_files = [
            {"path": p.name, "size_bytes": p.stat().st_size, "sha256": _sha(p)}
            for p in sorted(case_dir.iterdir())
            if p.is_file() and p.name != "manifest.json"
        ]
        _write_json(
            case_dir / "manifest.json",
            {
                "role": args.role,
                "mesh": mesh,
                "campaign_contract_sha256": args.contract_sha256,
                "source_bundle_sha256": source_digest,
                "policy_digest": contract["policy_digest"],
                "tangential_stiffness_mode": "surface",
                "tangential_stiffness_density_N_per_m3": KAPPA,
                "files": manifest_files,
                "formal_qualification": False,
            },
            exclusive=True,
        )
        return 0 if converged else 3
    except BaseException:
        telemetry.close()
        raise


def _launch(output: Path) -> int:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite an existing campaign directory: {output}")
    output.mkdir(parents=True, exist_ok=False)
    contract_path, contract_sha, source_digest = _make_contract(output)
    log_root = output / "_process_logs"
    log_root.mkdir()
    records: list[dict[str, Any]] = []
    results: dict[str, dict[str, str]] = {mesh: {} for mesh in ("M1", "M2", "M3")}
    for mesh in ("M1", "M2", "M3"):
        primary_dir = output / mesh / "production"
        primary_result = primary_dir / "result.json"
        primary = _invoke(output, log_root, contract_path, contract_sha, source_digest, mesh, "production", primary_dir)
        records.append(primary)
        primary_status = (
            "MISSING"
            if not primary_result.is_file()
            else json.loads(primary_result.read_text(encoding="utf-8")).get("terminal_classification", "UNKNOWN")
        )
        results[mesh]["production"] = primary_status
        _write_json(
            output / "progress.json",
            {"status": "RUNNING", "mesh": mesh, "phase": "PRIMARY_COMPLETE", "results": results, "processes": records},
        )
        if primary["exit_code"] == 0:
            reference_dir = output / mesh / "independent_reference"
            reference = _invoke(
                output,
                log_root,
                contract_path,
                contract_sha,
                source_digest,
                mesh,
                "reference",
                reference_dir,
                production_result=primary_result,
            )
            records.append(reference)
            results[mesh]["reference"] = "PASS" if reference["exit_code"] == 0 else "FAIL_CLOSED"
            replay_dir = output / mesh / "replay"
            replay = _invoke(
                output,
                log_root,
                contract_path,
                contract_sha,
                source_digest,
                mesh,
                "replay",
                replay_dir,
                production_result=primary_result,
            )
            records.append(replay)
            results[mesh]["replay"] = "PASS" if replay["exit_code"] == 0 else "FAIL_CLOSED"
        else:
            results[mesh]["reference"] = "NOT_RUN_PRIMARY_FAILED"
            results[mesh]["replay"] = "NOT_RUN_PRIMARY_FAILED"
        _write_json(
            output / "progress.json",
            {"status": "RUNNING", "mesh": mesh, "phase": "MESH_COMPLETE", "results": results, "processes": records},
        )
    all_pass = all(all(value == "PASS" for value in roles.values()) for roles in results.values())
    final = {
        "status": "EXPERIMENTAL_ALL_GATES_PASS_CANDIDATE"
        if all_pass
        else "EXPERIMENTAL_RESULTS_RECORDED_GATES_NOT_ALL_PASS",
        "formal_qualification": False,
        "points_awarded": False,
        "contract": contract_path.name,
        "contract_sha256": contract_sha,
        "source_bundle_sha256": source_digest,
        "kappa_N_per_m3": KAPPA,
        "results": results,
        "processes": records,
        "historical_wp08_status_reclassified": False,
    }
    _write_json(output / "final.json", final)
    _write_json(output / "progress.json", {"status": "COMPLETED", "phase": "RUN_END", **final})
    print(json.dumps(final, indent=2, sort_keys=True))
    return 0 if all_pass else 3


def _invoke(
    output: Path,
    log_root: Path,
    contract: Path,
    contract_sha: str,
    source_digest: str,
    mesh: str,
    role: str,
    case_dir: Path,
    *,
    production_result: Path | None = None,
) -> dict[str, Any]:
    case_dir.parent.mkdir(parents=True, exist_ok=True)
    label = f"{mesh}_{role}"
    command = [
        sys.executable,
        "-B",
        str(Path(__file__).resolve()),
        "--worker",
        "--contract",
        str(contract),
        "--contract-sha256",
        contract_sha,
        "--source-bundle-sha256",
        source_digest,
        "--output-root",
        str(output),
        "--mesh",
        mesh,
        "--role",
        role,
        "--case-dir",
        str(case_dir),
    ]
    if production_result is not None:
        command.extend(("--production-result", str(production_result)))
    stdout_path = log_root / f"{label}.stdout.log"
    stderr_path = log_root / f"{label}.stderr.log"
    started = _utc()
    with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
        child = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr, text=False)
        exit_code = child.wait()
    process = {
        "case": label,
        "mesh": mesh,
        "role": role,
        "pid": child.pid,
        "command": command,
        "started_utc": started,
        "ended_utc": _utc(),
        "exit_code": exit_code,
        "stdout_path": stdout_path.relative_to(output).as_posix(),
        "stdout_sha256": _sha(stdout_path),
        "stderr_path": stderr_path.relative_to(output).as_posix(),
        "stderr_sha256": _sha(stderr_path),
        "campaign_contract_sha256": contract_sha,
        "source_bundle_sha256": source_digest,
    }
    process_path = log_root / f"{label}.process.json"
    process["process_manifest_path"] = process_path.relative_to(output).as_posix()
    _write_json(process_path, process, exclusive=True)
    return process


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--launch", action="store_true")
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--contract", type=Path)
    parser.add_argument("--contract-sha256")
    parser.add_argument("--source-bundle-sha256")
    parser.add_argument("--mesh", choices=("M1", "M2", "M3"))
    parser.add_argument("--role", choices=("production", "reference", "replay"))
    parser.add_argument("--case-dir", type=Path)
    parser.add_argument("--production-result", type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.launch:
        return _launch(args.output_root)
    if args.worker and all(
        (args.contract, args.contract_sha256, args.source_bundle_sha256, args.mesh, args.role, args.case_dir)
    ):
        return _worker(args)
    raise SystemExit("Select --launch or provide a complete --worker invocation.")


if __name__ == "__main__":
    raise SystemExit(main())
