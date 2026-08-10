"""CalculiX S8R composite correlation on the conical-cutout laminate."""

from __future__ import annotations

import subprocess
import re
from dataclasses import dataclass
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from solveur.api import solve_model
from solveur.core.assembler import GlobalAssembler
from solveur.core.model import FiniteElementModel
from solveur.io.manifest import write_json_file
from solveur.verification.calculix_composite import parse_original_frd_displacement
from solveur.verification.composite_conical_cutout import (
    CompositeConicalCutoutStudy,
    build_composite_conical_cutout_model,
)
from solveur.verification.mitc4_conical_cutout import (
    _relative,
    _vector_displacements,
)
from solveur.verification.vnv_manifest import write_vnv_manifest


STUDY_ID = "VNV-COMP-CONICAL-CUTOUT-CALCULIX-S8R-011"
_PLY_STRESS_LINE = re.compile(
    r"^\s*(?P<element>\d+)\s+(?P<point>\d+)\s+"
    r"(?P<sxx>[+-]?[\d.]+E[+-]\d+)\s+(?P<syy>[+-]?[\d.]+E[+-]\d+)\s+"
    r"(?P<szz>[+-]?[\d.]+E[+-]\d+)\s+(?P<sxy>[+-]?[\d.]+E[+-]\d+)\s+"
    r"(?P<sxz>[+-]?[\d.]+E[+-]\d+)\s+(?P<syz>[+-]?[\d.]+E[+-]\d+)\s+"
    r"E(?P<label_element>\d+)P(?P<ply>\d+)_"
)


@dataclass(frozen=True)
class ConicalS8RMesh:
    """Quadratic CalculiX mesh with a mapping to the QF corner grid."""

    nodes: np.ndarray
    elements: tuple[tuple[int, ...], ...]
    outer_nodes: tuple[int, ...]
    qf_node_ids: np.ndarray


