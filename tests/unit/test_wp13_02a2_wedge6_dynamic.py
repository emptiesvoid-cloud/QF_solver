"""Focused WP13-02A2 checks for the experimental WEDGE6 dynamic enablement."""

from __future__ import annotations

import numpy as np
from scipy.linalg import eigh

from solveur import solve_model
from solveur.compatibility import check_compatibility, preflight_model
from solveur.core.assembly.assembler import GlobalAssembler
from solveur.core.model import FiniteElementModel


NODES = [
    [0.0, 0.0, 0.0],
    [2.0, 0.0, 0.0],
    [0.0, 1.0, 0.0],
    [0.0, 0.0, 1.0],
    [2.0, 0.0, 1.0],
    [0.0, 1.0, 1.0],
]
MATERIALS = {"steel": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3, "density": 7800.0}}
FIXED = [{"node": index, "dofs": ["UX", "UY", "UZ"]} for index in range(3)]


def _model(analysis: dict[str, object]) -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        nodes=NODES,
        elements=[{"type": "WEDGE6", "nodes": list(range(6)), "material": "steel"}],
        materials=MATERIALS,
        fixed_dofs=FIXED,
        loads=[{"node": 4, "dof": "UZ", "value": 1.0}],
        analysis=analysis,
        units={"system": "SI"},
    )


def test_wedge6_dynamic_routes_are_experimental_and_fail_closed() -> None:
    assert check_compatibility("WEDGE6", "newmark_transient", "elastic").status == "EXPERIMENTAL_ROUTE"
    assert check_compatibility("WEDGE6", "harmonic", "elastic").status == "EXPERIMENTAL_ROUTE"
    newmark = _model({"type": "transient_dynamic", "method": "newmark", "time_step": 1.0e-5, "steps": 1})
    harmonic = _model({"type": "harmonic_response", "method": "direct_frequency", "frequencies_hz": [0.0]})
    assert preflight_model(newmark).status == "EXPERIMENTAL_ROUTE"
    assert preflight_model(harmonic).status == "EXPERIMENTAL_ROUTE"
    assert preflight_model(newmark).ok
    assert preflight_model(harmonic).ok


def test_wedge6_consistent_km_and_modal_route_remain_unchanged() -> None:
    model = _model({"type": "linear_static"})
    dofs = model.dof_manager()
    stiffness, mass, _, _ = GlobalAssembler().assemble_stiffness_and_mass(model, dofs)
    fixed = GlobalAssembler().fixed_indices(model, dofs)
    free = np.setdiff1d(np.arange(dofs.ndof), fixed)
    kff = stiffness.toarray()[np.ix_(free, free)]
    mff = mass.toarray()[np.ix_(free, free)]
    values, _ = eigh(kff, mff)
    assert np.allclose(stiffness.toarray(), stiffness.toarray().T, rtol=1.0e-12, atol=1.0e-5)
    assert np.allclose(mass.toarray(), mass.toarray().T, rtol=1.0e-12, atol=1.0e-12)
    assert float(np.linalg.eigvalsh(mff).min()) > 0.0
    assert np.all(values > 0.0)


def test_wedge6_micro_routes_execute_without_policy_promotion() -> None:
    transient = _model(
        {
            "type": "transient_dynamic",
            "method": "newmark",
            "time_step": 1.0e-5,
            "steps": 2,
            "newmark_beta": 0.25,
            "newmark_gamma": 0.5,
            "postprocess_mode": "summary",
        }
    )
    harmonic = _model(
        {
            "type": "harmonic_response",
            "method": "direct_frequency",
            "frequencies_hz": [0.0, 1.0],
            "rayleigh_alpha": 0.0,
            "rayleigh_beta": 0.0,
        }
    )
    transient_result = solve_model(transient, enforce_policy=False)
    harmonic_result = solve_model(harmonic, enforce_policy=False)
    assert transient_result.status == "PASS"
    assert harmonic_result.status == "PASS"
    assert np.isfinite(transient_result.displacements).all()
    assert all(np.isfinite(response).all() for response in harmonic_result.responses)
