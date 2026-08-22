"""External TET10 J2 evidence on a re-entrant geometry with combined loads."""

from __future__ import annotations

from solveur.paths import project_root

import json
import shutil
from pathlib import Path
from typing import Any

import numpy as np

from solveur.api import solve_model
from solveur.core.model import FiniteElementModel
from solveur.io.json_writer import JsonResultWriter
from solveur.io.manifest import write_json_file
from solveur.io.model_writer import JsonModelWriter
from solveur.io.vtu_writer import VtuResultWriter
from solveur.mesh.gmsh_importer import GmshModelImporter
from solveur.verification.code_aster_tl_structural import CODE_ASTER_IMAGE, run_code_aster
from solveur.verification.vnv_manifest import write_vnv_manifest


STUDY_ID = "VNV-TET10-J2-CODEASTER-COMPLEX-026"


class CodeAsterTet10J2ComplexCampaign:
    """Compare a TET10 re-entrant bracket with Code_Aster TETRA10."""

    study_id = STUDY_ID
    element_type = "TET10"
    default_mesh_size = 0.32
    force_x = 3.0e6
    force_y = -6.0e6
    load_factors = (0.25, 0.50, 0.75, 1.00, 1.10)
    young = 210.0e9
    poisson = 0.3
    yield_stress = 250.0e6
    hardening = 50.0e9

    def __init__(
        self,
        output_dir: str | Path,
        *,
        mesh_size: float = default_mesh_size,
        publish_reference: bool = True,
    ):
        self.output_dir = Path(output_dir).resolve()
        self.mesh_size = float(mesh_size)
        self.publish_reference = bool(publish_reference)
        if not 0.12 <= self.mesh_size <= 0.50:
            raise ValueError("Complex TET10 J2 mesh_size must be in [0.12, 0.50].")

    def run(self) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        base, fixed, loaded = self._build_base_model()
        qf_rows = self._solve_qf_path(base, fixed, loaded)
        final_model = self._scaled_model(base, fixed, loaded, 1.0)
        final_result = solve_model(final_model, enforce_policy=False)
        JsonModelWriter().write(final_model, self.output_dir / "model.json")
        JsonResultWriter().write(final_result, self.output_dir / "results.json")
        VtuResultWriter().write(final_result, final_model, self.output_dir / "deformation.vtu")
        self._write_code_aster_files(final_model, fixed, loaded)
        work = self.output_dir / "code_aster"
        run_code_aster(work, f"{self.element_type.lower()}_j2_complex", timeout=1800)
        raw = json.loads((work / "code_aster_raw.json").read_text(encoding="utf-8"))
        summary = self._summary(final_model, qf_rows, raw, fixed, loaded)
        write_json_file(self.output_dir / "summary.json", summary)
        self._plot(summary, final_model, final_result)
        (self.output_dir / "report.md").write_text(_report(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, self.study_id)
        if self.publish_reference:
            self._publish_reference()
        return summary

    def _build_base_model(self) -> tuple[FiniteElementModel, np.ndarray, np.ndarray]:
        stem = f"{self.element_type.lower()}_j2_complex"
        mesh_path = self.output_dir / f"mesh_{stem}.msh"
        self._generate_mesh(mesh_path)
        setup_path = self.output_dir / f"mesh_{stem}.setup.json"
        write_json_file(setup_path, self._setup())
        imported = GmshModelImporter().import_model(mesh_path, setup_path).model
        fixed = np.flatnonzero(np.isclose(imported.nodes[:, 1], 2.6, atol=1.0e-8))
        loaded = np.flatnonzero(np.isclose(imported.nodes[:, 0], 3.2, atol=1.0e-8))
        if fixed.size == 0 or loaded.size == 0:
            raise RuntimeError("Complex TET10 J2 case has no complete boundary groups.")
        return imported, fixed, loaded

    def _scaled_model(
        self,
        base: FiniteElementModel,
        fixed: np.ndarray,
        loaded: np.ndarray,
        factor: float,
    ) -> FiniteElementModel:
        elements = [
            {"type": item.type, "nodes": list(item.nodes), "material": item.material}
            for item in base.elements
        ]
        loads = []
        for node in loaded:
            loads.extend(
                [
                    {"node": int(node), "dof": "UX", "value": factor * self.force_x / loaded.size},
                    {"node": int(node), "dof": "UY", "value": factor * self.force_y / loaded.size},
                ]
            )
        return FiniteElementModel.from_raw(
            nodes=base.nodes.tolist(),
            elements=elements,
            materials=base.materials,
            fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in fixed],
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

    def _solve_qf_path(self, base: FiniteElementModel, fixed: np.ndarray, loaded: np.ndarray) -> list[dict[str, float]]:
        rows = []
        for factor in self.load_factors:
            model = self._scaled_model(base, fixed, loaded, factor)
            result = solve_model(model, enforce_policy=False)
            ux = np.mean([result.displacements[result.dofs.index(int(node), "UX")] for node in loaded])
            uy = np.mean([result.displacements[result.dofs.index(int(node), "UY")] for node in loaded])
            peeq = [
                float(point["equivalent_plastic_strain"])
                for item in result.element_results
                for point in item.get("integration_points", [])
                if "equivalent_plastic_strain" in point
            ]
            rows.append(
                {
                    "load_factor": float(factor),
                    "tip_ux_m": float(ux),
                    "tip_uy_m": float(uy),
                    "equivalent_plastic_strain_mean": float(np.mean(peeq)) if peeq else 0.0,
                    "relative_residual": max(float(step["relative_residual"]) for step in result.solver["steps"]),
                }
            )
        return rows

    def _generate_mesh(self, path: Path) -> None:
        try:
            import gmsh
        except (ImportError, OSError) as exc:
            raise RuntimeError("The complex TET10 campaign requires gmsh 4.15.2.") from exc
        gmsh.initialize([f"qf_{self.element_type.lower()}_j2_complex", "-nopopup"])
        try:
            gmsh.option.setNumber("General.Terminal", 0)
            gmsh.option.setNumber("General.NumThreads", 1)
            gmsh.option.setNumber("Mesh.MaxNumThreads3D", 1)
            gmsh.option.setNumber("Mesh.MeshSizeMin", self.mesh_size)
            gmsh.option.setNumber("Mesh.MeshSizeMax", self.mesh_size)
            gmsh.option.setNumber("Mesh.MshFileVersion", 4.1)
            gmsh.option.setNumber("Mesh.Binary", 0)
            gmsh.model.add(f"{self.element_type.lower()}_j2_reentrant_bracket")
            horizontal = gmsh.model.occ.addBox(0.0, 0.0, -0.20, 3.2, 0.75, 0.40)
            vertical = gmsh.model.occ.addBox(0.0, 0.0, -0.20, 0.75, 2.6, 0.40)
            fused, _ = gmsh.model.occ.fuse([(3, horizontal)], [(3, vertical)])
            gmsh.model.occ.synchronize()
            volumes = [tag for dimension, tag in fused if dimension == 3]
            if len(volumes) != 1:
                raise RuntimeError(f"Expected one fused volume, found {len(volumes)}.")
            volume = int(volumes[0])
            fixed_surface = self._planar_surface(gmsh, volume, 1, 2.6)
            loaded_surface = self._planar_surface(gmsh, volume, 0, 3.2)
            gmsh.model.addPhysicalGroup(3, [volume], 1)
            gmsh.model.setPhysicalName(3, 1, "DOMAIN")
            gmsh.model.addPhysicalGroup(2, [fixed_surface], 2)
            gmsh.model.setPhysicalName(2, 2, "FIXED")
            gmsh.model.addPhysicalGroup(2, [loaded_surface], 3)
            gmsh.model.setPhysicalName(2, 3, "LOADED")
            gmsh.model.mesh.generate(3)
            if self.element_type == "TET10":
                gmsh.model.mesh.setOrder(2)
            gmsh.write(str(path))
        finally:
            gmsh.finalize()

    @staticmethod
    def _planar_surface(gmsh: Any, volume: int, axis: int, value: float) -> int:
        matches = []
        for dimension, tag in gmsh.model.getBoundary([(3, volume)], oriented=False):
            if dimension != 2:
                continue
            box = gmsh.model.getBoundingBox(2, tag)
            if abs(box[axis] - value) < 1.0e-7 and abs(box[axis + 3] - value) < 1.0e-7:
                matches.append(int(tag))
        if len(matches) != 1:
            raise RuntimeError(f"Expected one planar surface, found {len(matches)} at axis {axis}={value}.")
        return matches[0]

    def _setup(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "mesh_scale_to_m": 1.0,
            "units": {"system": "SI"},
            "verification_profile": "engineering",
            "analysis": "linear_static",
            "materials": {
                "J2": {
                    "type": "von_mises_elastoplastic_3d",
                    "E": self.young,
                    "nu": self.poisson,
                    "yield_stress": self.yield_stress,
                    "hardening_modulus": self.hardening,
                }
            },
            "groups": [
                {"name": "DOMAIN", "dimension": 3, "actions": [{"type": "elements", "element_type": self.element_type, "material": "J2"}]},
                {"name": "FIXED", "dimension": 2, "actions": [{"type": "fixed_dofs", "dofs": ["UX", "UY", "UZ"]}]},
                {"name": "LOADED", "dimension": 2, "actions": [{"type": "nodal_load", "dof": "UX", "value": 1.0}, {"type": "nodal_load", "dof": "UY", "value": 1.0}]},
            ],
        }

    def _write_code_aster_files(self, model: FiniteElementModel, fixed: np.ndarray, loaded: np.ndarray) -> None:
        work = self.output_dir / "code_aster"
        work.mkdir(parents=True, exist_ok=True)
        stem = f"{self.element_type.lower()}_j2_complex"
        (work / f"{stem}.mail").write_text(_aster_mesh(model, fixed, loaded, self.element_type), encoding="ascii")
        (work / f"{stem}.comm").write_text(_aster_commands(self, loaded), encoding="utf-8")

    def _summary(self, model: FiniteElementModel, qf: list[dict[str, float]], raw: dict[str, Any], fixed: np.ndarray, loaded: np.ndarray) -> dict[str, Any]:
        aster = _trim_initial(raw, len(qf))
        qf_vector = np.asarray([[row["tip_ux_m"], row["tip_uy_m"]] for row in qf])
        aster_vector = np.asarray([[row["tip_ux_m"], row["tip_uy_m"]] for row in aster])
        qf_peeq = np.asarray([row["equivalent_plastic_strain_mean"] for row in qf])
        aster_peeq = np.asarray([row["equivalent_plastic_strain"] for row in aster])
        vector_error = _normalized_rms(qf_vector, aster_vector)
        final_error = _relative(float(np.linalg.norm(qf_vector[-1])), float(np.linalg.norm(aster_vector[-1])))
        peeq_error = _normalized_rms(qf_peeq, aster_peeq)
        checks = [
            _check("combined_tip_displacement_path_rms", vector_error, 0.10),
            _check("combined_tip_displacement_final", final_error, 0.10),
            _check("peeq_path_rms", peeq_error, 0.15),
            _check("small_strain_tip_displacement_ratio", float(np.linalg.norm(qf_vector[-1])) / 3.2, 0.10),
            _check("qf_max_step_residual", max(row["relative_residual"] for row in qf), 1.0e-7),
        ]
        return {
            "study_id": self.study_id,
            "status": "PASS_EXTERNAL_CORRELATION" if all(item["status"] == "PASS" for item in checks) else "WARNING",
            "maturity": "experimental",
            "external_solver": {"name": "Code_Aster", "version": "18.1.0", "image": CODE_ASTER_IMAGE, "element": "TETRA10" if self.element_type == "TET10" else "TETRA4", "relation": "VMIS_ISOT_LINE"},
            "qf_solver": {"element": self.element_type, "material": "von_mises_elastoplastic_3d"},
            "geometry": "re-entrant L bracket, fused volumes",
            "model": {"nodes": model.node_count, "elements": len(model.elements), "mesh_size": self.mesh_size, "fixed_nodes": int(fixed.size), "loaded_nodes": int(loaded.size), "same_mesh": True, "same_combined_loads": True, "load_factors": list(self.load_factors)},
            "loads": {"base_force_x_n": self.force_x, "base_force_y_n": self.force_y},
            "material": {"E_pa": self.young, "nu": self.poisson, "yield_stress_pa": self.yield_stress, "hardening_modulus_pa": self.hardening},
            "qf_rows": qf,
            "code_aster_rows": aster,
            "checks": checks,
            "limitations": [
                "Small-strain isotropic J2 plasticity with linear isotropic hardening only.",
                "Re-entrant bracket with combined UX/UY nodal loads; no cyclic reversal.",
                "No geometric nonlinearity, contact, damage, rupture or singular-point stress acceptance.",
            ],
        }

    def _plot(self, summary: dict[str, Any], model: FiniteElementModel, result: Any) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        factors = np.asarray(self.load_factors)
        qf, aster = summary["qf_rows"], summary["code_aster_rows"]
        figure, axes = plt.subplots(1, 2, figsize=(11, 4.5), constrained_layout=True)
        for index, label in enumerate(("tip_ux_m", "tip_uy_m")):
            axes[index].plot(factors, [row[label] for row in qf], "o-", label=f"QF_solver {self.element_type}", color="#0072B2")
            axes[index].plot(factors, [row[label] for row in aster], "s--", label=f"Code_Aster TETRA{10 if self.element_type == 'TET10' else 4}", color="#D55E00")
            axes[index].set(xlabel="Facteur de charge", ylabel=f"{label.upper()} [m]", title=f"Reponse {label.upper()}")
            axes[index].grid(alpha=0.25)
            axes[index].legend(fontsize=8)
        figure.savefig(self.output_dir / "comparison.png", dpi=180)
        plt.close(figure)

        displacement = np.asarray(result.displacements, dtype=float)
        deformed = model.nodes.copy()
        scale = 0.20 / max(float(np.max(np.abs(displacement))), 1.0e-30)
        for node in range(model.node_count):
            base = 3 * node
            deformed[node] += scale * displacement[base : base + 3]
        figure = plt.figure(figsize=(8.5, 5.5))
        axis = figure.add_subplot(111, projection="3d")
        for element in model.elements:
            corners = np.asarray(element.nodes[:4], dtype=int)
            loop = np.append(corners, corners[0])
            axis.plot(model.nodes[loop, 0], model.nodes[loop, 1], model.nodes[loop, 2], color="#9aa0a6", linewidth=0.3)
            axis.plot(deformed[loop, 0], deformed[loop, 1], deformed[loop, 2], color="#0072B2", linewidth=0.5)
        axis.set(title=f"{self.element_type} J2 re-entrant bracket - deformation x{scale:.1f}", xlabel="X", ylabel="Y", zlabel="Z")
        figure.savefig(self.output_dir / "deformation.png", dpi=180)
        plt.close(figure)

    def _publish_reference(self) -> None:
        reference = ROOT / "qualification" / "vnv" / "external" / f"code_aster_{self.element_type.lower()}_j2_complex" / "reference"
        reference.mkdir(parents=True, exist_ok=True)
        for name in ("summary.json", "report.md", "vnv_manifest.json", "comparison.png", "deformation.png"):
            shutil.copy2(self.output_dir / name, reference / name)


ROOT = project_root()


class CodeAsterTet4J2ComplexCampaign(CodeAsterTet10J2ComplexCampaign):
    """Compare a TET4 re-entrant bracket with Code_Aster TETRA4."""

    study_id = "VNV-TET4-J2-CODEASTER-COMPLEX-027"
    element_type = "TET4"


def _aster_mesh(
    model: FiniteElementModel,
    fixed: np.ndarray,
    loaded: np.ndarray,
    element_type: str = "TET10",
) -> str:
    mesh_type = "TETRA10" if str(element_type).upper() == "TET10" else "TETRA4"
    lines = ["TITRE", f"QF_solver {element_type} J2 complex correlation", "FINSF", "COOR_3D"]
    lines.extend(f"N{i + 1} {node[0]:.16g} {node[1]:.16g} {node[2]:.16g}" for i, node in enumerate(model.nodes))
    lines.extend(["FINSF", mesh_type])
    lines.extend(f"M{i + 1} " + " ".join(f"N{int(node) + 1}" for node in item.nodes) for i, item in enumerate(model.elements))
    lines.extend(["FINSF", "GROUP_MA", "SOLID", *(f"M{i}" for i in range(1, len(model.elements) + 1)), "FINSF", "GROUP_NO", "FIXED", *(f"N{int(node) + 1}" for node in fixed), "FINSF", "GROUP_NO", "TIP", *(f"N{int(node) + 1}" for node in loaded), "FINSF", "FIN"])
    return "\n".join(lines) + "\n"


def _aster_commands(campaign: CodeAsterTet10J2ComplexCampaign, loaded: np.ndarray) -> str:
    factors = campaign.load_factors
    factor_values = ", ".join(f"{value:.16g}, {value:.16g}" for value in (0.0, *factors))
    times = ", ".join(f"{value:.16g}" for value in (0.0, *factors))
    fx = campaign.force_x / loaded.size
    fy = campaign.force_y / loaded.size
    loads = ",\n    ".join(f'_F(NOEUD="N{int(node) + 1}", FX={fx:.16g}, FY={fy:.16g})' for node in loaded)
    tangent = campaign.young * campaign.hardening / (campaign.young + campaign.hardening)
    return f'''# coding=utf-8
import json
import numpy as np
from code_aster.Commands import *

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", PHENOMENE="MECANIQUE", MODELISATION="3D"))
material = DEFI_MATERIAU(ELAS=_F(E={campaign.young:.16g}, NU={campaign.poisson:.16g}), ECRO_LINE=_F(SY={campaign.yield_stress:.16g}, D_SIGM_EPSI={tangent:.16g}))
field = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", MATER=material))
boundary = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=_F(GROUP_NO="FIXED", DX=0.0, DY=0.0, DZ=0.0))
force = AFFE_CHAR_MECA(MODELE=model, FORCE_NODALE=({loads}))
times = DEFI_LIST_REEL(VALE=({times}))
function = DEFI_FONCTION(NOM_PARA="INST", PROL_GAUCHE="CONSTANT", PROL_DROITE="CONSTANT", VALE=({factor_values}))
result = STAT_NON_LINE(MODELE=model, CHAM_MATER=field, EXCIT=(_F(CHARGE=boundary), _F(CHARGE=force, FONC_MULT=function)), COMPORTEMENT=_F(RELATION="VMIS_ISOT_LINE", DEFORMATION="PETIT"), INCREMENT=_F(LIST_INST=times), CONVERGENCE=_F(RESI_GLOB_RELA=1.0e-9, ITER_GLOB_MAXI=60))
rows = []
for order in result.getIndexes():
    displacement = result.getField("DEPL", order)
    ux, _ = displacement.getValuesWithDescription("DX", ["TIP"])
    uy, _ = displacement.getValuesWithDescription("DY", ["TIP"])
    try:
        internal = result.getField("VARI_ELGA", order)
        peeq, _ = internal.getValuesWithDescription("V1", ["SOLID"])
        peeq_value = float(np.mean(peeq))
    except Exception:
        peeq_value = float("nan")
    rows.append({{"tip_ux_m": float(np.mean(ux)), "tip_uy_m": float(np.mean(uy)), "equivalent_plastic_strain": peeq_value}})
with open("/work/code_aster_raw.json", "w", encoding="utf-8") as stream:
    json.dump({{"rows": rows}}, stream, indent=2)
FIN()
'''


def _trim_initial(raw: dict[str, Any], count: int) -> list[dict[str, float]]:
    rows = [{key: float(item[key]) for key in ("tip_ux_m", "tip_uy_m", "equivalent_plastic_strain")} for item in raw["rows"]]
    if len(rows) == count + 1:
        rows = rows[1:]
    if len(rows) != count:
        raise RuntimeError(f"Code_Aster returned {len(rows)} states; expected {count}.")
    return rows


def _normalized_rms(observed: np.ndarray, reference: np.ndarray) -> float:
    return float(np.sqrt(np.mean((observed - reference) ** 2)) / max(float(np.max(np.abs(reference))), 1.0e-30))


def _relative(value: float, reference: float) -> float:
    return abs(value - reference) / max(abs(reference), 1.0e-30)


def _check(identifier: str, value: float, limit: float) -> dict[str, float | str]:
    return {"id": identifier, "value": float(value), "limit": float(limit), "status": "PASS" if np.isfinite(value) and value <= limit else "FAIL"}


def _report(summary: dict[str, Any]) -> str:
    element = str(summary["qf_solver"]["element"])
    oracle = "TETRA10" if element == "TET10" else "TETRA4"
    lines = [f"# {summary['study_id']}", "", f"Statut : **{summary['status']}**", "", f"Correlation externe sur le meme maillage {element}/{oracle} d'une geometrie rentrante sous chargements combines.", "", "| Facteur | UX QF | UX Code_Aster | UY QF | UY Code_Aster | PEEQ QF | PEEQ Code_Aster |", "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for qf, aster in zip(summary["qf_rows"], summary["code_aster_rows"], strict=True):
        lines.append(f"| {qf['load_factor']:.2f} | {qf['tip_ux_m']:.6e} | {aster['tip_ux_m']:.6e} | {qf['tip_uy_m']:.6e} | {aster['tip_uy_m']:.6e} | {qf['equivalent_plastic_strain_mean']:.6e} | {aster['equivalent_plastic_strain']:.6e} |")
    lines.extend(["", "| Controle | Valeur | Limite | Statut |", "| --- | ---: | ---: | --- |"])
    lines.extend(f"| {item['id']} | {item['value']:.6e} | {item['limit']:.6e} | {item['status']} |" for item in summary["checks"])
    lines.extend(["", "![Comparaison](comparison.png)", "", "![Deformee](deformation.png)", "", "## Limites", ""])
    lines.extend(f"- {item}" for item in summary["limitations"])
    return "\n".join(lines) + "\n"
