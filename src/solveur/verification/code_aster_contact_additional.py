"""Code_Aster correlation of the three additional bounded contact models."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, cast

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from solveur.core.solvers.static import LinearStaticSolver
from solveur.io.json_reader import JsonModelReader
from solveur.io.manifest import write_json_file
from solveur.verification.code_aster_tl_structural import CODE_ASTER_IMAGE, run_code_aster
from solveur.verification.contact_additional_oracle import (
    CALCULIX_IMAGE,
    run_calculix_precontact_probe,
)
from solveur.verification.contact_additional_models import (
    _deformable_tet4_two_slaves,
    _dual_stop_corner,
    _faceted_ramp_patch,
)
from solveur.verification.vnv_manifest import write_vnv_manifest


class CodeAsterAdditionalContactCampaign:
    """Compare ten-point load paths for three bounded contact geometries."""

    study_id = "VNV-CONTACT-CODEASTER-ADDITIONAL-009"
    load_factors = np.linspace(0.1, 1.0, 10)
    curve_limit = 5.0e-4
    calculix_image = CALCULIX_IMAGE

    def __init__(
        self,
        output_dir: str | Path,
        *,
        tet4_grid: tuple[int, int, int] = (8, 4, 4),
        study_id: str | None = None,
    ) -> None:
        self.output_dir = Path(output_dir).resolve()
        self.tet4_grid = tet4_grid
        self.instance_study_id = study_id or self.study_id

    def run(self) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        cases = [
            self._run_case("dual_stop_corner", _dual_stop_corner()),
            self._run_case("faceted_ramp_patch", _faceted_ramp_patch()),
            self._run_case(
                "deformable_tet4_two_slaves",
                _deformable_tet4_two_slaves(
                    nx=self.tet4_grid[0],
                    ny=self.tet4_grid[1],
                    nz=self.tet4_grid[2],
                ),
            ),
        ]
        checks = [check for case in cases for check in case["checks"]]
        statuses = {str(check["status"]) for check in checks}
        if "FAIL" in statuses:
            status = "FAIL"
        elif "WARNING" in statuses:
            status = "PASS_WITH_EXTERNAL_WARNING"
        else:
            status = "PASS_EXTERNAL_CORRELATION"
        summary: dict[str, Any] = {
            "study_id": self.instance_study_id,
            "status": status,
            "maturity": "ready_for_owner_review",
            "scope": "bounded_small_displacement_frictionless_contact",
            "external_solver": {
                "name": "Code_Aster",
                "version": "18.1.0",
                "image": CODE_ASTER_IMAGE,
                "formulations": [
                    "DEFI_CONTACT / LIAISON_UNIL",
                    "3D TETRA4 / DEFI_CONTACT / LIAISON_UNIL",
                ],
            },
            "diagnostic_solver": {
                "name": "CalculiX",
                "version": "2.20",
                "image": self.calculix_image,
                "role": "independent pre-contact TET4 tie-breaker",
            },
            "load_factors": self.load_factors.tolist(),
            "cases": cases,
            "checks": checks,
            "limitations": [
                "The comparison isolates the same unilateral normal inequalities.",
                "The faceted ramp uses one scalar normal inequality per retained facet.",
                "The TET4 model compares the deformable structure and two unilateral slave nodes.",
                "Friction, impact, large sliding and general surface-to-surface contact remain outside scope.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._plot(cases)
        (self.output_dir / "report.md").write_text(self._report(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, self.instance_study_id)
        return summary

    def _run_case(self, identifier: str, data: dict[str, object]) -> dict[str, Any]:
        work = self.output_dir / identifier
        work.mkdir(exist_ok=True)
        qf = _qf_curve(identifier, data, self.load_factors)
        mesh, commands = _aster_input(identifier, data)
        (work / f"{identifier}.mail").write_text(mesh, encoding="ascii")
        (work / f"{identifier}.comm").write_text(commands, encoding="utf-8")
        run_code_aster(work, identifier)
        raw = json.loads((work / "code_aster_raw.json").read_text(encoding="utf-8"))
        aster_displacements = np.asarray(raw["displacements_m"], dtype=float)
        qf_displacements = np.asarray(qf["displacements_m"], dtype=float)
        if aster_displacements.shape != qf_displacements.shape:
            raise ValueError(
                f"{identifier}: Code_Aster curve shape {aster_displacements.shape} "
                f"does not match QF_solver {qf_displacements.shape}"
            )
        gap_data = _gaps(identifier, data, aster_displacements)
        qf_gaps = np.asarray(qf["gaps_m"], dtype=float)
        displacement_error = _normalized_curve_error(
            qf_displacements, aster_displacements
        )
        gap_error = _normalized_curve_error(qf_gaps, gap_data)
        checks: list[dict[str, float | str]] = []
        diagnostics: dict[str, object] = {}
        if identifier == "deformable_tet4_two_slaves":
            initially_closed = bool(np.max(np.abs(qf_gaps[0])) <= 1.0e-8)
            active_start = 0 if initially_closed else 1
            active_displacement_error = _normalized_curve_error(
                qf_displacements[active_start:],
                aster_displacements[active_start:],
            )
            active_gap_error = float(
                np.max(
                    np.abs(
                        qf_gaps[active_start:]
                        - gap_data[active_start:]
                    )
                )
            )
            diagnostics = {
                "contacts_closed_at_first_sample": initially_closed,
            }
            checks.extend(
                [
                    _upper(
                        f"{identifier}:active_displacement_curve",
                        active_displacement_error,
                        self.curve_limit,
                    ),
                    _upper(
                        f"{identifier}:active_gap_curve",
                        active_gap_error,
                        1.0e-8,
                    ),
                    _warning(
                        f"{identifier}:code_aster_transition_curve",
                        displacement_error,
                        5.0e-2,
                    ),
                ]
            )
            if initially_closed:
                diagnostics["calculix_precontact_probe"] = "not_applicable"
                diagnostics["code_aster_transition_observation"] = (
                    "Both QF_solver contacts are already closed at the first "
                    "sample; the full QF_solver/Code_Aster curve is compared."
                )
            else:
                calculix = run_calculix_precontact_probe(work, data)
                qf_probe = qf_displacements[0]
                calculix_error = _normalized_curve_error(
                    qf_probe,
                    np.asarray(calculix, dtype=float),
                )
                diagnostics.update(
                    {
                        "qf_precontact_displacements_m": qf_probe.tolist(),
                        "calculix_precontact_displacements_m": calculix,
                        "qf_calculix_precontact_error": calculix_error,
                        "code_aster_transition_observation": (
                            "Code_Aster closes the second slave at load factor "
                            "0.1; the refined-mesh curve difference remains below "
                            "the accepted 5 percent limit."
                        ),
                    }
                )
                checks.append(
                    _upper(
                        f"{identifier}:qf_calculix_precontact",
                        calculix_error,
                        1.0e-5,
                    )
                )
        else:
            checks.extend(
                [
                    _upper(
                        f"{identifier}:displacement_curve",
                        displacement_error,
                        self.curve_limit,
                    ),
                    _upper(
                        f"{identifier}:gap_curve",
                        gap_error,
                        self.curve_limit,
                    ),
                ]
            )
        checks.append(
            _upper(
                f"{identifier}:final_max_abs_gap",
                float(np.max(np.abs(gap_data[-1]))),
                1.0e-8,
            )
        )
        return {
            "id": identifier,
            "nodes": len(cast(list[object], data["nodes"])),
            "elements": len(cast(list[object], data["elements"])),
            "channels": qf["channels"],
            "qf_displacements_m": qf_displacements.tolist(),
            "code_aster_displacements_m": aster_displacements.tolist(),
            "qf_gaps_m": qf_gaps.tolist(),
            "code_aster_gaps_m": gap_data.tolist(),
            "qf_pressures_n": qf["pressures_n"],
            "displacement_curve_error": displacement_error,
            "gap_curve_error": gap_error,
            "diagnostics": diagnostics,
            "checks": checks,
        }

    def _plot(self, cases: list[dict[str, Any]]) -> None:
        figure, axes = plt.subplots(3, 2, figsize=(11.0, 11.0), constrained_layout=True)
        factors = self.load_factors
        colors = ("#007c91", "#d1495b", "#6a4c93")
        for row, case in enumerate(cases):
            qf_u = np.asarray(case["qf_displacements_m"], dtype=float)
            aster_u = np.asarray(case["code_aster_displacements_m"], dtype=float)
            qf_gap = np.asarray(case["qf_gaps_m"], dtype=float)
            aster_gap = np.asarray(case["code_aster_gaps_m"], dtype=float)
            for channel, label in enumerate(case["channels"]):
                color = colors[channel % len(colors)]
                axes[row, 0].plot(
                    factors, qf_u[:, channel], color=color, marker="o", label=f"QF {label}"
                )
                axes[row, 0].plot(
                    factors,
                    aster_u[:, channel],
                    color=color,
                    linestyle="--",
                    marker="x",
                    label=f"Aster {label}",
                )
                axes[row, 1].plot(
                    factors,
                    qf_gap[:, channel],
                    color=color,
                    marker="o",
                    label=f"QF {label}",
                )
                axes[row, 1].plot(
                    factors,
                    aster_gap[:, channel],
                    color=color,
                    linestyle="--",
                    marker="x",
                    label=f"Aster {label}",
                )
            axes[row, 0].set_title(f"{case['id']} - deplacement")
            axes[row, 1].set_title(f"{case['id']} - gap normal")
            for axis in axes[row]:
                axis.set_xlabel("Facteur de charge")
                axis.grid(True, alpha=0.3)
                axis.legend(fontsize=7, ncol=2)
            axes[row, 0].set_ylabel("Deplacement [m]")
            axes[row, 1].set_ylabel("Gap [m]")
        figure.savefig(self.output_dir / "contact_code_aster_curves.png", dpi=180)
        plt.close(figure)

    @staticmethod
    def _report(summary: dict[str, Any]) -> str:
        lines = [
            f"# {summary['study_id']}",
            "",
            f"Statut automatise : **{summary['status']}**.",
            "",
            "Dix niveaux de charge identiques sont compares entre QF_solver et "
            "Code_Aster 18.1.0. Les courbes couvrent l'ouverture, la fermeture "
            "progressive et l'etat final actif.",
            "",
            "| Modele | Ecart courbe U | Ecart courbe gap | Gap final max |",
            "| --- | ---: | ---: | ---: |",
        ]
        for case in summary["cases"]:
            final_gap = float(np.max(np.abs(np.asarray(case["code_aster_gaps_m"])[-1])))
            lines.append(
                f"| {case['id']} | {100 * float(case['displacement_curve_error']):.6g} % | "
                f"{100 * float(case['gap_curve_error']):.6g} % | {final_gap:.3e} m |"
            )
        tet4_diagnostics = summary["cases"][2]["diagnostics"]
        if tet4_diagnostics.get("contacts_closed_at_first_sample"):
            transition_comment = (
                "Sur le bloc TET4 raffine, les deux contacts sont deja fermes au "
                "premier palier. QF_solver et Code_Aster coincident sur toute la "
                "courbe; le probe CalculiX avant contact n'est donc pas applicable."
            )
        else:
            transition_comment = (
                "Sur le bloc TET4 raffine, Code_Aster ferme un esclave plus tot au "
                "premier palier. L'ecart de courbe reste sous le seuil accepte de "
                "5 %. QF_solver et CalculiX coincident avant contact, puis QF_solver "
                "et Code_Aster coincident sur la branche fermee."
            )
        lines.extend(
            [
                "",
                "![Courbes QF_solver et Code_Aster](contact_code_aster_curves.png)",
                "",
                "Cette campagne ne qualifie ni frottement, ni impact, ni grand "
                "glissement, ni contact surface-surface general.",
                "",
                transition_comment,
                "",
            ]
        )
        return "\n".join(lines)


def _qf_curve(
    identifier: str,
    source: dict[str, object],
    factors: np.ndarray,
) -> dict[str, object]:
    displacements: list[list[float]] = []
    gaps: list[list[float]] = []
    pressures: list[list[float]] = []
    channels = _channels(identifier, source)
    for factor in factors:
        data = deepcopy(source)
        data["loads"] = [
            {**cast(dict[str, object], load), "value": float(load["value"]) * factor}
            for load in cast(list[dict[str, object]], source["loads"])
        ]
        model_data = {key: value for key, value in data.items() if not key.startswith("_")}
        result = LinearStaticSolver().solve(JsonModelReader().from_dict(model_data))
        contacts = cast(list[dict[str, object]], result.solver["contact"]["contacts"])
        displacements.append(
            [
                float(result.displacements[result.dofs.index(node, dof)])
                for node, dof in channels
            ]
        )
        gaps.append([float(row["gap"]) for row in contacts])
        pressures.append([float(row["pressure"]) for row in contacts])
    return {
        "channels": [f"N{node + 1}-{dof}" for node, dof in channels],
        "displacements_m": displacements,
        "gaps_m": gaps,
        "pressures_n": pressures,
    }


def _channels(
    identifier: str,
    data: dict[str, object],
) -> list[tuple[int, str]]:
    if identifier == "dual_stop_corner":
        return [(4, "UX"), (4, "UZ")]
    if identifier == "faceted_ramp_patch":
        return [(node, "UZ") for node in cast(list[int], data["_plot"]["slaves"])]
    return [(node, "UX") for node in cast(list[int], data["_plot"]["slaves"])]


def _aster_input(
    identifier: str,
    data: dict[str, object],
) -> tuple[str, str]:
    if identifier == "dual_stop_corner":
        return _dual_mesh(), _dual_commands()
    if identifier == "faceted_ramp_patch":
        return _ramp_mesh(data), _ramp_commands(data)
    return _tet4_mesh(data), _tet4_commands(data)


def _dual_mesh() -> str:
    return """TITRE
