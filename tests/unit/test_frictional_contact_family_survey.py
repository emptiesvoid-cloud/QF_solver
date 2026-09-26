"""Tests for the three-family frictional-contact evidence survey."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import numpy as np
import pytest
from scipy.sparse import csr_matrix

from solveur.contact import slip_root
from solveur.core.errors import NumericalConvergenceError
from solveur.core.solvers.static import LinearStaticSolver
from solveur.io.json_reader import JsonModelReader
from solveur.verification.frictional_contact_family_survey import (
    FrictionalContactFamilySurvey,
)


def test_family_survey_exercises_three_geometries_and_sliding(tmp_path: Path) -> None:
    summary = FrictionalContactFamilySurvey(tmp_path).run()

    assert summary["status"] == "PASS_INTERNAL"
    assert summary["geometry_family_count"] == 3
    assert summary["mesh_policy"]["mesh_level_count_per_family"] == 3
    assert summary["mesh_policy"]["status"] == "PASS_INTERNAL"
    assert all(case["finite_response"] for case in summary["families"].values())
    assert any("slip" in case["states"] for case in summary["families"].values())
    assert all(check["status"] == "PASS" for check in summary["checks"])


def test_family_survey_writes_machine_readable_and_visual_evidence(tmp_path: Path) -> None:
    FrictionalContactFamilySurvey(tmp_path).run()

    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["campaign_id"] == "VNV-CONTACT-FRICTION-FAMILIES-004"
    assert (tmp_path / "report.md").is_file()
    assert (tmp_path / "frictional_contact_family_survey.png").stat().st_size > 0
    assert (tmp_path / "vnv_manifest.json").is_file()


def test_ramp_cycle_is_recovered_by_coupled_normal_and_friction_projection(monkeypatch: pytest.MonkeyPatch) -> None:
    solver_module = importlib.import_module("solveur.contact.solver")
    trace: list[dict[str, object]] = []
    monkeypatch.setattr(
        solver_module,
        "_contact_trace",
        lambda _telemetry, *, step, strategy: lambda phase, values: trace.append(
            {"step": step, "strategy": strategy, "phase": phase, **dict(values)}
        ),
    )

    data = FrictionalContactFamilySurvey._build_ramp(1)
    FrictionalContactFamilySurvey._prepare_ramp(data)
    model_data = {key: value for key, value in data.items() if not key.startswith("_")}
    result = LinearStaticSolver().solve(JsonModelReader().from_dict(model_data))

    contact = result.solver["contact"]
    assert contact["converged"] is True
    assert contact["history"][-1]["strategy"] == "coupled_coulomb_projection_root"
    assert contact["history"][-1]["active_contacts"] == [0, 1, 2]
    assert contact["history"][-1]["tangential_states"] == ["slip", "slip", "slip"]
    assert any(row["phase"] == "coupled_contact_candidate_accepted" for row in trace)

    for row in contact["contacts"]:
        assert row["active"] is True
        assert row["gap"] == pytest.approx(0.0, abs=1.0e-9)
        assert row["tangential_force_norm"] == pytest.approx(row["friction_limit"], rel=1.0e-10, abs=1.0e-8)


def test_coupled_projection_tries_large_seed_before_blocking_enumeration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Contact:
        has_friction = True

        def gap(self, _displacement: np.ndarray) -> float:
            return 0.0

    operators = [Contact() for _ in range(25)]
    seed_active = tuple(range(15))
    attempted: list[tuple[int, ...]] = []

    monkeypatch.setattr(slip_root, "_normal_active_set", lambda *_args, **_kwargs: seed_active)

    def reject_seed(*args: object, **_kwargs: object) -> None:
        attempted.append(tuple(args[5]))
        raise NumericalConvergenceError("synthetic inadmissible seed")

    monkeypatch.setattr(slip_root, "_solve_coupled_projection_on_active_set", reject_seed)

    with pytest.raises(NumericalConvergenceError, match="exhaustive search exceeds") as captured:
        slip_root.solve_coupled_contact_projection(
            cast(Any, SimpleNamespace(ndof=1)),
            csr_matrix(np.eye(1)),
            np.zeros(1),
            np.array([], dtype=int),
            operators,
            np.zeros((25, 2)),
            1.0e-9,
            solve_active_set=cast(Any, lambda *_args: None),
            pressures_for=cast(Any, lambda *_args: None),
            proposed_active=cast(Any, lambda *_args: None),
            tangential_force=cast(Any, lambda *_args: np.zeros(1)),
        )

    assert attempted == [seed_active]
    assert captured.value.diagnostics is not None
    assert captured.value.diagnostics["cause"] == "COUPLED_SEARCH_CONTACT_LIMIT_EXCEEDED"
    assert captured.value.diagnostics["attempted_candidate_count"] == 1
    assert captured.value.diagnostics["seed_frictional_contact_count"] == 15
    assert captured.value.diagnostics["contact_count"] == 25
