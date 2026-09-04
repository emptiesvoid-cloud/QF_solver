"""Execute the compact WEDGE6 WP07 evidence catalog through V&V v2."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess

import numpy as np

from solveur.elements.solid.wedge6 import Wedge6Element
from solveur.mesh.quality_contract import wedge6_jacobian_certificate
from solveur.materials.solid import SolidMaterial
from solveur.verification.v2 import ExecutionOutput, VnvRunner, canonical_json_bytes, load_cases


MATERIAL = SolidMaterial(E=210.0e9, nu=0.3)
CASE_PATH = Path(__file__).resolve().parents[1] / "qualification/0_2_7/vnv_v2/wp07_cases.json"
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "qualification/0_2_7/vnv_v2/wp07_evidence.json"
NOMINAL = np.array(
    ((0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (0.0, 1.0, 0.0),
     (0.0, 0.0, 3.0), (2.0, 0.0, 3.0), (0.0, 1.0, 3.0)),
    dtype=float,
)
TERRA_ADVERSARIAL = np.array(
    ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0),
     (-0.5, 0.5, 0.20), (0.5, 0.5, -0.20), (0.5, -0.5, 0.20)),
    dtype=float,
)


def _constant_strain_error(element: Wedge6Element) -> float:
    matrix = np.asarray(((0.02, 0.002, 0.003), (0.002, -0.01, -0.0025), (0.003, -0.0025, 0.03)))
    target = np.array(
        (
            matrix[0, 0],
            matrix[1, 1],
            matrix[2, 2],
            matrix[0, 1] + matrix[1, 0],
            matrix[1, 2] + matrix[2, 1],
            matrix[0, 2] + matrix[2, 0],
        ),
        dtype=float,
    )
    displacement = np.zeros(18, dtype=float)
    for index, coordinate in enumerate(NOMINAL):
        x, y, z = coordinate
        displacement[3 * index:3 * index + 3] = (
            matrix[0, 0] * x + matrix[0, 1] * y + matrix[0, 2] * z,
            matrix[1, 0] * x + matrix[1, 1] * y + matrix[1, 2] * z,
            matrix[2, 0] * x + matrix[2, 1] * y + matrix[2, 2] * z,
        )
    return max(
        float(np.max(np.abs(element.strain_at(NOMINAL, displacement, point) - target)))
        for point in element.integration_points
    )


def _execute(case) -> ExecutionOutput:
    if case.case_id == "WP07-JACOBIAN-TERRA-ADVERSARIAL":
        Wedge6Element(MATERIAL).integration_data(TERRA_ADVERSARIAL)
    element = Wedge6Element(MATERIAL)
    certificate = wedge6_jacobian_certificate(NOMINAL)
    stiffness = element.stiffness(NOMINAL)
    reference = element.reference_stiffness(NOMINAL)
    if case.case_id == "WP07-SHAPE-IDENTITIES":
        errors = []
        for point in ((0.2, 0.3, -0.4), (0.1, 0.2, 0.8)):
            values = element.shape_functions(point)
            derivatives = element.shape_derivatives_reference(point)
            errors.append(abs(float(np.sum(values)) - 1.0))
            errors.extend(abs(value) for value in np.sum(derivatives, axis=0))
        return ExecutionOutput({"max_identity_error": max(errors)})
    if case.case_id == "WP07-JACOBIAN-NOMINAL":
        return ExecutionOutput({"certified_min_det_jacobian": certificate["minimum_detJ"]})
    if case.case_id == "WP07-K-SYMMETRY":
        return ExecutionOutput({"max_symmetry_error": float(np.max(np.abs(stiffness - stiffness.T)))})
    if case.case_id == "WP07-RIGID-RANK":
        return ExecutionOutput(
            {
                "stiffness_rank": int(np.linalg.matrix_rank(stiffness, tol=1.0e-10 * np.max(np.abs(stiffness)))),
                "rigid_body_mode_count": 6,
            }
        )
    if case.case_id == "WP07-AFFINE-CONSTANT-STRAIN":
        return ExecutionOutput({"max_constant_strain_error": _constant_strain_error(element)})
    if case.case_id == "WP07-QUADRATURE-COMPARISON":
        scale = max(float(np.linalg.norm(reference)), 1.0e-30)
        return ExecutionOutput({"relative_stiffness_difference": float(np.linalg.norm(stiffness - reference) / scale)})
    if case.case_id == "WP07-STRESS-RECOVERY":
        return ExecutionOutput({"integration_point_count": len(element.integration_point_results(NOMINAL, np.zeros(18), MATERIAL))})
    raise ValueError(f"Unsupported WP07 case {case.case_id!r}.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    cases = load_cases(CASE_PATH)
    repo_root = CASE_PATH.parents[3]
    source_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_root, check=True, capture_output=True, text=True
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=repo_root, check=True, capture_output=True, text=True
    )
    if status.stdout.strip():
        raise SystemExit("WP07 evidence requires a clean committed source snapshot.")
    runner = VnvRunner(source_sha=source_sha, environment={"runner": "run_wedge6_wp07", "catalog": CASE_PATH.name})
    evidence = [runner.run(case, _execute).to_dict() for case in cases]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json_bytes(evidence))
    counts = {verdict: sum(item["verdict"] == verdict for item in evidence) for verdict in sorted({item["verdict"] for item in evidence})}
    print(f"WP07 evidence written to {args.output}: {counts}")
    return 0 if all(item["verdict"] in {"PASS", "EXPECTED_FAILURE_PASS"} for item in evidence) else 1


if __name__ == "__main__":
    raise SystemExit(main())
