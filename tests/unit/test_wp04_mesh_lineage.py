"""Anti-downgrade tests for the two distinct WP04 mesh-evidence generations."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from tests.helpers.wp04_lineage import (
    AUDIT_KEYS, HISTORY_PATH, CONTRACT_PATH, LIMITS, ROUTE, ROOT,
    WP04LineageError, active_mesh_metrics, historical_failure_metrics,
)


@pytest.fixture
def history() -> tuple[dict, dict]:
    return tuple(json.loads((ROOT / name).read_text(encoding="utf-8")) for name in (HISTORY_PATH, CONTRACT_PATH))


@pytest.fixture
def active_fixture() -> tuple[dict, dict, dict]:
    """Synthetic checker fixture only; never stored as qualification evidence."""
    cases = {}
    for label, cells, value in (("C2-M2", [48, 24, 24], 1.0), ("C2-M3", [64, 32, 32], 1.01)):
        factors = [index / 12 for index in range(1, 13)]
        digests = [f"{index:064x}" for index in range(1, 13)]
        cases[label] = {
            "status": "COMPLETED", "failure": None, "mesh_cells": cells,
            "route": dict(ROUTE), "start_sha": "fixture-only-not-execution-evidence",
            "accepted_records": [
                {"step": index, "load_factor": factor, "digest": digest}
                for index, (factor, digest) in enumerate(zip(factors, digests), start=1)
            ],
            "observables": {
                "tip_displacement": value, "strain_energy": value,
                "representative_stress_sigma_xx": value,
                "accepted_load_factors": factors, "accepted_state_digests": digests,
                "equilibrium": {"reaction_resultant_norm": value, "force_relative_error": 0.0, "moment_relative_error": 0.0},
                "minimum_det_f": 1.0, "minimum_principal_stretch": 1.0,
                "maximum_principal_stretch": 1.0, "maximum_green_lagrange_norm": 0.0,
            },
        }
    delta = abs(1.01 - 1.0) / 1.01
    audit = {
        "route": dict(ROUTE), "raw_campaign_top_level_g04_10": "UNRESOLVED",
        "source_sha": "fixture-only-not-execution-evidence",
        "mesh_pair_thresholds": {
            "definition": "abs(fine-medium)/max(abs(fine),abs(medium),1e-12)",
            "all_pass": True,
            **{AUDIT_KEYS[name]: {"value": delta, "limit": limit, "pass": True} for name, limit in LIMITS.items()},
        },
    }
    closure = {"structural_evidence": {"tet4_c2r6": {
        "thresholds": dict(LIMITS), "M2": {"fallbacks": 0}, "M3": {"fallbacks": 0},
        "M2_to_M3_deltas": {name: delta for name in LIMITS},
    }}}
    return {"G04-10": "UNRESOLVED", "cases": cases}, audit, closure


def test_original_coarse_evidence_is_still_numerically_failed(history: tuple[dict, dict]) -> None:
    result = historical_failure_metrics(*history)
    assert result["displacement"]["value"] == 0.1640618103457515
    assert result["energy"]["value"] == 0.16379509145773455
    assert result["stress"]["value"] == 0.24310580151133324
    assert {name for name, row in result.items() if row["status"] == "FAIL"} == {"displacement", "energy", "stress"}


@pytest.mark.parametrize("kind", ["status", "limit", "hierarchy", "delta", "nonfinite"])
def test_historical_failure_cannot_be_erased_or_weakened(history: tuple[dict, dict], kind: str) -> None:
    summary, contract = copy.deepcopy(history)
    if kind == "status":
        summary["gate_status"]["G04-10"]["status"] = "PASS"
    elif kind == "limit":
        contract["campaigns"]["mesh_convergence"]["fine_vs_medium_limits"]["tip_displacement_relative"] = 0.2
    elif kind == "hierarchy":
        summary["mesh_campaign"]["M3"]["cells"] = [64, 32, 32]
    elif kind == "delta":
        summary["mesh_convergence"]["fine_medium_tip_displacement_relative"] = 0.01
    else:
        summary["mesh_campaign"]["M3"]["tip_displacement"] = float("nan")
    with pytest.raises(WP04LineageError):
        historical_failure_metrics(summary, contract)


def test_synthetic_active_pair_fixture_passes(active_fixture: tuple[dict, dict, dict]) -> None:
    result = active_mesh_metrics(*active_fixture)
    assert all(row["status"] == "PASS" for row in result.values())


@pytest.mark.parametrize("kind", [
    "limit", "route", "fallback", "mesh", "missing_step", "state_digest", "execution_sha",
    "nonfinite", "equilibrium", "envelope", "delta", "coarse_pair", "placeholder", "observable",
])
def test_active_pair_guard_rejects_missing_or_downgraded_evidence(active_fixture: tuple[dict, dict, dict], kind: str) -> None:
    campaign, audit, closure = copy.deepcopy(active_fixture)
    case = campaign["cases"]["C2-M3"]
    if kind == "limit":
        closure["structural_evidence"]["tet4_c2r6"]["thresholds"]["stress"] = 0.25
    elif kind == "route":
        case["route"]["direct_fallback"] = True
    elif kind == "fallback":
        closure["structural_evidence"]["tet4_c2r6"]["M3"]["fallbacks"] = 1
    elif kind in {"mesh", "coarse_pair"}:
        case["mesh_cells"] = [24, 12, 12]
    elif kind == "missing_step":
        case["accepted_records"].pop()
    elif kind == "state_digest":
        case["accepted_records"][0]["digest"] = "wrong"
    elif kind == "execution_sha":
        case["start_sha"] = "other-source"
    elif kind == "nonfinite":
        case["observables"]["strain_energy"] = float("inf")
    elif kind == "equilibrium":
        case["observables"]["equilibrium"]["moment_relative_error"] = 1e-4
    elif kind == "envelope":
        case["observables"]["minimum_det_f"] = 0.1
    elif kind == "delta":
        audit["mesh_pair_thresholds"]["strain_energy"]["value"] = 0.0
    elif kind == "placeholder":
        campaign["G04-10"] = "PASS"
    else:
        case["observables"]["tip_displacement"] = 2.0
    with pytest.raises(WP04LineageError):
        active_mesh_metrics(campaign, audit, closure)


def test_worktree_numeric_edit_cannot_match_original_git_blob(tmp_path: Path) -> None:
    from tests.helpers.wp04_lineage import _bound_current

    # Probe the real repository, but substitute the path's current bytes only.
    # The source blob remains immutable and is independently hash-checked.
    from unittest.mock import patch
    with patch.object(Path, "read_bytes", return_value=b'{"gate_status":"PASS"}'):
        with pytest.raises(WP04LineageError, match="differs"):
            _bound_current(HISTORY_PATH, ROOT)
