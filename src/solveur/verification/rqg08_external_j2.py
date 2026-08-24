"""Common external Code_Aster correlation for the 0.2.4a0 J2 gate.

The campaign uses one affine displacement-controlled cube for TET4, TET10,
HEX8 and HEX20.  The material, displacement history and boundary conditions
are identical; only the solid interpolation changes.  The evidence is an
external numerical correlation, not a physical validation claim.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import numpy as np

from solveur.elements.solid.hex20 import Hex20Element
from solveur.elements.solid.hex8 import Hex8Element
from solveur.elements.solid.tet10 import Tet10Element
from solveur.elements.solid.tet4 import Tet4Element
from solveur.io.manifest import sha256, write_json_file
from solveur.materials.solid import VonMisesElastoplasticMaterial
from solveur.verification.code_aster_tl_structural import CODE_ASTER_IMAGE, run_code_aster


STUDY_ID = "VNV-RQ-G08-J2-COMMON-024"
ELEMENT_TYPES = ("TET4", "TET10", "HEX8", "HEX20")
LOAD_FACTORS = (0.0, 0.25, 0.5, 0.75, 1.0)
YOUNG_MPA = 210_000.0
POISSON = 0.3
YIELD_STRESS_MPA = 250.0
HARDENING_MPA = 50_000.0


def common_material() -> VonMisesElastoplasticMaterial:
    """Return the material shared by QF Solver and Code_Aster."""

    return VonMisesElastoplasticMaterial(
        E=YOUNG_MPA,
        nu=POISSON,
        yield_stress=YIELD_STRESS_MPA,
        hardening_modulus=HARDENING_MPA,
    )


def common_strain() -> np.ndarray:
    """Return the final affine strain used by every external deck."""

    plastic = (300.0 - YIELD_STRESS_MPA) / HARDENING_MPA
    axial = 300.0 / YOUNG_MPA + plastic
    lateral = -POISSON * 300.0 / YOUNG_MPA - 0.5 * plastic
    return np.diag([axial, lateral, lateral])


def _corners() -> np.ndarray:
    return np.asarray(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [1.0, 0.0, 1.0],
            [1.0, 1.0, 1.0],
            [0.0, 1.0, 1.0],
        ],
        dtype=float,
    )


def external_element_coordinates(element_type: str) -> np.ndarray:
    """Return common physical coordinates in QF's canonical local order."""

    corners = _corners()
    family = element_type.upper()
    if family == "TET4":
        return corners[[0, 1, 3, 4]]
    if family == "TET10":
        base = corners[[0, 1, 3, 4]]
        edges = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))
        return np.vstack([base, [(base[first] + base[second]) / 2.0 for first, second in edges]])
    if family == "HEX8":
        return corners
    if family == "HEX20":
        edges = ((0, 1), (0, 3), (0, 4), (1, 2), (1, 5), (2, 3), (2, 6), (3, 7), (4, 5), (4, 7), (5, 6), (6, 7))
        return np.vstack([corners, [(corners[first] + corners[second]) / 2.0 for first, second in edges]])
    raise ValueError(f"Unsupported external correlation element {element_type!r}.")


def _qf_element_coordinates(element_type: str) -> np.ndarray:
    """Return QF's canonical local ordering for the same physical cube."""

    from solveur.verification.robustness_nonlinear_solids import element_coordinates

    return element_coordinates(element_type)


def _element_class(element_type: str) -> type:
    return {"TET4": Tet4Element, "TET10": Tet10Element, "HEX8": Hex8Element, "HEX20": Hex20Element}[element_type]


def _loaded_face_area(element_type: str) -> float:
    """Return the x=1 face area of the unit-cube patch."""

    return 0.5 if element_type in {"TET4", "TET10"} else 1.0


def code_aster_mesh(element_type: str) -> tuple[np.ndarray, list[int], str]:
    """Build an ASTER mesh text and the right-face node ids."""

    nodes = external_element_coordinates(element_type)
    keywords = {"TET4": "TETRA4", "TET10": "TETRA10", "HEX8": "HEXA8", "HEX20": "HEXA20"}
    group = keywords[element_type]
    lines = ["TITRE", f"QF Solver RQ-G08 {element_type} J2", "FINSF", "COOR_3D"]
    lines.extend(f"N{i + 1} {x:.16g} {y:.16g} {z:.16g}" for i, (x, y, z) in enumerate(nodes))
    order = (0, 1, 2, 3, 4, 5, 6, 7, 8, 11, 13, 9, 10, 12, 14, 15, 16, 18, 19, 17) if element_type == "HEX20" else tuple(range(nodes.shape[0]))
    lines.extend(["FINSF", group, "M1", *[f"N{i + 1}" for i in order], "FINSF", "GROUP_MA", "SOLID", "M1", "FINSF", "GROUP_NO", "RIGHT"])
    lines.extend([f"N{i + 1}" for i, point in enumerate(nodes) if np.isclose(point[0], 1.0)])
    lines.extend(["FINSF", "GROUP_NO", "NALL", *[f"N{i + 1}" for i in range(nodes.shape[0])], "FINSF", "FIN"])
    right_nodes = [i + 1 for i, point in enumerate(nodes) if np.isclose(point[0], 1.0)]
    return nodes, right_nodes, "\n".join(lines) + "\n"


