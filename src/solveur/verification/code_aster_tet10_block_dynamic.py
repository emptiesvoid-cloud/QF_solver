"""Same-mesh TET10 dynamic correlation for a non-cantilever block load path."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from solveur.benchmarks.gmsh_factory import BenchmarkMeshFactory
from solveur.core.model import FiniteElementModel
from solveur.io.manifest import write_json_file
from solveur.mesh.gmsh_importer import GmshModelImporter
from solveur.verification.code_aster_tet10_dynamic import (
    CodeAsterTet10DynamicsCampaign,
)


class CodeAsterTet10BlockDynamicsCampaign(CodeAsterTet10DynamicsCampaign):
    """Compare a bottom-clamped block loaded on its top face with Code_Aster."""

    study_id = "VNV-TET10-DYNAMICS-CODEASTER-TETRA10-BLOCK-025"
    geometry_label = "bottom-clamped block under top-face load"

    def __init__(self, output_dir: str | Path, *, mesh_size: float = 0.32) -> None:
        super().__init__(
            output_dir,
            mesh_size=mesh_size,
            length=1.0,
            width=1.0,
            height=1.0,
        )

    def _spatial_mesh_sizes(self) -> tuple[float, float, float, float]:
        """Use four ordered levels for the non-cantilever path."""
        return (0.50, self.mesh_size, 0.24, 0.18)

    def _model(
        self,
        mesh_size: float,
        analysis: str | dict[str, Any],
        *,
        total_load: float = 0.0,
    ) -> tuple[FiniteElementModel, np.ndarray, np.ndarray]:
        mesh = BenchmarkMeshFactory().box_tetra(
            self.output_dir / "meshes" / f"tet10_block_h_{mesh_size:.3f}.msh",
            length=self.length,
            width=self.width,
            height=self.height,
            mesh_size=mesh_size,
            order=2,
        )
        setup_path = mesh.with_suffix(".setup.json")
        write_json_file(setup_path, self._mesh_setup())
        imported = GmshModelImporter().import_model(mesh, setup_path).model
        root = np.flatnonzero(np.isclose(imported.nodes[:, 2], 0.0, atol=1.0e-10))
        tip = np.flatnonzero(np.isclose(imported.nodes[:, 2], self.height, atol=1.0e-10))
        if not root.size or not tip.size:
            raise RuntimeError("TET10 block mesh has no complete bottom or top node group.")
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

