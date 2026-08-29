"""Reporting helpers for the diagnostic TL boundary campaign."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np

FAMILIES = ("TET4", "HEX8")
ASPECT_RATIOS = (4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0)


def signature(result: dict[str, Any]) -> tuple[Any, ...]:
    state = result.get("final_state", {})
    return (
        result.get("status"),
        result.get("failure_reason"),
        result.get("diagnostics", {}).get("load_factor"),
        result.get("diagnostics", {}).get("rejected_increments"),
        state.get("displacement_sha256"),
    )


def zone(fixed: dict[str, Any], adaptive: dict[str, Any]) -> str:
    fixed_ok = fixed.get("status") == "SUCCESS"
    adaptive_ok = adaptive.get("status") == "SUCCESS"
    cutbacks = int(adaptive.get("diagnostics", {}).get("rejected_increments", 0))
    if fixed_ok and adaptive_ok and cutbacks == 0:
        return "STABLE_ZONE"
    if fixed_ok or adaptive_ok:
        return "DEGRADED_ZONE"
    return "OUT_OF_RECOMMENDED_SCOPE"


def physical_rows(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, dict[str, Any]]] = {}
    for result in results:
        grouped.setdefault(result["id"], {})[result["variant"]] = result
    rows: list[dict[str, Any]] = []
    for case_id, variants in grouped.items():
        fixed = variants.get("fixed", {})
        adaptive = variants.get("adaptive", {})
        definition = fixed.get("definition", adaptive.get("definition", {}))
        quality = fixed.get("quality", adaptive.get("quality"))
        rows.append(
            {
                "id": case_id,
                "family": definition.get("family"),
                "mesh_level": definition.get("mesh_level"),
                "aspect": definition.get("aspect"),
                "mode": definition.get("mode"),
                "load_scale": definition.get("load_scale"),
                "increments": definition.get("increments"),
                "distortion": definition.get("distortion"),
                "quality_summary": (quality or {}).get("summary", {}),
                "fixed_status": fixed.get("status"),
                "fixed_reason": fixed.get("failure_reason"),
                "fixed_load_factor": fixed.get("diagnostics", {}).get("load_factor"),
                "fixed_iterations": fixed.get("diagnostics", {}).get("newton_iterations"),
                "adaptive_status": adaptive.get("status"),
                "adaptive_reason": adaptive.get("failure_reason"),
                "adaptive_load_factor": adaptive.get("diagnostics", {}).get("load_factor"),
                "adaptive_iterations": adaptive.get("diagnostics", {}).get("newton_iterations"),
                "adaptive_cutbacks": adaptive.get("diagnostics", {}).get("rejected_increments", 0),
                "fixed_state": fixed.get("final_state", {}),
                "adaptive_state": adaptive.get("final_state", {}),
                "zone": zone(fixed, adaptive),
            }
        )
    return rows


def zone_summary(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    output = {"STABLE_ZONE": [], "DEGRADED_ZONE": [], "OUT_OF_RECOMMENDED_SCOPE": []}
    for row in rows:
        output[row["zone"]].append(
            {
                "family": row["family"],
                "mesh_level": row["mesh_level"],
                "aspect": row["aspect"],
                "mode": row["mode"],
                "load_scale": row["load_scale"],
                "increments": row["increments"],
                "distortion": row["distortion"],
            }
        )
    return output


def aspect_outcomes(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    output: dict[str, list[dict[str, Any]]] = {}
    for family in FAMILIES:
        family_rows = [row for row in rows if row["family"] == family]
        output[family] = []
        for aspect in ASPECT_RATIOS:
            selected = [row for row in family_rows if row["aspect"] == aspect]
            if not selected:
                continue
            counts = {
                zone_name: sum(row["zone"] == zone_name for row in selected)
                for zone_name in ("STABLE_ZONE", "DEGRADED_ZONE", "OUT_OF_RECOMMENDED_SCOPE")
            }
            output[family].append({"aspect": aspect, "case_count": len(selected), "zone_counts": counts})
    return output


def conditioning_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_zone: dict[str, list[float]] = {zone_name: [] for zone_name in ("STABLE_ZONE", "DEGRADED_ZONE", "OUT_OF_RECOMMENDED_SCOPE")}
    by_aspect: dict[str, list[float]] = {}
    for row in rows:
        state = row.get("adaptive_state", {})
        condition = state.get("tangent_condition_number")
        if condition is not None and np.isfinite(condition) and condition > 0.0:
            by_zone[row["zone"]].append(float(condition))
            by_aspect.setdefault(f"{row['family']}:{row['aspect']:g}", []).append(float(condition))
    summary = {
        zone_name: {
            "count": len(values),
            "min": min(values) if values else None,
            "median": float(np.median(values)) if values else None,
            "max": max(values) if values else None,
        }
        for zone_name, values in by_zone.items()
    }
    return {
        "description": "Descriptive association only; no acceptance threshold or causal claim.",
        "condition_number_by_zone": summary,
        "condition_number_by_family_aspect": {
            key: {"count": len(values), "median": float(np.median(values)), "max": max(values)}
            for key, values in by_aspect.items()
        },
    }


def aspect_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[float, set[str]] = {}
    for row in rows:
        grouped.setdefault(float(row["aspect"]), set()).add(row["zone"])
    return {
        str(aspect): {
            "observed_zones": sorted(zones),
            "same_nominal_aspect_multiple_outcomes": len(zones) > 1,
        }
        for aspect, zones in sorted(grouped.items())
    }


def cutback_effect(rows: list[dict[str, Any]]) -> dict[str, Any]:
    fixed_success = sum(row["fixed_status"] == "SUCCESS" for row in rows)
    adaptive_success = sum(row["adaptive_status"] == "SUCCESS" for row in rows)
    recovered = sum(row["fixed_status"] != "SUCCESS" and row["adaptive_status"] == "SUCCESS" for row in rows)
    remained_failed = sum(row["fixed_status"] != "SUCCESS" and row["adaptive_status"] != "SUCCESS" for row in rows)
    return {
        "case_count": len(rows),
        "fixed_successes": fixed_success,
        "adaptive_successes": adaptive_success,
        "recovered_by_cutback": recovered,
        "failed_in_both_modes": remained_failed,
        "adaptive_cutback_counts": {
            "zero": sum(int(row["adaptive_cutbacks"]) == 0 for row in rows),
            "positive": sum(int(row["adaptive_cutbacks"]) > 0 for row in rows),
        },
        "interpretation": "Cutback changes resolution behavior in the tested cases; it does not redefine mesh scope or qualify TL.",
    }


def reproducibility(
    definitions: list[dict[str, Any]],
    run_variant: Callable[[dict[str, Any], bool], dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for definition in definitions:
        runs = {
            variant: [run_variant(definition, variant == "adaptive") for _ in range(2)]
            for variant in ("fixed", "adaptive")
        }
        rows.append(
            {
                "id": definition["id"],
                "fixed_signatures": [signature(item) for item in runs["fixed"]],
                "adaptive_signatures": [signature(item) for item in runs["adaptive"]],
                "fixed_reproducible": signature(runs["fixed"][0]) == signature(runs["fixed"][1]),
                "adaptive_reproducible": signature(runs["adaptive"][0]) == signature(runs["adaptive"][1]),
            }
        )
    return rows


def jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return [jsonable(item) for item in value.tolist()]
    if isinstance(value, (np.integer, np.floating, np.bool_)):
        return value.item()
    if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
        return None
    return value


def markdown(report: dict[str, Any]) -> str:
    rows = report["physical_cases"]
    lines = [
        "# TL Mesh / Conditioning Boundary Study",
        "",
        "Status: `DIAGNOSTIC_ONLY`; no solver, formulation, tangent, Newton criterion or tolerance was changed.",
        "",
        f"- Source SHA: `{report['source_sha']}`",
        f"- Worktree dirty at capture: `{report['dirty']}`",
        f"- Physical cases: `{len(rows)}`; fixed/adaptive solver runs: `{len(report['results'])}`",
        f"- Generated: `{report['timestamp_utc']}`",
        "",
        "## Observed zones",
        "",
        "The zones below describe observed behavior in the tested domain only. They are not qualification thresholds or universal mesh rules.",
        "",
        "| Zone | Cases |",
        "| --- | ---: |",
    ]
    for zone_name, values in report["zone_summary"].items():
        lines.append(f"| `{zone_name}` | {len(values)} |")
    lines.extend(
        [
            "",
            "## Fixed versus adaptive",
            "",
            "| Family | Fixed success | Adaptive success | Recovered by cutback | Failed in both |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for family in FAMILIES:
        family_rows = [row for row in rows if row["family"] == family]
        lines.append(
            f"| {family} | {sum(row['fixed_status'] == 'SUCCESS' for row in family_rows)} "
            f"| {sum(row['adaptive_status'] == 'SUCCESS' for row in family_rows)} "
            f"| {sum(row['fixed_status'] != 'SUCCESS' and row['adaptive_status'] == 'SUCCESS' for row in family_rows)} "
            f"| {sum(row['fixed_status'] != 'SUCCESS' and row['adaptive_status'] != 'SUCCESS' for row in family_rows)} |"
        )
    lines.extend(
        [
            "",
            "## Aspect observations",
            "",
            "| Family | Nominal aspect | Cases | Stable | Degraded | Out of recommended scope |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for family in FAMILIES:
        for item in report["aspect_outcomes"][family]:
            counts = item["zone_counts"]
            lines.append(
                f"| {family} | {item['aspect']:g} | {item['case_count']} | {counts['STABLE_ZONE']} "
                f"| {counts['DEGRADED_ZONE']} | {counts['OUT_OF_RECOMMENDED_SCOPE']} |"
            )
    lines.extend(
        [
            "",
            "## Boundary interpretation",
            "",
            "- Nominal aspect ratio is not sufficient by itself; the report retains actual edge/Jacobian/element-quality metrics and shows cases sharing an aspect with different outcomes.",
            "- Conditioning is reported descriptively alongside Newton behavior; no causal threshold is asserted.",
            "- Adaptive cutback can recover load-step-sensitive cases, while cases that exhaust the minimum increment remain explicit failures.",
            "- CASE2 and the historical TL failures remain in the failure zoo; this study does not convert them into qualification evidence.",
            "",
            "## Proposed Owner-review policies",
            "",
            "- `CANDIDATE_MESH_POLICY = PROPOSED_OWNER_REVIEW`: use the observed family/mode/load/distortion zones only as a bounded usage discussion.",
            "- `CANDIDATE_CONDITIONING_POLICY = PROPOSED_OWNER_REVIEW`: require reported conditioning diagnostics and fail-closed behavior; do not encode a universal numeric cutoff from this campaign.",
        ]
    )
    return "\n".join(lines) + "\n"
