from __future__ import annotations

import json

import pytest

from solveur.verification.external_correlation import (
    ExternalReferenceError,
    compare_nafems_13h,
    compare_pinched_cylinder,
    load_abaqus_nafems_13h_reference,
    load_abaqus_mitc4_static_reference,
)


def test_official_abaqus_reference_is_controlled_and_monotone() -> None:
    reference = load_abaqus_mitc4_static_reference()

    assert reference["publisher"] == "Dassault Systemes SIMULIA"
    assert reference["source"]["url"].startswith("https://docs.software.vt.edu/")
    values = [row["displacement"] for row in reference["regular_mesh_results"]]
    errors = [abs(value - reference["case"]["reference_displacement"]) for value in values]
    assert errors == sorted(errors, reverse=True)
    assert len(reference["source"]["input_files"]) == 3
    assert all(url.endswith(".inp") for url in reference["source"]["input_files"])


def test_pinched_cylinder_external_comparison_passes() -> None:
    comparison = compare_pinched_cylinder(
        {
            "points": [
                {
                    "mesh": [32, 64],
                    "element_count": 2048,
                    "value": 1.692335683714122e-5,
                }
            ]
        }
    )

    assert comparison["status"] == "PASS"
    assert comparison["comparison_type"] == "converged_response_non_identical_mesh"
    assert comparison["relative_difference"] == pytest.approx(0.04871518622028)


def test_invalid_external_reference_is_rejected(tmp_path) -> None:
    path = tmp_path / "reference.json"
    path.write_text(json.dumps({"reference_id": "incomplete"}), encoding="utf-8")

    with pytest.raises(ExternalReferenceError, match="missing"):
        load_abaqus_mitc4_static_reference(path)


def test_nafems_13h_reference_has_exact_abaqus_model_contract() -> None:
    reference = load_abaqus_nafems_13h_reference()

    assert reference["reference_id"] == "ABAQUS-2024-NAFEMS-13H-S4R-DIRECT"
    assert reference["model"]["mesh"] == "8x8 quadrilateral shell elements"
    assert reference["model"]["frequency_sweep_hz"] == {
        "start": 0.1,
        "stop": 4.16,
        "count": 200,
    }
    assert {row["element"] for row in reference["abaqus_direct_results"]} == {"S4", "S4R"}


def test_nafems_13h_external_comparison_accepts_measured_qf_peak() -> None:
    comparison = compare_nafems_13h(
        {
            "peak_displacement_mm": 44.27189938052172,
            "peak_frequency_hz": 2.4258291457286436,
            "peak_stress_n_mm2": 30.818588822773933,
            "max_relative_residual": 4.0e-10,
        }
    )

    assert comparison["status"] == "PASS"
    assert all(comparison["checks"].values())
    assert comparison["relative_differences"]["abaqus_displacement"] == pytest.approx(
        0.024418259574224017
    )
    assert comparison["relative_differences"]["abaqus_frequency"] == pytest.approx(
        0.00866076745473755
    )
    assert comparison["relative_differences"]["abaqus_stress"] == pytest.approx(
        0.014770787710699099
    )
    assert comparison["relative_differences"]["nafems_stress"] == pytest.approx(
        0.026260034058405976
    )
    assert comparison["relative_differences"]["abaqus_s4_stress"] == pytest.approx(
        0.014120639066732851
    )


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), float("-inf")])
def test_nafems_13h_external_comparison_rejects_nonfinite_metrics(invalid: float) -> None:
    with pytest.raises(ExternalReferenceError, match="positive number"):
        compare_nafems_13h(
            {
                "peak_displacement_mm": invalid,
                "peak_frequency_hz": 2.4,
                "peak_stress_n_mm2": 30.0,
                "max_relative_residual": 1.0e-10,
            }
        )
