"""Synthetic no-FEM checks for durable WP12-B pre-assertion evidence."""

from __future__ import annotations

import json

import pytest
import numpy as np

from wp12b_test_support import atomic_write_json_no_overwrite, json_safe
from test_wp12b_tet10_curved_load import _independent_pressure_resultant_moment


def test_wp12b_sidecar_survives_following_assertion_failure(tmp_path) -> None:
    path = tmp_path / "attempt.json"
    payload = {
        "stage": "PRE_ASSERTION_METRICS",
        "observables": {"tip_displacement_m": 0.125, "reaction_N": [1.0, -1.0]},
    }
    with pytest.raises(AssertionError, match="synthetic physical assertion"):
        atomic_write_json_no_overwrite(path, payload)
        raise AssertionError("synthetic physical assertion")
    recovered = json.loads(path.read_text(encoding="utf-8"))
    assert recovered["stage"] == "PRE_ASSERTION_METRICS"
    assert recovered["observables"] == payload["observables"]


def test_wp12b_sidecar_refuses_overwrite_without_changing_existing_bytes(tmp_path) -> None:
    path = tmp_path / "attempt.json"
    atomic_write_json_no_overwrite(path, {"value": 1})
    original = path.read_bytes()
    with pytest.raises(FileExistsError):
        atomic_write_json_no_overwrite(path, {"value": 2})
    assert path.read_bytes() == original


def test_wp12b_sidecar_encodes_non_finite_values_as_strict_json() -> None:
    encoded = json.dumps(json_safe({"nan": float("nan"), "infinity": float("inf")}), allow_nan=False)
    assert '"non_finite": "nan"' in encoded
    assert '"non_finite": "inf"' in encoded


def test_wp12b_tet10_independent_face_oracle_reproduces_historical_integral() -> None:
    nodes = np.asarray(
        [
            [0, 0, 0],
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 1],
            [0.5, 0, 0],
            [0.5, 0.5, 0],
            [0, 0.5, 0],
            [0, 0, 0.5],
            [0.5, 0, 0.5],
            [0, 0.5, 0.5],
        ],
        dtype=float,
    )
    nodes[4:] += np.asarray(
        [[0, 0.04, 0.01], [0.02, 0.02, 0.03], [0.03, 0, 0.01], [0.03, 0.01, 0], [0.01, 0.03, 0.02], [0.02, 0.01, 0.03]]
    )
    force, moment = _independent_pressure_resultant_moment(nodes)
    np.testing.assert_allclose(
        force, [1.0266666666666666, 0.013333333333333334, 0.013333333333333326], rtol=0.0, atol=1.0e-12
    )
    np.testing.assert_allclose(
        moment, [0.00021333333333333504, 0.35365333333333343, -0.3532266666666668], rtol=0.0, atol=1.0e-12
    )
