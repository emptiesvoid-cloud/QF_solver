"""Independent one-dimensional beam checks for the HEX8-SRI cantilever.

These closed-form values are engineering-scale references, not a 3-D accuracy
oracle: they omit the clamp and loaded-face boundary layers of the solid model.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BeamTipReference:
    """Cantilever tip-deflection terms, in SI units."""

    bending_m: float
    shear_m: float
    total_m: float
    shear_modulus_pa: float
    shear_factor: float


def cowper_rectangular_shear_factor(poisson_ratio: float) -> float:
    """Cowper's 1966 shear coefficient for a rectangular beam section."""
    nu = float(poisson_ratio)
    if not -1.0 < nu < 0.5:
        raise ValueError("Poisson ratio must lie in (-1, 0.5)")
    return 10.0 * (1.0 + nu) / (12.0 + 11.0 * nu)


def timoshenko_cantilever_tip(
    *,
    length_m: float,
    width_y_m: float,
    depth_z_m: float,
    young_modulus_pa: float,
    poisson_ratio: float,
    transverse_resultant_n: float,
    shear_factor: float = 5.0 / 6.0,
) -> BeamTipReference:
    """Return bending-plus-shear tip translation for a prismatic cantilever.

    The beam axis is x; the transverse load and tip translation are z-directed.
    ``width_y_m`` is the section breadth and ``depth_z_m`` its bending depth,
    so ``I_y = width_y * depth_z**3 / 12``. The load is represented by its
    centroidal transverse resultant. This expression does not model local 3-D
    end effects or constitute a strict error bound for a solid finite element.
    """
    length = float(length_m)
    width = float(width_y_m)
    depth = float(depth_z_m)
    young = float(young_modulus_pa)
    nu = float(poisson_ratio)
    load = float(transverse_resultant_n)
    kappa = float(shear_factor)
    if min(length, width, depth, young, kappa) <= 0.0:
        raise ValueError("length, section dimensions, E, and shear factor must be positive")
    if not -1.0 < nu < 0.5:
        raise ValueError("Poisson ratio must lie in (-1, 0.5)")

    area = width * depth
    inertia_y = width * depth**3 / 12.0
    shear_modulus = young / (2.0 * (1.0 + nu))
    bending = load * length**3 / (3.0 * young * inertia_y)
    shear = load * length / (kappa * shear_modulus * area)
    return BeamTipReference(
        bending_m=bending,
        shear_m=shear,
        total_m=bending + shear,
        shear_modulus_pa=shear_modulus,
        shear_factor=kappa,
    )


def cantilever_case_shear_factors(
    *,
    length_m: float,
    width_y_m: float,
    depth_z_m: float,
    young_modulus_pa: float,
    poisson_ratio: float,
    transverse_resultant_n: float,
) -> tuple[BeamTipReference, BeamTipReference]:
    """Compare the common 5/6 factor with Cowper's ν-dependent rectangle value."""
    common = timoshenko_cantilever_tip(
        length_m=length_m,
        width_y_m=width_y_m,
        depth_z_m=depth_z_m,
        young_modulus_pa=young_modulus_pa,
        poisson_ratio=poisson_ratio,
        transverse_resultant_n=transverse_resultant_n,
    )
    cowper = timoshenko_cantilever_tip(
        length_m=length_m,
        width_y_m=width_y_m,
        depth_z_m=depth_z_m,
        young_modulus_pa=young_modulus_pa,
        poisson_ratio=poisson_ratio,
        transverse_resultant_n=transverse_resultant_n,
        shear_factor=cowper_rectangular_shear_factor(poisson_ratio),
    )
    return common, cowper
