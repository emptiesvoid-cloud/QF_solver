"""Pure evaluation of explicitly supplied, unfrozen numeric criteria.

This module neither approves criteria nor invokes a solver.  It refuses missing,
nonfinite and malformed observations instead of interpreting them as passes.
"""
from __future__ import annotations

import math
from typing import Any


def evaluate(rule: dict[str, Any], observation: Any) -> dict[str, Any]:
    """Return a prospective verdict for a single numeric or finiteness rule."""
    if rule.get("classification") not in {"CASE_GATE", "CASE_DIAGNOSTIC", "CAMPAIGN_GATE"}:
        raise ValueError("invalid criterion classification")
    operator = rule.get("operator")
    threshold = rule.get("threshold")
    if operator == "ALL_TRUE":
        if threshold is not None or not isinstance(observation, list) or not observation:
            raise ValueError("ALL_TRUE requires a nonempty boolean list and no threshold")
        if any(type(value) is not bool for value in observation):
            raise ValueError("ALL_TRUE values must be booleans")
        passed = all(observation)
    else:
        if operator not in {"LE", "GE", "GT"}:
            raise ValueError("unsupported criterion operator")
        if (isinstance(threshold, bool) or not isinstance(threshold, (int, float))
                or not math.isfinite(threshold)):
            raise ValueError("threshold must be finite")
        if (isinstance(observation, bool) or not isinstance(observation, (int, float))
                or not math.isfinite(observation)):
            return {"status": "NOT_ASSESSED", "reason": "MISSING_OR_NONFINITE"}
        passed = {"LE": observation <= threshold, "GE": observation >= threshold,
                  "GT": observation > threshold}[operator]
    return {"status": "PROVISIONAL_PASS" if passed else "PROVISIONAL_FAIL",
            "classification": rule["classification"], "operator": operator,
            "threshold": threshold, "observation": observation}
