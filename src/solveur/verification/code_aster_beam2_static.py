"""Same-mesh Code_Aster static correlation for a slender BEAM2 cantilever."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from solveur.api import solve_model
from solveur.io.json_reader import JsonModelReader
from solveur.io.manifest import write_json_file
from solveur.verification.code_aster_tl_structural import CODE_ASTER_IMAGE, run_code_aster
from solveur.verification.vnv_manifest import write_vnv_manifest


class CodeAsterBeam2StaticCampaign:
    """Compare a slender multi-element BEAM2 cantilever to ``POU_D_E``."""

    study_id = "VNV-BEAM2-STATIC-CODEASTER-POUDE-020"
    mesh_levels = (4, 8, 16)
    relative_limit = 0.02
    length_m = 10.0
    young_pa = 210.0e9
    area_m2 = 0.01
    iy_m4 = 2.0e-6
    iz_m4 = 3.0e-6
    torsion_m4 = 5.0e-6
    density = 7800.0
    load_n = 1000.0

    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir).resolve()

    def run(self) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        rows = [self._run_level(elements) for elements in self.mesh_levels]
        qf_increment = _relative(rows[-1]["qf_tip_uy_m"], rows[-2]["qf_tip_uy_m"])
        aster_increment = _relative(rows[-1]["code_aster_tip_uy_m"], rows[-2]["code_aster_tip_uy_m"])
        checks = [
            _check("same_mesh_all_levels", all(row["same_mesh"] for row in rows), True),
            _check("fine_static_displacement_error", rows[-1]["relative_difference"], self.relative_limit),
            _check("qf_final_mesh_increment", qf_increment, self.relative_limit),
            _check("code_aster_final_mesh_increment", aster_increment, self.relative_limit),
            _check("finite_results", all(row["finite_results"] for row in rows), True),
        ]
        summary: dict[str, Any] = {
            "study_id": self.study_id,
            "status": "PASS_EXTERNAL_CORRELATION" if all(item["status"] == "PASS" for item in checks) else "FAIL",
            "maturity": "experimental",
            "scope": "BEAM2 slender linear static same-mesh correlation",
            "external_solver": {
                "name": "Code_Aster",
                "version": "18.1.0",
                "image": CODE_ASTER_IMAGE,
                "element": "POU_D_E (Euler-Bernoulli)",
            },
            "model": {
                "length_m": self.length_m,
                "same_mesh": True,
                "load_n": self.load_n,
                "observable": "tip UY",
                "qf_formulation": "Timoshenko BEAM2",
                "external_formulation": "Euler-Bernoulli POU_D_E",
            },
            "mesh_level_count": len(rows),
            "rows": rows,
            "fine_relative_difference": rows[-1]["relative_difference"],
            "qf_final_mesh_increment": qf_increment,
            "code_aster_final_mesh_increment": aster_increment,
            "checks": checks,
            "limitations": [
                "The comparison is deliberately slender so the Timoshenko shear correction remains small.",
                "Thick beams, variable sections, joints, damping, contact and geometric nonlinearity are excluded.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._plot(rows)
        (self.output_dir / "report.md").write_text(_report(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary

    def _run_level(self, element_count: int) -> dict[str, Any]:
        model_data = _model(element_count, self)
        qf_model = JsonModelReader().from_dict(model_data)
        qf_result = solve_model(qf_model, enforce_policy=False)
        tip = element_count
        qf_tip = float(qf_result.displacements[qf_result.dofs.index(tip, "UY")])
        work = self.output_dir / f"n{element_count}"
        work.mkdir(exist_ok=True)
        stem = "beam_static"
        (work / f"{stem}.mail").write_text(_mesh(element_count, self.length_m), encoding="ascii")
        (work / f"{stem}.comm").write_text(_commands(element_count, self), encoding="utf-8")
        run_code_aster(work, stem, timeout=900)
        raw = json.loads((work / "code_aster_raw.json").read_text(encoding="utf-8"))
        aster_tip = float(raw["tip_uy_m"])
        return {
            "element_count": element_count,
            "node_count": element_count + 1,
            "same_mesh": True,
            "qf_tip_uy_m": qf_tip,
            "code_aster_tip_uy_m": aster_tip,
            "relative_difference": _relative(qf_tip, aster_tip),
            "finite_results": bool(np.isfinite(qf_tip) and np.isfinite(aster_tip)),
        }

    def _plot(self, rows: list[dict[str, Any]]) -> None:
        elements = [int(row["element_count"]) for row in rows]
        figure, axes = plt.subplots(1, 2, figsize=(10.2, 4.0), constrained_layout=True)
        axes[0].plot(elements, [abs(row["qf_tip_uy_m"]) for row in rows], "o-", label="QF_solver")
        axes[0].plot(elements, [abs(row["code_aster_tip_uy_m"]) for row in rows], "s--", label="Code_Aster")
        axes[0].set(xlabel="BEAM2/POU_D_E", ylabel="|UY pointe| [m]", title="Convergence statique")
        axes[1].semilogy(elements, [row["relative_difference"] for row in rows], "o-", color="#c92a2a")
        axes[1].axhline(self.relative_limit, linestyle="--", color="#495057", label="Seuil 2 %")
        axes[1].set(xlabel="Elements", ylabel="Ecart relatif", title="QF_solver / Code_Aster")
        for axis in axes:
            axis.grid(True, alpha=0.25)
            axis.legend()
        figure.savefig(self.output_dir / "beam2_static_code_aster.png", dpi=180)
        plt.close(figure)


def _model(element_count: int, campaign: CodeAsterBeam2StaticCampaign) -> dict[str, Any]:
    nodes = [[campaign.length_m * index / element_count, 0.0, 0.0] for index in range(element_count + 1)]
    return {
        "analysis": {"type": "linear_static", "method": "direct"},
        "nodes": nodes,
        "elements": [
            {"type": "BEAM2", "nodes": [index, index + 1], "material": "beam"}
            for index in range(element_count)
        ],
        "materials": {
            "beam": {
                "type": "beam_isotropic",
                "E": campaign.young_pa,
                "nu": 0.3,
                "A": campaign.area_m2,
                "Iy": campaign.iy_m4,
                "Iz": campaign.iz_m4,
                "J": campaign.torsion_m4,
                "density": campaign.density,
                "reference_vector": [0.0, 1.0, 0.0],
            }
        },
        "fixed_dofs": [{"node": 0, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]}],
        "loads": [{"node": element_count, "dof": "UY", "value": campaign.load_n}],
    }


def _mesh(element_count: int, length: float) -> str:
    lines = ["TITRE", "QF_solver BEAM2 static external correlation", "FINSF", "COOR_3D"]
    lines.extend(f"N{i + 1} {length * i / element_count:.16g} 0.0 0.0" for i in range(element_count + 1))
    lines.extend(["FINSF", "SEG2"])
    lines.extend(f"E{i + 1} N{i + 1} N{i + 2}" for i in range(element_count))
    lines.extend(["FINSF", "GROUP_MA", "BEAM", *(f"E{i + 1}" for i in range(element_count)), "FINSF", "GROUP_NO", "ROOT", "N1", "FINSF", "GROUP_NO", "TIP", f"N{element_count + 1}", "FINSF", "FIN"])
    return "\n".join(lines) + "\n"


def _commands(element_count: int, campaign: CodeAsterBeam2StaticCampaign) -> str:
    return f'''# coding=utf-8
import json
from code_aster.Commands import *

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(MAILLAGE=mesh, AFFE=_F(GROUP_MA="BEAM", PHENOMENE="MECANIQUE", MODELISATION="POU_D_E"))
material = DEFI_MATERIAU(ELAS=_F(E={campaign.young_pa:.16g}, NU=0.3))
field = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA="BEAM", MATER=material))
section = AFFE_CARA_ELEM(MODELE=model, POUTRE=_F(GROUP_MA="BEAM", SECTION="GENERALE", CARA=("A", "IY", "IZ", "JX"), VALE=({campaign.area_m2:.16g}, {campaign.iy_m4:.16g}, {campaign.iz_m4:.16g}, {campaign.torsion_m4:.16g})))
boundary = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=_F(GROUP_NO="ROOT", DX=0.0, DY=0.0, DZ=0.0, DRX=0.0, DRY=0.0, DRZ=0.0))
force = AFFE_CHAR_MECA(MODELE=model, FORCE_NODALE=_F(GROUP_NO="TIP", FY={campaign.load_n:.16g}))
static = MECA_STATIQUE(MODELE=model, CHAM_MATER=field, CARA_ELEM=section, EXCIT=(_F(CHARGE=boundary), _F(CHARGE=force)))
values, _ = static.getField("DEPL", 1).getValuesWithDescription("DY", ["TIP"])
with open("/work/code_aster_raw.json", "w", encoding="utf-8") as stream:
    json.dump({{"tip_uy_m": float(values[0])}}, stream, indent=2)
FIN()
'''


def _relative(value: float, reference: float) -> float:
    return abs(value - reference) / max(abs(reference), 1.0e-30)


def _check(identifier: str, value: object, limit: object) -> dict[str, object]:
    passed = value == limit if isinstance(limit, bool) else bool(float(value) <= float(limit))
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if passed else "FAIL"}


def _report(summary: dict[str, Any]) -> str:
    lines = [f"# {summary['study_id']}", "", f"Statut automatise : **{summary['status']}**.", "", "| Elements | UY QF [m] | UY Code_Aster [m] | Ecart |", "| ---: | ---: | ---: | ---: |"]
    for row in summary["rows"]:
        lines.append(f"| {row['element_count']} | {row['qf_tip_uy_m']:.9e} | {row['code_aster_tip_uy_m']:.9e} | {100 * row['relative_difference']:.6g} % |")
    lines.extend(["", "![Convergence BEAM2 statique](beam2_static_code_aster.png)", "", "La comparaison est limitee a une poutre elancee : POU_D_E est Euler-Bernoulli et BEAM2 QF_solver est Timoshenko.", ""])
    return "\n".join(lines)
