"""Run a formulation-compatible Code_Aster branch diagnostic for the HEX8 case."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from run_tl_failure_isolation import _model  # noqa: E402
from solveur.verification.code_aster_tl_structural import (  # noqa: E402
    CODE_ASTER_IMAGE,
    run_code_aster,
)


CASE = {
    "id": "HEX8_m4_a10_compression_l0.2_d0.12",
    "family": "HEX8",
    "cells": 4,
    "mode": "compression",
    "aspect": 10.0,
    "load_scale": 0.2,
    "increments": 128,
    "distortion": 0.12,
    "angle": 0.0,
}


def _mesh_text(nodes: np.ndarray, elements: list[list[int]], fixed: np.ndarray, loaded: np.ndarray) -> str:
    lines = ["TITRE", "QF Solver TL physical branch HEX8 Code_Aster diagnostic", "FINSF", "COOR_3D"]
    lines.extend(
        f"N{index + 1} {point[0]:.16g} {point[1]:.16g} {point[2]:.16g}"
        for index, point in enumerate(nodes)
    )
    lines.extend(["FINSF", "HEXA8"])
    lines.extend(
        f"M{index + 1} " + " ".join(f"N{node + 1}" for node in element)
        for index, element in enumerate(elements)
    )
    lines.extend(["FINSF", "GROUP_MA", "SOLID"])
    lines.extend(f"M{index + 1}" for index in range(len(elements)))
    lines.extend(["FINSF", "GROUP_NO", "FIXED"])
    lines.extend(f"N{int(node) + 1}" for node in fixed)
    lines.extend(["FINSF", "GROUP_NO", "LOAD"])
    lines.extend(f"N{int(node) + 1}" for node in loaded)
    lines.extend(["FINSF", "GROUP_NO", "NALL"])
    lines.extend(f"N{index + 1}" for index in range(nodes.shape[0]))
    lines.extend(["FINSF", "FIN"])
    return "\n".join(lines) + "\n"


def _command_text(increments: int, loaded_count: int) -> str:
    force = -0.2 / loaded_count
    return f'''# coding=utf-8
import json
import numpy as np
from code_aster.Commands import *

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", PHENOMENE="MECANIQUE", MODELISATION="3D"))
material = DEFI_MATERIAU(ELAS=_F(E=10.0, NU=0.3))
field = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", MATER=material))
fixed = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=_F(GROUP_NO="FIXED", DX=0.0, DY=0.0, DZ=0.0))
load = AFFE_CHAR_MECA(MODELE=model, FORCE_NODALE=_F(GROUP_NO="LOAD", FX={force:.16g}))
ramp = DEFI_FONCTION(NOM_PARA="INST", PROL_GAUCHE="CONSTANT", PROL_DROITE="CONSTANT", VALE=(0.0, 0.0, 1.0, 1.0))
times = DEFI_LIST_REEL(DEBUT=0.0, INTERVALLE=_F(JUSQU_A=1.0, NOMBRE={increments}))
result = STAT_NON_LINE(
    MODELE=model,
    CHAM_MATER=field,
    EXCIT=(_F(CHARGE=fixed), _F(CHARGE=load, FONC_MULT=ramp)),
    COMPORTEMENT=_F(RELATION="ELAS", DEFORMATION="GREEN_LAGRANGE"),
    INCREMENT=_F(LIST_INST=times),
    NEWTON=_F(MATRICE="TANGENTE", REAC_ITER=1),
    CONVERGENCE=_F(RESI_GLOB_RELA=1.0e-10, ITER_GLOB_MAXI=80),
    SOLVEUR=_F(METHODE="MUMPS"),
)
CALC_CHAMP(reuse=result, RESULTAT=result, FORCE=("REAC_NODA",))
rows = []
for order, instant in zip(result.getIndexes(), result.getAccessParameters()["INST"]):
    if float(instant) <= 0.0:
        continue
    displacement = result.getField("DEPL", order)
    ux, _ = displacement.getValuesWithDescription("DX", ["LOAD"])
    uy, _ = displacement.getValuesWithDescription("DY", ["LOAD"])
    uz, _ = displacement.getValuesWithDescription("DZ", ["LOAD"])
    reaction = result.getField("REAC_NODA", order)
    rx, _ = reaction.getValuesWithDescription("DX", ["FIXED"])
    ry, _ = reaction.getValuesWithDescription("DY", ["FIXED"])
    rz, _ = reaction.getValuesWithDescription("DZ", ["FIXED"])
    stress_data = {{}}
    try:
        stress = result.getField("SIEF_ELGA", order)
        for name in ("SIXX", "SIYY", "SIZZ", "SIXY", "SIXZ", "SIYZ"):
            values, _ = stress.getValuesWithDescription(name, ["SOLID"])
            stress_data[name] = [float(value) for value in values]
    except Exception:
        stress_data = {{"status": "NOT_AVAILABLE"}}
    rows.append({{
        "order": int(order),
        "load_factor": float(instant),
        "loaded_mean_displacement": [float(np.mean(ux)), float(np.mean(uy)), float(np.mean(uz))],
        "loaded_mean_ux": float(np.mean(ux)),
        "reaction_resultant_fixed": [float(np.sum(rx)), float(np.sum(ry)), float(np.sum(rz))],
        "external_work_current_load": float(force * np.sum(ux)),
        "stress_sief_elga": stress_data,
    }})
with open("/work/code_aster_raw.json", "w", encoding="utf-8") as stream:
    json.dump({{"case": "{CASE['id']}", "rows": rows}}, stream, indent=2)
FIN()
'''


def run(output: Path) -> dict[str, Any]:
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    model, nodes, elements, fixed, loaded = _model(
        CASE["family"],
        CASE["cells"],
        CASE["mode"],
        CASE["load_scale"],
        CASE["increments"],
        distortion=CASE["distortion"],
        angle=CASE["angle"],
        aspect=CASE["aspect"],
    )
    work = output / "code_aster"
    work.mkdir(exist_ok=True)
    mesh = work / "physical_branch.mail"
    deck = work / "physical_branch.comm"
    mesh.write_text(_mesh_text(nodes, elements, fixed, loaded), encoding="ascii")
    deck.write_text(_command_text(CASE["increments"], len(loaded)), encoding="utf-8")
    try:
        run_code_aster(work, "physical_branch", timeout=1800)
    except Exception as exc:
        summary = {
            "status": "EXTERNAL_REFERENCE_FAILED",
            "case": CASE,
            "external_solver": {"name": "Code_Aster", "image": CODE_ASTER_IMAGE},
            "error_type": type(exc).__name__,
            "error": str(exc),
            "raw_available": False,
            "input_sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in (mesh, deck)},
        }
        (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        return summary
    raw = json.loads((work / "code_aster_raw.json").read_text(encoding="utf-8"))
    summary = {
        "status": "OBSERVED_EXTERNAL_PATH",
        "case": CASE,
        "external_solver": {
            "name": "Code_Aster",
            "version": "18.1.0",
            "image": CODE_ASTER_IMAGE,
            "formulation": "3D/HEXA8, STAT_NON_LINE, ELAS, GREEN_LAGRANGE",
        },
        "same_geometry": True,
        "same_mesh": True,
        "same_material": True,
        "same_nodal_loads": True,
        "raw": raw,
        "input_sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in (mesh, deck)},
        "limitations": [
            "Code_Aster native stress measure and det(F) were not converted to QF measures in this diagnostic.",
            "This is a branch comparison, not a qualification or physical validation.",
        ],
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = run(args.output)
    print(json.dumps({"status": summary["status"], "output": str(args.output.resolve())}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
