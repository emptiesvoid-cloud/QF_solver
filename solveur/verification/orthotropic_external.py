"""Cross-code V&V for complex oriented orthotropic TET4 structures."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np

from solveur.api.public import save_model, save_result, solve_model
from solveur.io.manifest import write_json_file
from solveur.verification.calculix_total_lagrangian import parse_last_frd_displacement
from solveur.verification.code_aster_tl_structural import (
    CODE_ASTER_IMAGE,
    code_aster_mesh,
    run_code_aster,
)
from solveur.verification.orthotropic_complex_mesh import (
    OrthotropicComplexCase,
    OrthotropicComplexMeshFactory,
)
from solveur.verification.vnv_manifest import write_vnv_manifest


CALCULIX_IMAGE = "qf-solver/calculix-nafems13h:2.20"


class OrthotropicExternalCampaign:
    """Compare QF_solver with Code_Aster and CalculiX on two complex meshes."""

    study_id = "VNV-ORTHOTROPIC-SOLID-EXTERNAL-002"

    def __init__(self, output_dir: str | Path, *, mesh_size: float = 0.30):
        self.output_dir = Path(output_dir).resolve()
        self.mesh_size = float(mesh_size)

    def run(self) -> dict[str, object]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        factory = OrthotropicComplexMeshFactory()
        cases = (
            factory.perforated_coupon(self.output_dir / "perforated_coupon.msh", self.mesh_size),
            factory.l_bracket(self.output_dir / "l_bracket.msh", 0.93 * self.mesh_size),
        )
        rows = [self._run_case(case) for case in cases]
        checks = []
        for row in rows:
            checks.extend(
                [
                    _upper(f"{row['case']}_calculix_displacement_l2", row["calculix_l2"], 2.0e-4),
                    _upper(f"{row['case']}_code_aster_displacement_l2", row["code_aster_l2"], 2.0e-4),
                    _upper(f"{row['case']}_code_aster_peak_stress", row["code_aster_peak_stress"], 5.0e-3),
                ]
            )
        passed = all(check["status"] == "PASS" for check in checks)
        summary: dict[str, object] = {
            "study_id": self.study_id,
            "status": "PASS_EXTERNAL_CORRELATION" if passed else "FAIL",
            "maturity": "research",
            "same_mesh": True,
            "same_boundary_conditions": True,
            "same_nodal_loads": True,
            "covered_specifications": ["SPEC-COMP-SOLID-007"],
            "external_solvers": [
                {"name": "Code_Aster", "version": "18.1.0", "element": "TETRA4", "image": CODE_ASTER_IMAGE},
                {"name": "CalculiX", "version": "2.20", "element": "C3D4", "image": CALCULIX_IMAGE},
            ],
            "cases": rows,
            "checks": checks,
            "limitations": [
                "CalculiX correlation covers nodal displacement; integration-point stresses are not compared.",
                "Code_Aster stress comparison uses the maximum global von Mises value without excluding singular zones.",
                "The campaign covers homogeneous constant orthotropy and two material orientations.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._write_report(summary)
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary

    def _run_case(self, case: OrthotropicComplexCase) -> dict[str, object]:
        work = self.output_dir / case.identifier.lower()
        work.mkdir(parents=True, exist_ok=True)
        model = case.qf_model()
        result = solve_model(model)
        qf = _displacement_matrix(result)
        save_model(model, work / "model.json")
        save_result(result, work / "qf_result.json")
        _plot_case(work / "qf_deformation.png", case, qf, f"QF_solver - {case.identifier}")

        calculix_deck = write_calculix_orthotropic_input(work / "calculix.inp", case)
        _run_calculix(work, calculix_deck.stem)
        calculix = parse_last_frd_displacement(work / "calculix.frd", case.nodes.shape[0])
        _plot_case(work / "calculix_deformation.png", case, calculix, f"CalculiX C3D4 - {case.identifier}")

        (work / "code_aster.mail").write_text(
            code_aster_mesh(
                case.nodes,
                case.elements,
                (case.fixed_nodes + 1).tolist(),
                groups={"FIXED": (case.fixed_nodes + 1).tolist(), "LOADED": (case.loaded_nodes + 1).tolist()},
            ),
            encoding="ascii",
        )
        (work / "code_aster.comm").write_text(code_aster_orthotropic_commands(case), encoding="utf-8")
        run_code_aster(work, "code_aster")
        raw = json.loads((work / "code_aster_raw.json").read_text(encoding="utf-8"))
        aster = np.asarray(raw["displacements"], dtype=float)
        _plot_case(work / "code_aster_deformation.png", case, aster, f"Code_Aster TETRA4 - {case.identifier}")

        qf_peak = max(float(item["von_mises"]) for item in result.element_results)
        aster_peak = float(raw["maximum_von_mises"])
        return {
            "case": case.identifier,
            "geometry": "perforated_coupon" if "PERFORATED" in case.identifier else "l_bracket",
            "nodes": int(case.nodes.shape[0]),
            "elements": int(case.elements.shape[0]),
            "material_angle_deg": case.angle_deg,
            "fixed_nodes": int(case.fixed_nodes.size),
            "loaded_nodes": int(case.loaded_nodes.size),
            "total_load_n": case.total_load,
            "qf_max_displacement_m": float(np.max(np.linalg.norm(qf, axis=1))),
            "calculix_max_displacement_m": float(np.max(np.linalg.norm(calculix, axis=1))),
            "code_aster_max_displacement_m": float(np.max(np.linalg.norm(aster, axis=1))),
            "calculix_l2": _relative_vector(qf, calculix),
            "code_aster_l2": _relative_vector(qf, aster),
            "qf_maximum_von_mises_pa": qf_peak,
            "code_aster_maximum_von_mises_pa": aster_peak,
            "code_aster_peak_stress": _relative(qf_peak, aster_peak),
            "artifacts": {
                "mesh": case.mesh_path.name,
                "qf_deformation": f"{work.name}/qf_deformation.png",
                "calculix_deformation": f"{work.name}/calculix_deformation.png",
                "code_aster_deformation": f"{work.name}/code_aster_deformation.png",
            },
        }

    def _write_report(self, summary: dict[str, object]) -> None:
        lines = [
            f"# {self.study_id}",
            "",
            f"Verdict automatise : **{summary['status']}**",
            "",
            "Les trois solveurs utilisent exactement les memes TET4, coordonnees, blocages et forces nodales.",
            "Les axes orthotropes sont tournes autour de Z et transmis par une orientation locale explicite.",
            "",
            "| Cas | Noeuds | TET4 | Angle | Ecart CalculiX U L2 | Ecart Code_Aster U L2 | Ecart pic VM |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for row in summary["cases"]:
            lines.append(
                f"| {row['case']} | {row['nodes']} | {row['elements']} | {row['material_angle_deg']:.1f} deg | "
                f"{100 * row['calculix_l2']:.5f} % | {100 * row['code_aster_l2']:.5f} % | "
                f"{100 * row['code_aster_peak_stress']:.4f} % |"
            )
            base = row["case"].lower()
            lines.extend(
                [
                    "",
                    f"## {row['case']}",
                    "",
                    f"![QF_solver]({base}/qf_deformation.png)",
                    "",
                    f"![CalculiX]({base}/calculix_deformation.png)",
                    "",
                    f"![Code_Aster]({base}/code_aster_deformation.png)",
                ]
            )
        lines.extend(
            [
                "",
                "## Interpretation",
                "",
                "La correlation porte sur des geometries avec trou et angle rentrant. Les pics de contrainte au bord du trou",
                "et a l'angle rentrant restent sensibles au maillage; leur convergence doit etre lue avec les champs de",
                "deplacement, et non comme une valeur locale certifiee independante du maillage.",
            ]
        )
        (self.output_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_calculix_orthotropic_input(path: str | Path, case: OrthotropicComplexCase) -> Path:
    """Write a deterministic C3D4 engineering-constants deck."""
    target = Path(path)
    lines = ["*HEADING", case.identifier, "*NODE"]
    lines.extend(
        f"{index + 1},{_ccx_number(point[0])},{_ccx_number(point[1])},{_ccx_number(point[2])}"
        for index, point in enumerate(case.nodes)
    )
    lines.append("*ELEMENT,TYPE=C3D4,ELSET=EALL")
    lines.extend(
        f"{index + 1}," + ",".join(str(int(node) + 1) for node in element)
        for index, element in enumerate(case.elements)
    )
    lines.extend(["*NSET,NSET=FIXED", *_csv_lines(case.fixed_nodes + 1)])
    lines.extend(["*NSET,NSET=LOADED", *_csv_lines(case.loaded_nodes + 1)])
    lines.extend(
        [
            "*ORIENTATION,NAME=MAT_ORIENTATION",
            "1.,0.,0.,0.,1.,0.",
            f"3,{case.angle_deg:.16g}",
            "*MATERIAL,NAME=ORTHO",
            "*ELASTIC,TYPE=ENGINEERING CONSTANTS",
            "1.35e11,1.0e10,8.0e9,0.28,0.22,0.35,5.2e9,4.1e9",
            "3.3e9",
            "*SOLID SECTION,ELSET=EALL,MATERIAL=ORTHO,ORIENTATION=MAT_ORIENTATION",
            "*BOUNDARY",
            "FIXED,1,3,0.",
            "*STEP",
            "*STATIC",
            "*CLOAD",
        ]
    )
    force = case.total_load / case.loaded_nodes.size
    lines.extend(f"{node + 1},{case.load_component + 1},{force:.16g}" for node in case.loaded_nodes)
    lines.extend(["*NODE FILE,FREQUENCY=1", "U", "*EL FILE,FREQUENCY=1", "S", "*END STEP"])
    target.write_text("\n".join(lines) + "\n", encoding="ascii")
    return target


def code_aster_orthotropic_commands(case: OrthotropicComplexCase) -> str:
    """Return linear TETRA4 Code_Aster commands with Euler-oriented ELAS_ORTH."""
    force = case.total_load / case.loaded_nodes.size
    component = ("FX", "FY", "FZ")[case.load_component]
    return f"""# coding=utf-8
