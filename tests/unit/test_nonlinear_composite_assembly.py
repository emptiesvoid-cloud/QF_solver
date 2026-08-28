from __future__ import annotations

import numpy as np
from scipy.sparse import diags

from solveur.core.nonlinear_iteration import CompositeNonlinearAssembly, solve_full_newton


class _LinearContribution:
    def __init__(self, stiffness: list[float]):
        self.matrix = diags(stiffness, format="csr")
        self.ndof = len(stiffness)

    def assemble(self, displacement: np.ndarray, *, tangent_required: bool = True):
        return self.matrix @ displacement, self.matrix if tangent_required else None


def test_composite_assembly_sums_sparse_material_and_geometric_contributions() -> None:
    assembly = CompositeNonlinearAssembly(
        [_LinearContribution([2.0, 3.0]), _LinearContribution([1.0, 1.0])]
    )
    internal, tangent = assembly.assemble(np.asarray([0.5, 0.25]))

    np.testing.assert_allclose(internal, [1.5, 1.0])
    assert tangent is not None
    assert tangent.nnz == 2
    np.testing.assert_allclose(tangent.diagonal(), [3.0, 4.0])


def test_composite_assembly_is_accepted_by_shared_full_newton_driver() -> None:
    assembly = CompositeNonlinearAssembly(
        [_LinearContribution([2.0, 3.0]), _LinearContribution([1.0, 1.0])]
    )
    displacement, diagnostics = solve_full_newton(
        assembly,
        np.asarray([0.0, 4.0]),
        np.asarray([0]),
        increments=2,
        tolerance=1.0e-12,
        max_iterations=5,
    )

    np.testing.assert_allclose(displacement, [0.0, 1.0])
    assert diagnostics["converged"] is True
    assert diagnostics["increments"][-1]["diagnostics"]["backend"] == "scipy.sparse.linalg.spsolve"
