from __future__ import annotations

from dataclasses import replace

import pytest

from solveur.core.nonlinear.load_control import _MaterialLoadControlContribution
from solveur.core.nonlinear.material_state import initial_material_states
from solveur.verification.robustness_mesh import _refinement_model


@pytest.mark.parametrize(("option", "expected"), [(True, True), (False, False), (None, False)])
def test_material_load_control_enables_guard_diagnostics_only_for_true_opt_in(
    option: bool | None, expected: bool
) -> None:
    base = _refinement_model("TET4", 1)
    parameters = dict(base.analysis.parameters)
    if option is None:
        parameters.pop("corotational_guard_diagnostics", None)
    else:
        parameters["corotational_guard_diagnostics"] = option
    model = replace(base, analysis=replace(base.analysis, parameters=parameters))
    contribution = _MaterialLoadControlContribution(
        object(), model, model.dof_manager(), {}, {}, initial_material_states(model)
    )

    assert contribution.corotational_guard_diagnostics_enabled is expected
