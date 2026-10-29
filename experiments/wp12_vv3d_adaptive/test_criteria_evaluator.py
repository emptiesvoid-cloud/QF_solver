"""Synthetic tests: no numerical assembly or solver execution."""
import pytest

from experiments.wp12_vv3d_adaptive.criteria_evaluator import evaluate


def test_boundaries_and_nonfinite_are_not_passes():
    rule = {"classification": "CASE_GATE", "operator": "LE", "threshold": 1e-8}
    assert evaluate(rule, 1e-8)["status"] == "PROVISIONAL_PASS"
    assert evaluate(rule, 2e-8)["status"] == "PROVISIONAL_FAIL"
    assert evaluate(rule, float("nan"))["status"] == "NOT_ASSESSED"
    assert evaluate(rule, None)["status"] == "NOT_ASSESSED"


def test_positive_jacobian_and_boolean_validity():
    rule = {"classification": "CASE_GATE", "operator": "GT", "threshold": 0}
    assert evaluate(rule, 0)["status"] == "PROVISIONAL_FAIL"
    assert evaluate(rule, 1)["status"] == "PROVISIONAL_PASS"
    finite = {"classification": "CASE_GATE", "operator": "ALL_TRUE", "threshold": None}
    assert evaluate(finite, [True, False])["status"] == "PROVISIONAL_FAIL"
    with pytest.raises(ValueError):
        evaluate(finite, [])
    with pytest.raises(ValueError):
        evaluate(finite, [1])


def test_invalid_or_mutated_rule_is_rejected():
    for rule in (
        {"classification": "UNKNOWN", "operator": "LE", "threshold": 1},
        {"classification": "CASE_GATE", "operator": "LT", "threshold": 1},
        {"classification": "CASE_GATE", "operator": "LE", "threshold": float("inf")},
    ):
        with pytest.raises(ValueError):
            evaluate(rule, 0)
