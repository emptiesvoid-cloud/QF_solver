"""Independent MMS error postprocessing for externally supplied nodal fields.

The reference path owns its shape functions, affine maps, Jacobian algebra, and
quadrature implementation. It imports only the analytic MMS field, not the load
adapter, candidate basis, or candidate sampling implementation. It performs no
stiffness/load assembly, solve, or modal analysis.
"""
from __future__ import annotations

import math
from itertools import product
from typing import Sequence

from experiments.wp12_vv3d_adaptive import oracle


_SUPPORTED_ORDERS = frozenset({4, 8, 12})


def _gauss_legendre(order: int) -> tuple[tuple[float, float], ...]:
    """Construct a Gauss-Legendre rule independently from the load rules."""
    if type(order) is not int or order not in _SUPPORTED_ORDERS:
        raise ValueError(f"reference quadrature order must be one of {sorted(_SUPPORTED_ORDERS)}")
    points: list[tuple[float, float]] = []
    for root_index in range(1, order // 2 + 1):
        root = math.cos(math.pi * (root_index - 0.25) / (order + 0.5))
        converged = False
        for _ in range(64):
            p_previous, p_current = 1.0, root
            for degree in range(2, order + 1):
                p_previous, p_current = p_current, (
                    (2 * degree - 1) * root * p_current - (degree - 1) * p_previous
                ) / degree
            derivative = order * (root * p_current - p_previous) / (root * root - 1.0)
            update = p_current / derivative
            root -= update
            if abs(update) <= 2.0e-15:
                converged = True
                break
        if not converged:
            raise ArithmeticError(f"reference Gauss-Legendre root {root_index} did not converge")
        p_previous, p_current = 1.0, root
        for degree in range(2, order + 1):
            p_previous, p_current = p_current, (
                (2 * degree - 1) * root * p_current - (degree - 1) * p_previous
            ) / degree
        derivative = order * (root * p_current - p_previous) / (root * root - 1.0)
        weight = 2.0 / ((1.0 - root * root) * derivative * derivative)
        points.extend(((-root, weight), (root, weight)))
    return tuple(sorted(points))


def _hexahedron_rule(order: int) -> tuple[tuple[float, float, float, float], ...]:
    one_d = _gauss_legendre(order)
    return tuple((r, s, t, wr * ws * wt)
                 for (r, wr), (s, ws), (t, wt) in product(one_d, repeat=3))


def _tetrahedron_rule(order: int) -> tuple[tuple[float, float, float, float], ...]:
    one_d = tuple(((point + 1.0) * 0.5, weight * 0.5)
                  for point, weight in _gauss_legendre(order))
    samples = []
    for (a, wa), (b, wb), (c, wc) in product(one_d, repeat=3):
        r = a
        s = (1.0 - a) * b
        t = (1.0 - a) * (1.0 - b) * c
        weight = wa * wb * wc * (1.0 - a) ** 2 * (1.0 - b)
        samples.append((r, s, t, weight))
    return tuple(samples)


_TET_EDGES = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))
_HEX_CORNERS = ((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
                (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1))
_HEX_EDGES = ((0, 1), (0, 3), (0, 4), (1, 2), (1, 5), (3, 2),
              (2, 6), (3, 7), (4, 5), (4, 7), (5, 6), (7, 6))
_EXPECTED_NODES = {"TET4": 4, "TET10": 10, "HEX8": 8, "HEX20": 20}


def _shape_data(family: str, point: tuple[float, float, float]
                ) -> tuple[tuple[float, ...], tuple[tuple[float, float, float], ...]]:
    """Return independently evaluated shape values and reference gradients."""
    r, s, t = point
    if family in {"TET4", "TET10"}:
        barycentric = (1.0 - r - s - t, r, s, t)
        if min(barycentric) < -1.0e-12:
            raise ValueError("reference point lies outside the tetrahedron")
        derivatives = ((-1.0, -1.0, -1.0), (1.0, 0.0, 0.0),
                       (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
        if family == "TET4":
            return barycentric, derivatives
        values = tuple(value * (2.0 * value - 1.0) for value in barycentric)
        gradients = tuple(tuple((4.0 * barycentric[i] - 1.0) * derivatives[i][axis]
                                for axis in range(3)) for i in range(4))
        edge_values = tuple(4.0 * barycentric[a] * barycentric[b] for a, b in _TET_EDGES)
        edge_gradients = tuple(tuple(4.0 * (derivatives[a][axis] * barycentric[b]
                                             + barycentric[a] * derivatives[b][axis])
                                     for axis in range(3)) for a, b in _TET_EDGES)
        return values + edge_values, gradients + edge_gradients

    if family not in {"HEX8", "HEX20"} or max(abs(value) for value in point) > 1.0 + 1.0e-12:
        raise ValueError("unknown family or reference point outside the hexahedron")
    signs = tuple(tuple(2 * component - 1 for component in corner) for corner in _HEX_CORNERS)
    coordinates = (r, s, t)
    corner_values: list[float] = []
    corner_gradients: list[tuple[float, float, float]] = []
    for sign in signs:
        factors = tuple(1.0 + sign[axis] * coordinates[axis] for axis in range(3))
        product_all = factors[0] * factors[1] * factors[2]
        if family == "HEX8":
            corner_values.append(product_all / 8.0)
        else:
            linear_factor = sum(sign[axis] * coordinates[axis] for axis in range(3)) - 2.0
            corner_values.append(product_all * linear_factor / 8.0)
        gradient = []
        for axis in range(3):
            other_axes = tuple(index for index in range(3) if index != axis)
            product_derivative = (sign[axis] * factors[other_axes[0]]
                                  * factors[other_axes[1]])
            if family == "HEX8":
                gradient.append(product_derivative / 8.0)
            else:
                gradient.append((product_derivative * linear_factor
                                 + product_all * sign[axis]) / 8.0)
        corner_gradients.append(tuple(gradient))
    if family == "HEX8":
        return tuple(corner_values), tuple(corner_gradients)

    edge_values = []
    edge_gradients = []
    for left, right in _HEX_EDGES:
        free_axis = next(axis for axis in range(3) if signs[left][axis] != signs[right][axis])
        fixed_axes = tuple(axis for axis in range(3) if axis != free_axis)
        free_coordinate = coordinates[free_axis]
        fixed_factors = tuple(1.0 + signs[left][axis] * coordinates[axis] for axis in fixed_axes)
        edge_values.append((1.0 - free_coordinate * free_coordinate)
                           * fixed_factors[0] * fixed_factors[1] / 4.0)
        gradient = []
        for axis in range(3):
            if axis == free_axis:
                derivative = (-2.0 * free_coordinate * fixed_factors[0]
                              * fixed_factors[1] / 4.0)
            else:
                other_fixed = fixed_axes[1] if axis == fixed_axes[0] else fixed_axes[0]
                derivative = ((1.0 - free_coordinate * free_coordinate) * signs[left][axis]
                              * (1.0 + signs[left][other_fixed] * coordinates[other_fixed]) / 4.0)
            gradient.append(derivative)
        edge_gradients.append(tuple(gradient))
    return (tuple(corner_values + edge_values),
            tuple(corner_gradients + edge_gradients))


def _determinant(matrix: tuple[tuple[float, float, float], ...]) -> float:
    a, b, c = matrix
    return (a[0] * (b[1] * c[2] - b[2] * c[1])
            - a[1] * (b[0] * c[2] - b[2] * c[0])
            + a[2] * (b[0] * c[1] - b[1] * c[0]))


def _inverse(matrix: tuple[tuple[float, float, float], ...], determinant: float
             ) -> tuple[tuple[float, float, float], ...]:
    a, b, c = matrix
    return (
        ((b[1] * c[2] - b[2] * c[1]) / determinant,
         (a[2] * c[1] - a[1] * c[2]) / determinant,
         (a[1] * b[2] - a[2] * b[1]) / determinant),
        ((b[2] * c[0] - b[0] * c[2]) / determinant,
         (a[0] * c[2] - a[2] * c[0]) / determinant,
         (a[2] * b[0] - a[0] * b[2]) / determinant),
        ((b[0] * c[1] - b[1] * c[0]) / determinant,
         (a[1] * c[0] - a[0] * c[1]) / determinant,
         (a[0] * b[1] - a[1] * b[0]) / determinant),
    )


def _cell_map(family: str, cell: Sequence[int], nodes_integer: Sequence[Sequence[int]], denominator: int
              ) -> tuple[tuple[float, float, float], tuple[tuple[float, float, float], ...], float]:
    """Build a straight-sided affine cell map without the load-adapter helper."""
    if family not in _EXPECTED_NODES or len(cell) != _EXPECTED_NODES[family]:
        raise ValueError("family/connectivity node count mismatch")
    if type(denominator) is not int or denominator <= 0:
        raise ValueError("invalid integer coordinate denominator")
    if len(set(cell)) != len(cell) or any(type(index) is not int or index < 0
                                           or index >= len(nodes_integer) for index in cell):
        raise ValueError("invalid cell node indices")
    points = [tuple(float(value) / denominator for value in nodes_integer[index]) for index in cell]
    if any(len(point) != 3 or not all(math.isfinite(value) for value in point) for point in points):
        raise ValueError("cell coordinates must be finite triples")
    corner_count = 4 if family.startswith("TET") else 8
    corners = points[:corner_count]
    if family.startswith("TET"):
        origin = corners[0]
        columns = tuple(tuple(corners[column + 1][axis] - origin[axis] for axis in range(3))
                        for column in range(3))
        jacobian = tuple(tuple(columns[column][axis] for column in range(3)) for axis in range(3))
    else:
        corner_origin = corners[0]
        edge_vectors = tuple(tuple(corners[node][axis] - corner_origin[axis] for axis in range(3))
                             for node in (1, 3, 4))
        jacobian = tuple(tuple(edge_vectors[column][axis] * 0.5 for column in range(3))
                         for axis in range(3))
        origin = tuple(corner_origin[axis] + sum(jacobian[axis]) for axis in range(3))
        # Verify every corner against the independently formed parallelepiped map.
        for node, corner in enumerate(_HEX_CORNERS):
            predicted = tuple(origin[axis] + sum(jacobian[axis][ref_axis]
                                                  * (2 * corner[ref_axis] - 1)
                                                  for ref_axis in range(3))
                              for axis in range(3))
            if any(abs(predicted[axis] - corners[node][axis]) > 1.0e-12 for axis in range(3)):
                raise ValueError("hexahedron corners are not an affine parallelepiped")
    determinant = _determinant(jacobian)
    if not math.isfinite(determinant) or determinant <= 0.0:
        raise ValueError("cell Jacobian must be finite and positive")
    if family in {"TET10", "HEX20"}:
        edges = _TET_EDGES if family == "TET10" else _HEX_EDGES
        for offset, (left, right) in enumerate(edges, corner_count):
            expected = tuple((corners[left][axis] + corners[right][axis]) * 0.5
                             for axis in range(3))
            if any(abs(points[offset][axis] - expected[axis]) > 1.0e-12 for axis in range(3)):
                raise ValueError("quadratic cell must have straight-sided midpoint nodes")
    return tuple(origin), jacobian, determinant


def sample_cell_reference(
    family: str,
    cell: Sequence[int],
    nodes_integer: Sequence[Sequence[int]],
    denominator: int,
    nodal_displacements: Sequence[Sequence[float]],
    reference_point: tuple[float, float, float],
) -> dict[str, object]:
    """Interpolate a supplied nodal field and its strain at one reference point."""
    if len(nodal_displacements) != len(nodes_integer):
        raise ValueError("displacement/node count mismatch")
    if any(len(vector) != 3 or any(isinstance(value, bool)
                                   or not isinstance(value, (int, float))
                                   or not math.isfinite(value) for value in vector)
           for vector in nodal_displacements):
        raise ValueError("nodal displacements must be finite triples")
    origin, jacobian, determinant = _cell_map(family, cell, nodes_integer, denominator)
    values, gradients_reference = _shape_data(family, reference_point)
    if len(values) != len(cell):
        raise ValueError("shape/connectivity node count mismatch")
    inverse = _inverse(jacobian, determinant)
    physical_point = tuple(origin[axis] + sum(jacobian[axis][ref_axis] * reference_point[ref_axis]
                                               for ref_axis in range(3))
                           for axis in range(3))
    displacement = tuple(sum(values[local] * nodal_displacements[node][component]
                             for local, node in enumerate(cell)) for component in range(3))
    gradient_u = [[0.0] * 3 for _ in range(3)]
    for local, node in enumerate(cell):
        gradient_physical = tuple(sum(gradients_reference[local][ref_axis] * inverse[ref_axis][axis]
                                      for ref_axis in range(3)) for axis in range(3))
        for component in range(3):
            for axis in range(3):
                gradient_u[component][axis] += nodal_displacements[node][component] * gradient_physical[axis]
    strain = (
        gradient_u[0][0], gradient_u[1][1], gradient_u[2][2],
        gradient_u[0][1] + gradient_u[1][0],
        gradient_u[1][2] + gradient_u[2][1],
        gradient_u[0][2] + gradient_u[2][0],
    )
    return {"point_m": physical_point, "displacement_m": displacement, "strain": strain,
            "jacobian_det_m3": determinant}


def _material() -> tuple[float, float]:
    # Independently transcribed isotropic small-strain conversion for E and nu.
    e_pa = oracle.E_PA
    poisson = oracle.NU
    return (e_pa * poisson / ((1.0 + poisson) * (1.0 - 2.0 * poisson)),
            e_pa / (2.0 * (1.0 + poisson)))


def integrated_errors(prepared_mesh: dict, nodal_displacements: Sequence[Sequence[float]], *, order: int
                      ) -> dict[str, float | int | str]:
    """Integrate independent L2/energy errors from supplied nodal values only."""
    family = prepared_mesh.get("family")
    nodes_integer = prepared_mesh.get("nodes_integer")
    connectivity = prepared_mesh.get("connectivity_zero_based")
    denominator = prepared_mesh.get("integer_coordinate_denominator")
    if (family not in _EXPECTED_NODES or not isinstance(nodes_integer, list)
            or not isinstance(connectivity, list) or len(nodal_displacements) != len(nodes_integer)):
        raise ValueError("prepared mesh and supplied displacement field are incompatible")
    rule = _tetrahedron_rule(order) if family.startswith("TET") else _hexahedron_rule(order)
    lam, mu = _material()
    sums = {name: 0.0 for name in (
        "displacement_error_sq", "energy_error_sq", "strain_error_sq", "stress_error_sq",
        "exact_displacement_sq", "exact_energy_sq", "exact_strain_sq", "exact_stress_sq",
        "scalar_energy_j",
    )}
    for cell in connectivity:
        _cell_map(family, cell, nodes_integer, denominator)
        for r, s, t, reference_weight in rule:
            sample = sample_cell_reference(family, cell, nodes_integer, denominator,
                                           nodal_displacements, (r, s, t))
            exact = oracle.field(sample["point_m"])
            strain = sample["strain"]
            trace = sum(strain[:3])
            stress = (tuple(lam * trace + 2.0 * mu * strain[index] for index in range(3))
                      + tuple(mu * strain[index] for index in range(3, 6)))
            weight = reference_weight * sample["jacobian_det_m3"]
            displacement_error = tuple(sample["displacement_m"][index] - exact["u_m"][index]
                                        for index in range(3))
            strain_error = tuple(strain[index] - exact["strain"][index] for index in range(6))
            stress_error = tuple(stress[index] - exact["stress_pa"][index] for index in range(6))

            def strain_density(values: Sequence[float]) -> float:
                return (lam * sum(values[:3]) ** 2
                        + 2.0 * mu * (sum(value * value for value in values[:3])
                                      + 0.5 * sum(value * value for value in values[3:])))

            def tensor_density(values: Sequence[float]) -> float:
                return (sum(value * value for value in values[:3])
                        + 2.0 * sum(value * value for value in values[3:]))

            sums["displacement_error_sq"] += weight * sum(value * value for value in displacement_error)
            sums["exact_displacement_sq"] += weight * sum(value * value for value in exact["u_m"])
            sums["energy_error_sq"] += weight * strain_density(strain_error)
            sums["exact_energy_sq"] += weight * strain_density(exact["strain"])
            sums["strain_error_sq"] += weight * (sum(value * value for value in strain_error[:3])
                                                  + 0.5 * sum(value * value for value in strain_error[3:]))
            sums["exact_strain_sq"] += weight * (sum(value * value for value in exact["strain"][:3])
                                                 + 0.5 * sum(value * value for value in exact["strain"][3:]))
            sums["stress_error_sq"] += weight * tensor_density(stress_error)
            sums["exact_stress_sq"] += weight * tensor_density(exact["stress_pa"])
            sums["scalar_energy_j"] += 0.5 * weight * sum(strain[index] * stress[index]
                                                           for index in range(3))
            sums["scalar_energy_j"] += 0.5 * weight * sum(strain[index] * stress[index]
                                                           for index in range(3, 6))
    if not all(math.isfinite(value) and value >= 0.0 for value in sums.values()):
        raise ValueError("independent postprocessing produced a nonfinite or negative integral")
    norm_keys = ("exact_displacement_sq", "exact_energy_sq", "exact_strain_sq", "exact_stress_sq")
    if any(sums[key] <= 0.0 for key in norm_keys):
        raise ValueError("exact MMS reference norm is zero or unavailable")
    values = {name: math.sqrt(value) for name, value in sums.items() if name.endswith("_sq")}
    return {
        "displacement_l2_m_5_2": values["displacement_error_sq"],
        "displacement_relative_l2": math.sqrt(sums["displacement_error_sq"]
                                               / sums["exact_displacement_sq"]),
        "energy_error_norm_sqrt_j": values["energy_error_sq"],
        "energy_error_relative": math.sqrt(sums["energy_error_sq"] / sums["exact_energy_sq"]),
        "strain_error_l2_m_3_2": values["strain_error_sq"],
        "strain_error_relative": math.sqrt(sums["strain_error_sq"] / sums["exact_strain_sq"]),
        "stress_error_l2_pa_m_3_2": values["stress_error_sq"],
        "stress_error_relative": math.sqrt(sums["stress_error_sq"] / sums["exact_stress_sq"]),
        "scalar_energy_j": sums["scalar_energy_j"],
        "quadrature_order": order,
        "status": "DIAGNOSTIC_UNQUALIFIED",
    }
