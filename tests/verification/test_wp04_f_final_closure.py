"""Evidence-only WP04-F closure checks; no solver or structural solve is run."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "qualification/0_2_9/wp04f/wp04_final_closure_audit.json"
AUDIT_SHA = "70e1bf953c8e6f37b8070e78ca97e58b21499291"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def relative_delta(a: float, b: float) -> float:
    return abs(a - b) / max(abs(a), abs(b), 1e-12)


def test_audit_scope_and_source_freeze() -> None:
    audit = load(AUDIT)
    assert audit["audit_sha"] == AUDIT_SHA
    assert audit["evidence_only"] is True
    assert audit["structural_solves_run"] is False
    assert audit["production_mechanics_changed"] is False
    assert audit["source_audit"]["production_paths_changed"] == []
    protected_paths = [item["path"] for item in audit["source_audit"]["source_files"]]
    diff = subprocess.run(
        ["git", "diff", "--name-only", AUDIT_SHA, "--", *protected_paths],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert diff.stdout.strip() == ""
    for item in audit["source_audit"]["source_files"]:
        assert hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest() == item["sha256"]


def test_original_failure_and_wp04b_metrics_are_preserved() -> None:
    audit = load(AUDIT)
    original = load(ROOT / "qualification/0_2_9/wp04_c_tet4_structural_summary.json")
    assert audit["original_g04_10_failure_preserved"] is True
    assert original["gate_status"]["G04-10"]["status"] == "FAIL"
    assert original["mesh_convergence"]["passes_fine_medium_limits"] is False
    blob = subprocess.run(
        ["git", "rev-parse", f"{AUDIT_SHA}:qualification/0_2_9/wp04_c_tet4_structural_summary.json"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert blob == audit["provenance"]["original_failure_preservation"]["summary_git_blob_at_audit_sha"]
    assert blob == "0138e7583c2e0ce0488c69ab8630f87118a299e6"

    b = load(ROOT / "qualification/0_2_9/wp04_b_mechanics_identities.json")
    assert max(x["scaled_energy"] for x in b["objectivity"]["TET4"]) <= 1e-12
    assert max(x["scaled_internal_force"] for x in b["objectivity"]["HEX8"]) <= 1e-11
    for family in ("TET4", "HEX8"):
        assert max(x["frobenius_relative_error"] for x in b["tangent"][family]) <= 1e-6
        assert max(x["maximum_column_relative_error"] for x in b["tangent"][family]) <= 5e-6
        assert max(x["symmetry_defect"] for x in b["tangent"][family]) <= 1e-12
        assert max(x["relative_l2"] for x in b["energy_gradient"][family]) <= 1e-7
        rows = b["energy_work"][family]
        row96 = next(x for x in rows if x["intervals"] == 96)
        row48 = next(x for x in rows if x["intervals"] == 48)
        assert row96["relative_delta_energy_work_error"] <= 1e-6
        assert relative_delta(row96["external_work"], row48["external_work"]) <= 2e-7


def test_structural_frozen_thresholds_and_envelopes() -> None:
    audit = load(AUDIT)
    c2 = audit["structural_evidence"]["tet4_c2r6"]
    h8 = audit["structural_evidence"]["hex8_wp04d"]
    for section, key in ((c2, "M2_to_M3_deltas"), (h8, "H2_to_H3_deltas")):
        limits = section["thresholds"]
        deltas = section[key]
        assert deltas["displacement"] <= limits["displacement"]
        assert deltas["reaction"] <= limits["reaction"]
        assert deltas["energy"] <= limits["energy"]
        assert deltas["stress"] <= limits["stress"]
        assert section["envelope_pass"] is True
        assert section["equilibrium_pass"] is True
        assert section["route_frozen"] is True
    assert h8["H4"] == "NOT_RUN_PREDECLARED_RESCUE_NOT_TRIGGERED"
    assert h8["H1_replay"]["accepted_path_equal"] is True
    assert h8["small_load_support"]["reaction_error"] > 1e-4
    assert audit["gates"]["G04-06"]["status"] == "PASS_WITH_LIMITATION"


def test_cross_family_gate_and_limitations_are_explicit() -> None:
    audit = load(AUDIT)
    cross = audit["structural_evidence"]["cross_family"]
    assert cross["physical_definitions_match"] is True
    assert cross["governing_load_resultant_and_first_moment_match"] is True
    for name, limit in cross["thresholds"].items():
        assert cross["deltas"][name] <= limit
    assert audit["gates"]["G04-12"]["status"] == "PASS"
    assert any(
        item["id"] == "L04-01" and not item["blocking"]
        for item in audit["limitations_ledger"]
    )
    assert any(
        item["id"] == "L04-02" and not item["blocking"]
        for item in audit["limitations_ledger"]
    )


def test_final_all_or_nothing_governance_decision() -> None:
    audit = load(AUDIT)
    statuses = {key: value["status"] for key, value in audit["gates"].items()}
    assert set(statuses) == {f"G04-{i:02d}" for i in range(1, 13)}
    assert all(value in {"PASS", "PASS_WITH_LIMITATION"} for value in statuses.values())
    decision = audit["final_decision"]
    assert decision["auditor_decision"] == "GO_WITH_LIMITATIONS"
    assert decision["wp04_status"] == "CLOSED"
    assert decision["wp04_points"] == 12
    assert decision["validated_total"] == 41
    assert decision["blocking_limitations"] == []
    for path, expected in audit["source_audit"]["evidence_record_digests"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected
