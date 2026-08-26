from __future__ import annotations

import numpy as np
import pytest

from solveur.core.errors import InputValidationError
from solveur.core.nonlinear_assembly import (
    assemble_internal_tangent,
    build_nonlinear_assembly_plan,
)
from tests.unit.test_analysis_features import nonlinear_tet4_model


def test_nonlinear_assembly_plan_reuses_kernels_without_reusing_states() -> None:
    model = nonlinear_tet4_model()
    dofs = model.dof_manager()
    displacement = np.zeros(dofs.ndof, dtype=float)
    plan = build_nonlinear_assembly_plan(model, dofs)
    first_timing: dict[str, float | int] = {}
    second_timing: dict[str, float | int] = {}

    first = assemble_internal_tangent(
        model,
        dofs,
        displacement,
        timing=first_timing,
        plan=plan,
    )
    second = assemble_internal_tangent(
        model,
        dofs,
        displacement,
        timing=second_timing,
        plan=plan,
    )

    assert plan.matches(model, dofs)
    assert first_timing["element_cache_hits"] == 1
    assert first_timing["element_cache_misses"] == 0
    assert second_timing["element_cache_hits"] == 1
    assert second_timing["element_cache_misses"] == 0
    assert np.allclose(first[0], second[0])
    assert (first[1] - second[1]).nnz == 0
    assert first[2] == second[2] == {}


def test_nonlinear_assembly_without_plan_preserves_uncached_contract() -> None:
    model = nonlinear_tet4_model()
    dofs = model.dof_manager()
    timing: dict[str, float | int] = {}

    assemble_internal_tangent(
        model,
        dofs,
        np.zeros(dofs.ndof, dtype=float),
        timing=timing,
    )

    assert timing["element_cache_hits"] == 0
    assert timing["element_cache_misses"] == 1


def test_nonlinear_sparse_tangent_assembly_is_chunked_and_sparse() -> None:
    model = nonlinear_tet4_model()
    model.analysis.parameters["nonlinear_assembly_chunk_size"] = 1
    dofs = model.dof_manager()
    timing: dict[str, float | int] = {}

    _, tangent, _ = assemble_internal_tangent(
        model,
        dofs,
        np.zeros(dofs.ndof, dtype=float),
        timing=timing,
    )

    assert tangent.nnz > 0
    assert timing["sparse_chunk_count"] == 1
    assert timing["sparse_peak_chunk_entries"] == 144
    assert timing["sparse_peak_chunk_bytes_estimate"] == 6912
    assert timing["sparse_accumulator_levels"] == 1


def test_nonlinear_sparse_chunk_size_rejects_invalid_values() -> None:
    model = nonlinear_tet4_model()
    model.analysis.parameters["nonlinear_assembly_chunk_size"] = 0

    with pytest.raises(InputValidationError, match="nonlinear_assembly_chunk_size"):
        assemble_internal_tangent(model, model.dof_manager(), np.zeros(model.dof_manager().ndof))
