"""Focused contracts for the additive 0.2.6 V&V foundation framework."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from solveur.core.router import AnalysisRouter
from solveur.verification.g06_analytical import evaluate_free_dof_oracle
from solveur.verification.framework import VnvCaseError, VnvRegistry, VnvRunner
from solveur.io.json_reader import JsonModelReader


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "qualification" / "0_2_6" / "case_registry.json"
DOCS_ROOT = ROOT / "docs" / "verification" / "0_2_6"
DATA_ROOT = ROOT / "qualification" / "0_2_6"


def test_registry_has_exact_corpus_and_separate_smoke_g05_and_g06_batches() -> None:
    registry = VnvRegistry.from_file(REGISTRY_PATH)

    assert len(registry.cases) == 180
    assert len(registry.select(profile="SMOKE")) == 10
    assert len(registry.select(profile="G05")) == 50
    assert len(registry.select(profile="G06")) == 80
    assert len(registry.select(profile="FULL")) == 140
    assert registry.digest == VnvRegistry.from_file(REGISTRY_PATH).digest


def test_foundation_documents_and_machine_data_are_present() -> None:
    required_documents = {
        "0_2_6_master_plan.md",
        "0_2_6_architecture_audit.md",
        "0_2_6_requirements_matrix.md",
        "0_2_6_vnv_architecture.md",
        "0_2_6_campaign_matrix.md",
        "0_2_6_gate_matrix.md",
        "0_2_6_risk_register.md",
        "0_2_6_work_packages.md",
    }
    required_data = {"requirements.json", "g05_requirements.json", "risk_register.json", "work_packages.json", "gates.json"}

    assert required_documents.issubset(path.name for path in DOCS_ROOT.iterdir())
    assert required_data.issubset(path.name for path in DATA_ROOT.iterdir())


def test_g05_contract_has_modal_dynamic_and_harmonic_targets() -> None:
    contract = json.loads((DATA_ROOT / "g05_requirements.json").read_text(encoding="utf-8"))
    requirements = {row["id"]: row for row in contract["requirements"]}
    assert requirements["G05-MOD-001"]["target_case_count"] == 14
    assert requirements["G05-DYN-001"]["target_case_count"] == 16
    assert requirements["G05-HAR-001"]["target_case_count"] == 12
    assert all(row["threshold"]["status"] in {"DEFINED_FROM_EXISTING_CONTRACT", "UNDEFINED_POLICY"} for row in requirements.values())


def test_g05b_deep_registry_has_requested_family_counts() -> None:
    registry = VnvRegistry.from_file(DATA_ROOT / "g05_deep_case_registry.json")
    assert len(registry.select(profile="G05B", tags=("modal",))) == 4
    assert len(registry.select(profile="G05B", tags=("dynamic",))) == 4
    assert len(registry.select(profile="G05B", tags=("harmonic",))) == 4


def test_registry_rejects_duplicate_case_ids() -> None:
    registry = VnvRegistry.from_file(REGISTRY_PATH)

    with pytest.raises(VnvCaseError, match="Duplicate"):
        VnvRegistry((registry.cases[0], registry.cases[0]))


def test_runner_rejects_models_outside_the_controlled_examples_directory() -> None:
    registry = VnvRegistry.from_file(REGISTRY_PATH)
    unsafe = replace(registry.select(profile="SMOKE")[0], input_model="pyproject.toml")

    with pytest.raises(ValueError, match="outside the controlled examples"):
        VnvRunner(ROOT)._model_path(unsafe)


def test_runner_records_expected_failure_and_manifest_digests(tmp_path: Path) -> None:
    registry = VnvRegistry.from_file(REGISTRY_PATH)
    summary = VnvRunner(ROOT).run(
        registry,
        tmp_path,
        profile="SMOKE",
        case_ids=("VNV026-ADV-INVERTED-TET4-001",),
    )

    assert summary["status"] == "PASS"
    assert summary["expected_failure_count"] == 1
    result = json.loads((tmp_path / "vnv026-adv-inverted-tet4-001.json").read_text(encoding="utf-8"))
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert result["status"] == "EXPECTED_FAILURE"
    assert result["timestamp_utc"].endswith("Z")
    assert result["solver_version"] == "0.2.6a0"
    assert result["threshold_source"] == "qualification/0_2_6/tolerance_policy.json"
    assert result["artifact_digests"]["case_payload"]
    assert manifest["result_files"][0]["sha256"]
    assert manifest["threshold_source"] == "qualification/0_2_6/tolerance_policy.json"


def test_runner_applies_declared_analysis_override_to_string_model(tmp_path: Path) -> None:
    registry = VnvRegistry.from_file(REGISTRY_PATH)

    summary = VnvRunner(ROOT).run(
        registry,
        tmp_path,
        profile="G06",
        case_ids=("VNV026-RBT-G06-002",),
    )

    assert summary["status"] == "PASS"
    assert summary["pass_count"] == 1


def test_g06_analytical_oracle_matches_all_four_solid_families() -> None:
    cases = {
        "TET4": "examples/tet4_g06_analytic.json",
        "TET10": "examples/tet10_g06_analytic.json",
        "HEX8": "examples/hex8_g06_analytic.json",
        "HEX20": "examples/hex20_g06_analytic.json",
    }
    for family, relative_path in cases.items():
        raw = json.loads((ROOT / relative_path).read_text(encoding="utf-8"))
        result = AnalysisRouter().solve(JsonModelReader().from_dict(raw)).to_dict()
        oracle = evaluate_free_dof_oracle(
            raw,
            result,
            {"type": "constrained_free_dof", "element_family": family, "free_node": 1, "free_dof": "UX"},
        )
        assert oracle["status"] == "PASS"
        assert oracle["relative_error"] <= 1.0e-12
