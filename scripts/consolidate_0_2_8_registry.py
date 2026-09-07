"""Build the cumulative, machine-readable QF Solver 0.2.8 registry."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "qualification" / "0_2_7" / "capability_registry_v2.json"
QUALIFICATION_ROOT = ROOT / "qualification" / "0_2_8"
OUTPUT_PATH = QUALIFICATION_ROOT / "consolidated_registry.json"

ROUTE_IDS = {
    "BEAM2_STATIC": "COMB-BEAM2-linear_static",
    "BEAM2_MODAL": "COMB-BEAM2-modal",
    "BEAM2_NEWMARK": "COMB-BEAM2-newmark_transient",
    "BEAM2_HARMONIC": "COMB-BEAM2-harmonic",
    "DISCRETE_STATIC": "COMB-DISCRETE-linear_static",
    "DISCRETE_MODAL": "COMB-DISCRETE-modal",
    "DISCRETE_NEWMARK": "COMB-DISCRETE-newmark_transient",
    "DISCRETE_HARMONIC": "COMB-DISCRETE-harmonic",
    "MITC3_STATIC": "COMB-MITC3-linear_static",
    "MITC3_MODAL": "COMB-MITC3-modal",
    "MITC3_NEWMARK": "COMB-MITC3-newmark_transient",
    "MITC3_HARMONIC": "COMB-MITC3-harmonic",
    "MITC4_STATIC": "COMB-MITC4-linear_static",
    "MITC4_MODAL": "COMB-MITC4-modal",
    "MITC4_NEWMARK": "COMB-MITC4-newmark_transient",
    "MITC4_HARMONIC": "COMB-MITC4-harmonic",
}

OWNER_RECORDS = {
    "WP03": QUALIFICATION_ROOT / "wp03_owner_gate_final.json",
    "WP04": QUALIFICATION_ROOT / "wp04_owner_gate_final.json",
    "WP05": QUALIFICATION_ROOT / "wp05_owner_gate_final.json",
    "WP11B": QUALIFICATION_ROOT / "wp11b_hex8_buckling_owner_gate_final.json",
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _owner_decision(
    *,
    work_package: str,
    record_path: Path,
    decision: dict[str, Any],
) -> dict[str, Any]:
    return {
        "work_package": work_package,
        "record": record_path.relative_to(ROOT).as_posix(),
        "owner_decision": decision.get("owner_decision"),
        "promotion_applied": bool(decision.get("promotion_applied", False)),
        "resulting_maturity": decision.get("resulting_maturity"),
        "scope": decision.get("scope"),
        "limitations": decision.get("limitations", []),
        "rejected_gate": decision.get("rejected_gate"),
    }


def _combination_records(source: dict[str, Any]) -> list[dict[str, Any]]:
    records = [row for row in source["records"] if row.get("record_kind") == "combination"]
    decisions: dict[str, list[dict[str, Any]]] = {row["capability_id"]: [] for row in records}
    final_state = {row["capability_id"]: row["qualification_state"] for row in records}

    wp03_path = OWNER_RECORDS["WP03"]
    wp03 = _load(wp03_path)
    for key, decision in wp03["decisions"].items():
        capability_id = ROUTE_IDS[key]
        decisions[capability_id].append(_owner_decision(work_package="WP03", record_path=wp03_path, decision=decision))
        if decision.get("promotion_applied"):
            final_state[capability_id] = decision["resulting_maturity"]

    wp04_path = OWNER_RECORDS["WP04"]
    wp04 = _load(wp04_path)
    for key, decision in wp04["decisions"].items():
        capability_id = ROUTE_IDS[key]
        decisions[capability_id].append(_owner_decision(work_package="WP04", record_path=wp04_path, decision=decision))
        if decision.get("promotion_applied"):
            final_state[capability_id] = decision["resulting_maturity"]

    wp05_path = OWNER_RECORDS["WP05"]
    wp05 = _load(wp05_path)
    wp05_decision = wp05["decision"]
    capability_id = wp05_decision["source_record"]
    decisions[capability_id].append(_owner_decision(work_package="WP05", record_path=wp05_path, decision=wp05_decision))
    if wp05_decision.get("promotion_applied"):
        final_state[capability_id] = wp05_decision["resulting_maturity"]

    wp11b_path = OWNER_RECORDS["WP11B"]
    wp11b = _load(wp11b_path)
    transition = wp11b["registry_reconciliation"]["transition"]
    buckling_id = "COMB-HEX8-linear_buckling"
    decisions[buckling_id].append(
        {
            "work_package": "WP11B",
            "record": wp11b_path.relative_to(ROOT).as_posix(),
            "owner_decision": wp11b["owner_decision"],
            "promotion_applied": True,
            "resulting_maturity": wp11b["final_status"],
            "scope": wp11b["scope"],
            "limitations": wp11b["limitations"],
            "transition": transition,
        }
    )
    final_state[buckling_id] = wp11b["final_status"]

    consolidated: list[dict[str, Any]] = []
    for row in records:
        capability_id = row["capability_id"]
        consolidated.append(
            {
                "capability_id": capability_id,
                "element_family": row["element_family"],
                "analysis": row["analysis"],
                "source_0_2_7_qualification_state": row["qualification_state"],
                "qualification_state": final_state[capability_id],
                "source_evidence_refs": row["evidence_refs"],
                "source_owner_decision": row["owner_decision"],
                "source_limitations": row["limitations"],
                "owner_decisions": decisions[capability_id],
            }
        )
    return consolidated


def _separate_workflows() -> list[dict[str, Any]]:
    wp07 = _load(QUALIFICATION_ROOT / "wp07_owner_gate_final.json")
    wp08b = _load(QUALIFICATION_ROOT / "wp08b_owner_gate_final.json")
    wp09 = _load(QUALIFICATION_ROOT / "wp09_pyramid5_matrix.json")
    wp10 = _load(QUALIFICATION_ROOT / "wp10_hex8_sri_owner_gate_final.json")
    wp11 = _load(QUALIFICATION_ROOT / "wp11_mixed_large_matrix.json")
    wp11b = _load(OWNER_RECORDS["WP11B"])
    return [
        {
            "id": "MIXED-TET4-WEDGE6-HEX8-linear_static",
            "record_kind": "mixed_workflow_qualification",
            "status": wp07["summary"]["mixed_workflow_status"],
            "owner_record": "qualification/0_2_8/wp07_owner_gate_final.json",
            "scope": wp07["decision"]["scope"],
            "limitations": wp07["decision"]["limitations"],
        },
        {
            "id": "MIXED-TET4-WEDGE6-HEX8-modal",
            "record_kind": "mixed_workflow_qualification",
            "status": wp08b["decision"]["mixed_modal_final_status"],
            "owner_record": "qualification/0_2_8/wp08b_owner_gate_final.json",
            "scope": wp08b["decision"]["scope"],
            "limitations": wp08b["decision"]["limitations"],
        },
        {
            "id": "PYRAMID5-feasibility",
            "record_kind": "internal_feasibility_kernel",
            "status": wp09["technical_decision"],
            "owner_record": None,
            "evidence_record": "qualification/0_2_8/wp09_pyramid5_vnv.json",
            "scope": wp09["scope"],
            "limitations": wp09["limitations"],
        },
        {
            "id": "HEX8-SRI-linear_static",
            "record_kind": "separate_experimental_capability",
            "status": wp10["final_status"],
            "owner_record": "qualification/0_2_8/wp10_hex8_sri_owner_gate_final.json",
            "scope": wp10["scope"],
            "limitations": wp10["limitations"],
        },
        {
            "id": "MIXED-TET4-WEDGE6-HEX8-large-linear_static",
            "record_kind": "bounded_performance_evidence",
            "status": wp11["decision"],
            "owner_record": "qualification/0_2_8/wp11_mixed_large_matrix.json",
            "scope": wp11["mandatory_model"],
            "limitations": wp11["limitations"],
        },
        {
            "id": "HEX8-linear_buckling-experimental",
            "record_kind": "experimental_capability",
            "status": wp11b["final_status"],
            "owner_record": "qualification/0_2_8/wp11b_hex8_buckling_owner_gate_final.json",
            "scope": wp11b["scope"],
            "limitations": wp11b["limitations"],
        },
    ]


def build_registry() -> dict[str, Any]:
    source = _load(SOURCE_PATH)
    combinations = _combination_records(source)
    counts = {
        state: sum(row["qualification_state"] == state for row in combinations)
        for state in ("QUALIFIED_BOUNDED", "EXPERIMENTAL", "NOT_QUALIFIED")
    }
    if len(combinations) != 46 or counts != {
        "QUALIFIED_BOUNDED": 32,
        "EXPERIMENTAL": 14,
        "NOT_QUALIFIED": 0,
    }:
        raise RuntimeError(f"Unexpected cumulative 0.2.8 registry state: {counts}")
    return {
        "schema_version": 1,
        "registry_id": "QF-028-CONSOLIDATED-CAPABILITY-REGISTRY",
        "applicable_version": "0.2.8-development",
        "source_registry": SOURCE_PATH.relative_to(ROOT).as_posix(),
        "source_registry_sha256": _sha256(SOURCE_PATH),
        "source_registry_state": {
            "QUALIFIED_BOUNDED": 20,
            "EXPERIMENTAL": 25,
            "NOT_QUALIFIED": 1,
            "TOTAL": 46,
        },
        "combination_registry": {
            "total": len(combinations),
            "state_counts": counts,
            "not_qualified_combination": None,
            "records": combinations,
        },
        "internal_research_kernels": [
            {
                "element_family": "PYRAMID5",
                "status": "FEASIBLE_CONTINUE",
                "public_registered": False,
                "record": "qualification/0_2_8/wp09_pyramid5_matrix.json",
                "reason": "bounded internal feasibility only; public dispatch remains fail-closed",
            }
        ],
        "separate_workflows": _separate_workflows(),
        "owner_records_preserved": [path.relative_to(ROOT).as_posix() for path in OWNER_RECORDS.values()],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate the checked-in consolidated registry")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()
    expected = build_registry()
    if args.check:
        if not args.output.is_file():
            print(f"Missing consolidated registry: {args.output}")
            return 1
        actual = _load(args.output)
        if actual != expected:
            print("Consolidated registry is stale or inconsistent.")
            return 1
        print("Consolidated registry: PASS")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
