"""Same-mesh Code_Aster static correlation for an isotropic TET4 cantilever."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from solveur.api import solve_model
from solveur.benchmarks.gmsh_factory import BenchmarkMeshFactory
from solveur.core.model import FiniteElementModel
from solveur.io.manifest import write_json_file
from solveur.mesh.gmsh_importer import GmshModelImporter
from solveur.paths import project_root
from solveur.verification.code_aster_tet10_dynamic import (
    _code_aster_tet_mesh,
    _mesh_setup,
    _mean_displacement,
    _relative,
    _tip_face_weights,
)
from solveur.verification.code_aster_tl_structural import CODE_ASTER_IMAGE, run_code_aster
from solveur.verification.vnv_manifest import write_vnv_manifest


class CodeAsterTet4StaticCampaign:
    """Compare QF_solver TET4 and Code_Aster TETRA4 on identical meshes."""

    study_id = "VNV-TET4-STATIC-CODEASTER-TETRA4-021"
    mesh_sizes = (0.95, 0.60, 0.42, 0.30)
    relative_limit = 0.01
    length = 4.0
    width = 0.4
    height = 0.4
    young = 70.0e9
    poisson = 0.3
    total_load = -1.0

    def __init__(
        self,
        output_dir: str | Path,
        *,
        mesh_size: float | None = None,
        publish_reference: bool = True,
    ) -> None:
        self.output_dir = Path(output_dir).resolve()
        self.publish_reference = bool(publish_reference)
        if mesh_size is not None:
            self.mesh_sizes = (float(mesh_size),)
        if any(size <= 0.0 for size in self.mesh_sizes):
            raise ValueError("TET4 static mesh sizes must be positive.")

    def run(self) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        rows = [self._run_level(size, index) for index, size in enumerate(self.mesh_sizes, 1)]
        fine = rows[-1]
        qf_increment = _relative(float(fine["qf_tip_uz_m"]), float(rows[-2]["qf_tip_uz_m"])) if len(rows) > 1 else 0.0
        aster_increment = _relative(float(fine["code_aster_tip_uz_m"]), float(rows[-2]["code_aster_tip_uz_m"])) if len(rows) > 1 else 0.0
        checks = [
            _check("same_mesh_all_levels", all(bool(row["same_mesh"]) for row in rows), True),
            _check("fine_external_displacement_error", float(fine["relative_difference"]), self.relative_limit),
            _check("qf_final_mesh_increment", qf_increment, self.relative_limit),
            _check("code_aster_final_mesh_increment", aster_increment, self.relative_limit),
            _check("finite_results", all(bool(row["finite_results"]) for row in rows), True),
        ]
        summary: dict[str, Any] = {
            "study_id": self.study_id,
            "status": "PASS_EXTERNAL_CORRELATION" if all(item["status"] == "PASS" for item in checks) else "WARNING",
            "maturity": "stable_candidate",
            "scope": "isotropic small-strain TET4 linear static same-mesh correlation",
            "external_solver": {"name": "Code_Aster", "version": "18.1.0", "image": CODE_ASTER_IMAGE, "element": "3D/TETRA4"},
            "model": {
                "length_m": self.length, "width_m": self.width, "height_m": self.height,
                "same_mesh": True, "load_n": self.total_load, "observable": "mean UZ over loaded end-face nodes",
            },
            "mesh_level_count": len(rows),
            "rows": rows,
            "fine_relative_difference": float(fine["relative_difference"]),
            "qf_final_mesh_increment": qf_increment,
            "code_aster_final_mesh_increment": aster_increment,
            "checks": checks,
            "limitations": [
                "The external comparison is restricted to isotropic small-strain TET4/TETRA4 linear statics.",
                "The same-mesh comparison is primary; the one-dimensional beam formula remains diagnostic only.",
                "Curved geometry, orthotropy, contact, material nonlinearity and finite strain are excluded.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._plot(rows)
        (self.output_dir / "report.md").write_text(_report(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, self.study_id)
        if self.publish_reference:
            self._publish_reference()
        return summary

    def _publish_reference(self) -> None:
        target = project_root() / "qualification" / "vnv" / "external" / "code_aster_tet4_static" / "reference"
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(self.output_dir, target)

    def _run_level(self, mesh_size: float, level: int) -> dict[str, Any]:
        work = self.output_dir / f"h{level}"
        work.mkdir(parents=True, exist_ok=True)
        mesh = BenchmarkMeshFactory().box_tetra(
            work / "tet4_static.msh", length=self.length, width=self.width,
            height=self.height, mesh_size=mesh_size,
        )
        imported = GmshModelImporter().import_model(mesh, _setup_path(mesh)).model
        root = np.flatnonzero(np.isclose(imported.nodes[:, 0], 0.0, atol=1.0e-10))
        tip = np.flatnonzero(np.isclose(imported.nodes[:, 0], self.length, atol=1.0e-10))
        if not root.size or not tip.size:
            raise RuntimeError("TET4 static mesh has no complete root or tip node group.")
        weights = _tip_face_weights(imported.nodes, imported.elements, tip)
        model = FiniteElementModel.from_raw(
            nodes=imported.nodes.tolist(),
            elements=[{"type": item.type, "nodes": list(item.nodes), "material": item.material} for item in imported.elements],
            materials=imported.materials,
            fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in root],
            loads=[{"node": int(node), "dof": "UZ", "value": self.total_load * float(weight)} for node, weight in zip(tip, weights, strict=True)],
            analysis="linear_static", verification_profile="quick",
        )
        qf = solve_model(model, enforce_policy=False)
        qf_tip = _mean_displacement(qf.displacements, qf.dofs, tip)
        stem = "tet4_static"
        (work / f"{stem}.mail").write_text(_code_aster_tet_mesh(imported.nodes, imported.elements, root, tip, "TETRA4", "TET4"), encoding="ascii")
        (work / f"{stem}.comm").write_text(_static_comm(self.young, self.poisson, self.total_load, tip, weights), encoding="utf-8")
        run_code_aster(work, stem, timeout=900)
        raw = json.loads((work / "code_aster_raw.json").read_text(encoding="utf-8"))
        aster_tip = float(raw["tip_uz_m"])
        return {
            "level": level, "mesh_size": mesh_size, "node_count": model.node_count,
            "element_count": len(model.elements), "same_mesh": True,
            "qf_tip_uz_m": qf_tip, "code_aster_tip_uz_m": aster_tip,
            "relative_difference": _relative(qf_tip, aster_tip),
            "finite_results": bool(np.isfinite(qf_tip) and np.isfinite(aster_tip)),
        }

    def _plot(self, rows: list[dict[str, Any]]) -> None:
        levels = [int(row["element_count"]) for row in rows]
        figure, axes = plt.subplots(1, 2, figsize=(10.5, 4.0), constrained_layout=True)
        axes[0].plot(levels, [abs(float(row["qf_tip_uz_m"])) for row in rows], "o-", label="QF_solver TET4")
        axes[0].plot(levels, [abs(float(row["code_aster_tip_uz_m"])) for row in rows], "s--", label="Code_Aster TETRA4")
        axes[0].set(xlabel="Elements", ylabel="|UZ pointe| [m]", title="Convergence statique")
        axes[1].semilogy(levels, [float(row["relative_difference"]) for row in rows], "o-", color="#c92a2a", label="Ecart relatif")
        axes[1].axhline(self.relative_limit, linestyle="--", color="#495057", label="Seuil 1 %")
        axes[1].set(xlabel="Elements", ylabel="Ecart relatif", title="Comparaison même maillage")
        for axis in axes:
            axis.grid(True, alpha=0.25)
            axis.legend()
        figure.savefig(self.output_dir / "tet4_static_code_aster.png", dpi=180)
        plt.close(figure)


def _setup_path(mesh: Path) -> Path:
    setup = mesh.with_suffix(".setup.json")
    write_json_file(setup, _mesh_setup("TET4"))
    return setup


def _static_comm(young: float, poisson: float, total_load: float, tip: np.ndarray, weights: np.ndarray) -> str:
    terms = ",\n    ".join(f'_F(NOEUD="N{int(node) + 1}", FZ={total_load * float(weight):.16g})' for node, weight in zip(tip, weights, strict=True))
    return f'''# coding=utf-8
import json
from code_aster.Commands import *

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", PHENOMENE="MECANIQUE", MODELISATION="3D"))
material = DEFI_MATERIAU(ELAS=_F(E={young:.16g}, NU={poisson:.16g}))
field = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", MATER=material))
boundary = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=_F(GROUP_NO="ROOT", DX=0.0, DY=0.0, DZ=0.0))
force = AFFE_CHAR_MECA(MODELE=model, FORCE_NODALE=(
    {terms}
))
static = MECA_STATIQUE(MODELE=model, CHAM_MATER=field, EXCIT=(_F(CHARGE=boundary), _F(CHARGE=force)))
values, _ = static.getField("DEPL", 1).getValuesWithDescription("DZ", ["TIP"])
with open("/work/code_aster_raw.json", "w", encoding="utf-8") as stream:
    json.dump({{"tip_uz_m": float(sum(values) / len(values))}}, stream, indent=2)
FIN()
'''


def _check(identifier: str, value: object, limit: object) -> dict[str, object]:
    passed = value == limit if isinstance(limit, bool) else bool(float(value) <= float(limit))
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if passed else "FAIL"}


def _report(summary: dict[str, Any]) -> str:
    lines = [f"# {summary['study_id']}", "", f"Statut automatise : **{summary['status']}**.", "", "| Niveau | UZ QF_solver [m] | UZ Code_Aster [m] | Ecart |", "| ---: | ---: | ---: | ---: |"]
    for row in summary["rows"]:
        lines.append(f"| {row['element_count']} | {row['qf_tip_uz_m']:.9e} | {row['code_aster_tip_uz_m']:.9e} | {100.0 * row['relative_difference']:.6g} % |")
    lines.extend(["", "![Correlation TET4 statique](tet4_static_code_aster.png)", "", "La comparaison primaire est realisee sur maillage et chargement identiques. La reference poutre 1D n'est pas utilisee pour fermer ce gate.", ""])
    return "\n".join(lines)
