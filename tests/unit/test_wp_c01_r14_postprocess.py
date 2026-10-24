"""Non-FEM tests for the supplemental, non-destructive R14 analyzer."""

from __future__ import annotations

import numpy as np
import pytest

from scripts.wp_c01_r14_postprocess import analyze, reconstruct_trial_margin


def test_reconstructs_trial_and_margin_from_current_pressure() -> None:
    basis = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    displacement = np.array([0.003, 0.004, 0.0])
    previous_slip_reference = np.array([0.0, 0.0])
    trial, norm, margin = reconstruct_trial_margin(
        basis, displacement, previous_slip_reference,
        tangential_stiffness=1000.0, pressure=100.0, friction_coefficient=0.5,
    )
    np.testing.assert_allclose(trial, [3.0, 4.0])
    assert norm == pytest.approx(5.0)
    assert margin == pytest.approx(-45.0)


@pytest.mark.parametrize(
    ("pressure", "expected"),
    [(0.0, 5.0), (10.0, 0.0), (20.0, -5.0)],
)
def test_margin_uses_accepted_pressure_not_a_fixed_capacity(pressure: float, expected: float) -> None:
    _, _, margin = reconstruct_trial_margin(
        np.eye(2), np.array([0.003, 0.004]), np.zeros(2),
        tangential_stiffness=1000.0, pressure=pressure, friction_coefficient=0.5,
    )
    assert margin == pytest.approx(expected)


def test_reconstruction_rejects_missing_or_nonfinite_inputs() -> None:
    with pytest.raises(ValueError, match="shape"):
        reconstruct_trial_margin(np.ones((2, 3)), np.ones(2), np.zeros(2), 1.0, 1.0, 0.2)
    with pytest.raises(ValueError, match="finite"):
        reconstruct_trial_margin(np.eye(2), np.array([np.nan, 0.0]), np.zeros(2), 1.0, 1.0, 0.2)


def test_analyzer_refuses_to_overwrite_historical_outputs(tmp_path) -> None:
    archive = tmp_path / "archive"
    archive.mkdir()
    protected = archive / "independent_postprocess.json"
    protected.write_text("historical", encoding="utf-8")
    with pytest.raises(ValueError, match="must not overwrite"):
        analyze(archive, protected)
    assert protected.read_text(encoding="utf-8") == "historical"


def test_analyzer_refuses_to_overwrite_existing_supplemental_output(tmp_path) -> None:
    archive = tmp_path / "archive"
    archive.mkdir()
    output = tmp_path / "supplemental.json"
    output.write_text("existing", encoding="utf-8")
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        analyze(archive, output)
    assert output.read_text(encoding="utf-8") == "existing"
