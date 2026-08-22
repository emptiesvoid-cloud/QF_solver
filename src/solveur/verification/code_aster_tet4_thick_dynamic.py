"""Code_Aster dynamic correlation for a second TET4 geometry.

This case keeps the same material and loading protocol as the reference
cantilever but changes the aspect ratio. It is a complementary structural
case, not a claim for arbitrary solid geometries.
"""

from __future__ import annotations

from pathlib import Path

from solveur.verification.code_aster_tet4_dynamic import CodeAsterTet4DynamicsCampaign


class CodeAsterTet4ThickDynamicsCampaign(CodeAsterTet4DynamicsCampaign):
    """Run a short, thick TET4 cantilever against Code_Aster TETRA4."""

    study_id = "VNV-TET4-DYNAMICS-CODEASTER-TETRA4-SECOND-GEOMETRY-021"

    def __init__(self, output_dir: str | Path, *, mesh_size: float = 0.24) -> None:
        super().__init__(
            output_dir,
            mesh_size=mesh_size,
            length=2.4,
            width=0.8,
            height=0.6,
        )

    def _spatial_mesh_sizes(self) -> tuple[float, float, float, float, float]:
        """Use levels that remain ordered for the thicker geometry."""
        return (0.40, self.mesh_size, 0.16, 0.10, 0.06)
