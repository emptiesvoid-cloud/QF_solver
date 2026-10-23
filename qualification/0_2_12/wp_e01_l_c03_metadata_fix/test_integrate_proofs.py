from fractions import Fraction
import unittest

from integrate_proofs import decisive_segment_interval, final_status, summarize_segment_bounds
from rigorous_math import RationalInterval


def encoded(lo: int, hi: int) -> dict[str, dict[str, str]]:
    return {
        "lo": {"numerator": str(lo), "denominator": "1"},
        "hi": {"numerator": str(hi), "denominator": "1"},
    }


class IntegrateProofTests(unittest.TestCase):
  def test_final_status_mapping_preserves_technical_aggregate(self):
    expected = {
        "PASS": ("C03_PROOF_READY_FOR_OWNER_REVIEW", "READY_FOR_OWNER_REVIEW", "PROPOSED_NOT_PROMOTED"),
        "FAIL": ("C03_PROOF_PARTIAL", "NOT_READY", "NOT_ELIGIBLE"),
        "INCONCLUSIVE": ("C03_PROOF_INCONCLUSIVE", "NOT_READY", "NOT_ELIGIBLE"),
        "INVALID_PROTOCOL": ("C03_PROOF_INVALID", "NOT_READY", "NOT_ELIGIBLE"),
    }
    for aggregate, (verdict, owner, certificate) in expected.items():
        with self.subTest(aggregate=aggregate):
            status = final_status(aggregate)
            self.assertEqual(status["technical_aggregate_verdict"], aggregate)
            self.assertEqual(status["global_verdict"], verdict)
            self.assertEqual(status["owner_status"], owner)
            self.assertEqual(status["certificate_status"], certificate)

  def test_decisive_extremum_is_branch_specific(self):
    result = {
        "minimum_margin_range": encoded(5, 7),
        "maximum_margin_range": encoded(10, 12),
        "margin_range": encoded(5, 12),
    }
    self.assertEqual(decisive_segment_interval(result, "plastic"), RationalInterval(Fraction(5), Fraction(7)))
    self.assertEqual(decisive_segment_interval(result, "elastic"), RationalInterval(Fraction(10), Fraction(12)))


  def test_mixed_branch_action_clearance_uses_each_points_own_extremum(self):
    # The full union is [-9, 8]. A previous first-point-branch shortcut would
    # incorrectly call -9 the plastic clearance; the correct minimum clearance
    # is min(5, -(-6)) = 5 Pa.
    full_range, clearance = summarize_segment_bounds([
        ("plastic", RationalInterval(Fraction(5), Fraction(8)), RationalInterval(Fraction(5), Fraction(6))),
        ("elastic", RationalInterval(Fraction(-9), Fraction(-6)), RationalInterval(Fraction(-8), Fraction(-6))),
    ])
    self.assertEqual(full_range, RationalInterval(Fraction(-9), Fraction(8)))
    self.assertEqual(clearance, RationalInterval(Fraction(5)))


  def test_mixed_branch_summary_rejects_unknown_branch(self):
    with self.assertRaisesRegex(ValueError, "branch-specific"):
        decisive_segment_interval({"minimum_margin_range": encoded(1, 2)}, "unknown")


if __name__ == "__main__":
    unittest.main()
