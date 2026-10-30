"""Pure sampling validation tests with fabricated nodal displacement fields."""
import math

import pytest

from experiments.wp12_vv3d_adaptive import mesh, sampling


@pytest.mark.parametrize("family", mesh.FORMULATIONS)
def test_affine_displacement_reproduces_point_value(family):
    prepared = mesh.generate(family, 2)
    denominator = prepared["integer_coordinate_denominator"]
    coordinates = prepared["nodes_integer"]
    displacements = []
    for integer_point in coordinates:
        x, y, z = (value / denominator for value in integer_point)
        displacements.append((0.3 + 2*x - y, -0.2 + x + 0.5*z, 0.1 - 2*y + z))
    cell = prepared["connectivity_zero_based"][0]
    ref = (0.2, 0.2, 0.2) if family.startswith("TET") else (0.2, -0.3, 0.1)
    result = sampling.sample_cell(family, cell, coordinates, denominator, displacements, ref)
    expected = (0.3 + 2*result["point_m"][0] - result["point_m"][1],
                -0.2 + result["point_m"][0] + 0.5*result["point_m"][2],
                0.1 - 2*result["point_m"][1] + result["point_m"][2])
    for actual, target in zip(result["displacement_m"], expected):
        assert math.isclose(actual, target, rel_tol=1e-12, abs_tol=1e-12)


@pytest.mark.parametrize("ref", [(float("nan"), 0, 0), (0.2, 0.2, 0.7)])
def test_invalid_reference_coordinates_are_refused(ref):
    prepared = mesh.generate("TET4", 2)
    displacements = [(0.0, 0.0, 0.0)] * prepared["summary"]["nodes"]
    with pytest.raises(ValueError):
        sampling.sample_cell("TET4", prepared["connectivity_zero_based"][0],
                             prepared["nodes_integer"], prepared["integer_coordinate_denominator"],
                             displacements, ref)


def test_nonfinite_supplied_field_is_refused():
    prepared = mesh.generate("HEX8", 2)
    displacements = [(0.0, 0.0, 0.0)] * prepared["summary"]["nodes"]
    displacements[0] = (float("inf"), 0.0, 0.0)
    with pytest.raises(ValueError, match="finite triples"):
        sampling.sample_cell("HEX8", prepared["connectivity_zero_based"][0],
                             prepared["nodes_integer"], prepared["integer_coordinate_denominator"],
                             displacements, (0.0, 0.0, 0.0))
