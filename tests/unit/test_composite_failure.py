"""Unit verification of non-degrading composite failure indicators."""

from __future__ import annotations

import numpy as np
import pytest

from solveur.materials.failure import CompositeFailureEvaluator, PlyStrainAllowables, PlyStrengths


@pytest.fixture
def strengths() -> PlyStrengths:
    return PlyStrengths(Xt=1500.0, Xc=1200.0, Yt=50.0, Yc=200.0, S12=75.0)


@pytest.mark.parametrize(
    "stress",
    (
        [1500.0, 0.0, 0.0],
        [-1200.0, 0.0, 0.0],
        [0.0, 50.0, 0.0],
        [0.0, -200.0, 0.0],
        [0.0, 0.0, 75.0],
        [0.0, 0.0, -75.0],
    ),
)
def test_uniaxial_strength_boundaries_have_unit_indices(strengths: PlyStrengths, stress: list[float]):
    maximum = CompositeFailureEvaluator.maximum_stress(np.asarray(stress), strengths)
    hill = CompositeFailureEvaluator.tsai_hill(np.asarray(stress), strengths)
    wu = CompositeFailureEvaluator.tsai_wu(np.asarray(stress), strengths)
    assert maximum.index == pytest.approx(1.0)
    assert hill.index == pytest.approx(1.0)
    assert wu.index == pytest.approx(1.0)
    assert maximum.reserve_factor == pytest.approx(1.0)
    assert hill.reserve_factor == pytest.approx(1.0)
    assert wu.reserve_factor == pytest.approx(1.0)


def test_maximum_stress_selects_tension_and_compression_allowables(strengths: PlyStrengths):
    result = CompositeFailureEvaluator.maximum_stress(np.array([-600.0, 25.0, -15.0]), strengths)
    assert result.components == pytest.approx({"fiber": 0.5, "transverse": 0.5, "shear": 0.2})
    assert result.index == pytest.approx(0.5)
    assert result.reserve_factor == pytest.approx(2.0)
    assert result.margin_of_safety == pytest.approx(1.0)
    assert result.passed


def test_maximum_strain_uses_engineering_shear():
    allowables = PlyStrainAllowables(e1t=0.015, e1c=0.012, e2t=0.005, e2c=0.02, g12=0.03)
    result = CompositeFailureEvaluator.maximum_strain(np.array([0.003, -0.01, 0.012]), allowables)
    assert result.components == pytest.approx({"fiber": 0.2, "transverse": 0.5, "shear": 0.4})
    assert result.index == pytest.approx(0.5)


@pytest.mark.parametrize("criterion", [CompositeFailureEvaluator.tsai_hill, CompositeFailureEvaluator.tsai_wu])
def test_reserve_factor_reaches_quadratic_surface(criterion, strengths: PlyStrengths):
    stress = np.array([320.0, 18.0, 22.0])
    result = criterion(stress, strengths)
    assert result.reserve_factor is not None
    boundary = criterion(stress * result.reserve_factor, strengths)
    assert boundary.index == pytest.approx(1.0, rel=1.0e-12)


def test_tsai_wu_interaction_coefficient_changes_biaxial_index(strengths: PlyStrengths):
    stress = np.array([300.0, 20.0, 0.0])
    default = CompositeFailureEvaluator.tsai_wu(stress, strengths)
    uncoupled = CompositeFailureEvaluator.tsai_wu(
        stress,
        PlyStrengths(1500.0, 1200.0, 50.0, 200.0, 75.0, f12_star=0.0),
    )
    assert default.components["F12"] < 0.0
    assert default.index < uncoupled.index


def test_evaluate_reports_all_configured_criteria(strengths: PlyStrengths):
    allowables = PlyStrainAllowables(0.015, 0.012, 0.005, 0.02, 0.03)
    results = CompositeFailureEvaluator.evaluate(
        np.array([100.0, 10.0, 5.0]),
        np.array([1.0e-3, 2.0e-3, 3.0e-3]),
        strengths,
        allowables,
    )
    assert [result.criterion for result in results] == [
        "maximum_stress",
        "maximum_strain",
        "tsai_hill",
        "tsai_wu",
    ]
    assert all(result.to_dict()["passed"] for result in results)


def test_zero_state_has_unbounded_reserve_factor(strengths: PlyStrengths):
    for result in CompositeFailureEvaluator.evaluate(np.zeros(3), np.zeros(3), strengths):
        assert result.index == pytest.approx(0.0)
        assert result.reserve_factor is None
        assert result.margin_of_safety is None


@pytest.mark.parametrize(
    "builder,match",
    [
        (lambda: PlyStrengths(0.0, 1.0, 1.0, 1.0, 1.0), "positive"),
        (lambda: PlyStrengths(1.0, 1.0, 1.0, 1.0, 1.0, 1.0), "strictly"),
        (lambda: PlyStrainAllowables(1.0, 1.0, 0.0, 1.0, 1.0), "positive"),
    ],
)
def test_invalid_allowables_are_rejected(builder, match: str):
    with pytest.raises(ValueError, match=match):
        builder()


def test_non_finite_or_wrong_size_vectors_are_rejected(strengths: PlyStrengths):
    with pytest.raises(ValueError, match="three finite"):
        CompositeFailureEvaluator.maximum_stress(np.zeros(2), strengths)
    with pytest.raises(ValueError, match="three finite"):
        CompositeFailureEvaluator.tsai_wu(np.array([0.0, np.nan, 0.0]), strengths)
