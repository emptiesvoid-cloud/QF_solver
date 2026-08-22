"""Code_Aster correlation for a curved MITC3+ projected-axis laminate."""

from __future__ import annotations

import json
import math
import shutil
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

from solveur.api import check_mesh, solve_model
from solveur.io.manifest import write_json_file
from solveur.paths import project_root
from solveur.verification.calculix_mitc3_curved_composite import (
    LAYUP,
    REFERENCE_DIRECTION,
    _qf_model,
    build_curved_s6_mesh,
)
from solveur.verification.code_aster_tl_structural import CODE_ASTER_IMAGE, run_code_aster
from solveur.verification.mitc3_models import LAMINATE_MATERIAL
from solveur.verification.vnv_manifest import write_vnv_manifest


STUDY_ID = "VNV-MITC3-LAMINATE-CURVED-PROJECTED-CODEASTER-DST-025"


class CodeAsterMitc3CurvedLaminateCampaign:
    """Compare a faceted projected-axis MITC3+ laminate with Code_Aster DST."""

    study_id = STUDY_ID
    fine_vector_limit = 0.01
    refined_vector_limit = 0.01
    final_increment_limit = 0.05
    curved_shell_residual_limit = 1.0e-7
    load_cases = ("mixed", "transverse", "axial")

    def __init__(
        self,
        output_dir: str | Path,
        *,
        levels: tuple[tuple[int, int], ...] = ((8, 4), (16, 8), (24, 12), (32, 16)),
        publish_reference: bool = True,
        study_id: str = STUDY_ID,
        load_cases: tuple[str, ...] = ("mixed", "transverse", "axial"),
    ) -> None:
        self.output_dir = Path(output_dir).resolve()
        self.levels = tuple((int(nx), int(ny)) for nx, ny in levels)
        self.publish_reference = bool(publish_reference)
        self.study_id = str(study_id)
        self.load_cases = tuple(str(case) for case in load_cases)
        unsupported = set(self.load_cases) - set(type(self).load_cases)
        if not self.load_cases or unsupported:
            raise ValueError(f"Unsupported curved MITC3 load cases: {sorted(unsupported)}")
        if len(self.levels) < 2 or any(nx < 2 or ny < 1 for nx, ny in self.levels):
            raise ValueError("Curved MITC3 levels require at least two positive mesh pairs.")

    def run(self) -> dict[str, Any]:
        """Run all levels and write the normalized evidence."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        family_rows = {
            load_case: [self._run_level(nx, ny, load_case) for nx, ny in self.levels]
            for load_case in self.load_cases
        }
        family_summaries = {
            load_case: self._family_summary(rows)
            for load_case, rows in family_rows.items()
        }
        rows = family_rows[self.load_cases[0]]
        checks = [check for summary in family_summaries.values() for check in summary["checks"]]
        summary: dict[str, Any] = {
            "study_id": self.study_id,
            "status": "PASS_EXTERNAL_CORRELATION" if all(item["status"] == "PASS" for item in checks) else "WARNING",
            "maturity": "verified_development_external_correlation",
            "qf_element": "MITC3+ shell_laminate",
            "external_solver": {
                "name": "Code_Aster",
                "version": "18.1.0",
                "image": CODE_ASTER_IMAGE,
                "element": "DST / TRIA3 / DEFI_COMPOSITE",
            },
            "geometry": {"kind": "faceted_cylindrical_panel", "length_m": 1.0, "radius_m": 0.5, "opening_deg": 60.0},
            "geometry_count": 1,
            "load_family_count": len(self.load_cases),
            "load_families": family_summaries,
            "layup_deg": list(LAYUP),
            "reference_direction_global": REFERENCE_DIRECTION.tolist(),
            "orientation_rule": (
                "The same global reference vector is projected by QF_solver and by Code_Aster "
                "VECTEUR on each shell facet; ply angles are then applied in that user frame."
            ),
            "comparison_basis": {
                "same_corner_mesh": True,
                "same_triangles": True,
                "same_boundary_nodes": True,
                "same_load_resultants": True,
                "same_layup": True,
                "observable": "weighted right-edge UX and UZ, mesh convergence and equilibrium",
            },
            "rows": rows,
            "checks": checks,
            "figures": [
                "convergence_qf_code_aster.png",
                "curved_laminate_deformation_qf_code_aster.png",
                "convergence_qf_code_aster_transverse.png",
                "curved_laminate_deformation_qf_code_aster_transverse.png",
                "convergence_qf_code_aster_axial.png",
                "curved_laminate_deformation_qf_code_aster_axial.png",
            ],
            "limitations": [
                "DST and MITC3+ are distinct shell formulations; this is an observable correlation, not matrix identity.",
                "The mesh is faceted. A quadratic curved geometry effect is intentionally excluded.",
                "Only global displacement observables are accepted here; ply stresses, S13, damage and delamination remain open.",
                "The result does not promote the MITC3 curved laminate maturity without Owner review.",
            ],
        }
        for index, load_case in enumerate(self.load_cases):
            suffix = "" if index == 0 else f"_{load_case}"
            self._plot_convergence(family_rows[load_case], suffix=suffix)
            self._plot_deformation(family_rows[load_case][-1], suffix=suffix)
        write_json_file(self.output_dir / "summary.json", summary)
        (self.output_dir / "report.md").write_text(_report(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, self.study_id)
        if self.publish_reference:
            self._publish_reference()
        return summary

    def _family_summary(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        fine = rows[-1]
        checks = [
            _check("fine_displacement_vector_difference", float(fine["vector_difference"]), self.fine_vector_limit),
            _check(
                "refined_displacement_vector_difference",
                max(float(row["vector_difference"]) for row in rows[-2:]),
                self.refined_vector_limit,
            ),
            _check("qf_final_mesh_increment", _relative(rows[-1]["qf_uz"], rows[-2]["qf_uz"]), self.final_increment_limit),
            _check(
                "code_aster_final_mesh_increment",
                _relative(rows[-1]["code_aster_uz"], rows[-2]["code_aster_uz"]),
                self.final_increment_limit,
            ),
            _check(
                "qf_free_residual",
                max(float(row["qf_free_residual"]) for row in rows),
                self.curved_shell_residual_limit,
            ),
        ]
        return {
            "status": "PASS_EXTERNAL_CORRELATION" if all(item["status"] == "PASS" for item in checks) else "WARNING",
            "mesh_level_count": len(rows),
            "mesh_levels": [f"{row['nx']}x{row['ny']}" for row in rows],
            "rows": rows,
            "checks": checks,
            "fine_vector_difference": float(fine["vector_difference"]),
        }

    def _run_level(self, nx: int, ny: int, load_case: str) -> dict[str, Any]:
        model, mesh = _qf_model(nx, ny, load_case=load_case)
        qf_report = check_mesh(model)
        qf = solve_model(model, enforce_policy=False)
        qf_displacement = _nodal_displacement(qf, model.node_count)
        qf_ux = _weighted_edge(qf_displacement, mesh.tip_nodes, mesh.tip_weights, 0)
        qf_uz = _weighted_edge(qf_displacement, mesh.tip_nodes, mesh.tip_weights, 2)

        work = self.output_dir / f"{load_case}_level_{nx}x{ny}"
        work.mkdir(parents=True, exist_ok=True)
        stem = "mitc3_curved_laminate"
        (work / f"{stem}.mail").write_text(
            _mesh_text(model.nodes, mesh.triangles, mesh.fixed_nodes, mesh.tip_nodes), encoding="ascii"
        )
        (work / f"{stem}.comm").write_text(
            _command_text(len(mesh.tip_nodes), mesh.tip_weights, load_case=load_case), encoding="utf-8"
        )
        run_code_aster(work, stem, timeout=1800)
        raw = json.loads((work / "code_aster_raw.json").read_text(encoding="utf-8"))
        aster_displacement = np.asarray(raw["displacements"], dtype=float)
        aster_ux = _weighted_edge(aster_displacement, mesh.tip_nodes, mesh.tip_weights, 0)
        aster_uz = _weighted_edge(aster_displacement, mesh.tip_nodes, mesh.tip_weights, 2)
        row = {
            "nx": nx,
            "ny": ny,
            "mitc3_elements": int(len(mesh.triangles)),
            "nodes": int(model.node_count),
            "qf_ux": qf_ux,
            "qf_uz": qf_uz,
            "code_aster_ux": aster_ux,
            "code_aster_uz": aster_uz,
            "vector_difference": float(
                np.linalg.norm([qf_ux - aster_ux, qf_uz - aster_uz])
                / max(np.linalg.norm([aster_ux, aster_uz]), 1.0e-30)
            ),
            "qf_mesh_status": qf_report.status,
            "qf_free_residual": float(qf.audit.equilibrium["free_relative_residual"]),
        }
        if (nx, ny) == self.levels[-1]:
            row["qf_displacement"] = qf_displacement.tolist()
            row["code_aster_displacement"] = aster_displacement.tolist()
        write_json_file(work / "comparison.json", row)
        return row

    def _plot_convergence(self, rows: list[dict[str, Any]], *, suffix: str = "") -> None:
        elements = [row["mitc3_elements"] for row in rows]
        figure, axes = plt.subplots(1, 2, figsize=(11.0, 4.4))
        axes[0].semilogx(elements, [abs(row["qf_uz"]) for row in rows], "o-", color="#0072B2", label="QF_solver MITC3+")
        axes[0].semilogx(elements, [abs(row["code_aster_uz"]) for row in rows], "s--", color="#D55E00", label="Code_Aster DST")
        axes[0].set(xlabel="Elements MITC3+", ylabel="|UZ bord droit| [m]", title="Convergence courbe")
        axes[0].grid(True, which="both", alpha=0.25)
        axes[0].legend(fontsize=8)
        axes[1].loglog(elements, [100.0 * row["vector_difference"] for row in rows], "^-", color="#009E73")
        axes[1].axhline(15.0, color="#CC79A7", linestyle="--", label="seuil fin 15 %")
        axes[1].set(xlabel="Elements MITC3+", ylabel="Ecart UX/UZ [%]", title="Correlation globale")
        axes[1].grid(True, which="both", alpha=0.25)
        axes[1].legend(fontsize=8)
        figure.tight_layout()
        figure.savefig(self.output_dir / f"convergence_qf_code_aster{suffix}.png", dpi=180)
        plt.close(figure)

    def _plot_deformation(self, row: dict[str, Any], *, suffix: str = "") -> None:
        mesh = build_curved_s6_mesh(int(row["nx"]), int(row["ny"]))
        nodes = mesh.nodes[: (int(row["nx"]) + 1) * (int(row["ny"]) + 1)]
        triangles = mesh.triangles
        qf = np.asarray(row["qf_displacement"], dtype=float)
        aster = np.asarray(row["code_aster_displacement"], dtype=float)
        amplitude = max(float(np.linalg.norm(qf, axis=1).max()), float(np.linalg.norm(aster, axis=1).max()), 1.0e-30)
        scale = 0.15 / amplitude
        figure = plt.figure(figsize=(11.0, 5.0))
        for index, (label, displacement, cmap) in enumerate((("QF_solver MITC3+", qf, "viridis"), ("Code_Aster DST", aster, "plasma")), start=1):
            axis = figure.add_subplot(1, 2, index, projection="3d")
            deformed = nodes + scale * displacement
            collection = Poly3DCollection(deformed[triangles], linewidth=0.06, alpha=0.92)
            values = np.linalg.norm(displacement, axis=1)[triangles].mean(axis=1)
            collection.set_array(values)
            collection.set_cmap(cmap)
            axis.add_collection3d(collection)
            axis.set(xlim=(-0.1, 1.1), ylim=(-0.35, 0.35), zlim=(-0.25, 0.25), xlabel="X [m]", ylabel="Y [m]", zlabel="Z [m]")
            axis.set_title(label)
            axis.set_box_aspect((1.0, 0.55, 0.55))
            axis.view_init(elev=24.0, azim=-58.0)
        figure.suptitle(f"MITC3+ multicouche courbe : deformee amplifiee x{scale:.3g}; couleur = |U|")
        figure.tight_layout()
        figure.savefig(self.output_dir / f"curved_laminate_deformation_qf_code_aster{suffix}.png", dpi=180)
        plt.close(figure)

    def _publish_reference(self) -> None:
        reference = project_root() / "qualification" / "vnv" / "external" / "code_aster_mitc3_curved_laminate" / "reference"
        reference.mkdir(parents=True, exist_ok=True)
        for name in (
            "summary.json",
            "report.md",
            "vnv_manifest.json",
            "convergence_qf_code_aster.png",
            "curved_laminate_deformation_qf_code_aster.png",
                "convergence_qf_code_aster_transverse.png",
                "curved_laminate_deformation_qf_code_aster_transverse.png",
                "convergence_qf_code_aster_axial.png",
            "curved_laminate_deformation_qf_code_aster_axial.png",
        ):
            source = self.output_dir / name
            if source.is_file():
                shutil.copy2(source, reference / name)


def _mesh_text(
    nodes: np.ndarray,
    triangles: np.ndarray,
    root_nodes: tuple[int, ...],
    tip_nodes: tuple[int, ...],
) -> str:
    """Write the common TRIA3 mesh and one load group per tip node."""
    lines = ["TITRE", "QF_solver MITC3 curved laminate correlation", "FINSF", "COOR_3D"]
    lines.extend(
        f"N{index + 1} {point[0]:.16g} {point[1]:.16g} {point[2]:.16g}"
        for index, point in enumerate(nodes)
    )
    lines.extend(["FINSF", "TRIA3"])
    lines.extend(
        f"M{index + 1} " + " ".join(f"N{int(node) + 1}" for node in triangle)
        for index, triangle in enumerate(triangles)
    )
    lines.extend(["FINSF", "GROUP_MA", "SHELL"])
    lines.extend(f"M{index + 1}" for index in range(len(triangles)))
    lines.extend(["FINSF", "GROUP_NO", "ROOT"])
    lines.extend(f"N{int(node) + 1}" for node in root_nodes)
    lines.extend(["FINSF", "GROUP_NO", "NALL"])
    lines.extend(f"N{index + 1}" for index in range(len(nodes)))
    lines.append("FINSF")
    for index, node in enumerate(tip_nodes):
        lines.extend(["GROUP_NO", f"TIP_{index:04d}", f"N{int(node) + 1}", "FINSF"])
    lines.append("FIN")
    return "\n".join(lines) + "\n"


def _command_text(tip_count: int, weights: np.ndarray, *, load_case: str = "mixed") -> str:
    if load_case not in {"mixed", "transverse", "axial"}:
        raise ValueError(f"Unsupported curved MITC3 load case: {load_case}")
    axial_force = 1000.0 if load_case in {"mixed", "axial"} else 0.0
    transverse_force = -20.0 if load_case == "mixed" else (-1000.0 if load_case == "transverse" else 0.0)
    layers = ",\n        ".join(f"_F(EPAIS=0.002, MATER=lamina, ORIENTATION={angle:.16g})" for angle in LAYUP)
    material = LAMINATE_MATERIAL
    loads = ",\n        ".join(
        f'_F(GROUP_NO="TIP_{index:04d}", FX={axial_force * float(weight):.16g}, FZ={transverse_force * float(weight):.16g})'
        for index, weight in enumerate(weights)
    )
    tip_reads = "\n".join(
        f'ux_{index}, _ = displacement.getValuesWithDescription("DX", ["TIP_{index:04d}"])\n'
        f'uz_{index}, _ = displacement.getValuesWithDescription("DZ", ["TIP_{index:04d}"])\n'
        f"tip_ux.append(float(ux_{index}[0]))\n"
        f"tip_uz.append(float(uz_{index}[0]))"
        for index in range(tip_count)
    )
    return f'''# coding=utf-8
import json
from code_aster.Commands import *

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SHELL", PHENOMENE="MECANIQUE", MODELISATION="DST"))
# These constants are intentionally identical to mitc3_models._laminate().
# A correlation deck must not introduce a second material definition.
lamina = DEFI_MATERIAU(ELAS_ORTH=_F(E_L={material["E1"]:.16g}, E_T={material["E2"]:.16g}, E_N={material["E2"]:.16g}, NU_LT={material["nu12"]:.16g}, NU_LN={material["nu12"]:.16g}, NU_TN={material["nu12"]:.16g}, G_LT={material["G12"]:.16g}, G_LN={material["G13"]:.16g}, G_TN={material["G23"]:.16g}, RHO={material["density"]:.16g}))
laminate = DEFI_COMPOSITE(COUCHE=(
        {layers}
))
field = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SHELL", MATER=laminate))
shell = AFFE_CARA_ELEM(MODELE=model, COQUE=_F(GROUP_MA="SHELL", EPAIS=0.008, COQUE_NCOU=4, VECTEUR=(0.7, 1.0, 0.2)))
fixed = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=_F(GROUP_NO="ROOT", DX=0.0, DY=0.0, DZ=0.0, DRX=0.0, DRY=0.0, DRZ=0.0))
load = AFFE_CHAR_MECA(MODELE=model, FORCE_NODALE=(
        {loads}
))
result = MECA_STATIQUE(MODELE=model, CHAM_MATER=field, CARA_ELEM=shell, EXCIT=(_F(CHARGE=fixed), _F(CHARGE=load)))
displacement = result.getField("DEPL", result.getIndexes()[-1])
dx, _ = displacement.getValuesWithDescription("DX", ["NALL"])
dy, _ = displacement.getValuesWithDescription("DY", ["NALL"])
dz, _ = displacement.getValuesWithDescription("DZ", ["NALL"])
tip_ux = []
tip_uz = []
{tip_reads}
with open("/work/code_aster_raw.json", "w", encoding="utf-8") as stream:
    json.dump({{"tip_ux": tip_ux, "tip_uz": tip_uz, "displacements": [[float(x), float(y), float(z)] for x, y, z in zip(dx, dy, dz)]}}, stream)
FIN()
'''


def _nodal_displacement(result: Any, node_count: int) -> np.ndarray:
    return np.asarray(
        [[result.displacements[result.dofs.index(node, component)] for component in ("UX", "UY", "UZ")] for node in range(node_count)],
        dtype=float,
    )


def _weighted_edge(displacement: np.ndarray, nodes: tuple[int, ...], weights: np.ndarray, component: int) -> float:
    return float(np.dot(weights, displacement[np.asarray(nodes, dtype=int), component]))


def _relative(value: float, reference: float) -> float:
    return abs(float(value) - float(reference)) / max(abs(float(reference)), 1.0e-30)


def _check(identifier: str, value: float, limit: float) -> dict[str, Any]:
    return {"id": identifier, "value": float(value), "limit": float(limit), "status": "PASS" if math.isfinite(value) and value <= limit else "FAIL"}


def _report(summary: dict[str, Any]) -> str:
    lines = [
        f"# {summary['study_id']}",
        "",
        f"Statut automatise : **{summary['status']}**.",
        "",
        "La campagne compare le MITC3+ multicouche QF_solver et Code_Aster DST sur les mêmes facettes triangulaires. Le vecteur global de reference est fourni aux deux solveurs ; chaque solveur le projette dans le plan tangent local.",
        "",
        "| Maillage | Elements | UZ QF [m] | UZ Code_Aster [m] | Ecart UX/UZ | Resid. QF |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary["rows"]:
        lines.append(f"| {row['nx']} x {row['ny']} | {row['mitc3_elements']} | {row['qf_uz']:.6e} | {row['code_aster_uz']:.6e} | {100.0 * row['vector_difference']:.4f} % | {row['qf_free_residual']:.3e} |")
    lines.extend(["", "## Familles de chargement", ""])
    for index, load_case in enumerate(summary["load_families"]):
        suffix = "" if index == 0 else f"_{load_case}"
        lines.extend(
            [
                f"### {load_case}",
                "",
                f"![Convergence {load_case}](convergence_qf_code_aster{suffix}.png)",
                "",
                f"![Deformee {load_case}](curved_laminate_deformation_qf_code_aster{suffix}.png)",
                "",
            ]
        )
    material = LAMINATE_MATERIAL
    lines.extend(
        [
            "## Contrat matériau",
            "",
            "Les constantes sont partagees avec QF_solver via "
            "`solveur.verification.mitc3_models.LAMINATE_MATERIAL`; le deck "
            "Code_Aster est genere a partir de la meme source.",
            "",
            "| Constante | Valeur |",
            "| --- | ---: |",
            f"| E1 | {material['E1']:.6e} Pa |",
            f"| E2 | {material['E2']:.6e} Pa |",
            f"| nu12 | {material['nu12']:.6g} |",
            f"| G12 | {material['G12']:.6e} Pa |",
            f"| G13 | {material['G13']:.6e} Pa |",
            f"| G23 | {material['G23']:.6e} Pa |",
            f"| rho | {material['density']:.6g} kg/m3 |",
            "",
        ]
    )
    lines.extend(["## Limites", ""])
    lines.extend(f"- {item}" for item in summary["limitations"])
    return "\n".join(lines) + "\n"
