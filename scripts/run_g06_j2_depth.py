"""Run and archive the deep 0.2.6 G06 small-strain J2 evidence pack.

This runner composes existing verification campaigns. It does not alter solver
formulations, gate status, thresholds, or public capability claims.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from solveur.io.manifest import sha256, write_json_file  # noqa: E402
from solveur.api import solve_model  # noqa: E402
from solveur.core.errors import MeshValidationError  # noqa: E402
from solveur.core.model import FiniteElementModel  # noqa: E402
from solveur.verification.framework.environment import capture_environment  # noqa: E402
from solveur.verification.j2_step_sensitivity import J2StepSensitivityCampaign  # noqa: E402
from solveur.verification.j2_structural import J2StructuralCyclicCampaign  # noqa: E402
from solveur.verification.j2_multielement_external import (  # noqa: E402
    ELEMENT_TYPES,
)
from solveur.verification.robustness_nonlinear_solids import (  # noqa: E402
    run_adversarial_rollback_benchmark,
    run_cyclic_load_benchmark,
    run_energy_balance_benchmark,
    run_mesh_refinement_benchmark,
    run_multi_element_benchmark,
)


PACK_ID = "VNV026-G06-J2-DEPTH-001"
EXTERNAL_COMMAND = "python scripts/run_j2_multielement_external_025.py --output results/g06_depth/code_aster_j2"


def _run_internal(output: Path) -> dict[str, Any]:
    tet10 = J2StructuralCyclicCampaign(output / "tet10_cyclic", element_type="TET10").run()
    invalid_tet10 = _invalid_tet10_case()
    mesh = run_mesh_refinement_benchmark(levels=(1, 2, 4, 8))
    write_json_file(output / "mesh_refinement.json", mesh)
    increment = J2StepSensitivityCampaign(output / "increment_sensitivity").run()
    multi = run_multi_element_benchmark()
    energy = run_energy_balance_benchmark()
    cyclic = run_cyclic_load_benchmark()
    rollback_rows = [run_adversarial_rollback_benchmark(family) for family in ELEMENT_TYPES]
    rollback = {
        "status": "PASS_INTERNAL_ROLLBACK" if all(row["status"] == "PASS_INTERNAL_ROLLBACK" for row in rollback_rows) else "FAIL",
        "rows": rollback_rows,
    }
    write_json_file(output / "multi_element.json", multi)
    write_json_file(output / "energy_balance.json", energy)
    write_json_file(output / "cyclic.json", cyclic)
    write_json_file(output / "rollback.json", rollback)
    write_json_file(output / "invalid_tet10.json", invalid_tet10)
    return {
        "tet10_dedicated": tet10,
        "invalid_tet10": invalid_tet10,
        "mesh_refinement": mesh,
        "increment_refinement": increment,
        "multi_element": multi,
        "energy_balance": energy,
        "cyclic": cyclic,
        "rollback": rollback,
    }


def _invalid_tet10_case() -> dict[str, Any]:
    """Record the expected rejection of an inverted TET10 before solving."""
    from solveur.verification.robustness_nonlinear_solids import mesh_refinement_mesh

    nodes, elements = mesh_refinement_mesh("TET10", 1)
    elements[0][0], elements[0][1] = elements[0][1], elements[0][0]
    fixed = [
        {"node": int(index), "dofs": ["UX", "UY", "UZ"]}
        for index, point in enumerate(nodes)
        if point[0] == 0.0
    ]
    model = FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": "TET10", "nodes": item, "material": "j2"} for item in elements],
        materials={
            "j2": {
                "type": "von_mises_elastoplastic_3d",
                "E": 1000.0,
                "nu": 0.3,
                "yield_stress": 0.02,
                "hardening_modulus": 10.0,
            }
        },
        fixed_dofs=fixed,
        loads=[
            {"node": int(index), "dof": "UX", "value": 0.1}
            for index, point in enumerate(nodes)
            if point[0] == 1.0
        ],
        analysis={"type": "nonlinear_static", "method": "newton_raphson", "load_path": [1.0]},
    )
    try:
        solve_model(model, enforce_policy=False)
    except MeshValidationError as error:
        return {
            "status": "EXPECTED_FAILURE",
            "failure_category": "INVALID_ELEMENT",
            "element": "TET10",
            "message": str(error),
        }
    return {
        "status": "FAIL",
        "failure_category": "INVALID_ELEMENT_NOT_REJECTED",
        "element": "TET10",
    }


def _external_evidence(path: Path, source: dict[str, Any]) -> dict[str, Any]:
    command = (
        "python scripts/run_j2_multielement_external_025.py --output "
        f"{path.relative_to(ROOT).as_posix()}"
    )
    summary_path = path / "summary.json"
    if not summary_path.is_file():
        return {
            "status": "SKIPPED_WITH_REASON",
            "executed": False,
            "reason": "Code_Aster summary is absent; run the opt-in external command first.",
            "command": command,
            "source": source,
        }
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    family_rows = {
        row["element"]: {
            "status": row["status"],
            "comparability_status": row["comparability_status"],
            "max_relative_error": max(
                check["value"]
                for check in summary["checks"]
                if check["id"].startswith(f"{row['element']}_")
            ),
        }
        for row in summary["rows"]
    }
    return {
        "status": summary.get("status", "UNKNOWN"),
        "executed": True,
        "command": command,
        "external_solver": summary.get("external_solver", {}),
        "checks": len(summary.get("checks", [])),
        "families": family_rows,
        "summary_path": path.relative_to(ROOT).as_posix() + "/summary.json",
        "summary_sha256": sha256(summary_path),
        "source": source,
        "quadrature_conventions": summary.get("scope", {}).get("quadrature_conventions", {}),
    }


def _status(item: dict[str, Any]) -> str:
    return str(item.get("status", "UNKNOWN"))


def _invariant_matrix(internal: dict[str, Any], external: dict[str, Any]) -> list[dict[str, Any]]:
    external_families = external.get("families", {})
    mesh_rows = {row["element"]: row for row in internal["mesh_refinement"]["rows"]}
    multi_rows = {row["element"]: row for row in internal["multi_element"]["rows"]}
    energy_rows = {row["element"]: row for row in internal["energy_balance"]["rows"]}
    cyclic_rows = {row["element"]: row for row in internal["cyclic"]["rows"]}
    rollback_rows = {row["element"]: row for row in internal["rollback"]["rows"]}
    rows = []
    for family in ELEMENT_TYPES:
        checks = {
            "mesh_refinement": mesh_rows[family]["status"],
            "multi_element": multi_rows[family]["status"],
            "energy_balance": energy_rows[family]["status"],
            "cyclic": cyclic_rows[family]["status"],
            "rollback": rollback_rows[family]["status"],
            "external": external_families.get(family, {}).get("status", "SKIPPED"),
        }
        rows.append({
            "element": family,
            "checks": checks,
            "internal_pass": all(value in {"PASS", "PASS_INTERNAL_ENERGY", "PASS_INTERNAL_ROLLBACK"} for key, value in checks.items() if key != "external"),
            "external_pass": checks["external"] == "PASS",
        })
    return rows


def _write_report(path: Path, summary: dict[str, Any]) -> None:
    internal = summary["internal"]
    lines = [
        f"# {PACK_ID}",
        "",
        f"Status: **{summary['proposed_decision']}** (official gate remains **NOT_STARTED**).",
        "",
        f"Source SHA: `{summary['environment']['source']['sha']}`; dirty: `{summary['environment']['source']['dirty']}`.",
        "",
        "## Dedicated TET10",
        "",
        f"`{internal['tet10_dedicated']['campaign_id']}`: **{internal['tet10_dedicated']['status']}**, "
        f"{internal['tet10_dedicated']['mesh']['nodes']} nodes, {internal['tet10_dedicated']['mesh']['elements']} elements, "
        f"{internal['tet10_dedicated']['mesh']['integration_points_per_element']} integration points/element.",
        "",
        f"Inverted TET10 rejection: **{internal['invalid_tet10']['status']}** ({internal['invalid_tet10'].get('failure_category', 'n/a')}).",
        "",
        "![TET10 cyclic response](tet10_cyclic/cyclic_response.png)",
        "",
        "## J2 mesh refinement",
        "",
        "| Family | Levels | Final PEEQ | Final VM | Energy | Newton iterations | Status |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for family in internal["mesh_refinement"]["rows"]:
        final = family["levels"][-1]
        lines.append(
            f"| {family['element']} | {', '.join(str(row['cells_x']) for row in family['levels'])} | "
            f"{final['peeq_max']:.6e} | {final['von_mises_max']:.6e} | {final['energy']:.6e} | "
            f"{final['newton_iterations']} | {family['status']} |"
        )
    lines.extend([
        "",
        "The four levels are a bounded regular-mesh internal study; no universal mesh threshold is claimed.",
        "",
        "## Common invariants",
        "",
        "| Family | Mesh | Multi-element | Energy | Cyclic | Rollback | External |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ])
    for row in summary["invariant_matrix"]:
        values = row["checks"]
        lines.append(
            f"| {row['element']} | {values['mesh_refinement']} | {values['multi_element']} | "
            f"{values['energy_balance']} | {values['cyclic']} | {values['rollback']} | {values['external']} |"
        )
    lines.extend([
        "",
        "## External correlation",
        "",
        f"Status: **{summary['external']['status']}**; checks: `{summary['external'].get('checks', 0)}`.",
        "",
        "This is bounded numerical correlation, not physical validation. TET10 uses `code_aster_5` for the external comparison; QF's historical default remains unchanged.",
        "",
        "## Limitations",
        "",
    ])
    lines.extend(f"- {item}" for item in summary["limitations"])
    (path / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_manifest(path: Path, summary: dict[str, Any]) -> None:
    files = []
    for artifact in sorted(path.rglob("*")):
        if artifact.is_file() and artifact.name != "evidence_manifest.json":
            files.append({"path": artifact.relative_to(path).as_posix(), "sha256": sha256(artifact)})
    manifest = {
        "schema_version": 1,
        "pack_id": PACK_ID,
        "gate": "026-G06",
        "official_gate_status": "NOT_STARTED",
        "source_sha": summary["environment"]["source"]["sha"],
        "source_dirty": summary["environment"]["source"]["dirty"],
        "captured_at_utc": summary["environment"]["captured_at_utc"],
        "solver_version": summary["environment"]["solver_version"],
        "threshold_source": "qualification/0_2_6/tolerance_policy.json",
        "files": files,
    }
    write_json_file(path / "evidence_manifest.json", manifest)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "g06_depth")
    parser.add_argument(
        "--external-output",
        type=Path,
        default=ROOT / "results" / "g06_depth" / "code_aster_j2",
    )
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    environment = capture_environment(ROOT)
    internal = _run_internal(output)
    external = _external_evidence(args.external_output.resolve(), environment["source"])
    summary: dict[str, Any] = {
        "schema_version": 1,
        "pack_id": PACK_ID,
        "gate": "026-G06",
        "official_gate_status": "NOT_STARTED",
        "environment": environment,
        "internal": internal,
        "external": external,
        "invariant_matrix": [],
        "finite_kinematic_j2": "RESEARCH_NOT_QUALIFIED",
        "unexpected_failures": [],
        "proposed_decision": "PASS_WITH_LIMITATIONS",
        "limitations": [
            "The official G06 gate is not closed by this runner; Owner closeout remains required.",
            "All four-family mesh evidence uses a regular unit-block benchmark and is bounded internal evidence.",
            "The load-increment refinement campaign is the existing TET4 structural path; it is not a universal path-independence claim for every family.",
            "The Code_Aster correlation is bounded to the regular two-cell shared benchmark and does not claim physical validation.",
            "Finite-kinematic J2 and coupled nonlinear workflows remain research/experimental and are not promoted.",
        ],
    }
    summary["invariant_matrix"] = _invariant_matrix(internal, external)
    internal_items = (internal["tet10_dedicated"], internal["mesh_refinement"], internal["increment_refinement"], internal["multi_element"], internal["energy_balance"], internal["cyclic"], internal["rollback"])
    expected_failure_ok = internal["invalid_tet10"]["status"] == "EXPECTED_FAILURE"
    internal_ok = all(_status(item).startswith("PASS") for item in internal_items)
    external_ok = external.get("status") == "PASS_EXTERNAL_CORRELATION"
    if not internal_ok or not expected_failure_ok or not external_ok:
        summary["proposed_decision"] = "OPEN_WITH_BLOCKERS"
        if not external_ok:
            summary["limitations"].append("External TET/HEX correlation is not PASS_EXTERNAL_CORRELATION in the archived input.")
    write_json_file(output / "summary.json", summary)
    _write_report(output, summary)
    _write_manifest(output, summary)
    print(json.dumps({
        "status": summary["proposed_decision"],
        "source": environment["source"],
        "tet10": internal["tet10_dedicated"]["status"],
        "mesh": internal["mesh_refinement"]["status"],
        "external": external["status"],
        "invariants": summary["invariant_matrix"],
        "output": str(output),
    }, indent=2))
    return 0 if internal_ok and external_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
