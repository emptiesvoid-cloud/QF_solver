"""Math-only regression contracts for WP12 TET4 field-error postprocessing.

The full integrated outputs below were captured from the immutable baseline
59fdf0be1dd4896eb2c09b49127d02cedd2324ae.  The fixture is deliberately local
to this test: it does not depend on a generated mesh, solver, FEM, or another
checkout.
"""
from __future__ import annotations

import pytest

from experiments.wp12_vv3d_adaptive import field_error_draft


_MESH = {
    "family": "TET4",
    "nodes_integer": [(1, 1, 1), (9, 1, 1), (1, 8, 1), (1, 1, 7)],
    "connectivity_zero_based": [[0, 1, 2, 3]],
    "integer_coordinate_denominator": 10,
}
_FIELD = [
    (1.2e-5, -2.1e-5, 0.7e-5),
    (2.2e-5, -1.4e-5, 1.1e-5),
    (0.4e-5, 0.8e-5, -0.5e-5),
    (-1.1e-5, 1.7e-5, 2.8e-5),
]


@pytest.mark.parametrize(
    ("order", "expected"),
    [
        (
            4,
            {
                "displacement_l2_m_5_2": 6.143413174462989e-06,
                "displacement_relative_l2": 0.8058701569172688,
                "energy_error_norm_sqrt_j": 0.03484257069453576,
                "energy_error_relative": 0.8291503524030849,
                "strain_error_l2_m_3_2": 3.7033096045915635e-05,
                "strain_error_relative": 0.9209245969975828,
                "stress_error_l2_pa_m_3_2": 36.48914071021455,
                "stress_error_relative": 0.7070690491448436,
                "scalar_energy_j": 0.0002294862255799753,
                "quadrature_order": 4,
                "status": "DIAGNOSTIC_UNQUALIFIED",
            },
        ),
        (
            8,
            {
                "displacement_l2_m_5_2": 6.127502559322169e-06,
                "displacement_relative_l2": 0.8051948193231878,
                "energy_error_norm_sqrt_j": 0.03477816418259721,
                "energy_error_relative": 0.8287401775496801,
                "strain_error_l2_m_3_2": 3.698644383565896e-05,
                "strain_error_relative": 0.9208027875152,
                "stress_error_l2_pa_m_3_2": 36.37909821062484,
                "stress_error_relative": 0.7060801498978156,
                "scalar_energy_j": 0.00022948622557997586,
                "quadrature_order": 8,
                "status": "DIAGNOSTIC_UNQUALIFIED",
            },
        ),
        (
            12,
            {
                "displacement_l2_m_5_2": 6.127502592115565e-06,
                "displacement_relative_l2": 0.805194820839227,
                "energy_error_norm_sqrt_j": 0.03477816384708516,
                "energy_error_relative": 0.8287401750468276,
                "strain_error_l2_m_3_2": 3.6986443566379164e-05,
                "strain_error_relative": 0.9208027864962692,
                "stress_error_l2_pa_m_3_2": 36.37909768851956,
                "stress_error_relative": 0.7060801448176124,
                "scalar_energy_j": 0.00022948622557997643,
                "quadrature_order": 12,
                "status": "DIAGNOSTIC_UNQUALIFIED",
            },
        ),
    ],
)
def test_tet4_integrated_error_full_output_matches_baseline(order: int, expected: dict) -> None:
    actual = field_error_draft.integrated_errors(_MESH, _FIELD, order=order)

    assert actual.keys() == expected.keys()
    for name, value in expected.items():
        if isinstance(value, float):
            assert actual[name] == pytest.approx(value, rel=2.0e-12, abs=1.0e-15)
        else:
            assert actual[name] == value


def test_tet4_sample_matches_affine_map_and_linear_field() -> None:
    sample = field_error_draft.sample_cell_reference(
        "TET4", _MESH["connectivity_zero_based"][0], _MESH["nodes_integer"], 10,
        _FIELD, (0.2, 0.25, 0.1),
    )

    assert sample["point_m"] == pytest.approx((0.26, 0.275, 0.16))
    assert sample["displacement_m"] == pytest.approx((9.7e-6, -8.55e-6, 6.9e-6))
    assert sample["strain"] == pytest.approx((
        1.25e-5, 4.1428571428571416e-5, 3.5e-5,
        -2.6785714285714264e-6, 4.6190476190476194e-5, -3.3333333333333335e-5,
    ))
    assert sample["jacobian_det_m3"] == pytest.approx(0.336)


