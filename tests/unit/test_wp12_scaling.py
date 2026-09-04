from __future__ import annotations

import json
from pathlib import Path

from scripts.run_wp12_scaling import (
    SCIPY_MAX_DOFS,
    _load_assembly_probe,
    _portable_profile_path,
    _solver_limited_row,
    _spec,
)

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "qualification" / "0_2_7" / "wp12_scaling_evidence.json"
ASSEMBLY_PROBE = ROOT / "qualification" / "0_2_7" / "wp12_assembly_probe_300k.json"
STATE = ROOT / "qualification" / "0_2_7" / "wp12_state.json"


def test_wp12_size_specs_are_monotone_and_reach_targets() -> None:
    targets = (100_000, 300_000, 500_000, 750_000, 1_000_000)
    actual = [_spec(target)["estimated"]["ndof"] for target in targets]

    assert actual == sorted(actual)
    assert all(value >= target for value, target in zip(actual, targets, strict=True))
    assert all(_spec(target)["family"] == "TET4" for target in targets)


def test_wp12_scipy_limit_is_fail_closed_without_allocating_a_large_model() -> None:
    spec = _spec(300_000)
    row = _solver_limited_row(spec, "cg")

    assert spec["estimated"]["ndof"] > SCIPY_MAX_DOFS
    assert row["status"] == "SOLVER_LIMITED"
    assert row["verdict"] == "SOLVER_LIMITED"
    assert "no allocation attempted" in row["error"]["message"]


def test_wp12_matching_assembly_probe_is_reused_as_assembly_evidence() -> None:
    probe = _load_assembly_probe()

    assert probe is not None
    assert probe["source_sha"] == "4971ac4f6c1e5cff2ca48e40ca6db5e8147d0d0a"
    assert probe["actual_dofs"] == 311_469
    assert probe["solve"] == "NOT_RUN"


def test_wp12_profile_locations_are_portable() -> None:
    private_repo_path = "C:" + r"\Users\private\repo\src\solveur\large\matrix_free.py"
    assert _portable_profile_path(private_repo_path) == (
        "src/solveur/large/matrix_free.py"
    )
    private_site_path = "C:" + "\\" + "Users" + "\\" + "private" + "\\" + "App" + "Data\\Roaming\\Python\\site-packages\\scipy\\sparse\\linalg.py"
    assert _portable_profile_path(
        private_site_path
    ) == "site-packages/scipy/sparse/linalg.py"


def test_wp12_evidence_records_bounded_size_and_resource_verdicts() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    state = json.loads(STATE.read_text(encoding="utf-8"))
    probe = json.loads(ASSEMBLY_PROBE.read_text(encoding="utf-8"))

    assert report["contract_id"] == "027-WP12-LARGE-SCALE"
    assert report["qualification_status"] == "PASS_WITH_LIMITATIONS"
    assert report["execution_sha"] == "4971ac4f6c1e5cff2ca48e40ca6db5e8147d0d0a"
    assert [item["target_dofs"] for item in report["size_ladder"]] == [
        100_000,
        300_000,
        500_000,
        750_000,
        1_000_000,
    ]
    assert report["summary"]["max_full_solve_dofs"] == 750_141
    assert report["summary"]["max_assembly_dofs"] == 311_469
    assert report["summary"]["numerical_failures"] == 0
    assert report["replay"]["deterministic"] is True
    assert report["claims"]["universal_scaling_claim"] is False
    optimization = report["optimization_log"][0]
    assert optimization["id"] == "WP12-OPT-001"
    assert optimization["measurement"]["iterations"] == 397
    assert optimization["measurement"]["speedup_scope"] == "local probe only; not a universal claim"

    assert probe["status"] == "PASS"
    assert probe["rows"][0]["total_dofs"] == 311_469
    assert probe["rows"][0]["linear_solve_seconds"] is None
    assert state["status"] == "PASS_WITH_LIMITATIONS"
    assert state["decision_state"] == "OWNER_REVIEW_REQUIRED"
    assert state["evidence_source_sha"] == report["execution_sha"]
