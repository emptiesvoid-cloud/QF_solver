"""Deterministically migrate the legacy capability registry to registry v2."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from capability_registry_v2 import ROOT, render_markdown, validate_registry


LEGACY_PATH = ROOT / "qualification" / "capability_registry.json"
G14_PATH = ROOT / "qualification" / "0_2_6" / "g14_capability_coverage.json"
V2_PATH = ROOT / "qualification" / "0_2_7" / "capability_registry_v2.json"
MAPPING_PATH = ROOT / "qualification" / "0_2_7" / "registry_migration.json"
VIEW_PATH = ROOT / "docs" / "verification" / "0_2_7" / "0_2_7_capability_matrix.md"
SOURCE_SNAPSHOT = "e839373b6aef291a93292186d7553ba5cd12af55"
TARGET_VERSION = "0.2.7a0"

ELEMENT_FAMILIES = {
    "ELE-BEAM2": "BEAM2",
    "ELE-MITC3": "MITC3",
    "ELE-MITC4": "MITC4",
    "ELE-TET4": "TET4",
    "ELE-TET10": "TET10",
    "ELE-HEX8": "HEX8",
    "ELE-HEX20": "HEX20",
    "ELE-DISCRETE": "DISCRETE",
}
ANALYSES = {
    "ANA-STATIC": "linear_static",
    "ANA-MODAL": "modal",
    "ANA-NEWMARK": "newmark_transient",
    "ANA-HARMONIC": "harmonic",
    "ANA-BUCKLING": "linear_buckling",
    "ANA-NONLINEAR-LOAD": "nonlinear_load_control",
    "ANA-GEOMETRIC-NONLINEAR": "geometric_nonlinear_static",
}


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _active_state(legacy: dict[str, Any]) -> str:
    maturity = legacy["MATURITY"]
    if maturity == "QUALIFIED_BOUNDED":
        return "QUALIFIED_BOUNDED"
    if maturity == "RESEARCH":
        return "NOT_QUALIFIED" if legacy["CAPABILITY_ID"] in {"MAT-FINITE-J2", "CON-FRICTION"} else "EXPERIMENTAL"
    return "EXPERIMENTAL"


def _verification_state(legacy: dict[str, Any]) -> str:
    if legacy["VNV_LEVEL"] == "L3":
        return "VERIFIED"
    if legacy["VNV_LEVEL"] == "L2":
        return "VERIFIED"
    if legacy["VNV_LEVEL"] == "L1":
        return "TESTED"
    return "SUPPORTED"


def _record_base(legacy: dict[str, Any], *, kind: str, capability_id: str) -> dict[str, Any]:
    state = _active_state(legacy)
    return {
        "capability_id": capability_id,
        "record_kind": kind,
        "element_family": legacy["ELEMENT"],
        "analysis": legacy["ANALYSIS"],
        "material_model": legacy["MATERIAL_PHYSICS"],
        "formulation_or_route": "legacy_aggregate_scope",
        "backend_or_solver_route": "not separately declared in legacy registry",
        "support_state": "SUPPORTED" if legacy["PRESENT_IN_CODE"] else "NOT_QUALIFIED",
        "verification_state": _verification_state(legacy),
        "qualification_state": state,
        "evidence_refs": list(legacy["EVIDENCE"]),
        "owner_decision": "INHERITED_0_2_6_SCOPE",
        "limitations": legacy["LIMITATIONS"],
        "applicable_version": TARGET_VERSION,
        "source_snapshot": legacy["LAST_VERIFIED_SHA"],
        "supersedes": [legacy["CAPABILITY_ID"]],
        "historical_origin": {
            "legacy_capability_id": legacy["CAPABILITY_ID"],
            "legacy_maturity": legacy["MATURITY"],
            "legacy_status": legacy["STATUS"],
            "legacy_gate_or_wp": legacy["026_GATE_OR_WP"],
            "source_registry": "qualification/capability_registry.json",
            "migration_note": "Traceability anchor; aggregate legacy scope is not new combination evidence.",
        },
    }


def _combination_record(element: dict[str, Any], analysis: dict[str, Any], combo: dict[str, str]) -> dict[str, Any]:
    element_id = combo["element"]
    analysis_id = combo["analysis"]
    capability_id = f"COMB-{ELEMENT_FAMILIES[element_id]}-{ANALYSES[analysis_id]}"
    state = "QUALIFIED_BOUNDED" if _active_state(element) == _active_state(analysis) == "QUALIFIED_BOUNDED" else "EXPERIMENTAL"
    limitation = "Combination state is inherited from aggregate 0.2.6 records; no new execution evidence is implied."
    owner_decision = "INHERITED_0_2_6_SCOPE"
    if element_id == "ELE-HEX8" and analysis_id == "ANA-BUCKLING":
        state = "NOT_QUALIFIED"
        owner_decision = "INHERITED_G14_MORE_EVIDENCE_REQUIRED"
        limitation = "G14 explicitly retains HEX8 buckling as more-evidence-required."
    return {
        "capability_id": capability_id,
        "record_kind": "combination",
        "element_family": ELEMENT_FAMILIES[element_id],
        "analysis": ANALYSES[analysis_id],
        "material_model": element["MATERIAL_PHYSICS"],
        "formulation_or_route": "element_route_with_legacy_analysis_mapping",
        "backend_or_solver_route": "not separately declared in legacy registry",
        "support_state": "SUPPORTED" if element["PRESENT_IN_CODE"] else "NOT_QUALIFIED",
        "verification_state": "VERIFIED" if element["VNV_LEVEL"] in {"L2", "L3"} and analysis["VNV_LEVEL"] in {"L2", "L3"} else "TESTED",
        "qualification_state": state,
        "evidence_refs": _unique(list(element["EVIDENCE"]) + list(analysis["EVIDENCE"])),
        "owner_decision": owner_decision,
        "limitations": f"{limitation} {element['LIMITATIONS']} {analysis['LIMITATIONS']}",
        "applicable_version": TARGET_VERSION,
        "source_snapshot": element["LAST_VERIFIED_SHA"],
        "supersedes": [f"{element_id}/{analysis_id}"],
        "historical_origin": {
            "legacy_capability_id": element_id,
            "legacy_analysis_id": analysis_id,
            "source_registry": "qualification/capability_registry.json",
            "source_snapshot": SOURCE_SNAPSHOT,
            "migration_note": "Combination mapping derived from the controlled public_analysis_combinations list; no new qualification is introduced.",
        },
    }


def build_registry() -> tuple[dict[str, Any], dict[str, Any]]:
    legacy = _read(LEGACY_PATH)
    g14 = _read(G14_PATH)
    if g14["public_status_guardrails"]["G08_HEX8_BUCKLING"] != "MORE_EVIDENCE_REQUIRED":
        raise ValueError("G14 HEX8 buckling guardrail changed; migration requires review")
    by_id = {row["CAPABILITY_ID"]: row for row in legacy["capabilities"]}
    anchors = [_record_base(row, kind="capability_anchor", capability_id=row["CAPABILITY_ID"]) for row in legacy["capabilities"]]
    combinations = [
        _combination_record(by_id[item["element"]], by_id[item["analysis"]], item)
        for item in legacy["public_analysis_combinations"]
    ]
    records = anchors + combinations
    registry = {
        "schema_version": 2,
        "registry_id": "QF-SOLVER-CAPABILITY-REGISTRY-V2",
        "source_of_truth": True,
        "applicable_version": TARGET_VERSION,
        "source_snapshot": SOURCE_SNAPSHOT,
        "public_capability_ids": list(legacy["public_capability_ids"]),
        "combination_record_ids": [record["capability_id"] for record in combinations],
        "migration": {
            "from_registry": "qualification/capability_registry.json",
            "from_schema_version": legacy["schema_version"],
            "source_public_capability_count": len(legacy["public_capability_ids"]),
            "migrated_capability_count": len(anchors),
            "combination_record_count": len(combinations),
            "source_snapshot": SOURCE_SNAPSHOT,
            "g14_guardrail_source": "qualification/0_2_6/g14_capability_coverage.json",
        },
        "vocabulary": {state: description for state, description in {
            "SUPPORTED": "implementation path declared",
            "TESTED": "case executed",
            "VERIFIED": "quantitative check or invariant recorded",
            "QUALIFIED_BOUNDED": "Owner-controlled qualification within declared scope",
            "EXPERIMENTAL": "available or exercised without bounded qualification",
            "NOT_QUALIFIED": "explicitly outside qualified scope",
            "SUPERSEDED": "retained only for historical traceability",
        }.items()},
        "policy": {
            "presence_is_not_maturity": True,
            "supported_is_not_verified": True,
            "verified_is_not_qualified": True,
            "qualified_requires_evidence_refs": True,
            "aggregate_migration_is_not_new_evidence": True,
            "generated_views_are_not_source_records": True,
        },
        "records": records,
    }
    mapping = {
        "schema_version": 1,
        "source_registry": "qualification/capability_registry.json",
        "source_snapshot": SOURCE_SNAPSHOT,
        "target_registry": "qualification/0_2_7/capability_registry_v2.json",
        "public_capability_ids": [
            {"legacy_id": row["CAPABILITY_ID"], "v2_anchor_id": row["CAPABILITY_ID"], "legacy_status": row["STATUS"]}
            for row in legacy["capabilities"]
        ],
        "combination_mapping": {
            "source": "public_analysis_combinations",
            "records": [
                {"element": item["element"], "analysis": item["analysis"], "v2_id": f"COMB-{ELEMENT_FAMILIES[item['element']]}-{ANALYSES[item['analysis']]}"}
                for item in legacy["public_analysis_combinations"]
            ],
        },
        "historical_status_policy": "Legacy statuses remain in historical_origin only; active v2 states use the closed vocabulary.",
    }
    return registry, mapping


def main() -> int:
    registry, mapping = build_registry()
    errors = validate_registry(registry)
    if errors:
        raise SystemExit("\n".join(errors))
    V2_PATH.write_text(json.dumps(registry, indent=2, ensure_ascii=True) + "\n", encoding="utf-8", newline="\n")
    MAPPING_PATH.write_text(json.dumps(mapping, indent=2, ensure_ascii=True) + "\n", encoding="utf-8", newline="\n")
    VIEW_PATH.write_text(render_markdown(registry), encoding="utf-8", newline="\n")
    print(f"Generated {V2_PATH} and {MAPPING_PATH}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
