from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import numpy as np
import pytest

from scripts.run_wp10_tet10_surface_m1 import (
    CONTRACT,
    LEVEL_CELLS,
    REFERENCE_RESULTANT,
    _boundary_surface_loads,
    _load_metadata,
    _model,
)


def test_contract_freezes_consistent_traction_hierarchy() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert contract["status"] == "M1_REQUALIFICATION_AUTHORIZED"
    assert contract["element"] == "TET10"
    assert contract["hierarchy"]["H1"]["cells_x"] == 1
    assert contract["hierarchy"]["H2"]["cells_x"] == 2
    assert contract["hierarchy"]["H3"]["cells_x"] == 4
    assert contract["load"]["reference_resultant"] == [REFERENCE_RESULTANT, 0.0, 0.0]


@pytest.mark.parametrize("level,cells", LEVEL_CELLS.items())
def test_x1_boundary_load_is_consistent_and_balanced(level: str, cells: int) -> None:
    model, surface = _model(cells)
    metadata = _load_metadata(model)
    assert surface["face_count"] == 2
    assert surface["total_area"] == pytest.approx(1.0)
    assert metadata["resultant"] == pytest.approx([REFERENCE_RESULTANT, 0.0, 0.0])
    assert metadata["resultant_error_norm"] == pytest.approx(0.0, abs=1.0e-14)
    assert len(model.distributed_loads) == 2
    assert not model.loads


def test_surface_load_face_discovery_is_unique() -> None:
    from solveur.verification.robustness_mesh import mesh_refinement_mesh

    nodes, elements = mesh_refinement_mesh("TET10", 4)
    loads, metadata = _boundary_surface_loads(nodes, elements)
    assert len(loads) == cast(int, metadata["face_count"]) == 2
    assert len({(item["element"], item["face"]) for item in loads}) == 2
    assert np.isfinite(cast(float, metadata["traction_magnitude"]))