@pytest.mark.parametrize("order", [0, 1, 2, 3, 5, 7, 9, 13, True, 4.0])
def test_tet4_integrated_errors_reject_unsupported_quadrature_order(order: object) -> None:
    with pytest.raises(ValueError, match="quadrature order"):
        field_error_draft.integrated_errors(_MESH, _FIELD, order=order)


@pytest.mark.parametrize(
    "mesh", [
        {**_MESH, "nodes_integer": [(1, 1, 1), (1, 8, 1), (9, 1, 1), (1, 1, 7)]},
        {**_MESH, "nodes_integer": [(1, 1, 1), (9, 1, 1), (1, 8, 1), (5, 4, 1)]},
    ],
)
def test_tet4_sample_rejects_inverted_or_degenerate_geometry(mesh: dict) -> None:
    with pytest.raises(ValueError, match="Jacobian must be finite and positive"):
        field_error_draft.sample_cell_reference(
            "TET4", mesh["connectivity_zero_based"][0], mesh["nodes_integer"], 10,
            _FIELD, (0.2, 0.25, 0.1),
        )


@pytest.mark.parametrize(
    ("mesh", "field", "message"),
    [
        ({**_MESH, "family": "TET10"}, _FIELD, "family/connectivity node count mismatch"),
        ({**_MESH, "integer_coordinate_denominator": 0}, _FIELD, "invalid integer coordinate denominator"),
        ({**_MESH, "connectivity_zero_based": [[0, 1, 2, 4]]}, _FIELD, "invalid cell node indices"),
        (_MESH, _FIELD[:-1], "displacement/node count mismatch"),
        (_MESH, [*_FIELD[:-1], (0.0, 0.0, float("nan"))], "finite triples"),
    ],
)
def test_tet4_sample_rejects_incompatible_postprocessing_inputs(
    mesh: dict, field: list[tuple[float, float, float]], message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        field_error_draft.sample_cell_reference(
            mesh["family"], mesh["connectivity_zero_based"][0], mesh["nodes_integer"],
            mesh["integer_coordinate_denominator"], field, (0.2, 0.25, 0.1),
        )


# These integration edge cases were also executed against the immutable
# baseline source loaded directly from git show (not via FEM).  They capture
# its lazy field validation and geometry-before-field exception ordering.
_MESH_WITH_UNUSED_NODE = {
    **_MESH,
    "nodes_integer": [*_MESH["nodes_integer"], (8, 8, 8)],
}
_FIELD_WITH_UNUSED_NODE = [*_FIELD, (1.0e-5, -2.0e-5, 3.0e-5)]


@pytest.mark.parametrize(
    "invalid_vector",
    [
        (True, 0.0, 0.0),
        (float("nan"), 0.0, 0.0),
        (float("inf"), 0.0, 0.0),
        (1.0, 2.0),
    ],
)
def test_tet4_integrated_errors_reject_invalid_unused_node_field(invalid_vector: tuple) -> None:
    field = [*_FIELD_WITH_UNUSED_NODE[:4], invalid_vector]

    with pytest.raises(ValueError, match="nodal displacements must be finite triples"):
        field_error_draft.integrated_errors(_MESH_WITH_UNUSED_NODE, field, order=4)


def test_tet4_integrated_errors_empty_connectivity_preserves_baseline_norm_error() -> None:
    mesh = {**_MESH_WITH_UNUSED_NODE, "connectivity_zero_based": []}
    field = [*_FIELD_WITH_UNUSED_NODE[:4], (float("nan"), 0.0, 0.0)]

    # The frozen baseline checked only field length before looping. With no
    # cells it reached the zero-reference-norm check without inspecting values.
    with pytest.raises(ValueError, match="exact MMS reference norm is zero or unavailable"):
        field_error_draft.integrated_errors(mesh, field, order=4)


def test_tet4_integrated_errors_checks_first_cell_geometry_before_invalid_field() -> None:
    inverted_mesh = {
        **_MESH_WITH_UNUSED_NODE,
        "nodes_integer": [(1, 1, 1), (1, 8, 1), (9, 1, 1), (1, 1, 7), (8, 8, 8)],
    }
    field = [*_FIELD_WITH_UNUSED_NODE[:4], (float("nan"), 0.0, 0.0)]

    with pytest.raises(ValueError, match="cell Jacobian must be finite and positive"):
        field_error_draft.integrated_errors(inverted_mesh, field, order=4)


def test_tet4_integrated_errors_checks_geometry_of_each_following_cell() -> None:
    mesh = {
        **_MESH,
        "nodes_integer": [
            (1, 1, 1), (9, 1, 1), (1, 8, 1), (1, 1, 7),
            (1, 8, 1), (9, 1, 1), (1, 1, 7),
        ],
        "connectivity_zero_based": [[0, 1, 2, 3], [0, 4, 5, 6]],
    }
    field = [*_FIELD, *_FIELD[:3]]

    # The first cell is valid and processed; the second cell's inverted
    # orientation still raises the baseline geometry error.
    with pytest.raises(ValueError, match="cell Jacobian must be finite and positive"):
        field_error_draft.integrated_errors(mesh, field, order=4)


def _non_tet4_mesh(family: str) -> dict:
    def midpoint(left: tuple[int, int, int], right: tuple[int, int, int]) -> tuple[int, int, int]:
        return tuple((left[axis] + right[axis]) // 2 for axis in range(3))

    if family == "TET10":
        corners = [(2, 2, 2), (18, 2, 2), (2, 16, 2), (2, 2, 14)]
        edges = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))
        nodes = corners + [midpoint(corners[left], corners[right]) for left, right in edges]
        return {
            "family": family,
            "nodes_integer": nodes,
            "connectivity_zero_based": [list(range(10))],
            "integer_coordinate_denominator": 20,
        }

    corners = [
        (2, 2, 2), (8, 2, 2), (8, 8, 2), (2, 8, 2),
        (2, 2, 6), (8, 2, 6), (8, 8, 6), (2, 8, 6),
    ]
    if family == "HEX8":
        nodes = corners
    elif family == "HEX20":
        edges = ((0, 1), (0, 3), (0, 4), (1, 2), (1, 5), (3, 2),
                 (2, 6), (3, 7), (4, 5), (4, 7), (5, 6), (7, 6))
        nodes = corners + [midpoint(corners[left], corners[right]) for left, right in edges]
    else:
        raise AssertionError(f"unexpected fixture family: {family}")
    return {
        "family": family,
        "nodes_integer": nodes,
        "connectivity_zero_based": [list(range(len(nodes)))],
        "integer_coordinate_denominator": 10,
    }


