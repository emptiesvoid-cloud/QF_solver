"""Fail-closed checker and Owner-review report for WP11-R2."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


FAMILIES = ("TET4", "HEX8", "TET10", "HEX20")
EXPECTED_DOFS = {"TET4": 12, "HEX8": 24, "TET10": 30, "HEX20": 60}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _relative_difference(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.max(np.abs(left - right)) / max(float(np.max(np.abs(left))), 1.0))


def audit(root: Path, contract_path: Path, report_json: Path, report_md: Path) -> dict[str, Any]:
    contract = _load(contract_path)
    contract_sha = _sha256(contract_path)
    errors: list[str] = []
    warnings: list[str] = []
    if contract.get("status") != "FROZEN":
        errors.append(f"contract status is {contract.get('status')!r}, not FROZEN")
    if contract.get("source_sha", "").startswith("TO_BE_"):
        errors.append("contract source SHA is not frozen")
    if contract.get("runner_sha", "").startswith("TO_BE_"):
        errors.append("contract runner SHA is not frozen")
    families: dict[str, Any] = {}
    manifest: dict[str, str] = {}
    tolerance = float(contract.get("gates", {}).get("m1_m2_displacement_relative_max", 1.0e-10))
    residual_tolerance = float(contract.get("gates", {}).get("free_residual_relative_l2_max", 1.0e-10))
    for family in FAMILIES:
        case_root = root / family
        phase_data: dict[str, Any] = {}
        required = ("M1", "M2", "M3", "reference")
        for phase in required:
            result_path = case_root / phase / "result.json" if phase != "reference" else case_root / phase / "reference.json"
            if not result_path.is_file():
                errors.append(f"{family}: missing {phase} artifact {result_path}")
                continue
            payload = _load(result_path)
            phase_data[phase] = payload
            manifest[str(result_path.relative_to(root))] = _sha256(result_path)
            if phase != "reference":
                expected_backend = "scipy" if phase == "M1" else "petsc"
                if payload.get("status") != "PASS":
                    errors.append(f"{family} {phase}: result status is not PASS")
                if payload.get("element_family") != family:
                    errors.append(f"{family} {phase}: family mismatch")
                if payload.get("backend") != expected_backend:
                    errors.append(f"{family} {phase}: backend mismatch")
                if payload.get("actual_dofs") != EXPECTED_DOFS[family]:
                    errors.append(f"{family} {phase}: DOF count mismatch")
                if payload.get("source_sha") != contract.get("source_sha"):
                    errors.append(f"{family} {phase}: source SHA mismatch")
                if payload.get("runner_sha") != contract.get("runner_sha"):
                    errors.append(f"{family} {phase}: runner SHA missing or mismatched")
                if payload.get("contract_sha256") != contract_sha:
                    errors.append(f"{family} {phase}: contract SHA mismatch")
                runtime = payload.get("runtime_versions")
                if not isinstance(runtime, dict):
                    errors.append(f"{family} {phase}: runtime versions are missing")
                else:
                    required_runtime = ("python", "numpy", "scipy")
                    if phase in ("M2", "M3"):
                        required_runtime += ("mpi4py", "mpi_library", "petsc4py", "petsc")
                    for runtime_name in required_runtime:
                        if not runtime.get(runtime_name):
                            errors.append(f"{family} {phase}: runtime field {runtime_name!r} is missing")
                if not isinstance(payload.get("command"), list) or not payload.get("command"):
                    errors.append(f"{family} {phase}: invocation command is missing")
                if payload.get("fallback_count") != 0:
                    errors.append(f"{family} {phase}: fallback was reported")
                if float(payload.get("observables", {}).get("free_residual_relative_l2", np.inf)) > residual_tolerance:
                    errors.append(f"{family} {phase}: free residual exceeds contract")
                for name in ("displacement.npy", "stiffness.npy", "loads.npy", "fixed.npy"):
                    evidence = case_root / phase / name
                    if not evidence.is_file():
                        errors.append(f"{family} {phase}: missing {name}")
                    else:
                        manifest[str(evidence.relative_to(root))] = _sha256(evidence)
            else:
                if payload.get("status") != "PASS":
                    errors.append(f"{family}: independent recomputation is not PASS")
                manifest[str(result_path.relative_to(root))] = _sha256(result_path)
        if all(phase in phase_data for phase in required):
            m1 = phase_data["M1"]
            m2 = phase_data["M2"]
            m3 = phase_data["M3"]
            ref = phase_data["reference"]
            m1_u = np.load(case_root / "M1" / "displacement.npy")
            m2_u = np.load(case_root / "M2" / "displacement.npy")
            m3_u = np.load(case_root / "M3" / "displacement.npy")
            m1_m2_delta = _relative_difference(m1_u, m2_u)
            m2_m3_delta = _relative_difference(m2_u, m3_u)
            if m1_m2_delta > tolerance:
                errors.append(f"{family}: M1/M2 displacement delta {m1_m2_delta:.3e} exceeds {tolerance:.3e}")
            if m2_m3_delta != 0.0:
                errors.append(f"{family}: M2/M3 displacement replay delta is {m2_m3_delta:.3e}")
            if m3.get("phase") != "M3" or not m3.get("fresh_process"):
                errors.append(f"{family}: M3 is not marked fresh-process")
            families[family] = {
                "status": "PASS" if not any(item.startswith(f"{family} ") or item.startswith(f"{family}:") for item in errors) else "FAIL_CLOSED",
                "dofs": EXPECTED_DOFS[family],
                "m1_m2_displacement_relative": m1_m2_delta,
                "m2_m3_displacement_relative": m2_m3_delta,
                "m1_observables": m1.get("observables", {}),
                "m2_observables": m2.get("observables", {}),
                "reference_status": ref.get("status"),
            }
        else:
            families[family] = {"status": "HOLD_MISSING_EVIDENCE", "dofs": EXPECTED_DOFS[family]}
    overall = "PASS_CANDIDATE" if not errors and len(families) == len(FAMILIES) else "HOLD_FAIL_CLOSED"
    limitations = [
        "bounded linear static one-element cases",
        "root-side assembly with replicated input",
        "no strong/weak scaling claim",
        "no dynamics/contact/friction qualification",
        "reference is observable recomputation, not an independent global FEM solve",
        "no external FEM solver correlation",
        "no cross-family result equivalence claim",
    ]
    output = {
        "audit_status": overall,
        "owner_review_status": "READY_FOR_OWNER_REVIEW" if overall == "PASS_CANDIDATE" else "HOLD",
        "work_package": "WP11",
        "revision": contract.get("revision"),
        "contract_sha256": contract_sha,
        "source_sha": contract.get("source_sha"),
        "runner_sha": contract.get("runner_sha"),
        "families": families,
        "candidate_points": "6/6" if overall == "PASS_CANDIDATE" else "0/6_PENDING",
        "official_points": "0/6",
        "manifest": manifest,
        "errors": errors,
        "warnings": warnings,
        "limitations": limitations,
    }
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# WP11 multi-family Owner review",
        "",
        f"- Audit status: `{overall}`",
        f"- Candidate status: `{output['owner_review_status']}`",
        f"- Contract SHA-256: `{contract_sha}`",
        f"- Source SHA: `{output['source_sha']}`",
        f"- Runner SHA: `{output['runner_sha']}`",
        "",
        "| Family | DOFs | Status | M1/M2 displacement delta | M2/M3 replay delta | Reference |",
        "|---|---:|---|---:|---:|---|",
    ]
    for family in FAMILIES:
        item = families[family]
        lines.append(
            f"| {family} | {item['dofs']} | {item['status']} | "
            f"{item.get('m1_m2_displacement_relative', 'n/a')} | "
            f"{item.get('m2_m3_displacement_relative', 'n/a')} | "
            f"{item.get('reference_status', 'n/a')} |"
        )
    lines.extend(["", "## Fail-closed findings", ""])
    lines.extend(f"- {error}" for error in errors) if errors else lines.append("- None")
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {limitation}" for limitation in limitations)
    lines.extend(
        [
            "",
            "## Decision boundary",
            "",
            "This package is a candidate only. Official WP11 points remain 0/6 until explicit Owner review.",
        ]
    )
    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--report-json", type=Path, required=True)
    parser.add_argument("--report-md", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.root, args.contract, args.report_json, args.report_md)
    return 0 if result["audit_status"] == "PASS_CANDIDATE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
