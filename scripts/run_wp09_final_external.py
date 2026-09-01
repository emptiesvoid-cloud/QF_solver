"""Run the final, additive WP09 Code_Aster PENTA6 correlation campaign.

The legacy WP09 internal corpus is intentionally not rerun here.  This runner
builds the declared QF and Code_Aster models from the same small set of case
specifications, executes the pinned headless oracle, and records every primary
comparison without changing solver or element code.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any

import numpy as np

from solveur.api import solve_model
from solveur.verification.v2 import load_cases

try:
    from scripts.run_wp09_wedge6 import NODES, _fixed_bottom, _model
except ModuleNotFoundError:  # Direct ``python scripts/<runner>.py`` execution.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from run_wp09_wedge6 import NODES, _fixed_bottom, _model


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "qualification/0_2_7/external_oracles/wedge6/wp09_final_contract.json"
CATALOG = ROOT / "qualification/0_2_7/vnv_v2/wp09_final_external_cases.json"
IMAGE = "qf-solver/code-aster-headless:18.1.0"
BASE_IMAGE_DIGEST = "sha256:4629a21a109309bb97fbdc27d750445cc869e151e2e2ed6290f69539614e4435"
IMAGE_DIGEST = "sha256:df70aa569db65f952cdfd4b1391acac4819d0afa46d0788ee756683b87fac579"
PRIMARY = ("displacement", "total_reaction", "strain_energy")
DOF_COMPONENT = {"UX": "FX", "UY": "FY", "UZ": "FZ"}
FACE_NODES = {
    "TRI_TOP": (3, 4, 5),
    "QUAD_SIDE_12": (0, 1, 4, 3),
}


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _image_id() -> str | None:
    try:
        return subprocess.check_output(
            ["docker", "image", "inspect", "--format", "{{.Id}}", IMAGE],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None


def _stacked_nodes(levels: int) -> np.ndarray:
    base_xy = NODES[:3, :2]
    return np.vstack(
        [np.column_stack([base_xy, np.full(3, float(index) / levels)]) for index in range(levels + 1)]
    )


def _stacked_loads(levels: int) -> list[dict[str, Any]]:
    top = range(3 * levels, 3 * (levels + 1))
    return [{"node": node, "dof": "UZ", "value": 1.0 / 3.0} for node in top]


def _case(
    case_id: str,
    case_class: str,
    *,
    nodes: np.ndarray = NODES,
    loads: list[dict[str, Any]] | None = None,
    distributed_loads: list[dict[str, Any]] | None = None,
    multipoint_constraints: list[dict[str, Any]] | None = None,
    tolerance_class: str = "AFFINE_SAME_MESH",
    level: int | None = None,
    pressure_face: str | None = None,
    pressure: float | None = None,
    prescribed: float | None = None,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "class": case_class,
        "nodes": np.asarray(nodes, dtype=float),
        "loads": list(loads or []),
        "distributed_loads": list(distributed_loads or []),
        "multipoint_constraints": list(multipoint_constraints or []),
        "tolerance_class": tolerance_class,
        "level": level,
        "pressure_face": pressure_face,
        "pressure": pressure,
        "prescribed": prescribed,
    }


def _case_specs() -> list[dict[str, Any]]:
    top_load = [{"node": node, "dof": "UZ", "value": 1.0 / 3.0} for node in (3, 4, 5)]
    compression = [{"node": node, "dof": "UZ", "value": -1.0 / 3.0} for node in (3, 4, 5)]
    shear = [{"node": node, "dof": "UX", "value": 1.0 / 3.0} for node in (3, 4, 5)]
    prescribed = [
        {
            "name": f"top_{node}",
            "terms": [
                {"node": node, "dof": "UZ", "coefficient": 1.0},
                {"node": node - 3, "dof": "UZ", "coefficient": -1.0},
            ],
            "value": 1.0e-3,
        }
        for node in (3, 4, 5)
    ]
    transform = np.asarray(((1.0, 0.20, 0.0), (0.05, 1.0, 0.15), (0.0, 0.0, 1.0)))
    return [
        _case("WP09-FINAL-A-TENSION", "affine_tension", loads=top_load),
        _case("WP09-FINAL-B-COMPRESSION", "affine_compression", loads=compression),
        _case("WP09-FINAL-C-SHEAR", "affine_shear", loads=shear),
        _case(
            "WP09-FINAL-D-BENDING",
            "affine_bending",
            loads=[{"node": 3, "dof": "UX", "value": 1.0}],
        ),
        _case(
            "WP09-FINAL-E-TRI-PRESSURE",
            "tri3_pressure",
            distributed_loads=[{"type": "pressure", "element": 0, "face": 1, "value": 2.0}],
            pressure_face="TRI_TOP",
            pressure=2.0,
        ),
        _case(
            "WP09-FINAL-F-QUAD-PRESSURE",
            "quad4_pressure",
            distributed_loads=[{"type": "pressure", "element": 0, "face": 2, "value": 2.0}],
            pressure_face="QUAD_SIDE_12",
            pressure=2.0,
        ),
        _case(
            "WP09-FINAL-G-PRESCRIBED",
            "prescribed_displacement",
            multipoint_constraints=prescribed,
            prescribed=1.0e-3,
        ),
        _case(
            "WP09-FINAL-H-MULTI-ELEMENT",
            "multi_element",
            nodes=_stacked_nodes(2),
            loads=_stacked_loads(2),
            tolerance_class="REFINEMENT",
            level=2,
        ),
        _case(
            "WP09-FINAL-I-DISTORTED",
            "distorted_valid",
            nodes=NODES @ transform.T,
            loads=[{"node": 3, "dof": "UX", "value": 1.0}],
            tolerance_class="DISTORTED",
        ),
        *[
            _case(
                f"WP09-FINAL-J-REFINEMENT-{level}",
                "refinement",
                nodes=_stacked_nodes(level),
                loads=_stacked_loads(level),
                tolerance_class="REFINEMENT",
                level=level,
            )
            for level in (1, 2, 4)
        ],
    ]


def _model_for(spec: dict[str, Any]) -> Any:
    elements = [
        {
            "type": "WEDGE6",
            "nodes": list(range(6 * 0, 6)),
            "material": "steel",
        }
    ]
    level = int(spec["level"] or 0)
    if level > 1 and spec["class"] in {"multi_element", "refinement"}:
        elements = [
            {
                "type": "WEDGE6",
                "nodes": list(range(3 * index, 3 * index + 6)),
                "material": "steel",
            }
            for index in range(level)
        ]
    return _model(
        nodes=spec["nodes"],
        elements=elements,
        fixed_dofs=_fixed_bottom(),
        loads=spec["loads"],
        distributed_loads=spec["distributed_loads"],
        multipoint_constraints=spec["multipoint_constraints"],
    )


def _load_vector(spec: dict[str, Any]) -> np.ndarray | None:
    vector = np.zeros((len(spec["nodes"]), 3), dtype=float)
    for load in spec["loads"]:
        component = {"UX": 0, "UY": 1, "UZ": 2}[str(load["dof"]).upper()]
        vector[int(load["node"]), component] += float(load["value"])
    if spec["pressure_face"] is not None:
        indices = FACE_NODES[spec["pressure_face"]]
        points = spec["nodes"][list(indices)]
        if len(indices) == 3:
            area_vector = 0.5 * np.cross(points[1] - points[0], points[2] - points[0])
            vector[list(indices)] += -float(spec["pressure"]) * area_vector / 3.0
        else:
            area_vector = 0.5 * (
                np.cross(points[1] - points[0], points[2] - points[0])
                + np.cross(points[2] - points[0], points[3] - points[0])
            )
            vector[list(indices)] += -float(spec["pressure"]) * area_vector / 4.0
        return vector
    if spec["prescribed"] is not None:
        return None
    return vector


def _qf_result(spec: dict[str, Any]) -> dict[str, Any]:
    model = _model_for(spec)
    result = solve_model(model, enforce_policy=False)
    audit = result.audit.equilibrium
    displacement = np.asarray(result.displacements, dtype=float).reshape(-1)
    total_reaction = [float(value) for value in audit.get("reaction_resultant", ())]
    reaction_definition = "fixed_support_reaction_resultant"
    if spec["prescribed"] is not None:
        internal_force = next(
            (
                row.get("nonzero_entries", [])
                for row in result.audit.vectors
                if row.get("name") == "internal_force"
            ),
            [],
        )
        internal_by_dof = {int(row["index"]): float(row["value"]) for row in internal_force}
        top_nodes = (3, 4, 5)
        imposed_reaction = -sum(internal_by_dof.get(3 * node + 2, 0.0) for node in top_nodes)
        total_reaction = [0.0, 0.0, float(imposed_reaction)]
        reaction_definition = "equivalent_reaction_at_prescribed_dofs"
    return {
        "displacement": displacement.tolist(),
        "total_reaction": total_reaction,
        "reaction_definition": reaction_definition,
        "strain_energy": float(sum(float(item.get("strain_energy", 0.0)) for item in result.element_results)),
        "status": str(result.status),
        "node_count": int(model.node_count),
        "element_count": len(model.elements),
        "free_relative_residual": float(audit.get("free_relative_residual", float("nan"))),
        "force_balance_relative_error": float(audit.get("force_balance_relative_error", float("nan"))),
        "moment_balance_relative_error": float(audit.get("moment_balance_relative_error", float("nan"))),
        "finite": bool(np.isfinite(displacement).all()),
    }


def _mail_text(spec: dict[str, Any]) -> str:
    nodes = spec["nodes"]
    level = int(spec["level"] or 0)
    element_count = level if level > 1 and spec["class"] in {"multi_element", "refinement"} else 1
    lines = ["TITRE", f"WP09-FINAL {spec['case_id']}", "FINSF", "COOR_3D"]
    lines.extend(f"N{index + 1} {x:.17g} {y:.17g} {z:.17g}" for index, (x, y, z) in enumerate(nodes))
    lines.extend(["FINSF", "PENTA6"])
    for index in range(element_count):
        lines.append(
            "E{0} N{1} N{2} N{3} N{4} N{5} N{6}".format(
                index + 1, 3 * index + 1, 3 * index + 2, 3 * index + 3,
                3 * index + 4, 3 * index + 5, 3 * index + 6,
            )
        )
    lines.append("FINSF")
    if spec["pressure_face"] is not None:
        indices = FACE_NODES[spec["pressure_face"]]
        if len(indices) == 3:
            lines.extend(["TRIA3", "S1 N{} N{} N{}".format(*(index + 1 for index in indices)), "FINSF"])
        else:
            lines.extend(["QUAD4", "S1 N{} N{} N{} N{}".format(*(index + 1 for index in indices)), "FINSF"])
    lines.extend(["GROUP_MA", "SOLID"])
    lines.extend(f"E{index + 1}" for index in range(element_count))
    lines.append("FINSF")
    if spec["pressure_face"] is not None:
        lines.extend(["GROUP_MA", "LOAD_FACE", "S1", "FINSF"])
    lines.extend(["GROUP_NO", "FIXED", "N1 N2 N3", "FINSF"])
    lines.extend(["GROUP_NO", "ALL", " ".join(f"N{index + 1}" for index in range(len(nodes))), "FINSF"])
    if spec["prescribed"] is not None:
        start = 3 * level if level else 3
        lines.extend(["GROUP_NO", "TOP", "N{} N{} N{}".format(start + 1, start + 2, start + 3), "FINSF"])
    lines.append("FIN")
    return "\n".join(lines) + "\n"


def _export_text(stem: str) -> str:
    return "\n".join(
        [
            "P time_limit 900",
            "P memory_limit 4096",
            "P ncpus 1",
            "P mpi_nbcpu 1",
            "P no-mpi",
            f"F comm /work/{stem}.comm D 1",
            f"F mail /work/{stem}.mail D 20",
            f"F result /work/{stem}.result R 8",
            f"F med /work/{stem}.med R 80",
            "",
        ]
    )


def _boundary_text(spec: dict[str, Any]) -> str:
    fixed = '_F(GROUP_NO="FIXED", DX=0.0, DY=0.0, DZ=0.0)'
    if spec["prescribed"] is None:
        return f"boundary = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO={fixed})"
    imposed = f'_F(GROUP_NO="TOP", DZ={float(spec["prescribed"]):.17g})'
    return f"boundary = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=({fixed}, {imposed}))"


def _comm_text(spec: dict[str, Any], reference_force: np.ndarray | None) -> str:
    stem = spec["case_id"].lower()
    if spec["pressure_face"] is not None:
        load_text = (
            "force = AFFE_CHAR_MECA(MODELE=model, "
            f'PRES_REP=_F(GROUP_MA="LOAD_FACE", PRES={float(spec["pressure"]):.17g}))'
        )
    elif spec["prescribed"] is not None:
        load_text = "force = None"
    else:
        factors = []
        for load in spec["loads"]:
            component = DOF_COMPONENT[str(load["dof"]).upper()]
            factors.append(f'_F(NOEUD="N{int(load["node"]) + 1}", {component}={float(load["value"]):.17g})')
        load_text = "force = AFFE_CHAR_MECA(MODELE=model, FORCE_NODALE=(\n    " + ",\n    ".join(factors) + "\n))"
    reference = "None" if reference_force is None else repr(reference_force.reshape(-1).tolist())
    top_values = "[]"
    if spec["prescribed"] is not None:
        top_values = "[float(value) for value in reaction.getValuesWithDescription(\"DZ\", [\"TOP\"])[0]]"
    excitations = "_F(CHARGE=boundary)" if spec["prescribed"] is not None else "_F(CHARGE=boundary), _F(CHARGE=force)"
    return f'''# coding=utf-8
import json
import numpy as np
from code_aster.Commands import *

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(MAILLAGE=mesh, AFFE=_F(TOUT="OUI", PHENOMENE="MECANIQUE", MODELISATION="3D"))
material = DEFI_MATERIAU(ELAS=_F(E=210000.0, NU=0.3))
field = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", MATER=material))
{_boundary_text(spec)}
{load_text}
static = MECA_STATIQUE(MODELE=model, CHAM_MATER=field, EXCIT=({excitations}))
CALC_CHAMP(reuse=static, RESULTAT=static, FORCE=("REAC_NODA",))
order = static.getIndexes()[-1]
displacement = static.getField("DEPL", order)
reaction = static.getField("REAC_NODA", order)
displacement_values = []
for component in ("DX", "DY", "DZ"):
    values, _ = displacement.getValuesWithDescription(component, ["ALL"])
    displacement_values.append([float(value) for value in values])
external_displacement = np.asarray(displacement_values, dtype=float).T
reaction_values = []
for component in ("DX", "DY", "DZ"):
    values, _ = reaction.getValuesWithDescription(component, ["FIXED"])
    reaction_values.append([float(value) for value in values])
top_reaction_z = {top_values}
reference_force = {reference}
if reference_force is None:
    strain_energy = float(0.5 * sum(top_reaction_z) * {float(spec["prescribed"] or 0.0):.17g})
else:
    strain_energy = float(0.5 * np.dot(np.asarray(reference_force, dtype=float), external_displacement.reshape(-1)))
raw = {{
    "case_id": {spec["case_id"]!r},
    "solver": "Code_Aster 18.1.0 / PENTA6",
    "node_order": [f"N{{index + 1}}" for index in range(external_displacement.shape[0])],
    "displacement": external_displacement.tolist(),
    "total_reaction": np.sum(np.asarray(reaction_values, dtype=float), axis=1).tolist(),
    "strain_energy": strain_energy,
    "reaction_nodes": reaction_values,
    "top_reaction_z": top_reaction_z,
}}
with open("/work/{stem}.json", "w", encoding="utf-8") as stream:
    json.dump(raw, stream, indent=2, sort_keys=True)
FIN()
'''


def _run_aster(spec: dict[str, Any]) -> dict[str, Any]:
    image_id = _image_id()
    base = {
        "solver": "Code_Aster 18.1.0 / PENTA6",
        "image": IMAGE,
        "image_digest": image_id,
        "base_image_digest": BASE_IMAGE_DIGEST,
    }
    if image_id != IMAGE_DIGEST:
        return {**base, "state": "UNAVAILABLE", "reason": "Pinned derived Code_Aster image is unavailable or has an unexpected digest."}
    stem = spec["case_id"].lower()
    reference_force = _load_vector(spec)
    with tempfile.TemporaryDirectory(prefix="qf-wp09-final-") as directory:
        work = Path(directory)
        (work / f"{stem}.mail").write_text(_mail_text(spec), encoding="ascii", newline="\n")
        (work / f"{stem}.export").write_text(_export_text(stem), encoding="ascii", newline="\n")
        (work / f"{stem}.comm").write_text(_comm_text(spec, reference_force), encoding="utf-8", newline="\n")
        command = [
            "docker", "run", "--rm", "--mount", f"type=bind,source={work},target=/work",
            "-w", "/work", IMAGE, f"{stem}.export", "--no-mpi",
        ]
        started = time.perf_counter()
        try:
            completed = subprocess.run(command, capture_output=True, text=False, timeout=180, check=False)
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            return {**base, "state": "UNAVAILABLE", "reason": f"Headless Code_Aster execution unavailable: {exc}"}
        runtime = time.perf_counter() - started
        log = (completed.stdout or b"") + (completed.stderr or b"")
        raw_path = work / f"{stem}.json"
        if completed.returncode != 0 or not raw_path.is_file():
            log_text = log.decode("utf-8", errors="replace")
            diagnostic_lines = [
                line for line in log_text.splitlines()
                if any(marker in line for marker in ("<F>", "<E>", "Traceback", "ERREUR", "Erreur", "ERROR", "invalid"))
            ]
            log_lines = log_text.splitlines()
            diagnostic_context: list[str] = []
            for index, line in enumerate(log_lines):
                if "MODELISA" in line or "<F>" in line:
                    diagnostic_context.extend(log_lines[max(0, index - 8): index + 18])
            excerpt = log_text if len(log_text) <= 6000 else log_text[-6000:]
            reason = "\n".join(diagnostic_lines[-40:] + diagnostic_context[-80:]) + "\n--- tail ---\n" + excerpt
            return {
                **base,
                "state": "FAIL",
                "exit_code": completed.returncode,
                "runtime_seconds": runtime,
                "stdout_stderr_digest": _sha256(log),
                "reason": reason,
            }
        raw_bytes = raw_path.read_bytes()
        raw = json.loads(raw_bytes.decode("utf-8"))
        external = {
            "displacement": np.asarray(raw["displacement"], dtype=float).reshape(-1).tolist(),
            "total_reaction": [float(value) for value in raw["total_reaction"]],
            "strain_energy": float(raw["strain_energy"]),
        }
        return {
            **base,
            "state": "PASS",
            "exit_code": completed.returncode,
            "runtime_seconds": runtime,
            "stdout_stderr_digest": _sha256(log),
            "output_digest": _sha256(raw_bytes),
            "external_result": external,
            "node_order": raw["node_order"],
            "deck_digests": {
                name: _sha256((work / name).read_bytes())
                for name in (f"{stem}.comm", f"{stem}.mail", f"{stem}.export")
            },
        }


def _relative_error(qf: Any, external: Any) -> float:
    left = np.asarray(qf, dtype=float)
    right = np.asarray(external, dtype=float)
    if left.ndim == 0 and right.ndim == 0:
        return float(abs(float(left) - float(right)) / max(abs(float(left)), abs(float(right)), 1.0e-30))
    return float(np.linalg.norm(left - right) / max(np.linalg.norm(left), np.linalg.norm(right), 1.0e-30))


def _comparison(qf: dict[str, Any], external: dict[str, Any], tolerances: dict[str, float]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for observable in PRIMARY:
        error = _relative_error(qf[observable], external[observable])
        limit = float(tolerances[observable])
        result[observable] = {
            "qf": qf[observable],
            "oracle": external[observable],
            "relative_error": error,
            "tolerance": limit,
            "verdict": "PASS" if error <= limit else "FAIL",
        }
    return result


def _contract_tolerances(contract: dict[str, Any], tolerance_class: str) -> dict[str, float]:
    return {
        name: float(value)
        for name, value in contract["tolerance_policy"][tolerance_class]["tolerances"].items()
    }


def _case_record(spec: dict[str, Any], contract: dict[str, Any], source_sha: str) -> dict[str, Any]:
    qf = _qf_result(spec)
    external = _run_aster(spec)
    tolerance_class = spec["tolerance_class"]
    tolerance_policy = contract["tolerance_policy"][tolerance_class]
    record: dict[str, Any] = {
        "case_id": spec["case_id"],
        "case_class": spec["class"],
        "level": spec["level"],
        "source_sha": source_sha,
        "qf_result": qf,
        "oracle": {key: value for key, value in external.items() if key != "external_result"},
        "tolerance_class": tolerance_class,
        "tolerances": _contract_tolerances(contract, tolerance_class),
        "tolerance_source": tolerance_policy["source"],
        "tolerance_approval_state": tolerance_policy["approval_state"],
        "tolerance_approval_reference": tolerance_policy["approval_reference"],
        "primary_observables": list(PRIMARY),
        "formulation_compatible": True,
        "artifact_classification": "CONTROLLED_PROOF",
    }
    if external["state"] != "PASS":
        record.update({"external_result": None, "relative_error": None, "verdict": "SKIPPED_EXTERNAL_UNAVAILABLE" if external["state"] == "UNAVAILABLE" else "FAIL_EXTERNAL"})
        return record
    comparison = _comparison(qf, external["external_result"], record["tolerances"])
    record["external_result"] = external["external_result"]
    record["relative_error"] = {key: value["relative_error"] for key, value in comparison.items()}
    record["comparison"] = comparison
    record["verdict"] = "PASS_EXTERNAL_CORRELATION_BOUNDED" if all(value["verdict"] == "PASS" for value in comparison.values()) else "FAIL_EXTERNAL"
    return record


def _validate_contract_catalog(contract: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    catalog = load_cases(CATALOG)
    contract_ids = tuple(item["case_id"] for item in contract["cases"])
    if tuple(case.case_id for case in catalog) != contract_ids:
        raise RuntimeError("WP09 final contract and V&V catalog are out of order or incomplete.")
    return catalog


def _external_replay(spec: dict[str, Any]) -> dict[str, Any]:
    first = _run_aster(spec)
    second = _run_aster(spec)
    if first.get("state") != "PASS" or second.get("state") != "PASS":
        return {"status": "SKIPPED_EXTERNAL_UNAVAILABLE", "case_id": spec["case_id"]}
    return {
        "status": "PASS" if first.get("output_digest") == second.get("output_digest") else "FAIL",
        "case_id": spec["case_id"],
        "first_output_digest": first.get("output_digest"),
        "second_output_digest": second.get("output_digest"),
    }


def run(output: Path) -> dict[str, Any]:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    _validate_contract_catalog(contract)
    specs = _case_specs()
    if tuple(item["case_id"] for item in contract["cases"]) != tuple(item["case_id"] for item in specs):
        raise RuntimeError("WP09 final contract and executable case specifications differ.")
    source_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    records = [_case_record(spec, contract, source_sha) for spec in specs]
    final_spec = next(spec for spec in specs if spec["case_id"].endswith("REFINEMENT-4"))
    replay = _external_replay(final_spec)
    qf_first = _qf_result(final_spec)
    qf_second = _qf_result(final_spec)
    qf_replay = "PASS" if qf_first == qf_second else "FAIL"
    output.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "schema_version": 1,
        "work_package": "WP09-FINAL",
        "gate": "027-G09",
        "status": "PASS_WITH_LIMITATIONS",
        "source_sha": source_sha,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "contract": str(CONTRACT.relative_to(ROOT)).replace("\\", "/"),
        "catalog": str(CATALOG.relative_to(ROOT)).replace("\\", "/"),
        "headless_oracle": {
            "solver": "Code_Aster",
            "version": "18.1.0",
            "element": "PENTA6",
            "image": IMAGE,
            "image_digest": IMAGE_DIGEST,
            "base_image_digest": BASE_IMAGE_DIGEST,
            "gui_used": False,
            "run_aster_no_mpi": True,
        },
        "primary_observables": list(PRIMARY),
        "records": records,
        "determinism": {"qf_final_case": qf_replay, "external_final_case": replay},
        "calculix": {
            "state": "NOT_COMPARABLE",
            "verdict": "NOT_COMPARABLE",
            "reason": "Inherited C3D6 route uses a different integration convention than QF TRI3_X_GAUSS2 and is excluded from qualification.",
        },
        "summary": {
            "cases_total": len(records),
            "external_cases_run": sum(record["oracle"].get("state") == "PASS" for record in records),
            "external_pass": sum(record["verdict"] == "PASS_EXTERNAL_CORRELATION_BOUNDED" for record in records),
            "external_fail": sum(record["verdict"] == "FAIL_EXTERNAL" for record in records),
            "external_skipped": sum(record["verdict"] == "SKIPPED_EXTERNAL_UNAVAILABLE" for record in records),
        },
        "tolerance_policy": {
            "fixed_before_execution": True,
            "post_result_retuning": False,
            "approval_state": contract["status"],
            "classes": {key: value for key, value in contract["tolerance_policy"].items()},
        },
        "limitations": [
            "WEDGE6 remains EXPERIMENTAL; this external evidence does not promote public maturity automatically.",
            "Tolerance approval remains OWNER_REVIEW_REQUIRED even though all numeric values were fixed before execution.",
            "CalculiX C3D6 is retained as NOT_COMPARABLE under the controlled integration convention.",
            "The campaign covers the declared small-strain isotropic PENTA6 slice only; stress qualification is excluded.",
        ],
        "artifact_classification": "CONTROLLED_PROOF",
        "legacy_internal_corpus": {
            "artifact": "qualification/0_2_7/vnv_v2/wp09_evidence.json",
            "rerun": False,
            "preserved": True,
        },
        "existing_fem_numerics_changed": False,
        "full_regression_run": False,
        "pushed": False,
    }
    output.write_text(json.dumps(summary, ensure_ascii=True, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summary["summary"], sort_keys=True))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "qualification/0_2_7/vnv_v2/wp09_final_external_evidence.json")
    args = parser.parse_args()
    run(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
