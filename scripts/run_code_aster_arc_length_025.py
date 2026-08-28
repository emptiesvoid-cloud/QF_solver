"""Run the pinned Code_Aster arc-length correlation for the G04 FEM case.

This runner is evidence infrastructure only.  It reuses the two-element TET4
geometry used by the common QF Solver snap-through benchmark and does not alter
the QF Solver numerical implementation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from solveur.verification.code_aster_tl_structural import run_code_aster


ROOT = Path(__file__).resolve().parents[1]


def mesh_text(*, imperfection_x: float = 0.0) -> str:
    """Return the deterministic ASTER mesh shared with the QF benchmark."""

    return "\n".join(
        [
            "TITRE",
            "QF Solver G04 common FEM snap-through correlation",
            "FINSF",
            "COOR_3D",
            "N1 -1.0 0.0 0.0",
            "N2 1.0 0.0 0.0",
            "N3 0.0 -0.05 0.20",
            "N4 0.0 0.05 0.20",
            f"N5 {imperfection_x:.16g} 0.0 0.25",
            "FINSF",
            "TETRA4",
            "M1 N1 N3 N4 N5",
            "M2 N2 N4 N3 N5",
            "FINSF",
            "GROUP_NO",
            "FIXED",
            "N1 N2",
            "FINSF",
            "GROUP_NO",
            "CROWN",
            "N3 N4 N5",
            "FINSF",
            "GROUP_NO",
            "APEX",
            "N5",
            "FINSF",
            "GROUP_MA",
            "SOLID",
            "M1 M2",
            "FINSF",
            "FIN",
            "",
        ]
    )


def command_text(
    *,
    reference_load_sign: float = -1.0,
    arc_length_end: float = 1.0,
    arc_length_steps: int = 80,
) -> str:
    """Return the Code_Aster LONG_ARC command file in QF load convention."""

    if not np.isfinite(reference_load_sign) or reference_load_sign == 0.0:
        raise ValueError("reference_load_sign must be a finite non-zero scalar.")
    if not np.isfinite(arc_length_end) or arc_length_end <= 0.0:
        raise ValueError("arc_length_end must be finite and strictly positive.")
    if isinstance(arc_length_steps, bool) or int(arc_length_steps) <= 0:
        raise ValueError("arc_length_steps must be a strictly positive integer.")

    template = '''# coding=utf-8
import json
import numpy as np
from code_aster.Commands import *

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(
    MAILLAGE=mesh,
    AFFE=_F(GROUP_MA="SOLID", PHENOMENE="MECANIQUE", MODELISATION="3D"),
)
material = DEFI_MATERIAU(ELAS=_F(E=100.0, NU=0.3))
field = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", MATER=material))
fixed = AFFE_CHAR_MECA(
    MODELE=model,
    DDL_IMPO=(
        _F(GROUP_NO="FIXED", DX=0.0, DY=0.0, DZ=0.0),
        _F(GROUP_NO="CROWN", DY=0.0),
    ),
)
load = AFFE_CHAR_MECA(
    MODELE=model,
    FORCE_NODALE=_F(GROUP_NO="CROWN", FZ=__REFERENCE_LOAD__),
)
times = DEFI_LIST_REEL(
    DEBUT=0.0,
    INTERVALLE=_F(JUSQU_A=__ARC_LENGTH_END__, NOMBRE=__ARC_LENGTH_STEPS__),
)
result = STAT_NON_LINE(
    MODELE=model,
    CHAM_MATER=field,
    EXCIT=(
        _F(CHARGE=fixed),
        _F(CHARGE=load, TYPE_CHARGE="FIXE_PILO"),
    ),
    COMPORTEMENT=_F(RELATION="ELAS", DEFORMATION="GREEN_LAGRANGE"),
    INCREMENT=_F(LIST_INST=times),
    NEWTON=_F(MATRICE="TANGENTE", REAC_ITER=1),
    PILOTAGE=_F(
        TYPE="LONG_ARC",
        COEF_MULT=1.0,
        ETA_PILO_MAX=50.0,
        ETA_PILO_MIN=-5.0,
        SELECTION="ANGL_INCR_DEPL",
        GROUP_NO="APEX",
        NOM_CMP=("DZ",),
    ),
    CONVERGENCE=_F(RESI_GLOB_RELA=1.0e-8, ITER_GLOB_MAXI=80),
    SOLVEUR=_F(METHODE="MUMPS"),
)
result = CALC_CHAMP(reuse=result, RESULTAT=result, FORCE="FORC_NODA")
eta = RECU_FONCTION(RESULTAT=result, NOM_PARA_RESU="ETA_PILOTAGE", TOUT_ORDRE="OUI")
eta_values = eta.getValuesAsArray().tolist()
access = result.getAccessParameters()
points = []
for order, instant in zip(result.getIndexes(), access["INST"]):
    displacement = result.getField("DEPL", order)
    dz, dz_description = displacement.getValuesWithDescription("DZ", ["CROWN"])
    apex_dz, apex_description = displacement.getValuesWithDescription("DZ", ["APEX"])
    reaction = result.getField("FORC_NODA", order)
    fixed_dz, fixed_description = reaction.getValuesWithDescription("DZ", ["FIXED"])
    points.append({
        "order": int(order),
        "instant": float(instant),
        "displacement_values": np.asarray(dz, dtype=float).tolist(),
        "displacement_description": [list(item) for item in dz_description if isinstance(item, tuple)],
        "apex_displacement_values": np.asarray(apex_dz, dtype=float).tolist(),
        "apex_displacement_description": [list(item) for item in apex_description if isinstance(item, tuple)],
        "reaction_values": np.asarray(fixed_dz, dtype=float).tolist(),
        "reaction_description": [list(item) for item in fixed_description if isinstance(item, tuple)],
        "control_displacement": float(np.mean(apex_dz)),
        "crown_mean_displacement": float(np.mean(dz)),
        "reaction_fixed_z": float(np.sum(fixed_dz)),
        "load_factor_from_reaction": float(-np.sum(fixed_dz)),
    })
with open("/work/code_aster_arc_length_raw.json", "w", encoding="utf-8") as stream:
    json.dump({"eta_pilotage": eta_values, "points": points}, stream, indent=2)
FIN()
'''
    return (
        template.replace("__REFERENCE_LOAD__", f"{reference_load_sign / 3.0:.17g}")
        .replace("__ARC_LENGTH_END__", f"{arc_length_end:.17g}")
        .replace("__ARC_LENGTH_STEPS__", str(int(arc_length_steps)))
    )


def run(
    output: Path,
    *,
    imperfection_x: float = 0.0,
    reference_load_sign: float = -1.0,
    arc_length_end: float = 1.0,
    arc_length_steps: int = 80,
) -> dict[str, object]:
    """Generate and execute the external deck, returning its raw history."""

    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    work = output / "code_aster"
    work.mkdir(exist_ok=True)
    (work / "arc_length.mail").write_text(mesh_text(imperfection_x=imperfection_x), encoding="ascii")
    (work / "arc_length.comm").write_text(
        command_text(
            reference_load_sign=reference_load_sign,
            arc_length_end=arc_length_end,
            arc_length_steps=arc_length_steps,
        ),
        encoding="utf-8",
    )
    run_code_aster(work, "arc_length", timeout=900)
    raw = json.loads((work / "code_aster_arc_length_raw.json").read_text(encoding="utf-8"))
    eta_series = raw.get("eta_pilotage", [])
    points = raw.get("points", [])
    load_factors = [float(point["load_factor_from_reaction"]) for point in points]
    factor_increments = np.diff(np.asarray(load_factors, dtype=float)) if len(load_factors) > 1 else np.array([])
    direction_changes = np.flatnonzero(factor_increments[:-1] * factor_increments[1:] < -1.0e-12)
    summary = {
        "status": "OBSERVED_EXTERNAL_PATH",
        "study_id": "VNV-G04-ARCLENGTH-CODEASTER-025",
        "solver": "Code_Aster",
        "version": "18.1.0",
        "model": "two-element TET4 common FEM snap-through model",
        "imperfection_x": float(imperfection_x),
        "reference_load_sign": float(reference_load_sign),
        "arc_length_end": float(arc_length_end),
        "arc_length_steps": int(arc_length_steps),
        "continuation_parameter_range": [
            float(value[0] if isinstance(value, list) else value)
            for value in (eta_series[0], eta_series[-1])
        ] if eta_series else [],
        "load_factor_range": [min(load_factors), max(load_factors)] if load_factors else [],
        "control_displacement_range": (
            [
                min(float(point["control_displacement"]) for point in points),
                max(float(point["control_displacement"]) for point in points),
            ]
            if points
            else []
        ),
        "turning_point_count": int(direction_changes.size),
        "turning_point_orders": [int(index + 1) for index in direction_changes],
        "complete_path": bool(points) and len(points) == len(eta_series),
        "source_deck": str((work / "arc_length.comm").relative_to(ROOT)),
        "mesh": str((work / "arc_length.mail").relative_to(ROOT)),
        "raw": raw,
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--imperfection-x", type=float, default=0.0)
    parser.add_argument("--reference-load-sign", type=float, default=-1.0)
    parser.add_argument("--arc-length-end", type=float, default=1.0)
    parser.add_argument("--arc-length-steps", type=int, default=80)
    args = parser.parse_args()
    summary = run(
        args.output,
        imperfection_x=args.imperfection_x,
        reference_load_sign=args.reference_load_sign,
        arc_length_end=args.arc_length_end,
        arc_length_steps=args.arc_length_steps,
    )
    print(f"{summary['study_id']}: {summary['status']} -> {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
