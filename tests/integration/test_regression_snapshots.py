import json
import csv
from pathlib import Path

from solveur.api import check_mesh, load_model, save_result_csv, solve_model


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOTS = PROJECT_ROOT / "tests" / "snapshots"
TET4_EXAMPLE = PROJECT_ROOT / "examples" / "tet4_static.json"
OFFICIAL_EXAMPLES = (
    "tet4_static",
    "tet10_static",
    "mitc4_shell_static",
    "tet4_nonlinear_static",
    "tet4_elastoplastic_static",
    "tet4_transient_dynamic",
    "tet4_dynamic_free_vibration",
    "tet4_dynamic_tabulated_load",
)


def test_tet4_result_audit_mesh_and_csv_snapshots(tmp_path: Path):
    model = load_model(TET4_EXAMPLE)
    report = check_mesh(model)
    result = solve_model(model)
    data = result.to_dict()
    audit = data["audit"]
    csv_paths = save_result_csv(result, tmp_path / "csv", model)
    with csv_paths["element_results"].open(encoding="utf-8", newline="") as handle:
        csv_rows = list(csv.reader(handle))

    assert _result_summary(data) == _snapshot("tet4_result_summary.json")
    assert _audit_summary(audit) == _snapshot("tet4_audit_summary.json")
    assert _mesh_summary(report) == _snapshot("tet4_mesh_report_summary.json")
    assert _csv_summary(csv_rows) == _snapshot("tet4_csv_summary.json")


def test_official_examples_regression_snapshots(tmp_path: Path):
    observed = {}
    for stem in OFFICIAL_EXAMPLES:
        model = load_model(PROJECT_ROOT / "examples" / f"{stem}.json")
        report = check_mesh(model)
        result = solve_model(model)
        data = result.to_dict()
        csv_paths = save_result_csv(result, tmp_path / stem / "csv", model)
        observed[stem] = {
            "result": _official_result_summary(data),
            "audit": _official_audit_summary(data["audit"]),
            "mesh": _mesh_summary(report),
            "csv": _official_csv_summary(csv_paths),
        }

    assert observed == _snapshot("official_examples_summary.json")


def _result_summary(data: dict[str, object]) -> dict[str, object]:
    return {
        "status": data["status"],
        "analysis": data["analysis"],
        "method": data["method"],
        "node_count": data["node_count"],
        "element_count": data["element_count"],
        "ndof": data["ndof"],
        "max_displacement": data["max_displacement"],
        "element_type": data["element_results"][0]["type"],
        "von_mises": data["element_results"][0]["von_mises"],
        "principal_stress": data["element_results"][0]["principal_stress"],
        "mesh_status": data["mesh_report"]["status"],
    }


def _audit_summary(audit: dict[str, object]) -> dict[str, object]:
    return {
        "purpose": audit["purpose"],
        "analysis": audit["analysis"],
        "mesh_status": audit["mesh_status"],
        "component_count": audit["mesh_details"]["component_count"],
        "matrix_names": [matrix["name"] for matrix in audit["matrices"]],
        "post_type": audit["post_results"][0]["type"],
        "check_names": [check["name"] for check in audit["checks"][:5]],
        "free_relative_residual": audit["equilibrium"]["free_relative_residual"],
    }


def _mesh_summary(report: object) -> dict[str, object]:
    quality = report.details["element_quality"][0]
    return {
        "status": report.status,
        "errors": report.errors,
        "warnings": report.warnings,
        "details": {
            "node_count": report.details["node_count"],
            "element_count": report.details["element_count"],
            "component_count": report.details["component_count"],
            "element_types": report.details["element_types"],
            "quality_keys": sorted(key for key in quality if key not in {"index", "type"}),
            "mechanical_rank_checked": report.details["mechanical_rank"]["checked"],
            "mechanical_zero_mode_count": report.details["mechanical_rank"]["zero_mode_count"],
        },
    }


def _csv_summary(rows: list[list[str]]) -> dict[str, object]:
    return {
        "element_results_header": rows[0],
        "element_results_first_row_columns": len(rows[1]),
    }


def _official_result_summary(data: dict[str, object]) -> dict[str, object]:
    first = data["element_results"][0]
    return {
        "status": data["status"],
        "analysis": data["analysis"],
        "method": data["method"],
        "node_count": data["node_count"],
        "element_count": data["element_count"],
        "ndof": data["ndof"],
        "max_displacement": data["max_displacement"],
        "element_type": first["type"],
        "element_result_keys": sorted(first.keys()),
        "von_mises": first.get("von_mises"),
        "principal_stress": first.get("principal_stress"),
        "shell_face_count": len(first.get("shell_faces", [])),
        "mesh_status": data["mesh_report"]["status"],
        "solver_converged": data["solver"].get("converged"),
        "solver_iterations": data["solver"].get("iterations"),
        "nonlinear_step_count": len(data["solver"].get("steps", [])),
    }


def _official_audit_summary(audit: dict[str, object]) -> dict[str, object]:
    return {
        "purpose": audit["purpose"],
        "analysis": audit["analysis"],
        "mesh_status": audit["mesh_status"],
        "component_count": audit["mesh_details"]["component_count"],
        "matrix_names": [matrix["name"] for matrix in audit["matrices"]],
        "post_type": audit["post_results"][0]["type"],
        "post_keys": sorted(audit["post_results"][0].keys()),
        "check_statuses": sorted({check["status"] for check in audit["checks"]}),
        "free_relative_residual": audit["equilibrium"]["free_relative_residual"],
    }


def _official_csv_summary(paths: dict[str, Path]) -> dict[str, object]:
    with paths["element_results"].open(encoding="utf-8", newline="") as handle:
        element_rows = list(csv.reader(handle))
    with paths["post_results"].open(encoding="utf-8", newline="") as handle:
        post_rows = list(csv.reader(handle))
    return {
        "element_results_header": element_rows[0],
        "element_results_first_row_columns": len(element_rows[1]),
        "post_results_first_row_columns": len(post_rows[1]),
    }


def _snapshot(name: str) -> dict[str, object]:
    return json.loads((SNAPSHOTS / name).read_text(encoding="utf-8"))
