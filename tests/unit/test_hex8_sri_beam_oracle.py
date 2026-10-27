from __future__ import annotations

import pytest

from experiments.hex8_sri_equilibrium.beam_oracle import (
    cantilever_case_shear_factors,
    cowper_rectangular_shear_factor,
    timoshenko_cantilever_tip,
)


@pytest.mark.parametrize(
    ("poisson_ratio", "common_total_m", "cowper_total_m"),
    ((0.3, 0.0320624, 0.0320612), (0.4999, 0.0320720, 0.0320700)),
)
def test_cantilever_reference_separates_bending_and_shear_terms(
    poisson_ratio: float, common_total_m: float, cowper_total_m: float
) -> None:
    common, cowper = cantilever_case_shear_factors(
        length_m=20.0,
        width_y_m=1.0,
        depth_z_m=1.0,
        young_modulus_pa=1.0e6,
        poisson_ratio=poisson_ratio,
        transverse_resultant_n=1.0,
    )

    assert common.bending_m == pytest.approx(0.032)
    assert common.shear_m > 0.0
    assert common.total_m == pytest.approx(common_total_m, abs=3.0e-7)
    assert cowper.total_m == pytest.approx(cowper_total_m, abs=3.0e-7)
    assert cowper.shear_factor == pytest.approx(cowper_rectangular_shear_factor(poisson_ratio))
    assert abs(common.total_m - cowper.total_m) < 3.0e-6


def test_signed_tip_deflection_follows_signed_transverse_resultant() -> None:
    downward = timoshenko_cantilever_tip(
        length_m=20.0,
        width_y_m=1.0,
        depth_z_m=1.0,
        young_modulus_pa=1.0e6,
        poisson_ratio=0.3,
        transverse_resultant_n=-1.0,
    )
    assert downward.total_m < 0.0
    assert downward.bending_m < 0.0
    assert downward.shear_m < 0.0


@pytest.mark.parametrize(
    "kwargs",
    (
        {"length_m": 0.0},
        {"young_modulus_pa": -1.0},
        {"depth_z_m": 0.0},
        {"poisson_ratio": 0.5},
        {"shear_factor": 0.0},
    ),
)
def test_beam_reference_rejects_invalid_parameters(kwargs: dict[str, float]) -> None:
    parameters = {
        "length_m": 20.0,
        "width_y_m": 1.0,
        "depth_z_m": 1.0,
        "young_modulus_pa": 1.0e6,
        "poisson_ratio": 0.3,
        "transverse_resultant_n": 1.0,
        **kwargs,
    }
    with pytest.raises(ValueError):
        timoshenko_cantilever_tip(**parameters)
