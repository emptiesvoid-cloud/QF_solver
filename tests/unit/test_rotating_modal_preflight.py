"""Fail-closed input and serialization tests for the bounded rotating route."""

from __future__ import annotations

import json

import numpy as np
import pytest

from solveur.compatibility import preflight_model
from solveur.core.analyses.rotating_input_validator import RotatingModalInputValidator
from solveur.core.analyses.rotation_config import RotationConfig
from solveur.core.analyses.settings import AnalysisSettings
from solveur.core.errors import InputValidationError
from solveur.core.model import BoundaryCondition, ElementDefinition, FiniteElementModel, NodalLoad
from solveur.core.qualification import model_maturity
from solveur.core.router import AnalysisRouter
from solveur.core.results import RotatingModalResult
from solveur.elements.discrete import ConcentratedMass, RotatingDisk, SpringDefinition
from solveur.io.json_reader import JsonModelReader
from solveur.io.model_writer import model_to_dict


def _circular_material(radius: float = 0.05) -> dict[str, float | str]:
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
    analysis: str = "rotating_modal",
    speed: float = 0.0,
    axis: tuple[float, float, float] = (1.0, 0.0, 0.0),
    disks: list[object] | None = None,
    elements: list[ElementDefinition] | None = None,
    nodes: np.ndarray | None = None,
    materials: dict[str, dict[str, object]] | None = None,
    springs: list[SpringDefinition] | None = None,
    loads: list[NodalLoad] | None = None,
    parameters: dict[str, object] | None = None,
) -> FiniteElementModel:
    if nodes is None:
        nodes = np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    if elements is None:
        elements = [ElementDefinition("BEAM2", (0, 1), "beam")]
    if materials is None:
        materials = {"beam": _circular_material()}
    if disks is None:
        disks = [RotatingDisk(1, 1.0, 0.01, 0.02, axis)]
    raw_parameters: dict[str, object] = {
        "rotation": {
            "axis_global": list(axis),
            "speed_rad_s": speed,
            "frame_convention": "global_fixed_right_hand_rule",
        },
        "modes": 6,
    }
    if parameters:
        raw_parameters.update(parameters)
    return FiniteElementModel(
        nodes=nodes,
        elements=elements,
        materials=materials,
        fixed_dofs=[BoundaryCondition(0, ("UX", "UY", "UZ", "RX", "RY", "RZ"))],
        loads=loads or [],
        springs=springs or [],
        concentrated_masses=disks,  # type: ignore[arg-type]
        analysis=AnalysisSettings.from_raw({"type": analysis, "parameters": raw_parameters}),
    )


def test_valid_bounded_model_is_explicitly_experimental() -> None:
    model = _model()

    validated = RotatingModalInputValidator().validate(model)
    report = preflight_model(model)

    assert validated.length_reference == pytest.approx(1.0)
    assert validated.rotation.axis_global == (1.0, 0.0, 0.0)
    assert validated.requested_modes == 6
    assert report.status == "EXPERIMENTAL_ROUTE"
    assert report.results[0].reason == "NO_REGISTRY_COMBINATION"
    assert model_maturity(model)["analysis"] == "experimental"
    assert model_maturity(model)["overall"] == "experimental"


def test_rotation_config_normalizes_axis_and_requires_explicit_rpm_conversion() -> None:
    config = RotationConfig.from_mapping(
        {
            "axis_global": [10.0, 0.0, 0.0],
            "speed_rad_s": -12.0,
            "frame_convention": "global_fixed_right_hand_rule",
        }
    )
    from_rpm = RotationConfig.from_rpm(axis_global=(1.0, 0.0, 0.0), speed_rpm=-60.0)

    assert config.axis_global == (1.0, 0.0, 0.0)
    assert config.speed_rad_s == -12.0
    assert from_rpm.speed_rad_s == pytest.approx(-2.0 * np.pi)
    with pytest.raises(InputValidationError, match="unknown fields"):
        RotationConfig.from_mapping(
            {
                "axis_global": [1.0, 0.0, 0.0],
                "speed_rad_s": 1.0,
                "frame_convention": "global_fixed_right_hand_rule",
                "rpm": 60,
            }
        )


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"nodes": np.asarray([[0.0, 0.0, 0.0], [1.0, 0.01, 0.0]])}, "straight"),
        ({"axis": (0.0, 1.0, 0.0)}, "parallel"),
        ({"disks": []}, "at least one RotatingDisk"),
        ({"parameters": {"rotation": {"axis_global": [1.0, 0.0, 0.0], "speed_rpm": 60}}}, "Invalid rotation configuration"),
        ({"loads": [NodalLoad(1, "UY", 1.0)]}, "unprestressed"),
    ],
)
def test_route_rejects_out_of_scope_inputs_before_assembly(changes: dict[str, object], message: str) -> None:
    with pytest.raises(InputValidationError, match=message):
        RotatingModalInputValidator().validate(_model(**changes))  # type: ignore[arg-type]


