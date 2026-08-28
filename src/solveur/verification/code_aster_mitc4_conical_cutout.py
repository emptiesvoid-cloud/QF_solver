"""Same-mesh Code_Aster DKQ correlation for the MITC4 conical cutout panel."""

from __future__ import annotations

from solveur.paths import project_root

import json
import shutil
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from solveur.api import solve_model
from solveur.core.assembly.assembler import GlobalAssembler
from solveur.core.model import FiniteElementModel
from solveur.io.manifest import write_json_file
from solveur.verification.code_aster_tl_structural import CODE_ASTER_IMAGE, run_code_aster
from solveur.verification.mitc4_conical_cutout import (
    STUDY_ID as INTERNAL_STUDY_ID,
    _outer_ring_nodes,
    _relative,
    _vector_displacements,
    build_conical_cutout_model,
)
from solveur.verification.vnv_manifest import write_vnv_manifest


STUDY_ID = "VNV-MITC4-CONICAL-CUTOUT-CODEASTER-DKQ-014"


class CodeAsterMitc4ConicalCutoutCorrelation:
    """Compare MITC4 and Code_Aster DKQ observables on common QUAD4 facets."""

    study_id = STUDY_ID
    meshes = ((8, 24), (12, 36), (16, 48))

    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir).resolve()

    def run(self) -> dict[str, Any]:
        """Run all mesh levels and write portable external-correlation evidence."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        rows: list[dict[str, Any]] = [
            self._run_mesh(radial, circumferential) for radial, circumferential in self.meshes
        ]
        fine = rows[-1]
        checks = [
            _check("fine_probe_uz_difference", float(fine["probe_uz_difference"]), 0.05),
            _check("fine_displacement_vector_difference", float(fine["vector_difference"]), 0.08),
            _check("fine_reaction_resultant_difference", float(fine["reaction_resultant_difference"]), 0.02),
            _check("qf_final_increment", _relative(rows[-1]["qf_probe_uz_m"], rows[-2]["qf_probe_uz_m"]), 0.05),
            _check(
                "code_aster_final_increment",
                _relative(rows[-1]["code_aster_probe_uz_m"], rows[-2]["code_aster_probe_uz_m"]),
                0.05,
            ),
        ]
        summary: dict[str, Any] = {
            "study_id": STUDY_ID,
            "status": "PASS_EXTERNAL_CORRELATION" if all(item["status"] == "PASS" for item in checks) else "WARNING",
            "maturity": "engineering_internal_supplementary_evidence",
            "internal_study": INTERNAL_STUDY_ID,
            "external_solver": {
                "name": "Code_Aster",
                "version": "18.1.0",
                "image": CODE_ASTER_IMAGE,
                "element": "DKQ on QUAD4",
            },
            "qf_element": "MITC4 isotropic shell",
            "comparison_basis": (
                "Common QUAD4 nodal coordinates and connectivity, isotropic material, thickness, "
                "outer-rim clamp and QF_solver-consistent nodal pressure vector."
            ),
            "same_mesh": True,
            "rows": rows,
            "checks": checks,
            "limitations": [
                "DKQ is a Kirchhoff quadrilateral whereas MITC4 is Reissner-Mindlin.",
                "The conical surface is represented by common planar facets in both solvers.",
                "The transferred nodal pressure is an exact QF_solver load vector, not an independent distributed-load convention.",
                "Free-edge stress peaks at the opening are not acceptance observables.",
                "No geometric nonlinearity, follower pressure, contact or buckling is covered.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._plot(rows)
        (self.output_dir / "report.md").write_text(_markdown(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, STUDY_ID)
        self._publish_reference()
        return summary

    def _run_mesh(self, radial: int, circumferential: int) -> dict[str, Any]:
        model, probe = build_conical_cutout_model(radial, circumferential)
        qf_result = solve_model(model)
        qf = _vector_displacements(qf_result, model)
        work = self.output_dir / f"{radial}x{circumferential}"
        work.mkdir(exist_ok=True)
        stem = "conical_cutout"
        (work / f"{stem}.mail").write_text(code_aster_quad_mesh(model), encoding="ascii")
        (work / f"{stem}.comm").write_text(code_aster_static_comm(model), encoding="utf-8")
        run_code_aster(work, stem, timeout=900)
        raw = json.loads((work / "code_aster_raw.json").read_text(encoding="utf-8"))
        aster = np.asarray(raw["displacements"], dtype=float)
        aster_reaction = np.asarray(raw["reaction_resultant_n"], dtype=float)
        qf_reaction = np.asarray(qf_result.audit.equilibrium["reaction_resultant"], dtype=float)
        displacement_scale = max(float(np.linalg.norm(aster)), 1.0e-30)
        reaction_scale = max(float(np.linalg.norm(aster_reaction)), 1.0e-30)
        return {
            "radial_elements": radial,
            "circumferential_elements": circumferential,
            "elements": len(model.elements),
            "nodes": model.node_count,
            "probe_node": probe,
            "qf_probe_uz_m": float(qf[probe, 2]),
            "code_aster_probe_uz_m": float(aster[probe, 2]),
            "probe_uz_difference": _relative(qf[probe, 2], aster[probe, 2]),
            "vector_difference": float(np.linalg.norm(qf - aster) / displacement_scale),
            "qf_reaction_resultant_n": qf_reaction.tolist(),
            "code_aster_reaction_resultant_n": aster_reaction.tolist(),
            "reaction_resultant_difference": float(
                np.linalg.norm(qf_reaction - aster_reaction) / reaction_scale
            ),
        }

    def _plot(self, rows: list[dict[str, Any]]) -> None:
        elements = [int(row["elements"]) for row in rows]
        figure, axes = plt.subplots(1, 2, figsize=(10.2, 4.2))
        axes[0].semilogx(elements, [abs(float(row["qf_probe_uz_m"])) for row in rows], "o-", color="#087f5b", label="QF_solver MITC4")
        axes[0].semilogx(elements, [abs(float(row["code_aster_probe_uz_m"])) for row in rows], "s--", color="#c92a2a", label="Code_Aster DKQ")
        axes[0].set(xlabel="Elements QUAD4", ylabel="|UZ sonde| [m]", title="Convergence meme maillage")
        axes[0].grid(True, which="both", alpha=0.25)
        axes[0].legend()
        axes[1].loglog(elements, [float(row["probe_uz_difference"]) for row in rows], "o-", color="#087f5b", label="Sonde UZ")
        axes[1].loglog(elements, [float(row["vector_difference"]) for row in rows], "s-", color="#1971c2", label="Vecteur U")
        axes[1].loglog(elements, [float(row["reaction_resultant_difference"]) for row in rows], "^-", color="#c92a2a", label="Resultante R")
        axes[1].axhline(0.05, color="#495057", linestyle="--", linewidth=1.0, label="Seuil U")
        axes[1].set(xlabel="Elements QUAD4", ylabel="Ecart relatif", title="Ecart QF_solver / Code_Aster")
        axes[1].grid(True, which="both", alpha=0.25)
        axes[1].legend()
        figure.tight_layout()
        figure.savefig(self.output_dir / "conical_cutout_code_aster_correlation.png", dpi=180)
        plt.close(figure)

    def _publish_reference(self) -> None:
        root = project_root()
        reference = root / "qualification" / "vnv" / "external" / "code_aster_mitc4_conical_cutout" / "reference"
        reference.mkdir(parents=True, exist_ok=True)
        names = ("summary.json", "report.md", "vnv_manifest.json", "conical_cutout_code_aster_correlation.png")
        for name in names:
            shutil.copy2(self.output_dir / name, reference / name)
        assets = root / "docs" / "assets" / "reviews"
        assets.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.output_dir / "conical_cutout_code_aster_correlation.png", assets / "conical_cutout_code_aster_correlation.png")


def code_aster_quad_mesh(model: FiniteElementModel) -> str:
    """Write an ASTER QUAD4 mesh preserving QF node and element ordering."""
    fixed = _outer_ring_nodes(model.nodes)
    lines = ["TITRE", "QF_solver MITC4 conical cutout same-mesh correlation", "FINSF", "COOR_3D"]
    lines.extend(
        f"N{index + 1} {point[0]:.16g} {point[1]:.16g} {point[2]:.16g}"
        for index, point in enumerate(model.nodes)
    )
    lines.extend(["FINSF", "QUAD4"])
    lines.extend(
        f"M{index + 1} " + " ".join(f"N{int(node) + 1}" for node in element.nodes)
        for index, element in enumerate(model.elements)
    )
    lines.extend(["FINSF", "GROUP_MA", "SHELL"])
    lines.extend(f"M{index + 1}" for index in range(len(model.elements)))
    lines.extend(["FINSF", "GROUP_NO", "FIXED"])
    lines.extend(f"N{int(node) + 1}" for node in fixed)
    lines.extend(["FINSF", "GROUP_NO", "NALL"])
    lines.extend(f"N{index + 1}" for index in range(model.node_count))
    lines.extend(["FINSF", "FIN"])
    return "\n".join(lines) + "\n"


def code_aster_static_comm(model: FiniteElementModel) -> str:
    """Return a Code_Aster DKQ deck with the exact QF consistent load vector."""
    loads = _qf_consistent_translation_loads(model)
    definitions = ",\n        ".join(
        f'_F(NOEUD="N{node}", {component}={value:.16g})'
        for node, component, value in loads
    )
    return f'''# coding=utf-8
import json
from code_aster.Commands import *

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(
    MAILLAGE=mesh,
    AFFE=_F(GROUP_MA="SHELL", PHENOMENE="MECANIQUE", MODELISATION="DKT"),
)
material = DEFI_MATERIAU(ELAS=_F(E=7.0e10, NU=0.33, RHO=2700.0))
field = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SHELL", MATER=material))
shell = AFFE_CARA_ELEM(MODELE=model, COQUE=_F(GROUP_MA="SHELL", EPAIS=0.004))
fixed = AFFE_CHAR_MECA(
    MODELE=model,
    DDL_IMPO=_F(GROUP_NO="FIXED", DX=0.0, DY=0.0, DZ=0.0, DRX=0.0, DRY=0.0, DRZ=0.0),
)
load = AFFE_CHAR_MECA(
    MODELE=model,
    FORCE_NODALE=(
        {definitions}
    ),
)
result = MECA_STATIQUE(
    MODELE=model, CHAM_MATER=field, CARA_ELEM=shell, EXCIT=(_F(CHARGE=fixed), _F(CHARGE=load)),
)
order = result.getIndexes()[-1]
depl = result.getField("DEPL", order)
result = CALC_CHAMP(reuse=result, RESULTAT=result, FORCE=("REAC_NODA",))
reaction = result.getField("REAC_NODA", order)
dx, _ = depl.getValuesWithDescription("DX", ["NALL"])
dy, _ = depl.getValuesWithDescription("DY", ["NALL"])
dz, _ = depl.getValuesWithDescription("DZ", ["NALL"])
rfx, _ = reaction.getValuesWithDescription("DX", ["FIXED"])
rfy, _ = reaction.getValuesWithDescription("DY", ["FIXED"])
rfz, _ = reaction.getValuesWithDescription("DZ", ["FIXED"])
with open("/work/code_aster_raw.json", "w", encoding="utf-8") as stream:
    json.dump({{
        "displacements": [[float(x), float(y), float(z)] for x, y, z in zip(dx, dy, dz)],
        "reaction_resultant_n": [float(sum(rfx)), float(sum(rfy)), float(sum(rfz))],
    }}, stream)
FIN()
'''


def _qf_consistent_translation_loads(model: FiniteElementModel) -> list[tuple[int, str, float]]:
    dofs = model.dof_manager()
    vector = GlobalAssembler().assemble_loads(model, dofs)
    loads: list[tuple[int, str, float]] = []
    for node in range(model.node_count):
        for dof, component in (("UX", "FX"), ("UY", "FY"), ("UZ", "FZ")):
            value = float(vector[dofs.index(node, dof)])
            if abs(value) > 1.0e-14:
                loads.append((node + 1, component, value))
    return loads


def _check(identifier: str, value: float, limit: float) -> dict[str, Any]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if np.isfinite(value) and value <= limit else "FAIL"}


def _markdown(summary: dict[str, Any]) -> str:
    lines = [
        f"# {summary['study_id']}",
        "",
        f"Statut : **{summary['status']}**.",
        "",
        "| Maillage | UZ QF [m] | UZ Code_Aster [m] | Ecart sonde | Ecart vecteur | Ecart reaction |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary["rows"]:
        lines.append(
            f"| {row['radial_elements']}x{row['circumferential_elements']} | {row['qf_probe_uz_m']:.7e} | "
            f"{row['code_aster_probe_uz_m']:.7e} | {100 * row['probe_uz_difference']:.4f} % | "
            f"{100 * row['vector_difference']:.4f} % | {100 * row['reaction_resultant_difference']:.4f} % |"
        )
    lines.extend([
        "",
        "Les coordonnees, connectivites QUAD4, materiau, epaisseur, blocages et forces nodales coherentes sont communs.",
        "`REAC_NODA` est somme uniquement sur les DDL de translation du bord encastre.",
    ])
    return "\n".join(lines) + "\n"
