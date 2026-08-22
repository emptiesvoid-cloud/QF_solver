from __future__ import annotations

import numpy as np
import pytest

from solveur.api import generate_large_tet4_cantilever, inspect_large_model, load_large_model
from solveur.verification.tet4_structured_convergence import (
    StructuredTet4ConvergencePlan,
    observed_orders,
    relative_error,
    richardson_extrapolation,
    timoshenko_tip_displacement,
)


def test_nested_plan_has_deterministic_levels() -> None:
    plan = StructuredTet4ConvergencePlan(refinement_factors=(1, 2, 4))
    assert [(level.nx, level.ny, level.nz) for level in plan.levels] == [(20, 4, 4), (40, 8, 8), (80, 16, 16)]
    assert [level.element_count for level in plan.levels] == [1920, 15360, 122880]
    assert plan.to_dict()["nested"] is True


def test_plan_rejects_non_nested_refinement() -> None:
    with pytest.raises(ValueError, match="nested"):
        StructuredTet4ConvergencePlan(refinement_factors=(1, 2, 3))


def test_centered_plan_and_surface_load_are_traceable(tmp_path) -> None:
    plan = StructuredTet4ConvergencePlan(
        base_nx=2,
        base_ny=1,
        base_nz=1,
        refinement_factors=(1, 2),
        decomposition="centered",
        load_distribution="surface_consistent",
    )
    assert [level.element_count for level in plan.levels] == [24, 192]
    assert plan.to_dict()["decomposition"] == "centered"
    level = plan.levels[0]
    assert level.node_count == (level.nx + 1) * (level.ny + 1) * (level.nz + 1) + level.nx * level.ny * level.nz
    assert level.ndof == 3 * level.node_count
    path = tmp_path / "centered.h5"
    generated = generate_large_tet4_cantilever(
        path,
        nx=2,
        ny=1,
        nz=1,
        decomposition="centered",
        load_distribution="surface_consistent",
        total_load=-12.0,
    )
    model = load_large_model(path)
    assert generated.element_count == 24
    assert model.analysis["large_model"]["tetrahedra_per_cell"] == 12
    assert np.all(model.load_components == 2)
    assert np.isclose(np.sum(model.load_values), -12.0)
    assert inspect_large_model(model).details["tet4_quality"]["invalid_volume_count"] == 0


def test_surface_consistent_face_load_has_no_diagonal_bias(tmp_path) -> None:
    path = tmp_path / "surface_load.h5"
    generate_large_tet4_cantilever(
        path,
        nx=1,
        ny=2,
        nz=2,
        load_distribution="surface_consistent",
        total_load=-16.0,
    )
    model = load_large_model(path)
    values = model.load_values.reshape((3, 3))
    # Uniform pressure integrated with bilinear face shape functions gives
    # tensor-product tributary weights on this regular rectangular face.
    expected = np.array(
        [[1.0, 2.0, 1.0], [2.0, 4.0, 2.0], [1.0, 2.0, 1.0]],
        dtype=float,
    )
    assert np.allclose(values, -16.0 * expected / expected.sum())


def test_structured_study_rejects_unknown_backend(tmp_path) -> None:
    from solveur.verification.tet4_structured_convergence import run_structured_tet4_study

    with pytest.raises(ValueError, match="solver_backend"):
        run_structured_tet4_study(tmp_path / "invalid", solver_backend="direct")


def test_cantilever_generator_uses_transverse_tributary_loads(tmp_path) -> None:
    path = tmp_path / "cantilever.h5"
    generated = generate_large_tet4_cantilever(path, nx=2, ny=2, nz=2, total_load=-12.0)
    model = load_large_model(path)

    assert generated.analysis["large_model"]["load_component"] == 2
    assert generated.analysis["large_model"]["load_distribution"] == "tributary"
    assert np.all(model.load_components == 2)
    assert np.isclose(np.sum(model.load_values), -12.0)
    audit = inspect_large_model(model)
    assert audit.status in {"PASS", "WARNING"}
    assert audit.details["tet4_quality"]["invalid_volume_count"] == 0


def test_timoshenko_reference_and_convergence_metrics() -> None:
    reference = timoshenko_tip_displacement(-1.0, 4.0, 0.4, 0.4, 70.0e9, 0.3)
    assert np.isclose(reference, -1.4397142857142855e-7)
    assert np.isclose(relative_error(-1.0, -2.0), 0.5)
    orders = observed_orders((0.32, 0.08, 0.02), (1.0, 0.5, 0.25))
    assert all(order > 1.0 for order in orders)
    extrapolated = richardson_extrapolation(1.0, 1.25, 2.0, 2.0)
    assert np.isclose(extrapolated, 1.3333333333333333)
