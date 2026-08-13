"""High-resolution MITC3+ shell benchmarks used for Owner review."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

from solveur.api import solve_model
from solveur.core.model import FiniteElementModel
from solveur.io.manifest import write_json_file
from solveur.verification.mitc3_models import pinched_cylinder_model, scordelis_model
from solveur.verification.vnv_manifest import write_vnv_manifest


@dataclass(frozen=True)
class RefinedMitc3Case:
    """Definition of one deterministic high-resolution shell benchmark."""

    key: str
    study_id: str
    nx: int
    ny: int
    element_count: int
    reference: float
    tolerance: float
    builder: Callable[[int, int], tuple[FiniteElementModel, object]]


def refined_cases() -> tuple[RefinedMitc3Case, ...]:
    """Return review meshes near 20k triangles without degrading their aspect ratios."""
    return (
        RefinedMitc3Case(
            key="scordelis",
            study_id="VNV-MITC3-SCORDELIS-005-H20K",
            nx=100,
            ny=100,
            element_count=20_000,
            reference=-0.3024,
            tolerance=0.05,
            builder=scordelis_model,
        ),
        RefinedMitc3Case(
            key="pinched",
            study_id="VNV-MITC3-PINCHED-006-H20K",
            nx=70,
            ny=140,
            element_count=19_600,
            reference=1.8248e-5,
            tolerance=0.10,
            builder=pinched_cylinder_model,
        ),
    )


class Mitc3RefinedShellCampaign:
    """Solve and publish refined Scordelis-Lo and pinched-cylinder evidence."""

    def __init__(self, output: str | Path) -> None:
        self.output = Path(output)

    def run(self) -> dict[str, Any]:
        self.output.mkdir(parents=True, exist_ok=True)
        results = {case.key: self._run_case(case) for case in refined_cases()}
        status = "PASS" if all(row["status"] == "PASS" for row in results.values()) else "FAIL"
        summary = {
            "schema_version": 1,
            "campaign": "MITC3-PLUS-REFINED-SHELL-H20K",
            "profile": "engineering",
            "maturity": "experimental",
            "status": status,
            "cases": results,
            "decision_note": (
                "Numerical PASS is evidence for Owner review; it does not change "
                "the MITC3+ maturity without a signed review."
            ),
        }
        write_json_file(self.output / "summary.json", summary)
        self._plot_convergence(results)
        self._write_report(summary)
        write_vnv_manifest(self.output, "VNV-MITC3-REFINED-SHELL-H20K")
        return summary

    def _run_case(self, case: RefinedMitc3Case) -> dict[str, Any]:
        model, monitor = case.builder(case.nx, case.ny)
        connectivity = np.asarray([element.nodes for element in model.elements], dtype=np.int64)
        if len(connectivity) != case.element_count:
            raise RuntimeError(
                f"{case.key}: expected {case.element_count} triangles, got {len(connectivity)}."
            )
        started = perf_counter()
        result = solve_model(model, enforce_policy=False)
        elapsed = perf_counter() - started
        translations = _nodal_translations(model, result)
        if case.key == "scordelis":
            edge = tuple(int(node) for node in monitor)
            value = 0.5 * sum(
                float(result.displacements[result.dofs.index(node, "UZ")]) for node in edge
            )
        else:
            node = int(monitor)
            value = abs(float(result.displacements[result.dofs.index(node, "UY")]))
        relative_error = abs(value - case.reference) / abs(case.reference)
        scale = _plot_deformation(
            model,
            connectivity,
            translations,
            self.output / f"{case.key}_mesh_deformation.png",
            title=_case_title(case),
        )
        np.savez_compressed(
            self.output / f"{case.key}_field.npz",
            nodes=np.asarray(model.nodes, dtype=np.float64),
            triangles=connectivity,
            translations=translations,
        )
        solver = dict(getattr(result, "solver", {}))
        return {
            "study_id": case.study_id,
            "status": "PASS" if relative_error <= case.tolerance else "FAIL",
            "mesh": {
                "nx": case.nx,
                "ny": case.ny,
                "nodes": model.node_count,
                "elements": len(model.elements),
                "dofs": result.dofs.ndof,
            },
            "value": value,
            "reference": case.reference,
            "relative_error": relative_error,
            "tolerance": case.tolerance,
            "maximum_translation": float(np.max(np.linalg.norm(translations, axis=1))),
            "deformation_scale": scale,
            "solve_elapsed_seconds": elapsed,
            "solver_status": str(getattr(result, "status", "unknown")),
            "solver_diagnostics": _scalar_diagnostics(solver),
        }

    def _plot_convergence(self, refined: dict[str, dict[str, Any]]) -> None:
        baseline = _baseline_points()
        figure, axes = plt.subplots(1, 2, figsize=(12.0, 4.8))
        for axis, key, title in (
            (axes[0], "scordelis", "Scordelis-Lo"),
            (axes[1], "pinched", "Cylindre pince"),
        ):
            points = list(baseline.get(key, []))
            current = refined[key]
            points.append(
                {
                    "element_count": current["mesh"]["elements"],
                    "relative_error": current["relative_error"],
                }
            )
            x = np.asarray([row["element_count"] for row in points], dtype=float)
            y = 100.0 * np.asarray([row["relative_error"] for row in points], dtype=float)
            axis.loglog(x, y, "o-", color="#176b87", linewidth=1.8)
            axis.scatter(x[-1], y[-1], s=70, color="#b34a23", zorder=3, label="raffinement ~20k")
            axis.axhline(
                100.0 * float(current["tolerance"]),
                color="#5f6b70",
                linestyle="--",
                linewidth=1.1,
                label="seuil",
            )
            axis.set_title(title)
            axis.set_xlabel("Nombre de triangles")
            axis.set_ylabel("Ecart relatif [%]")
            axis.grid(True, which="both", alpha=0.25)
            axis.legend(fontsize=8)
        figure.suptitle("MITC3+ - convergence des benchmarks de coque")
        figure.tight_layout()
        figure.savefig(self.output / "refined_convergence.png", dpi=180, bbox_inches="tight")
        plt.close(figure)

    def _write_report(self, summary: dict[str, Any]) -> None:
        rows = []
        for key in ("scordelis", "pinched"):
            case = summary["cases"][key]
            rows.append(
                "| {name} | {elements:,} | {dofs:,} | {value:.10e} | "
                "{reference:.10e} | {error:.4f} % | {status} |".format(
                    name="Scordelis-Lo" if key == "scordelis" else "Cylindre pince",
                    elements=case["mesh"]["elements"],
                    dofs=case["mesh"]["dofs"],
                    value=case["value"],
                    reference=case["reference"],
                    error=100.0 * case["relative_error"],
                    status=case["status"],
                )
            )
        report = [
            "---",
            "doc_id: DOC-VNV-MITC3-REFINED-H20K",
            "revision: 0.1",
            "status: ready_for_owner_review",
            'applicable_version: ">=0.3.0"',
            "reviewer: ''",
            "approver: ''",
            "---",
            "",
            "# MITC3+ - Raffinement Scordelis-Lo et cylindre pince",
            "",
            "Cette campagne ajoute un point proche de 20 000 triangles aux deux "
            "benchmarks courbes. Le cylindre conserve le rapport historique "
            "`ntheta = 2*nx`, d'ou 19 600 triangles plutot qu'un compte artificiel "
            "exact qui degraderait la regularite du maillage.",
            "",
            "| Cas | Elements | DDL | Reponse QF_solver | Reference | Ecart | Verdict |",
            "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
            *rows,
            "",
            "![Convergence](refined_convergence.png)",
            "",
            "## Scordelis-Lo",
            "",
            "![Maillage et deformee Scordelis-Lo](scordelis_mesh_deformation.png)",
            "",
            "## Cylindre pince",
            "",
            "![Maillage et deformee du cylindre pince](pinched_mesh_deformation.png)",
            "",
            "## Decision",
            "",
            "Le verdict automatique ne constitue pas une qualification. La decision "
            "de maturite exige la revue owner des references, conditions aux limites, "
            "courbes, deformees et limites du domaine.",
        ]
        (self.output / "owner_review.md").write_text("\n".join(report) + "\n", encoding="utf-8")


def _nodal_translations(model: FiniteElementModel, result: object) -> np.ndarray:
    values = np.asarray(getattr(result, "displacements"), dtype=float)
    dofs = getattr(result, "dofs")
    translations = np.zeros((model.node_count, 3), dtype=float)
    for node in range(model.node_count):
        for component, name in enumerate(("UX", "UY", "UZ")):
            translations[node, component] = values[dofs.index(node, name)]
    return translations


def _plot_deformation(
    model: FiniteElementModel,
    triangles: np.ndarray,
    translations: np.ndarray,
    output: Path,
    *,
    title: str,
) -> float:
    nodes = np.asarray(model.nodes, dtype=float)
    magnitude = np.linalg.norm(translations, axis=1)
    span = max(float(np.ptp(nodes, axis=0).max()), 1.0)
    maximum = max(float(magnitude.max()), 1.0e-30)
    scale = 0.12 * span / maximum
    deformed = nodes + scale * translations
    face_values = np.mean(magnitude[triangles], axis=1)
    colors = plt.get_cmap("viridis")(face_values / maximum)
    figure = plt.figure(figsize=(12.0, 5.2))
    initial_axis = figure.add_subplot(121, projection="3d")
    deformed_axis = figure.add_subplot(122, projection="3d")
    sample_step = max(1, len(triangles) // 5000)
    sampled = triangles[::sample_step]
    initial_axis.add_collection3d(
        Poly3DCollection(
            nodes[sampled],
            facecolors="#dce5e8",
            edgecolors="#4d5960",
            linewidths=0.12,
            alpha=0.95,
        )
    )
    deformed_axis.add_collection3d(
        Poly3DCollection(
            deformed[triangles],
            facecolors=colors,
            edgecolors="#263238",
            linewidths=0.035,
            alpha=0.96,
        )
    )
    fixed = np.asarray(sorted({condition.node for condition in model.fixed_dofs}), dtype=int)
    if fixed.size:
        initial_axis.scatter(*nodes[fixed].T, marker="s", s=5, color="#151f24")
        deformed_axis.scatter(*deformed[fixed].T, marker="s", s=5, color="#151f24")
    for axis, coordinates, label in (
        (initial_axis, nodes, "Geometrie et maillage"),
        (deformed_axis, deformed, f"Deformee amplifiee x{scale:.3g}"),
    ):
        _equal_axes(axis, coordinates)
        axis.set_title(label)
        axis.set_xlabel("X")
        axis.set_ylabel("Y")
        axis.set_zlabel("Z")
        axis.view_init(elev=24.0, azim=-58.0)
    scalar = plt.cm.ScalarMappable(cmap="viridis", norm=plt.Normalize(0.0, maximum))
    scalar.set_array([])
    colorbar = figure.colorbar(scalar, ax=deformed_axis, shrink=0.68, pad=0.08)
    colorbar.set_label("Norme du deplacement")
    figure.suptitle(title)
    figure.tight_layout()
    figure.savefig(output, dpi=180, bbox_inches="tight")
    plt.close(figure)
    return float(scale)


def _equal_axes(axis: object, coordinates: np.ndarray) -> None:
    minimum = coordinates.min(axis=0)
    maximum = coordinates.max(axis=0)
    center = 0.5 * (minimum + maximum)
    half = 0.52 * max(float(np.max(maximum - minimum)), 1.0)
    axis.set_xlim(center[0] - half, center[0] + half)
    axis.set_ylim(center[1] - half, center[1] + half)
    axis.set_zlim(center[2] - half, center[2] + half)


def _baseline_points() -> dict[str, list[dict[str, Any]]]:
    path = Path("qualification") / "vnv" / "mitc3" / "reference_v2" / "summary.json"
    if not path.is_file():
        return {}
    import json

    payload = json.loads(path.read_text(encoding="utf-8"))
    studies = payload.get("studies", {})
    return {
        key: list(studies.get(key, {}).get("points", []))
        for key in ("scordelis", "pinched")
    }


def _scalar_diagnostics(values: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in values.items()
        if isinstance(value, (str, int, float, bool)) and key not in {"message"}
    }


def _case_title(case: RefinedMitc3Case) -> str:
    name = "Scordelis-Lo" if case.key == "scordelis" else "Cylindre pince"
    return f"MITC3+ - {name} - {case.element_count:,} triangles"
