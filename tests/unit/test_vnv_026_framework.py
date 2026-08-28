"""Focused contracts for the additive 0.2.6 V&V foundation framework."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from solveur.verification.framework import VnvCaseError, VnvRegistry, VnvRunner


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
    required_data = {"requirements.json", "risk_register.json", "work_packages.json", "gates.json"}

    assert required_documents.issubset(path.name for path in DOCS_ROOT.iterdir())
    assert required_data.issubset(path.name for path in DATA_ROOT.iterdir())


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
