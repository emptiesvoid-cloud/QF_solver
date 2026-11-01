"""Produce a scientific M1-M5 report from historical AQ and native run records."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "qualification/0_2_12/wp_c02_ar_mesh_plan.json"
BASELINE_PATH = ROOT / "qualification/0_2_12/wp_c02_ar_native_historical_baseline.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _pass(actual: Any, criterion: str, threshold: Any) -> dict[str, Any]:
    if criterion != "bool_lt" and not _finite(actual):
        return {"actual": actual, "operator": criterion, "threshold": threshold, "passed": False,
                "evaluated": False, "status": "NOT_EVALUATED"}
    if criterion == "le":
        passed = _finite(actual) and float(actual) <= float(threshold)
    elif criterion == "ge":
        passed = _finite(actual) and float(actual) >= float(threshold)
    elif criterion == "lt":
        passed = _finite(actual) and float(actual) < float(threshold)
    elif criterion == "bool_lt":
        passed = bool(actual) is True
    else:
        raise ValueError(f"Unknown criterion {criterion!r}.")
    return {"actual": actual, "operator": criterion, "threshold": threshold, "passed": bool(passed),
            "evaluated": True, "status": "PASS" if passed else "FAIL"}


def _level_checks(level: str, diagnostic: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    gates = plan["frozen_aj_acceptance_gates"]
    d = diagnostic["diagnostics"]
    checks = {
        "partial_contact_active_count": {
            "actual": d["active_count"],
            "criterion": "0 < active_count < contact_rows",
            "passed": 0 < d["active_count"] < d["mesh"]["contact_rows"],
            "evaluated": True,
            "status": "PASS" if 0 < d["active_count"] < d["mesh"]["contact_rows"] else "FAIL",
        },
        "open_contact_count": {"actual": d["open_count"], "criterion": "> 0", "passed": d["open_count"] > 0,
                               "evaluated": True, "status": "PASS" if d["open_count"] > 0 else "FAIL"},
        "maximum_penetration_m": _pass(d["maximum_penetration_m"], "le", gates["production_maximum_penetration_m"]),
        "gap_reconstruction_error_m": _pass(d["production_gap_reconstruction_error_m"], "le", gates["production_gap_reconstruction_error_m"]),
        "production_complementarity_nm": _pass(d["production_complementarity_inf_nm"], "le", gates["complementarity_tolerance_nm"]),
        "strict_active_gap_m": _pass(d["strict_active_max_gap_m"], "le", gates["production_strict_active_max_gap_m"]),
        "strict_open_multiplier_n": _pass(d["strict_open_max_multiplier_n"], "le", gates["production_strict_open_max_multiplier_n"]),
        "production_stationarity_n": _pass(d["production_stationarity_inf_n"], "le", gates["production_stationarity_inf_residual_n"]),
        "independent_qp_primal_gap_m": _pass(d["independent_qp_primal_gap_min_m"], "ge", gates["independent_qp_primal_min_gap_m"]),
        "independent_qp_dual_multiplier_n": _pass(d["independent_qp_dual_multiplier_min_n"], "ge", gates["independent_qp_dual_min_multiplier_n"]),
        "independent_qp_complementarity_nm": _pass(d["independent_qp_complementarity_inf_nm"], "le", gates["independent_qp_complementarity_inf_nm"]),
        "independent_qp_stationarity_n": _pass(d["independent_qp_stationarity_inf_n"], "le", gates["independent_qp_stationarity_inf_residual_n"]),
        "production_vs_qp_displacement_m": _pass(d["independent_qp_displacement_max_error_m"], "le", gates["production_vs_independent_qp_displacement_max_error_m"]),
        "production_vs_qp_multiplier_n": _pass(d["independent_qp_multiplier_max_error_n"], "le", gates["production_vs_independent_qp_multiplier_max_error_n"]),
        "production_force_balance": _pass(d["production_force_balance_relative"], "le", gates["production_normalized_force_balance"]),
        "production_moment_balance": _pass(d["production_moment_balance_relative"], "le", gates["production_normalized_moment_balance"]),
        "independent_qp_force_balance": _pass(d["independent_qp_force_balance_relative"], "le", gates["independent_qp_normalized_force_balance"]),
        "independent_qp_moment_balance": _pass(d["independent_qp_moment_balance_relative"], "le", gates["independent_qp_normalized_moment_balance"]),
        "production_contact_work_identity_j": _pass(d["production_contact_work_identity_error_j"], "le", gates["production_contact_work_identity_error_j"]),
        "independent_qp_contact_work_identity_j": _pass(d["independent_qp_contact_work_identity_error_j"], "le", gates["independent_qp_contact_work_identity_error_j"]),
        "matrix_vs_quadrature_energy_j": _pass(d["fe_energy_matrix_vs_quadrature_error_j"], "le", gates["fe_matrix_energy_vs_quadrature_error_j"]),
        "finite_contact_resultant_discretization_error": {"actual": d["contact_resultant_relative_error"], "criterion": "finite; no AR discretization threshold", "passed": _finite(d["contact_resultant_relative_error"])},
        "finite_contact_moment_discretization_error": {"actual": d["contact_moment_relative_error"], "criterion": "finite; no AR discretization threshold", "passed": _finite(d["contact_moment_relative_error"])},
        "finite_front_diagnostic": {"actual": d["front_error_max_abs_m"], "criterion": "finite; no AJ threshold", "passed": _finite(d["front_error_max_abs_m"])},
    }
    front_policy = plan["proposed_ar_front_gate_requires_owner_approval"]
    if level in front_policy["eligible_levels"]:
        all_rows = (
            d["front_bracketed_row_count"] == d["front_row_count"]
            and d["front_bracket_ordered_row_count"] == d["front_row_count"]
        )
        all_mislabels_local = all(
            point["distance_to_front_over_hx"] <= 1.0
            for point in (*d["false_positives"], *d["false_negatives"])
        )
        checks["prospective_front_resolution"] = _pass(d["front_error_max_over_hx"], "le", 1.0)
        checks["prospective_front_row_coverage"] = {
            "actual": (
                f"{d['front_bracketed_row_count']}/{d['front_row_count']} bracketed; "
                f"{d['front_bracket_ordered_row_count']}/{d['front_row_count']} ordered"
            ),
            "criterion": "every y row has an ordered active/open front bracket",
            "passed": all_rows,
            "evaluated": True,
            "status": "PASS" if all_rows else "FAIL",
        }
        checks["prospective_front_misclassification_locality"] = {
            "actual": {
                "false_positive_count": d["false_positive_count"],
                "false_negative_count": d["false_negative_count"],
                "max_distance_over_hx": max(
                    (p["distance_to_front_over_hx"] for p in (*d["false_positives"], *d["false_negatives"])),
                    default=0.0,
                ),
            },
            "criterion": "all false positive/negative nodes within hx",
            "passed": all_mislabels_local,
            "evaluated": True,
            "status": "PASS" if all_mislabels_local else "FAIL",
        }
        checks["prospective_front_no_multiple_front"] = {
            "actual": d["rows_with_more_than_one_active_open_transition"],
            "criterion": "no row with multiple active/open transitions",
            "passed": not d["rows_with_more_than_one_active_open_transition"],
            "evaluated": True,
            "status": "PASS" if not d["rows_with_more_than_one_active_open_transition"] else "FAIL",
        }
    return checks


def _status(checks: dict[str, Any]) -> str:
    statuses = [check.get("status", "PASS" if check.get("passed") else "FAIL") for check in checks.values()]
    if any(status == "FAIL" for status in statuses):
        return "FAIL"
    if any(status == "NOT_EVALUATED" for status in statuses):
        return "NOT_ACQUIRED"
    return "PASS"


def _table_row(level: str, record: dict[str, Any] | None, baseline: dict[str, Any] | None) -> list[str]:
    if baseline is not None:
        return [
            level,
            f"{baseline['nodes']} / {baseline['tet4']}",
            f"{baseline['body_mechanical_dofs']} / {baseline['body_free_dofs']}",
            str(baseline["contact_rows"]),
            f"{baseline['relative_l2_displacement_error']:.7g}",
            f"{baseline['pressure_relative_l2_error']:.7g}",
            f"{baseline['strain_energy_error_norm_j_sqrt']:.7g}",
            f"{baseline['fe_strain_energy_j']:.9g}",
            f"{baseline['contact_resultant_n']:.9g}",
            f"{baseline['contact_resultant_relative_error']:.7g}",
            f"{baseline['contact_moment_error_nm']:.7g}",
            "NOT_RECORDED",
            f"{baseline['front_error_max_abs_m']:.7g} / {baseline['front_error_max_over_hx']:.7g}",
            "AQ HISTORICAL",
        ]
    if record is None:
        return [level, "—", "—", "—", "—", "—", "—", "—", "—", "—", "—", "—", "—", "NOT_ACQUIRED"]
    if record.get("scenario_state") != "COMPLETED_DIAGNOSTICS":
        return [
            level, "—", "—", "—", "—", "—", "—", "—", "—", "—", "—", "—", "—",
            _scenario_verdict(record),
        ]
    d = record["diagnostics"]
    front_error = "NOT_EVALUATED" if not _finite(d["front_error_max_abs_m"]) else f"{d['front_error_max_abs_m']:.7g}"
    front_error_hx = "NOT_EVALUATED" if not _finite(d["front_error_max_over_hx"]) else f"{d['front_error_max_over_hx']:.7g}"
    return [
        level,
        f"{d['mesh']['nodes']} / {d['mesh']['tet4']}",
        f"{d['mesh']['body_mechanical_dofs']} / {d['mesh']['body_free_dofs']}",
        str(d["mesh"]["contact_rows"]),
        f"{d['relative_l2_displacement_error']:.7g}",
        f"{d['pressure_relative_l2_error']:.7g}",
        f"{d['strain_energy_error_norm_j_sqrt']:.7g}",
        f"{d['strain_energy_j']:.9g}",
        f"{d['contact_resultant_n']:.9g}",
        f"{d['contact_resultant_relative_error']:.7g}",
        f"{d['contact_moment_error_nm']:.7g}",
        f"{d['support_resultant_error_n']:.7g} / {d['support_moment_error_nm']:.7g}",
        f"{front_error} / {front_error_hx}",
        record["scenario_state"],
    ]


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def _scenario_verdict(record: dict[str, Any] | None, checks: dict[str, Any] | None = None) -> str:
    if record is None:
        return "NOT_EVALUATED"
    # The one-shot ledger is the authoritative pytest outcome.  A later
    # missing derived metric must not erase an already recorded criterion fail.
    if record.get("_ledger_state") == "SCIENTIFIC_CRITERION_FAILURE":
        return "FAIL"
    if record.get("_ledger_state") in {
        "RSS_LIMIT_EXCEEDED", "WALL_TIMEOUT_EXCEEDED",
        "INFRASTRUCTURE_FAILURE_NO_DIAGNOSTIC", "INFRASTRUCTURE_FAILURE_INCOMPLETE_DIAGNOSTIC",
    }:
        return "NOT_EVALUATED"
    if record.get("_ledger_error") is not None:
        if checks is not None and _status(checks) == "FAIL":
            return "FAIL"
        return "ERROR_COLLECTION"
    if record.get("scenario_state") == "COLLECTION_ERROR":
        return "ERROR_COLLECTION"
    if record.get("scenario_state") == "COMPLETED_DIAGNOSTICS":
        if checks is None:
            return "NOT_EVALUATED"
        return _status(checks)
    failure = record.get("failure")
    if isinstance(failure, dict) and failure.get("type") in {"NumericalConvergenceError", "MeshValidationError"}:
        return "FAIL"
    if isinstance(failure, dict) or record.get("scenario_state") in {
        "SOLVER_OR_DIAGNOSTIC_EXCEPTION", "REPORT_GENERATION_FAILURE"
    }:
        return "ERROR_COLLECTION"
    return "NOT_EVALUATED"


def _load_scenario(
    path: Path,
    level: str,
    plan: dict[str, Any],
    ledger_entry: dict[str, Any] | None = None,
    *,
    ledger_error: str | None = None,
) -> dict[str, Any] | None:
    if not path.is_file():
        if ledger_entry is None and ledger_error is None:
            return None
        result: dict[str, Any] = {"level": level, "scenario_state": "DIAGNOSTICS_MISSING"}
        if ledger_entry is not None:
            result["_ledger_state"] = ledger_entry.get("state")
            result["failure"] = {"type": "MissingDiagnostics", "message": "pytest ledger has no diagnostic file"}
        if ledger_error is not None:
            result["_ledger_error"] = ledger_error
        return result
    try:
        record = _load(path)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        result = {"level": level, "scenario_state": "COLLECTION_ERROR", "failure": {
            "type": type(exc).__name__, "message": str(exc)
        }}
        if ledger_entry is not None:
            result["_ledger_state"] = ledger_entry.get("state")
        if ledger_error is not None:
            result["_ledger_error"] = ledger_error
        return result
    if not isinstance(record, dict):
        result = {"level": level, "scenario_state": "COLLECTION_ERROR", "failure": {
            "type": "InvalidRecord", "message": "Scenario diagnostics JSON must be an object."
        }}
        if ledger_entry is not None:
            result["_ledger_state"] = ledger_entry.get("state")
        if ledger_error is not None:
            result["_ledger_error"] = ledger_error
        return result
    record["level"] = level
    if ledger_entry is not None:
        record["_ledger_state"] = ledger_entry.get("state")
    if ledger_error is not None:
        record["_ledger_error"] = ledger_error
    if record.get("scenario_state") == "COMPLETED_DIAGNOSTICS":
        try:
            _validate_complete_record(record)
            _level_checks(level, record, plan)
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            return {**record, "scenario_state": "COLLECTION_ERROR", "failure": {
                "type": type(exc).__name__, "message": str(exc)
            }}
    return record


def _load_run_ledger(archive: Path) -> tuple[dict[str, dict[str, Any]], str | None]:
    path = archive / "run_ledger.json"
    if not path.is_file():
        has_campaign_identity = (archive / "archive_integrity_manifest.json").is_file() or any(
            candidate.is_file()
            for candidate in archive.glob("*execution_manifest*.json")
        )
        if has_campaign_identity:
            return {}, "MissingLedger: native campaign archive has no run_ledger.json"
        return {}, None
    try:
        ledger = _load(path)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {}, f"{type(exc).__name__}: {exc}"
    scenarios = ledger.get("scenarios") if isinstance(ledger, dict) else None
    if not isinstance(scenarios, list):
        return {}, "InvalidLedger: scenarios must be a list"
    entries: dict[str, dict[str, Any]] = {}
    for entry in scenarios:
        if not isinstance(entry, dict) or entry.get("level") not in {"M4", "M5"}:
            return {}, "InvalidLedger: each scenario entry must identify M4 or M5"
        if entry["level"] in entries or not isinstance(entry.get("state"), str):
            return {}, f"InvalidLedger: duplicate or missing state for {entry['level']}"
        entries[entry["level"]] = entry
    return entries, None


def _validate_complete_record(record: dict[str, Any]) -> None:
    diagnostics = record.get("diagnostics")
    fields = record.get("field_values")
    if not isinstance(diagnostics, dict) or not isinstance(fields, dict):
        raise ValueError("completed record lacks diagnostics or field_values objects")
    required_diagnostics = {
        "relative_l2_displacement_error", "pressure_relative_l2_error",
        "active_count", "open_count", "maximum_penetration_m", "production_gap_reconstruction_error_m",
        "production_complementarity_inf_nm", "strict_active_max_gap_m", "strict_open_max_multiplier_n",
        "production_stationarity_inf_n", "independent_qp_primal_gap_min_m", "independent_qp_dual_multiplier_min_n",
        "independent_qp_complementarity_inf_nm", "independent_qp_stationarity_inf_n",
        "independent_qp_displacement_max_error_m", "independent_qp_multiplier_max_error_n",
        "production_force_balance_relative", "production_moment_balance_relative",
        "independent_qp_force_balance_relative", "independent_qp_moment_balance_relative",
        "production_contact_work_identity_error_j", "independent_qp_contact_work_identity_error_j",
        "fe_energy_matrix_vs_quadrature_error_j", "contact_resultant_relative_error",
        "contact_moment_relative_error", "front_error_max_abs_m", "front_error_max_over_hx",
        "front_bracketed_row_count", "front_bracket_ordered_row_count", "front_row_count",
        "front_trace_by_y",
        "false_positives", "false_negatives", "false_positive_count", "false_negative_count",
        "rows_with_more_than_one_active_open_transition", "strain_energy_j", "fe_integrated_strain_energy_j",
        "exact_strain_energy_j", "absolute_strain_energy_difference_j", "strain_energy_error_norm_j_sqrt",
        "support_resultant_error_n", "support_moment_error_nm", "contact_resultant_n", "contact_moment_error_nm",
        "mesh",
    }
    missing = sorted(required_diagnostics - diagnostics.keys())
    if missing:
        raise ValueError(f"completed diagnostics are missing required fields: {missing}")
    numeric_fields = required_diagnostics - {
        "false_positives", "false_negatives", "rows_with_more_than_one_active_open_transition",
        "front_trace_by_y", "mesh",
    }
    nullable_when_population_empty = {
        "strict_active_max_gap_m",
        "front_error_max_abs_m",
        "front_error_max_over_hx",
    }
    for name in numeric_fields:
        value = diagnostics[name]
        if value is None and name in nullable_when_population_empty:
            continue
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
            raise ValueError(f"completed diagnostic {name!r} must be a finite number")
    if diagnostics["strict_active_max_gap_m"] is None and diagnostics["active_count"] != 0:
        raise ValueError("strict_active_max_gap_m may be null only when no strict-active rows were measured")
    if any(diagnostics[name] is None for name in ("front_error_max_abs_m", "front_error_max_over_hx")) and diagnostics["front_bracketed_row_count"] != 0:
        raise ValueError("front error metrics may be null only when no row front was bracketed")
    required_mesh = {"nodes", "tet4", "body_mechanical_dofs", "body_free_dofs", "contact_rows"}
    if not isinstance(diagnostics["mesh"], dict) or not required_mesh.issubset(diagnostics["mesh"]):
        raise ValueError("completed diagnostics have incomplete mesh dimensions")
    for name in ("nodes", "tet4", "body_mechanical_dofs", "body_free_dofs", "contact_rows"):
        value = diagnostics["mesh"][name]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"completed mesh dimension {name!r} must be a non-negative integer")
    for name in (
        "active_count", "open_count", "front_bracketed_row_count", "front_bracket_ordered_row_count",
        "front_row_count", "false_positive_count", "false_negative_count",
    ):
        value = diagnostics[name]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"completed diagnostic count {name!r} must be a non-negative integer")
    traces = diagnostics["front_trace_by_y"]
    if not isinstance(traces, list) or len(traces) != diagnostics["front_row_count"]:
        raise ValueError("front_trace_by_y must contain exactly front_row_count rows")
    seen_contact_nodes: set[int] = set()
    bracketed_rows = 0
    ordered_rows = 0
    for trace in traces:
        if not isinstance(trace, dict) or not isinstance(trace.get("contact_states_by_x"), list):
            raise ValueError("each front trace must contain a contact_states_by_x list")
        if not isinstance(trace.get("front_bracketed_by_observed_states"), bool):
            raise ValueError("each front trace must report its observed active/open bracket state")
        if not isinstance(trace.get("ordered_active_open_bracket"), bool):
            raise ValueError("each front trace must report its ordered active/open bracket state")
        bracketed_rows += int(trace["front_bracketed_by_observed_states"])
        ordered_rows += int(trace["ordered_active_open_bracket"])
        if not trace["contact_states_by_x"]:
            raise ValueError("front trace rows cannot omit their contact classifications")
        for state in trace["contact_states_by_x"]:
            if not isinstance(state, dict) or state.get("classification") not in {
                "ACTIVE", "OPEN", "BI-ACTIVE", "ACTIVE_AND_OPEN", "UNCLASSIFIED"
            }:
                raise ValueError("front trace contact states must carry a recognized classification")
            node = state.get("node")
            if (
                isinstance(node, bool) or not isinstance(node, int)
                or not 0 <= node < diagnostics["mesh"]["nodes"] or node in seen_contact_nodes
            ):
                raise ValueError("front trace contact node IDs must be unique integers")
            seen_contact_nodes.add(node)
    if len(seen_contact_nodes) != diagnostics["mesh"]["contact_rows"]:
        raise ValueError("front trace rows do not cover every contact row exactly once")
    if bracketed_rows != diagnostics["front_bracketed_row_count"]:
        raise ValueError("front_bracketed_row_count does not match front trace rows")
    if ordered_rows != diagnostics["front_bracket_ordered_row_count"]:
        raise ValueError("front_bracket_ordered_row_count does not match front trace rows")
    for name in ("false_positives", "false_negatives", "rows_with_more_than_one_active_open_transition"):
        if not isinstance(diagnostics[name], list):
            raise ValueError(f"completed diagnostic {name!r} must be a list")
    for point in (*diagnostics["false_positives"], *diagnostics["false_negatives"]):
        if not isinstance(point, dict) or not _finite(point.get("distance_to_front_over_hx")):
            raise ValueError("completed front misclassification records must include finite normalized distances")
    if diagnostics["false_positive_count"] != len(diagnostics["false_positives"]):
        raise ValueError("false_positive_count does not match its front point records")
    if diagnostics["false_negative_count"] != len(diagnostics["false_negatives"]):
        raise ValueError("false_negative_count does not match its front point records")
    required_fields = {
        "body_displacements_m_node_major_xyz", "contact_node_ids", "contact_gaps_m",
        "contact_multipliers_n", "production_contact_active_set_flags", "contact_pressures_pa",
        "contact_area_weights_m2", "support_reactions_n_node_major_xyz",
        "external_nodal_loads_n_node_major_xyz",
    }
    missing_fields = sorted(required_fields - fields.keys())
    if missing_fields:
        raise ValueError(f"completed field_values are missing required fields: {missing_fields}")
    if any(not isinstance(fields[name], list) for name in required_fields):
        raise ValueError("completed field_values arrays must be JSON lists")
    numeric_array_fields = required_fields - {"production_contact_active_set_flags"}
    for name in numeric_array_fields:
        if not _finite_json_array(fields[name]):
            raise ValueError(f"completed field_values[{name!r}] contains non-numeric or non-finite data")
    for flag in fields["production_contact_active_set_flags"]:
        if not isinstance(flag, bool):
            raise ValueError("production contact active-set flags must be booleans")
    body_nodes = diagnostics["mesh"]["nodes"]
    contact_rows = diagnostics["mesh"]["contact_rows"]
    node_ids = fields["contact_node_ids"]
    if any(isinstance(node, bool) or not isinstance(node, int) or not 0 <= node < body_nodes for node in node_ids):
        raise ValueError("contact_node_ids must be unique body mesh node indices")
    if len(set(node_ids)) != contact_rows:
        raise ValueError("contact_node_ids must identify each contact row exactly once")
    if set(node_ids) != seen_contact_nodes:
        raise ValueError("front trace contact node IDs do not match contact_node_ids")
    for name in (
        "body_displacements_m_node_major_xyz", "support_reactions_n_node_major_xyz",
        "external_nodal_loads_n_node_major_xyz",
    ):
        values = fields[name]
        if len(values) != body_nodes or any(not isinstance(row, list) or len(row) != 3 for row in values):
            raise ValueError(f"completed field_values[{name!r}] must have shape ({body_nodes}, 3)")
    for name in (
        "contact_node_ids", "contact_gaps_m", "contact_multipliers_n", "production_contact_active_set_flags",
        "contact_pressures_pa", "contact_area_weights_m2",
    ):
        if len(fields[name]) != contact_rows:
            raise ValueError(f"completed field_values[{name!r}] must contain {contact_rows} contact rows")


def _finite_json_array(value: Any) -> bool:
    if isinstance(value, list):
        return all(_finite_json_array(item) for item in value)
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _failure_details(record: dict[str, Any]) -> tuple[str, str]:
    failure = record.get("failure")
    if not isinstance(failure, dict):
        return "InvalidFailureRecord", f"failure field must be an object; got {type(failure).__name__}"
    return str(failure.get("type", "unknown")), str(failure.get("message", "no detail"))


def render_report(archive: Path) -> str:
    plan = _load(PLAN_PATH)
    baseline_doc = _load(BASELINE_PATH)
    baselines = {row["level"]: row for row in baseline_doc["levels"]}
    ledger_entries, ledger_error = _load_run_ledger(archive)
    records: dict[str, dict[str, Any] | None] = {
        level: _load_scenario(
            archive / f"{level.lower()}_diagnostics.json", level, plan,
            ledger_entries.get(level), ledger_error=ledger_error,
        )
        for level in ("M4", "M5")
    }

    per_level: dict[str, dict[str, Any] | None] = {}
    all_level_gates = True
    for level in ("M4", "M5"):
        record = records[level]
        if record is None or record.get("scenario_state") != "COMPLETED_DIAGNOSTICS":
            per_level[level] = None
            all_level_gates = False
        else:
            per_level[level] = _level_checks(level, record, plan)
            all_level_gates = all_level_gates and _status(per_level[level]) == "PASS"

    m1 = baselines["M1"]
    m3 = baselines["M3"]
    historical_m1_m3 = {
        "relative_displacement_error_ratio_M3_over_M1": _pass(
            m3["relative_l2_displacement_error"] / m1["relative_l2_displacement_error"],
            "lt",
            plan["frozen_aj_acceptance_gates"]["relative_displacement_error_ratio_M3_over_M1_strictly_less_than"],
        ),
        "relative_pressure_error_ratio_M3_over_M1": _pass(
            m3["pressure_relative_l2_error"] / m1["pressure_relative_l2_error"],
            "lt",
            plan["frozen_aj_acceptance_gates"]["relative_pressure_error_ratio_M3_over_M1_strictly_less_than"],
        ),
        "energy_error_norm_M3_less_than_M1": _pass(
            m3["strain_energy_error_norm_j_sqrt"] < m1["strain_energy_error_norm_j_sqrt"],
            "bool_lt",
            True,
        ),
    }

    endpoint: dict[str, Any] | None = None
    endpoint_status = "NOT_ACQUIRED"
    m5 = records["M5"]
    if m5 is not None and m5.get("scenario_state") == "COMPLETED_DIAGNOSTICS":
        d5 = m5["diagnostics"]
        endpoint = {
            "relative_displacement_error_ratio_M5_over_M1": _pass(
                d5["relative_l2_displacement_error"] / m1["relative_l2_displacement_error"],
                "lt",
                plan["proposed_ar_endpoint_gates_require_owner_approval"]["relative_displacement_error_ratio_M5_over_M1_strictly_less_than"],
            ),
            "relative_pressure_error_ratio_M5_over_M1": _pass(
                d5["pressure_relative_l2_error"] / m1["pressure_relative_l2_error"],
                "lt",
                plan["proposed_ar_endpoint_gates_require_owner_approval"]["relative_pressure_error_ratio_M5_over_M1_strictly_less_than"],
            ),
            "energy_error_norm_M5_less_than_M1": _pass(
                d5["strain_energy_error_norm_j_sqrt"] < m1["strain_energy_error_norm_j_sqrt"],
                "bool_lt",
                True,
            ),
        }
        endpoint_status = _status(endpoint)

    # The AQ summary contains aggregate M2/M3 front values, but not row traces,
    # row-bracket coverage, or multiple-front diagnostics.  AR explicitly
    # requires those for every row, so this sub-gate cannot be silently waived.
    _ = {
        level: {
            "reported_error_over_hx": baselines[level]["front_error_max_over_hx"],
            "reported_false_positives": baselines[level]["false_positive_count"],
            "reported_false_negatives": baselines[level]["false_negative_count"],
            "row_bracket_coverage": "NOT_RECORDED_IN_AQ_SUMMARY",
            "multiple_front_rows": "NOT_RECORDED_IN_AQ_SUMMARY",
        }
        for level in ("M2", "M3")
    }
    native_front = {
        level: (
            _level_checks(level, record, plan)
            if record is not None and record.get("scenario_state") == "COMPLETED_DIAGNOSTICS"
            else None
        )
        for level, record in records.items()
    }
    front_rows = []
    for level in ("M2", "M3"):
        base = baselines[level]
        front_rows.append(
            [
                level,
                f"{base['front_error_max_abs_m']:.7g}",
                f"{base['front_error_max_over_hx']:.7g}",
                f"{base['false_positive_count']} / {base['false_negative_count']}",
                f"{base['false_positive_max_distance_over_hx']:.7g} / {base['false_negative_max_distance_over_hx']:.7g}",
                "NOT_RECORDED",
                "NOT_RECORDED",
                "NOT_RECORDED",
            ]
        )
    for level in ("M4", "M5"):
        record = records[level]
        if record is None or record.get("scenario_state") != "COMPLETED_DIAGNOSTICS":
            front_rows.append([level, "—", "—", "—", "—", "NOT_ACQUIRED", "NOT_ACQUIRED", "NOT_ACQUIRED"])
            continue
        d = record["diagnostics"]
        front_error = "NOT_EVALUATED" if not _finite(d["front_error_max_abs_m"]) else f"{d['front_error_max_abs_m']:.7g}"
        front_error_hx = "NOT_EVALUATED" if not _finite(d["front_error_max_over_hx"]) else f"{d['front_error_max_over_hx']:.7g}"
        max_mislabel_distance = max(
            (p["distance_to_front_over_hx"] for p in (*d["false_positives"], *d["false_negatives"])),
            default=0.0,
        )
        front_rows.append(
            [
                level,
                front_error,
                front_error_hx,
                f"{d['false_positive_count']} / {d['false_negative_count']}",
                f"{max_mislabel_distance:.7g}",
                f"{d['front_bracketed_row_count']}/{d['front_row_count']}",
                str(len(d["rows_with_more_than_one_active_open_transition"])),
                f"{d['front_bracket_ordered_row_count']}/{d['front_row_count']}",
            ]
        )
    front_table = _md_table(
        ["Niveau", "Erreur front max m", "Erreur / hx", "FP / FN", "Distance max FP/FN / hx", "Rangées bracketées", "Rangées multi-front", "Rangées bracket ordonné"],
        front_rows,
    )
    front_status = "NOT_ACQUIRED"
    native_front_fail = any(
        checks is not None and any(
            name.startswith("prospective_front_") and check.get("status") == "FAIL"
            for name, check in checks.items()
        )
        for checks in native_front.values()
    )
    if native_front_fail:
        front_status = "FAIL"
    elif all(native_front[level] is not None for level in ("M4", "M5")):
        # The missing historical M2/M3 per-row records still prevent the
        # complete M2-M5 coverage criterion from being demonstrated.
        front_status = "NOT_ACQUIRED"

    if any(_scenario_verdict(records[level]) == "FAIL" for level in ("M4", "M5")):
        scientific_verdict = "FAIL"
    elif any(records[level] is not None and records[level].get("scenario_state") == "COMPLETED_DIAGNOSTICS" for level in ("M4", "M5")):
        if any(
            checks is not None and _status(checks) == "FAIL"
            for checks in per_level.values()
        ) or endpoint_status == "FAIL" or front_status == "FAIL":
            scientific_verdict = "FAIL"
        elif all(records[level] is not None and records[level].get("scenario_state") == "COMPLETED_DIAGNOSTICS" for level in ("M4", "M5")) and all_level_gates and endpoint_status == "PASS" and front_status == "PASS":
            scientific_verdict = "PASS"
        else:
            scientific_verdict = "NOT_ACQUIRED"
    else:
        scientific_verdict = "NOT_ACQUIRED"
    if ledger_error is not None and scientific_verdict == "PASS":
        scientific_verdict = "NOT_ACQUIRED"

    report_rows = [_table_row(level, None, baselines[level]) for level in ("M1", "M2", "M3")]
    report_rows.extend([_table_row(level, records[level], None) for level in ("M4", "M5")])
    headers = [
        "Niveau", "Nœuds / TET4", "DDL corps totaux / libres", "Lignes contact",
        "Erreur rel. déplacement", "Erreur rel. pression", "Norme erreur énergie √J",
        "Énergie FE J", "Résultante contact N", "Erreur rel. force", "Erreur moment Nm",
        "Erreur réaction support N / Nm", "Erreur front m / hx", "Provenance / état",
    ]

    level_sections = []
    for level in ("M4", "M5"):
        record = records[level]
        if record is None:
            level_sections.append(f"### {level}\n\nAucun enregistrement disponible : `NOT_ACQUIRED`.\n")
            continue
        state = record.get("scenario_state")
        if state != "COMPLETED_DIAGNOSTICS":
            failure_type, failure_message = _failure_details(record)
            level_sections.append(
                f"### {level}\n\nÉtat principal : `{_scenario_verdict(record)}` "
                f"(pytest ledger `{record.get('_ledger_state', 'NOT_RECORDED')}`, enregistrement `{state}`). "
                f"Cause/limitation : `{failure_type}: {failure_message}`. "
                "Les diagnostics dérivés absents ou invalides sont `NOT_EVALUATED`; ils ne remplacent pas un FAIL déjà consigné.\n"
            )
            continue
        diag = record["diagnostics"]
        fields = record["field_values"]
        checks = per_level[level]
        kkt_keys = [
            "maximum_penetration_m", "production_gap_reconstruction_error_m", "production_complementarity_inf_nm",
            "production_stationarity_inf_n", "independent_qp_primal_gap_min_m", "independent_qp_dual_multiplier_min_n",
            "independent_qp_complementarity_inf_nm", "independent_qp_stationarity_inf_n",
            "independent_qp_displacement_max_error_m", "independent_qp_multiplier_max_error_n",
            "production_force_balance_relative", "production_moment_balance_relative",
            "independent_qp_force_balance_relative", "independent_qp_moment_balance_relative",
            "production_contact_work_identity_error_j", "independent_qp_contact_work_identity_error_j",
        ]
        check_names = {
            "maximum_penetration_m": "maximum_penetration_m",
            "production_gap_reconstruction_error_m": "gap_reconstruction_error_m",
            "production_complementarity_inf_nm": "production_complementarity_nm",
            "production_stationarity_inf_n": "production_stationarity_n",
            "independent_qp_primal_gap_min_m": "independent_qp_primal_gap_m",
            "independent_qp_dual_multiplier_min_n": "independent_qp_dual_multiplier_n",
            "independent_qp_complementarity_inf_nm": "independent_qp_complementarity_nm",
            "independent_qp_stationarity_inf_n": "independent_qp_stationarity_n",
            "independent_qp_displacement_max_error_m": "production_vs_qp_displacement_m",
            "independent_qp_multiplier_max_error_n": "production_vs_qp_multiplier_n",
            "production_force_balance_relative": "production_force_balance",
            "production_moment_balance_relative": "production_moment_balance",
            "independent_qp_force_balance_relative": "independent_qp_force_balance",
            "independent_qp_moment_balance_relative": "independent_qp_moment_balance",
            "production_contact_work_identity_error_j": "production_contact_work_identity_j",
            "independent_qp_contact_work_identity_error_j": "independent_qp_contact_work_identity_j",
        }
        kkt_table = _md_table(
            ["Mesure KKT / équilibre", "Valeur", "Gate"],
            [[key, str(diag[key]), str(checks[check_names[key]].get("threshold", checks[check_names[key]].get("criterion")))] for key in kkt_keys],
        )
        field_note = (
            f"Les vecteurs nodaux sont archivés dans `{level.lower()}_diagnostics.json`: "
            f"{len(fields['body_displacements_m_node_major_xyz'])} déplacements corps, "
            f"{len(fields['contact_multipliers_n'])} multiplicateurs/pressions et "
            f"{len(fields['support_reactions_n_node_major_xyz'])} réactions nodales."
        )
        energy_rows = [
            ["Énergie FE matrice U_h", str(diag["strain_energy_j"])],
            ["Énergie FE quadrature", str(diag["fe_integrated_strain_energy_j"])],
            ["Énergie exacte", str(diag["exact_strain_energy_j"])],
            ["Écart total absolu", str(diag["absolute_strain_energy_difference_j"])],
            ["Norme d'erreur énergie", str(diag["strain_energy_error_norm_j_sqrt"])],
            ["Matrice / quadrature", str(diag["fe_energy_matrix_vs_quadrature_error_j"])],
        ]
        level_sections.append(
            f"### {level}\n\nVerdict local des gates M{level[-1]} : **{_status(checks)}**. {field_note}\n\n"
            f"**Énergies**\n\n{_md_table(['Mesure', 'Valeur'], energy_rows)}\n\n"
            f"**KKT, bilans et cohérence avec l'oracle QP indépendant**\n\n{kkt_table}\n\n"
            f"La trace active par rangée, les faux positifs/négatifs, le bracket et les valeurs `g, λ` voisin du front sont dans le bloc `diagnostics.front_trace_by_y`, `false_positives` et `false_negatives` de l'enregistrement JSON.\n"
        )

    ratios = "NOT_ACQUIRED"
    if endpoint is not None:
        ratios = _md_table(
            ["Critère prospectif AR", "Valeur", "Seuil inchangé", "Verdict"],
            [
                [key, str(value["actual"]), f"{value['operator']} {value['threshold']}", "PASS" if value["passed"] else "FAIL"]
                for key, value in endpoint.items()
            ],
        )

    check_lines = []
    for level, checks in per_level.items():
        check_lines.append(f"- **{level}** : `{_scenario_verdict(records[level], checks)}`")
    check_lines.append(f"- **M1→M3 historique AJ/AQ** : `{'PASS' if all(c['passed'] for c in historical_m1_m3.values()) else 'FAIL'}` (ne modifie pas le verdict Docker archivé).")
    check_lines.append(f"- **Ratios prospectifs M1→M5** : `{endpoint_status}`.")
    check_lines.append(f"- **Front actif M2–M5** : `{front_status}`; les traces historiques AQ M2/M3 ne sont pas archivées dans les preuves consultées.")

    return f"""# WP-C02-AR — rapport scientifique de convergence native M1–M5

