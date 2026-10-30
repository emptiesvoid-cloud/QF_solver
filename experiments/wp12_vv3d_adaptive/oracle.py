"""Manufactured 3D elasticity field. No solver, assembly or numerical integration."""
from __future__ import annotations

import math

E_PA = 1.0e6
NU = 0.3
AMPLITUDE_M = 1.0e-4
LENGTHS_M = (1.0, 1.0, 1.0)


def lame(e: float = E_PA, nu: float = NU) -> tuple[float, float]:
    if not math.isfinite(e) or e <= 0 or not math.isfinite(nu) or not -1.0 < nu < 0.5:
        raise ValueError("material must have finite E > 0 and -1 < nu < 0.5")
    return e * nu / ((1 + nu) * (1 - 2 * nu)), e / (2 * (1 + nu))


def field(xyz: tuple[float, float, float]) -> dict[str, tuple[float, ...]]:
    """u=(0,0,A sin(pi*x/Lx) sin(pi*y/Ly) sin(pi*z/Lz)); f=-div(sigma)."""
    if len(xyz) != 3 or not all(math.isfinite(x) and 0 <= x <= length for x, length in zip(xyz, LENGTHS_M)):
        raise ValueError("point outside the finite 3D domain")
    lam, mu = lame()
    kx, ky, kz = (math.pi / length for length in LENGTHS_M)
    x, y, z = xyz
    sx, sy, sz = math.sin(kx*x), math.sin(ky*y), math.sin(kz*z)
    cx, cy, cz = math.cos(kx*x), math.cos(ky*y), math.cos(kz*z)
    a = AMPLITUDE_M
    w = a*sx*sy*sz
    wx, wy, wz = a*kx*cx*sy*sz, a*ky*sx*cy*sz, a*kz*sx*sy*cz
    wxz, wyz = a*kx*kz*cx*sy*cz, a*ky*kz*sx*cy*cz
    # Stress order xx, yy, zz, xy, yz, xz in Pa; engineering shear strains.
    return {"u_m": (0.0, 0.0, w), "strain": (0.0, 0.0, wz, 0.0, wy, wx),
            "stress_pa": (lam*wz, lam*wz, (lam+2*mu)*wz, 0.0, mu*wy, mu*wx),
            "body_force_n_m3": (-(lam+mu)*wxz, -(lam+mu)*wyz,
                (mu*(kx*kx+ky*ky+kz*kz)+(lam+mu)*kz*kz)*w)}


def exact_energy_j() -> float:
    lam, mu = lame()
    kx, ky, kz = (math.pi / length for length in LENGTHS_M)
    volume = math.prod(LENGTHS_M)
    return AMPLITUDE_M**2 * volume / 8 * (0.5*mu*(kx*kx+ky*ky)+(mu+0.5*lam)*kz*kz)


def exact_global_balance() -> dict[str, tuple[float, ...]]:
    """Exact resultant and origin moment of body load and all-boundary reactions."""
    lam, mu = lame()
    kx, ky, kz = (math.pi / length for length in LENGTHS_M)
    coefficient = mu*(kx*kx+ky*ky+kz*kz)+(lam+mu)*kz*kz
    force_z = coefficient * AMPLITUDE_M * math.prod(LENGTHS_M) * (2/math.pi)**3
    lx, ly, _lz = LENGTHS_M
    return {"body_force_n": (0.0, 0.0, force_z), "reaction_n": (0.0, 0.0, -force_z),
            "body_moment_origin_nm": (ly*force_z/2, -lx*force_z/2, 0.0),
            "reaction_moment_origin_nm": (-ly*force_z/2, lx*force_z/2, 0.0)}
