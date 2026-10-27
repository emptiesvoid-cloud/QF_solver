from types import SimpleNamespace

import numpy as np
import pytest

from solveur.core.errors import InputValidationError
from solveur.core.analyses.prepared_dynamic_system import _validate_admissible_model
from solveur.mesh.mixed_validation import mixed_modal_scope_errors


_CONSTRAINT_CASES = (
    pytest.param("multipoint_constraints", id="mpc"),
    pytest.param("rbe2", id="rbe2"),
    pytest.param("rbe3", id="rbe3"),
)


def _mixed_model(analysis_type: str, constraint_field: str) -> SimpleNamespace:
    model = SimpleNamespace(
        analysis=SimpleNamespace(
            type=analysis_type,
            parameters={"required_mixed_families": ["TET4", "WEDGE6"]},
        ),
        nodes=np.asarray(
            [
                [0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
                [0.0, 0.0, -1.0],
                [1.0, 0.0, -1.0],
                [0.0, 1.0, -1.0],
            ]
        ),
        elements=[
            SimpleNamespace(type="TET4", nodes=(0, 1, 2, 3)),
            SimpleNamespace(type="WEDGE6", nodes=(0, 1, 2, 4, 5, 6)),
        ],
        multipoint_constraints=[],
        rbe2=[],
        rbe3=[],
    )
    setattr(model, constraint_field, [object()])
    return model


@pytest.mark.parametrize("constraint_field", _CONSTRAINT_CASES)
def test_mixed_modal_scope_rejects_mpc_rbe_coupling(constraint_field: str) -> None:
    errors = mixed_modal_scope_errors(_mixed_model("modal", constraint_field))

    assert "Mixed modal scope rejects MPC/RBE coupling; only the bounded linear_static translation-only route is enabled." in errors


@pytest.mark.parametrize("analysis_type", ["modal", "transient_dynamic", "harmonic_response"], ids=["modal", "transient", "harmonic"])
@pytest.mark.parametrize("constraint_field", _CONSTRAINT_CASES)
def test_dynamic_preparation_rejects_mpc_rbe_coupling(analysis_type: str, constraint_field: str) -> None:
    model = SimpleNamespace(
        analysis=SimpleNamespace(type=analysis_type),
        elements=[SimpleNamespace(type="TET4")],
        multipoint_constraints=[],
        rbe2=[],
        rbe3=[],
        contacts=[],
    )
    setattr(model, constraint_field, [object()])

    with pytest.raises(InputValidationError, match="PreparedDynamicSystem does not support MPC/RBE constraints"):
        _validate_admissible_model(model)