## Verdict

**Résultat scientifique global : {scientific_verdict}.**

**État de qualification : NOT_ACQUIRED.** Cette campagne locale n'est pas déclarée équivalente aux campagnes Docker antérieures. Aucun verdict historique `FAIL_CLOSED` n'est modifié, et aucun `VERIFIED_BOUNDED` n'est attribué par ce rapport.

{chr(10).join(check_lines)}

## Identité et portée

- Campagne : WP-C02-AR, exécution native Python/pytest, sans Docker.
- Source des modèles et seuils : `wp_c02_ar_mesh_plan.json` et le protocole AR gelé. Aucune équation ni tolérance scientifique n'est redéfinie ici.
- M1–M3 : mesures AQ historiques, non relancées; les valeurs ci-dessous conservent l'arrondi de l'AR.
- M4/M5 : solveur de production `LinearStaticSolver` → `GlobalAssembler` → `FrictionlessActiveSetSolver`; le modèle analytique AJ reste la référence exacte et l'oracle QP indépendant, sans substitution synthétique du résultat production.
- La représentation du plan rigide ajoute trois nœuds de géométrie fixes (9 DDL fixes) au modèle solveur. Les DDL de corps et lignes KKT ci-dessous gardent les comptes AR.
- Contrôles de contact : une contrainte nodale par nœud inférieur; normale +z; loi Signorini frictionless; `g=0.001+u_z`, `g≥0`, `λ≥0`, `gλ=0`; `gap_tolerance=1e−10 m`. La politique dimensionnelle utilise une force de référence 1000 N et une tolérance relative `1e−10`, soit `1e−7 N` par ligne unitaire; aucune aire de patch n'est utilisée pour redistribuer cette tolérance.
- Paramètres de résolution : active-set de production, projection `accepted_rigid_plane_v1`, recherche initiale, `contact_max_iterations=128`; les équations restent celles du solveur de production.
- Limites locales : 900 s par scénario; 4 GiB RSS cumulés du processus pytest et de ses descendants, échantillonnés chaque 0,5 s; variables BLAS/OpenMP à un thread. Le superviseur termine l'arbre de processus au dépassement. La limite RSS est surveillée par échantillonnage et peut donc présenter un léger dépassement entre deux mesures; aucune limite CPU matérielle indépendante n'est imposée.
- Toute entrée M4/M5 dans le ledger a `attempt_count=1`. Le runner refuse de réutiliser le répertoire d'archive existant et n'effectue aucun retry.

