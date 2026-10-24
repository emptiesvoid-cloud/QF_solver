"""Pure descriptive metrics shared by the inactive WP-D01-BJ experiment."""

from __future__ import annotations

import math


def correction_error_ratio(
    corrected_error: float,
    uncorrected_error: float,
) -> tuple[float | None, str]:
    """Return corrected/uncorrected relative-error ratio without inventing 0/0.

    Errors are norms, so they must be finite and nonnegative. A zero baseline
    makes the ratio undefined; direct error comparison remains available to
    describe whether the correction degraded the result.
    """
    corrected = float(corrected_error)
    uncorrected = float(uncorrected_error)
    if not math.isfinite(corrected) or not math.isfinite(uncorrected):
        raise ValueError("Relative errors must be finite.")
    if corrected < 0.0 or uncorrected < 0.0:
        raise ValueError("Relative-error norms must be nonnegative.")
    if uncorrected > 0.0:
        return corrected / uncorrected, "DEFINED"
    if corrected == 0.0:
        return None, "BOTH_ERRORS_ZERO"
    return None, "UNCORRECTED_ZERO_CORRECTED_NONZERO"
