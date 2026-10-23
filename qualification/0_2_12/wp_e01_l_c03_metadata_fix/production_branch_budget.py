"""Rational enclosure of the archived J2 base branch decision.

No solver or FEM code is imported. The implementation follows the frozen
scalar operation graph documented below, and treats IEEE-754 rounding mode as
unknown by enclosing each operation's exact rational result between adjacent
binary64 values.
"""

from __future__ import annotations

import math
import sys
from fractions import Fraction
from typing import Any, Literal

from rigorous_math import RationalInterval, as_fraction, serialize_interval

Branch = Literal["plastic", "elastic"]
_BINARY64_RUNTIME_CHECKED = False


def _check_binary64_runtime() -> None:
    global _BINARY64_RUNTIME_CHECKED
    if _BINARY64_RUNTIME_CHECKED:
        return
    info = sys.float_info
    if (info.radix != 2 or info.mant_dig != 53 or info.max_exp != 1024
            or info.min_exp != -1021):
        raise RuntimeError("runtime float format is not IEEE binary64")
    # Check that nextafter steps by one adjacent representable value around 1.
    one = 1.0
    above, below = math.nextafter(one, math.inf), math.nextafter(one, -math.inf)
    if not (as_fraction(below) < Fraction(1) < as_fraction(above)
            and math.nextafter(above, -math.inf) == one
            and math.nextafter(below, math.inf) == one):
        raise RuntimeError("nextafter adjacency does not match binary64 assumptions")
    _BINARY64_RUNTIME_CHECKED = True


def _binary64_source(value: Any, label: str) -> Fraction:
    """Accept a float or exact rational that is exactly representable as binary64."""
    exact = as_fraction(value)
    try:
        rounded = float(exact)
    except OverflowError as exc:
        raise ValueError(f"{label} overflows binary64") from exc
    if not math.isfinite(rounded) or as_fraction(rounded) != exact:
        raise ValueError(f"{label} is not a finite exact binary64 value")
    return exact


def _outward_binary64(x: Fraction) -> RationalInterval:
    """Adjacent-float enclosure of an exact rational, including subnormal scale."""
    _check_binary64_runtime()
    try:
        candidate = float(x)
    except OverflowError as exc:
        raise ValueError("binary64 operation overflow") from exc
    if not math.isfinite(candidate):
        raise ValueError("binary64 operation overflow")
    represented = as_fraction(candidate)
    if represented == x:
        return RationalInterval(represented)
    if represented < x:
        upper = math.nextafter(candidate, math.inf)
        if not math.isfinite(upper):
            raise ValueError("upper binary64 neighbor is infinite")
        upper_exact = as_fraction(upper)
        if not represented <= x <= upper_exact:
            raise RuntimeError("binary64 candidate and nextafter failed exact upper enclosure check")
        return RationalInterval(represented, upper_exact)
    lower = math.nextafter(candidate, -math.inf)
    if not math.isfinite(lower):
        raise ValueError("lower binary64 neighbor is infinite")
    lower_exact = as_fraction(lower)
    if not lower_exact <= x <= represented:
        raise RuntimeError("binary64 candidate and nextafter failed exact lower enclosure check")
    return RationalInterval(lower_exact, represented)


def _add(a: RationalInterval, b: RationalInterval) -> RationalInterval:
    return RationalInterval(_outward_binary64(a.lo + b.lo).lo,
                            _outward_binary64(a.hi + b.hi).hi)


def _multiply(a: RationalInterval, b: RationalInterval) -> RationalInterval:
    products = (a.lo*b.lo, a.lo*b.hi, a.hi*b.lo, a.hi*b.hi)
    return RationalInterval(_outward_binary64(min(products)).lo,
                            _outward_binary64(max(products)).hi)


def _divide_positive(a: RationalInterval, b: RationalInterval) -> RationalInterval:
    if a.lo < 0 or b.lo <= 0:
        raise ValueError("positive interval division requires nonnegative numerator and positive denominator")
    return RationalInterval(_outward_binary64(a.lo / b.hi).lo,
                            _outward_binary64(a.hi / b.lo).hi)


