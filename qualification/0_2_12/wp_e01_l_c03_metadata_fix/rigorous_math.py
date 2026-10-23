"""Exact-rational bounds for affine deviatoric trial stress paths.

This module is deliberately independent of the solver and FEM code.  It bounds
q(s)^2=A+B*s+C*s^2, then sqrt(q(s)^2)-R over a rational segment.  PASS means
only that the supplied mathematical inputs prove a strict sign over the whole
segment; callers must separately establish provenance and production linkage.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
import math
from typing import Any, Iterable, Literal


Verdict = Literal["PASS", "FAIL", "INCONCLUSIVE", "INVALID_PROTOCOL"]
Branch = Literal["plastic", "elastic"]


def as_fraction(value: Any) -> Fraction:
    """Convert an exact input representation to Fraction without decimalizing floats.

    A float becomes its exact binary64 value via as_integer_ratio().  A Decimal
    becomes its exact finite base-10 value; this says nothing about whether the
    Decimal encloses the underlying archived quantity.
    """
    if isinstance(value, bool):
        raise TypeError("boolean is not a numeric coefficient")
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite binary64 input")
        n, d = value.as_integer_ratio()
        return Fraction(n, d)
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("non-finite Decimal input")
        return Fraction(value)
    raise TypeError(f"unsupported exact numeric type: {type(value).__name__}")


@dataclass(frozen=True)
class RationalInterval:
    """Closed rational interval; endpoints are exact, including point intervals."""

    lo: Fraction
    hi: Fraction

    def __init__(self, lo: Any, hi: Any | None = None):
        low = as_fraction(lo)
        high = low if hi is None else as_fraction(hi)
        if low > high:
            raise ValueError("interval lower endpoint exceeds upper endpoint")
        object.__setattr__(self, "lo", low)
        object.__setattr__(self, "hi", high)


def _iv(value: Any) -> RationalInterval:
    return value if isinstance(value, RationalInterval) else RationalInterval(value)


def _quadratic_extreme(a: Fraction, b: Fraction, c: Fraction,
                       lo: Fraction, hi: Fraction, want_min: bool) -> Fraction:
    """Exact extremum of one quadratic on a closed rational interval."""
    values = [a + b * lo + c * lo * lo, a + b * hi + c * hi * hi]
    if c:
        vertex = -b / (2 * c)
        if lo < vertex < hi and ((c > 0) == want_min):
            values.append(a + b * vertex + c * vertex * vertex)
    return min(values) if want_min else max(values)


def _poly_range(a: Fraction, b: Fraction, c: Fraction,
                lo: Fraction, hi: Fraction) -> tuple[Fraction, Fraction]:
    return (_quadratic_extreme(a, b, c, lo, hi, True),
            _quadratic_extreme(a, b, c, lo, hi, False))


def _quadratic_envelope_extreme(A: RationalInterval, B: RationalInterval,
                                C: RationalInterval, s: RationalInterval,
                                want_min: bool, lower_envelope: bool) -> Fraction:
    """Extremum of the coefficient-box lower/upper envelope, exactly."""
    cuts = [s.lo] + ([Fraction(0)] if s.lo < 0 < s.hi else []) + [s.hi]
    values: list[Fraction] = []
    for left, right in zip(cuts, cuts[1:]):
        probe = left if left == right else (left + right) / 2
        if lower_envelope:
            b = B.lo if probe >= 0 else B.hi
            a, c = A.lo, C.lo
        else:
            b = B.hi if probe >= 0 else B.lo
            a, c = A.hi, C.hi
        values.extend(_poly_range(a, b, c, left, right))
    if s.lo == s.hi:
        x = s.lo
        b_low = B.lo if x >= 0 else B.hi
        b_high = B.hi if x >= 0 else B.lo
        a, b, c = (A.lo, b_low, C.lo) if lower_envelope else (A.hi, b_high, C.hi)
        values = [a + b*x + c*x*x]
    return min(values) if want_min else max(values)


def polynomial_range(A: Any, B: Any, C: Any, s: Any) -> RationalInterval:
    """Conservative exact range of A+B*s+C*s^2 for interval coefficients.

    The lower envelope chooses coefficient endpoints according to the sign of
    s; the upper envelope does the converse. Splitting at zero makes these
    envelopes exact for independent rectangular coefficient intervals.
    """
    aa, bb, cc, ss = _iv(A), _iv(B), _iv(C), _iv(s)
    cuts = [ss.lo] + ([Fraction(0)] if ss.lo < 0 < ss.hi else []) + [ss.hi]
    lower_values: list[Fraction] = []
    upper_values: list[Fraction] = []
    for left, right in zip(cuts, cuts[1:]):
        # A piece may be the single point zero; all endpoint choices then agree.
        probe = left if left == right else (left + right) / 2
        b_low = bb.lo if probe >= 0 else bb.hi
        b_high = bb.hi if probe >= 0 else bb.lo
        lower_values.extend(_poly_range(aa.lo, b_low, cc.lo, left, right))
        upper_values.extend(_poly_range(aa.hi, b_high, cc.hi, left, right))
    if ss.lo == ss.hi:
        x = ss.lo
        lower_values = [aa.lo + (bb.lo if x >= 0 else bb.hi)*x + cc.lo*x*x]
        upper_values = [aa.hi + (bb.hi if x >= 0 else bb.lo)*x + cc.hi*x*x]
    return RationalInterval(min(lower_values), max(upper_values))


def sqrt_enclosure(value: Any, bits: int = 128) -> RationalInterval:
    """Return dyadic rational bounds for sqrt(value), checked by exact squares."""
    x = as_fraction(value)
    if x < 0:
        raise ValueError("square root input is negative")
    if bits < 1:
        raise ValueError("bits must be positive")
    scale = 1 << bits
    floor_root = math.isqrt((x.numerator * scale * scale) // x.denominator)
    lower = Fraction(floor_root, scale)
    exact = floor_root * floor_root * x.denominator == x.numerator * scale * scale
    upper = lower if exact else Fraction(floor_root + 1, scale)
    # Independent exact inequalities; do not trust the integer-root derivation alone.
    if not (lower * lower <= x <= upper * upper):
        raise ArithmeticError("independent squared-root enclosure check failed")
    return RationalInterval(lower, upper)


def _fraction_json(value: Fraction) -> dict[str, str]:
    return {"numerator": str(value.numerator), "denominator": str(value.denominator)}


def _decimal_outward(value: Fraction, places: int, upper: bool) -> str:
    """Fixed-place decimal rounded outward using integer arithmetic only."""
    if places < 0:
        raise ValueError("decimal places must be nonnegative")
    scale = 10 ** places
    scaled = value * scale
    q, r = divmod(scaled.numerator, scaled.denominator)
    units = q + (1 if upper and r else 0)
    sign = "-" if units < 0 else ""
    magnitude = abs(units)
    if places == 0:
        return sign + str(magnitude)
    return f"{sign}{magnitude // scale}.{magnitude % scale:0{places}d}"


def serialize_interval(value: RationalInterval, decimal_places: int = 12) -> dict[str, Any]:
    """JSON-ready exact endpoints plus outward rounded decimal displays."""
    return {
        "lo": _fraction_json(value.lo),
        "hi": _fraction_json(value.hi),
        "decimal_outward": {
            "lo": _decimal_outward(value.lo, decimal_places, upper=False),
            "hi": _decimal_outward(value.hi, decimal_places, upper=True),
            "places": decimal_places,
        },
    }


def _sqrt_check_json(value: Fraction, bounds: RationalInterval) -> dict[str, Any]:
    return {
        "input": _fraction_json(value),
        "lower_squared": _fraction_json(bounds.lo * bounds.lo),
        "upper_squared": _fraction_json(bounds.hi * bounds.hi),
        "lower_squared_le_input": bounds.lo * bounds.lo <= value,
        "upper_squared_ge_input": bounds.hi * bounds.hi >= value,
    }


def parse_serialized_interval(payload: Any) -> RationalInterval:
    """Strictly parse our interval JSON and verify display/endpoints agree.

    This detects malformed or internally tampered payloads, not a coordinated
    rewrite of both endpoints and displays. Cryptographic provenance belongs to
    the archive/manifest layer and must be checked by the caller.
    """
    try:
        if not isinstance(payload, dict) or set(payload) != {"lo", "hi", "decimal_outward"}:
            raise ValueError("unexpected interval object shape")
        def read_fraction(obj: Any) -> Fraction:
            if not isinstance(obj, dict) or set(obj) != {"numerator", "denominator"}:
                raise ValueError("unexpected rational endpoint shape")
            n, d = obj["numerator"], obj["denominator"]
            if not isinstance(n, str) or not isinstance(d, str) or not n or not d:
                raise ValueError("rational endpoints must be integer strings")
            if str(int(n)) != n or str(int(d)) != d or int(d) <= 0:
                raise ValueError("noncanonical rational endpoint")
            value = Fraction(int(n), int(d))
            if str(value.numerator) != n or str(value.denominator) != d:
                raise ValueError("rational endpoint is not reduced")
            return value
        low, high = read_fraction(payload["lo"]), read_fraction(payload["hi"])
        display = payload["decimal_outward"]
        if not isinstance(display, dict) or set(display) != {"lo", "hi", "places"}:
            raise ValueError("unexpected decimal display shape")
        places = display["places"]
        if not isinstance(places, int) or isinstance(places, bool) or places < 0:
            raise ValueError("invalid decimal display precision")
        if (display["lo"] != _decimal_outward(low, places, False)
                or display["hi"] != _decimal_outward(high, places, True)):
            raise ValueError("decimal display does not match exact endpoints")
        return RationalInterval(low, high)
    except (TypeError, KeyError, ZeroDivisionError) as exc:
        raise ValueError(f"invalid serialized interval: {exc}") from exc


def coefficients_from_affine_deviator(s0: Iterable[Any], ds: Iterable[Any]) -> tuple[Fraction, Fraction, Fraction]:
    """Build von-Mises q^2 coefficients from tensor-component vectors.

    Components use the ordinary tensor Frobenius product (off-diagonal tensor
    entries occur twice if the caller flattens a symmetric 3x3 tensor). For
    q=sqrt(3/2 * dev:dev), coefficients are returned for exact affine data.
    """
    base, delta = tuple(map(as_fraction, s0)), tuple(map(as_fraction, ds))
    if not base or len(base) != len(delta):
        raise ValueError("deviator and direction must have the same nonzero length")
    dot00 = sum((x*x for x in base), Fraction(0))
    dot01 = sum((x*y for x, y in zip(base, delta)), Fraction(0))
    dot11 = sum((y*y for y in delta), Fraction(0))
    return Fraction(3, 2)*dot00, 3*dot01, Fraction(3, 2)*dot11


def evaluate_margin(A: Any, B: Any, C: Any, R: Any, s: Any,
                    expected_branch: Branch, *, provenance_valid: bool,
                    production_branch_linkage_valid: bool = False,
                    production_rounding_budget_valid: bool = False,
                    complete_archive_inputs_valid: bool = False,
                    sqrt_bits: int = 128, decimal_places: int = 12) -> dict[str, Any]:
    """Bound g(s)=sqrt(A+B*s+C*s²)-R and classify the expected strict branch.

    ``provenance_valid`` must be set only after the caller validates identities,
    units, histories, and input provenance. This routine does not validate them.
    An unproved nonnegative radicand or any zero-touching margin is inconclusive.
    """
    if expected_branch not in ("plastic", "elastic"):
        return {"mathematical_verdict": "INVALID_PROTOCOL", "action_verdict": "INVALID_PROTOCOL",
                "reason": "unknown_expected_branch"}
    if not provenance_valid:
        return {"mathematical_verdict": "INVALID_PROTOCOL", "action_verdict": "INVALID_PROTOCOL",
                "reason": "input_provenance_not_validated"}
    try:
        aa, bb, cc, ss = _iv(A), _iv(B), _iv(C), _iv(s)
        radicand = polynomial_range(aa, bb, cc, ss)
        resistance = _iv(R)
    except (TypeError, ValueError, ZeroDivisionError) as exc:
        return {"mathematical_verdict": "INVALID_PROTOCOL", "action_verdict": "INVALID_PROTOCOL",
                "reason": f"invalid_numeric_input:{exc}"}
    result: dict[str, Any] = {
        "expected_branch": expected_branch,
        "radicand_range": serialize_interval(radicand, decimal_places),
        "resistance_range": serialize_interval(resistance, decimal_places),
    }
    if radicand.lo < 0:
        exact_coefficients = aa.lo == aa.hi and bb.lo == bb.hi and cc.lo == cc.hi
        if exact_coefficients or radicand.hi < 0:
            result.update(mathematical_verdict="INVALID_PROTOCOL", action_verdict="INVALID_PROTOCOL",
                          reason="radicand_proven_negative_for_squared_quantity")
        else:
            result.update(mathematical_verdict="INCONCLUSIVE", action_verdict="INCONCLUSIVE",
                          reason="radicand_nonnegativity_not_proved")
        return result
    exact_coefficients = aa.lo == aa.hi and bb.lo == bb.hi and cc.lo == cc.hi
    minimum_q2_interval = RationalInterval(
        _quadratic_envelope_extreme(aa, bb, cc, ss, True, True),
        _quadratic_envelope_extreme(aa, bb, cc, ss, True, False))
    maximum_q2_interval = RationalInterval(
        _quadratic_envelope_extreme(aa, bb, cc, ss, False, True),
        _quadratic_envelope_extreme(aa, bb, cc, ss, False, False))
    if minimum_q2_interval.lo > minimum_q2_interval.hi or maximum_q2_interval.lo > maximum_q2_interval.hi:
        return {"mathematical_verdict": "INVALID_PROTOCOL", "action_verdict": "INVALID_PROTOCOL",
                "reason": "quadratic_envelope_extremum_ordering_failure"}
    min_root_bounds = sqrt_enclosure(minimum_q2_interval.lo, sqrt_bits)
    max_root_bounds = sqrt_enclosure(maximum_q2_interval.hi, sqrt_bits)
    min_margin = RationalInterval(min_root_bounds.lo - resistance.hi,
                                  sqrt_enclosure(minimum_q2_interval.hi, sqrt_bits).hi - resistance.lo)
    max_margin = RationalInterval(sqrt_enclosure(maximum_q2_interval.lo, sqrt_bits).lo - resistance.hi,
                                  max_root_bounds.hi - resistance.lo)
    # The full segment value range also uses the true q² minimum and maximum
    # when coefficients are exact, and remains conservative for interval data.
    root_lo = min_root_bounds.lo
    root_hi = max_root_bounds.hi
    margin = RationalInterval(root_lo - resistance.hi, root_hi - resistance.lo)
    result["sqrt_range"] = serialize_interval(RationalInterval(root_lo, root_hi), decimal_places)
    result["sqrt_squared_checks"] = {
        "minimum_extremum_lower": _sqrt_check_json(minimum_q2_interval.lo, min_root_bounds),
        "minimum_extremum_upper": _sqrt_check_json(
            minimum_q2_interval.hi, sqrt_enclosure(minimum_q2_interval.hi, sqrt_bits)),
        "maximum_extremum_lower": _sqrt_check_json(
            maximum_q2_interval.lo, sqrt_enclosure(maximum_q2_interval.lo, sqrt_bits)),
        "maximum_extremum_upper": _sqrt_check_json(maximum_q2_interval.hi, max_root_bounds),
    }
    result["margin_range"] = serialize_interval(margin, decimal_places)
    result["minimum_margin_range"] = serialize_interval(min_margin, decimal_places)
    result["maximum_margin_range"] = serialize_interval(max_margin, decimal_places)
    if expected_branch == "plastic":
        decisive_extremum = min_margin
        verdict = "PASS" if decisive_extremum.lo > 0 else (
            "FAIL" if decisive_extremum.hi < 0 else "INCONCLUSIVE")
    else:
        decisive_extremum = max_margin
        verdict = "PASS" if decisive_extremum.hi < 0 else (
            "FAIL" if decisive_extremum.lo > 0 else "INCONCLUSIVE")
    result["mathematical_verdict"] = verdict
    # The complete action gate requires all archive and production evidence;
    # this generic evaluator cannot manufacture that evidence itself.
    identity_and_branch = (complete_archive_inputs_valid and provenance_valid
                           and production_branch_linkage_valid)
    pass_evidence = identity_and_branch and production_rounding_budget_valid
    if verdict == "FAIL" and identity_and_branch:
        final_verdict = "FAIL"
        reason = "decisive_extremum_proves_branch_violation_with_archive_and_branch_identity"
    elif verdict == "PASS" and pass_evidence:
        final_verdict = "PASS"
        reason = "strict_sign_and_complete_positive_action_evidence_certified"
    elif verdict == "INCONCLUSIVE":
        final_verdict = "INCONCLUSIVE"
        reason = "decisive_extremum_touches_or_crosses_zero"
    else:
        final_verdict = "INCONCLUSIVE"
        reason = "mathematical_sign_only_archive_branch_or_required_rounding_evidence_missing"
    result["action_verdict"] = final_verdict
    result["reason"] = reason
    result["complete_action_evidence"] = {
        "archive_inputs_validated": bool(complete_archive_inputs_valid and provenance_valid),
        "production_branch_linkage_validated": bool(production_branch_linkage_valid),
        "production_rounding_budget_validated": bool(production_rounding_budget_valid),
    }
    return result
