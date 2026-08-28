"""Same-mesh CalculiX S4 correlation for the conical MITC4 cutout study."""

from __future__ import annotations

import subprocess
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from solveur.api import solve_model
from solveur.core.assembly.assembler import GlobalAssembler
from solveur.core.model import FiniteElementModel
from solveur.io.manifest import write_json_file
from solveur.verification.calculix_composite import parse_original_frd_displacement
from solveur.verification.mitc4_conical_cutout import (
    STUDY_ID as INTERNAL_STUDY_ID,
    _outer_ring_nodes,
    _relative,
    _vector_displacements,
    build_conical_cutout_model,
)
from solveur.verification.vnv_manifest import write_vnv_manifest


STUDY_ID = "VNV-MITC4-CONICAL-CUTOUT-CALCULIX-S4-013"


class CalculixMitc4ConicalCutoutCorrelation:
    """Compare MITC4 with CalculiX S4 on identical faceted conical meshes."""

    study_id = STUDY_ID
    meshes = ((8, 24), (12, 36), (16, 48))

    def __init__(self, output_dir: str | Path, *, image: str = "qf-solver/calculix-nafems13h:2.20"):
        self.output_dir = Path(output_dir).resolve()
        self.image = image

    def run(self) -> dict[str, object]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        rows: list[dict[str, object]] = []
        payload: tuple[FiniteElementModel, np.ndarray, np.ndarray] | None = None
        for radial, circumferential in self.meshes:
            row, payload = self._run_mesh(radial, circumferential)
            rows.append(row)
        checks = [
            _upper("fine_probe_uz_difference", float(rows[-1]["probe_uz_difference"]), 0.05),
            _upper("fine_displacement_vector_difference", float(rows[-1]["vector_difference"]), 0.08),
            _upper("maximum_reaction_resultant_difference", max(float(row["reaction_resultant_difference"]) for row in rows), 2.0e-5),
            _upper("qf_final_increment", _relative(rows[-1]["qf_probe_uz_m"], rows[-2]["qf_probe_uz_m"]), 0.05),
            _upper("calculix_final_increment", _relative(rows[-1]["calculix_probe_uz_m"], rows[-2]["calculix_probe_uz_m"]), 0.05),
        ]
        passed = all(check["status"] == "PASS" for check in checks)
        summary: dict[str, object] = {
            "study_id": STUDY_ID,
            "status": "PASS_EXTERNAL_CORRELATION" if passed else "WARNING",
            "maturity": "engineering_internal_supplementary_evidence",
            "internal_study": INTERNAL_STUDY_ID,
            "external_solver": {
                "name": "CalculiX",
                "version": "2.20",
                "image": self.image,
                "element": "S4 isotropic shell",
            },
            "qf_element": "MITC4 isotropic shell",
            "comparison_basis": (
                "Same node coordinates, S4/MITC4 four-node connectivity, thickness, "
                "isotropic material and outer-rim clamp. The CalculiX deck receives the "
                "exact consistent nodal pressure vector integrated by QF_solver."
            ),
            "same_element": False,
            "rows": rows,
            "checks": checks,
            "limitations": [
                "S4 and MITC4 are distinct shell formulations; this is not an element identity test.",
                "The conical surface is represented by common planar facets in both solvers.",
                "The external pressure is intentionally transferred as QF consistent nodal loads; CalculiX *DLOAD P has a different shell-load convention on this deck.",
                "CalculiX S4 RF output is retained as a diagnostic only: its support resultant is not yet accepted as an equivalent global reaction for this CLOAD deck.",
                "Free-edge peak stresses are intentionally excluded from the comparison scalar.",
                "No geometric nonlinearity, contact, buckling or follower pressure is covered.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        if payload is not None:
            self._plot_deformation(*payload)
        self._plot_convergence(rows)
        self._write_report(summary)
        write_vnv_manifest(self.output_dir, STUDY_ID)
        return summary

    def _run_mesh(self, radial: int, circumferential: int) -> tuple[dict[str, object], tuple[FiniteElementModel, np.ndarray, np.ndarray]]:
        model, probe = build_conical_cutout_model(radial, circumferential)
        qf_result = solve_model(model)
        qf = _vector_displacements(qf_result, model)
        stem = f"conical_cutout_s4_{radial}x{circumferential}"
        write_calculix_conical_cutout_input(self.output_dir / f"{stem}.inp", model)
        self._execute(stem)
        calculix = parse_original_frd_displacement(self.output_dir / f"{stem}.frd", model.node_count)
        calculix_support_internal = _parse_total_reaction(self.output_dir / f"{stem}.dat")
        fixed_c_load = _fixed_c_load_resultant(model)
        # CalculiX RF is the internal nodal force. Recover the net support reaction
        # by removing the CLOAD entries placed directly on constrained nodes.
        calculix_reaction = calculix_support_internal - fixed_c_load
        qf_reaction = np.asarray(qf_result.audit.equilibrium["reaction_resultant"], dtype=float)
        qf_probe = float(qf[probe, 2])
        calculix_probe = float(calculix[probe, 2])
        difference = _relative(qf_probe, calculix_probe)
        return (
            {
                "radial_elements": radial,
                "circumferential_elements": circumferential,
                "elements": len(model.elements),
                "nodes": model.node_count,
                "probe_node": probe,
                "qf_probe_uz_m": qf_probe,
                "calculix_probe_uz_m": calculix_probe,
                "probe_uz_difference": difference,
                "vector_difference": float(
                    np.linalg.norm(qf - calculix) / max(np.linalg.norm(calculix), np.finfo(float).tiny)
                ),
                "qf_reaction_resultant_n": qf_reaction.tolist(),
                "calculix_support_internal_resultant_n": calculix_support_internal.tolist(),
                "calculix_fixed_c_load_resultant_n": fixed_c_load.tolist(),
                "calculix_net_reaction_resultant_n": calculix_reaction.tolist(),
                "reaction_resultant_difference": float(
                    np.linalg.norm(qf_reaction - calculix_reaction)
                    / max(np.linalg.norm(qf_reaction), np.finfo(float).tiny)
                ),
            },
            (model, qf, calculix),
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
            tail = "\n".join((completed.stdout + completed.stderr).splitlines()[-50:])
            raise RuntimeError(f"CalculiX S4 conical-cutout run failed for {stem}:\n{tail}")

    def _plot_deformation(self, model: FiniteElementModel, qf: np.ndarray, calculix: np.ndarray) -> None:
        scale = 0.12 / max(float(np.max(np.linalg.norm(calculix, axis=1))), 1.0e-30)
        figure = plt.figure(figsize=(9.6, 4.8))
        for index, (name, displacement, color) in enumerate(
            (("QF_solver MITC4", qf, "#c44536"), ("CalculiX S4", calculix, "#315d84")), start=1
        ):
            axis = figure.add_subplot(1, 2, index, projection="3d")
            nodes = model.nodes + scale * displacement
            for element in model.elements:
                quad = np.asarray(element.nodes, dtype=int)
                loop = np.append(quad, quad[0])
                axis.plot(nodes[loop, 0], nodes[loop, 1], nodes[loop, 2], color=color, linewidth=0.36)
            axis.set(title=f"{name}, x{scale:.1f}", xlabel="X [m]", ylabel="Y [m]", zlabel="Z [m]")
            axis.set_box_aspect((1.0, 1.0, 0.32))
            axis.view_init(elev=26.0, azim=-54.0)
        figure.tight_layout()
        figure.savefig(self.output_dir / "conical_cutout_calculix_deformation.png", dpi=180)
        plt.close(figure)

    def _plot_convergence(self, rows: list[dict[str, object]]) -> None:
        elements = [int(row["elements"]) for row in rows]
        figure, axes = plt.subplots(1, 2, figsize=(10.2, 4.3))
        axes[0].semilogx(elements, [abs(float(row["qf_probe_uz_m"])) for row in rows], "o-", label="QF MITC4")
        axes[0].semilogx(elements, [abs(float(row["calculix_probe_uz_m"])) for row in rows], "s-", label="CalculiX S4")
        axes[0].set(xlabel="Elements", ylabel="|UZ sonde| [m]", title="Convergence meme maillage")
        axes[0].grid(True, which="both", alpha=0.25)
        axes[0].legend()
        axes[1].loglog(elements, [float(row["probe_uz_difference"]) for row in rows], "^-", label="Sonde UZ")
        axes[1].loglog(elements, [float(row["vector_difference"]) for row in rows], "o-", label="Vecteur nodal")
        axes[1].loglog(elements, [float(row["reaction_resultant_difference"]) for row in rows], "s-", label="Resultante reaction")
        axes[1].axhline(0.05, color="#c44536", linestyle="--", linewidth=1.0, label="Seuil sonde")
        axes[1].set(xlabel="Elements", ylabel="Ecart relatif", title="Ecart QF / CalculiX")
        axes[1].grid(True, which="both", alpha=0.25)
        axes[1].legend()
        figure.tight_layout()
        figure.savefig(self.output_dir / "conical_cutout_calculix_correlation.png", dpi=180)
        plt.close(figure)

    def _write_report(self, summary: dict[str, object]) -> None:
        lines = [
            f"# {STUDY_ID}", "", f"Statut : **{summary['status']}**", "",
            "Correlation externe sur le panneau annulaire conique ajoure. Les coordonnees,",
            "connectivites, materiau, epaisseur et appuis sont identiques. La pression QF",
            "est transferee dans CalculiX sous forme de forces nodales coherentes exactes. Les",
            "formulations restent MITC4 (QF_solver) et S4 (CalculiX).", "",
            "| Maillage | UZ QF [m] | UZ CalculiX [m] | Ecart sonde | Ecart vecteur | Ecart reaction |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
        for row in summary["rows"]:
            lines.append(
                f"| {row['radial_elements']}x{row['circumferential_elements']} | {row['qf_probe_uz_m']:.7e} | "
                f"{row['calculix_probe_uz_m']:.7e} | {100 * row['probe_uz_difference']:.3f} % | "
                f"{100 * row['vector_difference']:.3f} % | {100 * row['reaction_resultant_difference']:.3e} % |"
            )
        lines.extend([
            "", "![Correlation](conical_cutout_calculix_correlation.png)", "",
            "![Deformees](conical_cutout_calculix_deformation.png)", "",
            "La reaction nette CalculiX est obtenue par `RF - CLOAD` sur les noeuds",
            "encastres, car la sortie `RF` seule est la force interne nodale lorsque",
            "des forces sont appliquees directement sur un appui.", "",
            "Les pics de contrainte du bord libre restent hors critere de correlation :",
            "ils devront etre traites par une methode de linearisation ou d'extrapolation",
            "de contrainte dediee, avec un maillage localement raffine.", "",
        ])
        (self.output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def write_calculix_conical_cutout_input(path: str | Path, model: FiniteElementModel) -> Path:
    """Write a CalculiX S4 deck matching the QF conical-cutout model exactly."""
    target = Path(path)
    fixed = _outer_ring_nodes(model.nodes) + 1
    loads = _qf_consistent_translation_loads(model)
    lines = ["*HEADING", "QF_solver MITC4 conical cutout same-mesh correlation", "*NODE"]
    lines.extend(f"{index},{point[0]:.14g},{point[1]:.14g},{point[2]:.14g}" for index, point in enumerate(model.nodes, start=1))
    lines.append("*ELEMENT,TYPE=S4,ELSET=EALL")
    lines.extend(f"{index}," + ",".join(str(int(node) + 1) for node in element.nodes) for index, element in enumerate(model.elements, start=1))
    lines.extend(["*NSET,NSET=FIXED", *_csv_lines(fixed.tolist())])
    lines.extend([
        "*MATERIAL,NAME=ALUMINIUM", "*ELASTIC", "7.0e10,0.33", "*DENSITY", "2700.",
        "*SHELL SECTION,ELSET=EALL,MATERIAL=ALUMINIUM", "0.004", "*BOUNDARY", "FIXED,1,6",
        "*STEP", "*STATIC", "*CLOAD",
        *[f"{node},{component},{value:.16g}" for node, component, value in loads],
        "*NODE PRINT,NSET=FIXED,TOTALS=YES", "RF",
        "*NODE FILE,OUTPUT=2D", "U", "*END STEP",
    ])
    target.write_text("\n".join(lines) + "\n", encoding="ascii")
    return target


def _qf_consistent_translation_loads(model: FiniteElementModel) -> list[tuple[int, int, float]]:
    """Return the initial-normal pressure vector in CalculiX CLOAD notation."""
    dofs = model.dof_manager()
    vector = GlobalAssembler().assemble_loads(model, dofs)
    loads: list[tuple[int, int, float]] = []
    for node in range(model.node_count):
        for component, dof in enumerate(("UX", "UY", "UZ"), start=1):
            value = float(vector[dofs.index(node, dof)])
            if abs(value) > 1.0e-14:
                loads.append((node + 1, component, value))
    return loads


def _fixed_c_load_resultant(model: FiniteElementModel) -> np.ndarray:
    """Sum QF's transferred CLOAD entries that are directly applied on the support."""
    fixed = set((_outer_ring_nodes(model.nodes) + 1).tolist())
    resultant = np.zeros(3)
    for node, component, value in _qf_consistent_translation_loads(model):
        if node in fixed:
            resultant[component - 1] += value
    return resultant


def _parse_total_reaction(path: Path) -> np.ndarray:
    """Read the deterministic ``TOTALS=YES`` resultant from CalculiX text output."""
    lines = path.read_text(encoding="ascii", errors="replace").splitlines()
    for index, line in enumerate(lines):
        if "total force (fx,fy,fz) for set fixed" in line.lower():
            for candidate in lines[index + 1 : index + 5]:
                values = candidate.split()
                if len(values) >= 3:
                    try:
                        return np.asarray([float(value) for value in values[:3]], dtype=float)
                    except ValueError:
                        continue
    raise ValueError(f"CalculiX total reaction was not found in {path.name}.")


def _csv_lines(values: list[int]) -> list[str]:
    return [",".join(str(value) for value in values[index : index + 16]) for index in range(0, len(values), 16)]


def _upper(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if value <= limit else "FAIL"}