def _sheared_non_tet4_mesh(family: str) -> dict:
    """Return a translated, skewed affine cell inside the MMS unit domain."""
    mesh = _non_tet4_mesh(family)
    center_y, center_z = (9, 8) if family == "TET10" else (5, 4)
    mesh["nodes_integer"] = [
        (20 * x + y - center_y, 20 * y + z - center_z, 20 * z)
        for x, y, z in mesh["nodes_integer"]
    ]
    mesh["integer_coordinate_denominator"] *= 20
    return mesh


_NON_TET4_BASELINE_OUTPUTS = {
    ("TET10", 8): {
        "displacement_l2_m_5_2": 5.389253904980166e-05,
        "displacement_relative_l2": 7.081840084596093,
        "energy_error_norm_sqrt_j": 0.08652903616884988,
        "energy_error_relative": 2.061928525648247,
        "strain_error_l2_m_3_2": 9.23924844895134e-05,
        "strain_error_relative": 2.3001740216337585,
        "stress_error_l2_pa_m_3_2": 89.78601463375027,
        "stress_error_relative": 1.7426523962820621,
        "scalar_energy_j": 0.0034871143925518967,
        "quadrature_order": 8,
        "status": "DIAGNOSTIC_UNQUALIFIED",
    },
    ("TET10", 12): {
        "displacement_l2_m_5_2": 5.3892539053557e-05,
        "displacement_relative_l2": 7.081840060522565,
        "energy_error_norm_sqrt_j": 0.08652903603400026,
        "energy_error_relative": 2.0619285360995514,
        "strain_error_l2_m_3_2": 9.239248438170066e-05,
        "strain_error_relative": 2.300174033150805,
        "stress_error_l2_pa_m_3_2": 89.78601442223861,
        "stress_error_relative": 1.742652404648752,
        "scalar_energy_j": 0.0034871143925518937,
        "quadrature_order": 12,
        "status": "DIAGNOSTIC_UNQUALIFIED",
    },
    ("HEX8", 8): {
        "displacement_l2_m_5_2": 5.336435094379268e-05,
        "displacement_relative_l2": 2.0820301885855637,
        "energy_error_norm_sqrt_j": 0.08212864106352273,
        "energy_error_relative": 1.3427142538974641,
        "strain_error_l2_m_3_2": 8.683753845937244e-05,
        "strain_error_relative": 1.428702184521107,
        "stress_error_l2_pa_m_3_2": 86.89001862784565,
        "stress_error_relative": 1.2135256862728587,
        "scalar_energy_j": 0.0020207820512820494,
        "quadrature_order": 8,
        "status": "DIAGNOSTIC_UNQUALIFIED",
    },
    ("HEX8", 12): {
        "displacement_l2_m_5_2": 5.3364350943792885e-05,
        "displacement_relative_l2": 2.0820301885855343,
        "energy_error_norm_sqrt_j": 0.08212864106352279,
        "energy_error_relative": 1.342714253897464,
        "strain_error_l2_m_3_2": 8.683753845937229e-05,
        "strain_error_relative": 1.4287021845211072,
        "stress_error_l2_pa_m_3_2": 86.89001862784619,
        "stress_error_relative": 1.2135256862728556,
        "scalar_energy_j": 0.0020207820512820438,
        "quadrature_order": 12,
        "status": "DIAGNOSTIC_UNQUALIFIED",
    },
    ("HEX20", 8): {
        "displacement_l2_m_5_2": 0.00024076579380439745,
        "displacement_relative_l2": 9.393567844711722,
        "energy_error_norm_sqrt_j": 0.5945930605104167,
        "energy_error_relative": 9.720952000147578,
        "strain_error_l2_m_3_2": 0.0005970092858055571,
        "strain_error_relative": 9.822347408072185,
        "stress_error_l2_pa_m_3_2": 685.8451490315877,
        "stress_error_relative": 9.578668738928593,
        "scalar_energy_j": 0.1852426527065528,
        "quadrature_order": 8,
        "status": "DIAGNOSTIC_UNQUALIFIED",
    },
    ("HEX20", 12): {
        "displacement_l2_m_5_2": 0.00024076579380439747,
        "displacement_relative_l2": 9.393567844711553,
        "energy_error_norm_sqrt_j": 0.5945930605104167,
        "energy_error_relative": 9.72095200014757,
        "strain_error_l2_m_3_2": 0.0005970092858055581,
        "strain_error_relative": 9.822347408072215,
        "stress_error_l2_pa_m_3_2": 685.8451490315874,
        "stress_error_relative": 9.578668738928508,
        "scalar_energy_j": 0.1852426527065527,
        "quadrature_order": 12,
        "status": "DIAGNOSTIC_UNQUALIFIED",
    },
}


