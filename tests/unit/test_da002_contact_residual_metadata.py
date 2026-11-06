from __future__ import annotations

import json

from solveur.core.solvers.static import _contact_solver_metadata
from solveur.io.audit_markdown import AuditMarkdownWriter


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



def test_contact_residual_status_is_visible_in_markdown_without_fabricating_a_value() -> None:
    metadata = _contact_solver_metadata(
        {"method": "frictionless_active_set", "iteration_count": 3, "converged": True}
    )

    rendered = AuditMarkdownWriter().render({}, solver=metadata)

    assert "| Residu final | None |" in rendered
    assert "| Statut residu | NOT_COMPUTABLE |" in rendered
