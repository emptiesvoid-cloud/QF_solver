from __future__ import annotations

import numpy as np
import pytest

from solveur.large.multifamily import (
    SUPPORTED_WP11_FAMILIES,
    assemble_linear_system,
    build_wp11_family_model,
    family_node_count,
    normalize_family,
    solve_linear_system,
)


@pytest.mark.parametrize(
    ("family", "nodes", "dofs"),
    (("TET4", 4, 12), ("HEX8", 8, 24), ("TET10", 10, 30), ("HEX20", 20, 60)),
)
def test_wp11_multifamily_build_and_solve_is_finite(family: str, nodes: int, dofs: int) -> None:
    model = build_wp11_family_model(family)
    system = assemble_linear_system(model)
    displacement, observables = solve_linear_system(system)

    assert model.node_count == nodes
    assert family_node_count(family) == nodes
    assert model.dof_manager().ndof == dofs
    assert displacement.shape == (dofs,)
    assert np.all(np.isfinite(displacement))
    assert observables["finite"] is True
    assert observables["free_residual_relative_l2"] <= 1.0e-10


def test_wp11_multifamily_family_names_are_normalized_and_fail_closed() -> None:
    assert normalize_family("hex8") == "HEX8"
    assert normalize_family(" TET10 ") == "TET10"
    assert set(SUPPORTED_WP11_FAMILIES) == {"TET4", "HEX8", "TET10", "HEX20"}
    with pytest.raises(ValueError, match="Unsupported WP11 family"):
        normalize_family("WEDGE6")


@pytest.mark.parametrize("family", SUPPORTED_WP11_FAMILIES)
def test_wp11_multifamily_has_fixed_and_loaded_faces(family: str) -> None:
    model = build_wp11_family_model(family)
    fixed_nodes = {item.node for item in model.fixed_dofs}
    loaded_nodes = {item.node for item in model.loads}
    assert fixed_nodes
    assert loaded_nodes
    assert fixed_nodes.isdisjoint(loaded_nodes)
    assert sum(float(item.value) for item in model.loads) == pytest.approx(-1000.0)
