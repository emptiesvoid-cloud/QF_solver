"""Pure postprocessing of supplied data; no assembly, solver or eigenanalysis."""
from __future__ import annotations

import math
from typing import Sequence


def _finite_vector(v: Sequence[float], size: int) -> None:
    if len(v) != size or not all(math.isfinite(x) for x in v):
        raise ValueError("invalid finite vector")


def field_errors(
    weights_m3: Sequence[float], displacement_error_m: Sequence[Sequence[float]],
    strain_error: Sequence[Sequence[float]], *, lame_lambda_pa: float, shear_mu_pa: float,
) -> dict[str, float]:
    """Quadrature samples are supplied by the caller, independently of this function.

    Voigt strain is xx, yy, zz, gamma_xy, gamma_yz, gamma_xz.
    """
    if (not weights_m3 or len(weights_m3) != len(displacement_error_m) or len(weights_m3) != len(strain_error)
            or not math.isfinite(lame_lambda_pa) or not math.isfinite(shear_mu_pa)
            or shear_mu_pa <= 0 or 3*lame_lambda_pa + 2*shear_mu_pa <= 0):
        raise ValueError("invalid quadrature or isotropic material")
    u2=energy=0.0
    for weight,du,de in zip(weights_m3,displacement_error_m,strain_error):
        if not math.isfinite(weight) or weight <= 0:
            raise ValueError("quadrature weights must be finite and positive")
        _finite_vector(du,3)
        _finite_vector(de,6)
        trace = sum(de[:3])
        e2 = sum(x*x for x in de[:3]) + 0.5*sum(x*x for x in de[3:])
        u2 += weight*sum(x*x for x in du)
        energy += weight*(lame_lambda_pa*trace*trace+2*shear_mu_pa*e2)
    if energy < 0:
        raise ValueError("negative energy norm requires investigation")
    return {"displacement_l2_m_5_2": math.sqrt(u2), "energy_error_norm_sqrt_j": math.sqrt(energy)}


def force_moment_balance(
    coordinates_m: Sequence[Sequence[float]], loads_n: Sequence[Sequence[float]],
    reactions_n: Sequence[Sequence[float]], origin_m: Sequence[float] = (0.0,0.0,0.0),
) -> dict[str, tuple[float, float, float]]:
    """Unnormalized global closure in N and N m about an explicitly supplied origin."""
    if not coordinates_m or len(coordinates_m) != len(loads_n) or len(loads_n) != len(reactions_n):
        raise ValueError("mismatched nodal arrays")
    _finite_vector(origin_m,3)
    force = [0.0]*3
    moment = [0.0]*3
    for point,load,reaction in zip(coordinates_m,loads_n,reactions_n):
        _finite_vector(point,3)
        _finite_vector(load,3)
        _finite_vector(reaction,3)
        x,y,z = (point[i]-origin_m[i] for i in range(3))
        fx,fy,fz = (load[i]+reaction[i] for i in range(3))
        for i,value in enumerate((fx,fy,fz)):
            force[i] += value
        for i,value in enumerate((y*fz-z*fy,z*fx-x*fz,x*fy-y*fx)):
            moment[i] += value
    return {"force_closure_n": tuple(force), "moment_closure_nm": tuple(moment)}
