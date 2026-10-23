"""Synthetic exact-math tests; never imports or evaluates the FEM solver."""

import sys
import unittest
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rigorous_math import (  # noqa: E402
    RationalInterval,
    as_fraction,
    coefficients_from_affine_deviator,
    evaluate_margin,
    parse_serialized_interval,
    polynomial_range,
    serialize_interval,
    sqrt_enclosure,
)


class RationalInputTests(unittest.TestCase):
    def test_float_is_exact_binary64_not_shortest_decimal(self):
        self.assertEqual(as_fraction(0.1), Fraction(*0.1.as_integer_ratio()))
        self.assertNotEqual(as_fraction(0.1), Fraction(1, 10))

    def test_decimal_is_exact_representation_and_nonfinite_refused(self):
        self.assertEqual(as_fraction(Decimal("0.100")), Fraction(1, 10))
        with self.assertRaises(ValueError):
            as_fraction(Decimal("NaN"))
        with self.assertRaises(ValueError):
            as_fraction(float("inf"))

    def test_affine_deviator_coefficients_exact(self):
        self.assertEqual(coefficients_from_affine_deviator([1, 0], [0, 2]),
                         (Fraction(3, 2), Fraction(0), Fraction(6)))


class PolynomialRangeTests(unittest.TestCase):
    def test_monotonic_endpoint_extrema_left_and_right(self):
        # Increasing linear: minimum at left and maximum at right endpoint.
        self.assertEqual(polynomial_range(2, 1, 0, RationalInterval(-1, 1)), RationalInterval(1, 3))
        # Decreasing linear: minimum at right and maximum at left endpoint.
        self.assertEqual(polynomial_range(2, -1, 0, RationalInterval(-1, 1)), RationalInterval(1, 3))

    def test_interior_minimum_and_endpoint_maximum(self):
        self.assertEqual(polynomial_range(1, -2, 1, RationalInterval(0, 2)), RationalInterval(0, 1))
        # Concave quadratic: minimum at the left endpoint, maximum at its interior vertex.
        self.assertEqual(polynomial_range(0, 0, -1, RationalInterval(-2, 1)), RationalInterval(-4, 0))

    def test_linear_c_zero_and_singleton_zero(self):
        self.assertEqual(polynomial_range(3, 2, 0, RationalInterval(-2, 4)), RationalInterval(-1, 11))
        self.assertEqual(polynomial_range(2, RationalInterval(-3, 5), 8, RationalInterval(0)), RationalInterval(2))

    def test_interval_coefficients_are_conservative_across_zero(self):
        self.assertEqual(polynomial_range(RationalInterval(1, 2), RationalInterval(-2, 3),
                                          RationalInterval(4, 5), RationalInterval(-1, 1)),
                         RationalInterval(Fraction(7, 16), 10))

    def test_large_scale_exact_extremum(self):
        scale = 10**100
        result = polynomial_range(0, -2*scale, scale, RationalInterval(0, 2))
        self.assertEqual(result, RationalInterval(-scale, 0))


class SqrtAndSerializationTests(unittest.TestCase):
    def test_sqrt_bounds_are_checked_and_adverse_rounding_is_outward(self):
        bound = sqrt_enclosure(Fraction(2), 16)
        self.assertLessEqual(bound.lo**2, 2)
        self.assertGreaterEqual(bound.hi**2, 2)
        payload = serialize_interval(RationalInterval(Fraction(1, 3), Fraction(2, 3)), 2)
        self.assertEqual(payload["decimal_outward"]["lo"], "0.33")
        self.assertEqual(payload["decimal_outward"]["hi"], "0.67")
        self.assertEqual(parse_serialized_interval(payload), RationalInterval(Fraction(1, 3), Fraction(2, 3)))

    def test_negative_crossing_and_tiny_decimal_displays_round_outward(self):
        negative = serialize_interval(RationalInterval(Fraction(-2, 3), Fraction(-1, 3)), 2)
        self.assertEqual(negative["decimal_outward"]["lo"], "-0.67")
        self.assertEqual(negative["decimal_outward"]["hi"], "-0.33")
        crossing = serialize_interval(RationalInterval(Fraction(-1, 3), Fraction(1, 3)), 2)
        self.assertEqual(crossing["decimal_outward"]["lo"], "-0.34")
        self.assertEqual(crossing["decimal_outward"]["hi"], "0.34")
        tiny_negative = serialize_interval(RationalInterval(Fraction(-1, 10**8)), 2)
        self.assertEqual(tiny_negative["decimal_outward"]["lo"], "-0.01")
        self.assertEqual(tiny_negative["decimal_outward"]["hi"], "0.00")

    def test_serialized_tampering_and_malformed_data_refused(self):
        payload = serialize_interval(RationalInterval(Fraction(1, 3), Fraction(2, 3)), 2)
        payload["hi"]["numerator"] = "3"
        with self.assertRaises(ValueError):
            parse_serialized_interval(payload)
        with self.assertRaises(ValueError):
            parse_serialized_interval({"lo": {"numerator": "1", "denominator": "0"}})


