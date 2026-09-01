from __future__ import annotations

import numpy as np
import pytest

from scripts.run_wp17r_petsc_remediation import (
    MONITOR_PATTERN,
    _compare_replays,
    _frozen_config,
    _monitor_evidence,
    _reaction_diagnostics,
    _resolve_solver_rtol,
)
from solveur.large.generator import generate_tet4_block


def test_wp17r_config_is_frozen_and_backend_explicit() -> None:
    config = _frozen_config("petsc", "gamg", True, 2, "contiguous")

    assert config["backend"] == "petsc"
    assert config["solver"] == "CG"
    assert config["rtol"] == 1.0e-8
    assert config["solver_rtol"] == 1.0e-8
    assert config["atol"] == 0.0
    assert config["max_iterations"] == 10000
    assert config["petsc_options"] == {
        "ksp_monitor_true_residual": None,
        "ksp_rtol": 1.0e-8,
        "ksp_norm_type": "unpreconditioned",
    }
    assert config["stopping_norm"] == "unpreconditioned"
    assert "no implicit fallback" in config["fallback_policy"]


def test_wp17r_strict_internal_tolerance_is_explicit_and_bounded() -> None:
    config = _frozen_config("petsc", "gamg", False, 2, "contiguous", 1.0e-10)

    assert config["rtol"] == 1.0e-8
    assert config["solver_rtol"] == 1.0e-10
    assert config["petsc_options"]["ksp_rtol"] == 1.0e-10
    assert "predeclared strict" in config["solver_rtol_policy"]


@pytest.mark.parametrize("value", [0.0, -1.0, 1.0e-7, float("nan"), float("inf")])
def test_wp17r_internal_tolerance_rejects_invalid_or_relaxed_values(value: float) -> None:
    with pytest.raises(ValueError):
        _resolve_solver_rtol(value)


def test_wp17r_monitor_parser_records_true_residual() -> None:
    line = " 12 KSP preconditioned resid norm 1.0e-6 true resid norm 2.0e-4 ||r(i)||/||b|| 3.0e-8"
    match = MONITOR_PATTERN.match(line)

    assert match is not None
    assert int(match.group("iteration")) == 12
    assert float(match.group("true")) == 2.0e-4
    assert float(match.group("relative")) == 3.0e-8


def test_wp17r_monitor_evidence_is_deterministic(tmp_path) -> None:
    path = tmp_path / "monitor.log"
    path.write_text(
        "\n".join(
            f" {index} KSP preconditioned resid norm 1.0e-{index + 2} "
            f"true resid norm 1.0e-{index + 2} ||r(i)||/||b|| 1.0e-{index + 3}"
            for index in range(20)
        )
        + "\n",
        encoding="utf-8",
    )

    evidence = _monitor_evidence(path)

    assert evidence["status"] == "PASS"
    assert evidence["entry_count"] == 20
    assert evidence["last_iteration"] == 19
    assert evidence["raw_log_sha256"]


def test_wp17r_replay_comparison_rejects_configuration_drift() -> None:
    first = {
        "input_digest_sha256": "input",
        "source_sha": "source",
        "configuration_digest_sha256": "a",
        "true_dof": 100,
        "matvec_count": 10,
        "post": {"residual_relative": 1.0e-9, "equilibrium_relative": 2.0e-9, "energy_relative": 3.0e-9},
    }
    second = {**first, "configuration_digest_sha256": "b"}

    result = _compare_replays(first, second)

    assert result["status"] == "FAIL"
    assert result["same_configuration"] is False
    assert result["same_source"] is True


def test_wp17r_replay_comparison_rejects_source_drift() -> None:
    first = {
        "source_sha": "a",
        "input_digest_sha256": "input",
        "configuration_digest_sha256": "config",
        "true_dof": 100,
        "matvec_count": 10,
        "post": {"residual_relative": 1.0e-9, "equilibrium_relative": 2.0e-9, "energy_relative": 3.0e-9},
    }
    second = {**first, "source_sha": "b"}

    result = _compare_replays(first, second)

    assert result["status"] == "FAIL"
    assert result["same_source"] is False


def test_wp17r_replay_comparison_accepts_canonical_free_residual() -> None:
    record = {
        "source_sha": "source",
        "input_digest_sha256": "input",
        "configuration_digest_sha256": "config",
        "true_dof": 100,
        "matvec_count": 10,
        "post": {
            "free_relative_residual": 1.0e-9,
            "equilibrium_relative": 2.0e-9,
            "energy_relative": 3.0e-9,
        },
    }

    result = _compare_replays(record, {**record})

    assert result["status"] == "PASS"
    assert result["mismatches"] == []


def test_wp17r_reaction_diagnostic_is_finite(tmp_path) -> None:
    model = generate_tet4_block(tmp_path / "model.h5", nx=1, ny=1, nz=1)
    displacement = np.zeros(model.ndof, dtype=float)

    result = _reaction_diagnostics(model, displacement)

    assert result["finite_outputs"] is True
    assert np.isfinite(result["equilibrium_relative"])