def _source_denominator(E: Fraction, nu: Fraction, H: Fraction) -> RationalInterval:
    """Enclose D through fl(1+nu), fl(2*x), fl(E/x), fl(3*mu), fl(...+H)."""
    one = RationalInterval(Fraction(1))
    two = RationalInterval(Fraction(2))
    three = RationalInterval(Fraction(3))
    nu_i = RationalInterval(nu)
    E_i = RationalInterval(E)
    H_i = RationalInterval(H)
    one_plus_nu = _add(one, nu_i)
    if one_plus_nu.lo <= 0:
        raise ValueError("1+nu denominator is not proved positive")
    twice = _multiply(two, one_plus_nu)
    if twice.lo <= 0:
        raise ValueError("2*(1+nu) denominator is not proved positive")
    shear = _divide_positive(E_i, twice)
    triple_shear = _multiply(three, shear)
    denominator = _add(triple_shear, H_i)
    if denominator.lo <= 0:
        raise ValueError("consistency modulus is not proved positive")
    # The actual stored scalar is a finite normal binary64. If any possible
    # operation result crosses subnormal/overflow territory, stop conservatively.
    if denominator.lo < as_fraction(sys.float_info.min) or denominator.hi > as_fraction(sys.float_info.max):
        raise ValueError("consistency modulus interval reaches subnormal or overflow range")
    return denominator


def _difference(a: RationalInterval, b: RationalInterval) -> RationalInterval:
    return RationalInterval(a.lo - b.hi, a.hi - b.lo)


def _expected_sign_status(value: RationalInterval, branch: Branch, label: str) -> tuple[str, str]:
    if branch == "plastic":
        if value.lo > 0:
            return "PASS", f"{label}_strictly_positive"
        if value.hi < 0:
            return "FAIL", f"{label}_strictly_negative_for_plastic"
    else:
        if value.hi < 0:
            return "PASS", f"{label}_strictly_negative"
        if value.lo > 0:
            return "FAIL", f"{label}_strictly_positive_for_elastic"
    return "INCONCLUSIVE", f"{label}_touches_or_crosses_zero"