## Résultats M1–M5

{_md_table(headers, report_rows)}

Les réactions exactes des supports pour M1–M3 ne sont pas présentes dans le résumé historique AQ (`NOT_RECORDED`) et ne sont pas inférées. Les vecteurs complets de déplacement, pression/multiplicateur, gap et réaction sont archivés pour les niveaux M4/M5 effectivement résolus.

## Critères et évaluations

Les seuils historiques AJ sont lus directement dans `frozen_aj_acceptance_gates` du plan AR : non-pénétration et reconstruction de gap `≤1e−10 m`, complémentarité `≤1e−10 N·m`, gap actif `≤1e−10 m`, multiplicateur ouvert `≤1e−7 N`, stationnarité et résidus QP `≤1e−6 N`, admissibilité QP `g_min≥−1e−10 m`, `λ_min≥−1e−7 N`, écart production/QP `u≤1e−9 m`, `λ≤1e−6 N`, bilans normalisés `≤1e−9`, identité de travail `≤1e−9 J`, et énergie matrice/quadrature `≤1e−10 J`. Les gates de raffinement AJ M1→M3 restent `E_u(M3)/E_u(M1)<0.9`, `E_p(M3)/E_p(M1)<0.9` et `E_U(M3)<E_U(M1)`.

Les extensions prospectives AR M1→M5 gardent les mêmes valeurs numériques : ratio d'erreur déplacement `<0.9`, ratio pression `<0.9`, norme d'erreur énergie strictement décroissante. Aucune monotonie de M1→M2→…→M5 n'est exigée.

