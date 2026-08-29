"""Contracts that prevent QF Solver capabilities from disappearing from 0.2.6 planning."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "audit_capability_registry.py"
SPEC = importlib.util.spec_from_file_location("capability_registry_audit", MODULE_PATH)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def test_controlled_capability_registry_passes_its_contract() -> None:
    assert AUDIT.validate_registry(AUDIT.load_registry()) == []


def test_registry_rejects_duplicate_capability_ids() -> None:
    registry = AUDIT.load_registry()
    registry["capabilities"].append(copy.deepcopy(registry["capabilities"][0]))

    assert any("Duplicate CAPABILITY_ID" in error for error in AUDIT.validate_registry(registry))


def test_registry_rejects_orphaned_public_capability() -> None:
    registry = AUDIT.load_registry()
    registry["capabilities"] = [row for row in registry["capabilities"] if row["CAPABILITY_ID"] != "ANA-MODAL"]

    assert any("Public capability orphaned" in error for error in AUDIT.validate_registry(registry))


def test_registry_rejects_orphaned_public_element_analysis_combination() -> None:
    registry = AUDIT.load_registry()
    registry["public_analysis_combinations"].append({"element": "ELE-TET4", "analysis": "ANA-NOT-REGISTERED"})

    assert any("Public element/analysis combination is orphaned" in error for error in AUDIT.validate_registry(registry))


def test_registry_rejects_an_unregistered_source_family() -> None:
    registry = AUDIT.load_registry()
    registry["capabilities"] = [row for row in registry["capabilities"] if row["CAPABILITY_ID"] != "ELE-TET4"]

    assert any("Implemented capability is unregistered: ELE-TET4" in error for error in AUDIT.validate_registry(registry))


def test_registry_rejects_an_unregistered_analysis_route() -> None:
    registry = AUDIT.load_registry()
    registry["capabilities"] = [
        row for row in registry["capabilities"] if row["CAPABILITY_ID"] != "ANA-GEOMETRIC-NONLINEAR"
    ]

    assert any("Public analysis route is unregistered: geometric_nonlinear_static" in error for error in AUDIT.validate_registry(registry))


def test_registry_rejects_a_missing_status_and_silent_historical_removal() -> None:
    registry = AUDIT.load_registry()
    registry["capabilities"][0].pop("STATUS")
    registry["capabilities"] = [row for row in registry["capabilities"] if row["CAPABILITY_ID"] != "ANA-ARC-LENGTH"]

    errors = AUDIT.validate_registry(registry)

    assert any("missing required fields: STATUS" in error for error in errors)
    assert any("Historical capability silently removed: ANA-ARC-LENGTH" in error for error in errors)


def test_registry_rejects_a_rewritten_historical_release_inventory() -> None:
    registry = AUDIT.load_registry()
    registry["historical_releases"][0]["elements"].remove("TET10")

    assert any("Historical element inventory changed unexpectedly" in error for error in AUDIT.validate_registry(registry))


def test_registry_requires_implemented_capabilities_to_explain_evidence_or_scope() -> None:
    registry = AUDIT.load_registry()
    row = registry["capabilities"][0]
    row["TESTS"] = []
    row["026_GATE_OR_WP"] = ""
    row["LIMITATIONS"] = ""

    assert any("has no test, gate or limitation justification" in error for error in AUDIT.validate_registry(registry))


def test_coverage_document_is_generated_from_the_controlled_registry() -> None:
    document = AUDIT.render_document(AUDIT.load_registry())

    assert "# Capability Coverage Register" in document
    assert "G05-B Integration And Open Gaps" in document
    assert "OWNER_APPROVED_BOUNDED" in document
    assert "v0.2.0-alpha" in document
