"""Targeted checks for the independent J11 continuum axial-bar reference."""

from __future__ import annotations

import math

import numpy as np
from scipy.integrate import quad

from research.j11_transient.axial_bar_reference import (
    axial_bar_response,
    constrained_axial_modulus,
    piecewise_linear_force_convolution,
)
from research.j11_transient.tet10_axial_transient import (
    MESH_LEVELS,
    PROBE_POSITION_M,
    TIP_POSITION_M,
    _exact_node,
    _mesh,
    _uniform_tip_force,
)


def test_piecewise_linear_force_convolution_matches_quadrature() -> None:
    segments = ((0.0, 1.0e-3, 0.0, 1.0), (1.0e-3, 2.0e-3, 1.0, 0.0))
    for time_s, omega in ((0.5e-3, 1750.0), (1.5e-3, 3100.0), (4.2e-3, 8300.0)):
        actual = float(piecewise_linear_force_convolution([time_s], omega, segments)[0])

        def force(value: float) -> float:
            if value <= 1.0e-3:
                return value / 1.0e-3
            if value <= 2.0e-3:
                return (2.0e-3 - value) / 1.0e-3
            return 0.0

        expected = math.fsum(
            quad(
                lambda value: force(value) * math.sin(omega * (time_s - value)),
                start,
                min(end, time_s),
                epsabs=1.0e-18,
                epsrel=2.0e-13,
            )[0]
            for start, end, _, _ in segments
            if min(end, time_s) > start
        )
        assert math.isclose(actual, expected, rel_tol=2.0e-11, abs_tol=1.0e-18)


def test_guided_axial_bar_reference_has_zero_initial_state_and_finite_response() -> None:
    modulus = constrained_axial_modulus(70.0e9, 0.3)
    expected = 70.0e9 * (1.0 - 0.3) / ((1.0 + 0.3) * (1.0 - 2.0 * 0.3))
    assert math.isclose(modulus, expected, rel_tol=1.0e-15)
    values = axial_bar_response(
        np.asarray([0.0, 0.25e-3, 1.0e-3, 2.0e-3, 8.0e-3]),
        length_m=2.0,
        area_m2=0.16,
        density_kg_m3=2700.0,
        axial_modulus_pa=modulus,
        force_segments=((0.0, 1.0e-3, 0.0, 1.0), (1.0e-3, 2.0e-3, 1.0, 0.0)),
        position_m=1.0,
        mode_count=256,
    )
    assert values[0] == 0.0
    assert np.all(np.isfinite(values))
    assert np.max(np.abs(values)) > 0.0


def test_tet10_meshes_have_physical_probes_and_balanced_quadratic_tip_load() -> None:
    for nx in MESH_LEVELS:
        coordinates, connectivity, signed_volumes = _mesh(nx)
        _exact_node(coordinates, PROBE_POSITION_M)
        _exact_node(coordinates, TIP_POSITION_M)
        assert len(connectivity) == 6 * nx
        assert np.all(signed_volumes > 0.0)
        _, nodal_force = _uniform_tip_force(nx, coordinates, connectivity)
        assert math.isclose(math.fsum(map(float, nodal_force)), 1.0, rel_tol=0.0, abs_tol=1.0e-13)
        assert math.isclose(
            math.fsum(float(nodal_force[i] * coordinates[i, 1]) for i in range(len(nodal_force))),
            0.2,
            rel_tol=0.0,
            abs_tol=1.0e-13,
        )