**Ratios prospectifs M1→M5**

{ratios}

**Front actif.** Le gate AR prospectif M2–M5 est limité à une cellule (`D_front,max/hx≤1`), exige un bracket actif/ouvert dans chaque rangée, des erreurs de classification à distance `≤hx` et aucune ligne à front multiple. M1 reste un diagnostic d'aliasing. Les valeurs agrégées historiques M2/M3 sont disponibles, mais les traces par rangée, le compte complet des brackets et le diagnostic de fronts multiples n'apparaissent pas dans le résumé AQ conservé. Elles restent donc `NOT_ACQUIRED` pour la couverture historique M2/M3. Cette lacune n'est pas comblée en relançant M1–M3.

{front_table}

## Détail KKT et champs M4/M5

{chr(10).join(level_sections)}

## Interprétation et limites

- Un `PASS` des erreurs de champ et des gates KKT pour M4/M5 établit le comportement observé sur les scénarios exacts exécutés; les extensions M1/M5 sont des critères AR prospectifs et non des résultats AQ historiques.
- Si M4/M5 passent mais que les traces historiques M2/M3 restent indisponibles, la convergence complète du front M1–M5 demeure `NOT_ACQUIRED` selon la couverture AR. Un échec numérique ou d'un seuil est `FAIL`; un scénario interrompu avant données suffisantes est `NOT_ACQUIRED`.
- Les niveaux sont non emboîtés après M1→M2; les erreurs de champ restent comparées à la même solution continue intégrée sur chaque maillage, et non par index de nœud.
- La ligne `x=0.5 m` reste alignée sur une limite de cellule à chaque niveau. Les résultats ne démontrent ni un ordre asymptotique, ni un théorème général de convergence de frontière libre.
- Ce rapport n'accorde pas d'équivalence avec Docker ni de qualification générale de contact. Une telle décision relève d'un protocole de remplacement explicitement approuvé par l'Owner et du contrat de qualification applicable.

## Archive et provenance

Le répertoire contient le ledger one-shot, les logs pytest, les diagnostics JSON par scénario, le snapshot source gelé, le manifeste d'exécution et `archive_integrity_manifest.json` avec les empreintes SHA-256 des éléments archivés. Le hash du manifeste d'intégrité se trouve dans `archive_integrity_manifest.sha256`.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    args = parser.parse_args()
    archive = args.archive.resolve()
    report = render_report(archive)
    (archive / "wp_c02_ar_native_spatial_convergence_report.md").write_text(report, encoding="utf-8")
    print("report_written=wp_c02_ar_native_spatial_convergence_report.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