def code_aster_commands(element_type: str, nodes: np.ndarray, face_area: float) -> str:
    """Generate the common displacement-controlled VMIS_ISOT_LINE deck."""

    strain = common_strain()
    imposed = ",\n        ".join(
        f'_F(NOEUD="N{index + 1}", DX={float(strain[0] @ point):.16g}, '
        f'DY={float(strain[1] @ point):.16g}, DZ={float(strain[2] @ point):.16g})'
        for index, point in enumerate(nodes)
    )
    return f'''# coding=utf-8
import json
import numpy as np
from code_aster.Commands import *

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", PHENOMENE="MECANIQUE", MODELISATION="3D"))
material = DEFI_MATERIAU(
    ELAS=_F(E={YOUNG_MPA:.16g}, NU={POISSON:.16g}),
    ECRO_LINE=_F(SY={YIELD_STRESS_MPA:.16g}, D_SIGM_EPSI={YOUNG_MPA * HARDENING_MPA / (YOUNG_MPA + HARDENING_MPA):.16g}),
)
field = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", MATER=material))
boundary = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=(
        {imposed}
))
ramp = DEFI_FONCTION(NOM_PARA="INST", VALE=(0.0, 0.0, 1.0, 1.0))
times = DEFI_LIST_REEL(DEBUT=0.0, INTERVALLE=_F(JUSQU_A=1.0, NOMBRE=4))
result = STAT_NON_LINE(
    MODELE=model, CHAM_MATER=field, EXCIT=_F(CHARGE=boundary, FONC_MULT=ramp),
    COMPORTEMENT=_F(RELATION="VMIS_ISOT_LINE", DEFORMATION="PETIT"),
    INCREMENT=_F(LIST_INST=times),
    CONVERGENCE=_F(RESI_GLOB_RELA=1.0e-10, ITER_GLOB_MAXI=40),
)
raw = {{"element": "{element_type}", "steps": []}}
access = result.getAccessParameters()
for order, instant in zip(result.getIndexes(), access["INST"]):
    stress = result.getField("SIEF_ELGA", order)
    components = []
    for name in ("SIXX", "SIYY", "SIZZ", "SIXY", "SIXZ", "SIYZ"):
        values, _ = stress.getValuesWithDescription(name, ["SOLID"])
        components.append(float(np.mean(values)))
    internal = result.getField("VARI_ELGA", order)
    peeq, _ = internal.getValuesWithDescription("V1", ["SOLID"])
    raw["steps"].append({{
        "time": float(instant),
        "stress_mpa": components,
        "von_mises_mpa": float(np.sqrt(0.5 * ((components[0] - components[1]) ** 2 + (components[1] - components[2]) ** 2 + (components[2] - components[0]) ** 2))),
        "equivalent_plastic_strain": float(np.mean(peeq)),
        "reaction_x": float(components[0] * {face_area:.16g}),
        "reaction_source": "SIEF_ELGA face resultant; all affine displacements are prescribed",
    }})
with open("/work/code_aster_raw.json", "w", encoding="utf-8") as stream:
    json.dump(raw, stream, indent=2)
FIN()
'''


def _qf_history(element_type: str) -> list[dict[str, float]]:
    """Evaluate the same history through the QF element/material path."""

    material = common_material()
    element = _element_class(element_type)(material)
    coords = _qf_element_coordinates(element_type)
    strain = common_strain()
    committed: list[dict[str, object]] | None = None
    rows: list[dict[str, float]] = []
    face_area = _loaded_face_area(element_type)
    for factor in LOAD_FACTORS:
        displacement = np.concatenate([factor * strain @ point for point in coords])
        _, _, trial = element.internal_force_tangent_state(coords, displacement, committed)
        committed = deepcopy(trial)
        stresses = [np.asarray(state["stress"], dtype=float) for state in committed]
        mean_stress = np.mean(stresses, axis=0)
        rows.append({
            "time": factor,
            "stress_mpa": float(mean_stress[0]),
            "von_mises_mpa": float(np.mean([state["equivalent_stress"] for state in committed])),
            "equivalent_plastic_strain": float(np.mean([state["equivalent_plastic_strain"] for state in committed])),
            "reaction_x": float(mean_stress[0] * face_area),
        })
    return rows


