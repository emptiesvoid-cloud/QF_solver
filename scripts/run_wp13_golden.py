"""Replay the compact WP13 golden numerical set through V&V harness v2."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

import numpy as np  # noqa: E402

from solveur.api import solve_model  # noqa: E402
from solveur.compatibility import CompatibilityError  # noqa: E402
from solveur.core.model import FiniteElementModel  # noqa: E402
from solveur.verification.j2_material import J2MaterialVerificationCampaign  # noqa: E402
from solveur.verification.v2 import (  # noqa: E402
    ExecutionOutput,
    VnvRunner,
    canonical_json_bytes,
    load_cases,
    load_json_strict,
    replay_case,
)
from solveur.verification.wedge6_modal import modal_metrics  # noqa: E402


CASE_PATH = ROOT / "qualification/0_2_7/golden/cases.json"
DEFAULT_OUTPUT = ROOT / "qualification/0_2_7/golden/evidence.json"


def _solid_model(element_type: str) -> FiniteElementModel:
    if element_type == "TET4":
        nodes = [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]]
        fixed = (0, 2, 3)
    elif element_type == "TET10":
        corners = np.asarray([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=float)
        edges = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))
        nodes = np.vstack([corners, [(corners[a] + corners[b]) / 2.0 for a, b in edges]]).tolist()
        fixed = (0, 2, 3, 6, 7, 9)
    elif element_type == "HEX8":
        nodes = [
            [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
            [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1],
        ]
        fixed = (0, 3, 4, 7)
    elif element_type == "HEX20":
        corners = np.asarray(
            [
                [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
                [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1],
            ],
            dtype=float,
        )
        edges = (
            (0, 1), (0, 3), (0, 4), (1, 2), (1, 5), (2, 3),
            (2, 6), (3, 7), (4, 5), (4, 7), (5, 6), (6, 7),
        )
        nodes = np.vstack([corners, [(corners[a] + corners[b]) / 2.0 for a, b in edges]]).tolist()
        fixed = (0, 3, 4, 7, 9, 10, 15, 17)
    else:
        raise ValueError(f"Unsupported golden solid {element_type!r}.")
    return FiniteElementModel.from_raw(
        nodes=nodes,
        elements=[{"type": element_type, "nodes": list(range(len(nodes))), "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3, "density": 7800.0}},
        fixed_dofs=[{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in fixed],
        loads=[{"node": 1, "dof": "UX", "value": 1000.0}],
    )


def _wedge_static_model() -> FiniteElementModel:
    nodes = [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [1, 0, 1], [0, 1, 1]]
    return FiniteElementModel.from_raw(
        nodes=nodes,
        elements=[{"type": "WEDGE6", "nodes": list(range(6)), "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3, "density": 7800.0}},
        fixed_dofs=[{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in range(3)],
        loads=[{"node": node, "dof": "UZ", "value": 1.0 / 3.0} for node in (3, 4, 5)],
    )


def _buckling_model() -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "E": 1000.0, "nu": 0.3}},
        fixed_dofs=[{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in (0, 2, 3)],
        loads=[{"node": 1, "dof": "UX", "value": -1.0}],
        analysis={"type": "linear_buckling", "load_increments": 4, "maximum_factor": 100.0},
    )


def _canonical_eigenvalue(value: float) -> float:
    """Remove harmless eigensolver ulps from the persisted golden record."""

    return round(float(value), 12)


def _unknown_element_model() -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "PYRAMID5", "nodes": [0, 1, 2, 3, 0], "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "E": 1.0, "nu": 0.3}},
    )


def _static_observables(element_type: str) -> dict[str, Any]:
    result = solve_model(_solid_model(element_type), enforce_policy=False)
    equilibrium = result.audit.equilibrium
    return {
        "status": str(result.status),
        "displacement_norm": float(np.linalg.norm(result.displacements)),
        "reaction_resultant": [float(value) for value in equilibrium["reaction_resultant"]],
        "strain_energy": float(equilibrium["secant_internal_energy"]),
        "free_relative_residual": float(equilibrium["free_relative_residual"]),
        "finite": bool(np.isfinite(result.displacements).all()),
    }


def _wedge_static_observables() -> dict[str, Any]:
    result = solve_model(_wedge_static_model(), enforce_policy=False)
    equilibrium = result.audit.equilibrium
    return {
        "status": str(result.status),
        "displacement_norm": float(np.linalg.norm(result.displacements)),
        "reaction_resultant": [float(value) for value in equilibrium["reaction_resultant"]],
        "strain_energy": float(equilibrium["secant_internal_energy"]),
        "free_relative_residual": float(equilibrium["free_relative_residual"]),
        "finite": bool(np.isfinite(result.displacements).all()),
    }


def _execute(case) -> ExecutionOutput:
    case_id = case.case_id
    if case_id.startswith("WP13-STATIC-"):
        return ExecutionOutput(_static_observables(case.element))
    if case_id == "WP13-WEDGE6-STATIC":
        return ExecutionOutput(_wedge_static_observables())
    if case_id == "WP13-WEDGE6-MODAL":
        metrics = modal_metrics(1)
        return ExecutionOutput(
            {
                "status": metrics["status"],
                "first_frequency_hz": metrics["frequencies_hz"][0],
                "max_relative_residual": metrics["max_relative_residual"],
                "finite_modes": metrics["finite_modes"],
                "deterministic_modes": metrics["deterministic_modes"],
            }
        )
    if case_id == "WP13-J2-SMALL-STRAIN":
        with TemporaryDirectory(prefix="qf-wp13-j2-") as directory:
            summary = J2MaterialVerificationCampaign(directory).run()
        return ExecutionOutput(
            {
                "status": summary["status"],
                "check_count": len(summary["checks"]),
                "all_checks_pass": all(check["status"] == "PASS" for check in summary["checks"]),
            }
        )
    if case_id == "WP13-BUCKLING-BOUNDED":
        result = solve_model(_buckling_model(), enforce_policy=False)
        return ExecutionOutput(
            {
                "status": str(result.status),
                "critical_factor": _canonical_eigenvalue(result.solver["critical_factor"]),
                "critical_mode_residual_relative": _canonical_eigenvalue(result.solver["critical_mode_residual_relative"]),
                "finite": bool(np.isfinite(result.solver["critical_factor"])),
            }
        )
    if case_id == "WP13-PREFLIGHT-UNKNOWN-ELEMENT":
        try:
            solve_model(_unknown_element_model(), enforce_policy=False)
        except CompatibilityError as exc:
            raise RuntimeError(exc.result.reason) from exc
        raise RuntimeError("UNKNOWN_ELEMENT was not raised.")
    raise ValueError(f"Unsupported WP13 golden case {case_id!r}.")


def _source_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def run(output: Path = DEFAULT_OUTPUT) -> dict[str, int]:
    cases = load_cases(CASE_PATH)
    source_sha = _source_sha()
    runner = VnvRunner(
        source_sha=source_sha,
        environment={"runner": "run_wp13_golden", "catalog": CASE_PATH.name, "tier": "T1"},
    )
    evidence = [runner.run(case, _execute).to_dict() for case in cases]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_json_bytes(evidence))
    counts = {verdict: sum(item["verdict"] == verdict for item in evidence) for verdict in sorted({item["verdict"] for item in evidence})}
    print(f"WP13 golden evidence written to {output}: {counts}")
    return counts


def replay(output: Path = DEFAULT_OUTPUT) -> dict[str, int]:
    cases = {case.case_id: case for case in load_cases(CASE_PATH)}
    records = load_json_strict(output)
    source_sha = _source_sha()
    outcomes: dict[str, int] = {"PASS": 0, "MISMATCH": 0}
    for record in records:
        case = cases[record["case_id"]]
        ok, status, _ = replay_case(case, _execute, record, source_sha=source_sha)
        if ok and status == "PASS":
            outcomes["PASS"] += 1
        else:
            outcomes["MISMATCH"] += 1
            print(f"Replay mismatch for {case.case_id}: {status}")
    print(f"WP13 golden replay: {outcomes}")
    return outcomes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--replay", action="store_true", help="Replay committed evidence at the same source SHA.")
    args = parser.parse_args()
    result = replay(args.output) if args.replay else run(args.output)
    return 0 if not any(result.get(key, 0) for key in ("FAIL", "INVALID_EVIDENCE", "MISMATCH")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
