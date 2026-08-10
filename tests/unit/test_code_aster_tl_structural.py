import numpy as np

from solveur.verification.code_aster_tl_structural import (
    _boundary_nodes,
    code_aster_mesh,
    stress_patch_comm,
)
from solveur.verification.tet4_total_lagrangian_assembly import _structured_tet4_mesh


def test_code_aster_tl_inputs_are_deterministic() -> None:
    nodes, elements = _structured_tet4_mesh(2, 1, 1, 2.0, 1.0, 0.75)
    boundary = _boundary_nodes(nodes, 2.0, 1.0, 0.75)
    mesh = code_aster_mesh(nodes, elements, boundary)
    commands = stress_patch_comm(nodes, boundary, np.eye(3))
    assert "TETRA4" in mesh
    assert "GROUP_MA\nSOLID" in mesh
    assert 'DEFORMATION="GREEN_LAGRANGE"' in commands
    assert "SIEF_ELGA" in commands
