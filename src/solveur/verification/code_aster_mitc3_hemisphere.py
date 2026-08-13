"""MITC3+ pinched-hemisphere convergence and same-mesh Code_Aster DKT correlation."""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from solveur.api import solve_model
from solveur.io.manifest import write_json_file
from solveur.verification.code_aster_tl_structural import CODE_ASTER_IMAGE, run_code_aster
from solveur.verification.mitc3_models import pinched_hemisphere_model
from solveur.verification.vnv_manifest import write_vnv_manifest


REFERENCE_DISPLACEMENT = 0.0924


class CodeAsterMitc3HemisphereCampaign:
    """Correlate a doubly-curved MITC3+ shell against DKT and literature."""

    study_id = "VNV-MITC3-PINCHED-HEMISPHERE-CODEASTER-015"

    def __init__(
        self,
        output_dir: str | Path,
        *,
        levels: tuple[int, ...] = (4, 8, 12, 16, 24, 32),
    ) -> None:
        self.output_dir = Path(output_dir).resolve()
        self.levels = tuple(int(level) for level in levels)
        if not self.levels or any(level < 2 for level in self.levels):
            raise ValueError("Hemisphere levels must contain integers greater than one.")

    def run(self) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        rows = [self._run_level(level) for level in self.levels]
        finest = rows[-1]
        increment = (
            abs(float(rows[-1]["qf_abs_ux"]) - float(rows[-2]["qf_abs_ux"]))
            / max(abs(float(rows[-1]["qf_abs_ux"])), 1.0e-30)
            if len(rows) > 1
            else math.inf
        )
        checks = [
            _check("qf_reference_error", float(finest["qf_reference_error"]), 0.05),
            _check("qf_final_increment", increment, 0.02),
            _check("qf_quadrant_symmetry", float(finest["qf_quadrant_difference"]), 0.02),
            _check("qf_code_aster_probe", float(finest["probe_difference"]), 0.05),
            _check("qf_code_aster_vector", float(finest["vector_difference"]), 0.10),
        ]
        summary = {
            "study_id": self.study_id,
            "status": (
                "PASS_EXTERNAL_CORRELATION"
                if all(check["status"] == "PASS" for check in checks)
                else "WARNING"
            ),
            "maturity": "experimental",
            "benchmark": {
                "name": "pinched hemispherical shell with 18 degree cut-out",
                "radius": 10.0,
                "thickness": 0.04,
                "young_modulus": 6.825e7,
                "poisson_ratio": 0.3,
                "full_force_magnitude": 2.0,
                "quarter_boundary_force": 1.0,
                "reference_displacement": REFERENCE_DISPLACEMENT,
                "reference": "Ko et al., Computers & Structures 193 (2017), Fig. 19-20",
            },
            "external_solver": {
                "name": "Code_Aster",
                "version": "18.1.0",
                "image": CODE_ASTER_IMAGE,
                "element": "DKT/TRIA3",
            },
            "same_mesh": True,
            "levels": rows,
            "final_increment": increment,
            "checks": checks,
            "figures": [
                "geometry_boundary_loads.png",
                "convergence_qf_code_aster.png",
                f"level_{self.levels[-1]}/fine_deformation_qf_code_aster.png",
                f"level_{self.levels[-1]}/code_aster_displacement_field.png",
            ],
            "limitations": [
                "The benchmark is linear static; large rotations are outside this scope.",
                "DKT is Kirchhoff while MITC3+ is Reissner-Mindlin.",
                "Point-load stresses are singular and are not acceptance observables.",
                "The quarter loads are half of the physical full-shell boundary loads.",
            ],
        }
        _plot_convergence(rows, self.output_dir / "convergence_qf_code_aster.png")
        _plot_geometry(self.output_dir / "geometry_boundary_loads.png")
        write_json_file(self.output_dir / "summary.json", summary)
        (self.output_dir / "report.md").write_text(_markdown(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary

    def _run_level(self, level: int) -> dict[str, Any]:
        work = self.output_dir / f"level_{level}"
        work.mkdir(exist_ok=True)
        model, triangles, probes = pinched_hemisphere_model(level)
        start = time.perf_counter()
        result = solve_model(model, enforce_policy=False)
        qf_elapsed = time.perf_counter() - start
        qf = np.asarray(
            [
                [result.displacements[result.dofs.index(node, dof)] for dof in ("UX", "UY", "UZ")]
                for node in range(model.node_count)
            ],
            dtype=float,
        )
        point_x = int(probes["point_x"])
        point_y = int(probes["point_y"])
        qf_ux = float(qf[point_x, 0])
        qf_uy = float(qf[point_y, 1])
        groups = _groups(model.nodes, level)
        stem = "pinched_hemisphere"
        (work / f"{stem}.mail").write_text(
            code_aster_hemisphere_mesh(model.nodes, triangles, groups), encoding="ascii"
        )
        (work / f"{stem}.comm").write_text(code_aster_hemisphere_comm(), encoding="utf-8")
        start = time.perf_counter()
        run_code_aster(work, stem, timeout=1800)
        aster_elapsed = time.perf_counter() - start
        raw = json.loads((work / "code_aster_raw.json").read_text(encoding="utf-8"))
        aster = np.asarray(raw["displacements"], dtype=float)
        aster_ux = float(raw["point_x_ux"])
        aster_uy = float(raw["point_y_uy"])
        probe_difference = abs(qf_ux - aster_ux) / max(abs(aster_ux), 1.0e-30)
        vector_difference = float(
            np.linalg.norm(qf - aster) / max(np.linalg.norm(aster), 1.0e-30)
        )
        if level == self.levels[-1]:
            _plot_deformations(
                model.nodes,
                triangles,
                qf,
                aster,
                work / "fine_deformation_qf_code_aster.png",
            )
            _plot_single_field(
                model.nodes,
                triangles,
                aster,
                work / "code_aster_displacement_field.png",
            )
        row = {
            "level": level,
            "quarter_triangles": int(len(triangles)),
            "reconstructed_triangles": int(4 * len(triangles)),
            "quarter_dofs": int(result.ndof),
            "qf_ux": qf_ux,
            "qf_uy": qf_uy,
            "qf_abs_ux": abs(qf_ux),
            "qf_reference_error": abs(abs(qf_ux) - REFERENCE_DISPLACEMENT)
            / REFERENCE_DISPLACEMENT,
            "qf_quadrant_difference": abs(abs(qf_ux) - abs(qf_uy))
            / max(abs(qf_ux), 1.0e-30),
            "code_aster_ux": aster_ux,
            "code_aster_uy": aster_uy,
            "code_aster_reference_error": abs(abs(aster_ux) - REFERENCE_DISPLACEMENT)
            / REFERENCE_DISPLACEMENT,
            "probe_difference": probe_difference,
            "vector_difference": vector_difference,
            "qf_elapsed_seconds": qf_elapsed,
            "code_aster_elapsed_seconds": aster_elapsed,
        }
        write_json_file(work / "comparison.json", row)
        return row


def code_aster_hemisphere_mesh(
    nodes: np.ndarray,
    triangles: np.ndarray,
    groups: dict[str, np.ndarray],
) -> str:
    """Write the identical quarter-hemisphere TRIA3 mesh in ASTER format."""
    lines = ["TITRE", "QF_solver MITC3 pinched hemisphere", "FINSF", "COOR_3D"]
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
    lines.extend(f"M{index}" for index in range(1, len(triangles) + 1))
    lines.append("FINSF")
    for name, node_ids in groups.items():
        lines.extend(["GROUP_NO", name])
        lines.extend(f"N{int(node) + 1}" for node in node_ids)
        lines.append("FINSF")
    lines.append("FIN")
    return "\n".join(lines) + "\n"


def code_aster_hemisphere_comm() -> str:
    """Return the pinned Code_Aster DKT command for the linear benchmark."""
    return '''# coding=utf-8
import json
from code_aster.Commands import *

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(
    MAILLAGE=mesh,
    AFFE=_F(GROUP_MA="SHELL", PHENOMENE="MECANIQUE", MODELISATION="DKT"),
)
material = DEFI_MATERIAU(ELAS=_F(E=6.825e7, NU=0.3))
field = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SHELL", MATER=material))
shell = AFFE_CARA_ELEM(MODELE=model, COQUE=_F(GROUP_MA="SHELL", EPAIS=0.04))
fixed = AFFE_CHAR_MECA(
    MODELE=model,
    DDL_IMPO=(
        _F(GROUP_NO="YZERO", DY=0.0, DRX=0.0, DRZ=0.0),
        _F(GROUP_NO="XZERO", DX=0.0, DRY=0.0, DRZ=0.0),
        _F(GROUP_NO="POINTX", DZ=0.0),
    ),
)
load = AFFE_CHAR_MECA(
    MODELE=model,
    FORCE_NODALE=(
        _F(GROUP_NO="POINTX", FX=-1.0),
        _F(GROUP_NO="POINTY", FY=1.0),
    ),
)
result = MECA_STATIQUE(
    MODELE=model,
    CHAM_MATER=field,
    CARA_ELEM=shell,
    EXCIT=(_F(CHARGE=fixed), _F(CHARGE=load)),
)
depl = result.getField("DEPL", result.getIndexes()[-1])
dx, _ = depl.getValuesWithDescription("DX", ["NALL"])
dy, _ = depl.getValuesWithDescription("DY", ["NALL"])
dz, _ = depl.getValuesWithDescription("DZ", ["NALL"])
point_x, _ = depl.getValuesWithDescription("DX", ["POINTX"])
point_y, _ = depl.getValuesWithDescription("DY", ["POINTY"])
with open("/work/code_aster_raw.json", "w", encoding="utf-8") as stream:
    json.dump({
        "point_x_ux": float(point_x[0]),
        "point_y_uy": float(point_y[0]),
        "displacements": [[float(x), float(y), float(z)] for x, y, z in zip(dx, dy, dz)],
    }, stream)
FIN()
'''


def _groups(nodes: np.ndarray, level: int) -> dict[str, np.ndarray]:
    stride = level + 1
    return {
        "YZERO": np.arange(0, len(nodes), stride, dtype=int),
        "XZERO": np.arange(level, len(nodes), stride, dtype=int),
        "POINTX": np.asarray([level * stride], dtype=int),
        "POINTY": np.asarray([level * stride + level], dtype=int),
        "NALL": np.arange(len(nodes), dtype=int),
    }


def _check(identifier: str, value: float, limit: float) -> dict[str, Any]:
    return {
        "id": identifier,
        "value": value,
        "limit": limit,
        "status": "PASS" if math.isfinite(value) and value <= limit else "FAIL",
    }


def _plot_convergence(rows: list[dict[str, Any]], path: Path) -> None:
    levels = [row["level"] for row in rows]
    figure, axis = plt.subplots(figsize=(7.4, 4.8))
    axis.plot(levels, [row["qf_abs_ux"] for row in rows], "o-", label="QF_solver MITC3+")
    axis.plot(
        levels,
        [abs(row["code_aster_ux"]) for row in rows],
        "s--",
        label="Code_Aster DKT",
    )
    axis.axhline(REFERENCE_DISPLACEMENT, color="#c92a2a", label="Reference 0.0924")
    axis.set(xlabel="Divisions par direction du quart", ylabel="|Ux(A)|")
    axis.grid(True, alpha=0.3)
    axis.legend()
    figure.tight_layout()
    figure.savefig(path, dpi=200)
    plt.close(figure)


def _plot_geometry(path: Path) -> None:
    model, triangles, _ = pinched_hemisphere_model(8)
    figure = plt.figure(figsize=(8.0, 6.2))
    axis = figure.add_subplot(projection="3d")
    for sx, sy, color in ((1, 1, "#1971c2"), (-1, 1, "#2f9e44"), (-1, -1, "#f08c00"), (1, -1, "#9c36b5")):
        points = model.nodes * np.array([sx, sy, 1.0])
        for triangle in triangles:
            loop = np.append(triangle, triangle[0])
            axis.plot(*points[loop].T, color=color, linewidth=0.35, alpha=0.75)
    axis.quiver(10.0, 0.0, 0.0, -2.0, 0.0, 0.0, color="#c92a2a", linewidth=2.0)
    axis.quiver(0.0, 10.0, 0.0, 0.0, 2.0, 0.0, color="#c92a2a", linewidth=2.0)
    axis.quiver(-10.0, 0.0, 0.0, 2.0, 0.0, 0.0, color="#c92a2a", linewidth=2.0)
    axis.quiver(0.0, -10.0, 0.0, 0.0, -2.0, 0.0, color="#c92a2a", linewidth=2.0)
    axis.set_title("Hemisphère pince : quatre quadrants, ouverture polaire 18 deg")
    axis.set(xlabel="X", ylabel="Y", zlabel="Z")
    axis.set_box_aspect((1, 1, 0.8))
    axis.view_init(elev=25.0, azim=-45.0)
    figure.tight_layout()
    figure.savefig(path, dpi=200)
    plt.close(figure)


def _full_surface(
    nodes: np.ndarray,
    triangles: np.ndarray,
    displacement: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    all_nodes = []
    all_triangles = []
    all_displacements = []
    for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
        offset = len(all_nodes)
        transform = np.array([sx, sy, 1.0])
        all_nodes.extend(nodes * transform)
        all_displacements.extend(displacement * transform)
        current = triangles[:, ::-1] if sx * sy < 0 else triangles
        all_triangles.extend(current + offset)
    return np.asarray(all_nodes), np.asarray(all_triangles), np.asarray(all_displacements)


def _plot_deformations(
    nodes: np.ndarray,
    triangles: np.ndarray,
    qf: np.ndarray,
    aster: np.ndarray,
    path: Path,
) -> None:
    amplitude = max(np.linalg.norm(qf, axis=1).max(), np.linalg.norm(aster, axis=1).max())
    scale = 18.0 / max(float(amplitude), 1.0e-30)
    figure = plt.figure(figsize=(11.0, 5.2))
    for index, (title, displacement) in enumerate(
        (("QF_solver MITC3+", qf), ("Code_Aster DKT", aster)), start=1
    ):
        axis = figure.add_subplot(1, 2, index, projection="3d")
        full_nodes, full_triangles, full_u = _full_surface(nodes, triangles, displacement)
        deformed = full_nodes + scale * full_u
        collection = Poly3DCollection(deformed[full_triangles], linewidth=0.05, alpha=0.92)
        values = np.linalg.norm(full_u, axis=1)[full_triangles].mean(axis=1)
        collection.set_array(values)
        collection.set_cmap("viridis")
        axis.add_collection3d(collection)
        axis.set(xlim=(-12, 12), ylim=(-12, 12), zlim=(-2, 12))
        axis.set_title(title)
        axis.set_box_aspect((1, 1, 0.65))
        axis.view_init(elev=25.0, azim=-45.0)
    figure.suptitle(f"Deformee amplifiee x{scale:.3g}; couleur = norme du deplacement")
    figure.tight_layout()
    figure.savefig(path, dpi=200)
    plt.close(figure)


def _plot_single_field(
    nodes: np.ndarray,
    triangles: np.ndarray,
    displacement: np.ndarray,
    path: Path,
) -> None:
    full_nodes, full_triangles, full_u = _full_surface(nodes, triangles, displacement)
    scale = 18.0 / max(float(np.linalg.norm(full_u, axis=1).max()), 1.0e-30)
    deformed = full_nodes + scale * full_u
    figure = plt.figure(figsize=(7.6, 6.2))
    axis = figure.add_subplot(projection="3d")
    collection = Poly3DCollection(deformed[full_triangles], linewidth=0.04)
    values = np.linalg.norm(full_u, axis=1)[full_triangles].mean(axis=1)
    collection.set_array(values)
    collection.set_cmap("plasma")
    axis.add_collection3d(collection)
    figure.colorbar(collection, ax=axis, shrink=0.65, label="|U| Code_Aster")
    axis.set(xlim=(-12, 12), ylim=(-12, 12), zlim=(-2, 12))
    axis.set_title(f"Code_Aster 18.1.0 DKT - deformee x{scale:.3g}")
    axis.set_box_aspect((1, 1, 0.65))
    axis.view_init(elev=25.0, azim=-45.0)
    figure.tight_layout()
    figure.savefig(path, dpi=200)
    plt.close(figure)


def _markdown(summary: dict[str, Any]) -> str:
    lines = [
        f"# {summary['study_id']}",
        "",
        f"Statut automatique : **{summary['status']}**.",
        "",
        "![Geometrie, maillage et chargements](geometry_boundary_loads.png)",
        "",
        "## Convergence et correlation",
        "",
        "| N | Triangles quart | Triangles reconstruits | QF | Code_Aster | Ecart ref. QF | Ecart QF/Aster |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary["levels"]:
        lines.append(
            f"| {row['level']} | {row['quarter_triangles']} | {row['reconstructed_triangles']} | "
            f"{row['qf_abs_ux']:.9f} | {abs(row['code_aster_ux']):.9f} | "
            f"{100.0 * row['qf_reference_error']:.4f} % | "
            f"{100.0 * row['probe_difference']:.4f} % |"
        )
    finest = summary["levels"][-1]
    lines.extend(
        [
            "",
            "![Courbe de convergence](convergence_qf_code_aster.png)",
            "",
            f"![Deformees comparees](level_{finest['level']}/fine_deformation_qf_code_aster.png)",
            "",
            f"![Champ Code_Aster](level_{finest['level']}/code_aster_displacement_field.png)",
            "",
            "## Interpretation",
            "",
            "Le quart utilise des demi-forces aux deux noeuds situes sur les plans de symetrie. "
            "La reconstruction sur quatre quadrants restitue les quatre forces physiques de magnitude 2.",
            "Les contraintes au point charge ne sont pas retenues, car la charge ponctuelle y cree une singularite.",
            "Code_Aster DKT est un oracle externe reproductible, mais sa formulation n'est pas identique au MITC3+.",
            "",
        ]
    )
    return "\n".join(lines)