def certify_production_branch(*, expected_branch: Branch, archived_elastic: bool,
                              archived_yield_function: Any | None,
                              archived_plastic_multiplier: Any | None,
                              E_binary64: Any, nu_binary64: Any, H_binary64: Any,
                              g0_interval: RationalInterval,
                              segment_extremum_interval: RationalInterval,
                              provenance_valid: bool | None = None,
                              source_identity_valid: bool | None = None,
                              decimal_places: int = 12) -> dict[str, Any]:
    """Recover and bound the production pre-return yield value at the base state.

    Frozen source scalar graph:
      shear = fl(E / fl(2 * fl(1+nu)))
      D = fl(fl(3*shear) + H)
      delta_gamma = fl(yield_value / D)

    Elastic records store the true pre-return `yield_function` directly.
    Plastic records overwrite `yield_function` with post-return zero, so the
    actual numeric yield value is unavailable; its enclosure is recovered from
    the archived positive normal `plastic_multiplier` and D. The discrepancy
    B=max|Yprod-G0| is a posteriori only; it is not a priori roundoff budget.
    """
    if expected_branch not in ("plastic", "elastic"):
        return {"verdict": "INVALID_PROTOCOL", "reason": "unknown_expected_branch"}
    if not isinstance(archived_elastic, bool):
        return {"verdict": "INVALID_PROTOCOL", "reason": "archived_elastic_flag_not_bool"}
    if not isinstance(g0_interval, RationalInterval) or not isinstance(segment_extremum_interval, RationalInterval):
        return {"verdict": "INVALID_PROTOCOL", "reason": "certified_model_intervals_required"}
    if source_identity_valid is False:
        return {"verdict": "INVALID_PROTOCOL", "reason": "frozen_source_identity_mismatch"}
    if provenance_valid is not True or source_identity_valid is not True:
        return {"verdict": "INCONCLUSIVE", "reason": "archive_provenance_or_source_identity_not_validated"}
    try:
        E = _binary64_source(E_binary64, "E")
        nu = _binary64_source(nu_binary64, "nu")
        H = _binary64_source(H_binary64, "H")
        if E <= 0 or H < 0 or not (-1 < nu < Fraction(1, 2)):
            raise ValueError("material scalar violates E>0, H>=0, -1<nu<1/2")
        denominator = _source_denominator(E, nu, H)
        if archived_elastic:
            if archived_yield_function is None:
                raise ValueError("elastic record requires pre-return yield_function")
            y = _binary64_source(archived_yield_function, "archived yield_function")
            yprod = RationalInterval(y)
            numeric_value_available = True
        else:
            if archived_plastic_multiplier is None:
                raise ValueError("plastic record requires archived plastic_multiplier")
            delta = _binary64_source(archived_plastic_multiplier, "archived plastic_multiplier")
            if delta <= 0 or delta < as_fraction(sys.float_info.min):
                raise ValueError("plastic multiplier must be finite, positive, and normal")
            delta_float = float(delta)
            predecessor = math.nextafter(delta_float, -math.inf)
            successor = math.nextafter(delta_float, math.inf)
            if not (math.isfinite(predecessor) and math.isfinite(successor)
                    and predecessor >= sys.float_info.min):
                raise ValueError("plastic multiplier quotient neighbors are subnormal or overflow")
            quotient = RationalInterval(as_fraction(predecessor), as_fraction(successor))
            yprod = _multiply(quotient, denominator)
            numeric_value_available = False
        discrepancy = _difference(yprod, g0_interval)
        discrepancy_bound = max(abs(discrepancy.lo), abs(discrepancy.hi))
    except (TypeError, ValueError, ZeroDivisionError, OverflowError) as exc:
        return {"verdict": "INVALID_PROTOCOL", "reason": f"invalid_or_unsupported_production_input:{exc}"}

    branch_matches = archived_elastic == (expected_branch == "elastic")
    prod_status, prod_reason = _expected_sign_status(yprod, expected_branch, "production_yield_value")
    g0_status, g0_reason = _expected_sign_status(g0_interval, expected_branch, "mathematical_base_g0")
    segment_status, segment_reason = _expected_sign_status(segment_extremum_interval, expected_branch,
                                                           "mathematical_segment_extremum")
    clearance = g0_interval.lo if expected_branch == "plastic" else -g0_interval.hi
    clearance_dominates_B = clearance > discrepancy_bound
    production_branch_linkage_valid = (branch_matches and prod_status == "PASS"
                                       and g0_status == "PASS" and clearance_dominates_B)
    if not branch_matches:
        verdict, reason = "FAIL", "archived_elastic_flag_conflicts_with_expected_branch"
    elif prod_status == "FAIL" or g0_status == "FAIL":
        verdict = "FAIL"
        reason = prod_reason if prod_status == "FAIL" else g0_reason
    elif segment_status == "FAIL" and production_branch_linkage_valid:
        verdict, reason = "FAIL", segment_reason
    elif not production_branch_linkage_valid:
        verdict, reason = "INCONCLUSIVE", "base_sign_or_clearance_does_not_dominate_a_posteriori_discrepancy"
    elif segment_status == "PASS":
        verdict, reason = "PASS", "production_base_and_segment_signs_consistent_with_clearance_over_B"
    else:
        verdict, reason = "INCONCLUSIVE", segment_reason

    return {
        "verdict": verdict,
        "reason": reason,
        "expected_branch": expected_branch,
        "archived_elastic": archived_elastic,
        "production_branch_linkage_valid": production_branch_linkage_valid,
        "archive_provenance_validated": provenance_valid,
        "frozen_source_identity_validated": source_identity_valid,
        "production_numeric_yield_value_available": numeric_value_available,
        "production_yield_value_pa": serialize_interval(yprod, decimal_places),
        "production_yield_value_representation": "exact_archived_binary64" if numeric_value_available else "certified_inverse_division_enclosure; actual value unavailable",
        "consistency_modulus_D_pa": serialize_interval(denominator, decimal_places),
        "g0_interval_pa": serialize_interval(g0_interval, decimal_places),
        "segment_decisive_extremum_interval_pa": serialize_interval(segment_extremum_interval, decimal_places),
        "discrepancy_interval_production_minus_model_pa": serialize_interval(discrepancy, decimal_places),
        "base_branch_clearance_pa": {
            "numerator": str(clearance.numerator),
            "denominator": str(clearance.denominator),
        },
        "base_clearance_dominates_B": clearance_dominates_B,
        "production_sign_status": prod_status,
        "mathematical_base_sign_status": g0_status,
        "mathematical_segment_sign_status": segment_status,
        "a_posteriori_discrepancy_bound_B_pa": str(discrepancy_bound),
        "a_posteriori_discrepancy_bound_B_exact": {
            "numerator": str(discrepancy_bound.numerator),
            "denominator": str(discrepancy_bound.denominator),
        },
        "rounding_budget_scope": "a_posteriori_base_state_discrepancy_only_not_a_priori_segment_budget",
    }
