"""Run the controlled WP09 WEDGE6 robustness and external-evidence lot.

The campaign is deliberately additive: it exercises the WP08 public static
slice and V&V infrastructure, while external results are recorded separately
from QF results.  No element or solver implementation is changed here.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
from typing import Any

import numpy as np

from solveur.api import import_gmsh_model, solve_model
from solveur.core.model import FiniteElementModel
from solveur.mesh.quality_contract import assess_element
from solveur.verification.v2 import ExecutionOutput, VnvRunner, load_cases


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "qualification/0_2_7/vnv_v2/wp09_cases.json"
CALCULIX_IMAGE = "qf-solver/calculix-nafems13h:2.20"
CODE_ASTER_HEADLESS_IMAGE = "qf-solver/code-aster-headless:18.1.0"
CALCULIX_IMAGE_DIGEST = "sha256:d9b16f92e61d0dc6fbe857549306c1efc5155c7bdc309c13c6a6f175193d1faf"
CODE_ASTER_IMAGE_DIGEST = "sha256:4629a21a109309bb97fbdc27d750445cc869e151e2e2ed6290f69539614e4435"
CODE_ASTER_HEADLESS_IMAGE_DIGEST = "sha256:df70aa569db65f952cdfd4b1391acac4819d0afa46d0788ee756683b87fac579"
CODE_ASTER_CONTRACT = ROOT / "qualification/0_2_7/external_oracles/wedge6/docker/headless_contract.json"
NODES = np.asarray(
    ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0),
     (0.0, 0.0, 1.0), (1.0, 0.0, 1.0), (0.0, 1.0, 1.0)),
    dtype=float,
)
MATERIALS = {"steel": {"type": "isotropic_3d", "E": 210000.0, "nu": 0.3, "density": 7800.0}}


def _fixed_bottom() -> list[dict[str, Any]]:
    return [{"node": index, "dofs": ["UX", "UY", "UZ"]} for index in range(3)]


def _model(
    *,
    nodes: np.ndarray = NODES,
    elements: list[dict[str, Any]] | None = None,
    fixed_dofs: list[dict[str, Any]] | None = None,
    loads: list[dict[str, Any]] | None = None,
    distributed_loads: list[dict[str, Any]] | None = None,
    multipoint_constraints: list[dict[str, Any]] | None = None,
) -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        nodes=np.asarray(nodes, dtype=float).tolist(),
        elements=elements or [{"type": "WEDGE6", "nodes": list(range(6)), "material": "steel"}],
        materials=MATERIALS,
        fixed_dofs=fixed_dofs,
        loads=loads,
        distributed_loads=distributed_loads,
        multipoint_constraints=multipoint_constraints,
        analysis="linear_static",
    )


def _stacked_model(levels: int, direction: str = "UZ") -> FiniteElementModel:
    base_xy = NODES[:3, :2]
    nodes = np.vstack([np.column_stack([base_xy, np.full(3, float(level))]) for level in range(levels + 1)])
    elements = [
        {
            "type": "WEDGE6",
            "nodes": list(range(3 * level, 3 * (level + 1))) + list(range(3 * (level + 1), 3 * (level + 2))),
            "material": "steel",
        }
        for level in range(levels)
    ]
    top = range(3 * levels, 3 * (levels + 1))
    loads = [{"node": node, "dof": direction, "value": 1.0 / 3.0} for node in top]
    return _model(nodes=nodes, elements=elements, fixed_dofs=_fixed_bottom(), loads=loads)


def _solve_details(model: FiniteElementModel) -> dict[str, Any]:
    result = solve_model(model, enforce_policy=False)
    audit = result.audit.equilibrium
    return {
        "status": str(result.status),
        "node_count": int(model.node_count),
        "element_count": int(len(model.elements)),
        "displacement_norm": float(np.linalg.norm(result.displacements)),
        "max_displacement": float(result.max_displacement),
        "total_reaction": [float(value) for value in audit.get("reaction_resultant", ())],
        "strain_energy": float(sum(float(item.get("strain_energy", 0.0)) for item in result.element_results)),
        "free_relative_residual": float(audit.get("free_relative_residual", float("nan"))),
        "force_balance_relative_error": float(audit.get("force_balance_relative_error", float("nan"))),
        "moment_balance_relative_error": float(audit.get("moment_balance_relative_error", float("nan"))),
        "finite": bool(np.isfinite(result.displacements).all()),
    }


def _quality_details(nodes: np.ndarray) -> dict[str, Any]:
    assessment = assess_element(0, "WEDGE6", nodes)
    return {
        "status": assessment.classification,
        "quality_classification": assessment.classification,
        "metrics": assessment.metrics,
        "warnings": list(assessment.warnings),
        "fatal_findings": list(assessment.fatal_findings),
    }


def _expected_failure(model: FiniteElementModel, expected: str) -> None:
    try:
        result = solve_model(model, enforce_policy=False)
        if str(getattr(result, "status", "PASS")) != "PASS":
            raise RuntimeError(expected)
    except Exception as exc:
        if expected in str(exc):
            raise
        raise RuntimeError(expected) from exc
    raise RuntimeError(f"{expected} was not raised.")


def _execute_internal(case_id: str, expected_failure: str | None) -> dict[str, Any]:
    if case_id == "WP09-AFFINE-TENSION":
        model = _model(fixed_dofs=_fixed_bottom(), loads=[{"node": node, "dof": "UZ", "value": 1.0 / 3.0} for node in (3, 4, 5)])
        return _solve_details(model)
    if case_id == "WP09-COMPRESSION":
        model = _model(fixed_dofs=_fixed_bottom(), loads=[{"node": node, "dof": "UZ", "value": -1.0 / 3.0} for node in (3, 4, 5)])
        return _solve_details(model)
    if case_id == "WP09-SHEAR":
        model = _model(fixed_dofs=_fixed_bottom(), loads=[{"node": node, "dof": "UX", "value": 1.0 / 3.0} for node in (3, 4, 5)])
        return _solve_details(model)
    if case_id == "WP09-BENDING":
        model = _model(fixed_dofs=_fixed_bottom(), loads=[{"node": 3, "dof": "UX", "value": 1.0}])
        return _solve_details(model)
    if case_id == "WP09-TRI-PRESSURE":
        model = _model(fixed_dofs=_fixed_bottom(), distributed_loads=[{"type": "pressure", "element": 0, "face": 1, "value": 2.0}])
        return _solve_details(model)
    if case_id == "WP09-QUAD-PRESSURE":
        model = _model(fixed_dofs=_fixed_bottom(), distributed_loads=[{"type": "pressure", "element": 0, "face": 2, "value": 2.0}])
        return _solve_details(model)
    if case_id == "WP09-PRESCRIBED-DISPLACEMENT":
        model = _model(
            fixed_dofs=_fixed_bottom(),
            multipoint_constraints=[{"name": "prescribed", "terms": [{"node": 5, "dof": "UZ", "coefficient": 1.0}, {"node": 3, "dof": "UZ", "coefficient": -1.0}], "value": 1.0e-3}],
        )
        return _solve_details(model)
    if case_id == "WP09-MULTI-ELEMENT":
        return _solve_details(_stacked_model(2))
    if case_id == "WP09-DISTORTED-VALID":
        transform = np.asarray(((1.0, 0.20, 0.0), (0.05, 1.0, 0.15), (0.0, 0.0, 1.0)))
        return _solve_details(_model(nodes=NODES @ transform.T, fixed_dofs=_fixed_bottom(), loads=[{"node": 3, "dof": "UX", "value": 1.0}]))
    if case_id.startswith("WP09-REFINEMENT-"):
        level = int(case_id.rsplit("-", 1)[1])
        return _solve_details(_stacked_model(level))
    if case_id == "WP09-ASPECT-RATIOS":
        values = []
        for ratio in (1.0, 4.0, 10.0):
            nodes = NODES.copy()
            nodes[:, 0] *= ratio
            values.append({"ratio": ratio, **_solve_details(_model(nodes=nodes, fixed_dofs=_fixed_bottom(), loads=[{"node": 3, "dof": "UZ", "value": 1.0}]))})
        return {"status": "PASS", "aspect_results": values}
    if case_id == "WP09-SKEW":
        transform = np.asarray(((1.0, 0.35, 0.0), (0.0, 1.0, 0.20), (0.0, 0.0, 1.0)))
        return _solve_details(_model(nodes=NODES @ transform.T, fixed_dofs=_fixed_bottom(), loads=[{"node": 3, "dof": "UX", "value": 1.0}]))
    if case_id == "WP09-NEAR-DEGENERATE":
        nodes = NODES.copy()
        nodes[3:, 2] = (1.0e-9, 3.0, 3.0)
        return _quality_details(nodes)
    if case_id in {"WP09-INVERTED", "WP09-WRONG-NODE-ORDER"}:
        connectivity = [0, 2, 1, 3, 5, 4]
        model = _model(elements=[{"type": "WEDGE6", "nodes": connectivity, "material": "steel"}], fixed_dofs=_fixed_bottom())
        _expected_failure(model, expected_failure or "WEDGE6_JACOBIAN_CERTIFICATE_INVALID")
    if case_id == "WP09-MALFORMED-GMSH":
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mesh = root / "invalid.msh"
            setup = root / "invalid.json"
            mesh.write_text("$MeshFormat\nnot-a-gmsh-file\n", encoding="utf-8", newline="\n")
            setup.write_text("{}\n", encoding="utf-8", newline="\n")
            try:
                import_gmsh_model(mesh, setup)
            except Exception as exc:
                raise RuntimeError(expected_failure or "MALFORMED_GMSH_REJECTED") from exc
        raise RuntimeError("MALFORMED_GMSH_REJECTED was not raised.")
    if case_id == "WP09-SINGULAR-BC":
        _expected_failure(_model(loads=[{"node": 3, "dof": "UZ", "value": 1.0}]), expected_failure or "SINGULAR_BC_REJECTED")
    if case_id == "WP09-RIGID-TRANSFORM":
        rotation = np.asarray(((0.0, -1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)))
        baseline = _quality_details(NODES)
        transformed = _quality_details(NODES @ rotation.T + (4.0, -2.0, 7.0))
        if baseline["quality_classification"] != transformed["quality_classification"]:
            raise RuntimeError("RIGID_TRANSFORM_INVARIANCE_FAILED")
        return {"status": "PASS", "baseline": baseline, "transformed": transformed}
    if case_id == "WP09-SCALE":
        baseline = _quality_details(NODES)
        scaled = _quality_details(NODES * 1.0e-9)
        ratio_a = baseline["metrics"]["certified_detj_ratio"]
        ratio_b = scaled["metrics"]["certified_detj_ratio"]
        if baseline["quality_classification"] != scaled["quality_classification"] or not np.isclose(ratio_a, ratio_b):
            raise RuntimeError("SCALE_INVARIANCE_FAILED")
        return {"status": "PASS", "baseline": baseline, "scaled": scaled}
    if case_id == "WP09-DETERMINISTIC-REPLAY":
        first = _solve_details(_model(fixed_dofs=_fixed_bottom(), loads=[{"node": 3, "dof": "UZ", "value": 1.0}]))
        second = _solve_details(_model(fixed_dofs=_fixed_bottom(), loads=[{"node": 3, "dof": "UZ", "value": 1.0}]))
        if first != second:
            raise RuntimeError("DETERMINISTIC_REPLAY_FAILED")
        return {"status": "PASS", "replayed": True, "result": first}
    raise ValueError(f"Unknown WP09 case {case_id!r}.")


def _numeric_rows(text: str, header: str) -> list[tuple[int, float, float, float]]:
    start = text.lower().find(header.lower())
    if start < 0:
        return []
    rows = []
    pattern = re.compile(r"^\s*(\d+)\s+([-+0-9.Ee]+)\s+([-+0-9.Ee]+)\s+([-+0-9.Ee]+)\s*$")
    for line in text[start:].splitlines()[1:]:
        match = pattern.match(line)
        if match is None:
            if rows and line.strip():
                break
            continue
        rows.append((int(match.group(1)), float(match.group(2)), float(match.group(3)), float(match.group(4))))
    return rows


def _relative_error(left: Any, right: Any) -> float | None:
    if left is None or right is None:
        return None
    a = np.asarray(left, dtype=float)
    b = np.asarray(right, dtype=float)
    scale = max(float(np.linalg.norm(a)), float(np.linalg.norm(b)), 1.0e-30)
    return float(np.linalg.norm(a - b) / scale)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _docker_image_id(image: str) -> str | None:
    try:
        return subprocess.check_output(
            ["docker", "image", "inspect", "--format", "{{.Id}}", image],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None


def _calculix_affine(qf: dict[str, Any]) -> dict[str, Any]:
    source_deck = ROOT / "qualification/0_2_7/external_oracles/wedge6/decks/calculix/WP05-A-affine-patch.inp"
    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory)
        deck = work / "wp09_affine.inp"
        text = source_deck.read_text(encoding="utf-8")
        text = text.replace("\nU\n*EL PRINT", "\nU\nRF\n*EL PRINT")
        deck.write_text(text, encoding="utf-8", newline="\n")
        command = ["docker", "run", "--rm", "-v", f"{work}:/work", "-w", "/work", CALCULIX_IMAGE, "wp09_affine"]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=90, check=False)
        if completed.returncode != 0:
            return {"state": "UNAVAILABLE", "reason": completed.stderr.strip()[-1000:] or "CalculiX container failed."}
        output = (work / "wp09_affine.dat").read_text(encoding="utf-8")
        displacements = _numeric_rows(output, "displacements")
        reactions = _numeric_rows(output, "reaction forces")
        if len(displacements) != 6:
            return {"state": "PARTIAL", "reason": "CalculiX completed but displacement output was not parseable."}
        external_u = np.asarray([value for _, x, y, z in displacements for value in (x, y, z)])
        external_reaction = [float(sum(row[index] for row in reactions)) for index in range(1, 4)] if reactions else None
        return {
            "state": "PARTIAL",
            "solver": "CalculiX 2.20 / C3D6",
            "image_digest": CALCULIX_IMAGE_DIGEST,
            "case_id": "WP09-CALCULIX-AFFINE",
            "qf_result": qf,
            "external_result": {
                "displacement": external_u.tolist(),
                "total_reaction": external_reaction,
                "strain_energy": float(0.5 * external_u[11]),
            },
            "relative_error": {
                "displacement": _relative_error(qf["displacements"], external_u),
                "total_reaction": _relative_error(qf["total_reaction"], external_reaction),
                "strain_energy": _relative_error(qf["strain_energy"], 0.5 * external_u[11]),
            },
            "tolerance": 1.0e-6,
            "tolerance_source": "WP05 AFFINE_SAME_MESH candidate; predeclared OWNER_REVIEW_REQUIRED",
            "formulation_compatible": False,
            "comparison_status": "NOT_FORMULATION_COMPATIBLE",
            "comparison_reason": "CalculiX C3D6 reports two integration points (one triangular point times two thickness points), while QF WEDGE6 production uses TRI3_X_GAUSS2 (six points). The large displacement/energy difference is therefore not an apples-to-apples qualification comparison.",
            "verdict": "NOT_FORMULATION_COMPATIBLE",
        }


def _run_code_aster_preflight(qf: dict[str, Any]) -> dict[str, Any]:
    source_dir = ROOT / "qualification/0_2_7/external_oracles/wedge6/decks/code_aster"
    image_id = _docker_image_id(CODE_ASTER_HEADLESS_IMAGE)
    if image_id is None:
        return {
            "state": "UNAVAILABLE",
            "solver": "Code_Aster 18.1.0 / PENTA6",
            "image": CODE_ASTER_HEADLESS_IMAGE,
            "base_image_digest": CODE_ASTER_IMAGE_DIGEST,
            "reason": "The reproducible derived Docker image is not available locally.",
        }
    if image_id != CODE_ASTER_HEADLESS_IMAGE_DIGEST:
        return {
            "state": "UNAVAILABLE",
            "solver": "Code_Aster 18.1.0 / PENTA6",
            "image": CODE_ASTER_HEADLESS_IMAGE,
            "base_image_digest": CODE_ASTER_IMAGE_DIGEST,
            "image_id": image_id,
            "reason": "The local image digest does not match the pinned WP09-R headless contract.",
        }
    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory)
        for source in (
            source_dir / "WP09R-A-penta6-affine.comm",
            source_dir / "WP09R-A-penta6-affine.mail",
            source_dir / "WP09R-A-penta6-affine.export",
        ):
            shutil.copy2(source, work / source.name)
        command = [
            "docker", "run", "--rm", "--mount", f"type=bind,source={work},target=/work", "-w", "/work",
            CODE_ASTER_HEADLESS_IMAGE, "WP09R-A-penta6-affine.export", "--no-mpi",
        ]
        started = time.perf_counter()
        try:
            completed = subprocess.run(command, capture_output=True, text=False, timeout=120, check=False)
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            return {
                "state": "UNAVAILABLE",
                "solver": "Code_Aster 18.1.0 / PENTA6",
                "image": CODE_ASTER_HEADLESS_IMAGE,
                "image_digest": image_id,
                "base_image_digest": CODE_ASTER_IMAGE_DIGEST,
                "reason": f"Headless Docker execution unavailable: {exc}",
            }
        runtime = time.perf_counter() - started
        stdout = (completed.stdout or b"").decode("utf-8", errors="replace")
        stderr = (completed.stderr or b"").decode("utf-8", errors="replace")
        log = (stdout + stderr).encode("utf-8")
        result_path = work / "WP09R-A-penta6-affine.json"
        if completed.returncode != 0 or not result_path.is_file():
            return {
                "state": "FAIL",
                "solver": "Code_Aster 18.1.0 / PENTA6",
                "image": CODE_ASTER_HEADLESS_IMAGE,
                "image_digest": image_id,
                "base_image_digest": CODE_ASTER_IMAGE_DIGEST,
                "exit_code": completed.returncode,
                "runtime_seconds": runtime,
                "stdout_stderr_digest": _sha256_bytes(log),
                "reason": (stdout + stderr).strip()[-1600:],
                "verdict": "FAIL_EXTERNAL",
            }
        raw = json.loads(result_path.read_text(encoding="utf-8"))
        external_result = {
            "displacements": np.asarray(raw["displacement"], dtype=float).reshape(-1).tolist(),
            "total_reaction": [float(value) for value in raw["total_reaction"]],
            "strain_energy": float(raw["strain_energy"]),
        }
        relative_error = {
            "displacement": _relative_error(qf["displacements"], external_result["displacements"]),
            "total_reaction": _relative_error(qf["total_reaction"], external_result["total_reaction"]),
            "strain_energy": _relative_error(qf["strain_energy"], external_result["strain_energy"]),
        }
        tolerance = 1.0e-6
        within_tolerance = all(value is not None and value <= tolerance for value in relative_error.values())
        result_bytes = result_path.read_bytes()
        return {
            "state": "PASS" if within_tolerance else "FAIL",
            "solver": "Code_Aster 18.1.0 / PENTA6",
            "image": CODE_ASTER_HEADLESS_IMAGE,
            "image_digest": image_id,
            "base_image_digest": CODE_ASTER_IMAGE_DIGEST,
            "case_id": "WP09-CODE_ASTER-AFFINE",
            "qf_result": qf,
            "external_result": external_result,
            "relative_error": relative_error,
            "tolerance": tolerance,
            "tolerance_source": "WP05 AFFINE_SAME_MESH predeclared candidate; OWNER_REVIEW_REQUIRED",
            "tolerance_approval_state": "OWNER_REVIEW_REQUIRED",
            "formulation_compatible": True,
            "comparison_status": "PASS_EXTERNAL_CORRELATION_BOUNDED" if within_tolerance else "FAIL_EXTERNAL",
            "comparison_reason": "Same six-node prism, node groups, nodal load, material and primary observables; QF and Code_Aster use the controlled affine deck contract.",
            "deck_digests": {
                name: _sha256_bytes((work / name).read_bytes())
                for name in ("WP09R-A-penta6-affine.comm", "WP09R-A-penta6-affine.mail", "WP09R-A-penta6-affine.export")
            },
            "output_digest": _sha256_bytes(result_bytes),
            "stdout_stderr_digest": _sha256_bytes(log),
            "runtime_seconds": runtime,
            "exit_code": completed.returncode,
            "verdict": "PASS_EXTERNAL_CORRELATION_BOUNDED" if within_tolerance else "FAIL_EXTERNAL",
            "raw_output_contract": str(CODE_ASTER_CONTRACT.relative_to(ROOT)).replace("\\", "/"),
        }


def run(output: Path) -> dict[str, Any]:
    output.parent.mkdir(parents=True, exist_ok=True)
    source_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    cases = load_cases(CATALOG)
    runner = VnvRunner(source_sha=source_sha, environment={"runner": "run_wp09_wedge6", "catalog": CATALOG.name})
    records: list[dict[str, Any]] = []
    for case in cases:
        details: dict[str, Any] = {}

        def execute(item: Any) -> ExecutionOutput:
            details.update(_execute_internal(item.case_id, item.expected_failure))
            return ExecutionOutput({"status": details["status"]})

        evidence = runner.run(case, execute).to_dict()
        if details:
            evidence["observables"].update({key: value for key, value in details.items() if key != "status"})
        evidence["case_category"] = case.route
        records.append(evidence)
    affine_model = _model(fixed_dofs=_fixed_bottom(), loads=[{"node": 3, "dof": "UZ", "value": 1.0}])
    affine_result = solve_model(affine_model, enforce_policy=False)
    affine_audit = affine_result.audit.equilibrium
    affine_qf = {
        "displacements": np.asarray(affine_result.displacements, dtype=float).tolist(),
        "total_reaction": [float(value) for value in affine_audit.get("reaction_resultant", ())],
        "strain_energy": float(sum(float(item.get("strain_energy", 0.0)) for item in affine_result.element_results)),
    }
    external = {"calculix_c3d6": _calculix_affine(affine_qf), "code_aster_penta6": _run_code_aster_preflight(affine_qf)}
    external["code_aster_penta6"]["source_sha"] = source_sha
    external["code_aster_penta6"]["contract"] = str(CODE_ASTER_CONTRACT.relative_to(ROOT)).replace("\\", "/")
    external_artifact = {
        "schema_version": 1,
        "work_package": "WP09-R",
        "gate": "027-G09",
        "source_sha": source_sha,
        "case_id": "WP09-CODE_ASTER-AFFINE",
        "oracle": external["code_aster_penta6"],
        "primary_observables": ["displacement", "total_reaction", "strain_energy"],
        "artifact_classification": "CONTROLLED_PROOF",
        "verdict_boundary": "This is one affine same-mesh external correlation; it does not promote WEDGE6 public maturity.",
    }
    external_artifact_path = output.parent / "wp09r_code_aster_evidence.json"
    external_artifact_path.write_bytes(
        json.dumps(external_artifact, ensure_ascii=True, sort_keys=True, separators=(",", ":"), indent=2).encode("utf-8")
    )
    unexpected = [item for item in records if item["verdict"] not in {"PASS", "EXPECTED_FAILURE_PASS"}]
    summary = {
        "schema_version": 1,
        "work_package": "WP09",
        "gate": "027-G09",
        "source_sha": source_sha,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "contract_refs": ["qualification/0_2_7/external_oracles/wedge6/contract.json", "qualification/0_2_7/external_oracles/wedge6/mapping.json"],
        "wp09r_external_evidence": str(external_artifact_path.relative_to(ROOT)).replace("\\", "/") if external_artifact_path.is_relative_to(ROOT) else external_artifact_path.name,
        "policy": {
            "primary_observables": ["displacement", "total_reaction", "strain_energy"],
            "affine_same_mesh_relative_tolerance": 1.0e-6,
            "affine_tolerance_status": "OWNER_REVIEW_REQUIRED",
            "non_affine_tolerance": "case-specific Owner approval required before execution",
            "post_observation_retuning": False,
            "external_unavailable_is_not_pass": True,
        },
        "internal_cases": records,
        "external": external,
        "summary": {
            "case_count": len(records),
            "pass": sum(item["verdict"] == "PASS" for item in records),
            "expected_failure_pass": sum(item["verdict"] == "EXPECTED_FAILURE_PASS" for item in records),
            "fail": sum(item["verdict"] == "FAIL" for item in records),
            "invalid_evidence": sum(item["verdict"] == "INVALID_EVIDENCE" for item in records),
            "unexpected_failures": [item["case_id"] for item in unexpected],
        },
        "artifact_classification": "CONTROLLED_PROOF",
    }
    output.write_bytes(json.dumps(summary, ensure_ascii=True, sort_keys=True, separators=(",", ":"), indent=2).encode("utf-8"))
    if unexpected:
        raise RuntimeError("WP09 unexpected failures: " + ", ".join(item["case_id"] for item in unexpected))
    print(json.dumps({"cases": len(records), "pass": summary["summary"]["pass"], "expected_failure_pass": summary["summary"]["expected_failure_pass"], "external": {key: value.get("state") for key, value in external.items()}}, sort_keys=True))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "qualification/0_2_7/vnv_v2/wp09_evidence.json")
    args = parser.parse_args()
    run(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
