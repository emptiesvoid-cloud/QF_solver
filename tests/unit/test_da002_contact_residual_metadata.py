from __future__ import annotations

import json

from solveur.core.solvers.static import _contact_solver_metadata


def test_contact_solver_metadata_serializes_unmeasured_residuals_as_null() -> None:
    metadata = _contact_solver_metadata(
        {"method": "frictionless_active_set", "iteration_count": 3, "converged": True}
    )

    assert metadata["residual_norm"] is None
    assert metadata["relative_residual_norm"] is None
    assert metadata["residual_status"] == "NOT_COMPUTABLE"
    serialized = json.loads(json.dumps({"solver": metadata}, allow_nan=False))
    assert serialized["solver"]["residual_norm"] is None
    assert serialized["solver"]["residual_status"] == "NOT_COMPUTABLE"
