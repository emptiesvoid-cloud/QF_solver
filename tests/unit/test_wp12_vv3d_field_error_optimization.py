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
