"""Run the six frozen WP07-E negative cases against the accepted WP07-D source."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_D_SHA = "ed89446bb74d454ec40170a75c9252514ecc95e2"
EXPECTED_CASES = {
    "reversed_orientation": {"VALIDATION_FAILURE"},
    "open_no_contact": {"PASS_OPEN_NO_CONTACT"},
    "excessive_penetration": {"CONTACT_PENETRATION_EXCESSIVE", "ROUTE_NATIVE_FAILURE"},
    "unsupported_combination": {"UNSUPPORTED_EXPLICIT"},
    "nonfinite_observable": {"EVIDENCE_VALIDATION_FAILURE"},
    "incompatible_restart_metadata": {"RESTART_METADATA_MISMATCH"},
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _load_checker_finiteness() -> Callable[[Any], bool]:
    checker_path = ROOT / "scripts/build_wp07e_closure.py"
    spec = importlib.util.spec_from_file_location("wp07e_r2_existing_closure_checker", checker_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load the existing WP07-E finite-payload validator.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._is_finite_payload


def _load_d_modules(source_root: Path) -> dict[str, Any]:
    if _git(source_root, "rev-parse", "HEAD") != EXPECTED_D_SHA:
        raise RuntimeError("The tested WP07-D source root is not the accepted execution SHA.")
    clean_check = subprocess.run(
        ["git", "-C", str(source_root), "diff", "--quiet", "HEAD", "--", "src"],
        check=False,
        capture_output=True,
        text=True,
    )
    if clean_check.returncode != 0:
        raise RuntimeError("Tracked WP07-D production source has local modifications.")
    d_root = source_root.resolve()
    d_src = d_root / "src"
    if not d_src.is_dir():
        raise RuntimeError(f"The accepted WP07-D checkout has no src package directory: {d_src}")
    current = sys.modules.get("solveur")
    if current is not None:
        module_file = getattr(current, "__file__", None)
        if not isinstance(module_file, str):
            raise RuntimeError("The already-loaded solveur package has no concrete source path.")
        module_path = Path(module_file).resolve()
        if not module_path.is_relative_to(d_src):
            raise RuntimeError(f"A different solveur package is already loaded: {module_path}")
    elif str(d_src) not in sys.path:
        sys.path.insert(0, str(d_src))

    from solveur.contact.evaluation import (  # noqa: PLC0415
        PenaltyContactRestartMetadata,
        evaluate_penalty_contact,
    )
    from solveur.contact.solver import assemble_penalty_contact  # noqa: PLC0415
    from solveur.core.analyses.geometric_nonlinear import GeometricNonlinearStaticSolver  # noqa: PLC0415
    from solveur.core.errors import InputValidationError, MeshValidationError, NumericalConvergenceError  # noqa: PLC0415
    from solveur.core.model import FiniteElementModel  # noqa: PLC0415
    from solveur.core.dofs import DofManager  # noqa: PLC0415
    from solveur.io.json_reader import JsonModelReader  # noqa: PLC0415
    from solveur.mesh.validation import MeshValidator  # noqa: PLC0415

    return {
        "PenaltyContactRestartMetadata": PenaltyContactRestartMetadata,
        "evaluate_penalty_contact": evaluate_penalty_contact,
        "assemble_penalty_contact": assemble_penalty_contact,
        "GeometricNonlinearStaticSolver": GeometricNonlinearStaticSolver,
        "InputValidationError": InputValidationError,
        "MeshValidationError": MeshValidationError,
        "NumericalConvergenceError": NumericalConvergenceError,
        "FiniteElementModel": FiniteElementModel,
        "DofManager": DofManager,
        "JsonModelReader": JsonModelReader,
        "MeshValidator": MeshValidator,
    }


def _point_model(modules: dict[str, Any], *, max_penetration: float | None = None) -> Any:
    analysis: dict[str, Any] = {"type": "linear_static", "method": "direct"}
    if max_penetration is not None:
        analysis["contact_max_penetration"] = max_penetration
    return modules["JsonModelReader"]().from_dict(
        {
            "analysis": analysis,
            "nodes": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.25, 0.25, 0.1]],
            "elements": [],
            "materials": {},
            "fixed_dofs": [],
            "loads": [],
            "springs": [{"node_a": 3, "dofs": ["UZ"], "stiffness": 1000.0}],
            "contacts": [{"name": "plane", "slave_node": 3, "master_nodes": [0, 1, 2]}],
        }
    )


def _run_reversed_orientation(modules: dict[str, Any]) -> dict[str, Any]:
    model = modules["FiniteElementModel"].from_raw(
        nodes=[
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [0.25, 0.25, 0.1],
        ],
        elements=[{"type": "TET4", "nodes": [0, 2, 1, 3], "material": "steel"}],
        materials={"steel": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3}},
        contacts=[{"name": "plane", "slave_node": 4, "master_nodes": [0, 1, 2]}],
        analysis={"type": "linear_static", "method": "direct"},
    )
    report = modules["MeshValidator"]().validate(model)
    errors = [str(item) for item in report.errors]
    detected = report.status == "FAIL" and any("volume" in item.lower() or "inverted" in item.lower() for item in errors)
    return {
        "observed_classification": "VALIDATION_FAILURE" if detected else "NO_VALIDATION_FAILURE",
        "raw_result": {"mesh_validation_status": report.status, "errors": errors},
        "log": ["MeshValidator executed on contact model with reversed TET4 connectivity."],
    }


def _run_open_no_contact(modules: dict[str, Any]) -> dict[str, Any]:
    model = _point_model(modules)
    dofs = model.dof_manager()
    import numpy as np  # noqa: PLC0415

    evaluation = modules["evaluate_penalty_contact"](model, dofs, np.zeros(dofs.ndof), penalty=1.0e6)
    force_norm = float(np.linalg.norm(evaluation.internal_force))
    gap = float(evaluation.gaps[0])
    active_count = int(evaluation.diagnostics["contact_active_count"])
    passed = gap > 0.0 and active_count == 0 and force_norm == 0.0
    return {
        "observed_classification": "PASS_OPEN_NO_CONTACT" if passed else "OPEN_CONTACT_INVARIANT_FAILURE",
        "raw_result": {"gap": gap, "active_contact_count": active_count, "contact_force_norm": force_norm},
        "log": [f"gap={gap:.17g}", f"active_contact_count={active_count}", f"contact_force_norm={force_norm:.17g}"],
    }


def _run_excessive_penetration(modules: dict[str, Any]) -> dict[str, Any]:
    import numpy as np  # noqa: PLC0415

    model = _point_model(modules, max_penetration=0.05)
    dofs = model.dof_manager()
    trial = np.zeros(dofs.ndof)
    trial[dofs.index(3, "UZ")] = -0.2
    try:
        modules["assemble_penalty_contact"](model, dofs, trial, penalty=1.0e6)
    except modules["NumericalConvergenceError"] as error:
        reason = getattr(error, "reason", None)
        reason_value = getattr(reason, "value", reason)
        classification = str(reason_value)
        return {
            "observed_classification": classification,
            "raw_result": {
                "exception_type": type(error).__name__,
                "message": str(error),
                "reason": classification,
                "diagnostics": getattr(error, "diagnostics", {}),
            },
            "log": [f"{type(error).__name__}: {error}", f"reason={classification}"],
        }
    return {
        "observed_classification": "NO_PENETRATION_FAILURE",
        "raw_result": {"trial_displacement_z": -0.2, "configured_contact_max_penetration": 0.05},
        "log": ["Expected explicit excessive-penetration failure was not raised."],
    }


def _run_unsupported_combination(modules: dict[str, Any]) -> dict[str, Any]:
    model = modules["FiniteElementModel"].from_raw(
        nodes=[
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [0.25, 0.25, 0.1],
        ],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "steel"}],
        materials={"steel": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3}},
        contacts=[
            {
                "name": "frictional-plane",
                "slave_node": 4,
                "master_nodes": [0, 1, 2],
                "friction_coefficient": 0.2,
                "tangential_stiffness": 1.0e5,
            }
        ],
        analysis={
            "type": "geometric_nonlinear_static",
            "method": "newton_raphson",
            "contact_mode": "penalty",
        },
    )
    try:
        modules["GeometricNonlinearStaticSolver"]._validate_scope(model)
    except modules["InputValidationError"] as error:
        message = str(error)
        explicit = "supports frictionless contact only" in message
        return {
            "observed_classification": "UNSUPPORTED_EXPLICIT" if explicit else "VALIDATION_FAILURE",
            "raw_result": {"exception_type": type(error).__name__, "message": message},
            "log": [f"{type(error).__name__}: {message}"],
        }
    return {
        "observed_classification": "UNSUPPORTED_COMBINATION_ACCEPTED",
        "raw_result": {"analysis_type": model.analysis.type, "contact_mode": model.analysis.parameters.get("contact_mode")},
        "log": ["Unsupported friction/geometric-nonlinear combination was not rejected."],
    }


def _run_nonfinite_observable(_: dict[str, Any]) -> dict[str, Any]:
    import math  # noqa: PLC0415

    is_finite_payload = _load_checker_finiteness()
    raw_payload = {"wp07d_observables": {"selected_displacement": math.nan}}
    rejected = is_finite_payload(raw_payload) is False
    return {
        "observed_classification": "EVIDENCE_VALIDATION_FAILURE" if rejected else "NONFINITE_ACCEPTED",
        "raw_result": {
            "probe_path": "wp07d_observables.selected_displacement",
            "injected_python_type": "float",
            "injected_value_repr": repr(raw_payload["wp07d_observables"]["selected_displacement"]),
            "finite_validator_returned": is_finite_payload(raw_payload),
        },
        "log": ["The exact WP07-E evidence finite-payload validator received float('nan').", f"rejected={rejected}"],
    }


def _run_incompatible_restart(modules: dict[str, Any]) -> dict[str, Any]:
    model = _point_model(modules)
    metadata = modules["PenaltyContactRestartMetadata"].from_model(
        model,
        penalty=1.0e6,
        model_signature="model-signature-expected",
        accepted_state_digest="accepted-state-expected",
    )
    try:
        metadata.validate_compatible(
            model,
            penalty=1.0e6,
            model_signature="model-signature-expected",
            accepted_state_digest="accepted-state-different",
        )
    except modules["InputValidationError"] as error:
        message = str(error)
        rejected = "does not match" in message
        return {
            "observed_classification": "RESTART_METADATA_MISMATCH" if rejected else "VALIDATION_FAILURE",
            "raw_result": {
                "exception_type": type(error).__name__,
                "message": message,
                "expected_state_digest": "accepted-state-expected",
                "supplied_state_digest": "accepted-state-different",
            },
            "log": [f"{type(error).__name__}: {message}"],
        }
    return {
        "observed_classification": "INCOMPATIBLE_RESTART_ACCEPTED",
        "raw_result": {"metadata": metadata.to_dict()},
        "log": ["Incompatible accepted-state digest was not rejected."],
    }


CASE_RUNNERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "reversed_orientation": _run_reversed_orientation,
    "open_no_contact": _run_open_no_contact,
    "excessive_penetration": _run_excessive_penetration,
    "unsupported_combination": _run_unsupported_combination,
    "nonfinite_observable": _run_nonfinite_observable,
    "incompatible_restart_metadata": _run_incompatible_restart,
}


def run_cases(source_root: Path, output_dir: Path) -> dict[str, Any]:
    d_root = source_root.resolve(strict=True)
    d_sha = _git(d_root, "rev-parse", "HEAD")
    if d_sha != EXPECTED_D_SHA:
        raise RuntimeError(f"WP07-D tested source SHA mismatch: {d_sha}")
    modules = _load_d_modules(d_root)
    runner_sha = _git(ROOT, "rev-parse", "HEAD")
    runner_source_sha256 = _sha256(Path(__file__).resolve())
    runner_blob = subprocess.run(
        ["git", "-C", str(ROOT), "show", f"{runner_sha}:scripts/run_wp07e_negative_cases_r2.py"],
        check=True,
        capture_output=True,
    ).stdout
    if _sha256_bytes(runner_blob) != runner_source_sha256:
        raise RuntimeError("Negative-case runner source does not match the committed execution SHA.")
    contract_path = ROOT / "qualification/0_2_9/wp07e_closure_r2/wp07e_closure_contract_r2.json"
    binding_path = ROOT / "qualification/0_2_9/wp07e_closure_r2/wp07e_closure_binding_r2.json"
    contract_sha256 = _sha256(contract_path)
    binding_sha256 = _sha256(binding_path)
    timestamp = datetime.now(timezone.utc).isoformat()
    output_dir.mkdir(parents=True, exist_ok=False)
    case_records: list[dict[str, Any]] = []
    for index, case in enumerate(EXPECTED_CASES, start=1):
        outcome = CASE_RUNNERS[case](modules)
        observed = outcome["observed_classification"]
        status = "PASS" if observed in EXPECTED_CASES[case] else "FAIL"
        record = {
            "schema_version": 1,
            "artifact_id": f"QF-029-WP07-E-NEG-{index:02d}-{case.upper()}",
            "gate": "WP07",
            "work_package": "WP07-E",
            "case": case,
            "source_sha": d_sha if case != "nonfinite_observable" else runner_sha,
            "execution_sha": d_sha if case != "nonfinite_observable" else runner_sha,
            "runner_commit_sha": runner_sha,
            "runner_source_sha256": runner_source_sha256,
            "contract_file_sha256": contract_sha256,
            "binding_file_sha256": binding_sha256,
            "runner_source_path": str(Path(__file__).resolve()).replace("\\", "/"),
            "tested_source_root": str(d_root).replace("\\", "/"),
            "expected_classifications": sorted(EXPECTED_CASES[case]),
            "observed_classification": observed,
            "status": status,
            "configuration": {
                "scenario": case,
                "frozen_contract_revision": "R2_D_R1_EVIDENCE_BINDING",
                "mechanical_parameters_changed": False,
            },
            "raw_result": outcome["raw_result"],
            "logs": outcome["log"],
            "environment": {"python": sys.version.split()[0], "platform": platform.platform()},
            "timestamp_utc": timestamp,
        }
        case_path = output_dir / f"{case}.json"
        case_path.write_text(json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
        case_records.append(
            {
                "case": case,
                "path": str(case_path.resolve()).replace("\\", "/"),
                "sha256": _sha256(case_path),
                "size_bytes": case_path.stat().st_size,
                "expected_classifications": record["expected_classifications"],
                "observed_classification": observed,
                "status": status,
                "source_sha": record["source_sha"],
                "execution_sha": record["execution_sha"],
            }
        )
    manifest = {
        "schema_version": 1,
        "artifact_id": "QF-029-WP07-E-NEGATIVE-CASE-MANIFEST-R2-001",
        "gate": "WP07",
        "work_package": "WP07-E",
        "contract_revision": "R2_D_R1_EVIDENCE_BINDING",
        "runner_commit_sha": runner_sha,
        "runner_script_sha256": runner_source_sha256,
        "contract_file_sha256": contract_sha256,
        "binding_file_sha256": binding_sha256,
        "wp07d_tested_source_sha": d_sha,
        "cases": case_records,
        "all_six_present_once": len(case_records) == len(EXPECTED_CASES) and len({item["case"] for item in case_records}) == len(EXPECTED_CASES),
        "all_pass": all(item["status"] == "PASS" for item in case_records),
        "production_mechanics_changed": False,
        "thresholds_changed": False,
        "structural_wp07d_rerun": False,
        "timestamp_utc": timestamp,
    }
    manifest_path = output_dir.parent / "negative_case_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--d-source-root", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "qualification/0_2_9/wp07e_closure_r2/negative_cases",
    )
    args = parser.parse_args()
    manifest = run_cases(args.d_source_root, args.output_dir)
    print(json.dumps({"all_pass": manifest["all_pass"], "cases": manifest["cases"]}, indent=2))
    return 0 if manifest["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
