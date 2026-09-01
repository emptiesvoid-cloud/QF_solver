"""Targeted tests for the final bounded WP10 modal evidence path."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from scripts.run_wp10_final_modal import _aster_comm, run
from solveur.verification.modal_comparison import match_modes
from solveur.verification.v2 import load_cases


ROOT = Path(__file__).resolve().parents[2]
CASES = ROOT / "qualification" / "0_2_7" / "vnv_v2" / "wp10_final_cases.json"


def test_final_catalog_declares_refinement_mac_and_replay_cases() -> None:
    cases = load_cases(CASES)
    assert len(cases) == 6
    assert {case.case_id for case in cases} == {
        "WP10-FINAL-REFINEMENT",
        "WP10-FINAL-MAC-AXIAL",
        "WP10-FINAL-MAC-BENDING",
        "WP10-FINAL-MAC-DISTORTED",
        "WP10-FINAL-MAC-MULTI-WEDGE",
        "WP10-FINAL-REPLAY",
    }
    assert all(case.capability_refs == ("COMB-WEDGE6-modal",) for case in cases)
    assert all(case.element == "WEDGE6" and case.analysis == "modal" for case in cases)
    external = [case for case in cases if case.oracle.type == "EXTERNAL_SOLVER"]
    assert len(external) == 4
    assert all(case.oracle.tolerance == 0.01 for case in external)
    assert all(case.oracle.provenance["status"] == "predeclared_before_replay" for case in external)


def test_mac_is_invariant_to_sign_and_deterministically_matches_reordered_modes() -> None:
    reference_modes = np.eye(3)
    candidate_modes = reference_modes[:, [1, 2, 0]] * np.asarray((-1.0, 1.0, -1.0))
    comparison = match_modes(
        [10.0, 20.0, 30.0],
        reference_modes,
        [20.0, 30.0, 10.0],
        candidate_modes,
        frequency_tolerance=1.0e-8,
        mac_tolerance=0.99,
    )
    assert comparison["status"] == "PASS"
    assert [(pair["reference_mode"], pair["candidate_mode"]) for pair in comparison["pairs"]] == [
        (1, 3),
        (2, 1),
        (3, 2),
    ]
    assert all(pair["mac"] == 1.0 for pair in comparison["pairs"])


def test_near_degenerate_modes_use_subspace_mac() -> None:
    reference_modes = np.eye(3)
    rotation = np.asarray(((1.0, -1.0), (1.0, 1.0))) / np.sqrt(2.0)
    candidate_modes = np.column_stack((reference_modes[:, :2] @ rotation, reference_modes[:, 2]))
    comparison = match_modes(
        [10.0, 10.0 + 5.0e-6, 20.0],
        reference_modes,
        [10.0, 10.0 + 4.0e-6, 20.0],
        candidate_modes,
        frequency_tolerance=1.0e-5,
        mac_tolerance=0.99,
        near_degenerate_tolerance=1.0e-5,
    )
    assert comparison["status"] == "PASS"
    assert [pair["quality_rule"] for pair in comparison["pairs"]] == [
        "subspace_mac",
        "subspace_mac",
        "individual_mac",
    ]


def test_mode_mismatch_is_not_forced_to_pass() -> None:
    comparison = match_modes(
        [10.0, 20.0, 30.0],
        np.eye(3),
        [10.0, 20.0, 30.0],
        np.asarray(((1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, 1.0, 0.0))),
        frequency_tolerance=1.0e-8,
        mac_tolerance=0.99,
    )
    assert comparison["status"] == "FAIL"


def test_final_runner_preserves_explicit_external_skip(tmp_path: Path) -> None:
    output = tmp_path / "wp10_final_evidence.json"
    summary = run(output, run_external=False)
    assert summary["external"]["status"] == "SKIPPED_EXTERNAL_UNAVAILABLE"
    assert summary["maturity"] == "EXPERIMENTAL"
    assert json.loads(output.read_text(encoding="utf-8"))["artifact_classification"] == "CONTROLLED_PROOF"


def test_code_aster_deck_extracts_physical_mode_components() -> None:
    comm = _aster_comm()
    assert "getValuesWithDescription" in comm
    assert 'component_index = {"DX": 0, "DY": 1, "DZ": 2}' in comm
    assert '"mode_vectors": mode_vectors' in comm
