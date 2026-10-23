"""Metadata decision regressions using synthetic records only; no J2 or FEM."""
from __future__ import annotations

from copy import deepcopy
import unittest
from finalize_inventory import validate_inventory_provenance_links

from integrate_proofs import (
    EXPECTED_ACTION_POINTS,
    build_final_inventory,
    derive_final_decision,
    serialize_json,
    validate_final_inventory,
)
from archive_inputs import extraction_stage_metadata


def _point(point_id: str, branch: str = "plastic") -> dict:
    decisive = {
        "lo": {"numerator": "1", "denominator": "1"},
        "hi": {"numerator": "2", "denominator": "1"},
    }
    if branch == "elastic":
        decisive = {
            "lo": {"numerator": "-2", "denominator": "1"},
            "hi": {"numerator": "-1", "denominator": "1"},
        }
    return {
        "point_id": point_id,
        "point_verdict": "PASS",
        "mathematical_verdict_for_exact_real_target": "PASS",
        "expected_branch_from_archive": branch,
        "production_branch_archived": branch,
        "bounds": {
            "minimum_margin_range": decisive if branch == "plastic" else {
                "lo": {"numerator": "-3", "denominator": "1"},
                "hi": {"numerator": "-2", "denominator": "1"},
            },
            "maximum_margin_range": decisive if branch == "elastic" else {
                "lo": {"numerator": "2", "denominator": "1"},
                "hi": {"numerator": "3", "denominator": "1"},
            },
            "sqrt_squared_checks": {
                "minimum": {"lower_squared_le_input": True, "upper_squared_ge_input": True},
                "maximum": {"lower_squared_le_input": True, "upper_squared_ge_input": True},
            },
        },
        "production_branch_budget": {
            "verdict": "PASS",
            "expected_branch": branch,
            "archived_elastic": branch == "elastic",
            "archive_provenance_validated": True,
            "frozen_source_identity_validated": True,
            "production_branch_linkage_valid": True,
            "base_clearance_dominates_B": True,
            "mathematical_base_sign_status": "PASS",
            "production_sign_status": "PASS",
            "mathematical_segment_sign_status": "PASS",
            "a_posteriori_discrepancy_bound_B_exact": {"numerator": "1", "denominator": "1"},
            "rounding_budget_scope": "a_posteriori_base_state_discrepancy_only_not_a_priori_segment_budget",
        },
    }


def _proof_results(action_ids: list[str] | None = None) -> list[dict]:
    selected = list(EXPECTED_ACTION_POINTS) if action_ids is None else action_ids
    result = []
    for action_id in selected:
        count = EXPECTED_ACTION_POINTS[action_id]
        points = [_point(f"p{i}") for i in range(count)]
        result.append({
            "action_id": action_id,
            "action_verdict": "PASS",
            "point_count": count,
            "points": points,
            "mathematical_candidate_verdict": "PASS",
            "mathematical_point_pass_count": count,
            "production_point_pass_count": count,
            "production_branch_linkage_valid": True,
            "production_rounding_budget_valid": True,
            "provenance_valid": True,
            "complete_archive_inputs_valid": True,
        })
    return result


def _extraction(complete: bool = True) -> dict:
    return {
        "snapshot_commit": "87e54913077c7d9fce6f259fb4a4a11f5295e6a5",
        "snapshot_tree": "c42e3c2241af1862d66cab51a38fda74a1167361",
        "all_eight_raw_input_archives_complete": complete,
        "actions": [
            {"action_id": action_id, "point_count": count, "branch_linkage_valid": False}
            for action_id, count in EXPECTED_ACTION_POINTS.items()
        ],
        "archives": [{"manifest_sha256": "frozen-archive-identity"}],
        "reason": "intermediate extraction: branch linkage has not yet been evaluated",
    }


