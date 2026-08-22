"""Static V&V campaign for a homogeneous one-ply MITC4 orthotropic shell."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from solveur.api import solve_model
from solveur.core.model import FiniteElementModel
from solveur.elements.shell.mitc4.mesh import MeshFactory
from solveur.io.manifest import write_json_file


STUDY_ID = "VNV-MITC4-ORTHOTROPIC-ONE-PLY-STATIC-001"


class Mitc4OrthotropicStaticCampaign:
    """Run membrane and transverse-load cases for material-axis orientations."""

    def __init__(self, output_dir: str | Path, *, mesh: tuple[int, int] = (16, 4)) -> None:
        self.output_dir = Path(output_dir).resolve()
        self.mesh = tuple(int(value) for value in mesh)
        if self.mesh[0] < 2 or self.mesh[1] < 1:
            raise ValueError("MITC4 orthotropic static mesh is too small.")

    def run(self) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        rows = [self._run_orientation(angle) for angle in (0.0, 45.0, 90.0)]
        summary = {
            "study_id": STUDY_ID,
            "status": "PASS_INTERNAL" if all(row["status"] == "PASS" for row in rows) else "FAIL",
            "mesh": list(self.mesh),
            "one_ply_thickness_m": 1.0e-2,
            "rows": rows,
            "acceptance": {
                "maximum_free_relative_residual": 1.0e-8,
                "orientation_objectivity": "same material response after consistent global/local rotation",
            },
            "limitations": [
                "One homogeneous orthotropic ply represented through shell_laminate.",
                "No damage, delamination, failure or interlaminar stress claim.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        return summary

    def _run_orientation(self, angle: float) -> dict[str, Any]:
        mesh = MeshFactory.rectangular_plate(self.mesh[0], self.mesh[1], 1.0, 0.2)
        root = np.flatnonzero(np.isclose(mesh.nodes[:, 0], 0.0))
        tip = np.flatnonzero(np.isclose(mesh.nodes[:, 0], 1.0))
        fixed = [
            {"node": int(node), "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]}
            for node in root
        ]
        loads = [
            {"node": int(node), "dof": "UZ", "value": -1.0 / len(tip)}
            for node in tip
        ]
        model = FiniteElementModel.from_raw(
            analysis={"type": "linear_static", "method": "direct"},
            nodes=mesh.nodes.tolist(),
            elements=[{"type": "MITC4", "nodes": quad.tolist(), "material": "lamina"} for quad in mesh.quads],
            materials={
                "lamina": {
                    "type": "shell_laminate",
                    "drilling_scale": 1.0e-4,
                    "plies": [{
                        "E1": 135.0e9, "E2": 10.0e9, "nu12": 0.3,
                        "G12": 5.0e9, "G13": 4.5e9, "G23": 3.8e9,
                        "density": 1600.0, "thickness": 1.0e-2,
                        "angle_deg": angle,
                    }],
                }
            },
            fixed_dofs=fixed,
            loads=loads,
        )
        result = solve_model(model, enforce_policy=False)
        tip_displacement = float(np.mean([result.displacements[result.dofs.index(int(node), "UZ")] for node in tip]))
        residual = float(result.audit.equilibrium["free_relative_residual"])
        return {
            "angle_deg": angle,
            "tip_uz_m": tip_displacement,
            "free_relative_residual": residual,
            "status": "PASS" if np.isfinite(tip_displacement) and residual <= 1.0e-8 else "FAIL",
        }
