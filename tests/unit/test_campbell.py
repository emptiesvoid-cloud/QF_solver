"""End-to-end experimental Campbell route and fail-closed input tests."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

import solveur.core.analyses.campbell as campbell_analysis
from solveur.core.analyses.campbell import CampbellInputValidator, CampbellSolver
from solveur.core.analyses.settings import AnalysisSettings
from solveur.core.dofs import DOF_ORDER
from solveur.core.errors import InputValidationError, NumericalConvergenceError
from solveur.core.model import BoundaryCondition, ElementDefinition, FiniteElementModel
from solveur.elements.discrete import RotatingDisk
from solveur.core.router import AnalysisRouter
from solveur.io.model_writer import model_to_dict
from solveur.io.schema import JsonSchemaValidator


def test_implementation_hash_paths_support_installed_wheel_layout(tmp_path: Path, monkeypatch) -> None:
    package_root = tmp_path / "venv" / "Lib" / "site-packages" / "solveur"
    module_file = package_root / "core" / "analyses" / "campbell.py"
    module_file.parent.mkdir(parents=True)
    module_file.write_text("# installed wheel layout\n", encoding="utf-8")
    monkeypatch.setattr(campbell_analysis, "__file__", str(module_file))

    implementation = campbell_analysis._implementation_source_path(
        "src/solveur/core/analyses/rotating_modal.py"
    )

    assert implementation == package_root / "core" / "analyses" / "rotating_modal.py"


def _beam_material() -> dict[str, float | str]:
    radius = 0.05
    area = np.pi * radius**2
    inertia = area**2 / (4.0 * np.pi)
    return {
        "type": "beam_isotropic",
        "E": 210.0e9,
        "nu": 0.3,
        "A": area,
        "Iy": inertia,
        "Iz": inertia,
        "J": 2.0 * inertia,
        "density": 7800.0,
    }


def _model(
    *,
    speeds: list[float] | None = None,
    rotation_axis: list[float] | None = None,
    method: str = "complex_mac_hungarian",
) -> FiniteElementModel:
    parameters = {
        "rotation": {
            "axis_global": rotation_axis or [1.0, 0.0, 0.0],
            "frame_convention": "global_fixed_right_hand_rule",
        },
        "spin_speeds_rad_s": speeds if speeds is not None else [0.0, 10.0, 25.0],
        "modes": 2,
        "qep_settings": {"contract": "wp05-frozen-qep-v1"},
        "tracking_policy": "QF0211-COMPLEX-MAC-GLOBAL-v1",
    }
    return FiniteElementModel(
        nodes=np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]),
        elements=[ElementDefinition("BEAM2", (0, 1), "beam")],
        materials={"beam": _beam_material()},
        fixed_dofs=[BoundaryCondition(0, DOF_ORDER)],
        concentrated_masses=[RotatingDisk(1, 1.0, 0.01, 0.02, (1.0, 0.0, 0.0))],
        analysis=AnalysisSettings(type="campbell", method=method, parameters=parameters),
    )


@pytest.mark.parametrize(
    "speeds",
    [
        [0.0],
        [0.0, 1.0, 1.0],
        [0.0, float("nan")],
        [1.0, 0.0],
        [0.0, float("inf")],
    ],
)
def test_campbell_rejects_implicit_or_invalid_speed_grids(speeds: list[float]) -> None:
    with pytest.raises(InputValidationError):
        CampbellInputValidator().validate(_model(speeds=speeds))


def test_campbell_requires_frozen_qep_and_tracking_contracts() -> None:
    model = _model()
    model.analysis.parameters["tracking_policy"] = "greedy"
    with pytest.raises(InputValidationError, match="tracking_policy"):
        CampbellInputValidator().validate(model)


def test_campbell_fails_closed_if_requested_mode_count_is_unavailable() -> None:
    model = _model()
    model.analysis.parameters["modes"] = 100

    with pytest.raises(NumericalConvergenceError, match="requested 100"):
        CampbellSolver().solve(model)


def test_campbell_sweep_reuses_one_model_and_serializes_complex_source_results() -> None:
    model = _model()
    result = CampbellSolver().solve(model)

    assert result.numerical_status == "PASS"
    assert result.maturity == "EXPERIMENTAL"
    assert result.spin_speeds_rad_s == (0.0, 10.0, 25.0)
    assert len(result.source_results) == 3
    assert len(result.source_result_hashes) == 3
    assert len(set(result.source_result_hashes)) == 3
    assert result.diagnostics["invariant_reduced_k_m_g_sha256"]
    assert result.execution_identity["case_definition"]["spin_speeds_rad_s"] == [0.0, 10.0, 25.0]
    assert result.to_dict()["analysis"] == "campbell"
    serialized = json.loads(json.dumps(result.to_dict(), sort_keys=True, allow_nan=False))
    serialized_sample = next(
        sample
        for branch in serialized["branches"]
        for sample in branch["samples"]
        if sample is not None
    )
    decoded = result.complex_eigenvalues_from_sample(serialized_sample)
    assert np.all(np.isfinite(decoded))
    assert np.any(np.abs(decoded.imag) > 0.0)
    assert len(serialized["source_result_hashes"]) == len(result.source_results)


def test_campbell_is_exposed_through_model_schema_and_analysis_router() -> None:
    model = _model(speeds=[0.0, 5.0])
    JsonSchemaValidator().validate(model_to_dict(model))

    result = AnalysisRouter().solve(model)

    assert result.to_dict()["analysis"] == "campbell"
    assert result.maturity == "EXPERIMENTAL"