class MetadataFinalizationTests(unittest.TestCase):
    def test_incomplete_extraction_cannot_become_ready(self):
        stage = extraction_stage_metadata()
        self.assertEqual(stage["technical_aggregate_verdict"], "NOT_EVALUATED")
        self.assertFalse(stage["extraction_stage"]["strict_action_proofs_ready"])
        decision = derive_final_decision(_extraction(False), _proof_results())
        self.assertEqual(decision["technical_aggregate_verdict"], "INCONCLUSIVE")
        self.assertFalse(decision["strict_action_proofs_ready"])

    def test_demonstrated_branch_linkage_allows_technical_pass(self):
        decision = derive_final_decision(_extraction(), _proof_results())
        self.assertEqual(decision["technical_aggregate_verdict"], "PASS")
        self.assertTrue(decision["strict_action_proofs_ready"])

    def test_missing_branch_linkage_remains_inconclusive(self):
        results = _proof_results()
        results[0]["points"][0]["production_branch_budget"]["production_branch_linkage_valid"] = False
        decision = derive_final_decision(_extraction(), results)
        self.assertEqual(decision["technical_aggregate_verdict"], "INCONCLUSIVE")
        self.assertFalse(decision["strict_action_proofs_ready"])
        final = build_final_inventory(_extraction(), results, [])
        self.assertFalse(final["actions"][0]["branch_linkage_valid"])
        self.assertTrue(final["actions"][0]["production_rounding_budget_valid"])

    def test_partial_action_set_remains_inconclusive(self):
        results = _proof_results(list(EXPECTED_ACTION_POINTS)[:-1])
        decision = derive_final_decision(_extraction(), results)
        self.assertEqual(decision["technical_aggregate_verdict"], "INCONCLUSIVE")
        self.assertEqual(decision["action_count"], 7)

    def test_partial_extraction_action_rows_remain_inconclusive(self):
        extraction = _extraction()
        extraction["actions"] = extraction["actions"][:-1]
        decision = derive_final_decision(extraction, _proof_results())
        self.assertEqual(decision["technical_aggregate_verdict"], "INCONCLUSIVE")
        self.assertFalse(decision["strict_action_proofs_ready"])

    def test_pass_reason_matches_the_verified_proof_decision(self):
        inventory = build_final_inventory(_extraction(), _proof_results(), [{"action_id": "proof-id"}])
        validate_final_inventory(inventory)
        self.assertTrue(inventory["reason"].startswith("PASS: all 8/8 authorized actions and 304/304 points"))
        self.assertIn("base states", inventory["reason"])
        self.assertIn("a-posteriori at the base only", inventory["reason"])

    def test_pass_with_contradictory_reason_is_rejected(self):
        inventory = build_final_inventory(_extraction(), _proof_results(), [])
        inventory["reason"] = "branch linkage remains unproved"
        with self.assertRaisesRegex(ValueError, "reason contradicts"):
            validate_final_inventory(inventory)

    def test_inventory_serialization_is_deterministic(self):
        first = build_final_inventory(_extraction(), _proof_results(), [{"action_id": "same"}])
        second = build_final_inventory(_extraction(), _proof_results(), [{"action_id": "same"}])
        self.assertEqual(serialize_json(first), serialize_json(second))

    def test_snapshot_archive_and_proof_identities_are_preserved(self):
        extraction = _extraction()
        summaries = [{"action_id": "frozen-action", "proof_input_sha256": "input-hash", "proof_result_sha256": "result-hash"}]
        before_snapshot = (extraction["snapshot_commit"], extraction["snapshot_tree"])
        before_archives = deepcopy(extraction["archives"])
        final = build_final_inventory(extraction, _proof_results(), summaries)
        self.assertEqual((final["snapshot_commit"], final["snapshot_tree"]), before_snapshot)
        self.assertEqual(final["archives"], before_archives)
        self.assertEqual(final["proof_results"], summaries)
        self.assertTrue(all(action["branch_linkage_valid"] for action in final["actions"]))

    def _provenance_fixture(self):
        archives = [
            {"path": r"C:\archive\probe", "manifest": "archive_integrity.json", "manifest_sha256": "a" * 64,
             "verified_files": 28, "campaign_status": "INCOMPLETE"},
            {"path": r"C:\archive\hex8", "manifest": "artifact_inventory.json", "manifest_sha256": "b" * 64,
             "verified_files": 35, "campaign_status": "COMPLETED_EXPLORATORY"},
        ]
        adapters = [
            {"archive": r"C:\archive\probe", "commit": "commit-probe", "tree": "tree-probe", "file_sha256": {"a.py": "c" * 64}},
            {"archive": r"C:\archive\hex8", "commit": "commit-hex", "tree": "tree-hex", "file_sha256": {"a.py": "d" * 64}},
        ]
        expected = {
            "archives": deepcopy(archives),
            "historical_source_files": {"src/j2.py": "e" * 64},
            "capture_source_commits": deepcopy(adapters),
        }
        return expected, deepcopy(archives), deepcopy(adapters)

    def test_current_provenance_rechecks_bind_preserved_identities(self):
        expected, archives, adapters = self._provenance_fixture()
        validate_inventory_provenance_links(expected, archives, expected["historical_source_files"], adapters)

    def test_changed_archive_manifest_identity_is_rejected(self):
        expected, archives, adapters = self._provenance_fixture()
        archives[0]["manifest_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "manifest digest"):
            validate_inventory_provenance_links(expected, archives, expected["historical_source_files"], adapters)

    def test_changed_adapter_identity_is_rejected(self):
        expected, archives, adapters = self._provenance_fixture()
        adapters[1]["tree"] = "different-tree"
        with self.assertRaisesRegex(ValueError, "adapter commit/tree"):
            validate_inventory_provenance_links(expected, archives, expected["historical_source_files"], adapters)

    def test_changed_historical_source_hash_is_rejected(self):
        expected, archives, adapters = self._provenance_fixture()
        with self.assertRaisesRegex(ValueError, "historical source file hashes"):
            validate_inventory_provenance_links(expected, archives, {"src/j2.py": "f" * 64}, adapters)


if __name__ == "__main__":
    unittest.main()