class CalculixCompositeConicalCutoutCorrelation:
    """Cross-correlate projected-axis MITC4 and S8R on the same cone mesh."""

    study_id = STUDY_ID
    meshes = ((8, 24), (12, 36), (16, 48))

    def __init__(self, output_dir: str | Path, *, image: str = "qf-solver/calculix-nafems13h:2.20"):
        self.output_dir = Path(output_dir).resolve()
        self.image = image

    def run(self) -> dict[str, object]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        rows: list[dict[str, object]] = []
        fine: tuple[FiniteElementModel, np.ndarray, np.ndarray] | None = None
        for radial, circumferential in self.meshes:
            row, fine = self._run_mesh(radial, circumferential)
            rows.append(row)
        checks = [
            _upper("fine_probe_uz_difference", float(rows[-1]["probe_uz_difference"]), 0.03),
            _upper("fine_vector_difference", float(rows[-1]["vector_difference"]), 0.03),
            _upper("qf_final_increment", _relative(rows[-1]["qf_probe_uz_m"], rows[-2]["qf_probe_uz_m"]), 0.03),
            _upper(
                "calculix_final_increment",
                _relative(rows[-1]["calculix_probe_uz_m"], rows[-2]["calculix_probe_uz_m"]),
                0.03,
            ),
        ]
        summary: dict[str, object] = {
            "study_id": STUDY_ID,
            "status": "PASS_EXTERNAL_CORRELATION" if all(c["status"] == "PASS" for c in checks) else "WARNING",
            "maturity": "experimental",
            "external_solver": {"name": "CalculiX", "version": "2.20", "image": self.image, "element": "S8R COMPOSITE"},
            "qf_element": "MITC4 shell_laminate",
            "comparison_basis": "Same conical corner mesh, [0/+45/-45/90] layup, projected [1,0,0] material axis, outer-rim clamp and QF's complete consistent pressure vector transferred to CalculiX CLOAD.",
            "rows": rows,
            "checks": checks,
            "limitations": [
                "MITC4 is linear/faceted while CalculiX S8R is quadratic; this is a cross-formulation convergence correlation.",
                "The CalculiX deck receives QF's already-integrated pressure vector; this isolates shell stiffness and projected material axes, not native pressure quadrature.",
                "Ply stresses at the free opening remain inspection-only until distance-controlled external extraction is added.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        if fine is not None:
            self._plot(*fine, rows)
        self._write_report(summary)
        write_vnv_manifest(self.output_dir, STUDY_ID)
        return summary

    def _run_mesh(
        self, radial: int, circumferential: int
    ) -> tuple[dict[str, object], tuple[FiniteElementModel, np.ndarray, np.ndarray]]:
        qf_model, probe = build_loaded_qf_model(radial, circumferential)
        qf_result = solve_model(qf_model)
        qf = _vector_displacements(qf_result, qf_model)
        mesh = build_conical_s8r_mesh(radial, circumferential)
        stem = f"composite_conical_s8r_{radial}x{circumferential}"
        write_conical_s8r_input(self.output_dir / f"{stem}.inp", mesh, qf_model)
        self._execute(stem)
        calculix_full = parse_original_frd_displacement(self.output_dir / f"{stem}.frd", len(mesh.nodes))
        calculix = calculix_full[mesh.qf_node_ids]
        return (
            {
                "radial_elements": radial,
                "circumferential_elements": circumferential,
                "elements": radial * circumferential,
                "qf_probe_uz_m": float(qf[probe, 2]),
                "calculix_probe_uz_m": float(calculix[probe, 2]),
                "probe_uz_difference": _relative(qf[probe, 2], calculix[probe, 2]),
                "vector_difference": float(
                    np.linalg.norm(qf - calculix) / max(np.linalg.norm(calculix), np.finfo(float).tiny)
                ),
            },
            (qf_model, qf, calculix),
        )

    def _execute(self, stem: str) -> None:
        completed = subprocess.run(
            ["docker", "run", "--rm", "-v", f"{self.output_dir}:/work", "-w", "/work", self.image, stem],
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        (self.output_dir / f"{stem}.log").write_text(completed.stdout + completed.stderr, encoding="utf-8")
        if completed.returncode:
            raise RuntimeError(
                "CalculiX composite conical run failed:\n"
                + "\n".join((completed.stdout + completed.stderr).splitlines()[-50:])
            )

    def _plot(
        self, model: FiniteElementModel, qf: np.ndarray, calculix: np.ndarray, rows: list[dict[str, object]]
    ) -> None:
        scale = 0.12 / max(float(np.max(np.linalg.norm(calculix, axis=1))), 1.0e-30)
        figure = plt.figure(figsize=(9.6, 4.7))
        for index, (name, displacement, color) in enumerate(
            (("QF MITC4", qf, "#c44536"), ("CalculiX S8R", calculix, "#315d84")), start=1
        ):
            axis = figure.add_subplot(1, 2, index, projection="3d")
            nodes = model.nodes + scale * displacement
            for element in model.elements:
                quad = np.asarray(element.nodes, dtype=int)
                loop = np.append(quad, quad[0])
                axis.plot(nodes[loop, 0], nodes[loop, 1], nodes[loop, 2], color=color, linewidth=0.32)
            axis.set(title=f"{name} x{scale:.1f}", xlabel="X [m]", ylabel="Y [m]", zlabel="Z [m]")
            axis.set_box_aspect((1.0, 1.0, 0.32))
            axis.view_init(elev=26.0, azim=-54.0)
        figure.tight_layout()
        figure.savefig(self.output_dir / "composite_conical_calculix_deformation.png", dpi=180)
        plt.close(figure)
        figure, axis = plt.subplots(figsize=(7.1, 4.3))
        elements = [int(row["elements"]) for row in rows]
        axis.semilogx(elements, [abs(float(row["qf_probe_uz_m"])) for row in rows], "o-", label="QF MITC4")
        axis.semilogx(elements, [abs(float(row["calculix_probe_uz_m"])) for row in rows], "s-", label="CalculiX S8R")
        axis.set(xlabel="Elements", ylabel="|UZ sonde| [m]", title="Coque composite conique")
        axis.grid(True, which="both", alpha=0.25)
        axis.legend()
        figure.tight_layout()
        figure.savefig(self.output_dir / "composite_conical_calculix_correlation.png", dpi=180)
        plt.close(figure)

    def _write_report(self, summary: dict[str, object]) -> None:
        lines = [
            f"# {STUDY_ID}",
            "",
            f"Statut : **{summary['status']}**",
            "",
            "| Maillage | UZ QF [m] | UZ CalculiX [m] | Ecart sonde | Ecart vecteur |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
        for row in summary["rows"]:
            lines.append(
                f"| {row['radial_elements']}x{row['circumferential_elements']} | {row['qf_probe_uz_m']:.7e} | {row['calculix_probe_uz_m']:.7e} | {100 * row['probe_uz_difference']:.3f} % | {100 * row['vector_difference']:.3f} % |"
            )
        lines.extend(
            [
                "",
                "![Correlation](composite_conical_calculix_correlation.png)",
                "",
                "![Deformees](composite_conical_calculix_deformation.png)",
                "",
            ]
        )
        (self.output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def build_loaded_qf_model(radial: int, circumferential: int) -> tuple[FiniteElementModel, int]:
    """Build the regular pressure case used by the internal composite campaign."""
    return build_composite_conical_cutout_model(radial, circumferential)


def build_conical_s8r_mesh(radial: int, circumferential: int) -> ConicalS8RMesh:
    """Create quadratic S8R nodes on the exact conical surface."""
    ids: dict[tuple[int, int], int] = {}
    points: list[list[float]] = []
    qf_ids: list[int] = []
    for i in range(2 * radial + 1):
        radius = 0.20 + 0.55 * i / (2 * radial)
        for j in range(2 * circumferential):
            if i % 2 and j % 2:
                continue
            ids[i, j] = len(points) + 1
            theta = 2.0 * np.pi * j / (2 * circumferential)
            points.append([radius * np.cos(theta), radius * np.sin(theta), 0.35 * (radius - 0.20)])
    for i in range(radial + 1):
        for j in range(circumferential):
            qf_ids.append(ids[2 * i, 2 * j] - 1)
    elements = []
    for i in range(radial):
        for j in range(circumferential):
            a, b = 2 * i, 2 * j
            nxt = (b + 2) % (2 * circumferential)
            elements.append(
                (
                    ids[a, b],
                    ids[a + 2, b],
                    ids[a + 2, nxt],
                    ids[a, nxt],
                    ids[a + 1, b],
                    ids[a + 2, b + 1],
                    ids[a + 1, nxt],
                    ids[a, b + 1],
                )
            )
    outer = tuple(ids[2 * radial, j] for j in range(2 * circumferential))
    return ConicalS8RMesh(np.asarray(points), tuple(elements), outer, np.asarray(qf_ids, dtype=int))


def write_conical_s8r_input(
    path: str | Path,
    mesh: ConicalS8RMesh,
    qf_model: FiniteElementModel,
    *,
    include_ply_stress_output: bool = False,
) -> Path:
    """Write S8R composite deck with optional integration-point ply stresses."""
    target = Path(path)
    lines = ["*HEADING", "QF_solver composite conical cutout", "*NODE"]
    lines.extend(f"{i},{p[0]:.14g},{p[1]:.14g},{p[2]:.14g}" for i, p in enumerate(mesh.nodes, 1))
    lines.append("*ELEMENT,TYPE=S8R,ELSET=EALL")
    lines.extend(f"{i}," + ",".join(map(str, e)) for i, e in enumerate(mesh.elements, 1))
    lines.extend(["*NSET,NSET=FIXED", *_csv(mesh.outer_nodes)])
    for index, element in enumerate(mesh.elements, 1):
        center = np.mean(mesh.nodes[np.asarray(element[:4]) - 1], axis=0)
        normal = np.array([-0.35 * center[0], -0.35 * center[1], np.linalg.norm(center[:2])])
        normal /= np.linalg.norm(normal)
        first = np.array([1.0, 0.0, 0.0])
        first -= np.dot(first, normal) * normal
        first /= np.linalg.norm(first)
        for ply, angle_deg in enumerate(CompositeConicalCutoutStudy.angles):
            angle = np.deg2rad(angle_deg)
            axis = np.cos(angle) * first + np.sin(angle) * np.cross(normal, first)
            second = np.cross(normal, axis)
            lines.extend([f"*ORIENTATION,NAME=E{index}P{ply}", ",".join(f"{v:.10g}" for v in (*axis, *second))])
        lines.extend([f"*ELSET,ELSET=E{index}", str(index)])
    lines.extend(
        [
            "*MATERIAL,NAME=LAMINA",
            "*ELASTIC,TYPE=ENGINEERING CONSTANTS",
            "1.35e11,1.0e10,1.0e10,0.3,0.3,0.4,5.0e9,4.5e9",
            "3.8e9",
            "*DENSITY",
            "1600.",
        ]
    )
    for index in range(1, len(mesh.elements) + 1):
        lines.append(f"*SHELL SECTION,ELSET=E{index},COMPOSITE")
        lines.extend(f"0.002,,LAMINA,E{index}P{ply}" for ply in range(4))
    loads = _qf_pressure_cloads(qf_model, mesh)
    lines.extend(["*BOUNDARY", "FIXED,1,6", "*STEP", "*STATIC", "*CLOAD"])
    lines.extend(f"{node},{component},{value:.16g}" for node, component, value in loads)
    lines.extend(["*NODE FILE,OUTPUT=2D", "U"])
    if include_ply_stress_output:
        # CalculiX writes shell stresses at integration points by default.  Do
        # not request a non-portable POSITION parameter: 2.20 rejects it.
        lines.extend(["*EL PRINT,ELSET=EALL", "S"])
    lines.append("*END STEP")
    target.write_text("\n".join(lines) + "\n", encoding="ascii")
    return target


def _qf_pressure_cloads(model: FiniteElementModel, mesh: ConicalS8RMesh) -> list[tuple[int, int, float]]:
    """Map QF's full consistent pressure vector to matching S8R corner nodes."""
    dofs = model.dof_manager()
    vector = GlobalAssembler().assemble_loads(model, dofs)
    loads: list[tuple[int, int, float]] = []
    for qf_node, s8r_node in enumerate(mesh.qf_node_ids):
        for component, name in enumerate(("UX", "UY", "UZ"), start=1):
            value = float(vector[dofs.index(qf_node, name)])
            if abs(value) > 1.0e-14:
                loads.append((int(s8r_node) + 1, component, value))
    return loads


def parse_calculix_composite_ply_stresses(path: str | Path) -> list[dict[str, object]]:
    """Parse CalculiX S8R integration-point stresses with their ply label.

    The parser deliberately accepts only the documented text layout written by
    the controlled deck.  It avoids nodal extrapolation and preserves the
    original element, integration-point and ply identifiers for traceability.
    """
    records: list[dict[str, object]] = []
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        match = _PLY_STRESS_LINE.match(line)
        if match is None:
            continue
        values = match.groupdict()
        element = int(values["element"])
        if element != int(values["label_element"]):
            raise ValueError(f"CalculiX ply-stress label does not match element {element}.")
        records.append(
            {
                "element": element,
                "integration_point": int(values["point"]),
                "ply_index": int(values["ply"]),
                "stress_output": [float(values[name]) for name in ("sxx", "syy", "szz", "sxy", "sxz", "syz")],
            }
        )
    if not records:
        raise ValueError(f"No composite S8R integration-point stresses found in {Path(path).name}.")
    return records


def _csv(values: tuple[int, ...]) -> list[str]:
    return [",".join(map(str, values[i : i + 16])) for i in range(0, len(values), 16)]


def _upper(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if value <= limit else "FAIL"}
