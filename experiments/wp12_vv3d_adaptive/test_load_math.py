"""Synthetic load-adapter math checks; deliberately no load assembly or solve."""
import math
import unittest

from experiments.wp12_vv3d_adaptive import basis, load_assembly_draft, mesh, quadrature


class LoadAdapterMath(unittest.TestCase):
    def test_affine_jacobians_for_all_four_families(self):
        for family in mesh.FORMULATIONS:
            for n in mesh.LEVELS:
                prepared = mesh.generate(family, n)
                expected = 1.0 / (n**3 * (1 if family.startswith("TET") else 8))
                for cell in prepared["connectivity_zero_based"]:
                    with self.subTest(family=family, n=n):
                        _origin, jacobian, determinant = load_assembly_draft._affine_cell_geometry(
                            family, cell, prepared["nodes_integer"], prepared["integer_coordinate_denominator"])
                        self.assertAlmostEqual(determinant, expected, delta=1e-14)
                        self.assertTrue(all(math.isfinite(value) for row in jacobian for value in row))

    def test_basis_mapping_jacobians_are_constant_on_affine_cells(self):
        points = {
            "TET4": (0.13, 0.19, 0.17), "TET10": (0.13, 0.19, 0.17),
            "HEX8": (-0.21, 0.17, 0.31), "HEX20": (-0.21, 0.17, 0.31),
        }
        step = 1e-6
        for family in mesh.FORMULATIONS:
            prepared = mesh.generate(family, 2)
            cell = prepared["connectivity_zero_based"][0]
            coordinates = prepared["nodes_integer"]
            denominator = prepared["integer_coordinate_denominator"]
            _origin, expected, _determinant = load_assembly_draft._affine_cell_geometry(
                family, cell, coordinates, denominator)
            physical_nodes = [tuple(coordinates[i][axis] / denominator for axis in range(3)) for i in cell]
            point = points[family]
            for ref_axis in range(3):
                plus, minus = list(point), list(point)
                plus[ref_axis] += step
                minus[ref_axis] -= step
                mapped_plus = tuple(sum(basis.shape_values(family, tuple(plus))[j] * physical_nodes[j][axis]
                                        for j in range(len(cell))) for axis in range(3))
                mapped_minus = tuple(sum(basis.shape_values(family, tuple(minus))[j] * physical_nodes[j][axis]
                                         for j in range(len(cell))) for axis in range(3))
                for physical_axis in range(3):
                    derivative = (mapped_plus[physical_axis] - mapped_minus[physical_axis]) / (2 * step)
                    with self.subTest(family=family, ref_axis=ref_axis, physical_axis=physical_axis):
                        self.assertAlmostEqual(derivative, expected[physical_axis][ref_axis], delta=2e-9)

    def test_supported_quadrature_orders_integrate_each_reference_shape(self):
        expected = {
            "TET4": (1/24,) * 4,
            "TET10": (-1/120,) * 4 + (1/30,) * 6,
            "HEX8": (1.0,) * 8,
            "HEX20": (-1.0,) * 8 + (4/3,) * 12,
        }
        for family in mesh.FORMULATIONS:
            for order in (4, 8, 12):
                rule = (quadrature.tetrahedron_duffy_rule(order) if family.startswith("TET")
                        else quadrature.hexahedron_rule(order))
                integrals = [0.0] * len(expected[family])
                for r, s, t, weight in rule:
                    values = basis.shape_values(family, (r, s, t))
                    for i, value in enumerate(values):
                        integrals[i] += weight * value
                for actual, target in zip(integrals, expected[family]):
                    with self.subTest(family=family, order=order, actual=actual):
                        self.assertAlmostEqual(actual, target, delta=2e-13)

    def test_geometry_contract_rejects_curved_or_invalid_cells(self):
        for family in ("TET10", "HEX20"):
            prepared = mesh.generate(family, 2)
            cell = prepared["connectivity_zero_based"][0]
            coordinates = list(prepared["nodes_integer"])
            node = cell[4 if family == "TET10" else 8]
            p = coordinates[node]
            coordinates[node] = (p[0] + 1, p[1], p[2])
            with self.subTest(family=family), self.assertRaisesRegex(ValueError, "straight-sided affine"):
                load_assembly_draft._affine_cell_geometry(
                    family, cell, coordinates, prepared["integer_coordinate_denominator"])
        prepared = mesh.generate("HEX8", 2)
        cell = list(prepared["connectivity_zero_based"][0])
        cell[1] = cell[0]
        with self.assertRaisesRegex(ValueError, "node count|indices"):
            load_assembly_draft._affine_cell_geometry(
                "HEX8", cell, prepared["nodes_integer"], prepared["integer_coordinate_denominator"])

    def test_entry_point_requires_a_complete_controller_context(self):
        prepared = mesh.generate("HEX8", 2)
        with self.assertRaisesRegex(PermissionError, "validated controller permit"):
            load_assembly_draft.assemble_body_load(prepared, order=8)

    def test_entry_point_refuses_without_or_after_controller_validation(self):
        prepared = mesh.generate("TET4", 2)
        context = {
            "campaign_id": "WP12-VV3D-ADAPTIVE-20261029-R1",
            "case_id": "VV3D-TET4-L1",
            "nodeid": "tests/unit/test_wp12_vv3d_adaptive_prepared.py::test_prepared_fem_case[VV3D-TET4-L1]",
            "manifest_sha256": "a" * 64,
            "scientific_fingerprint": "b" * 64,
            "controller_fingerprint": "c" * 64,
        }
        called = []
        with self.assertRaisesRegex(PermissionError, "rejected"):
            load_assembly_draft.assemble_body_load(
                prepared, order=8, execution_context=context,
                permit_validator=lambda received: called.append(received) or False,
            )
        self.assertEqual(called, [context])
        with self.assertRaisesRegex(PermissionError, "requires a validated controller permit"):
            load_assembly_draft.assemble_body_load(
                prepared, order=8, execution_context={"case_id": context["case_id"]},
                permit_validator=lambda _received: True,
            )


if __name__ == "__main__":
    unittest.main()
