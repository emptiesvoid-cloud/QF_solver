"""External TET10 Newmark/harmonic correlation with declared damping."""

from __future__ import annotations

from pathlib import Path

from solveur.verification.code_aster_tet10_cylinder_dynamic import (
    CodeAsterTet10CylinderDynamicsCampaign,
)


class CodeAsterTet10DampedCylinderDynamicsCampaign(
    CodeAsterTet10CylinderDynamicsCampaign
):
    """Compare a circular TET10 shaft with 2 percent mass-Rayleigh damping."""

    study_id = "VNV-TET10-DYNAMICS-DAMPED-CODEASTER-TETRA10-CYLINDER-024"
    damping_ratio = 0.02

    def __init__(self, output_dir: str | Path, *, mesh_size: float = 0.32) -> None:
        super().__init__(output_dir, mesh_size=mesh_size)

