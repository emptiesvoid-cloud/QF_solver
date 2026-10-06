"""Run and record the frozen WP05 GYRO-01..04 regression checks."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import sys
from typing import Any

import numpy as np
import scipy


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "qualification" / "0_2_11" / "wp05_gyroscopic_contract.json"
CASES: dict[str, dict[str, Any]] = {
    "GYRO-01": {
        "purpose": "zero-speed recovery against the classic modal solution for the same physical K/M",
        "commands": [
            "tests/unit/test_rotating_modal_cases.py::test_gyro01_zero_speed_matches_modal_frequencies_multiplicity_and_subspaces"
        ],
        "files": ["tests/unit/test_rotating_modal_cases.py"],
        "reference": {
            "id": "classic-modal-solver-same-assembled-KM-v1",
            "authority": "ModalAnalysisSolver using equivalent concentrated disk inertia",
        },
        "metrics": {
            "frequency_relative_error": "maximum paired selected frequency relative error; <= frozen 1e-8",
            "mode_assurance": "phase-invariant mass-weighted MAC; >= frozen 0.99999999",
            "degenerate_subspace": "minimum singular value of M-weighted cross-subspace; >= frozen 0.99999999",
        },
    },
    "GYRO-02": {
        "purpose": "disk mass/G formulation, skewness, zero gyroscopic work, frame covariance, ownership, fail-closed inputs",
        "commands": [
            "tests/unit/test_rotating_disk_gyro.py",
            "tests/unit/test_rotating_modal_preflight.py",
        ],
        "files": ["tests/unit/test_rotating_disk_gyro.py", "tests/unit/test_rotating_modal_preflight.py"],
        "reference": {
            "id": "analytical-axisymmetric-disk-blocks-v1",
            "authority": "frozen WP05 contract and independent tensor covariance identities",
        },
        "metrics": {
            "mass_block": "exact translational and principal rotary inertia blocks",
            "gyro_skew_error": "||G+G.T||F/max(||G||F,tiny); <= frozen 1e-12",
            "quadratic_work": "v.T G v for deterministic vectors; zero within floating point unit-test tolerance",
            "frame_covariance": "rotated blocks equal orthogonal congruence transform",
        },
    },
    "GYRO-03": {
        "purpose": "independent analytical gyroscopic disk oscillator across the frozen signed-speed fixture",
        "commands": ["tests/unit/test_rotating_qep.py::test_gyro03_independent_disk_oracle_and_qep_residual"],
        "files": ["tests/unit/test_rotating_qep.py"],
        "reference": {
            "id": "closed-form-two-axis-disk-oscillator-v1",
            "formula": "omega0=sqrt(k_theta/Jd); s=Omega*Jp/Jd; omega_pm=sqrt(omega0^2+(s/2)^2) +/- abs(s)/2",
            "independent_of_production_G_assembler": True,
        },
        "metrics": {
            "analytic_frequency_relative_error": "<= frozen 1e-10",
            "qep_relative_residual": "<= frozen 1e-10",
            "mass_normalization_absolute_error": "<= frozen 1e-10",
            "conservative_growth_ratio": "<= frozen 1e-8",
            "conjugate_spectrum_mismatch": "<= frozen 1e-8",
        },
    },
    "GYRO-04": {
        "purpose": "signed-speed pencil behavior, zero-speed degeneracy and unordered spectrum symmetry",
        "commands": ["tests/unit/test_rotating_qep.py"],
        "files": ["tests/unit/test_rotating_qep.py"],
        "reference": {
            "id": "conservative-real-qep-conjugate-spectrum-v1",
            "authority": "frozen QEP invariants plus the independent disk oscillator oracle",
        },
        "metrics": {
            "signed_speed": "scaled signed speed reverses sign while G remains unit-speed",
            "spectral_pairing": "all raw roots have conjugate partners within frozen normalized 1e-8",
            "residual": "all raw roots satisfy original quadratic polynomial within frozen 1e-8",
        },
    },
}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _identity(source_sha: str, case_id: str, case: dict[str, Any], contract: dict[str, Any]) -> Any:
    sys.path.insert(0, str(ROOT / "src"))
    from solveur.verification.v2.execution_identity import ExecutionIdentity, InputFileIdentity

    files = tuple(
        InputFileIdentity.from_bytes(
            logical_role="verification_test",
            logical_id=path,
            content=(ROOT / path).read_bytes(),
            provenance="REPOSITORY",
            availability_status="AVAILABLE_AND_REPRODUCIBLE",
            public_identifier=path,
        )
        for path in case["files"]
    ) + (
        InputFileIdentity.from_bytes(
            logical_role="wp05_test_runner",
            logical_id="scripts/record_wp05_gyro_evidence.py",
            content=Path(__file__).read_bytes(),
            provenance="REPOSITORY",
            availability_status="AVAILABLE_AND_REPRODUCIBLE",
            public_identifier="scripts/record_wp05_gyro_evidence.py",
        ),
    )
    contract_file = InputFileIdentity.from_bytes(
        logical_role="frozen_scientific_contract",
        logical_id="qualification/0_2_11/wp05_gyroscopic_contract.json",
        content=CONTRACT.read_bytes(),
        provenance="REPOSITORY",
        availability_status="AVAILABLE_AND_REPRODUCIBLE",
        public_identifier="qualification/0_2_11/wp05_gyroscopic_contract.json",
    )
    return ExecutionIdentity(
        source_sha=source_sha,
        case_contract_version="0.2.11-wp05-v1",
        units_resolved=True,
        case_definition={"case_id": case_id, "schema_version": 2, "purpose": case["purpose"]},
        model_input={"bounded_scope": contract["scope"]["capability"], "fixtures": case.get("reference", {})},
        input_files=files,
        mesh={"kind": "deterministic_unit_test_fixture", "test_files": list(case["files"])},
        material_data={"model": "linear_elastic_beam_for_GYRO01"} if case_id == "GYRO-01" else {},
        boundary_conditions={"fixture_defined_by_test": True},
        loads={"expected": "zero external load"},
        solver_configuration={"commands": case["commands"], "backend": "SciPy dense generalized QEP where applicable"},
        resolved_overrides={},
        reference_identity=dict(case["reference"]),
        reference_files=(contract_file,),
        tolerance_policy=dict(contract["frozen_tolerances"]),
        metric_definitions=dict(case["metrics"]),
        software_versions={"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__},
        numerical_environment={
            "os": platform.system(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "cpu_count": __import__("os").cpu_count() or 1,
            "dtype": "float64/complex128",
        },
        rotation_configuration={"fixture_speed_is_explicit_per_test": True, "unit": "rad/s"},
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if len(args.source_sha) != 40 or any(char not in "0123456789abcdef" for char in args.source_sha):
        parser.error("--source-sha must be a lowercase full Git SHA")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if head != args.source_sha or status:
        parser.error(
            f"evidence requires a clean working tree at {args.source_sha}; found HEAD={head}, dirty={bool(status)}"
        )

    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    cases: list[dict[str, Any]] = []
    for case_id, case in CASES.items():
        identity = _identity(args.source_sha, case_id, case, contract)
        command = [sys.executable, "-m", "pytest", "-q", *case["commands"]]
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        cases.append(
            {
                "case_id": case_id,
                "purpose": case["purpose"],
                "command": ["python", "-m", "pytest", "-q", *case["commands"]],
                "execution_key": identity.execution_key(),
                "execution_identity": identity.to_dict(),
                "evidence_availability": "AVAILABLE_AND_REPRODUCIBLE",
                "numerical_status": "PASS" if completed.returncode == 0 else "FAIL",
                "maturity": "EXPERIMENTAL",
                "maturity_promotion": "NONE",
                "expected_metrics": case["metrics"],
                "return_code": completed.returncode,
                "stdout": completed.stdout.strip(),
                "stderr": completed.stderr.strip(),
                "observed_at_utc": datetime.now(timezone.utc).isoformat(),
            }
        )

    record: dict[str, Any] = {
        "record_schema": "qf.wp05.gyro-verification-suite.v1",
        "schema_version": 2,
        "work_package": "WP05",
        "source_sha": args.source_sha,
        "contract_path": "qualification/0_2_11/wp05_gyroscopic_contract.json",
        "contract_sha256": _sha(CONTRACT.read_bytes()),
        "cases": cases,
        "overall_status": "PASS" if all(case["numerical_status"] == "PASS" for case in cases) else "FAIL",
        "g04_formulation_status": "PASS" if cases[1]["numerical_status"] == "PASS" else "FAIL",
        "g05_qep_result_status": "PASS"
        if all(cases[index]["numerical_status"] == "PASS" for index in (0, 2, 3))
        else "FAIL",
        "maturity_promotion": "NONE",
    }
    record["suite_sha256"] = _sha(
        json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"overall_status": record["overall_status"], "suite_sha256": record["suite_sha256"]}, sort_keys=True))
    return 0 if record["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
