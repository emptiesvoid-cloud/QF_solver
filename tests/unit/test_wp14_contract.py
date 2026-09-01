from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.validate_wp14_contract import CONTRACT_PATH, load_contract, validate_contract


def test_wp14_contract_is_valid_and_reaches_true_one_million_dof() -> None:
    contract = load_contract()
    assert validate_contract(contract) == []
    assert contract["reference_model"]["mesh"]["true_dof"] == 1_029_000
    assert contract["reference_model"]["mesh"]["element_count"] == 1_971_054


def test_wp14_contract_is_deterministic_json_and_has_no_implicit_fallback() -> None:
    first = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    second = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert first == second
    assert first["solver_contract"]["backend_selection"] == "explicit_only"
    assert first["solver_contract"]["fallback_policy"].startswith("none")
    assert first["solver_contract"]["random_seed"] == 0
    assert "timestamp_utc" in first["evidence_schema"]["required_fields"]
    assert first["acceptance_metrics"]["post_result_retuning"] is False


def test_wp14_validator_cli_passes() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/validate_wp14_contract.py"],
        cwd=Path(__file__).resolve().parents[2],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
