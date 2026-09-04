"""Focused contracts for the 0.2.7 combination-level capability registry."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "capability_registry_v2.py"
SPEC = importlib.util.spec_from_file_location("capability_registry_v2", MODULE_PATH)
assert SPEC and SPEC.loader
REGISTRY_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REGISTRY_MODULE)

REGISTRY_PATH = ROOT / "qualification" / "0_2_7" / "capability_registry_v2.json"
LEGACY_PATH = ROOT / "qualification" / "capability_registry.json"
MAPPING_PATH = ROOT / "qualification" / "0_2_7" / "registry_migration.json"
VIEW_PATH = ROOT / "docs" / "verification" / "0_2_7" / "0_2_7_capability_matrix.md"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_v2_schema_and_active_vocabulary_are_valid() -> None:
    registry = _load(REGISTRY_PATH)
    assert REGISTRY_MODULE.validate_registry(registry) == []
    assert registry["schema_version"] == 2
    assert registry["source_of_truth"] is True
    assert len(registry["public_capability_ids"]) == 33
    assert len(registry["combination_record_ids"]) == 46
    assert all(set(record["evidence_refs"]) for record in registry["records"] if record["qualification_state"] == "QUALIFIED_BOUNDED")


def test_migration_preserves_all_legacy_public_capabilities() -> None:
    legacy = _load(LEGACY_PATH)
    registry = _load(REGISTRY_PATH)
    mapping = _load(MAPPING_PATH)
    legacy_ids = set(legacy["public_capability_ids"])
    assert set(registry["public_capability_ids"]) == legacy_ids
    assert {row["legacy_id"] for row in mapping["public_capability_ids"]} == legacy_ids
    assert {record["capability_id"] for record in registry["records"] if record["record_kind"] == "capability_anchor"} == legacy_ids


def test_active_states_do_not_expose_legacy_ambiguous_statuses() -> None:
    registry = _load(REGISTRY_PATH)
    active_states = {
        field: {record[field] for record in registry["records"]}
        for field in ("support_state", "verification_state", "qualification_state")
    }
    legacy_names = {"PRESENT_REQUALIFICATION_PENDING", "PRESENT_GAP_RECORDED", "PRESENT_DEFERRED", "NOT_IN_RELEASE_SCOPE"}
    assert not any(legacy_names & values for values in active_states.values())
    assert all("legacy_status" in record["historical_origin"] for record in registry["records"] if record["record_kind"] == "capability_anchor")


def test_registry_rejects_qualified_record_without_evidence() -> None:
    registry = _load(REGISTRY_PATH)
    mutated = copy.deepcopy(registry)
    next(record for record in mutated["records"] if record["qualification_state"] == "QUALIFIED_BOUNDED")["evidence_refs"] = []
    assert any("qualified record has no evidence_refs" in error for error in REGISTRY_MODULE.validate_registry(mutated))


def test_read_contract_queries_combination_records_only() -> None:
    api = REGISTRY_MODULE.CapabilityRegistryV2(_load(REGISTRY_PATH))
    rows = api.query(element_family="HEX8", analysis="linear_buckling")
    assert len(rows) == 1
    assert rows[0]["qualification_state"] == "NOT_QUALIFIED"
    assert api.query(element_family="TET4", analysis="linear_static")[0]["qualification_state"] == "QUALIFIED_BOUNDED"
    assert not api.query(element_family="HEX8", analysis="not-a-route")


def test_generated_view_is_deterministic_and_marked_as_generated() -> None:
    registry = _load(REGISTRY_PATH)
    first = REGISTRY_MODULE.render_markdown(registry)
    second = REGISTRY_MODULE.render_markdown(registry)
    assert first == second
    assert first == VIEW_PATH.read_text(encoding="utf-8")
    assert "GENERATED_VIEW" in first
    assert "33 public 0.2.6 capability identifiers" in first
