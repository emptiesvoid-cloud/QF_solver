"""Targeted WP19 adversarial robustness and HEX8 diagnostic checks."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.run_wp19_robustness import run_adversarial, run_golden_replay, run_hex8_diagnostic
from solveur.verification.v2 import load_cases


ROOT = Path(__file__).resolve().parents[2]
CASES = ROOT / "qualification/0_2_7/wp19_cases.json"


def test_wp19_catalog_is_complete_and_explicit() -> None:
    cases = load_cases(CASES)
    assert len(cases) == 24
    assert len({case.case_id for case in cases}) == len(cases)
    assert sum(case.expected_failure is None for case in cases) == 10
    assert sum(case.expected_failure is not None for case in cases) == 14
    assert all(case.execution_tier == "T1" for case in cases)
    assert all(case.provenance["artifact_classification"] == "CONTROLLED_PROOF" for case in cases)


def test_wp19_adversarial_cases_fail_closed_and_replay(tmp_path: Path) -> None:
    summary = run_adversarial(tmp_path)
    assert summary["verdict_counts"] == {"EXPECTED_FAILURE_PASS": 14, "PASS": 10}
    assert summary["replay"]["status"] == "PASS"
    assert summary["fail_closed"] is True
    assert summary["no_nan_inf"] is True

    evidence = json.loads((tmp_path / "wp19_robustness_evidence.json").read_text(encoding="utf-8"))
    assert len(evidence) == 24
    assert all(record["source_sha"] for record in evidence)
    assert all(record["result_digest"] for record in evidence)
    assert not any(record["verdict"] in {"FAIL", "INVALID_EVIDENCE"} for record in evidence)


def test_wp19_hex8_diagnostic_is_bounded_and_deterministic(tmp_path: Path) -> None:
    summary = run_hex8_diagnostic(tmp_path, run_calculix=False)
    rows = summary["rows"]
    assert len(rows) == 9
    assert {row["family"] for row in rows} == {"refinement", "slenderness", "transverse"}
    assert all(row["calculix"]["status"] == "NOT_RUN" for row in rows)
    assert all(row["qf"]["finite"] for row in rows)
    assert all(row["qf"]["euler_relative_error"] >= 0.0 for row in rows)
    assert all(row["qf"]["response_classification"] == "GLOBAL_BENDING_RESPONSE_CANDIDATE" for row in rows)
    assert summary["comparability"]["reaction"].startswith("QF-only")
    assert summary["comparability"]["energy"].startswith("QF-only")
    assert summary["interpretation"]["qf_specific_bug"] is False


def test_wp19_replays_golden_set_without_rewriting_wp13_evidence(tmp_path: Path) -> None:
    summary = run_golden_replay(tmp_path)
    assert summary["status"] == "PASS"
    assert summary["run_counts"] == {"EXPECTED_FAILURE_PASS": 1, "PASS": 8}
    assert summary["replay_counts"] == {"PASS": 9, "MISMATCH": 0}
    assert summary["historical_wp13_evidence_preserved"] is True
    assert summary["historical_wp13_source_sha"] == "94ce10a53e31ad6884383c7ec8ce1761d9533eff"