@pytest.mark.parametrize(("family", "order"), sorted(_NON_TET4_BASELINE_OUTPUTS))
def test_optimized_non_tet4_integrated_errors_match_immutable_baseline(
    family: str, order: int,
) -> None:
    mesh = _non_tet4_mesh(family)
    field = [
        (1.2e-5 * (index + 1), -2.1e-5 * (index + 2), 0.7e-5 * (index - 1))
        for index in range(len(mesh["nodes_integer"]))
    ]

    actual = field_error_draft.integrated_errors(mesh, field, order=order)
    expected = _NON_TET4_BASELINE_OUTPUTS[(family, order)]

    assert actual.keys() == expected.keys()
    for name, value in expected.items():
        if isinstance(value, float):
            assert actual[name] == pytest.approx(value, rel=2.0e-12, abs=1.0e-15)
        else:
            assert actual[name] == value


_NON_TET4_SHEARED_BASELINE_OUTPUTS = {
    ("TET10", 8): {
        "displacement_l2_m_5_2": 5.391275677971163e-05,
        "displacement_relative_l2": 7.306476652476794,
        "energy_error_norm_sqrt_j": 0.08563299884918979,
        "energy_error_relative": 2.0819533874757195,
        "strain_error_l2_m_3_2": 9.147121021530311e-05,
        "strain_error_relative": 2.3159280979164,
        "stress_error_l2_pa_m_3_2": 88.78599527891276,
        "stress_error_relative": 1.7648765337386343,
        "scalar_energy_j": 0.003418302625216804,
        "quadrature_order": 8,
        "status": "DIAGNOSTIC_UNQUALIFIED",
    },
    ("TET10", 12): {
        "displacement_l2_m_5_2": 5.39127567839355e-05,
        "displacement_relative_l2": 7.306476622666502,
        "energy_error_norm_sqrt_j": 0.08563299872392478,
        "energy_error_relative": 2.0819533976339386,
        "strain_error_l2_m_3_2": 9.147121011287012e-05,
        "strain_error_relative": 2.315928109234534,
        "stress_error_l2_pa_m_3_2": 88.7859950868798,
        "stress_error_relative": 1.7648765418152201,
        "scalar_energy_j": 0.003418302625216807,
        "quadrature_order": 12,
        "status": "DIAGNOSTIC_UNQUALIFIED",
    },
    ("HEX8", 8): {
        "displacement_l2_m_5_2": 5.3360470128093895e-05,
        "displacement_relative_l2": 2.0824783557694184,
        "energy_error_norm_sqrt_j": 0.08165641449362536,
        "energy_error_relative": 1.3351489937863827,
        "strain_error_l2_m_3_2": 8.612551343530465e-05,
        "strain_error_relative": 1.4170511109331523,
        "stress_error_l2_pa_m_3_2": 86.79778647288606,
        "stress_error_relative": 1.212498281596535,
        "scalar_energy_j": 0.0019655877975160315,
        "quadrature_order": 8,
        "status": "DIAGNOSTIC_UNQUALIFIED",
    },
    ("HEX8", 12): {
        "displacement_l2_m_5_2": 5.336047012809409e-05,
        "displacement_relative_l2": 2.0824783557693847,
        "energy_error_norm_sqrt_j": 0.08165641449362532,
        "energy_error_relative": 1.3351489937863805,
        "strain_error_l2_m_3_2": 8.612551343530453e-05,
        "strain_error_relative": 1.417051110933156,
        "stress_error_l2_pa_m_3_2": 86.79778647288657,
        "stress_error_relative": 1.2124982815965315,
        "scalar_energy_j": 0.0019655877975160246,
        "quadrature_order": 12,
        "status": "DIAGNOSTIC_UNQUALIFIED",
    },
    ("HEX20", 8): {
        "displacement_l2_m_5_2": 0.00024076703295313037,
        "displacement_relative_l2": 9.396321541097837,
        "energy_error_norm_sqrt_j": 0.6008222007249987,
        "energy_error_relative": 9.823933143735157,
        "strain_error_l2_m_3_2": 0.0005996084666741898,
        "strain_error_relative": 9.865553306266673,
        "stress_error_l2_pa_m_3_2": 699.10399440377,
        "stress_error_relative": 9.765944804786445,
        "scalar_energy_j": 0.18906187083974565,
        "quadrature_order": 8,
        "status": "DIAGNOSTIC_UNQUALIFIED",
    },
    ("HEX20", 12): {
        "displacement_l2_m_5_2": 0.0002407670329531302,
        "displacement_relative_l2": 9.396321541097642,
        "energy_error_norm_sqrt_j": 0.6008222007249986,
        "energy_error_relative": 9.823933143735145,
        "strain_error_l2_m_3_2": 0.0005996084666741889,
        "strain_error_relative": 9.865553306266701,
        "stress_error_l2_pa_m_3_2": 699.1039944037694,
        "stress_error_relative": 9.76594480478635,
        "scalar_energy_j": 0.18906187083974568,
        "quadrature_order": 12,
        "status": "DIAGNOSTIC_UNQUALIFIED",
    },
}