def _relative_error(value: float, reference: float) -> float:
    if max(abs(value), abs(reference)) <= 1.0e-12:
        return abs(value - reference)
    return abs(value - reference) / abs(reference)


def evaluate_external_correlation(raw: dict[str, Any]) -> dict[str, Any]:
    """Compare Code_Aster histories with the QF element path."""

    checks: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    for element_type in ELEMENT_TYPES:
        external = next(item for item in raw["elements"] if item["element"] == element_type)
        qf_rows = _qf_history(element_type)
        external_rows = external["steps"]
        element_checks: list[dict[str, Any]] = []
        for qf, code_aster in zip(qf_rows, external_rows, strict=True):
            for metric in ("stress_mpa", "von_mises_mpa", "equivalent_plastic_strain", "reaction_x"):
                external_value = code_aster[metric][0] if metric == "stress_mpa" else code_aster[metric]
                error = _relative_error(float(external_value), float(qf[metric]))
                check = {"id": f"{element_type}_{metric}_t{qf['time']:.2f}", "value": error, "limit": 5.0e-4, "status": "PASS" if np.isfinite(error) and error <= 5.0e-4 else "FAIL"}
                checks.append(check)
                element_checks.append(check)
        rows.append({"element": element_type, "status": "PASS" if all(item["status"] == "PASS" for item in element_checks) else "FAIL", "qf_solver": qf_rows, "code_aster": external_rows})
    return {
        "campaign_id": STUDY_ID,
        "status": "PASS_EXTERNAL_CORRELATION" if all(item["status"] == "PASS" for item in checks) else "FAIL",
        "maturity": "experimental",
        "scope": {"elements": list(ELEMENT_TYPES), "material": "VMIS_ISOT_LINE / small-strain J2 isotropic hardening", "history": list(LOAD_FACTORS), "observables": ["force-displacement", "reactions", "von Mises", "PEEQ", "yield onset", "final state"]},
        "checks": checks,
        "rows": rows,
        "limitations": ["Code_Aster is the external numerical reference; no physical validation claim is made.", "The comparison is a displacement-controlled affine one-element patch.", "No cyclic reversal or multi-element mesh convergence is claimed by RQ-G08 itself.", "The reaction resultant is reconstructed from the uniform SIEF_ELGA traction over the loaded face because every affine displacement is prescribed."],
    }


def run_campaign(output_dir: str | Path) -> dict[str, Any]:
    """Run all four Code_Aster decks and write raw and normalized evidence."""

    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    raw: dict[str, Any] = {"campaign_id": STUDY_ID, "external_solver": {"name": "Code_Aster", "version": "18.1.0", "image": CODE_ASTER_IMAGE}, "elements": []}
    for element_type in ELEMENT_TYPES:
        work = output / element_type.lower()
        work.mkdir(parents=True, exist_ok=True)
        nodes, _, mesh = code_aster_mesh(element_type)
        face_area = 0.5 if element_type in {"TET4", "TET10"} else 1.0
        (work / "rqg08.mail").write_text(mesh, encoding="ascii")
        (work / "rqg08.comm").write_text(code_aster_commands(element_type, nodes, face_area), encoding="utf-8")
        run_code_aster(work, "rqg08")
        raw["elements"].append(json.loads((work / "code_aster_raw.json").read_text(encoding="utf-8")))
    summary = evaluate_external_correlation(raw)
    summary["external_solver"] = raw["external_solver"]
    summary["raw_digest"] = {element: sha256(output / element.lower() / "rqg08.comm") for element in ELEMENT_TYPES}
    write_json_file(output / "summary.json", summary)
    _write_report(output, summary)
    return summary


def _write_report(output: Path, summary: dict[str, Any]) -> None:
    lines = [f"# {STUDY_ID}", "", f"Statut : **{summary['status']}**", "", "Corrélation Code_Aster externe commune TET4/TET10/HEX8/HEX20 avec même matériau, historique et patch affine.", "", "| Élément | Statut | Erreur maximale |", "| --- | --- | ---: |"]
    for row in summary["rows"]:
        errors = [item["value"] for item in summary["checks"] if item["id"].startswith(f"{row['element']}_")]
        lines.append(f"| {row['element']} | {row['status']} | {max(errors):.3e} |")
    lines.extend(["", "## Portée", "", "- Même matériau J2, mêmes déplacements imposés et même historique [0, 0.25, 0.5, 0.75, 1].", "- Observables : contrainte axiale, von Mises, PEEQ et résultant de traction sur la face x=1.", "- Le résultant est reconstruit par intégration de la traction SIEF_ELGA uniforme, car tous les déplacements affines sont imposés.", "- Cette preuve est une corrélation numérique externe; elle ne constitue pas une validation physique.", "- La preuve reste bornée à un patch affine à un élément; elle ne couvre pas à elle seule la convergence multi-éléments, les cycles ou la qualification industrielle.", ""])
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8")