class VerdictTests(unittest.TestCase):
    def run_eval(self, A, B, C, R, branch, *, linked=True, s=None):
        return evaluate_margin(A, B, C, R, s or RationalInterval(-1, 1), branch,
                               provenance_valid=True,
                               production_branch_linkage_valid=linked)

    def test_strictly_positive_and_negative_branches(self):
        positive = self.run_eval(4, 0, 0, 1, "plastic")
        negative = self.run_eval(1, 0, 0, 2, "elastic")
        self.assertEqual(positive["mathematical_verdict"], "PASS")
        self.assertEqual(negative["mathematical_verdict"], "PASS")
        self.assertEqual(positive["action_verdict"], "INCONCLUSIVE")

    def test_near_zero_and_touching_zero_never_pass(self):
        near = self.run_eval(Fraction(1000001, 1000000)**2, 0, 0, 1, "plastic")
        touch_plastic = self.run_eval(1, 0, 0, 1, "plastic")
        touch_elastic = self.run_eval(1, 0, 0, 1, "elastic")
        self.assertEqual(near["mathematical_verdict"], "PASS")
        self.assertEqual(touch_plastic["mathematical_verdict"], "INCONCLUSIVE")
        self.assertEqual(touch_elastic["mathematical_verdict"], "INCONCLUSIVE")

    def test_interval_straddling_zero_and_adverse_resistance(self):
        straddle = self.run_eval(1, 0, 0, RationalInterval(Fraction(9, 10), Fraction(11, 10)), "plastic")
        adverse = self.run_eval(1, 0, 0, RationalInterval(Fraction(1, 2), Fraction(3, 2)), "elastic")
        self.assertEqual(straddle["mathematical_verdict"], "INCONCLUSIVE")
        self.assertEqual(adverse["mathematical_verdict"], "INCONCLUSIVE")

    def test_wrong_sign_fails_but_missing_provenance_invalidates(self):
        failed = self.run_eval(1, 0, 0, 2, "plastic")
        invalid = evaluate_margin(1, 0, 0, 2, RationalInterval(-1, 1), "plastic", provenance_valid=False)
        self.assertEqual(failed["mathematical_verdict"], "FAIL")
        self.assertEqual(failed["action_verdict"], "INCONCLUSIVE")
        self.assertEqual(invalid["action_verdict"], "INVALID_PROTOCOL")

    def test_interior_minimum_proves_plastic_violation_despite_positive_base_and_endpoints(self):
        # q²=(s-1/2)²+1/4=s²-s+1/2; at s=0 and both endpoints g>0,
        # while the interior minimum has sqrt(q²)=1/2 < R=3/5.
        result = self.run_eval(Fraction(1, 2), -1, 1, Fraction(3, 5), "plastic")
        self.assertEqual(result["minimum_margin_range"], serialize_interval(
            RationalInterval(Fraction(-1, 10)), 12))
        self.assertEqual(result["mathematical_verdict"], "FAIL")

    def test_elastic_maximum_violation_when_base_is_negative(self):
        # At s=0, sqrt(1/2)-1 < 0; at the endpoint maximum sqrt(5/2)-1 > 0.
        result = self.run_eval(Fraction(1, 2), -1, 1, 1, "elastic")
        self.assertGreater(parse_serialized_interval(result["maximum_margin_range"]).lo, 0)
        self.assertEqual(result["mathematical_verdict"], "FAIL")

    def test_mathematical_pass_is_not_complete_without_production_linkage(self):
        limited = self.run_eval(4, 0, 0, 1, "plastic", linked=True)
        self.assertEqual(limited["mathematical_verdict"], "PASS")
        self.assertEqual(limited["action_verdict"], "INCONCLUSIVE")
        self.assertEqual(limited["sqrt_squared_checks"]["maximum_extremum_upper"]["upper_squared_ge_input"], True)

    def test_invalid_branch_and_negative_radicand(self):
        self.assertEqual(self.run_eval(1, 0, 0, 0, "other")["action_verdict"], "INVALID_PROTOCOL")
        uncertain = self.run_eval(RationalInterval(0, 1), 0, -1,
                                  RationalInterval(0, 2), "plastic")
        contradictory = self.run_eval(-2, 0, 0, 0, "plastic")
        self.assertEqual(uncertain["action_verdict"], "INCONCLUSIVE")
        self.assertEqual(contradictory["action_verdict"], "INVALID_PROTOCOL")

    def test_complete_action_pass_requires_every_evidence_gate(self):
        result = evaluate_margin(4, 0, 0, 1, RationalInterval(-1, 1), "plastic",
                                 provenance_valid=True, complete_archive_inputs_valid=True,
                                 production_branch_linkage_valid=True,
                                 production_rounding_budget_valid=True)
        self.assertEqual(result["mathematical_verdict"], "PASS")
        self.assertEqual(result["action_verdict"], "PASS")

    def test_decisive_fail_needs_archive_and_base_branch_identity_not_positive_budget(self):
        result = evaluate_margin(Fraction(1, 2), -1, 1, Fraction(3, 5),
                                 RationalInterval(-1, 1), "plastic", provenance_valid=True,
                                 complete_archive_inputs_valid=True,
                                 production_branch_linkage_valid=True,
                                 production_rounding_budget_valid=False)
        self.assertEqual(result["mathematical_verdict"], "FAIL")
        self.assertEqual(result["action_verdict"], "FAIL")


if __name__ == "__main__":
    unittest.main(verbosity=2)
