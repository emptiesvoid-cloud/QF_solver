"""Immutable metadata for the first paired HEX8-SRI convergence campaign."""

from __future__ import annotations


FORMULATIONS = ("hex8_standard", "sri_historical", "sri_corrected")
POISSON_RATIOS = (0.3, 0.4999)
MESH_LEVELS = ((4, 2, 2), (8, 4, 4), (16, 8, 8), (32, 16, 16))
MESH_BUDGETS = {
    (4, 2, 2): {"timeout_seconds": 180, "rss_soft_limit_mib": 512},
    (8, 4, 4): {"timeout_seconds": 300, "rss_soft_limit_mib": 1024},
    (16, 8, 8): {"timeout_seconds": 900, "rss_soft_limit_mib": 4096},
    (32, 16, 16): {"timeout_seconds": 3600, "rss_soft_limit_mib": 16384},
}
LENGTH_M = 20.0
WIDTH_Y_M = 1.0
DEPTH_Z_M = 1.0
YOUNG_MODULUS_PA = 1.0e6
TRACTION_Z_PA = -1.0


def convergence_case_id(formulation: str, poisson_ratio: float, divisions_xyz: tuple[int, int, int]) -> str:
    """Return the stable manifest case ID for one first-campaign tuple."""
    if formulation not in FORMULATIONS or poisson_ratio not in POISSON_RATIOS or divisions_xyz not in MESH_LEVELS:
        raise ValueError("case is outside the first convergence-campaign matrix")
    nu_token = "0p3" if poisson_ratio == 0.3 else "0p4999"
    mesh_token = "x".join(str(value) for value in divisions_xyz)
    return f"{formulation}_nu_{nu_token}_{mesh_token}"


def convergence_nodeid(formulation: str, poisson_ratio: float, divisions_xyz: tuple[int, int, int]) -> str:
    """Return the exact proposed pytest identity, without collecting it."""
    convergence_case_id(formulation, poisson_ratio, divisions_xyz)
    nu_token = "0p3" if poisson_ratio == 0.3 else "0p4999"
    mesh_token = "x".join(str(value) for value in divisions_xyz)
    return (
        "tests/verification/test_hex8_sri_convergence.py::test_convergence_case["
        f"{formulation}-nu_{nu_token}-{mesh_token}]"
    )
