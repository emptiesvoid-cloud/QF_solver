from __future__ import annotations

from scripts.run_code_aster_mitc4_modal_10k_vnv import _modal_analysis_parameters


def test_modal_runner_exposes_sparse_method_controls() -> None:
    parameters = _modal_analysis_parameters(
        method="eigsh",
        preconditioner="spilu",
        tolerance=1.0e-8,
        maxiter=120,
        ncv=10,
        shift_hz=1.0,
        lazy_condensation=False,
        inner_rtol=1.0e-7,
        inner_maxiter=1200,
        inner_restart=100,
    )

    assert parameters["method"] == "eigsh"
    assert parameters["lobpcg_preconditioner"] == "spilu"
    assert parameters["arpack_tolerance"] == 1.0e-8
    assert parameters["arpack_maxiter"] == 120
    assert parameters["arpack_ncv"] == 10
    assert parameters["modal_shift_hz"] == 1.0
    assert parameters["lazy_drilling_condensation"] is False
    assert parameters["drilling_mass_tolerance"] == 1.0e-10
    assert parameters["modal_inner_rtol"] == 1.0e-7
    assert parameters["modal_inner_maxiter"] == 1200
    assert parameters["modal_inner_restart"] == 100
