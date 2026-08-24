"""Reproducible same-mesh HEX20/C3D20 external correlation."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import numpy as np

from solveur.api import solve_model
from solveur.core.model import FiniteElementModel
from solveur.io.manifest import write_json_file
from solveur.verification.calculix_total_lagrangian import parse_last_frd_displacement


STUDY_ID = "VNV-HEX20-CALCULIX-C3D20-STATIC-001"
DEFAULT_IMAGE = "qf-solver/calculix-nafems13h:2.20"
# QF_solver follows Gmsh's edge order.  CalculiX C3D20 follows the Abaqus
# convention: four bottom edges, four top edges, then four vertical edges.
_CALCULIX_C3D20_NODE_ORDER = (0, 1, 2, 3, 4, 5, 6, 7, 8, 11, 13, 9, 16, 18, 19, 17, 10, 12, 14, 15)


def run_hex20_calculix_correlation(
    output_dir: str | Path,
    *,
    image: str = DEFAULT_IMAGE,
) -> dict[str, object]:
    """Run QF_solver and CalculiX on the same one-element HEX20 mesh."""
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    model = _hex20_model(load_value=1.0, young_modulus=210.0e6)
    qf_result = solve_model(model)
    input_path = write_calculix_c3d20_input(output / "hex20_c3d20.inp", model)
    completed = _execute_calculix(output, input_path.stem, image)
    (output / "calculix.log").write_text(completed.stdout + completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError("CalculiX C3D20 failed; see calculix.log")
    frd_path = output / "hex20_c3d20.frd"
    if not frd_path.is_file():
        raise RuntimeError(f"CalculiX did not produce {frd_path}")
    calculix = parse_last_frd_displacement(frd_path, len(model.nodes))
    qf = np.asarray(qf_result.displacements, dtype=float).reshape((-1, 3))
    difference = float(np.linalg.norm(qf - calculix) / max(np.linalg.norm(calculix), np.finfo(float).tiny))
    qf_tip = qf[1]
    calculix_tip = calculix[1]
    tip_difference = float(np.linalg.norm(qf_tip - calculix_tip) / max(np.linalg.norm(calculix_tip), np.finfo(float).tiny))
    checks = [
        _check("full_displacement_relative_difference", difference, 0.01),
        _check("loaded_node_relative_difference", tip_difference, 0.01),
    ]
    summary: dict[str, object] = {
        "study_id": STUDY_ID,
        "status": "PASS_EXTERNAL_CORRELATION" if all(item["status"] == "PASS" for item in checks) else "FAIL",
        "external_solver": {"name": "CalculiX", "version": "2.20", "image": image, "element": "C3D20"},
        "same_mesh": True,
        "same_boundary_conditions": True,
        "same_material": True,
        "same_nodal_loads": True,
        "nodes": len(model.nodes),
        "elements": len(model.elements),
        "dofs": int(qf.size),
        "qf_solver": {"max_displacement": float(np.max(np.abs(qf))), "loaded_node": qf_tip.tolist()},
        "calculix": {"max_displacement": float(np.max(np.abs(calculix))), "loaded_node": calculix_tip.tolist()},
        "checks": checks,
        "input_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        "limitations": [
            "One structured unit-cube mesh and one linear static nodal-load case are covered.",
            "Modal, dynamic, J2 and multi-model external correlations remain separate gates.",
        ],
    }
    write_json_file(output / "summary.json", summary)
    (output / "report.md").write_text(_report(summary), encoding="utf-8")
    return summary


def write_calculix_c3d20_input(path: str | Path, model: FiniteElementModel) -> Path:
    """Write a deterministic C3D20 deck preserving QF_solver ordering."""
    target = Path(path)
    material = model.materials[model.elements[0].material]
    lines = ["*HEADING", "QF_solver HEX20 same-mesh CalculiX C3D20 correlation", "*NODE"]
    lines.extend(f"{index + 1},{_number(node[0])},{_number(node[1])},{_number(node[2])}" for index, node in enumerate(model.nodes))
    lines.append("*ELEMENT,TYPE=C3D20,ELSET=EALL")
    for index, element in enumerate(model.elements):
        ordered_nodes = [element.nodes[position] for position in _CALCULIX_C3D20_NODE_ORDER]
        connectivity = [str(index + 1), *(str(int(node) + 1) for node in ordered_nodes)]
        # CalculiX accepts at most 16 comma-separated fields per input line.
        lines.append(",".join(connectivity[:16]))
        lines.append(",".join(connectivity[16:]))
    lines.extend(
        [
            "*SOLID SECTION,ELSET=EALL,MATERIAL=MAT",
            "*MATERIAL,NAME=MAT",
            "*ELASTIC",
            f"{_number(material['E'])},{_number(material['nu'])}",
            "*BOUNDARY",
        ]
    )
    component = {"UX": 1, "UY": 2, "UZ": 3}
    for constraint in model.fixed_dofs:
        for dof in constraint.dofs:
            lines.append(f"{constraint.node + 1},{component[dof]},{component[dof]},0.")
    lines.extend(["*STEP", "*STATIC", "0.1,1.0,1.E-8,0.1", "*CLOAD"])
    for load in model.loads:
        lines.append(f"{load.node + 1},{component[load.dof]},{_number(load.value)}")
    lines.extend(["*NODE FILE,FREQUENCY=1", "U", "*END STEP"])
    target.write_text("\n".join(lines) + "\n", encoding="ascii")
    return target


def _hex20_model(*, load_value: float, young_modulus: float) -> FiniteElementModel:
    corners = np.asarray(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [1.0, 0.0, 1.0],
            [1.0, 1.0, 1.0],
            [0.0, 1.0, 1.0],
        ]
    )
    edges = ((0, 1), (0, 3), (0, 4), (1, 2), (1, 5), (2, 3), (2, 6), (3, 7), (4, 5), (4, 7), (5, 6), (6, 7))
    nodes = np.vstack([corners, [(corners[first] + corners[second]) / 2.0 for first, second in edges]])
    return FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": "HEX20", "nodes": list(range(20)), "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "E": young_modulus, "nu": 0.3, "density": 7800.0}},
        fixed_dofs=[{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in (0, 3, 4, 7, 9, 10, 15, 17)],
        loads=[{"node": 1, "dof": "UX", "value": load_value}],
        analysis="linear_static",
    )


def _execute_calculix(work: Path, stem: str, image: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", "run", "--rm", "-v", f"{work}:/work", "-w", "/work", image, stem],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )


def _number(value: object) -> str:
    number = float(value)
    return f"{0.0 if abs(number) < 1.0e-12 else number:.12g}"


def _check(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if np.isfinite(value) and value <= limit else "FAIL"}


def _report(summary: dict[str, object]) -> str:
    lines = [
        f"# {summary['study_id']}",
        "",
        f"Statut : **{summary['status']}**",
        "",
        "Même maillage HEX20/C3D20, mêmes BC, matériau et charges nodales.",
        "",
        "| Vérification | Écart | Limite | Statut |",
        "| --- | ---: | ---: | --- |",
    ]
    lines.extend(f"| {item['id']} | {item['value']:.6e} | {item['limit']:.6e} | {item['status']} |" for item in summary["checks"])
    return "\n".join(lines) + "\n"
