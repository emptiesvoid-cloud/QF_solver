from __future__ import annotations

import json

import pytest

from solveur.verification.code_aster_nafems import CodeAsterNafems13HParser, relative_difference


def test_code_aster_rotation_gradient_recovers_constant_curvature() -> None:
    parser = CodeAsterNafems13HParser(young_pa=100.0, poisson=0.0, thickness_m=0.2)
    # DRY = 2*x on a unit square gives kappa_x=2 and S11=E*t/2*kappa_x=20.
    stress = parser.top_face_s11([0j] * 4, [0j, 2.0 + 0j, 2.0 + 0j, 0j], element_size=1.0)
    assert stress == pytest.approx(20.0 + 0j)


def test_code_aster_parser_averages_the_four_center_elements(tmp_path) -> None:
    rotations = [[node, [0.0, 0.0], [float((node - 1) % 3), 0.0]] for node in range(1, 10)]
    payload = {
        "frequency_points": [
            {
                "frequency_hz": 2.0,
                "center_uz": [1.0, -2.0],
                "element_size_m": 1.0,
                "center_elements": [[1, 2, 5, 4], [2, 3, 6, 5], [4, 5, 8, 7], [5, 6, 9, 8]],
                "center_rotations": rotations,
            }
        ]
    }
    path = tmp_path / "raw.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    point = CodeAsterNafems13HParser(young_pa=100.0, poisson=0.0, thickness_m=0.2).parse(path)[0]
    assert point.frequency_hz == 2.0
    assert point.uz_m == 1.0 - 2.0j
    assert point.s11_top_pa == pytest.approx(10.0 + 0j)


def test_relative_difference_rejects_zero_reference() -> None:
    with pytest.raises(ValueError, match="non-zero"):
        relative_difference(1.0, 0.0)


def test_code_aster_transient_parser_preserves_time_and_signed_stress(tmp_path) -> None:
    payload = {
        "time_points": [
            {
                "time_s": 0.25,
                "center_uz": -0.002,
                "element_size_m": 1.0,
                "center_elements": [[1, 2, 3, 4]],
                "center_rotations": [
                    [1, 0.0, 0.0], [2, 0.0, 2.0], [3, 0.0, 2.0], [4, 0.0, 0.0]
                ],
            }
        ]
    }
    path = tmp_path / "transient.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    point = CodeAsterNafems13HParser(
        young_pa=100.0, poisson=0.0, thickness_m=0.2
    ).parse_transient(path)[0]
    assert point.time_s == 0.25
    assert point.uz_m == -0.002
    assert point.s11_top_pa == pytest.approx(20.0)
