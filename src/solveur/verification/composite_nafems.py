"""NAFEMS R0031/1 composite-strip correlation with Code_Aster DST."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from solveur.elements.shell.mitc4.mesh import MeshFactory, QuadMesh

from solveur.api import solve_model
from solveur.core.model import FiniteElementModel
from solveur.io.manifest import write_json_file
from solveur.verification.code_aster_tl_structural import CODE_ASTER_IMAGE, run_code_aster
from solveur.verification.vnv_manifest import write_vnv_manifest


STUDY_ID = "VNV-COMP-NAFEMS-R0031-CODEASTER-004"
NAFEMS_UZ_M = -1.06e-3
NAFEMS_S11_PA = 684.0e6
NAFEMS_S13_PA = -4.1e6
MESHES = ((10, 2), (20, 4), (40, 8), (80, 16), (160, 32))


class CompositeNafemsR0031Campaign:
    """Run QF_solver and Code_Aster against NAFEMS composite benchmark 1."""

    study_id = STUDY_ID

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir).resolve()

    def run(self, *, execute_code_aster: bool = True) -> dict[str, object]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        rows = []
        fine_mesh: QuadMesh | None = None
        fine_displacement: np.ndarray | None = None
        for nx, ny in MESHES:
            qf, mesh, displacement = solve_qf_nafems_case(nx, ny)
            aster = self._code_aster_case(nx, ny, execute=execute_code_aster)
            rows.append(
                {
                    **qf,
                    **aster,
                    "qf_nafems_uz_error": _relative(float(qf["qf_uz_e_m"]), NAFEMS_UZ_M),
                    "code_aster_nafems_uz_error": _relative(float(aster["code_aster_uz_e_m"]), NAFEMS_UZ_M),
                    "qf_code_aster_uz_difference": _relative(
                        float(qf["qf_uz_e_m"]), float(aster["code_aster_uz_e_m"])
                    ),
                }
            )
            fine_mesh, fine_displacement = mesh, displacement
        checks = [
            _upper("qf_fine_uz_vs_nafems", float(rows[-1]["qf_nafems_uz_error"]), 0.02),
            _upper("code_aster_fine_uz_vs_nafems", float(rows[-1]["code_aster_nafems_uz_error"]), 0.02),
            _upper(
                "qf_final_mesh_increment",
                _relative(float(rows[-1]["qf_uz_e_m"]), float(rows[-2]["qf_uz_e_m"])),
                0.002,
            ),
            _upper(
                "code_aster_final_mesh_increment",
                _relative(
                    float(rows[-1]["code_aster_uz_e_m"]),
                    float(rows[-2]["code_aster_uz_e_m"]),
                ),
                0.002,
            ),
            _upper(
                "qf_code_aster_maximum_uz_difference",
                max(float(row["qf_code_aster_uz_difference"]) for row in rows),
                0.02,
            ),
            _upper(
                "qf_maximum_free_residual",
                max(float(row["qf_free_relative_residual"]) for row in rows),
                1.0e-8,
            ),
        ]
        passed = all(check["status"] == "PASS" for check in checks)
        summary: dict[str, object] = {
            "study_id": self.study_id,
            "status": "PASS_EXTERNAL_CORRELATION" if passed else "FAIL",
            "maturity": "experimental",
            "benchmark": {
                "name": "NAFEMS R0031/1 laminated strip under three-point bending",
                "reference_uz_e_m": NAFEMS_UZ_M,
                "reference_s11_e_pa": NAFEMS_S11_PA,
                "reference_s13_d_pa": NAFEMS_S13_PA,
                "source": "NAFEMS R0031 as reproduced by Abaqus Verification Guide 2024",
            },
            "external_solver": {
                "name": "Code_Aster",
                "version": "18.1.0",
                "image": CODE_ASTER_IMAGE,
                "modelisation": "DST/DSQ",
            },
            "rows": rows,
            "checks": checks,
            "limitations": [
                "Acceptance uses displacement UZ at point E, whose public NAFEMS target is unambiguous.",
                "QF_solver S11 is sampled at element centers adjacent to E and is informative, not an acceptance value.",
                "Interlaminar S13 recovery at point D is not yet implemented in QF_solver and remains open.",
                "Code_Aster DST/DSQ and QF_solver MITC4 are different shell formulations.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._plot_convergence(rows)
        if fine_mesh is not None and fine_displacement is not None:
            self._plot_deformation(fine_mesh, fine_displacement)
        self._write_report(summary)
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary

    def _code_aster_case(self, nx: int, ny: int, *, execute: bool) -> dict[str, object]:
        stem = f"nafems_r0031_{nx}x{ny}"
        (self.output_dir / f"{stem}.mail").write_text(code_aster_mesh(nx, ny), encoding="ascii")
        (self.output_dir / f"{stem}.comm").write_text(code_aster_commands(stem), encoding="utf-8")
        if execute:
            run_code_aster(self.output_dir, stem)
        raw_path = self.output_dir / f"{stem}_raw.json"
        if not raw_path.is_file():
            raise FileNotFoundError(f"Missing Code_Aster normalized result: {raw_path}")
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        value = float(raw["uz_e_m"])
        if not np.isfinite(value):
            raise ValueError("Code_Aster returned a non-finite NAFEMS displacement.")
        return {"code_aster_uz_e_m": value}

    def _plot_convergence(self, rows: list[dict[str, object]]) -> None:
        elements = [int(row["elements"]) for row in rows]
        figure, axes = plt.subplots(1, 2, figsize=(10.8, 4.6))
        axes[0].semilogx(elements, [1.0e3 * abs(float(row["qf_uz_e_m"])) for row in rows], "o-", label="QF_solver MITC4")
        axes[0].semilogx(
            elements,
            [1.0e3 * abs(float(row["code_aster_uz_e_m"])) for row in rows],
            "s--",
            label="Code_Aster DST",
        )
        axes[0].axhline(1.0e3 * abs(NAFEMS_UZ_M), color="#555555", linestyle=":", label="NAFEMS")
        axes[0].set(xlabel="Nombre d'elements", ylabel="|UZ(E)| [mm]", title="Reponse de la bande stratifiee")
        axes[0].grid(True, which="both", alpha=0.25)
        axes[0].legend()
        axes[1].loglog(elements, [float(row["qf_nafems_uz_error"]) for row in rows], "o-", label="QF / NAFEMS")
        axes[1].loglog(
            elements,
            [float(row["code_aster_nafems_uz_error"]) for row in rows],
            "s--",
            label="Code_Aster / NAFEMS",
        )
        axes[1].set(xlabel="Nombre d'elements", ylabel="Ecart relatif", title="Correlation au benchmark")
        axes[1].grid(True, which="both", alpha=0.25)
        axes[1].legend()
        figure.tight_layout()
        figure.savefig(self.output_dir / "nafems_r0031_convergence.png", dpi=180)
        plt.close(figure)

    def _plot_deformation(self, mesh: QuadMesh, displacement: np.ndarray) -> None:
        scale = 0.006 / max(float(np.max(np.linalg.norm(displacement, axis=1))), np.finfo(float).tiny)
        deformed = mesh.nodes + scale * displacement
        figure = plt.figure(figsize=(8.4, 4.8))
        axis = figure.add_subplot(111, projection="3d")
        for quad in mesh.quads:
            loop = np.append(quad, quad[0])
            axis.plot(mesh.nodes[loop, 0], mesh.nodes[loop, 1], mesh.nodes[loop, 2], color="#999999", linewidth=0.35)
            axis.plot(deformed[loop, 0], deformed[loop, 1], deformed[loop, 2], color="#2b6cb0", linewidth=0.65)
        axis.set(xlabel="X [m]", ylabel="Y [m]", zlabel="Z amplifie [m]")
        axis.set_title(f"NAFEMS R0031/1 - MITC4 {len(mesh.quads)} elements - x{scale:.2f}")
        axis.view_init(elev=24.0, azim=-62.0)
        axis.set_box_aspect((1.0, 0.25, 0.25))
        figure.tight_layout()
        figure.savefig(self.output_dir / "nafems_r0031_deformation.png", dpi=180)
        plt.close(figure)

    def _write_report(self, summary: dict[str, object]) -> None:
        lines = [
            f"# {self.study_id}",
            "",
            f"Statut automatise : **{summary['status']}**",
            "",
            "Reference NAFEMS R0031/1: `UZ(E) = -1,06 mm`.",
            "",
            "| Maillage | QF UZ [mm] | Aster UZ [mm] | Ecart QF/NAFEMS | Ecart Aster/NAFEMS |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
        for row in summary["rows"]:
            lines.append(
                f"| {row['nx']}x{row['ny']} | {1e3 * row['qf_uz_e_m']:.6f} | "
                f"{1e3 * row['code_aster_uz_e_m']:.6f} | {100 * row['qf_nafems_uz_error']:.3f} % | "
                f"{100 * row['code_aster_nafems_uz_error']:.3f} % |"
            )
        previous = summary["rows"][-2]
        fine = summary["rows"][-1]
        qf_increment = _relative(float(fine["qf_uz_e_m"]), float(previous["qf_uz_e_m"]))
        aster_increment = _relative(
            float(fine["code_aster_uz_e_m"]),
            float(previous["code_aster_uz_e_m"]),
        )
        lines.extend(
            [
                "",
                f"Increment final QF_solver : `{100 * qf_increment:.4f} %`; "
                f"Code_Aster : `{100 * aster_increment:.4f} %` (seuil `0,2 %`).",
            ]
        )
        lines.extend(
            [
                "",
                "![Convergence NAFEMS](nafems_r0031_convergence.png)",
                "",
                "![Maillage et deformee](nafems_r0031_deformation.png)",
                "",
                "La contrainte S11 QF est publiee comme sonde de centre d'element",
                "adjacent au point E. Elle ne remplace pas l'extraction nodale NAFEMS.",
                "La recuperation interlaminaire S13 au point D reste ouverte.",
                "",
            ]
        )
        (self.output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def solve_qf_nafems_case(nx: int, ny: int) -> tuple[dict[str, object], QuadMesh, np.ndarray]:
    """Solve the controlled quarter-strip model with MITC4."""
    if nx % 10 or ny % 2:
        raise ValueError("NAFEMS refinements must preserve x=10 mm and the mid-width load node.")
    mesh = MeshFactory.rectangular_plate(nx, ny, 0.025, 0.005)
    half_width = 0.0025
    back = _nodes_where(mesh, lambda point: np.isclose(point[1], half_width))
    right = _nodes_where(mesh, lambda point: np.isclose(point[0], 0.025))
    support = _nodes_where(mesh, lambda point: np.isclose(point[0], 0.010))
    fixed = [{"node": node, "dofs": ["UY", "RX", "RZ"]} for node in back]
    fixed.extend({"node": node, "dofs": ["UX", "RY", "RZ"]} for node in right)
    fixed.extend({"node": node, "dofs": ["UZ"]} for node in support)
    load_data = ((-half_width, -4.16665), (0.0, -16.66665), (half_width, -4.16665))
    loads = [
        {
            "node": next(node for node in right if np.isclose(mesh.nodes[node, 1], y)),
            "dof": "UZ",
            "value": force,
        }
        for y, force in load_data
    ]
    model = FiniteElementModel.from_raw(
        nodes=mesh.nodes,
        elements=[{"type": "MITC4", "nodes": quad, "material": "laminate"} for quad in mesh.quads],
        materials={"laminate": nafems_laminate()},
        fixed_dofs=fixed,
        loads=loads,
    )
    result = solve_model(model)
    point_e = next(node for node in right if np.isclose(mesh.nodes[node, 1], -half_width))
    displacement = np.asarray(
        [
            [result.displacements[result.dofs.index(node, dof)] for dof in ("UX", "UY", "UZ")]
            for node in range(len(mesh.nodes))
        ]
    )
    adjacent = [index for index, quad in enumerate(mesh.quads) if point_e in quad]
    s11 = max(
        (
            abs(float(point["material_stress"][0]))
            for index in adjacent
            for point in result.element_results[index].get("ply_results", [])
        ),
        default=0.0,
    )
    row = {
        "nx": nx,
        "ny": ny,
        "elements": int(len(mesh.quads)),
        "qf_uz_e_m": float(result.displacements[result.dofs.index(point_e, "UZ")]),
        "qf_s11_probe_pa": s11,
        "qf_s11_probe_nafems_difference": _relative(s11, NAFEMS_S11_PA),
        "qf_free_relative_residual": float(result.audit.equilibrium["free_relative_residual"]),
    }
    return row, mesh, displacement


def nafems_laminate() -> dict[str, object]:
    """Return the seven-layer NAFEMS R0031/1 laminate in SI units."""
    angles = (0.0, 90.0, 0.0, 90.0, 0.0, 90.0, 0.0)
    thicknesses = (1.0e-4, 1.0e-4, 1.0e-4, 4.0e-4, 1.0e-4, 1.0e-4, 1.0e-4)
    return {
        "type": "shell_laminate",
        "plies": [
            {
                "name": f"ply-{index + 1}",
                "E1": 100.0e9,
                "E2": 5.0e9,
                "nu12": 0.4,
                "G12": 3.0e9,
                "G13": 3.0e9,
                "G23": 2.0e9,
                "density": 1600.0,
                "thickness": thickness,
                "angle_deg": angle,
            }
            for index, (angle, thickness) in enumerate(zip(angles, thicknesses, strict=True))
        ],
    }


def code_aster_mesh(nx: int, ny: int) -> str:
    """Return the Code_Aster QUAD4 mesh and NAFEMS boundary groups."""
    if nx % 10 or ny % 2:
        raise ValueError("NAFEMS refinements must be multiples of 10x2.")
    lines = ["TITRE", "NAFEMS R0031/1 composite strip", "FINSF", "COOR_3D"]
    for j in range(ny + 1):
        for i in range(nx + 1):
            node = j * (nx + 1) + i + 1
            lines.append(f"N{node} {0.025 * i / nx:.16g} {0.005 * j / ny:.16g} 0.0")
    lines.extend(["FINSF", "QUAD4"])
    for j in range(ny):
        for i in range(nx):
            element = j * nx + i + 1
            n1 = j * (nx + 1) + i + 1
            lines.append(f"M{element} N{n1} N{n1 + 1} N{n1 + nx + 2} N{n1 + nx + 1}")
    lines.extend(["FINSF", "GROUP_MA", "PLATE", *(f"M{i}" for i in range(1, nx * ny + 1)), "FINSF"])
    groups = {
        "NBACK": [ny * (nx + 1) + i + 1 for i in range(nx + 1)],
        "NRT": [j * (nx + 1) + nx + 1 for j in range(ny + 1)],
        "SUP": [j * (nx + 1) + int(0.4 * nx) + 1 for j in range(ny + 1)],
        "LOAD0": [nx + 1],
        "LOAD1": [(ny // 2) * (nx + 1) + nx + 1],
        "LOAD2": [ny * (nx + 1) + nx + 1],
    }
    for name, nodes in groups.items():
        lines.extend(["GROUP_NO", name, *(f"N{node}" for node in nodes), "FINSF"])
    lines.append("FIN")
    return "\n".join(lines) + "\n"


def code_aster_commands(stem: str) -> str:
    """Return the controlled Code_Aster DST composite calculation."""
    layers = ",\n        ".join(
        f"_F(EPAIS={thickness:.16g}, MATER=lamina, ORIENTATION={angle:.1f})"
        for angle, thickness in zip(
            (0.0, 90.0, 0.0, 90.0, 0.0, 90.0, 0.0),
            (1.0e-4, 1.0e-4, 1.0e-4, 4.0e-4, 1.0e-4, 1.0e-4, 1.0e-4),
            strict=True,
        )
    )
    return f'''# coding=utf-8
import json
from code_aster.Commands import *

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(MAILLAGE=mesh, AFFE=_F(GROUP_MA="PLATE", PHENOMENE="MECANIQUE", MODELISATION="DST"))
lamina = DEFI_MATERIAU(ELAS_ORTH=_F(
    E_L=100.0e9, E_T=5.0e9, NU_LT=0.4, G_LT=3.0e9, G_LN=3.0e9, G_TN=2.0e9
))
laminate = DEFI_COMPOSITE(COUCHE=(
        {layers}
))
material = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA="PLATE", MATER=laminate))
shell = AFFE_CARA_ELEM(MODELE=model, COQUE=_F(GROUP_MA="PLATE", EPAIS=1.0e-3, COQUE_NCOU=7))
boundary = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=(
    _F(GROUP_NO="NBACK", DY=0.0, DRX=0.0, DRZ=0.0),
    _F(GROUP_NO="NRT", DX=0.0, DRY=0.0, DRZ=0.0),
    _F(GROUP_NO="SUP", DZ=0.0),
))
load = AFFE_CHAR_MECA(MODELE=model, FORCE_NODALE=(
    _F(GROUP_NO="LOAD0", FZ=-4.16665),
    _F(GROUP_NO="LOAD1", FZ=-16.66665),
    _F(GROUP_NO="LOAD2", FZ=-4.16665),
))
result = MECA_STATIQUE(
    MODELE=model, CHAM_MATER=material, CARA_ELEM=shell,
    EXCIT=(_F(CHARGE=boundary), _F(CHARGE=load)),
)
displacement = result.getField("DEPL", result.getIndexes()[-1])
values, _ = displacement.getValuesWithDescription("DZ", ["LOAD0"])
with open("/work/{stem}_raw.json", "w", encoding="utf-8") as stream:
    json.dump({{"uz_e_m": float(sum(values) / len(values))}}, stream, indent=2)
FIN()
'''


def _nodes_where(mesh: QuadMesh, predicate: object) -> list[int]:
    return [index for index, point in enumerate(mesh.nodes) if predicate(point)]


def _relative(value: float, reference: float) -> float:
    return abs(value - reference) / max(abs(reference), np.finfo(float).tiny)


def _upper(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if value <= limit else "FAIL"}