import json
import numpy as np
from code_aster.Commands import *

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", PHENOMENE="MECANIQUE", MODELISATION="3D"))
material = DEFI_MATERIAU(ELAS_ORTH=_F(
    E_L=1.35e11, E_T=1.0e10, E_N=8.0e9,
    NU_LT=0.28, NU_LN=0.22, NU_TN=0.35,
    G_LT=5.2e9, G_LN=4.1e9, G_TN=3.3e9, RHO=1580.0,
))
field = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", MATER=material))
orientation = AFFE_CARA_ELEM(MODELE=model, MASSIF=_F(GROUP_MA="SOLID", ANGL_EULER=({case.angle_deg:.16g}, 0.0, 0.0)))
fixed = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=_F(GROUP_NO="FIXED", DX=0.0, DY=0.0, DZ=0.0))
load = AFFE_CHAR_MECA(MODELE=model, FORCE_NODALE=_F(GROUP_NO="LOADED", {component}={force:.16g}))
result = MECA_STATIQUE(
    MODELE=model, CHAM_MATER=field, CARA_ELEM=orientation,
    EXCIT=(_F(CHARGE=fixed), _F(CHARGE=load)),
)
order = result.getIndexes()[-1]
depl = result.getField("DEPL", order)
displacements = np.zeros(({case.nodes.shape[0]}, 3), dtype=float)
for component_index, name in enumerate(("DX", "DY", "DZ")):
    values, (node_ids, _) = depl.getValuesWithDescription(name, ["NALL"])
    for node_id, value in zip(node_ids, values):
        displacements[int(node_id), component_index] = float(value)
