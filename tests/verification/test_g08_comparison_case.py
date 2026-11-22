
"""Exact execution targets for an approved G08 comparison controller."""
import json
import pytest

from research.g08_compare.case import prepare, solve_one


@pytest.fixture
def g08_execution_context(request):
    try:
        return request.getfixturevalue("g08_registered_attempt")
    except pytest.FixtureLookupError:
        pytest.skip("G08 execution scope is prepared but has no approved controller")


def _run(scope, context):
    source, output, expected_inputs = context
    model, receipt = prepare(source, scope)
    if receipt["inputs_sha256"] != expected_inputs:
        raise ValueError("input fingerprint differs from reserved manifest")
    from qf_solver import solve_model

    try:
        solve_one(model, receipt, output, solve_model)
    except Exception as exc:
        (output / "failure.json").write_text(
            json.dumps(
                {
                    "scope": receipt["scope"],
                    "source": receipt["source"],
                    "inputs_sha256": receipt["inputs_sha256"],
                    "exception_type": type(exc).__name__,
                    "message": str(exc),
                },
                allow_nan=False,
            ),
            encoding="utf-8",
        )
        raise


def test_g08_before(g08_execution_context):
    _run("g08-tet10-before", g08_execution_context)


def test_g08_after(g08_execution_context):
    _run("g08-tet10-after", g08_execution_context)
