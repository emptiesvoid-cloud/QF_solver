"""Same-mesh external structural correlation for TET10 with isotropic J2 plasticity."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import numpy as np

from solveur.api import solve_model
from solveur.benchmarks.gmsh_factory import BenchmarkMeshFactory
from solveur.core.model import FiniteElementModel
from solveur.io.json_writer import JsonResultWriter
from solveur.io.manifest import write_json_file
from solveur.io.model_writer import JsonModelWriter
from solveur.io.vtu_writer import VtuResultWriter
from solveur.mesh.gmsh_importer import GmshModelImporter
from solveur.verification.code_aster_tl_structural import CODE_ASTER_IMAGE, run_code_aster
from solveur.verification.vnv_manifest import write_vnv_manifest


STUDY_ID = "VNV-TET10-J2-CODEASTER-STRUCTURAL-025"


class CodeAsterTet10J2StructuralCampaign:
    """Compare a meshed TET10 J2 bar with Code_Aster TETRA10 VMIS_ISOT_LINE."""

    study_id = STUDY_ID
    mesh_size = 0.18
    length = 1.0
    width = 0.2
    height = 0.2
    target_force = 18.0e6
    load_factors = (0.25, 0.50, 0.75, 1.00, 1.10, 1.20)
    young = 210.0e9
    poisson = 0.3
    yield_stress = 250.0e6
    hardening = 50.0e9
    external_limit = 0.10
    final_limit = 0.05

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir).resolve()

    def run(self) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        model, root, tip = self._model(1.0)
        qf_rows = self._solve_qf_path(root, tip)
        JsonModelWriter().write(model, self.output_dir / "model.json")
        final_result = self._model_result(root, tip, 1.0)
        JsonResultWriter().write(final_result, self.output_dir / "results.json")
        VtuResultWriter().write(final_result, model, self.output_dir / "deformation.vtu")
        self._write_code_aster_files(model, root, tip)
        work = self.output_dir / "code_aster"
        run_code_aster(work, "tet10_j2_structural", timeout=1800)
        raw = json.loads((work / "code_aster_raw.json").read_text(encoding="utf-8"))
        summary = self._summary(model, qf_rows, raw)
        write_json_file(self.output_dir / "summary.json", summary)
        self._plot(summary, model, final_result, root, tip)
        (self.output_dir / "report.md").write_text(_report(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, self.study_id)
        self._publish_reference()
        return summary

    def _model(self, factor: float) -> tuple[FiniteElementModel, np.ndarray, np.ndarray]:
        mesh_path = self.output_dir / "mesh_tet10_j2.msh"
        BenchmarkMeshFactory().box_tetra(
            mesh_path,
            length=self.length,
            width=self.width,
            height=self.height,
            mesh_size=self.mesh_size,
            order=2,
        )
        setup_path = self.output_dir / "mesh_tet10_j2.setup.json"
        write_json_file(setup_path, self._mesh_setup())
        imported = GmshModelImporter().import_model(mesh_path, setup_path).model
        root = np.flatnonzero(np.isclose(imported.nodes[:, 0], 0.0, atol=1.0e-9))
        tip = np.flatnonzero(np.isclose(imported.nodes[:, 0], self.length, atol=1.0e-9))
        if root.size == 0 or tip.size == 0:
            raise RuntimeError("TET10 J2 benchmark has no complete root or tip face.")
        elements = [
            {"type": item.type, "nodes": list(item.nodes), "material": item.material}
            for item in imported.elements
        ]
        loads = [
            {"node": int(node), "dof": "UX", "value": factor * self.target_force / len(tip)}
            for node in tip
        ]
        model = FiniteElementModel.from_raw(
            nodes=imported.nodes.tolist(),
            elements=elements,
            materials=imported.materials,
            fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in root],
            loads=loads,
            analysis={
                "type": "nonlinear_static",
                "method": "newton_raphson",
                "load_steps": 1,
                "load_path": [1.0],
                "max_iterations": 60,
                "tolerance": 1.0e-8,
            },
            verification_profile="engineering",
        )
        return model, root, tip

    def _model_result(self, root: np.ndarray, tip: np.ndarray, factor: float) -> Any:
        model, _, _ = self._model(factor)
        return solve_model(model, enforce_policy=False)

    def _solve_qf_path(self, root: np.ndarray, tip: np.ndarray) -> list[dict[str, float]]:
        rows = []
        for factor in self.load_factors:
            model, _, _ = self._model(factor)
            result = solve_model(model, enforce_policy=False)
            tip_ux = float(np.mean([result.displacements[result.dofs.index(int(node), "UX")] for node in tip]))
            plastic = [
                float(point["equivalent_plastic_strain"])
                for item in result.element_results
                for point in item.get("integration_points", [])
                if "equivalent_plastic_strain" in point
            ]
            rows.append(
                {
                    "load_factor": float(factor),
                    "tip_ux_m": tip_ux,
                    "equivalent_plastic_strain_mean": float(np.mean(plastic)) if plastic else 0.0,
                    "equivalent_plastic_strain_max": max(plastic, default=0.0),
                    "relative_residual": max(float(step["relative_residual"]) for step in result.solver["steps"]),
                    "nodes": float(model.node_count),
                    "elements": float(len(model.elements)),
                }
            )
        return rows

    def _write_code_aster_files(self, model: FiniteElementModel, root: np.ndarray, tip: np.ndarray) -> None:
        work = self.output_dir / "code_aster"
        work.mkdir(parents=True, exist_ok=True)
        elements = model.elements
        (work / "tet10_j2_structural.mail").write_text(
            _aster_mesh(model.nodes, elements, root, tip), encoding="ascii"
        )
        (work / "tet10_j2_structural.comm").write_text(
            _aster_commands(self, tip, self.load_factors), encoding="utf-8"
        )

    def _mesh_setup(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "mesh_scale_to_m": 1.0,
            "units": {"system": "SI"},
            "verification_profile": "engineering",
            "analysis": "linear_static",
            "materials": {
                "j2": {
                    "type": "von_mises_elastoplastic_3d",
                    "E": self.young,
                    "nu": self.poisson,
                    "yield_stress": self.yield_stress,
                    "hardening_modulus": self.hardening,
                }
            },
            "groups": [
                {"name": "domain", "dimension": 3, "actions": [{"type": "elements", "element_type": "TET10", "material": "j2"}]}
            ],
        }

    def _summary(self, model: FiniteElementModel, qf: list[dict[str, float]], raw: dict[str, Any]) -> dict[str, Any]:
        aster = _trim_initial(raw, len(qf))
        qf_tip = np.asarray([row["tip_ux_m"] for row in qf], dtype=float)
        aster_tip = np.asarray([row["tip_ux_m"] for row in aster], dtype=float)
        qf_peeq = np.asarray([row["equivalent_plastic_strain_mean"] for row in qf], dtype=float)
        aster_peeq = np.asarray([row["equivalent_plastic_strain"] for row in aster], dtype=float)
        tip_error = _normalized_rms(qf_tip, aster_tip)
        final_error = _relative(float(qf_tip[-1]), float(aster_tip[-1]))
        peeq_error = _normalized_rms(qf_peeq, aster_peeq) if np.any(aster_peeq > 0.0) else float("nan")
        checks = [
            _check("tip_displacement_path_rms", tip_error, self.external_limit),
            _check("final_tip_displacement", final_error, self.final_limit),
            _check("qf_equivalent_plastic_strain_path", peeq_error, self.external_limit),
            _check("qf_max_step_residual", max(row["relative_residual"] for row in qf), 1.0e-7),
        ]
        return {
            "study_id": self.study_id,
            "status": "PASS_EXTERNAL_CORRELATION" if all(item["status"] == "PASS" for item in checks) else "WARNING",
            "maturity": "experimental",
            "external_solver": {"name": "Code_Aster", "version": "18.1.0", "image": CODE_ASTER_IMAGE, "element": "TETRA10", "relation": "VMIS_ISOT_LINE"},
            "qf_solver": {"element": "TET10", "material": "von_mises_elastoplastic_3d"},
            "model": {"nodes": model.node_count, "elements": len(model.elements), "same_mesh": True, "same_load_factors": True, "load_factors": list(self.load_factors)},
            "material": {"E_pa": self.young, "nu": self.poisson, "yield_stress_pa": self.yield_stress, "hardening_modulus_pa": self.hardening},
            "qf_rows": qf,
            "code_aster_rows": aster,
            "checks": checks,
            "limitations": [
                "Small-strain isotropic J2 plasticity with linear isotropic hardening only.",
                "Structural comparison uses a straight homogeneous TET10 bar under monotone axial loading.",
                "No geometric nonlinearity, cyclic reversal, damage, rupture, contact or finite-strain claim.",
                "The external comparison uses global tip displacement and equivalent plastic strain, not singular-point stresses.",
            ],
        }

    def _plot(self, summary: dict[str, Any], model: FiniteElementModel, result: Any, root: np.ndarray, tip: np.ndarray) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        qf = summary["qf_rows"]
        aster = summary["code_aster_rows"]
        factors = np.asarray(self.load_factors)
        figure, axes = plt.subplots(1, 2, figsize=(11.0, 4.5), constrained_layout=True)
        axes[0].plot(factors, [row["tip_ux_m"] for row in qf], "o-", label="QF_solver TET10")
        axes[0].plot(factors, [row["tip_ux_m"] for row in aster], "s--", label="Code_Aster TETRA10")
        axes[0].set(xlabel="Facteur de charge", ylabel="UX moyen bout [m]", title="Reponse structurelle J2")
        axes[0].grid(alpha=0.25)
        axes[0].legend(fontsize=8)
        axes[1].plot(factors, [row["equivalent_plastic_strain_mean"] for row in qf], "o-", label="QF_solver")
        axes[1].plot(factors, [row["equivalent_plastic_strain"] for row in aster], "s--", label="Code_Aster")
        axes[1].set(xlabel="Facteur de charge", ylabel="PEEQ", title="Evolution plastique")
        axes[1].grid(alpha=0.25)
        axes[1].legend(fontsize=8)
        figure.savefig(self.output_dir / "comparison.png", dpi=180)
        plt.close(figure)

        displacement = np.asarray(result.displacements, dtype=float)
        deformed = model.nodes.copy()
        scale = 0.15 / max(float(np.max(np.abs(displacement))), 1.0e-30)
        for node in range(model.node_count):
            deformed[node] += scale * np.asarray([displacement[result.dofs.index(node, dof)] for dof in ("UX", "UY", "UZ")])
        figure = plt.figure(figsize=(8.5, 5.0))
        axis = figure.add_subplot(111, projection="3d")
        for element in model.elements:
            corners = np.asarray(element.nodes[:4], dtype=int)
            loop = np.append(corners, corners[0])
            axis.plot(model.nodes[loop, 0], model.nodes[loop, 1], model.nodes[loop, 2], color="#8c8c8c", linewidth=0.3)
            axis.plot(deformed[loop, 0], deformed[loop, 1], deformed[loop, 2], color="#0072B2", linewidth=0.5)
        axis.scatter(model.nodes[tip, 0], model.nodes[tip, 1], model.nodes[tip, 2], color="#D55E00", s=4, label="tip")
        axis.set(title=f"TET10 J2 structurel - deformation amplifiee x{scale:.1f}", xlabel="X", ylabel="Y", zlabel="Z")
        axis.legend(fontsize=8)
        figure.savefig(self.output_dir / "deformation.png", dpi=180)
        plt.close(figure)

    def _publish_reference(self) -> None:
        reference = Path(__file__).resolve().parents[2] / "qualification" / "vnv" / "external" / "code_aster_tet10_j2_structural" / "reference"
        reference.mkdir(parents=True, exist_ok=True)
        for name in ("summary.json", "report.md", "vnv_manifest.json", "comparison.png", "deformation.png"):
            shutil.copy2(self.output_dir / name, reference / name)


def _aster_mesh(nodes: np.ndarray, elements: list[Any], root: np.ndarray, tip: np.ndarray) -> str:
    lines = ["TITRE", "QF_solver TET10 J2 structural correlation", "FINSF", "COOR_3D"]
    lines.extend(f"N{i + 1} {node[0]:.16g} {node[1]:.16g} {node[2]:.16g}" for i, node in enumerate(nodes))
    lines.extend(["FINSF", "TETRA10"])
    lines.extend(f"M{i + 1} " + " ".join(f"N{int(node) + 1}" for node in element.nodes) for i, element in enumerate(elements))
    lines.extend(["FINSF", "GROUP_MA", "SOLID", *(f"M{i}" for i in range(1, len(elements) + 1)), "FINSF", "GROUP_NO", "ROOT", *(f"N{int(node) + 1}" for node in root), "FINSF", "GROUP_NO", "TIP", *(f"N{int(node) + 1}" for node in tip), "FINSF", "GROUP_NO", "ALL", *(f"N{i + 1}" for i in range(len(nodes))), "FINSF", "FIN"])
    return "\n".join(lines) + "\n"


def _aster_commands(campaign: CodeAsterTet10J2StructuralCampaign, tip: np.ndarray, factors: tuple[float, ...]) -> str:
    factor_values = ", ".join(f"{value:.16g}, {value:.16g}" for value in (0.0, *factors))
    times = ", ".join(f"{value:.16g}" for value in (0.0, *factors))
    nodal = campaign.target_force / len(tip)
    total_tangent = campaign.young * campaign.hardening / (campaign.young + campaign.hardening)
    loads = ",\n    ".join(f'_F(NOEUD="N{int(node) + 1}", FX={nodal:.16g})' for node in tip)
    return f'''# coding=utf-8
import json
import numpy as np
from code_aster.Commands import *

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", PHENOMENE="MECANIQUE", MODELISATION="3D"))
material = DEFI_MATERIAU(
    ELAS=_F(E={campaign.young:.16g}, NU={campaign.poisson:.16g}),
    ECRO_LINE=_F(SY={campaign.yield_stress:.16g}, D_SIGM_EPSI={total_tangent:.16g}),
)
field = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", MATER=material))
boundary = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=_F(GROUP_NO="ROOT", DX=0.0, DY=0.0, DZ=0.0))
force = AFFE_CHAR_MECA(MODELE=model, FORCE_NODALE=(
    {loads}
))
times = DEFI_LIST_REEL(VALE=({times}))
function = DEFI_FONCTION(NOM_PARA="INST", PROL_GAUCHE="CONSTANT", PROL_DROITE="CONSTANT", VALE=({factor_values}))
result = STAT_NON_LINE(
    MODELE=model,
    CHAM_MATER=field,
    EXCIT=(_F(CHARGE=boundary), _F(CHARGE=force, FONC_MULT=function)),
    COMPORTEMENT=_F(RELATION="VMIS_ISOT_LINE", DEFORMATION="PETIT"),
    INCREMENT=_F(LIST_INST=times),
    CONVERGENCE=_F(RESI_GLOB_RELA=1.0e-9, ITER_GLOB_MAXI=60),
)
rows = []
for order in result.getIndexes():
    displacement = result.getField("DEPL", order)
    ux, _ = displacement.getValuesWithDescription("DX", ["TIP"])
    try:
        internal = result.getField("VARI_ELGA", order)
        peeq, _ = internal.getValuesWithDescription("V1", ["SOLID"])
        peeq_value = float(np.mean(peeq))
    except Exception:
        peeq_value = float("nan")
    rows.append({{"tip_ux_m": float(np.mean(ux)), "equivalent_plastic_strain": peeq_value}})
with open("/work/code_aster_raw.json", "w", encoding="utf-8") as stream:
    json.dump({{"rows": rows}}, stream, indent=2)
FIN()
'''


def _trim_initial(raw: dict[str, Any], count: int) -> list[dict[str, float]]:
    rows = [{"tip_ux_m": float(item["tip_ux_m"]), "equivalent_plastic_strain": float(item["equivalent_plastic_strain"])} for item in raw["rows"]]
    if len(rows) == count + 1:
        rows = rows[1:]
    if len(rows) != count:
        raise RuntimeError(f"Code_Aster returned {len(rows)} structural states; expected {count}.")
    return rows


def _normalized_rms(observed: np.ndarray, reference: np.ndarray) -> float:
    return float(np.sqrt(np.mean((observed - reference) ** 2)) / max(float(np.max(np.abs(reference))), 1.0e-30))


def _relative(value: float, reference: float) -> float:
    return abs(value - reference) / max(abs(reference), 1.0e-30)


def _check(identifier: str, value: float, limit: float) -> dict[str, float | str]:
    return {"id": identifier, "value": float(value), "limit": float(limit), "status": "PASS" if np.isfinite(value) and value <= limit else "FAIL"}


def _report(summary: dict[str, Any]) -> str:
    lines = [
        f"# {summary['study_id']}",
        "",
        f"Statut : **{summary['status']}**",
        "",
        "Correlation structurelle sur le meme maillage TET10 entre QF_solver et Code_Aster TETRA10 `VMIS_ISOT_LINE`.",
        "",
        "| Facteur | UX QF [m] | UX Code_Aster [m] | PEEQ QF | PEEQ Code_Aster | |",
        "| ---: | ---: | ---: | ---: | ---: |",
    ]
    for qf, aster in zip(summary["qf_rows"], summary["code_aster_rows"], strict=True):
        lines.append(f"| {qf['load_factor']:.2f} | {qf['tip_ux_m']:.6e} | {aster['tip_ux_m']:.6e} | {qf['equivalent_plastic_strain_mean']:.6e} | {aster['equivalent_plastic_strain']:.6e} |")
    lines.extend(["", "| Controle | Valeur | Limite | Statut |", "| --- | ---: | ---: | --- |"])
    for check in summary["checks"]:
        lines.append(f"| {check['id']} | {check['value']:.6e} | {check['limit']:.6e} | {check['status']} |")
    lines.extend(["", "![Comparaison structurelle](comparison.png)", "", "![Deformee TET10](deformation.png)", ""])
    lines.extend(f"- {item}" for item in summary["limitations"])
    return "\n".join(lines) + "\n"
