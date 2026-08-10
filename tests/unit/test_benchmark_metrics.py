from __future__ import annotations

import numpy as np
import pytest

from solveur.benchmarks.solid import observed_convergence_order


def test_observed_convergence_order_recovers_power_law() -> None:
    mesh_sizes = np.asarray([0.8, 0.4, 0.2, 0.1])
    errors = 2.5 * mesh_sizes**1.5
    assert observed_convergence_order(mesh_sizes, errors) == pytest.approx(1.5, abs=1.0e-12)


@pytest.mark.parametrize(
    ("mesh_sizes", "errors"),
    [
        ([1.0], [0.1]),
        ([1.0, 0.5], [0.1]),
        ([1.0, 0.0], [0.1, 0.05]),
        ([1.0, 0.5], [0.1, np.nan]),
        ([1.0, 1.0], [0.1, 0.05]),
    ],
)
def test_observed_convergence_order_rejects_invalid_series(mesh_sizes: object, errors: object) -> None:
    with pytest.raises(ValueError):
        observed_convergence_order(mesh_sizes, errors)
