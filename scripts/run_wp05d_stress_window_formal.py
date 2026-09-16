"""Run the Owner-authorized formal WP05-D HEX20 requalification.

The production solve remains the frozen WP05 structural route.  Only the
representative stress post-processing observable is replaced by the explicit
Owner-approved exact reference-window candidate.  Historical evidence is
read-only and the independent observable reference is implemented in a
separate NumPy-only module.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter, process_time
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_wp05_structural_qualification import (  # noqa: E402
    _model,
    _observables,
    _policy_digest,
    _sha256,
    _write_json,
)
from scripts.wp05_cd_structural_harness import (  # noqa: E402
    CONTRACT_JSON,
    StructuralBenchmarkContract,
    build_mesh,
    check_load_conservation,
    mesh_quality,
)
from scripts.wp05d_hex20_independent_reference import evaluate_raw  # noqa: E402
from scripts.wp05_stress_window_candidate import (  # noqa: E402
    ExactReferenceWindowCandidate,
    clipped_reference_window_sigma_xx_hex20,
)
from solveur.core.assembly.geometric import build_total_lagrangian_assembly  # noqa: E402
from solveur.core.analyses.geometric_nonlinear import _newton_dead_load  # noqa: E402
from solveur.core.nonlinear.robustness import NonlinearRobustnessOptions  # noqa: E402


CANDIDATE_CONTRACT_JSON = ROOT / "qualification" / "0_2_9" / "wp05_cd_stress_window_remediation_candidate.json"
AUTHORIZATION_JSON = ROOT / "qualification" / "0_2_9" / "wp05d_formal_requalification_authorization.json"
ARCHIVE_MANIFEST_JSON = ROOT / "qualification" / "0_2_9" / "wp05d_stress_window_diagnostic_archive_manifest.json"
DEFAULT_OUTPUT = ROOT / "qualification" / "0_2_9" / "wp05d_formal_requalification"
EXPECTED_CANDIDATE_CONTRACT_SHA = "b5c05bc59d70ea53fdb0b480f4734c0dd53451b75c889e16e750c9fc6e7c12da"
EXPECTED_HISTORICAL_CONTRACT_SHA = "e8ce5ed095bf3f142b64d5a5838682c638478a5a92c8330a10af88584f52d680"
EXPECTED_POLICY_CODE_SHA = "93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac"
EXPECTED_RUNTIME_POLICY_BINDING_SHA = "895d3c932278c0207b207318216c263a427636d57738bef730917fdc7d9b0ef5"
AUTHORIZED_BASE_SHA = "a670f106f4eef88a3cfe5ca65a09ed55cdcc19fe"
REMEDIATION_SHA = "817b5d098b280fbd0b7fa2938c3204d859f20b0c"
FORMAL_STRESS_LIMIT = 0.08
REPLAY_RTOL = 1.0e-12
REPLAY_ATOL = 1.0e-14
REFERENCE_RTOL = 1.0e-10
REFERENCE_ATOL = 1.0e-12


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _git_branch() -> str:
    return subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object in {path}.")
    return value


def _relative_delta(left: object, right: object) -> float:
    left_array = np.asarray(left, dtype=float)
    right_array = np.asarray(right, dtype=float)
    difference = float(np.linalg.norm(left_array - right_array))
    denominator = max(float(np.linalg.norm(right_array)), 1.0e-300)
    return difference / denominator


def _policy_binding(contract: StructuralBenchmarkContract) -> dict[str, Any]:
    frozen = _read_json(CONTRACT_JSON)["termination_policy"]
    return {
        "policy_source_sha": frozen["policy_source_sha"],
        "frozen_policy_code_digest": frozen["policy_code_digest_sha256"],
        "runtime_policy_binding_digest": _policy_digest(contract),
        "runtime_policy_binding_definition": "canonical solver settings + historical contract digest + mesh thresholds",
    }


def _preflight(output: Path) -> dict[str, Any]:
    if output.exists() and any(output.iterdir()):
        raise RuntimeError(f"Refusing to overwrite non-empty formal output: {output}")
    authorization = _read_json(AUTHORIZATION_JSON)
    if authorization.get("owner_authorizes_formal_requalification") is not True:
        raise RuntimeError("Formal requalification is not explicitly Owner-authorized.")
    if authorization.get("candidate_contract_sha256") != EXPECTED_CANDIDATE_CONTRACT_SHA:
        raise RuntimeError("Authorization candidate contract digest does not match the frozen candidate.")
    if authorization.get("historical_contract_sha256") != EXPECTED_HISTORICAL_CONTRACT_SHA:
        raise RuntimeError("Authorization historical contract digest does not match the preserved contract.")
    candidate_sha = _sha256(CANDIDATE_CONTRACT_JSON)
    historical_sha = _sha256(CONTRACT_JSON)
    if candidate_sha != EXPECTED_CANDIDATE_CONTRACT_SHA:
        raise RuntimeError(f"Candidate contract drift: {candidate_sha}")
    if historical_sha != EXPECTED_HISTORICAL_CONTRACT_SHA:
        raise RuntimeError(f"Historical contract drift: {historical_sha}")
    frozen_contract = _read_json(CONTRACT_JSON)
    policy_code_sha = frozen_contract["termination_policy"]["policy_code_digest_sha256"]
    if policy_code_sha != EXPECTED_POLICY_CODE_SHA:
        raise RuntimeError(f"Frozen policy-code digest drift: {policy_code_sha}")
    contract = StructuralBenchmarkContract()
    runtime_policy_sha = _policy_digest(contract)
    if runtime_policy_sha != EXPECTED_RUNTIME_POLICY_BINDING_SHA:
        raise RuntimeError(f"Runtime policy-binding drift: {runtime_policy_sha}")
    if not ARCHIVE_MANIFEST_JSON.is_file():
        raise RuntimeError("Diagnostic replay archive manifest is missing.")
    status = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)
    if status.strip():
        raise RuntimeError(f"Working tree must be clean before formal execution: {status.strip()}")
    changed = subprocess.check_output(
        ["git", "diff", "--name-only", f"{AUTHORIZED_BASE_SHA}...HEAD"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    production_changes = [path for path in changed if path.startswith("src/")]
    if production_changes:
        raise RuntimeError(f"Unexpected production mechanics changes: {production_changes}")
    output.mkdir(parents=True, exist_ok=True)
    binding = _policy_binding(contract)
    return {
        "authorized_base_sha": AUTHORIZED_BASE_SHA,
        "remediation_sha": REMEDIATION_SHA,
        "execution_sha": _git_sha(),
        "branch": _git_branch(),
        "candidate_contract_sha256": candidate_sha,
        "historical_contract_sha256": historical_sha,
        "policy_binding": binding,
        "authorization_id": authorization.get("authorization_id"),
        "preflight_status": "PASS",
    }


def _run_case(level: str, output: Path, run_kind: str, execution_sha: str) -> dict[str, Any]:
    contract = StructuralBenchmarkContract()
    mesh = build_mesh("HEX20", level, contract)
    case_dir = output / "HEX20" / level
    case_dir.mkdir(parents=True, exist_ok=True)
    result_path = case_dir / "result.json"
    raw_path = case_dir / "raw.npz"
    started = perf_counter()
    cpu_started = process_time()
    binding = _policy_binding(contract)
    payload: dict[str, Any] = {
        "status": "RUNNING",
        "run_kind": run_kind,
        "formal_claim": True,
        "authorized_base_sha": AUTHORIZED_BASE_SHA,
        "remediation_sha": REMEDIATION_SHA,
        "execution_sha": execution_sha,
        "source_sha": execution_sha,
        "branch_at_capture": _git_branch(),
        "evidence_schema_version": 3,
        "candidate_contract_sha256": _sha256(CANDIDATE_CONTRACT_JSON),
        "historical_contract_sha256": _sha256(CONTRACT_JSON),
        "governing_policy_code_digest": binding["frozen_policy_code_digest"],
        "runtime_policy_binding_digest": binding["runtime_policy_binding_digest"],
        "policy_source_sha": binding["policy_source_sha"],
        "contract_path": str(CONTRACT_JSON.relative_to(ROOT)).replace("\\", "/"),
        "candidate_contract_path": str(CANDIDATE_CONTRACT_JSON.relative_to(ROOT)).replace("\\", "/"),
        "family": "HEX20",
        "mesh_level": level,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "node_count": mesh.nodes,
        "element_count": mesh.elements,
        "dof_count": mesh.dofs,
        "mesh_quality": mesh_quality(mesh),
        "load_check": check_load_conservation(mesh, contract),
        "solver_route": "geometric_nonlinear_static / MINRES + Jacobi / canonical line search / floor-aware termination",
        "thresholds": dict(contract.mesh_thresholds),
        "candidate_observable_contract": {
            "method": ExactReferenceWindowCandidate().method_id,
            "claim_scope": "Owner-approved exact reference-window post-processing for straight-sided affine HEX20",
            "formal_requalification": True,
        },
    }
    _write_json(result_path, payload)
    try:
        model, mesh, loads, fixed_nodes = _model("HEX20", level, contract)
        assembly = build_total_lagrangian_assembly(model)
        fixed = np.concatenate([3 * fixed_nodes + component for component in range(3)]).astype(int)
        options = NonlinearRobustnessOptions(
            linear_solver="minres",
            linear_preconditioner="jacobi",
            linear_rtol=1.0e-11,
            linear_atol=1.0e-14,
            linear_maxiter=10_000,
            linear_residual_tolerance=1.0e-10,
            linear_backward_error_tolerance=1.0e-10,
            linear_direct_fallback=False,
            line_search="existing",
            floor_aware_termination=True,
        )
        options.validate()
        displacement, diagnostics = _newton_dead_load(
            assembly,
            loads.reshape(-1),
            fixed,
            increments=12,
            tolerance=1.0e-10,
            max_iterations=40,
            determinant_assembly=assembly,
            robustness_options=options,
        )
        historical_observables, arrays = _observables(model, mesh, loads, fixed_nodes, displacement)
        candidate_observables = clipped_reference_window_sigma_xx_hex20(
            mesh,
            displacement,
            assembly._kernels[0].material,
            contract,
            ExactReferenceWindowCandidate(),
        )
        np.savez_compressed(raw_path, **arrays)
        payload.update(
            {
                "status": "PASS",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "wall_time_s": perf_counter() - started,
                "cpu_time_s": process_time() - cpu_started,
                "observables": historical_observables,
                "candidate_observables": candidate_observables,
                "solver_diagnostics": diagnostics,
                "raw_npz": str(raw_path.relative_to(ROOT)).replace("\\", "/"),
                "raw_sha256": _sha256(raw_path),
                "accepted_load_factors": [
                    item.get("load_factor")
                    for item in diagnostics.get("increments", [])
                    if isinstance(item, dict)
                ],
                "newton_iterations": sum(
                    int(item.get("iterations", 0))
                    for item in diagnostics.get("increments", [])
                    if isinstance(item, dict)
                ),
                "fallback_count": sum(
                    int(item.get("fallback_count", 0))
                    for item in diagnostics.get("increments", [])
                    if isinstance(item, dict)
                ),
            }
        )
    except Exception as exc:
        payload.update(
            {
                "status": "FAILED",
                "terminal_classification": type(exc).__name__,
                "error": str(exc),
                "wall_time_s": perf_counter() - started,
                "cpu_time_s": process_time() - cpu_started,
            }
        )
    _write_json(result_path, payload)
    print(f"{run_kind} {level}: {payload['status']}", flush=True)
    return payload


def _run_independent_reference(
    level: str,
    production: dict[str, Any],
    output: Path,
    execution_sha: str,
) -> dict[str, Any]:
    reference_dir = output / "independent_reference" / level
    reference_dir.mkdir(parents=True, exist_ok=True)
    result_path = reference_dir / "result.json"
    raw_path = ROOT / production["raw_npz"]
    payload: dict[str, Any] = {
        "status": "RUNNING",
        "run_kind": "INDEPENDENT_OBSERVABLE_REFERENCE",
        "formal_claim": True,
        "authorized_base_sha": AUTHORIZED_BASE_SHA,
        "remediation_sha": REMEDIATION_SHA,
        "execution_sha": execution_sha,
        "source_sha": execution_sha,
        "branch_at_capture": _git_branch(),
        "mesh_level": level,
        "production_result_sha256": _sha256(output / "production" / "HEX20" / level / "result.json"),
        "source_raw_sha256": _sha256(raw_path),
        "candidate_contract_sha256": _sha256(CANDIDATE_CONTRACT_JSON),
        "historical_contract_sha256": _sha256(CONTRACT_JSON),
        "governing_policy_code_digest": EXPECTED_POLICY_CODE_SHA,
        "reference_implementation": "scripts/wp05d_hex20_independent_reference.py",
        "independence_claim": {
            "imports_production_solver": False,
            "imports_production_stress_window": False,
            "uses_raw_coordinates_connectivity_displacement_only": True,
        },
    }
    _write_json(result_path, payload)
    try:
        reference = evaluate_raw(raw_path, CANDIDATE_CONTRACT_JSON)
        production_candidate = production["candidate_observables"]
        sigma_error = _relative_delta(
            production_candidate["representative_sigma_xx"],
            reference["representative_sigma_xx"],
        )
        volume_error = abs(
            float(production_candidate["reference_volume"])
            - float(reference["reference_volume"])
        )
        comparison_pass = sigma_error <= REFERENCE_RTOL and volume_error <= REFERENCE_ATOL
        payload.update(
            {
                "status": "PASS" if comparison_pass else "FAIL_CLOSED",
                "reference_observables": reference,
                "comparison": {
                    "production_candidate_sigma_xx": production_candidate["representative_sigma_xx"],
                    "independent_reference_sigma_xx": reference["representative_sigma_xx"],
                    "sigma_relative_error": sigma_error,
                    "sigma_relative_tolerance": REFERENCE_RTOL,
                    "production_candidate_reference_volume": production_candidate["reference_volume"],
                    "independent_reference_volume": reference["reference_volume"],
                    "volume_absolute_error": volume_error,
                    "volume_absolute_tolerance": REFERENCE_ATOL,
                    "status": "PASS" if comparison_pass else "FAIL_CLOSED",
                },
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    except Exception as exc:
        payload.update(
            {
                "status": "FAIL_CLOSED",
                "terminal_classification": type(exc).__name__,
                "error": str(exc),
            }
        )
    _write_json(result_path, payload)
    return payload


def _compare_replay(production: dict[str, Any], replay: dict[str, Any]) -> dict[str, Any]:
    checks: dict[str, bool] = {
        "production_status": production.get("status") == "PASS",
        "replay_status": replay.get("status") == "PASS",
        "accepted_load_factors": False,
        "newton_iterations_exact": production.get("newton_iterations") == replay.get("newton_iterations"),
        "fallback_count_exact": production.get("fallback_count") == replay.get("fallback_count"),
        "observables": False,
        "candidate_observables": False,
    }
    if checks["production_status"] and checks["replay_status"]:
        left_factors = np.asarray(production.get("accepted_load_factors", []), dtype=float)
        right_factors = np.asarray(replay.get("accepted_load_factors", []), dtype=float)
        checks["accepted_load_factors"] = bool(
            left_factors.shape == right_factors.shape
            and np.allclose(left_factors, right_factors, rtol=REPLAY_RTOL, atol=REPLAY_ATOL)
        )
        scalar_keys = (
            "tip_displacement",
            "reaction_resultant",
            "reaction_moment",
            "strain_energy",
            "representative_sigma_xx",
            "stress_region_reference_volume",
            "minimum_detF",
            "minimum_principal_stretch",
            "maximum_principal_stretch",
            "maximum_green_lagrange_norm",
            "external_resultant",
            "external_moment",
            "force_equilibrium_relative",
            "moment_equilibrium_relative",
        )
        checks["observables"] = all(
            key in production.get("observables", {})
            and key in replay.get("observables", {})
            and bool(
                np.allclose(
                    np.asarray(production["observables"][key], dtype=float),
                    np.asarray(replay["observables"][key], dtype=float),
                    rtol=REPLAY_RTOL,
                    atol=REPLAY_ATOL,
                )
            )
            for key in scalar_keys
        ) and production.get("observables", {}).get("envelope_status") == replay.get("observables", {}).get("envelope_status")
        checks["candidate_observables"] = all(
            key in production.get("candidate_observables", {})
            and key in replay.get("candidate_observables", {})
            and bool(
                np.allclose(
                    np.asarray(production["candidate_observables"][key], dtype=float),
                    np.asarray(replay["candidate_observables"][key], dtype=float),
                    rtol=REPLAY_RTOL,
                    atol=REPLAY_ATOL,
                )
            )
            for key in (
                "representative_sigma_xx",
                "reference_volume",
                "expected_reference_volume",
                "reference_volume_absolute_error",
            )
        )
    checks["status"] = all(checks.values())
    return {
        "status": "PASS" if checks["status"] else "FAIL_CLOSED",
        "checks": checks,
        "relative_tolerance": REPLAY_RTOL,
        "absolute_tolerance": REPLAY_ATOL,
    }


def _evaluate_gates(results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    h2 = results["H2"]
    h3 = results["H3"]
    h2_obs = h2.get("observables", {})
    h3_obs = h3.get("observables", {})
    h2_candidate = h2.get("candidate_observables", {})
    h3_candidate = h3.get("candidate_observables", {})
    deltas = {
        "displacement": _relative_delta(h2_obs.get("tip_displacement"), h3_obs.get("tip_displacement")),
        "reaction_resultant": _relative_delta(h2_obs.get("reaction_resultant"), h3_obs.get("reaction_resultant")),
        "reaction_moment": _relative_delta(h2_obs.get("reaction_moment"), h3_obs.get("reaction_moment")),
        "strain_energy": _relative_delta(h2_obs.get("strain_energy"), h3_obs.get("strain_energy")),
        "representative_sigma_xx": _relative_delta(
            h2_candidate.get("representative_sigma_xx"),
            h3_candidate.get("representative_sigma_xx"),
        ),
    }
    thresholds = {
        "displacement": 0.02,
        "reaction_resultant": 0.02,
        "reaction_moment": 0.02,
        "strain_energy": 0.02,
        "representative_sigma_xx": FORMAL_STRESS_LIMIT,
    }
    per_metric = {
        key: {"delta": value, "limit": thresholds[key], "pass": value <= thresholds[key]}
        for key, value in deltas.items()
    }
    structural_gates: dict[str, Any] = {
        "H1": {},
        "H2": {},
        "H3": {},
    }
    for level, result in results.items():
        observed = result.get("observables", {})
        structural_gates[level] = {
            "result_status": result.get("status") == "PASS",
            "load_check": result.get("load_check", {}).get("status") == "PASS",
            "accepted_increment_count": len(result.get("accepted_load_factors", [])) == 12,
            "fallback_count": result.get("fallback_count") == 0,
            "force_equilibrium": observed.get("force_equilibrium_relative", float("inf")) <= 1.0e-8,
            "moment_equilibrium": observed.get("moment_equilibrium_relative", float("inf")) <= 1.0e-8,
            "envelope": observed.get("envelope_status") is True,
        }
        structural_gates[level]["pass"] = all(structural_gates[level].values())
    return {
        "h2_to_h3_deltas": deltas,
        "h2_to_h3_thresholds": thresholds,
        "h2_to_h3_metrics": per_metric,
        "structural_gates": structural_gates,
        "pass": all(item["pass"] for item in per_metric.values()) and all(
            item["pass"] for item in structural_gates.values()
        ),
    }


def _write_report(summary: dict[str, Any], path: Path) -> None:
    deltas = summary["gates"]["h2_to_h3_deltas"]
    lines = [
        "# WP05-D formal HEX20 requalification",
        "",
        "## Decision",
        "",
        f"`FORMAL_STATUS = {summary['formal_status']}`",
        "",
        "The run used the Owner-authorized candidate stress observable. Historical",
        "WP05-D `FAIL_CLOSED` evidence is preserved and remains available for audit.",
        "",
        "## Provenance",
        "",
        f"- `AUTHORIZED_BASE_SHA = {summary['authorized_base_sha']}`",
        f"- `REMEDIATION_SHA = {summary['remediation_sha']}`",
        f"- `EXECUTION_SHA = {summary['execution_sha']}`",
        f"- `EVIDENCE_COMMIT_SHA = {summary['evidence_commit_sha']}`",
        f"- `FINAL_SHA = {summary['final_sha']}`",
        f"- `REMOTE_HEAD = {summary['remote_head']}`",
        f"- branch: `{summary['branch']}`",
        f"- candidate contract SHA-256: `{summary['candidate_contract_sha256']}`",
        f"- historical contract SHA-256: `{summary['historical_contract_sha256']}`",
        f"- frozen policy-code digest: `{summary['frozen_policy_code_digest']}`",
        f"- runtime policy-binding digest: `{summary['runtime_policy_binding_digest']}`",
        "",
        "The policy-code digest and runtime binding digest are deliberately",
        "reported as separate identifiers; neither was silently substituted.",
        "",
        "## Production and reference results",
        "",
        f"- production H1/H2/H3: `{summary['production_status']}`",
        f"- independent observable reference: `{summary['independent_reference_status']}`",
        f"- H1 replay: `{summary['replay_status']}`",
        f"- H2→H3 gates: `{summary['gates']['pass']}`",
        "",
        "H2→H3 relative deltas:",
        "",
        f"- displacement: `{deltas['displacement']:.16g}`",
        f"- reaction resultant: `{deltas['reaction_resultant']:.16g}`",
        f"- reaction moment: `{deltas['reaction_moment']:.16g}`",
        f"- strain energy: `{deltas['strain_energy']:.16g}`",
        f"- candidate representative sigma_xx: `{deltas['representative_sigma_xx']:.16g}`",
        "",
        "The candidate representative stress values are stored in each production",
        "result and are independently recomputed from the raw NPZ files by the",
        "NumPy-only reference.",
        "",
        "## Governance",
        "",
        f"- `WP05D_CANDIDATE_POINTS = {summary['candidate_points']}`",
        f"- `WP05D_FORMAL_POINTS = {summary['formal_points']}`",
        f"- `WP05D_OFFICIAL_POINTS = {summary['official_points']}`",
        f"- `OFFICIAL_TOTAL = {summary['official_total']}`",
        "- `WP05E_STATUS = NOT_RUN_DEPENDENCY_AND_SCOPE_SEPARATE`",
        "- production mechanics changed: `NO`",
        "- thresholds changed: `NO`",
        "- full test suite: `NO`",
        "",
        "A successful execution is evidence for Owner review; it does not itself",
        "rewrite the official ledger. WP05-E is not started automatically.",
        "",
        "## Fail-closed rule",
        "",
        "Any missing artifact, provenance mismatch, reference mismatch, replay",
        "failure, equilibrium failure, envelope failure, or threshold failure",
        "classifies the run as `FAIL_CLOSED` and awards no point.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    preflight = _preflight(output)
    execution_sha = preflight["execution_sha"]
    production_results: dict[str, dict[str, Any]] = {}
    references: dict[str, dict[str, Any]] = {}
    for level in ("H1", "H2", "H3"):
        production = _run_case(level, output / "production", "FORMAL_REQUALIFICATION", execution_sha)
        production_results[level] = production
        if production.get("status") != "PASS":
            summary = {
                **preflight,
                "formal_status": "FAIL_CLOSED",
                "production_status": "FAIL_CLOSED",
                "independent_reference_status": "NOT_RUN_DEPENDENCY_FAILURE",
                "replay_status": "NOT_RUN_DEPENDENCY_FAILURE",
                "gates": {"pass": False, "h2_to_h3_deltas": {}, "h2_to_h3_thresholds": {}, "h2_to_h3_metrics": {}, "structural_gates": {}},
                "candidate_points": "0/1",
                "formal_points": "0/1",
                "official_points": "0/1",
                "official_total": "58/100",
                "evidence_commit_sha": "NOT_YET_COMMITTED",
                "final_sha": "NOT_YET_COMMITTED",
                "remote_head": "NOT_PUSHED",
                "production_results": production_results,
                "independent_references": references,
            }
            _write_json(output / "formal_requalification_summary.json", summary)
            _write_report(summary, output / "formal_requalification_report.md")
            return 1
        references[level] = _run_independent_reference(level, production, output, execution_sha)
        if references[level].get("status") != "PASS":
            summary = {
                **preflight,
                "formal_status": "FAIL_CLOSED",
                "production_status": "PASS_CANDIDATE",
                "independent_reference_status": "FAIL_CLOSED",
                "replay_status": "NOT_RUN_REFERENCE_FAILURE",
                "gates": {"pass": False, "h2_to_h3_deltas": {}, "h2_to_h3_thresholds": {}, "h2_to_h3_metrics": {}, "structural_gates": {}},
                "candidate_points": "0/1",
                "formal_points": "0/1",
                "official_points": "0/1",
                "official_total": "58/100",
                "evidence_commit_sha": "NOT_YET_COMMITTED",
                "final_sha": "NOT_YET_COMMITTED",
                "remote_head": "NOT_PUSHED",
                "production_results": production_results,
                "independent_references": references,
            }
            _write_json(output / "formal_requalification_summary.json", summary)
            _write_report(summary, output / "formal_requalification_report.md")
            return 1
    replay = _run_case("H1", output / "replay", "FORMAL_REPLAY", execution_sha)
    replay_check = _compare_replay(production_results["H1"], replay)
    gates = _evaluate_gates(production_results)
    reference_pass = all(item.get("status") == "PASS" for item in references.values())
    all_pass = reference_pass and replay_check["status"] == "PASS" and gates["pass"]
    binding = preflight["policy_binding"]
    summary = {
        **preflight,
        "formal_status": "PASS_CANDIDATE_OWNER_REVIEW_REQUIRED" if all_pass else "FAIL_CLOSED",
        "production_status": "PASS_CANDIDATE" if all(item.get("status") == "PASS" for item in production_results.values()) else "FAIL_CLOSED",
        "independent_reference_status": "PASS" if reference_pass else "FAIL_CLOSED",
        "replay_status": replay_check["status"],
        "gates": gates,
        "replay_check": replay_check,
        "candidate_points": "1/1" if all_pass else "0/1",
        "formal_points": "1/1" if all_pass else "0/1",
        "official_points": "0/1_OWNER_REVIEW_PENDING" if all_pass else "0/1",
        "official_total": "58/100",
        "frozen_policy_code_digest": binding["frozen_policy_code_digest"],
        "runtime_policy_binding_digest": binding["runtime_policy_binding_digest"],
        "evidence_commit_sha": "NOT_YET_COMMITTED",
        "final_sha": "NOT_YET_COMMITTED",
        "remote_head": "NOT_PUSHED",
        "production_results": production_results,
        "independent_references": references,
        "replay_result": replay,
        "historical_fail_closed_preserved": True,
        "production_mechanics_changed": False,
        "thresholds_changed": False,
        "full_test_suite_run": False,
        "wp05e_status": "NOT_RUN_DEPENDENCY_AND_SCOPE_SEPARATE",
    }
    _write_json(output / "formal_requalification_summary.json", summary)
    _write_report(summary, output / "formal_requalification_report.md")
    print(
        json.dumps(
            {
                "status": summary["formal_status"],
                "candidate_stress_delta": gates["h2_to_h3_deltas"].get("representative_sigma_xx"),
                "reference": summary["independent_reference_status"],
                "replay": summary["replay_status"],
            },
            sort_keys=True,
        ),
        flush=True,
    )
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
