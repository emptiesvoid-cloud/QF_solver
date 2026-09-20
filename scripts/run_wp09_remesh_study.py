"""Run a diagnostic 3-D remeshing study for the bounded WP09 route.

This study is deliberately separate from the frozen formal contract.  It uses
the accepted bounded load scale of 25 percent, compares isotropic H1/H2/H3
meshes, and records mesh quality, DOFs, structural observables, and refinement
delays without awarding formal points.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from solveur.api import solve_model  # noqa: E402
from solveur.mesh.validation import MeshValidator  # noqa: E402


FAMILIES = ("TET4", "HEX8")
LEVELS = (1, 2, 4)
LOAD_SCALE = 0.25
LOAD_STEPS = (0.25, 0.5, 0.75, 1.0)
LOCAL_STRAIN_LIMIT = 0.05
MATERIAL = {
    "type": "von_mises_elastoplastic_3d",
    "E": 1000.0,
    "nu": 0.3,
    "yield_stress": 0.02,
    "hardening_modulus": 10.0,
}


def _json_default(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"unsupported JSON value: {type(value).__name__}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git(*args: str) -> str:
    import subprocess

    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else "UNAVAILABLE"


def _node_id(i: int, j: int, k: int, n: int) -> int:
    side = n + 1
    return k * side * side + j * side + i


def _mesh(family: str, n: int) -> tuple[np.ndarray, list[list[int]]]:
    coordinates = np.asarray(
        [
            (i / n, j / n, k / n)
            for k in range(n + 1)
            for j in range(n + 1)
            for i in range(n + 1)
        ],
        dtype=float,
    )
    elements: list[list[int]] = []
    tet_templates = ((0, 1, 3, 4), (1, 2, 3, 6), (1, 3, 4, 6), (1, 4, 5, 6), (3, 4, 6, 7))
    for k in range(n):
        for j in range(n):
            for i in range(n):
                corners = [
                    _node_id(i, j, k, n),
                    _node_id(i + 1, j, k, n),
                    _node_id(i + 1, j + 1, k, n),
                    _node_id(i, j + 1, k, n),
                    _node_id(i, j, k + 1, n),
                    _node_id(i + 1, j, k + 1, n),
                    _node_id(i + 1, j + 1, k + 1, n),
                    _node_id(i, j + 1, k + 1, n),
                ]
                if family == "HEX8":
                    elements.append(corners)
                else:
                    for template in tet_templates:
                        tet = [corners[index] for index in template]
                        matrix = np.column_stack(
                            (
                                coordinates[tet[1]] - coordinates[tet[0]],
                                coordinates[tet[2]] - coordinates[tet[0]],
                                coordinates[tet[3]] - coordinates[tet[0]],
                            )
                        )
                        if np.linalg.det(matrix) < 0.0:
                            tet[2], tet[3] = tet[3], tet[2]
                        elements.append(tet)
    return coordinates, elements


def _model(family: str, n: int):
    from solveur.core.model import FiniteElementModel

    nodes, elements = _mesh(family, n)
    fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
    loaded_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 1.0))
    return FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": family, "nodes": element, "material": "j2"} for element in elements],
        materials={"j2": dict(MATERIAL)},
        fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in fixed_nodes],
        loads=[
            {"node": int(node), "dof": "UX", "value": LOAD_SCALE / len(loaded_nodes)}
            for node in loaded_nodes
        ],
        analysis={
            "type": "nonlinear_static",
            "method": "newton_raphson",
            "load_path": list(LOAD_STEPS),
            "max_iterations": 40,
            "tolerance": 1.0e-7,
            "parameters": {
                "kinematics": "corotational_j2",
                "corotational_max_local_strain": LOCAL_STRAIN_LIMIT,
                "adaptive_load_steps": False,
            },
        },
    )


def _metrics(result: Any, elapsed: float) -> dict[str, Any]:
    audit = result.audit.equilibrium if result.audit is not None else {}
    steps = list(result.solver.get("steps", []))
    points = [point for element in result.element_results for point in element.get("integration_points", [])]
    states = [state for values in result.material_states.values() for state in values]
    return {
        "status": str(result.status),
        "node_count": int(result.node_count),
        "element_count": int(result.element_count),
        "dof_count": int(result.displacements.size),
        "selected_displacement": float(np.max(np.abs(result.displacements))),
        "reaction_norm": float(np.linalg.norm(audit.get("reaction_resultant", ()))),
        "energy": float(sum(float(step.get("incremental_internal_work", 0.0)) for step in steps)),
        "von_mises_max": float(max((float(row.get("von_mises", 0.0)) for row in result.element_results), default=0.0)),
        "equivalent_plastic_strain_max": float(max((float(state.get("equivalent_plastic_strain", 0.0)) for state in states), default=0.0)),
        "plastic_dissipation_max": float(max((float(state.get("plastic_dissipation", 0.0)) for state in states), default=0.0)),
        "min_det_f": float(min((float(point["det_f"]) for point in points if "det_f" in point), default=float("nan"))),
        "max_local_strain_norm": float(max((float(point["corotational_strain_norm"]) for point in points if "corotational_strain_norm" in point), default=float("nan"))),
        "accepted_steps": len(steps) if str(result.status) == "PASS" else 0,
        "newton_iterations": int(sum(int(step.get("iterations", 0)) for step in steps)),
        "rejected_increments": int(result.solver.get("rejected_increments", 0)),
        "free_relative_residual": float(audit.get("free_relative_residual", float("nan"))),
        "force_balance_relative_error": float(audit.get("force_balance_relative_error", float("nan"))),
        "moment_balance_relative_error": float(audit.get("moment_balance_relative_error", float("nan"))),
        "elapsed_seconds": elapsed,
    }


def _run(family: str, n: int, output: Path) -> dict[str, Any]:
    started = time.perf_counter()
    model = _model(family, n)
    quality = MeshValidator().validate(model)
    mesh_payload = {
        "nodes": model.nodes,
        "elements": [
            {"type": element.type, "nodes": list(element.nodes), "material": element.material}
            for element in model.elements
        ],
    }
    row: dict[str, Any] = {
        "family": family,
        "level": f"{n}x{n}x{n}",
        "nodes": int(model.node_count),
        "elements": int(len(model.elements)),
        "dofs": int(model.dof_manager().ndof),
        "quality": quality.to_dict(),
        "mesh_sha256": hashlib.sha256(
            json.dumps(mesh_payload, sort_keys=True, default=_json_default).encode()
        ).hexdigest(),
    }
    try:
        result = solve_model(model, enforce_policy=False)
        row["metrics"] = _metrics(result, time.perf_counter() - started)
        row["displacements"] = np.asarray(result.displacements, dtype=float).tolist()
        row["solver"] = result.solver
        row["audit"] = result.audit.to_dict() if result.audit is not None else {}
    except Exception as exc:  # diagnostic failure is preserved.
        row["metrics"] = {
            "status": "FAIL_EXCEPTION",
            "exception_type": type(exc).__name__,
            "exception": str(exc),
            "elapsed_seconds": time.perf_counter() - started,
        }
    path = output / f"{family.lower()}_{n}x{n}x{n}.json"
    path.write_text(json.dumps(row, indent=2, default=_json_default, allow_nan=False), encoding="utf-8")
    return row


def _relative(left: float, right: float) -> float:
    return abs(left - right) / max(abs(left), abs(right), 1.0e-14)


def _comparison(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    comparisons = []
    for coarse, fine in zip(rows, rows[1:]):
        c = coarse["metrics"]
        f = fine["metrics"]
        if c.get("status") != "PASS" or f.get("status") != "PASS":
            comparisons.append(
                {
                    "from": coarse["level"],
                    "to": fine["level"],
                    "status": "NOT_COMPARABLE_FAILED_LEVEL",
                    "relative_deltas": {},
                    "coarse_status": c.get("status"),
                    "fine_status": f.get("status"),
                }
            )
            continue
        names = ("selected_displacement", "reaction_norm", "energy", "von_mises_max", "equivalent_plastic_strain_max")
        comparisons.append(
            {
                "from": coarse["level"],
                "to": fine["level"],
                "status": "PASS_COMPARABLE",
                "relative_deltas": {name: _relative(float(c[name]), float(f[name])) for name in names},
            }
        )
    return comparisons


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "qualification" / "0_2_9" / "wp09_remesh_study_r1")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise SystemExit(f"Refusing to overwrite non-empty output: {output}")
    output.mkdir(parents=True, exist_ok=True)
    summary: dict[str, Any] = {
        "status": "RUNNING",
        "classification": "DIAGNOSTIC_ONLY_NO_FORMAL_POINTS",
        "branch": _git("branch", "--show-current"),
        "execution_sha": _git("rev-parse", "HEAD"),
        "load_scale": LOAD_SCALE,
        "load_path": list(LOAD_STEPS),
        "local_strain_limit": LOCAL_STRAIN_LIMIT,
        "material": MATERIAL,
        "levels": [f"{n}x{n}x{n}" for n in LEVELS],
        "mesh_generation": "structured isotropic 3-D unit cube; HEX8 or five positive TET4 per brick",
        "families": {},
    }
    for family in FAMILIES:
        print(f"START {family} H1/H2/H3", flush=True)
        rows = [_run(family, n, output) for n in LEVELS]
        summary["families"][family] = {
            "rows": rows,
            "refinement_comparisons": _comparison(rows),
            "status": "PASS_RUNS" if all(row["metrics"].get("status") == "PASS" for row in rows) else "FAIL_RUN",
        }
    summary["status"] = "PASS_DIAGNOSTIC_RUNS" if all(
        data["status"] == "PASS_RUNS" for data in summary["families"].values()
    ) else "FAIL_DIAGNOSTIC_RUN"
    (output / "summary.json").write_text(json.dumps(summary, indent=2, default=_json_default, allow_nan=False), encoding="utf-8")
    manifest = []
    for path in sorted(output.glob("*.json")):
        if path.name == "manifest.json":
            continue
        manifest.append({"path": path.name, "sha256": _sha256(path), "bytes": path.stat().st_size})
    (output / "manifest.json").write_text(
        json.dumps({"schema_version": 1, "execution_sha": summary["execution_sha"], "files": manifest}, indent=2),
        encoding="utf-8",
    )
    report = [
        "# WP09 isotropic 3-D remesh study",
        "",
        f"Status: `{summary['status']}`",
        f"Load scale: `{LOAD_SCALE}`",
        f"Execution SHA: `{summary['execution_sha']}`",
        "",
        "| Family | Level | Nodes | Elements | DOFs | Status |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for family, data in summary["families"].items():
        for row in data["rows"]:
            report.append(
                f"| {family} | {row['level']} | {row['nodes']} | {row['elements']} | {row['dofs']} | {row['metrics'].get('status')} |"
            )
        report.append("")
        for comparison in data["refinement_comparisons"]:
            report.append(f"{family} {comparison['from']} → {comparison['to']}: `{comparison['relative_deltas']}`")
    report.extend(
        [
            "",
            "This study is diagnostic only. It does not rebind the formal contract or award WP09 points.",
        ]
    )
    (output / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps({"status": summary["status"], "families": {family: data["status"] for family, data in summary["families"].items()}}, indent=2), flush=True)
    return 0 if summary["status"] == "PASS_DIAGNOSTIC_RUNS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
