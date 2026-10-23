"""Synthetic scalar tests for production branch reconstruction; no FEM imports."""

import math
import sys
import unittest
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from production_branch_budget import (  # noqa: E402
    _outward_binary64,
    _source_denominator,
    certify_production_branch,
)
from rigorous_math import RationalInterval, as_fraction, parse_serialized_interval  # noqa: E402


class ProductionBranchBudgetTests(unittest.TestCase):
    # Frozen source scalar inputs used by the eight exploratory actions.
    E = 210.0e9
    NU = 0.30
    H = 1.5e9

    def call(self, **overrides):
        args = dict(
            expected_branch="plastic",
            archived_elastic=False,
            archived_yield_function=0.0,  # post-return field: intentionally ignored on plastic path
            archived_plastic_multiplier=0.001,
            E_binary64=self.E,
            nu_binary64=self.NU,
            H_binary64=self.H,
            g0_interval=RationalInterval(1000, 1001),
            segment_extremum_interval=RationalInterval(100, 900),
            provenance_valid=True,
            source_identity_valid=True,
        )
        args.update(overrides)
        return certify_production_branch(**args)

    def test_source_denominator_encloses_actual_frozen_scalar_graph(self):
        # Independent ordinary Python binary64 evaluation of pinned scalar expression.
        shear64 = self.E / (2.0 * (1.0 + self.NU))
        denominator64 = 3.0 * shear64 + self.H
        enclosure = _source_denominator(as_fraction(self.E), as_fraction(self.NU), as_fraction(self.H))
        self.assertLessEqual(enclosure.lo, as_fraction(denominator64))
        self.assertGreaterEqual(enclosure.hi, as_fraction(denominator64))
        self.assertEqual(parse_serialized_interval(self.call()["consistency_modulus_D_pa"]), enclosure)

    def test_inverse_division_encloses_all_rounding_mode_candidates(self):
        delta = 0.001
        previous = math.nextafter(delta, -math.inf)
        following = math.nextafter(delta, math.inf)
        # Exact quotients on both sides of delta can round to delta under directed
        # or nearest modes; all are inside the adjacent-float inverse basin.
        below = (as_fraction(previous) + as_fraction(delta)) / 2
        above = (as_fraction(delta) + as_fraction(following)) / 2
        for exact_quotient, possible_rounded in ((below, (previous, delta)),
                                                 (above, (delta, following))):
            self.assertTrue(all(previous <= got <= following for got in possible_rounded))
            result = self.call(archived_plastic_multiplier=delta)
            y = parse_serialized_interval(result["production_yield_value_pa"])
            d = parse_serialized_interval(result["consistency_modulus_D_pa"])
            possible_y = exact_quotient * as_fraction(float(d.lo))
            self.assertLessEqual(y.lo, possible_y)
            self.assertGreaterEqual(y.hi, possible_y)

    def test_plastic_numeric_value_is_unavailable_but_enclosure_and_B_are_returned(self):
        result = self.call()
        self.assertFalse(result["production_numeric_yield_value_available"])
        self.assertIn("inverse_division_enclosure", result["production_yield_value_representation"])
        self.assertGreater(Fraction(int(result["a_posteriori_discrepancy_bound_B_exact"]["numerator"]),
                                    int(result["a_posteriori_discrepancy_bound_B_exact"]["denominator"])), 0)
        self.assertEqual(result["rounding_budget_scope"],
                         "a_posteriori_base_state_discrepancy_only_not_a_priori_segment_budget")

    def test_elastic_yield_value_is_exact_archived_pre_return_value(self):
        result = self.call(expected_branch="elastic", archived_elastic=True,
                           archived_yield_function=-2.0, archived_plastic_multiplier=0.0,
                           g0_interval=RationalInterval(-10, -9),
                           segment_extremum_interval=RationalInterval(-5, -1))
        self.assertTrue(result["production_numeric_yield_value_available"])
        self.assertEqual(parse_serialized_interval(result["production_yield_value_pa"]),
                         RationalInterval(as_fraction(-2.0)))
        self.assertEqual(result["verdict"], "PASS")

    def test_wrong_base_branch_or_math_sign_is_fail_or_inconclusive(self):
        wrong = self.call(archived_elastic=True, archived_yield_function=-1.0)
        self.assertEqual(wrong["verdict"], "FAIL")
        inconsistent = self.call(g0_interval=RationalInterval(-2, -1))
        self.assertEqual(inconsistent["verdict"], "FAIL")
        touching = self.call(g0_interval=RationalInterval(0, 1))
        self.assertEqual(touching["verdict"], "INCONCLUSIVE")

    def test_clearance_must_strictly_dominate_observed_discrepancy(self):
        dominated = self.call(g0_interval=RationalInterval(500_000_000, 500_000_010),
                              segment_extremum_interval=RationalInterval(300_000_000, 600_000_000))
        self.assertTrue(dominated["base_clearance_dominates_B"])
        self.assertTrue(dominated["production_branch_linkage_valid"])
        not_dominated = self.call(g0_interval=RationalInterval(1000, 1001))
        self.assertFalse(not_dominated["base_clearance_dominates_B"])
        self.assertFalse(not_dominated["production_branch_linkage_valid"])

    def test_linked_branch_with_wrong_segment_extremum_is_fail(self):
        result = self.call(g0_interval=RationalInterval(500_000_000, 500_000_010),
                           segment_extremum_interval=RationalInterval(-2, -1))
        self.assertTrue(result["production_branch_linkage_valid"])
        self.assertEqual(result["verdict"], "FAIL")

    def test_missing_evidence_is_inconclusive_identity_mismatch_invalid(self):
        missing = self.call(provenance_valid=None)
        mismatch = self.call(source_identity_valid=False)
        self.assertEqual(missing["verdict"], "INCONCLUSIVE")
        self.assertEqual(mismatch["verdict"], "INVALID_PROTOCOL")

    def test_subnormal_and_overflow_inputs_are_refused(self):
        subnormal = self.call(archived_plastic_multiplier=math.ulp(0.0))
        self.assertEqual(subnormal["verdict"], "INVALID_PROTOCOL")
        overflow = self.call(E_binary64=sys.float_info.max, nu_binary64=0.0, H_binary64=0.0)
        self.assertEqual(overflow["verdict"], "INVALID_PROTOCOL")
        nonfinite = self.call(archived_plastic_multiplier=float("inf"))
        self.assertEqual(nonfinite["verdict"], "INVALID_PROTOCOL")

    def test_binary64_source_scalars_reject_nonrepresentable_exact_rationals(self):
        result = self.call(E_binary64=Fraction(1, 10))
        self.assertEqual(result["verdict"], "INVALID_PROTOCOL")

    def test_outward_binary64_neighbors_enclose_exact_tiny_and_negative_rationals(self):
        tiny = Fraction(1, 10**400)
        bounds = _outward_binary64(tiny)
        self.assertLessEqual(bounds.lo, tiny)
        self.assertGreaterEqual(bounds.hi, tiny)
        negative = _outward_binary64(-tiny)
        self.assertLessEqual(negative.lo, -tiny)
        self.assertGreaterEqual(negative.hi, -tiny)

    def test_runtime_binary64_shape_and_near_power_max_boundaries(self):
        from production_branch_budget import _check_binary64_runtime
        _check_binary64_runtime()
        for x in (Fraction(1) + Fraction(1, 2**54),
                  -Fraction(1) - Fraction(1, 2**54),
                  as_fraction(sys.float_info.max),
                  as_fraction(math.nextafter(sys.float_info.max, 0.0))):
            enclosure = _outward_binary64(x)
            self.assertLessEqual(enclosure.lo, x)
            self.assertGreaterEqual(enclosure.hi, x)


if __name__ == "__main__":
    unittest.main(verbosity=2)