def test_rejects_non_beam_mixed_and_non_circular_sections() -> None:
    solid = _model(elements=[ElementDefinition("TET4", (0, 1, 0, 1), "beam")])
    with pytest.raises(InputValidationError, match="BEAM2 elements only"):
        RotatingModalInputValidator().validate(solid)

    noncircular_material = {"beam": {**_circular_material(), "Iz": 2.0 * _circular_material()["Iz"]}}
    with pytest.raises(InputValidationError, match="Iy=Iz"):
        RotatingModalInputValidator().validate(_model(materials=noncircular_material))


def test_accepts_circular_hollow_section_with_consistent_polar_inertia() -> None:
    solid = _circular_material()
    hollow = {
        **solid,
        "A": 0.5 * float(solid["A"]),
        "Iy": 1.5 * float(solid["Iy"]),
        "Iz": 1.5 * float(solid["Iz"]),
        "J": 3.0 * float(solid["Iy"]),
    }
    validated = RotatingModalInputValidator().validate(_model(materials={"beam": hollow}))
    assert validated.length_reference == pytest.approx(1.0)


def test_duplicate_generic_mass_and_unsupported_discrete_are_rejected() -> None:
    duplicate = _model(disks=[RotatingDisk(1, 1.0, 0.01, 0.02, (1.0, 0.0, 0.0)), ConcentratedMass(1, 2.0)])
    with pytest.raises(InputValidationError, match="duplicates the rotating disk mass owner"):
        RotatingModalInputValidator().validate(duplicate)

    unsupported_spring = SpringDefinition(1, ("UX",), ((100.0,),), node_b=0)
    with pytest.raises(InputValidationError, match="fixed-ground"):
        RotatingModalInputValidator().validate(_model(springs=[unsupported_spring]))


def test_multiple_explicit_disks_may_share_a_shaft_node() -> None:
    disks = [
        RotatingDisk(1, 1.0, 0.01, 0.02, (1.0, 0.0, 0.0)),
        RotatingDisk(1, 0.5, 0.005, 0.01, (1.0, 0.0, 0.0)),
    ]
    assert RotatingModalInputValidator().validate(_model(disks=disks)).length_reference == pytest.approx(1.0)


def test_rotating_disk_is_rejected_by_classic_modal_route() -> None:
    model = _model(analysis="modal")
    with pytest.raises(InputValidationError, match="only valid for analysis='rotating_modal'"):
        AnalysisRouter().solve(model)


def test_rotating_disk_json_model_round_trip_is_explicit() -> None:
    model = _model()
    payload = model_to_dict(model)
    reloaded = JsonModelReader().from_dict(payload)
    disk = reloaded.concentrated_masses[0]

    assert isinstance(disk, RotatingDisk)
    assert disk.axis_global == (1.0, 0.0, 0.0)
    assert disk.matrix().shape == (6, 6)
    assert reloaded.analysis.type == "rotating_modal"


def test_explicit_legacy_concentrated_mass_type_remains_parseable() -> None:
    model = FiniteElementModel.from_raw(
        nodes=[[0.0, 0.0, 0.0]],
        elements=[],
        materials={},
        concentrated_masses=[{"type": "concentrated_mass", "node": 0, "mass": 1.0}],
    )
    assert isinstance(model.concentrated_masses[0], ConcentratedMass)


def test_router_returns_separate_experimental_rotating_modal_result() -> None:
    result = AnalysisRouter().solve(_model())

    assert isinstance(result, RotatingModalResult)
    assert result.numerical_status == "PASS"
    assert result.maturity == "EXPERIMENTAL"
    assert result.spin_speed_rad_s == 0.0
    assert result.eigenvalues.dtype == np.complex128
    assert result.modes.dtype == np.complex128
    assert result.selected_mode_indices
    assert max(result.qep_residuals) <= 1.0e-8
    assert result.run_verdict.value == "WARNING"
    json.dumps(result.to_dict(), allow_nan=False)
