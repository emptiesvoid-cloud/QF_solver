"""Same-mesh Code_Aster TETRA4 correlation for linear TET4 dynamics.

The campaign reuses the checked structural protocol for TET10: a three-
dimensional cantilever, spatial and temporal refinements, then identical
modal, Newmark and harmonic decks in QF_solver and Code_Aster.  It only
covers isotropic small-strain TET4 behaviour without damping, contact or
nonlinearity.
"""

from __future__ import annotations

from pathlib import Path

from solveur.verification.code_aster_tet10_dynamic import CodeAsterTet10DynamicsCampaign


class CodeAsterTet4DynamicsCampaign(CodeAsterTet10DynamicsCampaign):
    """Run the bounded TET4 structural dynamic comparison against Code_Aster."""

    study_id = "VNV-TET4-DYNAMICS-CODEASTER-TETRA4-020"
    element_type = "TET4"
    aster_element_type = "TETRA4"
    gmsh_order = 1
    deck_stem = "tet4_dynamic"
    require_static_spatial_convergence = False

    def __init__(self, output_dir: str | Path, *, mesh_size: float = 0.60) -> None:
        super().__init__(output_dir, mesh_size=mesh_size)
