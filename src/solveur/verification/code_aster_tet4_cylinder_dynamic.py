"""Code_Aster dynamic correlation for a circular TET4 cantilever."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from solveur.benchmarks.gmsh_factory import BenchmarkMeshFactory
from solveur.core.model import FiniteElementModel
from solveur.io.manifest import write_json_file
from solveur.mesh.gmsh_importer import GmshModelImporter
from solveur.verification.code_aster_tet4_dynamic import CodeAsterTet4DynamicsCampaign


class CodeAsterTet4CylinderDynamicsCampaign(CodeAsterTet4DynamicsCampaign):
    """Run a circular-shaft TET4 cantilever against Code_Aster TETRA4."""

    study_id = "VNV-TET4-DYNAMICS-CODEASTER-TETRA4-CYLINDER-022"
    geometry_label = "circular-shaft cantilever"

    def __init__(self, output_dir: str | Path, *, mesh_size: float = 0.25) -> None:
        super().__init__(
            output_dir,
            mesh_size=mesh_size,
            length=2.4,
            width=0.8,
            height=0.8,
        )

    def _spatial_mesh_sizes(self) -> tuple[float, float, float, float]:
        """Use ordered levels for the circular shaft."""
        return (0.40, self.mesh_size, 0.17, 0.12)

    def _model(
        self,
        mesh_size: float,
        analysis: str | dict[str, Any],
        *,
        total_load: float = 0.0,
    ) -> tuple[FiniteElementModel, np.ndarray, np.ndarray]:
        mesh = BenchmarkMeshFactory().cylinder_tetra(
            self.output_dir / "meshes" / f"tet4_cylinder_h_{mesh_size:.3f}.msh",
            length=self.length,
            radius=0.4,
            mesh_size=mesh_size,
            order=1,
        )
        setup_path = mesh.with_suffix(".setup.json")
        write_json_file(setup_path, self._mesh_setup())
        imported = GmshModelImporter().import_model(mesh, setup_path).model
        root = np.flatnonzero(np.isclose(imported.nodes[:, 0], 0.0, atol=1.0e-10))
        tip = np.flatnonzero(np.isclose(imported.nodes[:, 0], self.length, atol=1.0e-10))
        if not root.size or not tip.size:
            raise RuntimeError("Circular TET4 mesh has no complete root or tip node group.")
        elements = [
            {"type": element.type, "nodes": list(element.nodes), "material": element.material}
            for element in imported.elements
        ]
        model = FiniteElementModel.from_raw(
            nodes=imported.nodes.tolist(),
            elements=elements,
            materials=imported.materials,
            fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in root],
            loads=self._tip_loads(imported.nodes, imported.elements, tip, total_load),
            analysis=analysis,
            verification_profile="quick",
        )
        return model, root, tip
