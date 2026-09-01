from __future__ import annotations

import numpy as np

from scripts.run_wp17_solver_stack import (
    _compare_preconditioners,
    _config,
    _InstrumentedOperator,
    _petsc_availability,
    _reaction_metrics,
)
from solveur.large.generator import generate_tet4_block
from solveur.large.assembler import fixed_dof_indices


def test_wp17_instrumented_operator_counts_matrix_vector_actions(tmp_path) -> None:
    model = generate_tet4_block(tmp_path / "model.h5", nx=1, ny=1, nz=1)
    fixed = fixed_dof_indices(model)
    free = np.setdiff1d(np.arange(model.ndof, dtype=np.int64), fixed)
    operator = _InstrumentedOperator(model, free=free, chunk_size=4096)

    result = operator @ np.ones(free.size)

    assert result.shape == free.shape
    assert operator.matvec_calls == 1
    assert operator.operator_setup_seconds >= 0.0
    assert operator.block_build_seconds >= 0.0


def test_wp17_reaction_diagnostic_reports_compensated_reduction() -> None:
    residual = np.zeros(9, dtype=float)
    residual[0] = -1.0
    residual[3] = 1.0
    loads = np.zeros(9, dtype=float)
    loads[6] = 1.0
    fixed = np.array([0, 1, 2], dtype=np.int64)

    metrics = _reaction_metrics(residual=residual, loads=loads, fixed=fixed)

    assert set(metrics) >= {
        "numpy_relative",
        "fsum_relative",
        "free_residual_resultant",
        "equilibrium_free_residual_identity_relative",
        "equilibrium_difference_due_to_reduction",
    }
    assert np.isfinite(metrics["numpy_relative"])
    assert np.isfinite(metrics["fsum_relative"])


def test_wp17_preconditioner_comparison_keeps_wp14_reference() -> None:
    block = {
        "status": "PASS",
        "preconditioner": "nodal_block_jacobi",
        "total_seconds": 2.0,
        "iterations": 10.0,
        "spd_contract": True,
    }
    diagonal = {
        "status": "PASS",
        "preconditioner": "diagonal_jacobi",
        "total_seconds": 1.0,
        "iterations": 12.0,
        "spd_contract": True,
    }

    comparison = _compare_preconditioners(block, diagonal)

    assert comparison["selected"] == "nodal_block_jacobi"
    assert comparison["candidate_faster"] is True
    assert comparison["decision"] is True


def test_wp17_config_keeps_frozen_wp14_solver_contract() -> None:
    config = _config("nodal_block_jacobi")

    assert config["solver"] == "CG"
    assert config["chunk_size"] == 4096
    assert config["rtol"] == 1.0e-8
    assert config["atol"] == 0.0
    assert config["max_iterations"] == 10000


def test_wp17_petsc_probe_is_explicit_and_no_fallback() -> None:
    status = _petsc_availability()

    assert status["classification"] in {"AVAILABLE_REPRODUCIBLE", "UNAVAILABLE"}
    assert status["fallback_policy"].startswith("no implicit fallback")
