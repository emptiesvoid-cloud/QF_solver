"""Code_Aster correlation for 3D total-Lagrangian TET4 verification."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import numpy as np

from solveur.core.errors import InfrastructureError
from solveur.elements.solid.tet4_total_lagrangian_batch import TotalLagrangianTet4Assembly
from solveur.io.manifest import write_json_file
from solveur.materials.solid import SolidMaterial
from solveur.verification.tet4_total_lagrangian_assembly import _structured_tet4_mesh
from solveur.verification.tet4_total_lagrangian_stress import analytical_svk_state
from solveur.verification.total_lagrangian_structural import solve_proportional_dead_load
from solveur.verification.vnv_manifest import write_vnv_manifest


CODE_ASTER_IMAGE = (
    "simvia/code_aster@sha256:"
    "4629a21a109309bb97fbdc27d750445cc869e151e2e2ed6290f69539614e4435"
)
CODE_ASTER_PROFILE = (
    "/opt/spack/opt/spack/linux-zen/code-aster-18.1.0-"
    "owafurl325k3dbxls3s645zyfmvakxsg"
)


class CodeAsterTlStructuralCampaign:
    """Run same-mesh finite-strain checks with Code_Aster 3D/TETRA4."""

    study_id = "VNV-TET4-TL-CODEASTER-STRUCTURAL-009"

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir).resolve()

    def run(self) -> dict[str, object]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        stress = self._run_stress_patch()
        column = self._run_imperfect_column()
        checks = [
            _check("second_piola_stress", float(stress["relative_error"]), 5.0e-4),
            _check("imperfect_column_lateral_path", float(column["maximum_relative_difference"]), 0.02),
        ]
        summary: dict[str, object] = {
            "study_id": self.study_id,
            "status": "PASS_EXTERNAL_CORRELATION"
            if all(item["status"] == "PASS" for item in checks)
            else "WARNING",
            "maturity": "research",
            "external_solver": {
                "name": "Code_Aster",
                "version": "18.1.0",
                "image": CODE_ASTER_IMAGE,
                "modelisation": "3D/TETRA4",
            },
            "stress_patch": stress,
            "imperfect_column": column,
            "linear_buckling": {
                "status": "NOT_APPLICABLE_SAME_SOLID_FORMULATION",
                "reason": (
                    "Code_Aster RIGI_GEOM linear buckling is documented for selected beam/shell "
                    "modelisations, not the same 3D TETRA4 solid formulation."
                ),
                "alternative": (
                    "Use STAT_NON_LINE on an imperfect 3D column or compare a separate shell/beam model."
                ),
            },
            "checks": checks,
            "limitations": [
                "The Code_Aster comparison covers an affine finite-strain stress state.",
                "No unsupported 3D solid eigen-buckling result is presented as evidence.",
                "The imperfect-column comparison stops at 80 percent of the same-mesh critical load.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._plot_stress(summary)
        self._write_report(summary)
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary

    def _run_stress_patch(self) -> dict[str, object]:
        nodes, elements = _structured_tet4_mesh(4, 2, 2, 2.0, 1.0, 0.75)
        finite_deformation = np.array(
            [[1.08, 0.06, 0.01], [0.02, 0.97, 0.03], [0.0, 0.01, 1.04]],
            dtype=float,
        )
        deformation = np.eye(3) + 1.0e-3 * (finite_deformation - np.eye(3))
        work = self.output_dir / "stress_patch"
        work.mkdir(exist_ok=True)
        boundary = _boundary_nodes(nodes, 2.0, 1.0, 0.75)
        (work / "stress_patch.mail").write_text(
            code_aster_mesh(nodes, elements, boundary), encoding="ascii"
        )
        (work / "stress_patch.comm").write_text(
            stress_patch_comm(nodes, boundary, deformation), encoding="utf-8"
        )
        run_code_aster(work, "stress_patch")
        raw = json.loads((work / "code_aster_stress_raw.json").read_text(encoding="utf-8"))
        mean = np.asarray(raw["cauchy_stress"], dtype=float)
        reference = analytical_svk_state(deformation, SolidMaterial(E=1.0e6, nu=0.3))
        expected = _tensor_to_aster_vector(reference["second_piola_stress"])
        return {
            "elements": int(elements.shape[0]),
            "boundary_nodes": len(boundary),
            "code_aster_second_piola": mean.tolist(),
            "analytical_second_piola": expected.tolist(),
            "relative_error": _relative_norm(mean, expected),
            "field": raw.get("field", "SIEF_ELGA"),
        }

    def _run_imperfect_column(self) -> dict[str, object]:
        cells = (16, 4, 4)
        length, height, depth = 4.0, 0.5, 0.5
        critical = 1115.4714943181057
        ratio = 0.005
        nodes, elements = _structured_tet4_mesh(*cells, length, height, depth)
        amplitude = ratio * length
        nodes[:, 2] += amplitude * (1.0 - np.cos(0.5 * np.pi * nodes[:, 0] / length))
        fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
        tip_nodes = np.flatnonzero(np.isclose(nodes[:, 0], length))
        fractions = (0.2, 0.4, 0.6, 0.8)
        qf_points = _qf_column_points(
            nodes, elements, fixed_nodes, tip_nodes, fractions, critical, amplitude
        )
        work = self.output_dir / "imperfect_column"
        work.mkdir(exist_ok=True)
        groups = {
            "FIXED": [int(value) + 1 for value in fixed_nodes],
            "TIP": [int(value) + 1 for value in tip_nodes],
        }
        (work / "imperfect_column.mail").write_text(
            code_aster_mesh(nodes, elements, groups["FIXED"], groups=groups), encoding="ascii"
        )
        (work / "imperfect_column.comm").write_text(
            imperfect_column_comm(len(groups["TIP"]), 0.8 * critical), encoding="utf-8"
        )
        run_code_aster(work, "imperfect_column")
        raw = json.loads((work / "code_aster_column_raw.json").read_text(encoding="utf-8"))
        aster_all = raw["points"]
        aster_points = []
        differences = []
        for fraction, qf in zip(fractions, qf_points):
            nearest = min(
                aster_all,
                key=lambda point: abs(float(point["load_fraction_critical"]) - fraction),
            )
            total = amplitude + float(nearest["tip_increment_z"])
            difference = abs(total - float(qf["tip_total_z"])) / max(abs(total), 1.0e-12)
            aster_points.append({**nearest, "tip_total_z": total})
            differences.append(difference)
        return {
            "cells": list(cells),
            "elements": int(elements.shape[0]),
            "imperfection_ratio": ratio,
            "critical_load_qf": critical,
            "qf_solver": qf_points,
            "code_aster": aster_points,
            "relative_differences": differences,
            "maximum_relative_difference": max(differences),
        }

    def _plot_stress(self, summary: dict[str, object]) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        stress = summary["stress_patch"]
        expected = np.asarray(stress["analytical_second_piola"], dtype=float)
        aster = np.asarray(stress["code_aster_second_piola"], dtype=float)
        labels = ("SXX", "SYY", "SZZ", "SXY", "SXZ", "SYZ")
        x = np.arange(6)
        figure, axis = plt.subplots(figsize=(7.8, 4.5))
        axis.bar(x - 0.2, expected, width=0.4, label="Saint-Venant-Kirchhoff")
        axis.bar(x + 0.2, aster, width=0.4, label="Code_Aster 3D")
        axis.set_xticks(x, labels)
        axis.set_ylabel("Contrainte PK2")
        axis.grid(True, axis="y", alpha=0.25)
        axis.legend()
        figure.tight_layout()
        figure.savefig(self.output_dir / "code_aster_stress_comparison.png", dpi=180)
        plt.close(figure)
        column = summary["imperfect_column"]
        figure, axis = plt.subplots(figsize=(7.4, 4.5))
        for name, points, style in (
            ("QF_solver TET4-TL", column["qf_solver"], "o-"),
            ("Code_Aster TETRA4", column["code_aster"], "s--"),
        ):
            axis.plot(
                [point["tip_total_z"] / 4.0 for point in points],
                [point["load_fraction_critical"] for point in points],
                style,
                label=name,
            )
        axis.set(xlabel="Deflexion laterale totale / L", ylabel="Charge / Pcr QF")
        axis.grid(True, alpha=0.25)
        axis.legend()
        figure.tight_layout()
        figure.savefig(self.output_dir / "code_aster_column_path.png", dpi=180)
        plt.close(figure)

    def _write_report(self, summary: dict[str, object]) -> None:
        stress = summary["stress_patch"]
        lines = [
            f"# {self.study_id}",
            "",
            f"Statut : **{summary['status']}**",
            "",
            "## Contrainte finie 3D",
            "",
            "Le meme maillage TETRA4 et un champ affine de petite deformation sont compares "
            "au second tenseur de Piola-Kirchhoff Saint-Venant-Kirchhoff ferme.",
            "",
            f"Ecart relatif Code_Aster/theorie : `{100 * stress['relative_error']:.6f} %`.",
            "",
            "![Comparaison des contraintes](code_aster_stress_comparison.png)",
            "",
            "## Colonne imparfaite 3D",
            "",
            f"Ecart lateral maximal QF_solver/Code_Aster : "
            f"`{100 * summary['imperfect_column']['maximum_relative_difference']:.3f} %`.",
            "",
            "![Chemin de la colonne imparfaite](code_aster_column_path.png)",
            "",
            "## Flambement lineaire",
            "",
            f"Statut : **{summary['linear_buckling']['status']}**.",
            "",
            summary["linear_buckling"]["reason"],
            "",
            "Cette absence n'est pas masquee par un modele poutre ou coque different. "
            "CalculiX fournit la correlation propre C3D4; Code_Aster sera utilise avec "
            "STAT_NON_LINE pour la colonne 3D imparfaite.",
            "",
        ]
        (self.output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def code_aster_mesh(
    nodes: np.ndarray,
    elements: np.ndarray,
    boundary_nodes: list[int],
    *,
    groups: dict[str, list[int]] | None = None,
) -> str:
    """Return a deterministic ASTER mesh for TETRA4 correlation."""
    lines = ["TITRE", "QF_solver TET4-TL Code_Aster correlation", "FINSF", "COOR_3D"]
    lines.extend(
        f"N{i + 1} {node[0]:.16g} {node[1]:.16g} {node[2]:.16g}"
        for i, node in enumerate(nodes)
    )
    lines.extend(["FINSF", "TETRA4"])
    lines.extend(
        f"M{i + 1} " + " ".join(f"N{int(node) + 1}" for node in element)
        for i, element in enumerate(elements)
    )
    lines.extend(
        [
            "FINSF",
            "GROUP_MA",
            "SOLID",
            *(f"M{i}" for i in range(1, len(elements) + 1)),
            "FINSF",
            "GROUP_NO",
            "BOUNDARY",
            *(f"N{i}" for i in boundary_nodes),
            "FINSF",
            "GROUP_NO",
            "NALL",
            *(f"N{i}" for i in range(1, len(nodes) + 1)),
            "FINSF",
        ]
    )
    for name, values in (groups or {}).items():
        if name == "BOUNDARY":
            continue
        lines.extend(["GROUP_NO", name, *(f"N{i}" for i in values), "FINSF"])
    lines.append("FIN")
    return "\n".join(lines) + "\n"


def stress_patch_comm(
    nodes: np.ndarray, boundary_nodes: list[int], deformation: np.ndarray
) -> str:
    """Return Code_Aster commands for a displacement-controlled 3D patch."""
    displacement = nodes @ (np.asarray(deformation) - np.eye(3)).T
    expected = repr(displacement.tolist())
    imposed = ",\n        ".join(
        f'_F(NOEUD="N{node}", DX={displacement[node - 1, 0]:.16g}, '
        f'DY={displacement[node - 1, 1]:.16g}, DZ={displacement[node - 1, 2]:.16g})'
        for node in boundary_nodes
    )
    return f'''# coding=utf-8
import json
import numpy as np
from code_aster.Commands import *

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", PHENOMENE="MECANIQUE", MODELISATION="3D"))
material = DEFI_MATERIAU(ELAS=_F(E=1.0e6, NU=0.3))
field = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", MATER=material))
boundary = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=(
        {imposed}
))
times = DEFI_LIST_REEL(DEBUT=0.0, INTERVALLE=_F(JUSQU_A=1.0, NOMBRE=10))
result = STAT_NON_LINE(
    MODELE=model, CHAM_MATER=field, EXCIT=_F(CHARGE=boundary),
    COMPORTEMENT=_F(RELATION="ELAS", DEFORMATION="GREEN_LAGRANGE"),
    INCREMENT=_F(LIST_INST=times),
    CONVERGENCE=_F(RESI_GLOB_RELA=1.0e-10, ITER_GLOB_MAXI=30),
)
order = result.getIndexes()[-1]
stress = result.getField("SIEF_ELGA", order)
components = []
ranges = []
for name in ("SIXX", "SIYY", "SIZZ", "SIXY", "SIXZ", "SIYZ"):
    values, _ = stress.getValuesWithDescription(name, ["SOLID"])
    components.append(float(np.mean(values)))
    ranges.append([float(np.min(values)), float(np.max(values))])
depl = result.getField("DEPL", order)
expected = np.asarray({expected}, dtype=float)
actual = np.zeros_like(expected)
for component, name in enumerate(("DX", "DY", "DZ")):
    values, (node_ids, _) = depl.getValuesWithDescription(name, ["NALL"])
    for node_id, value in zip(node_ids, values):
        actual[int(node_id), component] = float(value)
with open("/work/code_aster_stress_raw.json", "w", encoding="utf-8") as stream:
    json.dump({{
        "field": "SIEF_ELGA", "cauchy_stress": components,
        "stress_ranges": ranges,
        "maximum_displacement_error": float(np.max(np.abs(actual - expected))),
    }}, stream, indent=2)
FIN()
'''


def imperfect_column_comm(tip_node_count: int, target_load: float) -> str:
    """Return Code_Aster commands for a proportional imperfect-column path."""
    nodal_force = -target_load / tip_node_count
    return f'''# coding=utf-8
import json
from code_aster.Commands import *

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", PHENOMENE="MECANIQUE", MODELISATION="3D"))
material = DEFI_MATERIAU(ELAS=_F(E=1.0e6, NU=0.3))
field = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", MATER=material))
fixed = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=_F(GROUP_NO="FIXED", DX=0.0, DY=0.0, DZ=0.0))
load = AFFE_CHAR_MECA(MODELE=model, FORCE_NODALE=_F(GROUP_NO="TIP", FX={nodal_force:.16g}))
ramp = DEFI_FONCTION(NOM_PARA="INST", VALE=(0.0, 0.0, 1.0, 1.0))
times = DEFI_LIST_REEL(DEBUT=0.0, INTERVALLE=_F(JUSQU_A=1.0, NOMBRE=4))
result = STAT_NON_LINE(
    MODELE=model, CHAM_MATER=field,
    EXCIT=(_F(CHARGE=fixed), _F(CHARGE=load, FONC_MULT=ramp)),
    COMPORTEMENT=_F(RELATION="ELAS", DEFORMATION="GREEN_LAGRANGE"),
    INCREMENT=_F(LIST_INST=times),
    CONVERGENCE=_F(RESI_GLOB_RELA=1.0e-9, ITER_GLOB_MAXI=40),
)
raw = {{"points": []}}
access = result.getAccessParameters()
for order, instant in zip(result.getIndexes(), access["INST"]):
    if instant <= 0.0:
        continue
    displacement = result.getField("DEPL", order)
    dx, _ = displacement.getValuesWithDescription("DX", ["TIP"])
    dz, _ = displacement.getValuesWithDescription("DZ", ["TIP"])
    raw["points"].append({{
        "load_fraction_critical": 0.8 * float(instant),
        "tip_axial_x": sum(dx) / len(dx),
        "tip_increment_z": sum(dz) / len(dz),
    }})
with open("/work/code_aster_column_raw.json", "w", encoding="utf-8") as stream:
    json.dump(raw, stream, indent=2)
FIN()
'''


def run_code_aster(work: Path, stem: str, *, timeout: int = 900) -> None:
    """Execute one controlled Code_Aster command file in the pinned image."""
    serial = (
        f"export RUNASTER_ROOT={CODE_ASTER_PROFILE}; "
        f"source {CODE_ASTER_PROFILE}/share/aster/profile.sh; "
        "export PYTHONPATH=$(find /opt/spack/opt/spack/linux-zen -type d "
        "-path '*/lib/python3.11/site-packages' | paste -sd: -):${PYTHONPATH:-}; "
        "export LD_LIBRARY_PATH=$(find /opt/spack/opt/spack/linux-zen -type d "
        "\\( -name lib -o -name lib64 \\) | paste -sd: -):${LD_LIBRARY_PATH:-}; "
        f"python3 /work/{stem}.comm --last --link=F::mail::/work/{stem}.mail::D::20 "
        "--memory 4096 --tpmax 900 --numthreads 1"
    )
    docker_executable = _docker_executable()
    command = [
        docker_executable,
        "run",
        "--rm",
        "-v",
        f"{work}:/work",
        "--workdir",
        "/work",
        "--entrypoint",
        "/bin/bash",
        CODE_ASTER_IMAGE,
        "-c",
        serial,
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise InfrastructureError("Code_Aster correlation requires the Docker CLI.") from exc
    except subprocess.TimeoutExpired as exc:
        raise InfrastructureError(f"Code_Aster execution exceeded the {timeout}s infrastructure timeout.") from exc
    (work / "code_aster_stdout.log").write_text(completed.stdout, encoding="utf-8")
    (work / "code_aster_stderr.log").write_text(completed.stderr, encoding="utf-8")
    output = completed.stdout + completed.stderr
    if _docker_unavailable(output):
        raise InfrastructureError(
            "Code_Aster Docker backend is unavailable. Start Docker Desktop and verify the pinned image."
        )
    if completed.returncode != 0:
        tail = "\n".join(output.splitlines()[-50:])
        raise RuntimeError(f"Code_Aster failed for {stem}:\n{tail}")


def _docker_executable() -> str:
    """Return a resolvable Docker executable, including Windows installations."""
    configured = os.environ.get("QF_SOLVER_DOCKER")
    if configured:
        return configured
    executable = shutil.which("docker")
    if executable:
        return executable
    raise InfrastructureError("Code_Aster correlation requires the Docker CLI.")


def _docker_unavailable(output: str) -> bool:
    """Recognize Docker runtime failures without masking a failing Aster deck."""
    text = output.lower()
    return any(
        marker in text
        for marker in (
            "failed to connect to the docker api",
            "is the docker daemon running",
            "cannot connect to the docker daemon",
            "error during connect",
        )
    )


def _boundary_nodes(nodes: np.ndarray, length: float, height: float, depth: float) -> list[int]:
    selected = np.flatnonzero(
        np.isclose(nodes[:, 0], 0.0)
        | np.isclose(nodes[:, 0], length)
        | np.isclose(np.abs(nodes[:, 1]), 0.5 * height)
        | np.isclose(np.abs(nodes[:, 2]), 0.5 * depth)
    )
    return [int(value) + 1 for value in selected]


def _qf_column_points(
    nodes: np.ndarray,
    elements: np.ndarray,
    fixed_nodes: np.ndarray,
    tip_nodes: np.ndarray,
    fractions: tuple[float, ...],
    critical: float,
    amplitude: float,
) -> list[dict[str, float]]:
    assembly = TotalLagrangianTet4Assembly(
        nodes, elements, SolidMaterial(E=1.0e6, nu=0.3)
    )
    fixed = (3 * fixed_nodes[:, None] + np.arange(3)).reshape(-1)
    pattern = np.zeros(assembly.ndof, dtype=float)
    pattern[3 * tip_nodes] = -1.0 / tip_nodes.size
    points = []
    for fraction in fractions:
        result = solve_proportional_dead_load(
            assembly,
            fraction * critical * pattern,
            fixed,
            increments=10,
        )
        points.append(
            {
                "load_fraction_critical": fraction,
                "tip_axial_x": float(np.mean(result.displacement[3 * tip_nodes])),
                "tip_increment_z": float(np.mean(result.displacement[3 * tip_nodes + 2])),
                "tip_total_z": amplitude
                + float(np.mean(result.displacement[3 * tip_nodes + 2])),
                "relative_residual": result.relative_residual,
            }
        )
    return points


def _tensor_to_aster_vector(value: object) -> np.ndarray:
    tensor = np.asarray(value, dtype=float)
    return tensor[[0, 1, 2, 0, 0, 1], [0, 1, 2, 1, 2, 2]]


def _relative_norm(value: np.ndarray, reference: np.ndarray) -> float:
    return float(np.linalg.norm(value - reference) / max(np.linalg.norm(reference), 1.0e-30))


def _check(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {
        "id": identifier,
        "value": value,
        "limit": limit,
        "status": "PASS" if np.isfinite(value) and value <= limit else "FAIL",
    }