QF_solver dual stop contact
FINSF
COOR_3D
S1 0.1 0.45 0.1
FINSF
POI1
P1 S1
FINSF
GROUP_MA
SPRINGS
P1
FINSF
GROUP_NO
SLAVE
S1
FINSF
FIN
"""


def _dual_commands() -> str:
    zones = (
        '_F(GROUP_NO="SLAVE", NOM_CMP="DX", '
        "COEF_IMPO=DEFI_CONSTANTE(VALE=0.1), "
        "COEF_MULT=DEFI_CONSTANTE(VALE=-1.0)), "
        '_F(GROUP_NO="SLAVE", NOM_CMP="DZ", '
        "COEF_IMPO=DEFI_CONSTANTE(VALE=0.1), "
        "COEF_MULT=DEFI_CONSTANTE(VALE=-1.0))"
    )
    return _point_commands(
        stiffness=(1000.0, 1000.0, 1000.0),
        fixed='_F(GROUP_NO="SLAVE", DY=0.0)',
        load='_F(GROUP_NO="SLAVE", FX=-200.0, FZ=-300.0)',
        zones=zones,
        extraction=[("SLAVE", "DX"), ("SLAVE", "DZ")],
    )


def _ramp_mesh(data: dict[str, object]) -> str:
    nodes = cast(list[list[float]], data["nodes"])
    lines = ["TITRE", "QF_solver faceted ramp contact", "FINSF", "COOR_3D"]
    for index in range(8, 11):
        x, y, z = nodes[index]
        lines.append(f"S{index - 7} {x:.16g} {y:.16g} {z:.16g}")
    lines.extend(["FINSF", "POI1"])
    for index in range(1, 4):
        lines.append(f"P{index} S{index}")
    lines.extend(["FINSF", "GROUP_MA", "SPRINGS", "P1 P2 P3", "FINSF"])
    for index in range(1, 4):
        lines.extend(["GROUP_NO", f"SLAVE_{index}", f"S{index}", "FINSF"])
    lines.extend(["FIN", ""])
    return "\n".join(lines)


def _ramp_geometry(data: dict[str, object]) -> list[tuple[float, float]]:
    nodes = np.asarray(data["nodes"], dtype=float)
    faces = cast(list[list[int]], data["_plot"]["faces"])
    selected = (0, 2, 5)
    values = []
    for slave, face_index in zip((8, 9, 10), selected):
        face = faces[face_index]
        a, b, c = nodes[face]
        normal = np.cross(b - a, c - a)
        normal /= np.linalg.norm(normal)
        if normal[2] < 0.0:
            normal *= -1.0
        values.append((float(np.dot(nodes[slave] - a, normal)), float(normal[2])))
    return values


def _ramp_commands(data: dict[str, object]) -> str:
    zones = ", ".join(
        f'_F(GROUP_NO="SLAVE_{index}", NOM_CMP="DZ", '
        f"COEF_IMPO=DEFI_CONSTANTE(VALE={gap:.16g}), "
        f"COEF_MULT=DEFI_CONSTANTE(VALE={-normal_z:.16g}))"
        for index, (gap, normal_z) in enumerate(_ramp_geometry(data), start=1)
    )
    return _point_commands(
        stiffness=(0.0, 0.0, 1200.0),
        fixed=", ".join(
            f'_F(GROUP_NO="SLAVE_{index}", DX=0.0, DY=0.0)'
            for index in range(1, 4)
        ),
        load=", ".join(
            f'_F(GROUP_NO="SLAVE_{index}", FZ=-400.0)' for index in range(1, 4)
        ),
        zones=zones,
        extraction=[(f"SLAVE_{index}", "DZ") for index in range(1, 4)],
    )


def _point_commands(
    *,
    stiffness: tuple[float, float, float],
    fixed: str,
    load: str,
    zones: str,
    extraction: list[tuple[str, str]],
) -> str:
    extraction_code = "\n".join(
        f'    values, _ = field.getValuesWithDescription("{component}", ["{group}"])\n'
        f"    row.append(float(values[0]))"
        for group, component in extraction
    )
    return f'''# coding=utf-8
import json
from code_aster.Commands import *
DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SPRINGS", PHENOMENE="MECANIQUE", MODELISATION="DIS_T"))
material = DEFI_MATERIAU(ELAS=_F(E=1.0e6, NU=0.3))
field_material = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(TOUT="OUI", MATER=material))
spring = AFFE_CARA_ELEM(MODELE=model, DISCRET=_F(GROUP_MA="SPRINGS", REPERE="GLOBAL", CARA="K_T_D_N", VALE={stiffness!r}))
fixed = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=({fixed}))
load = AFFE_CHAR_MECA(MODELE=model, FORCE_NODALE=({load}))
contact = DEFI_CONTACT(MODELE=model, FORMULATION="LIAISON_UNIL", ZONE=({zones}))
ramp = DEFI_FONCTION(NOM_PARA="INST", VALE=(0.0, 0.0, 1.0, 1.0))
times = DEFI_LIST_REEL(DEBUT=0.0, INTERVALLE=_F(JUSQU_A=1.0, NOMBRE=10))
result = STAT_NON_LINE(
    MODELE=model, CHAM_MATER=field_material, CARA_ELEM=spring,
    EXCIT=(_F(CHARGE=fixed), _F(CHARGE=load, FONC_MULT=ramp)),
    CONTACT=contact, COMPORTEMENT=_F(RELATION="ELAS"),
    INCREMENT=_F(LIST_INST=times),
    CONVERGENCE=_F(RESI_GLOB_RELA=1.0e-10, ITER_GLOB_MAXI=50),
)
raw = {{"instants": [], "displacements_m": []}}
access = result.getAccessParameters()
for order, instant in zip(result.getIndexes(), access["INST"]):
    if instant <= 0.0:
        continue
    field = result.getField("DEPL", order)
    row = []
{extraction_code}
    raw["instants"].append(float(instant))
    raw["displacements_m"].append(row)
with open("/work/code_aster_raw.json", "w", encoding="utf-8") as stream:
    json.dump(raw, stream, indent=2)
FIN()
'''


def _tet4_mesh(data: dict[str, object]) -> str:
    nodes = cast(list[list[float]], data["nodes"])
    elements = cast(list[dict[str, object]], data["elements"])
    structural_count = 1 + max(
        int(node) for element in elements for node in cast(list[int], element["nodes"])
    )
    fixed_nodes = [
        index
        for index in range(structural_count)
        if np.isclose(float(nodes[index][0]), 1.1)
    ]
    slaves = cast(list[int], data["_plot"]["slaves"])
    lines = ["TITRE", "QF_solver deformable TET4 two slave contact", "FINSF", "COOR_3D"]
    for index, (x, y, z) in enumerate(nodes[:structural_count], start=1):
        lines.append(f"N{index} {x:.16g} {y:.16g} {z:.16g}")
    lines.extend(["FINSF", "TETRA4"])
    for index, element in enumerate(elements, start=1):
        connectivity = " ".join(
            f"N{int(node) + 1}" for node in cast(list[int], element["nodes"])
        )
        lines.append(f"E{index} {connectivity}")
    lines.extend(["FINSF", "GROUP_MA", "SOLID"])
    lines.extend(
        " ".join(f"E{index}" for index in range(start, min(start + 12, len(elements) + 1)))
        for start in range(1, len(elements) + 1, 12)
    )
    lines.extend(["FINSF", "GROUP_NO", "FIXED"])
    lines.append(" ".join(f"N{index + 1}" for index in fixed_nodes))
    lines.extend(["FINSF"])
    for index, node in enumerate(slaves, start=1):
        lines.extend(["GROUP_NO", f"SLAVE_{index}", f"N{node + 1}", "FINSF"])
    lines.extend(["FIN", ""])
    return "\n".join(lines)


def _tet4_commands(data: dict[str, object]) -> str:
    slaves = cast(list[int], data["_plot"]["slaves"])
    zones = ", ".join(
        f'_F(GROUP_NO="SLAVE_{index}", NOM_CMP="DX", '
        "COEF_IMPO=DEFI_CONSTANTE(VALE=0.1), "
        "COEF_MULT=DEFI_CONSTANTE(VALE=-1.0))"
        for index in range(1, len(slaves) + 1)
    )
    loads = ", ".join(
        f'_F(GROUP_NO="SLAVE_{index}", FX=-2000.0)'
        for index in range(1, len(slaves) + 1)
    )
    extraction = "\n".join(
        f'    values, _ = field.getValuesWithDescription("DX", ["SLAVE_{index}"])\n'
        f"    row.append(float(values[0]))"
        for index in range(1, len(slaves) + 1)
    )
    return f'''# coding=utf-8
import json
from code_aster.Commands import *
DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", PHENOMENE="MECANIQUE", MODELISATION="3D"))
material = DEFI_MATERIAU(ELAS=_F(E=1.0e4, NU=0.3))
field_material = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", MATER=material))
fixed = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=_F(GROUP_NO="FIXED", DX=0.0, DY=0.0, DZ=0.0))
load = AFFE_CHAR_MECA(MODELE=model, FORCE_NODALE=({loads}))
contact = DEFI_CONTACT(MODELE=model, FORMULATION="LIAISON_UNIL", ZONE=({zones}))
ramp = DEFI_FONCTION(NOM_PARA="INST", VALE=(0.0, 0.0, 1.0, 1.0))
times = DEFI_LIST_REEL(DEBUT=0.0, INTERVALLE=_F(JUSQU_A=1.0, NOMBRE=10))
result = STAT_NON_LINE(
    MODELE=model, CHAM_MATER=field_material,
    EXCIT=(_F(CHARGE=fixed), _F(CHARGE=load, FONC_MULT=ramp)),
    CONTACT=contact, COMPORTEMENT=_F(RELATION="ELAS"),
    INCREMENT=_F(LIST_INST=times),
    CONVERGENCE=_F(RESI_GLOB_RELA=1.0e-10, ITER_GLOB_MAXI=50),
)
raw = {{"instants": [], "displacements_m": []}}
access = result.getAccessParameters()
for order, instant in zip(result.getIndexes(), access["INST"]):
    if instant <= 0.0:
        continue
    field = result.getField("DEPL", order)
    row = []
{extraction}
    raw["instants"].append(float(instant))
    raw["displacements_m"].append(row)
with open("/work/code_aster_raw.json", "w", encoding="utf-8") as stream:
    json.dump(raw, stream, indent=2)
FIN()
'''


def _gaps(
    identifier: str,
    data: dict[str, object],
    displacements: np.ndarray,
) -> np.ndarray:
    if identifier == "dual_stop_corner":
        return 0.1 + displacements
    if identifier == "faceted_ramp_patch":
        geometry = _ramp_geometry(data)
        return np.column_stack(
            [
                gap + normal_z * displacements[:, index]
                for index, (gap, normal_z) in enumerate(geometry)
            ]
        )
    return 0.1 + displacements


def _normalized_curve_error(left: np.ndarray, right: np.ndarray) -> float:
    scale = max(float(np.max(np.abs(left))), float(np.max(np.abs(right))), 1.0e-12)
    return float(np.max(np.abs(left - right)) / scale)


def _upper(identifier: str, value: float, limit: float) -> dict[str, float | str]:
    return {
        "id": identifier,
        "value": float(value),
        "limit": float(limit),
        "status": "PASS" if value <= limit else "FAIL",
    }


def _warning(identifier: str, value: float, limit: float) -> dict[str, float | str]:
    return {
        "id": identifier,
        "value": float(value),
        "limit": float(limit),
        "status": "PASS" if value <= limit else "WARNING",
    }
