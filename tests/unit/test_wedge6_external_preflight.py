"""Targeted WP05 checks for external WEDGE6 oracle preflight artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from solveur.compatibility.descriptors import get_element_descriptor
from solveur.verification.v2 import (
    DuplicateJsonKeyError,
    ExternalUnavailableError,
    VnvRunner,
    canonical_sha256,
    load_cases,
    load_json_strict,
)


ROOT = Path(__file__).resolve().parents[2]
ORACLE_ROOT = ROOT / "qualification" / "0_2_7" / "external_oracles" / "wedge6"
SOURCE_SHA = "fb102e649235a276096b3a37e19eb61e19a5b43f"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_wp05_records_and_case_catalog_are_controlled() -> None:
    contract = read_json(ORACLE_ROOT / "contract.json")
    mapping = read_json(ORACLE_ROOT / "mapping.json")
    evidence = read_json(ORACLE_ROOT / "preflight_evidence.json")
    registry = read_json(ROOT / "qualification" / "0_2_7" / "capability_registry_v2.json")
    cases = load_cases(ORACLE_ROOT / "specs" / "cases.json")

    assert contract["source_sha"] == SOURCE_SHA
    assert contract["candidate_element"] == {
        "qf_name": "WEDGE6",
        "implemented": False,
        "public_capability": False,
        "dimension": 3,
        "node_count": 6,
        "topology": "linear triangular prism",
        "faces": ["TRI3", "TRI3", "QUAD4", "QUAD4", "QUAD4"],
    }
    assert mapping["source_sha"] == SOURCE_SHA
    assert mapping["primary_node_order"]["qf_future_wedge6"] == [1, 2, 3, 4, 5, 6]
    assert len(mapping["face_mapping"]) == 5
    assert {tuple(face["topological_nodes"]) for face in mapping["face_mapping"]} == {
        (1, 2, 3),
        (4, 5, 6),
        (1, 2, 5, 4),
        (2, 3, 6, 5),
        (3, 1, 4, 6),
    }
    assert len(cases) == 8
    assert all(case.element == "WEDGE6" for case in cases)
    assert all(case.requirement_id == "027-REQ-006" for case in cases)
    assert all(case.provenance["campaign_state"] in {"PLANNED", "READY_CALCULIX_PLANNED_CODE_ASTER"} for case in cases)
    assert evidence["source_sha"] == SOURCE_SHA
    assert evidence["calculated_deck_validation"]["not_qf_correlation"] is True
    assert evidence["code_aster_deck_validation"]["not_qf_correlation"] is True
    assert "ELE-WEDGE6" not in registry["public_capability_ids"]


def test_preflight_deck_digests_match_recorded_outputs() -> None:
    evidence = read_json(ORACLE_ROOT / "preflight_evidence.json")
    calculix = evidence["calculated_deck_validation"]
    assert sha256(ORACLE_ROOT / calculix["input"]) == calculix["input_sha256"]
    for output in calculix["outputs"]:
        assert sha256(ORACLE_ROOT / output["path"]) == output["sha256"]

    code_aster = evidence["code_aster_deck_validation"]
    assert sha256(ORACLE_ROOT / code_aster["mesh"]) == code_aster["mesh_sha256"]
    assert sha256(ORACLE_ROOT / code_aster["command_file"]) == code_aster["command_file_sha256"]
    for output in code_aster["outputs"]:
        assert sha256(ORACLE_ROOT / output["path"]) == output["sha256"]


def test_external_unavailability_is_an_explicit_skip() -> None:
    case = load_cases(ORACLE_ROOT / "specs" / "cases.json")[0]
    evidence = VnvRunner(source_sha=SOURCE_SHA).run(
        case,
        lambda _case: (_ for _ in ()).throw(ExternalUnavailableError("external tool unavailable")),
    )
    assert evidence.verdict == "SKIPPED_EXTERNAL_UNAVAILABLE"
    assert "unavailable" in (evidence.failure_reason or "")


def test_mapping_and_metadata_hashes_are_deterministic_without_wedge6_route() -> None:
    mapping = read_json(ORACLE_ROOT / "mapping.json")
    assert canonical_sha256(mapping) == canonical_sha256(read_json(ORACLE_ROOT / "mapping.json"))
    with pytest.raises(KeyError, match="Unknown element family"):
        get_element_descriptor("WEDGE6")


def test_duplicate_json_keys_are_rejected_explicitly(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"primary_observables": ["displacement"], "primary_observables": []}', encoding="utf-8")

    with pytest.raises(DuplicateJsonKeyError, match="Duplicate JSON key 'primary_observables'"):
        load_json_strict(duplicate)


def test_external_tolerance_categories_are_predeclared_and_non_retunable() -> None:
    contract = load_json_strict(ORACLE_ROOT / "contract.json")
    comparison = contract["comparability_contract"]
    assert comparison["primary_observables"] == ["displacement", "total_reaction", "strain_energy"]
    policy = comparison["tolerance_policy"]
    assert policy["categories"]["AFFINE_SAME_MESH"]["relative_tolerance"] == pytest.approx(1.0e-6)
    assert policy["categories"]["NON_AFFINE_DISTORTED_REFINEMENT"]["relative_tolerance"] is None
    assert policy["post_observation_retuning"].startswith("FORBIDDEN")
