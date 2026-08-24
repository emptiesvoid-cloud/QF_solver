"""Reproducible same-mesh HEX8/C3D8 external correlation."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import numpy as np

from solveur.api import solve_model
from solveur.io.manifest import write_json_file
from solveur.verification.calculix_total_lagrangian import parse_last_frd_displacement
from solveur.verification.hex8_tet_benchmark import _hex8_model


STUDY_ID = "VNV-HEX8-CALCULIX-C3D8-001"
DEFAULT_IMAGE = "qf-solver/calculix-nafems13h:2.20"


def run_hex8_calculix_correlation(
    output_dir: str | Path,
    *,
    image: str = DEFAULT_IMAGE,
) -> dict[str, object]:
    """Run QF_solver and CalculiX on the same small, displacement-scaled mesh."""
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    # Scale the stiffness, rather than the load, so qualification diagnostics
    # remain in their normal numerical range while FRD output is well resolved.
    model = _hex8_model(load_value=1.0, young_modulus=210.0e6)
    qf_result = solve_model(model)
    input_path = write_calculix_c3d8_input(output / "hex8_c3d8.inp", model)
    completed = _execute_calculix(output, input_path.stem, image)
    (output / "calculix.log").write_text(completed.stdout + completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError("CalculiX C3D8 failed; see calculix.log")
    frd_path = output / "hex8_c3d8.frd"
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
        "external_solver": {"name": "CalculiX", "version": "2.20", "image": image, "element": "C3D8"},
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
            "One structured unit-cube mesh and one nodal-load case are covered.",
            "The comparison is linear static C3D8 only; modal and dynamic external correlation remain separate gates.",
        ],
    }
    write_json_file(output / "summary.json", summary)
    (output / "report.md").write_text(_report(summary), encoding="utf-8")
    return summary


def write_calculix_c3d8_input(path: str | Path, model: object) -> Path:
    """Write a deterministic C3D8 deck preserving the QF_solver model."""
    target = Path(path)
    material = model.materials[model.elements[0].material]
    lines = ["*HEADING", "QF_solver HEX8 same-mesh CalculiX C3D8 correlation", "*NODE"]
    lines.extend(f"{index + 1},{_number(node[0])},{_number(node[1])},{_number(node[2])}" for index, node in enumerate(model.nodes))
    lines.append("*ELEMENT,TYPE=C3D8,ELSET=EALL")
    lines.extend(f"{index + 1}," + ",".join(str(int(node) + 1) for node in element.nodes) for index, element in enumerate(model.elements))
    lines.extend([
        "*SOLID SECTION,ELSET=EALL,MATERIAL=MAT",
        "*MATERIAL,NAME=MAT",
        "*ELASTIC",
        f"{_number(material['E'])},{_number(material['nu'])}",
        "*BOUNDARY",
    ])
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
    lines = [f"# {summary['study_id']}", "", f"Statut : **{summary['status']}**", "", "| Verification | Ecart | Limite | Statut |", "| --- | ---: | ---: | --- |"]
    lines.extend(f"| {item['id']} | {item['value']:.6e} | {item['limit']:.6e} | {item['status']} |" for item in summary["checks"])
    lines.extend(["", "Même maillage HEX8/C3D8, mêmes BC, matériau et charges nodales.", ""])
    return "\n".join(lines)
