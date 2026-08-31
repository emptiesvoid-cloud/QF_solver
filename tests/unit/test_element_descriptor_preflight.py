"""Targeted contracts for WP03 element descriptors and compatibility preflight."""

from __future__ import annotations

from solveur.compatibility import (
    DESCRIPTORS,
    check_compatibility,
    explain_compatibility,
    get_element_descriptor,
    get_maturity,
    preflight_model,
)
from solveur.core.model import FiniteElementModel


def test_all_existing_element_descriptors_are_complete() -> None:
    assert set(DESCRIPTORS) == {"BEAM2", "MITC3", "MITC4", "TET4", "TET10", "HEX8", "HEX20", "DISCRETE"}
    for descriptor in DESCRIPTORS.values():
        assert descriptor.canonical_name
        assert descriptor.aliases
        assert descriptor.topology
        assert descriptor.registry_capability_refs
        assert descriptor.supported_analyses
        assert descriptor.supported_load_categories


def test_aliases_are_deterministic() -> None:
    assert get_element_descriptor("tetra4").canonical_name == "TET4"
    assert get_element_descriptor("mitc3+").canonical_name == "MITC3"
    assert get_element_descriptor("hexa20").node_count == 20


def test_registry_and_descriptor_combinations_are_consistent() -> None:
    for family, descriptor in DESCRIPTORS.items():
        for analysis in descriptor.supported_analyses:
            if family == "DISCRETE":
                continue
            result = check_compatibility(family, analysis, descriptor.supported_material_families[0])
            assert result.status in {"SUPPORTED_ROUTE", "EXPERIMENTAL_ROUTE", "NOT_QUALIFIED_ROUTE"}
            assert result.element_family == family


def test_supported_and_experimental_routes_remain_distinct() -> None:
    assert check_compatibility("TET4", "linear_static", "isotropic_3d").status == "SUPPORTED_ROUTE"
    assert check_compatibility("BEAM2", "modal", "beam_isotropic").status == "EXPERIMENTAL_ROUTE"
    assert get_maturity("TET4", "linear_static") == "QUALIFIED_BOUNDED"


def test_not_qualified_route_is_explicit_without_being_silently_supported() -> None:
    result = check_compatibility("HEX8", "linear_buckling", "isotropic_3d")
    assert result.status == "NOT_QUALIFIED_ROUTE"
    assert result.reason == "REGISTRY_NOT_QUALIFIED"

    finite_j2 = check_compatibility("HEX8", "linear_static", "finite_kinematic_j2")
    assert finite_j2.status == "NOT_QUALIFIED_ROUTE"
    assert finite_j2.reason == "MATERIAL_NOT_QUALIFIED"


def test_unsupported_inputs_fail_closed_with_structured_diagnostics() -> None:
    unknown = explain_compatibility(element_family="WEDGE6", analysis="linear_static", material_model="isotropic_3d")
    assert unknown["status"] == "UNSUPPORTED_ROUTE"
    assert unknown["reason"] == "UNKNOWN_ELEMENT"
    assert "WEDGE6" in str(unknown["message"])

    bad_material = check_compatibility("MITC4", "linear_static", "isotropic_3d")
    assert bad_material.status == "UNSUPPORTED_ROUTE"
    assert bad_material.reason == "MATERIAL_NOT_SUPPORTED"

    bad_load = check_compatibility("BEAM2", "linear_static", "beam_isotropic", load_categories=("pressure",))
    assert bad_load.status == "UNSUPPORTED_ROUTE"
    assert bad_load.reason == "LOAD_NOT_SUPPORTED"


def test_model_preflight_reports_before_dispatch_and_keeps_experimental_routes_usable() -> None:
    model = FiniteElementModel.from_raw(
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "E": 1.0, "nu": 0.3}},
        fixed_dofs=[{"node": 0, "dofs": ["UX", "UY", "UZ"]}],
        loads=[{"node": 1, "dof": "UX", "value": 1.0}],
        analysis="linear_static",
    )
    report = preflight_model(model)
    assert report.ok
    assert report.status == "SUPPORTED_ROUTE"
    assert report.results[0].reason == "SUPPORTED_COMBINATION"
