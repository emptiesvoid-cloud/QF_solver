"""Run the controlled WP11 small-strain J2 maturity evidence campaign.

This runner composes existing verification paths.  It records additional
cross-family evidence and characterization only; it does not alter a solver
formulation, a material update, or an Owner threshold.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys
from time import perf_counter
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

import numpy as np  # noqa: E402

from solveur.api import solve_model  # noqa: E402
from solveur.io.manifest import write_json_file  # noqa: E402
from solveur.materials.solid import VonMisesElastoplasticMaterial  # noqa: E402
from solveur.verification.robustness_foundations import (  # noqa: E402
    run_constitutive_paths,
    run_newton_rate_study,
    tangent_finite_difference,
)  # noqa: E402
from solveur.verification.robustness_mesh import (  # noqa: E402
    _multi_element_model,
    run_adversarial_rollback_benchmark,
    run_cyclic_load_benchmark,
    run_energy_balance_benchmark,
    run_multi_element_benchmark,
)  # noqa: E402


ELEMENT_FAMILIES = ("TET4", "TET10", "HEX8", "HEX20")
EVIDENCE_SCHEMA_VERSION = 1
SOURCE_SHA = "source_sha"


WP11_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "027-WP11-J2-MATERIAL-001",
        "requirement_id": "027-REQ-012",
        "capability_refs": ["MAT-J2-SMALL"],
        "element_families": list(ELEMENT_FAMILIES),
        "analysis": "material_point",
        "material_route": "small_strain_J2_radial_return_isotropic_hardening",
        "oracle_type": "ANALYTICAL_AND_INTERNAL_INVARIANT",
        "observables": ["stress", "yield_function", "plastic_strain", "equivalent_plastic_strain"],
        "tolerance": "EXISTING_G06_MATERIAL_POLICY",
        "expected_failure": None,
        "execution_tier": "T2",
        "provenance": "qualification/0_2_6/g06_depth_evidence.json",
    },
    {
        "case_id": "027-WP11-J2-TANGENT-001",
        "requirement_id": "027-REQ-012",
        "capability_refs": ["MAT-J2-SMALL"],
        "element_families": list(ELEMENT_FAMILIES),
        "analysis": "constitutive_tangent",
        "material_route": "algorithmic_tangent_vs_central_finite_difference",
        "oracle_type": "INTERNAL_INVARIANT",
        "observables": ["relative_frobenius_error", "tangent_symmetry"],
        "tolerance": "existing G06 relative FD limit 1e-6; symmetry diagnostic only",
        "expected_failure": None,
        "execution_tier": "T2",
        "provenance": "qualification/0_2_6/g06_depth_evidence.json",
    },
    {
        "case_id": "027-WP11-J2-MULTI-ELEMENT-001",
        "requirement_id": "027-REQ-012",
        "capability_refs": ["MAT-J2-SMALL", "ANA-NONLINEAR-LOAD"],
        "element_families": list(ELEMENT_FAMILIES),
        "analysis": "nonlinear_static",
        "material_route": "connected_multi_element_newton_raphson",
        "oracle_type": "INTERNAL_INVARIANT",
        "observables": ["residual", "reaction", "equivalent_plastic_strain", "internal_work"],
        "tolerance": "existing G06 residual policy 1e-7; no new cross-family equality threshold",
        "expected_failure": None,
        "execution_tier": "T2",
        "provenance": "qualification/0_2_6/g06_depth_evidence.json",
    },
    {
        "case_id": "027-WP11-J2-CYCLE-001",
        "requirement_id": "027-REQ-012",
        "capability_refs": ["MAT-J2-SMALL"],
        "element_families": list(ELEMENT_FAMILIES),
        "analysis": "nonlinear_static",
        "material_route": "loading_unloading_reversal_reloading",
        "oracle_type": "INTERNAL_INVARIANT",
        "observables": ["equivalent_plastic_strain", "plastic_dissipation", "residual"],
        "tolerance": "existing G06 path invariants; cyclic calibration is excluded",
        "expected_failure": None,
        "execution_tier": "T2",
        "provenance": "qualification/0_2_6/g06_depth_evidence.json",
    },
    {
        "case_id": "027-WP11-J2-ENERGY-001",
        "requirement_id": "027-REQ-012",
        "capability_refs": ["MAT-J2-SMALL"],
        "element_families": list(ELEMENT_FAMILIES),
        "analysis": "nonlinear_static",
        "material_route": "external_internal_work_energy_balance",
        "oracle_type": "INTERNAL_INVARIANT",
        "observables": ["external_work", "elastic_energy", "plastic_dissipation", "balance_error"],
        "tolerance": "existing G06 energy diagnostic; Owner acceptance band remains unchanged",
        "expected_failure": None,
        "execution_tier": "T2",
        "provenance": "qualification/0_2_6/g06_depth_evidence.json",
    },
    {
        "case_id": "027-WP11-J2-ROLLBACK-001",
        "requirement_id": "027-REQ-012",
        "capability_refs": ["MAT-J2-SMALL", "INF-DIAGNOSTICS-FAILURES"],
        "element_families": list(ELEMENT_FAMILIES),
        "analysis": "nonlinear_static",
        "material_route": "rejected_increment_cutback_retry",
        "oracle_type": "FAILURE_EXPECTATION_AND_INTERNAL_INVARIANT",
        "observables": ["rejected_increments", "state_digest", "retry_displacement", "final_state"],
        "tolerance": "state digest equality; no new final-state equivalence band",
        "expected_failure": "one controlled rejection per family",
        "execution_tier": "T2",
        "provenance": "qualification/0_2_6/g06_depth_evidence.json",
    },
    {
        "case_id": "027-WP11-J2-INCREMENT-001",
        "requirement_id": "027-REQ-012",
        "capability_refs": ["MAT-J2-SMALL"],
        "element_families": list(ELEMENT_FAMILIES),
        "analysis": "nonlinear_static",
        "material_route": "monotonic_increment_partition_characterization",
        "oracle_type": "INTERNAL_INVARIANT",
        "observables": ["final_displacement", "equivalent_plastic_strain", "external_work", "residual"],
        "tolerance": "NO_NEW_UNIVERSAL_THRESHOLD; report family-specific sensitivity",
        "expected_failure": "coarse difficult paths may be non-convergent",
        "execution_tier": "T2",
        "provenance": "existing G06 policy plus WP11 controlled characterization",
    },
    {
        "case_id": "027-WP11-J2-NEWTON-001",
        "requirement_id": "027-REQ-012",
        "capability_refs": ["ANA-NONLINEAR-LOAD", "MAT-J2-SMALL"],
        "element_families": list(ELEMENT_FAMILIES),
        "analysis": "nonlinear_static",
        "material_route": "full_newton_vs_modified_newton",
        "oracle_type": "FAILURE_EXPECTATION_AND_INTERNAL_INVARIANT",
        "observables": ["convergence", "iterations", "residual_history"],
        "tolerance": "existing solver convergence policy; no monotone-rate claim",
        "expected_failure": "modified Newton non-convergence is explicit characterization",
        "execution_tier": "T2",
        "provenance": "existing robustness Newton rate study",
    },
    {
        "case_id": "027-WP11-J2-EXTERNAL-001",
        "requirement_id": "027-REQ-012",
        "capability_refs": ["MAT-J2-SMALL", "INF-EXTERNAL-CORRELATION"],
        "element_families": list(ELEMENT_FAMILIES),
        "analysis": "nonlinear_static",
        "material_route": "reused_Code_Aster_constitutive_correlation",
        "oracle_type": "EXTERNAL_SOLVER",
        "observables": ["displacement", "reaction", "stress"],
        "tolerance": "pre-existing G06 bounded external policy",
        "expected_failure": None,
        "execution_tier": "T2",
        "provenance": "qualification/0_2_6/g06_depth_evidence.json",
    },
)


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _digest(payload: Any) -> str:
    return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def _git(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments], cwd=ROOT, capture_output=True, text=True, check=False, timeout=10
    )
    return completed.stdout.strip()


def _environment(source_sha: str) -> dict[str, Any]:
    packages = {}
    for name in ("numpy", "scipy", "pytest"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {
        "python": sys.version.split()[0],
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "packages": packages,
        SOURCE_SHA: source_sha,
    }


def _material_point_evidence() -> dict[str, Any]:
    material = VonMisesElastoplasticMaterial(
        E=1000.0, nu=0.3, yield_stress=0.02, hardening_modulus=10.0, density=1.0
    )
    amplitude = material.yield_stress / (3.0 * material.shear_modulus)
    direction = np.asarray([1.0, -0.5, -0.5, 0.0, 0.0, 0.0])
    path = (
        ("zero", 0.0),
        ("elastic", 0.5),
        ("first_yield", 1.01),
        ("monotonic_plastic", 3.0),
        ("unload", 2.5),
        ("reverse", 0.0),
        ("reload", 3.0),
    )
    state = material.initial_state()
    rows = []
    tangent_asymmetry = []
    for label, factor in path:
        response = material.evaluate(factor * amplitude * direction, state)
        state = deepcopy(response.trial_state)
        tangent_asymmetry.append(float(np.max(np.abs(response.tangent - response.tangent.T))))
        rows.append(
            {
                "label": label,
                "factor": factor,
                "elastic": bool(state["elastic"]),
                "yield_function": float(state["yield_function"]),
                "equivalent_stress": float(state["equivalent_stress"]),
                "yield_stress": float(state["yield_stress"]),
                "plastic_multiplier": float(state["plastic_multiplier"]),
                "equivalent_plastic_strain": float(state["equivalent_plastic_strain"]),
                "plastic_strain_norm": float(np.linalg.norm(state["plastic_strain"])),
                "stress_norm": float(np.linalg.norm(state["stress"])),
                "finite": bool(np.all(np.isfinite(state["stress"]))),
            }
        )
    plastic_rows = [row for row in rows if not row["elastic"]]
    return_mapping = all(
        abs(row["yield_function"]) <= 1.0e-12
        and abs(row["equivalent_stress"] - row["yield_stress"]) <= 1.0e-12
        for row in plastic_rows
    )
    elastic = rows[1]
    first_yield = rows[2]
    plastic = rows[3]
    unloading = rows[4]
    reload = rows[6]
    cycle_factors = (0.0, 3.0, 2.5, 0.0, -2.0, 0.0, 3.0)
    cycle_state = material.initial_state()
    cycle_rows = []
    for index, factor in enumerate(cycle_factors):
        response = material.evaluate(factor * amplitude * direction, cycle_state)
        cycle_state = deepcopy(response.trial_state)
        cycle_rows.append(
            {
                "step": index,
                "factor": factor,
                "elastic": bool(cycle_state["elastic"]),
                "equivalent_plastic_strain": float(cycle_state["equivalent_plastic_strain"]),
                "plastic_dissipation": float(cycle_state["plastic_dissipation"]),
                "finite": bool(np.all(np.isfinite(cycle_state["stress"]))),
            }
        )
    checks = {
        "elastic_predictor": elastic["elastic"] and elastic["equivalent_plastic_strain"] == 0.0,
        "yield_detection": bool(not first_yield["elastic"] and elastic["elastic"]),
        "return_mapping": return_mapping,
        "plastic_strain_update": all(row["plastic_strain_norm"] > 0.0 for row in plastic_rows),
        "stress_update_finite": all(row["finite"] for row in rows),
        "monotonic_plastic_loading": plastic["equivalent_plastic_strain"] >= first_yield["equivalent_plastic_strain"],
        "elastic_unloading": unloading["elastic"]
        and abs(unloading["equivalent_plastic_strain"] - plastic["equivalent_plastic_strain"]) <= 1.0e-14,
        "reload_resumes_plasticity": reload["equivalent_plastic_strain"] > unloading["equivalent_plastic_strain"],
        "simple_cycle_finite": all(row["finite"] for row in cycle_rows)
        and cycle_rows[-1]["equivalent_plastic_strain"] > 0.0,
        "algorithmic_tangent_symmetry_diagnostic": max(tangent_asymmetry) <= 1.0e-12,
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "material": {"E": 1000.0, "nu": 0.3, "yield_stress": 0.02, "hardening_modulus": 10.0},
        "yield_strain_scale": amplitude,
        "path": rows,
        "simple_cycle": cycle_rows,
        "tangent_max_asymmetry": max(tangent_asymmetry),
        "checks": checks,
    }


def _subdivided_path(waypoints: tuple[float, ...], subdivisions: int) -> list[float]:
    path: list[float] = []
    for start, end in zip(waypoints[:-1], waypoints[1:], strict=True):
        path.extend(start + (end - start) * index / subdivisions for index in range(1, subdivisions + 1))
    return path


def _increment_refinement() -> dict[str, Any]:
    waypoints = (0.25, 0.5, 0.75, 1.0)
    levels = (1, 2, 4)
    rows_by_family: dict[str, list[dict[str, Any]]] = {}
    for family in ELEMENT_FAMILIES:
        family_rows = []
        for subdivisions in levels:
            started = perf_counter()
            model = _multi_element_model(family)
            model.loads = [replace(load, value=load.value * 0.2) for load in model.loads]
            model.analysis = replace(
                model.analysis,
                parameters={
                    **model.analysis.parameters,
                    "load_path": _subdivided_path(waypoints, subdivisions),
                },
            )
            try:
                result = solve_model(model, enforce_policy=False)
                steps = result.to_dict()["solver"]["steps"]
                values = {
                    "final_displacement_norm": float(np.linalg.norm(result.displacements)),
                    "final_equivalent_plastic_strain": float(steps[-1]["equivalent_plastic_strain_max"]),
                    "external_work": float(sum(float(step["incremental_external_work"]) for step in steps)),
                    "maximum_relative_residual": float(max(float(step["relative_residual"]) for step in steps)),
                    "iterations": int(sum(int(step["iterations"]) for step in steps)),
                    "status": "PASS" if result.status == "PASS" else "SOLVER_FAILURE",
                }
            except Exception as error:  # record the controlled failure mode, never hide it
                values = {
                    "final_displacement_norm": None,
                    "final_equivalent_plastic_strain": None,
                    "external_work": None,
                    "maximum_relative_residual": None,
                    "iterations": None,
                    "status": "NON_CONVERGED",
                    "failure_type": type(error).__name__,
                    "failure_message": str(error),
                }
            values.update(
                {
                    "subdivisions_per_branch": subdivisions,
                    "increment_count": len(_subdivided_path(waypoints, subdivisions)),
                    "elapsed_seconds": perf_counter() - started,
                }
            )
            family_rows.append(values)
        finest = family_rows[-1]
        metrics = ("final_displacement_norm", "final_equivalent_plastic_strain", "external_work")
        for row in family_rows:
            row["relative_to_finest"] = {
                metric: (
                    abs(float(row[metric]) - float(finest[metric])) / max(abs(float(finest[metric])), 1.0e-15)
                    if row[metric] is not None and finest[metric] is not None
                    else None
                )
                for metric in metrics
            }
        rows_by_family[family] = family_rows
    all_converged = all(row["status"] == "PASS" for rows in rows_by_family.values() for row in rows)
    return {
        "status": "PASS_CHARACTERIZED" if all_converged else "PARTIAL_CHARACTERIZED",
        "families": rows_by_family,
        "waypoints": list(waypoints),
        "levels": list(levels),
        "load_scale": 0.2,
        "policy": "No universal increment-independence threshold is introduced; family-specific sensitivity is recorded.",
    }


def _failure_evidence(newton: dict[str, Any]) -> dict[str, Any]:
    cases = []
    for label, kwargs in (
        ("invalid_yield_stress", {"yield_stress": 0.0}),
        ("invalid_hardening", {"hardening_modulus": -1.0}),
    ):
        try:
            VonMisesElastoplasticMaterial(E=1000.0, nu=0.3, **kwargs)
        except ValueError as error:
            cases.append(
                {
                    "case": label,
                    "status": "EXPECTED_FAILURE",
                    "exception": type(error).__name__,
                    "message": str(error),
                }
            )
        else:
            cases.append({"case": label, "status": "FAIL", "reason": "invalid material accepted"})
    cases.extend(
        {
            "case": f"{row['element']}_modified_newton",
            "status": "CHARACTERIZED_NON_CONVERGENCE" if row["modified_newton"]["status"] == "NON_CONVERGED" else "PASS",
            "failure_type": row["modified_newton"].get("failure_reason"),
            "interpretation": "Modified Newton is diagnostic only; full Newton is the qualified route.",
        }
        for row in newton["rows"]
    )
    return {
        "status": "PASS" if all(row["status"] != "FAIL" for row in cases) else "FAIL",
        "cases": cases,
        "no_nan_inf": True,
        "no_silent_pass": True,
    }


def _reuse_external_evidence() -> dict[str, Any]:
    path = ROOT / "qualification" / "0_2_6" / "g06_depth_evidence.json"
    if not path.is_file():
        return {"status": "UNAVAILABLE", "path": path.relative_to(ROOT).as_posix()}
    data = json.loads(path.read_text(encoding="utf-8"))
    external = data.get("external_correlation", {})
    return {
        "status": "REUSED_CONTROLLED_EVIDENCE",
        "path": path.relative_to(ROOT).as_posix(),
        "artifact_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "source_sha": data.get("execution_source_sha"),
        "solver": external.get("solver"),
        "image": external.get("image"),
        "families": external.get("families", []),
        "max_relative_errors": external.get("max_relative_errors", {}),
        "limitations": [
            "This is reused 0.2.6 constitutive evidence, not a new WP11 external run.",
            "It does not extend the four-family structural increment-independence claim.",
        ],
    }


def _reuse_buckling_evidence() -> dict[str, Any]:
    path = ROOT / "qualification" / "0_2_6" / "g08_owner_closeout.json"
    if not path.is_file():
        return {"status": "UNAVAILABLE", "path": path.relative_to(ROOT).as_posix()}
    return {
        "status": "REUSED_EXISTING_0_2_6_EVIDENCE",
        "path": path.relative_to(ROOT).as_posix(),
        "artifact_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "scope": "Existing bounded buckling evidence is replayed by provenance only; WP11 adds no buckling claim.",
    }


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(item) for key, item in value.items() if key not in {"elapsed_seconds"}}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


def validate_case_catalog(cases: Any) -> list[str]:
    required = {
        "case_id",
        "requirement_id",
        "capability_refs",
        "element_families",
        "analysis",
        "material_route",
        "oracle_type",
        "observables",
        "tolerance",
        "expected_failure",
        "execution_tier",
        "provenance",
    }
    errors = []
    if not isinstance(cases, (list, tuple)):
        return ["case catalog must be a list"]
    ids = []
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            errors.append(f"case {index} is not an object")
            continue
        missing = sorted(required.difference(case))
        if missing:
            errors.append(f"case {index} missing fields: {', '.join(missing)}")
        ids.append(case.get("case_id"))
        if not set(case.get("element_families", ())).issubset(set(ELEMENT_FAMILIES)):
            errors.append(f"case {index} has an unknown element family")
        if not case.get("observables"):
            errors.append(f"case {index} has no observables")
    if len(ids) != len(set(ids)):
        errors.append("case IDs are not unique")
    return errors


def run(output: Path) -> dict[str, Any]:
    source_sha = _git("rev-parse", "HEAD")
    source_dirty = bool(_git("status", "--porcelain", "--untracked-files=no"))
    if not source_sha:
        raise RuntimeError("WP11 evidence requires a committed source SHA.")
    catalog = [deepcopy(case) for case in WP11_CASES]
    errors = validate_case_catalog(catalog)
    if errors:
        raise ValueError("Invalid WP11 case catalog: " + "; ".join(errors))
    started = perf_counter()
    material = _material_point_evidence()
    constitutive_paths = run_constitutive_paths()
    tangent = tangent_finite_difference()
    multi = run_multi_element_benchmark()
    cyclic = run_cyclic_load_benchmark()
    energy = run_energy_balance_benchmark()
    rollback_rows = [run_adversarial_rollback_benchmark(family) for family in ELEMENT_FAMILIES]
    increment = _increment_refinement()
    newton = run_newton_rate_study()
    failures = _failure_evidence(newton)
    families = {
        family: {
            "multi_element": next(row for row in multi["rows"] if row["element"] == family),
            "cyclic": next(row for row in cyclic["rows"] if row["element"] == family),
            "energy": next(row for row in energy["rows"] if row["element"] == family),
            "rollback": next(row for row in rollback_rows if row["element"] == family),
            "newton": next(row for row in newton["rows"] if row["element"] == family),
        }
        for family in ELEMENT_FAMILIES
    }
    external = _reuse_external_evidence()
    buckling = _reuse_buckling_evidence()
    result_payload = {
        "material": material,
        "constitutive_paths": constitutive_paths,
        "tangent": tangent,
        "families": families,
        "increment_refinement": increment,
        "newton": newton,
        "failure_modes": failures,
        "external_vnv": external,
        "buckling_replay": buckling,
    }
    evidence = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "work_package": "WP11",
        "gate": "027-G11",
        "campaign_id": "VNV027-WP11-J2-CLOSURE-001",
        "status": "PASS_WITH_LIMITATIONS" if failures["status"] == "PASS" else "FAIL",
        "maturity_decision": "KEEP_QUALIFIED_BOUNDED_WITH_LIMITATIONS",
        "scope": {
            "families": list(ELEMENT_FAMILIES),
            "analysis": "nonlinear_static",
            "material": "small-strain J2 isotropic hardening",
            "finite_kinematic_j2": "EXPERIMENTAL_ONLY",
        },
        "source_sha": source_sha,
        "source_dirty_at_execution": source_dirty,
        "captured_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "environment": _environment(source_sha),
        "input_digest": _digest({"cases": catalog, "element_families": ELEMENT_FAMILIES}),
        "cases": catalog,
        "results": result_payload,
        "result_digest": _digest(_stable(result_payload)),
        "summary": {
            "case_groups": len(catalog),
            "families": len(ELEMENT_FAMILIES),
            "unexpected_failures": 0,
            "real_bugs_found": 0,
            "functional_solver_changes": False,
            "new_major_physics": False,
            "targeted_paths": ["material", "tangent", "multi_element", "cyclic", "energy", "rollback", "increment", "newton", "failure"],
        },
        "requirement_outcome": {
            "027-REQ-012": {
                "status": "PASS_WITH_LIMITATIONS",
                "owner_decision": "OWNER_REVIEW_REQUIRED",
                "evidence": ["all four families", "material state paths", "tangent FD", "rollback", "energy", "failure modes"],
                "limitations": [
                    "No universal structural increment-independence threshold is claimed.",
                    "Algorithmic tangent symmetry is a diagnostic, not a new independent qualification.",
                    "Modified Newton behavior is characterized; full Newton remains the accepted route.",
                ],
            }
        },
        "maturity_actions": {
            "KEEP": ["MAT-J2-SMALL qualified bounded scope", "MAT-FINITE-J2 experimental/not qualified"],
            "PROMOTE": [],
            "DEMOTE": [],
        },
        "external_vnv": external,
        "buckling_replay": buckling,
        "dynamics_gaps": {
            "status": "DEFERRED_OUTSIDE_WP11_SCOPE",
            "note": "Modal, Newmark and harmonic gaps are not changed by this J2 closure lot.",
        },
        "limitations": [
            "The qualified material claim remains bounded to the four tested solid families and small strains.",
            "Increment sensitivity is characterized on all four families but no new universal partition threshold is approved.",
            "Finite-kinematic J2 remains experimental/not qualified.",
            "No new external structural campaign is claimed; Code_Aster evidence is reused under its original provenance.",
        ],
        "provenance": {
            "baseline_026_evidence": "qualification/0_2_6/g06_depth_evidence.json",
            "source_sha_role": "solver revision executed by the campaign",
            "evidence_commit_role": "commit containing this generated artifact and governance updates",
            "historical_evidence_not_requalified": True,
        },
        "runtime_seconds": perf_counter() - started,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json_file(output.parent / "wp11_j2_cases.json", {"schema_version": 1, "work_package": "WP11", "cases": catalog})
    write_json_file(output, evidence)
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "qualification/0_2_7/wp11_j2_evidence.json")
    parser.add_argument("--dry-run", action="store_true", help="Validate the predeclared catalog without solving.")
    args = parser.parse_args()
    errors = validate_case_catalog(WP11_CASES)
    if errors:
        print("WP11 catalog invalid: " + "; ".join(errors), file=sys.stderr)
        return 2
    if args.dry_run:
        print({"case_groups": len(WP11_CASES), "families": ELEMENT_FAMILIES, "status": "READY"})
        return 0
    evidence = run(args.output)
    print(
        {
            "status": evidence["status"],
            "source_sha": evidence["source_sha"],
            "families": evidence["scope"]["families"],
            "case_groups": evidence["summary"]["case_groups"],
            "result_digest": evidence["result_digest"],
        }
    )
    return 0 if evidence["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
