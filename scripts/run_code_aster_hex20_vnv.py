"""Run a same-mesh QF_solver HEX20 / Code_Aster HEXA20 static correlation."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

from solveur.api import solve_model
from solveur.io.manifest import write_json_file
from solveur.verification.hex20_calculix import _hex20_model


STUDY_ID = "VNV-HEX20-CODE-ASTER-HEXA20-STATIC-001"
DEFAULT_IMAGE = "simvia/code_aster:18.1.0"
CODE_ASTER_PROFILE = (
    "/opt/spack/opt/spack/linux-zen/code-aster-18.1.0-"
    "owafurl325k3dbxls3s645zyfmvakxsg"
)
_CODE_ASTER_HEXA20_NODE_ORDER = (0, 1, 2, 3, 4, 5, 6, 7, 8, 11, 13, 9, 10, 12, 14, 15, 16, 18, 19, 17)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    args = parser.parse_args()
    summary = run(args.output, image=args.image)
    print(f"Code_Aster HEX20 correlation: {summary['status']}")
    return 0 if summary["status"] == "PASS_EXTERNAL_CORRELATION" else 1


def run(output_dir: str | Path, *, image: str = DEFAULT_IMAGE) -> dict[str, Any]:
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    model = _hex20_model(load_value=1.0, young_modulus=210.0e6)
    qf_result = solve_model(model)
    root = [index for index, point in enumerate(model.nodes) if abs(float(point[0])) < 1.0e-12]
    load_node = 1
    stem = "hex20_hexa20"
    mesh = output / f"{stem}.mail"
    comm = output / f"{stem}.comm"
    mesh.write_text(_mesh_text(model.nodes, model.elements, root, load_node), encoding="ascii")
    comm.write_text(_comm_text(model.materials[model.elements[0].material], load_node), encoding="utf-8")
    completed = _run_code_aster(output, stem, image)
    (output / "code_aster.log").write_text(completed.stdout + completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError("Code_Aster HEXA20 failed; see code_aster.log")
    raw_path = output / "code_aster_raw.json"
    if not raw_path.is_file():
        raise RuntimeError("Code_Aster completed without code_aster_raw.json")
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    qf = np.asarray(qf_result.displacements, dtype=float).reshape((-1, 3))
    qf_loaded = qf[load_node]
    aster_loaded = np.asarray(raw["loaded_node_displacement"], dtype=float)
    difference = float(np.linalg.norm(qf_loaded - aster_loaded) / max(np.linalg.norm(aster_loaded), np.finfo(float).tiny))
    checks = [{"id": "loaded_node_relative_difference", "value": difference, "limit": 0.01, "status": "PASS" if np.isfinite(difference) and difference <= 0.01 else "FAIL"}]
    summary: dict[str, Any] = {
        "study_id": STUDY_ID,
        "status": "PASS_EXTERNAL_CORRELATION" if checks[0]["status"] == "PASS" else "FAIL",
        "external_solver": {"name": "Code_Aster", "version": "18.1.0", "image": image, "element": "3D/HEXA20"},
        "same_mesh": True,
        "same_boundary_conditions": True,
        "same_material": True,
        "same_nodal_loads": True,
        "nodes": len(model.nodes),
        "elements": len(model.elements),
        "dofs": int(qf.size),
        "qf_solver": {"loaded_node_index": load_node, "loaded_node_displacement": qf_loaded.tolist()},
        "code_aster": {"loaded_node_index": load_node, "loaded_node_displacement": aster_loaded.tolist()},
        "checks": checks,
        "input_sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in (mesh, comm)},
        "limitations": [
            "One structured unit-cube and one linear static nodal-load case are covered.",
            "The Code_Aster comparison is an external correlation gate; J2 and multi-model external campaigns remain open.",
        ],
    }
    write_json_file(output / "summary.json", summary)
    (output / "report.md").write_text(_report(summary), encoding="utf-8")
    return summary


def _mesh_text(nodes: Any, elements: Any, root: list[int], load_node: int) -> str:
    lines = ["TITRE", "QF_solver HEX20 same-mesh Code_Aster HEXA20 correlation", "FINSF", "COOR_3D"]
    lines.extend(f"N{i + 1} {float(node[0]):.16g} {float(node[1]):.16g} {float(node[2]):.16g}" for i, node in enumerate(nodes))
    lines.extend(["FINSF", "HEXA20"])
    lines.extend(
        f"M{i + 1} "
        + " ".join(f"N{int(element.nodes[position]) + 1}" for position in _CODE_ASTER_HEXA20_NODE_ORDER)
        for i, element in enumerate(elements)
    )
    lines.extend(["FINSF", "GROUP_MA", "SOLID", *(f"M{i}" for i in range(1, len(elements) + 1)), "FINSF"])
    lines.extend(["GROUP_NO", "ROOT", *(f"N{node + 1}" for node in root), "FINSF"])
    lines.extend(["GROUP_NO", "LOAD", f"N{load_node + 1}", "FINSF", "FIN"])
    return "\n".join(lines) + "\n"


def _comm_text(material: dict[str, Any], load_node: int) -> str:
    return f'''# coding=utf-8
import json
from code_aster.Commands import *

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", PHENOMENE="MECANIQUE", MODELISATION="3D"))
material = DEFI_MATERIAU(ELAS=_F(E={float(material['E']):.16g}, NU={float(material['nu']):.16g}))
field = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", MATER=material))
boundary = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=_F(GROUP_NO="ROOT", DX=0.0, DY=0.0, DZ=0.0))
force = AFFE_CHAR_MECA(MODELE=model, FORCE_NODALE=_F(NOEUD="N{load_node + 1}", FX=1.0))
static = MECA_STATIQUE(MODELE=model, CHAM_MATER=field, EXCIT=(_F(CHARGE=boundary), _F(CHARGE=force)))
field = static.getField("DEPL", 1)
dx, _ = field.getValuesWithDescription("DX", ["LOAD"])
dy, _ = field.getValuesWithDescription("DY", ["LOAD"])
dz, _ = field.getValuesWithDescription("DZ", ["LOAD"])
with open("/work/code_aster_raw.json", "w", encoding="utf-8") as stream:
    json.dump({{"loaded_node_displacement": [float(dx[0]), float(dy[0]), float(dz[0])]}}, stream, indent=2)
FIN()
'''


def _run_code_aster(work: Path, stem: str, image: str) -> subprocess.CompletedProcess[str]:
    serial = (
        f"export RUNASTER_ROOT={CODE_ASTER_PROFILE}; source {CODE_ASTER_PROFILE}/share/aster/profile.sh; "
        "export PYTHONPATH=$(find /opt/spack/opt/spack/linux-zen -type d -path '*/lib/python3.11/site-packages' | paste -sd: -):${PYTHONPATH:-}; "
        r"export LD_LIBRARY_PATH=$(find /opt/spack/opt/spack/linux-zen -type d \( -name lib -o -name lib64 \) | paste -sd: -):${LD_LIBRARY_PATH:-}; "
        f"python3 /work/{stem}.comm --last --link=F::mail::/work/{stem}.mail::D::20 --memory 4096 --tpmax 900 --numthreads 1"
    )
    return subprocess.run(
        ["docker", "run", "--rm", "-v", f"{work}:/work", "--workdir", "/work", "--entrypoint", "/bin/bash", image, "-c", serial],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=1200,
        check=False,
    )


def _report(summary: dict[str, Any]) -> str:
    check = summary["checks"][0]
    return "\n".join(
        [
            f"# {summary['study_id']}",
            "",
            f"Statut : **{summary['status']}**",
            "",
            "Même maillage HEX20/HEXA20, mêmes BC, matériau et charge nodale.",
            "",
            "| Vérification | Écart | Limite | Statut |",
            "| --- | ---: | ---: | --- |",
            f"| {check['id']} | {check['value']:.6e} | {check['limit']:.6e} | {check['status']} |",
            "",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
