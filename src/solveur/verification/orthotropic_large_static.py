"""Verification campaign for the large-scale orthotropic TET4 static path."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import h5py
import numpy as np

from solveur.api import solve_model
from solveur.core.model import FiniteElementModel
from solveur.io.manifest import write_json_file
from solveur.large.generator import generate_tet4_block
from solveur.large.io import load_large_model, save_large_model
from solveur.large.solver import solve_large_model
from solveur.verification.vnv_manifest import write_vnv_manifest


ORTHOTROPIC_MATERIAL: dict[str, Any] = {
    "type": "orthotropic_3d",
    "E1": 145.0e9,
    "E2": 12.0e9,
    "E3": 9.0e9,
    "nu12": 0.24,
    "nu13": 0.21,
    "nu23": 0.28,
    "G12": 5.5e9,
    "G13": 4.8e9,
    "G23": 3.9e9,
    "density": 1580.0,
    "e1": [2.0**-0.5, 2.0**-0.5, 0.0],
    "e2_hint": [-(2.0**-0.5), 2.0**-0.5, 0.0],
}


class OrthotropicLargeStaticCampaign:
    """Compare standard and large-scale paths on one homogeneous TET4 model."""

    study_id = "VNV-ORTHOTROPIC-LARGE-STATIC-008"

    def __init__(self, output_dir: str | Path, *, nx: int = 8, ny: int = 4, nz: int = 3) -> None:
        self.output_dir = Path(output_dir).resolve()
        self.nx, self.ny, self.nz = int(nx), int(ny), int(nz)
        if min(self.nx, self.ny, self.nz) <= 0:
            raise ValueError("Orthotropic large-static dimensions must be positive.")

    def run(self) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        model_path = self.output_dir / "model.h5"
        generated = generate_tet4_block(
            model_path,
            nx=self.nx,
            ny=self.ny,
            nz=self.nz,
            material=ORTHOTROPIC_MATERIAL,
        )
        analysis = {
            "type": "linear_static",
            "method": "cg",
            "parameters": {"rtol": 1.0e-10, "atol": 0.0, "max_it": 20_000},
            "large_model": dict(generated.analysis.get("large_model", {})),
        }
        model = replace(generated, analysis=analysis)
        save_large_model(model, model_path)

        large_path = self.output_dir / "large_scipy"
        large_result = solve_large_model(
            load_large_model(model_path),
            large_path,
            solver_backend="scipy",
            preconditioner="jacobi",
            parameters={"method": "cg", "rtol": 1.0e-10, "max_it": 20_000},
        )
        matrix_free_path = self.output_dir / "large_matrix_free"
        matrix_free_result = solve_large_model(
            load_large_model(model_path),
            matrix_free_path,
            solver_backend="matrix_free",
            parameters={"rtol": 1.0e-10, "max_it": 20_000},
        )
        standard_result = solve_model(_standard_model(model), enforce_policy=False)
        large_displacement = _read_displacement(large_path / "displacements.h5")
        matrix_free_displacement = _read_displacement(matrix_free_path / "displacements.h5")
        standard_displacement = standard_result.displacements.reshape((-1, 3))
        large_standard_error = _relative_difference(large_displacement, standard_displacement)
        matrix_free_error = _relative_difference(matrix_free_displacement, large_displacement)
        solution = large_result.audit.details.get("solution", {})
        energy_work_error = abs(float(solution.get("strain_energy", 0.0)) * 2.0 - float(solution.get("external_work", 0.0)))
        energy_work_error /= max(abs(float(solution.get("external_work", 0.0))), 1.0e-30)

        checks = [
            _status_check("large_scipy_status", large_result.status == "PASS"),
            _status_check("large_audit_status", large_result.audit.status == "PASS"),
            _status_check("matrix_free_status", matrix_free_result.status == "PASS"),
            _status_check("standard_status", standard_result.status == "PASS"),
            _upper_check("large_vs_standard_displacement", large_standard_error, 1.0e-9),
            _upper_check("matrix_free_vs_assembled_displacement", matrix_free_error, 1.0e-7),
            _upper_check("energy_work_relative_error", energy_work_error, 1.0e-8),
            _status_check("finite_large_displacement", bool(np.all(np.isfinite(large_displacement)))),
        ]
        passed = all(item["status"] == "PASS" for item in checks)
        summary: dict[str, Any] = {
            "study_id": self.study_id,
            "status": "PASS_TECHNICAL_VERIFICATION" if passed else "FAIL",
            "maturity": "experimental",
            "scope": "linear_static / homogeneous orthotropic 3D / TET4 / large-model array path",
            "model": {
                "nx": self.nx,
                "ny": self.ny,
                "nz": self.nz,
                "nodes": generated.node_count,
                "elements": generated.element_count,
                "dofs": generated.ndof,
                "material": ORTHOTROPIC_MATERIAL,
            },
            "large_scipy": large_result.summary,
            "matrix_free": matrix_free_result.summary,
            "standard_solver": {
                "status": standard_result.status,
                "method": standard_result.method,
                "max_displacement": standard_result.max_displacement,
            },
            "comparisons": {
                "large_vs_standard_displacement_relative_error": large_standard_error,
                "matrix_free_vs_assembled_displacement_relative_error": matrix_free_error,
                "energy_work_relative_error": energy_work_error,
            },
            "checks": checks,
            "limitations": [
                "The campaign uses a homogeneous constant material orientation; orientation_field remains unsupported.",
                "The comparison is an internal independent-path verification, not an external Code_Aster correlation.",
                "This bounded case does not qualify orthotropic million-DOF performance.",
                "The scope remains experimental until a dedicated Owner review accepts its evidence and limits.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        (self.output_dir / "report.md").write_text(_markdown(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary


def _standard_model(model: Any) -> FiniteElementModel:
    fixed_by_node: dict[int, list[str]] = {}
    names = ("UX", "UY", "UZ")
    for node, component in zip(model.fixed_nodes, model.fixed_components):
        fixed_by_node.setdefault(int(node), []).append(names[int(component)])
    loads = [
        {"node": int(node), "dof": names[int(component)], "value": float(value)}
        for node, component, value in zip(model.load_nodes, model.load_components, model.load_values)
    ]
    return FiniteElementModel.from_raw(
        nodes=model.nodes.tolist(),
        elements=[
            {"type": "TET4", "nodes": connectivity.tolist(), "material": "solid"}
            for connectivity in model.tet4
        ],
        materials={"solid": dict(ORTHOTROPIC_MATERIAL)},
        fixed_dofs=[{"node": node, "dofs": dofs} for node, dofs in sorted(fixed_by_node.items())],
        loads=loads,
        analysis={"type": "linear_static", "method": "direct"},
        units={"system": "SI"},
        verification_profile="engineering",
    )


def _read_displacement(path: Path) -> np.ndarray:
    with h5py.File(path, "r") as handle:
        return np.asarray(handle["displacements"], dtype=float)


def _relative_difference(candidate: np.ndarray, reference: np.ndarray) -> float:
    return float(np.linalg.norm(candidate - reference) / max(float(np.linalg.norm(reference)), 1.0e-30))


def _status_check(identifier: str, passed: bool) -> dict[str, Any]:
    return {"id": identifier, "status": "PASS" if passed else "FAIL", "value": bool(passed)}


def _upper_check(identifier: str, value: float, limit: float) -> dict[str, Any]:
    return {"id": identifier, "status": "PASS" if value <= limit else "FAIL", "value": value, "limit": limit}


def _markdown(summary: dict[str, Any]) -> str:
    comparisons = summary["comparisons"]
    checks = summary["checks"]
    lines = [
        f"# {summary['study_id']}",
        "",
        f"Verdict technique : **{summary['status']}**.",
        "",
        "Cette campagne compare le chemin standard, l'assembleur large SciPy et le chemin matrix-free sur le même modèle TET4 orthotrope.",
        "",
        "| Grandeur | Valeur | Limite |",
        "| --- | ---: | ---: |",
        f"| Ecart deplacement large / standard | {comparisons['large_vs_standard_displacement_relative_error']:.3e} | 1.0e-9 |",
        f"| Ecart deplacement matrix-free / assemble | {comparisons['matrix_free_vs_assembled_displacement_relative_error']:.3e} | 1.0e-7 |",
        f"| Erreur energie interne / travail externe | {comparisons['energy_work_relative_error']:.3e} | 1.0e-8 |",
        "",
        "| Check | Statut |",
        "| --- | --- |",
    ]
    lines.extend(f"| {item['id']} | {item['status']} |" for item in checks)
    lines.extend(
        [
            "",
            "## Limites",
            "",
            *[f"- {item}" for item in summary["limitations"]],
            "",
            "La preuve est technique et reproductible; elle ne constitue pas une qualification externe.",
        ]
    )
    return "\n".join(lines) + "\n"
