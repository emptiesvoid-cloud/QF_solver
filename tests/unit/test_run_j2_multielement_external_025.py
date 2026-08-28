from __future__ import annotations

from scripts import run_j2_multielement_external_025 as runner


def test_external_runner_returns_nonzero_for_unclosed_correlation() -> None:
    assert runner.exit_code({"status": "FAIL"}) == 1
    assert runner.exit_code({"status": "PASS_EXTERNAL_CORRELATION"}) == 0
