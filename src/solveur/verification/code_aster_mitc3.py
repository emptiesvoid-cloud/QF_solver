"""Pinned same-mesh Code_Aster DKT correlation for MITC3+."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from solveur.api import solve_model
from solveur.core.model import FiniteElementModel
from solveur.io.manifest import write_json_file
from solveur.verification.code_aster_tl_structural import (
    CODE_ASTER_IMAGE,
    run_code_aster,
)
from solveur.verification.mitc3_models import rectangular_tri_mesh
from solveur.verification.vnv_manifest import write_vnv_manifest


class CodeAsterMitc3Correlation:
    """Compare membrane and bending observables on identical TRIA3 meshes."""

    study_id = "VNV-MITC3-CODEASTER-DKT-013"

    def __init__(self, output_dir: str | Path, *, nx: int = 32, ny: int = 8) -> None:
        self.output_dir = Path(output_dir).resolve()
        self.nx = int(nx)
        self.ny = int(ny)
        if self.nx < 2 or self.ny < 1:
            raise ValueError("MITC3 Code_Aster correlation requires nx >= 2 and ny >= 1.")

    def run(self) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        rows = [self._run_case("membrane", "UX", 1000.0), self._run_case("bending", "UZ", -1.0)]
        checks = [
            _check("membrane_difference", float(rows[0]["difference"]), 1.0e-6),
            _check("bending_difference", float(rows[1]["difference"]), 0.15),
        ]
        summary = {
            "study_id": self.study_id,
            "status": (
                "PASS_EXTERNAL_CORRELATION"
                if all(check["status"] == "PASS" for check in checks)
                else "WARNING"
            ),
            "maturity": "experimental",
            "qf_element": "MITC3+ Reissner-Mindlin",
            "external_solver": {
                "name": "Code_Aster",
                "version": "18.1.0",
                "image": CODE_ASTER_IMAGE,
                "element": "DKT",
            },
            "same_mesh": True,
            "mesh": {"nx": self.nx, "ny": self.ny, "triangles": 2 * self.nx * self.ny},
            "cases": rows,
            "checks": checks,
            "limitations": [
                "DKT is a Kirchhoff triangle whereas MITC3+ is Reissner-Mindlin.",
                "The membrane comparison is expected to reproduce an affine field.",
                "The bending tolerance includes formulation and finite-mesh differences.",
                "This study does not qualify curved shells, dynamics or laminates.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        (self.output_dir / "report.md").write_text(_markdown(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary

    def _run_case(self, name: str, dof: str, total_load: float) -> dict[str, Any]:
        work = self.output_dir / name
        work.mkdir(exist_ok=True)
        model, triangles, root, tip = _qf_model(
            self.nx,
            self.ny,
            dof=dof,
            total_load=total_load,
        )
        qf = solve_model(model, enforce_policy=False)
        qf_value = float(
            np.mean([qf.displacements[qf.dofs.index(int(node), dof)] for node in tip])
        )
        stem = f"mitc3_{name}"
        (work / f"{stem}.mail").write_text(
            code_aster_triangle_mesh(model.nodes, triangles, root, tip),
            encoding="ascii",
        )
        (work / f"{stem}.comm").write_text(
            code_aster_static_comm(dof, total_load, len(tip)),
            encoding="utf-8",
        )
        run_code_aster(work, stem)
        raw = json.loads((work / "code_aster_raw.json").read_text(encoding="utf-8"))
        aster_value = float(raw["mean_tip"])
        aster_displacement = np.asarray(raw["displacements"], dtype=float)
        qf_displacement = np.asarray(
            [
                [
                    qf.displacements[qf.dofs.index(node, component)]
                    for component in ("UX", "UY", "UZ")
                ]
                for node in range(model.node_count)
            ],
            dtype=float,
        )
        _plot_deformations(
            model.nodes,
            triangles,
            qf_displacement,
            aster_displacement,
            work / f"{name}_deformation.png",
            external_label="Code_Aster DKT",
        )
        return {
            "id": name,
            "dof": dof,
            "total_load": total_load,
            "qf_value": qf_value,
            "code_aster_value": aster_value,
            "difference": abs(qf_value - aster_value) / max(abs(aster_value), 1.0e-30),
            "vector_difference": float(
                np.linalg.norm(qf_displacement - aster_displacement)
                / max(np.linalg.norm(aster_displacement), 1.0e-30)
            ),
        }


def code_aster_triangle_mesh(
    nodes: np.ndarray,
    triangles: np.ndarray,
    root: np.ndarray,
    tip: np.ndarray,
) -> str:
    """Write an ASTER mesh preserving QF node and triangle order."""
    lines = ["TITRE", "QF_solver MITC3+ same-mesh correlation", "FINSF", "COOR_3D"]
    lines.extend(
        f"N{index + 1} {point[0]:.16g} {point[1]:.16g} {point[2]:.16g}"
        for index, point in enumerate(nodes)
    )
    lines.extend(["FINSF", "TRIA3"])
    lines.extend(
        f"M{index + 1} " + " ".join(f"N{int(node) + 1}" for node in triangle)
        for index, triangle in enumerate(triangles)
    )
    lines.extend(
        [
            "FINSF",
            "GROUP_MA",
            "SHELL",
            *(f"M{index}" for index in range(1, len(triangles) + 1)),
            "FINSF",
            "GROUP_NO",
            "ROOT",
            *(f"N{int(node) + 1}" for node in root),
            "FINSF",
            "GROUP_NO",
            "TIP",
            *(f"N{int(node) + 1}" for node in tip),
            "FINSF",
            "GROUP_NO",
            "NALL",
            *(f"N{index + 1}" for index in range(len(nodes))),
            "FINSF",
            "FIN",
        ]
    )
    return "\n".join(lines) + "\n"


def code_aster_static_comm(dof: str, total_load: float, tip_count: int) -> str:
    """Return a deterministic DKT static command file."""
    component = {"UX": ("FX", "DX"), "UZ": ("FZ", "DZ")}[dof]
    nodal = total_load / tip_count
    return f'''# coding=utf-8
import json
import numpy as np
from code_aster.Commands import *

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(
    MAILLAGE=mesh,
    AFFE=_F(GROUP_MA="SHELL", PHENOMENE="MECANIQUE", MODELISATION="DKT"),
)
material = DEFI_MATERIAU(ELAS=_F(E=7.0e10, NU=0.3, RHO=2700.0))
field = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SHELL", MATER=material))
shell = AFFE_CARA_ELEM(MODELE=model, COQUE=_F(GROUP_MA="SHELL", EPAIS=0.01))
fixed = AFFE_CHAR_MECA(
    MODELE=model,
    DDL_IMPO=_F(
        GROUP_NO="ROOT", DX=0.0, DY=0.0, DZ=0.0,
        DRX=0.0, DRY=0.0, DRZ=0.0,
    ),
)
load = AFFE_CHAR_MECA(
    MODELE=model,
    FORCE_NODALE=_F(GROUP_NO="TIP", {component[0]}={nodal:.16g}),
)
result = MECA_STATIQUE(
    MODELE=model,
    CHAM_MATER=field,
    CARA_ELEM=shell,
    EXCIT=(_F(CHARGE=fixed), _F(CHARGE=load)),
)
displacement = result.getField("DEPL", result.getIndexes()[-1])
values, _ = displacement.getValuesWithDescription("{component[1]}", ["TIP"])
dx, _ = displacement.getValuesWithDescription("DX", ["NALL"])
dy, _ = displacement.getValuesWithDescription("DY", ["NALL"])
dz, _ = displacement.getValuesWithDescription("DZ", ["NALL"])
with open("/work/code_aster_raw.json", "w", encoding="utf-8") as stream:
    json.dump({{
        "mean_tip": float(np.mean(values)),
        "tip_values": [float(v) for v in values],
        "displacements": [[float(x), float(y), float(z)] for x, y, z in zip(dx, dy, dz)],
    }}, stream)
FIN()
'''


def _qf_model(
    nx: int,
    ny: int,
    *,
    dof: str,
    total_load: float,
) -> tuple[FiniteElementModel, np.ndarray, np.ndarray, np.ndarray]:
    nodes, triangles, node = rectangular_tri_mesh(1.0, 0.2, nx, ny)
    root = np.asarray([node(0, j) for j in range(ny + 1)], dtype=int)
    tip = np.asarray([node(nx, j) for j in range(ny + 1)], dtype=int)
    model = FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[
            {"type": "MITC3", "nodes": triangle.tolist(), "material": "skin"}
            for triangle in triangles
        ],
        materials={
            "skin": {
                "type": "shell_isotropic",
                "E": 70.0e9,
                "nu": 0.3,
                "t": 0.01,
                "density": 2700.0,
            }
        },
        fixed_dofs=[
            {"node": int(current), "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]}
            for current in root
        ],
        loads=[
            {"node": int(current), "dof": dof, "value": total_load / len(tip)}
            for current in tip
        ],
        verification_profile="quick",
    )
    return model, triangles, root, tip


def _check(identifier: str, value: float, limit: float) -> dict[str, Any]:
    return {
        "id": identifier,
        "value": value,
        "limit": limit,
        "status": "PASS" if np.isfinite(value) and value <= limit else "FAIL",
    }


def _markdown(summary: dict[str, Any]) -> str:
    lines = [
        f"# {summary['study_id']}",
        "",
        f"Statut: **{summary['status']}**.",
        "",
        "| Cas | DDL | QF_solver | Code_Aster DKT | Ecart |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for row in summary["cases"]:
        lines.append(
            f"| {row['id']} | {row['dof']} | {row['qf_value']:.12e} | "
            f"{row['code_aster_value']:.12e} | {100.0 * row['difference']:.5f} % |"
        )
    lines.extend(
        [
            "",
            "Le maillage, les coordonnees, l'epaisseur, le materiau, les charges",
            "nodales et les blocages sont identiques. DKT et MITC3+ restent des",
            "formulations differentes; la comparaison mesure leur accord observable.",
            "",
        ]
    )
    return "\n".join(lines)


def _plot_deformations(
    nodes: np.ndarray,
    triangles: np.ndarray,
    qf: np.ndarray,
    external: np.ndarray,
    path: Path,
    *,
    external_label: str,
) -> None:
    amplitude = max(
        float(np.max(np.linalg.norm(qf, axis=1))),
        float(np.max(np.linalg.norm(external, axis=1))),
        1.0e-30,
    )
    scale = 0.15 / amplitude
    figure = plt.figure(figsize=(10.0, 4.5))
    for index, (label, displacement, color) in enumerate(
        (
            ("QF_solver MITC3+", qf, "#087f5b"),
            (external_label, external, "#c92a2a"),
        ),
        start=1,
    ):
        axis = figure.add_subplot(1, 2, index, projection="3d")
        deformed = nodes + scale * displacement
        for triangle in triangles:
            loop = np.append(triangle, triangle[0])
            axis.plot(*nodes[loop].T, color="#adb5bd", linewidth=0.25)
            axis.plot(*deformed[loop].T, color=color, linewidth=0.4)
        axis.set_title(label)
        axis.set(xlabel="X [m]", ylabel="Y [m]", zlabel="Z [m]")
        axis.set_box_aspect((1.0, 0.25, 0.25))
        axis.view_init(elev=24.0, azim=-62.0)
    figure.suptitle(f"Maillage initial gris, deformee amplifiee x{scale:.3g}")
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)
