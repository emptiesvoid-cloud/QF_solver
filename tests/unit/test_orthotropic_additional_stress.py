from __future__ import annotations

import pytest

from solveur.core.errors import InfrastructureError
from solveur.verification.orthotropic_complex_mesh import OrthotropicComplexMeshFactory


@pytest.mark.parametrize("builder_name", ["edge_notched_coupon", "double_hole_coupon"])
def test_additional_orthotropic_geometry_is_valid(tmp_path, builder_name) -> None:
    factory = OrthotropicComplexMeshFactory()
    builder = getattr(factory, builder_name)
    try:
        case = builder(tmp_path / f"{builder_name}.msh", 0.35)
    except InfrastructureError:
        pytest.skip("Gmsh optional dependency is unavailable.")

    assert case.nodes.shape[1] == 3
    assert case.elements.shape[1] == 4
    assert case.elements.shape[0] > 100
    assert case.fixed_nodes.size > 0
    assert case.loaded_nodes.size > 0
