"""Run the controlled WP08 WEDGE6 static vertical-slice evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import tempfile

import numpy as np

from solveur.api import import_gmsh_model, solve_model
from solveur.benchmarks.gmsh_factory import BenchmarkMeshFactory
from solveur.core.errors import InfrastructureError
from solveur.core.model import FiniteElementModel
from solveur.loads.entities import BodyLoad, SurfaceLoad
from solveur.loads.integration import DistributedLoadIntegrator
from solveur.verification.v2 import ExternalUnavailableError, ExecutionOutput, VnvRunner, load_cases


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "qualification" / "0_2_7" / "vnv_v2" / "wp08_cases.json"
NODES = [
    [0.0, 0.0, 0.0],
    [2.0, 0.0, 0.0],
    [0.0, 1.0, 0.0],
    [0.0, 0.0, 1.0],
    [2.0, 0.0, 1.0],
    [0.0, 1.0, 1.0],
]
MATERIALS = {"steel": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3, "density": 7800.0}}


def _model(
    *,
    nodes: list[list[float]] | None = None,
    elements: list[dict[str, object]] | None = None,
    fixed_dofs: list[dict[str, object]] | None = None,
    loads: list[dict[str, object]] | None = None,
    distributed_loads: list[dict[str, object]] | None = None,
    multipoint_constraints: list[dict[str, object]] | None = None,
) -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        nodes=nodes or NODES,
        elements=elements or [{"type": "WEDGE6", "nodes": list(range(6)), "material": "steel"}],
        materials=MATERIALS,
        fixed_dofs=fixed_dofs,
        loads=loads,
        distributed_loads=distributed_loads,
        multipoint_constraints=multipoint_constraints,
        analysis="linear_static",
    )


def _fixed_triangle() -> list[dict[str, object]]:
    return [{"node": index, "dofs": ["UX", "UY", "UZ"]} for index in range(3)]


def _two_prism_model() -> FiniteElementModel:
    nodes = NODES + [[0.0, 0.0, 2.0], [2.0, 0.0, 2.0], [0.0, 1.0, 2.0]]
    elements = [
        {"type": "WEDGE6", "nodes": [0, 1, 2, 3, 4, 5], "material": "steel"},
        {"type": "WEDGE6", "nodes": [3, 4, 5, 6, 7, 8], "material": "steel"},
    ]
    return _model(
        nodes=nodes,
        elements=elements,
        fixed_dofs=_fixed_triangle(),
        loads=[{"node": 6, "dof": "UX", "value": 1.0}, {"node": 7, "dof": "UX", "value": 1.0}],
        distributed_loads=[{"type": "pressure", "element": 1, "face": 1, "value": 10.0}],
    )


def _gmsh_setup() -> dict[str, object]:
    return {
        "schema_version": 1,
        "mesh_scale_to_m": 1.0,
        "units": {"system": "SI"},
        "verification_profile": "engineering",
        "analysis": "linear_static",
        "materials": MATERIALS,
        "groups": [
            {
                "name": "domain",
                "dimension": 3,
                "actions": [
                    {"type": "elements", "element_type": "WEDGE6", "material": "steel"},
                    {"type": "body_force", "value": [0.0, 0.0, -10.0]},
                ],
            },
            {"name": "tri_bottom", "dimension": 2, "actions": [{"type": "fixed_dofs", "dofs": ["UX", "UY", "UZ"]}]},
            {"name": "tri_top", "dimension": 2, "actions": [{"type": "pressure", "value": 2.0}]},
            {"name": "quad_side_12", "dimension": 2, "actions": [{"type": "surface_traction", "value": [0.0, 0.0, -3.0]}]},
            {"name": "loaded_node", "dimension": 0, "actions": [{"type": "nodal_load", "dof": "UX", "value": 1.0}]},
        ],
    }


def _imported_gmsh() -> object:
    try:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mesh = BenchmarkMeshFactory().discrete_wedge6_prism(
                root / "wedge6.msh", length=2.0, width=1.0, height=1.0
            )
            setup_path = root / "wedge6.setup.json"
            setup_path.write_text(json.dumps(_gmsh_setup()), encoding="utf-8")
            return import_gmsh_model(mesh, setup_path)
    except InfrastructureError as exc:
        raise ExternalUnavailableError(str(exc)) from exc


def _result(case_id: str) -> ExecutionOutput:
    if case_id == "WP08-GMSH-IMPORT":
        imported = _imported_gmsh()
        return ExecutionOutput({"element_family": imported.report.element_family})
    if case_id == "WP08-GMSH-FACE-MAP":
        imported = _imported_gmsh()
        faces = [load.face for load in imported.model.distributed_loads if load.type != "body_force"]
        return ExecutionOutput({"mapped_faces": faces})
    if case_id == "WP08-NODAL-STATIC":
        result = solve_model(_model(fixed_dofs=_fixed_triangle(), loads=[{"node": 4, "dof": "UX", "value": 1.0}]), enforce_policy=False)
        return ExecutionOutput({"status": result.status, "max_displacement": result.max_displacement})
    if case_id == "WP08-BODY-FORCE":
        model = _model()
        integrated = DistributedLoadIntegrator().integrate_sparse(model, model.dof_manager(), BodyLoad((0.0, 0.0, -10.0)), 0)
        return ExecutionOutput({"resultant_z": integrated.details["resultant"][2]})
    if case_id == "WP08-TRI-PRESSURE":
        model = _model()
        load = SurfaceLoad(0, "pressure", 2.0, face=1)
        integrated = DistributedLoadIntegrator().integrate_sparse(model, model.dof_manager(), load, 0)
        return ExecutionOutput({"resultant_z": integrated.details["resultant"][2]})
    if case_id == "WP08-QUAD-PRESSURE":
        model = _model()
        load = SurfaceLoad(0, "pressure", 3.0, face=2)
        integrated = DistributedLoadIntegrator().integrate_sparse(model, model.dof_manager(), load, 0)
        return ExecutionOutput({"resultant_y": integrated.details["resultant"][1]})
    if case_id == "WP08-TRACTION":
        model = _model()
        load = SurfaceLoad(0, "surface_traction", (0.0, 0.0, -3.0), face=2)
        integrated = DistributedLoadIntegrator().integrate_sparse(model, model.dof_manager(), load, 0)
        return ExecutionOutput({"resultant_z": integrated.details["resultant"][2]})
    if case_id == "WP08-MULTI-PRISM":
        result = solve_model(_two_prism_model(), enforce_policy=False)
        return ExecutionOutput({"force_balance_relative_error": result.audit.equilibrium["force_balance_relative_error"]})
    if case_id == "WP08-MOMENT-EQUILIBRIUM":
        result = solve_model(_two_prism_model(), enforce_policy=False)
        return ExecutionOutput({"moment_balance_relative_error": result.audit.equilibrium["moment_balance_relative_error"]})
    if case_id == "WP08-PRESCRIBED-DISPLACEMENT":
        model = _model(
            fixed_dofs=_fixed_triangle(),
            multipoint_constraints=[
                {
                    "name": "prescribed_relative_uz",
                    "terms": [
                        {"node": 5, "dof": "UZ", "coefficient": 1.0},
                        {"node": 3, "dof": "UZ", "coefficient": -1.0},
                    ],
                    "value": 1.0e-6,
                }
            ],
        )
        result = solve_model(model, enforce_policy=False)
        return ExecutionOutput({"constraint_violation": result.audit.equilibrium["constraint_forces"]["constraint_violation_max_abs"]})
    if case_id == "WP08-POST":
        model = _model(fixed_dofs=_fixed_triangle(), loads=[{"node": 4, "dof": "UX", "value": 1.0}])
        result = solve_model(model, enforce_policy=False)
        payload = result.to_dict()
        finite = np.isfinite(result.displacements).all() and np.isfinite(float(result.element_results[0]["strain_energy"]))
        return ExecutionOutput({"result_schema": "PASS" if finite and "element_results" in payload else "FAIL"})
    if case_id == "WP08-ENERGY":
        model = _model(fixed_dofs=_fixed_triangle(), loads=[{"node": 4, "dof": "UX", "value": 1.0}])
        result = solve_model(model, enforce_policy=False)
        return ExecutionOutput({"strain_energy": result.element_results[0]["strain_energy"]})
    if case_id == "WP08-BENDING":
        result = solve_model(_two_prism_model(), enforce_policy=False)
        return ExecutionOutput({"max_displacement": result.max_displacement})
    if case_id == "WP08-DISTORTED":
        skew = np.asarray(((1.0, 0.25, 0.0), (0.0, 1.0, 0.15), (0.0, 0.0, 1.0)))
        nodes = (np.asarray(NODES) @ skew.T).tolist()
        result = solve_model(
            _model(nodes=nodes, fixed_dofs=_fixed_triangle(), loads=[{"node": 4, "dof": "UX", "value": 1.0}]),
            enforce_policy=False,
        )
        return ExecutionOutput({"status": result.status})
    if case_id == "WP08-INVERTED":
        inverted = _model(
            elements=[{"type": "WEDGE6", "nodes": [0, 2, 1, 3, 5, 4], "material": "steel"}],
            fixed_dofs=_fixed_triangle(),
        )
        solve_model(inverted, enforce_policy=False)
        return ExecutionOutput({"failure_code": None})
    raise ValueError(f"Unknown WP08 case {case_id!r}.")


def _source_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def run(output: Path) -> dict[str, object]:
    source_sha = _source_sha()
    cases = load_cases(CATALOG)
    runner = VnvRunner(
        source_sha=source_sha,
        environment={"runner": "run_wp08_wedge6", "catalog": CATALOG.name},
    )
    evidence = [runner.run(case, lambda item: _result(item.case_id)) for case in cases]
    failures = [item for item in evidence if item.verdict not in {"PASS", "EXPECTED_FAILURE_PASS", "SKIPPED_EXTERNAL_UNAVAILABLE"}]
    payload = [item.to_dict() for item in evidence]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), indent=2).encode("utf-8"))
    if failures:
        raise RuntimeError("WP08 evidence contains unexpected failures: " + ", ".join(item.case_id for item in failures))
    summary = {
        "source_sha": source_sha,
        "case_count": len(evidence),
        "pass": sum(item.verdict == "PASS" for item in evidence),
        "expected_failure_pass": sum(item.verdict == "EXPECTED_FAILURE_PASS" for item in evidence),
        "skipped_external_unavailable": sum(item.verdict == "SKIPPED_EXTERNAL_UNAVAILABLE" for item in evidence),
        "fail": sum(item.verdict == "FAIL" for item in evidence),
    }
    print(json.dumps(summary, sort_keys=True))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "qualification/0_2_7/vnv_v2/wp08_evidence.json")
    args = parser.parse_args()
    run(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