stress = result.getField("SIEF_ELGA", order)
components = []
for name in ("SIXX", "SIYY", "SIZZ", "SIXY", "SIYZ", "SIXZ"):
    values, _ = stress.getValuesWithDescription(name, ["SOLID"])
    components.append(np.asarray(values, dtype=float))
stress_values = np.column_stack(components)
mean = np.mean(stress_values[:, :3], axis=1)
deviator = stress_values[:, :3] - mean[:, None]
von_mises = np.sqrt(1.5 * np.sum(deviator**2, axis=1) + 3.0 * np.sum(stress_values[:, 3:]**2, axis=1))
with open("/work/code_aster_raw.json", "w", encoding="utf-8") as stream:
    json.dump({{
        "displacements": displacements.tolist(),
        "stress_global": stress_values.tolist(),
        "maximum_von_mises": float(np.max(von_mises)),
    }}, stream, indent=2)
FIN()
"""


def _run_calculix(work: Path, stem: str) -> None:
    completed = subprocess.run(
        ["docker", "run", "--rm", "-v", f"{work}:/work", "-w", "/work", CALCULIX_IMAGE, stem],
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    (work / "calculix.log").write_text(completed.stdout + completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        tail = "\n".join((completed.stdout + completed.stderr).splitlines()[-40:])
        raise RuntimeError(f"CalculiX failed for {stem}:\n{tail}")


def _plot_case(path: Path, case: OrthotropicComplexCase, displacement: np.ndarray, title: str) -> None:
    import matplotlib.pyplot as plt
    from matplotlib import cm, colors
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    faces = _exterior_faces(case.elements)
    magnitude = np.linalg.norm(displacement, axis=1)
    span = float(np.max(np.ptp(case.nodes, axis=0)))
    maximum = max(float(np.max(magnitude)), np.finfo(float).tiny)
    scale = 0.12 * span / maximum
    deformed = case.nodes + scale * displacement
    face_values = np.mean(magnitude[faces], axis=1)
    normalization = colors.Normalize(vmin=0.0, vmax=maximum)

    figure = plt.figure(figsize=(9.0, 6.0))
    axis = figure.add_subplot(111, projection="3d")
    initial = Poly3DCollection(case.nodes[faces], facecolors="#d7dde2", edgecolors="#66727d", linewidths=0.18)
    initial.set_alpha(0.16)
    axis.add_collection3d(initial)
    collection = Poly3DCollection(
        deformed[faces],
        facecolors=cm.viridis(normalization(face_values)),
        edgecolors="#263238",
        linewidths=0.18,
    )
    collection.set_alpha(0.82)
    axis.add_collection3d(collection)
    axis.scatter(*case.nodes[case.fixed_nodes].T, color="#006d77", s=17, label="blocage UX/UY/UZ")
    loaded = case.nodes[case.loaded_nodes]
    axis.scatter(*loaded.T, color="#c1121f", s=17, label="charge nodale repartie")
    load_center = np.mean(loaded, axis=0)
    direction = np.zeros(3)
    direction[case.load_component] = np.sign(case.total_load)
    axis.quiver(*load_center, *direction, length=0.16 * span, color="#c1121f", linewidth=2.2)

    bounds = np.vstack((case.nodes, deformed))
    center = 0.5 * (np.min(bounds, axis=0) + np.max(bounds, axis=0))
    radius = 0.55 * float(np.max(np.ptp(bounds, axis=0)))
    axis.set_xlim(center[0] - radius, center[0] + radius)
    axis.set_ylim(center[1] - radius, center[1] + radius)
    axis.set_zlim(center[2] - radius, center[2] + radius)
    axis.set_box_aspect((1.0, 1.0, 0.75))
    axis.set(xlabel="X [m]", ylabel="Y [m]", zlabel="Z [m]")
    axis.set_title(f"{title}\npeau TET4, amplification {scale:.3g}")
    axis.legend(loc="upper right", fontsize=8)
    scalar = cm.ScalarMappable(norm=normalization, cmap="viridis")
    scalar.set_array([])
    figure.colorbar(scalar, ax=axis, shrink=0.67, pad=0.08, label="|U| [m]")
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _exterior_faces(elements: np.ndarray) -> np.ndarray:
    owners: dict[tuple[int, int, int], tuple[int, int, int] | None] = {}
    for element in elements:
        for local in ((0, 2, 1), (0, 1, 3), (1, 2, 3), (2, 0, 3)):
            face = tuple(int(element[index]) for index in local)
            key = tuple(sorted(face))
            owners[key] = None if key in owners else face
    return np.asarray([face for face in owners.values() if face is not None], dtype=np.int64)


def _displacement_matrix(result: object) -> np.ndarray:
    values = np.zeros((result.node_count, 3), dtype=float)
    for node in range(result.node_count):
        for component, dof in enumerate(("UX", "UY", "UZ")):
            values[node, component] = result.displacements[result.dofs.index(node, dof)]
    return values


def _csv_lines(values: np.ndarray) -> list[str]:
    rows = [str(int(value)) for value in values]
    return [",".join(rows[index : index + 16]) for index in range(0, len(rows), 16)]


def _ccx_number(value: float) -> str:
    number = float(value)
    if abs(number) < 1.0e-12:
        number = 0.0
    return f"{number:.12g}"


def _relative_vector(value: np.ndarray, reference: np.ndarray) -> float:
    return float(np.linalg.norm(value - reference) / max(np.linalg.norm(reference), np.finfo(float).tiny))


def _relative(value: float, reference: float) -> float:
    return abs(value - reference) / max(abs(reference), np.finfo(float).tiny)


def _upper(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if value <= limit else "FAIL"}