@pytest.mark.parametrize(("family", "order"), sorted(_NON_TET4_SHEARED_BASELINE_OUTPUTS))
def test_optimized_non_tet4_sheared_geometry_matches_immutable_baseline(
    family: str, order: int,
) -> None:
    mesh = _sheared_non_tet4_mesh(family)
    field = [
        (1.2e-5 * (index + 1), -2.1e-5 * (index + 2), 0.7e-5 * (index - 1))
        for index in range(len(mesh["nodes_integer"]))
    ]

    actual = field_error_draft.integrated_errors(mesh, field, order=order)
    expected = _NON_TET4_SHEARED_BASELINE_OUTPUTS[(family, order)]

    assert actual.keys() == expected.keys()
    for name, value in expected.items():
        if isinstance(value, float):
            assert actual[name] == pytest.approx(value, rel=2.0e-12, abs=1.0e-15)
        else:
            assert actual[name] == value


@pytest.mark.parametrize("family", ["TET10", "HEX8", "HEX20"])
def test_optimized_non_tet4_integrated_errors_reuses_validation_and_cell_geometry(
    family: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    mesh = _non_tet4_mesh(family)
    cell = mesh["connectivity_zero_based"][0]
    mesh["connectivity_zero_based"] = [cell, cell]
    field = [
        (1.2e-5 * (index + 1), -2.1e-5 * (index + 2), 0.7e-5 * (index - 1))
        for index in range(len(mesh["nodes_integer"]))
    ]
    calls = {"validate": 0, "cell_map": 0, "inverse": 0}
    for name in calls:
        original = getattr(field_error_draft, f"_{name if name != 'validate' else 'validate_nodal_displacements'}")

        def counted(*args: object, _name: str = name, _original=original, **kwargs: object):
            calls[_name] += 1
            return _original(*args, **kwargs)

        monkeypatch.setattr(
            field_error_draft,
            f"_{name if name != 'validate' else 'validate_nodal_displacements'}",
            counted,
        )

    field_error_draft.integrated_errors(mesh, field, order=4)

    assert calls == {"validate": 1, "cell_map": 2, "inverse": 2}
