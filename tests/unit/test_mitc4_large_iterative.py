from __future__ import annotations

import numpy as np

from mitc4.constants import UZ
from mitc4.material import ShellMaterial
from mitc4.mesh import MeshFactory
from mitc4.model import ShellModel


def test_chunked_scaled_cg_matches_direct_solution() -> None:
    mesh = MeshFactory.rectangular_plate(4, 2, 1.0, 0.2)
    model = ShellModel(mesh.nodes, mesh.quads, ShellMaterial(E=70.0e9, nu=0.3, t=0.01))
    for node in np.where(np.isclose(mesh.nodes[:, 0], 0.0))[0]:
        model.fix_node(int(node))
    for node in np.where(np.isclose(mesh.nodes[:, 0], 1.0))[0]:
        model.add_nodal_load(int(node), UZ, -1.0)

    direct = model.solve()
    iterative, diagnostics = model.solve_iterative(chunk_size=2, relative_tolerance=1.0e-10)

    assert diagnostics["method"] == "scaled_cg"
    assert diagnostics["relative_residual"] <= 2.0e-10
    assert np.allclose(iterative, direct, rtol=1.0e-8, atol=1.0e-12)
