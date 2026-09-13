"""Governing-branch integration guards for the bounded WP07 candidate."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from scripts.prepare_wp07d_structural_vnv import load_contract, validate_contract


ROOT = Path(__file__).resolve().parents[2]
QUALIFICATION = ROOT / "qualification" / "0_2_9"


def _record(name: str) -> dict[str, Any]:
    return json.loads((QUALIFICATION / name).read_text(encoding="utf-8"))


def test_wp07_a_b_c_contracts_revalidate_on_governing_tree() -> None:
    contract_a = _record("wp07a_contact_formulation_contract.json")
    contract_b = _record("wp07b_contact_evaluation_restart.json")
    contract_c = _record("wp07c_contact_identities.json")

    assert contract_a["gate"] == "WP07"
    assert contract_a["work_package"] == "WP07-A"
    assert contract_a["formulation_regimes"]["LINEAR_ACTIVE_SET_INITIAL_SEARCH"]["baseline_scope"] is True
    assert contract_a["formulation_regimes"]["NONLINEAR_PENALTY_INITIAL_SEARCH"]["baseline_scope"] is True
    assert contract_a["formulation_regimes"]["UPDATED_SEARCH_FINITE_SLIDING"]["status"] == "RESEARCH_ONLY"
    assert contract_b["contact_evaluation_contract"]["persistent_contact_state_mutated"] is False
    assert contract_b["restart_contract"]["model_signature_required_for_full_restart"] is True
    assert contract_b["restart_contract"]["accepted_state_digest_required_for_full_restart"] is True
    assert contract_c["qualification_campaign_executed"] is False
    assert contract_c["governance"]["contact_mechanics_changed"] is False


def test_wp07_d_and_e_remain_preparation_only_and_fail_closed() -> None:
    contract_d = load_contract()
    validate_contract(contract_d)
    contract_e = _record("wp07e_closure_contract.json")

    assert contract_d["structural_solves_run"] is False
    assert contract_d["external_solver_run"] is False
    assert contract_d["execution_policy"]["structural_solves_allowed"] is False
    assert contract_e["qualification_campaign_executed"] is False
    assert contract_e["decision_matrix"]["no_downgrade_rule"]
    assert contract_e["governance"]["structural_solves_run"] is False


def test_wp07_contact_identity_observations_pass_frozen_limits() -> None:
    contract_c = _record("wp07c_contact_identities.json")
    observed = contract_c["observed_results"]
    thresholds = contract_c["frozen_thresholds"]

    assert observed["penalty_energy_gradient_relative_error"] <= thresholds["penalty_energy_gradient_relative"]
    assert observed["penalty_tangent_frobenius_relative_error"] <= thresholds["penalty_tangent_frobenius_relative"]
    assert observed["penalty_tangent_max_column_relative_error"] <= thresholds["penalty_tangent_max_column_relative"]
    assert observed["penalty_tangent_symmetry_relative_error"] <= thresholds["penalty_tangent_symmetry_relative"]
    assert observed["active_set_force_equilibrium_relative_error"] <= thresholds["equilibrium_force_relative"]
    assert observed["active_set_moment_equilibrium_relative_error"] <= thresholds["equilibrium_moment_relative"]


def test_wp07_contact_public_exports_are_safe_for_model_first_import() -> None:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from solveur.core.model import FiniteElementModel; from solveur.contact import ContactEvaluation; print('ok')",
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"
