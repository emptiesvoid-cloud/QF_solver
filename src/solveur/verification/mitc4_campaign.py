"""Executable MITC4 qualification-candidate evidence campaign."""

from __future__ import annotations

from solveur.paths import project_root

import json
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np
from scipy.linalg import eigh

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from mitc4.locking import EnhancedShearLockingStudy, LockingCampaign
from mitc4.mesh import MeshFactory
from mitc4.convergence import Mitc4StructuralConvergence
from mitc4.verification import MechanicalVerifier

from solveur.core.analysis import AnalysisSettings
from solveur.core.assembler import GlobalAssembler
from solveur.core.dynamic_reduction import DynamicDofReducer
from solveur.core.model import FiniteElementModel
from solveur.io.manifest import discovered_file_entries, git_source_state, write_json_file
from solveur.verification.external_correlation import compare_pinched_cylinder

PROJECT_ROOT = project_root()


class Mitc4ValidationCampaign:
    """Generate reviewable MITC4 static, modal and Newmark evidence."""

    def __init__(self, output: str | Path, *, quick: bool = False) -> None:
        self.output = Path(output)
        self.quick = quick

    def run(self) -> dict[str, Any]:
        self.output.mkdir(parents=True, exist_ok=True)
        mechanical = MechanicalVerifier().run(include_benchmark=not self.quick)
        locking = self._locking_study()
        structural_runs = Mitc4StructuralConvergence().run(quick=self.quick)
        structural = {name: run.to_dict() for name, run in structural_runs.items()}
        structural_review = _structural_review(structural)
        external_correlation = _external_static_correlation(structural)
        drilling = Mitc4StructuralConvergence.drilling_sensitivity()
        modal_model, quads = _plate_model(
            {
                "type": "modal",
                "method": "eigsh",
                "modes": 4,
                "arpack_tolerance": 1.0e-12,
                "arpack_maxiter": 5000,
            }
        )
        modal = _solve_model(modal_model)
        free_free = _free_free_summary()
        dynamic, dynamic_error = self._newmark_study(modal_model, modal, damped=False)
        damped, _ = self._newmark_study(modal_model, modal, damped=True)
        time_convergence = []
        for steps_per_period in (20, 40, 80, 160):
            result, error = self._newmark_study(
                modal_model,
                modal,
                damped=False,
                steps_per_period=steps_per_period,
                periods=1,
            )
            time_convergence.append(
                {
                    "steps_per_period": steps_per_period,
                    "time_step": result.solver["time_step"],
                    "period_return_error": error,
                    "maximum_energy_drift": max(
                        abs(float(row["relative_energy_drift"])) for row in result.solver["time_history"]
                    ),
                }
            )

        summary = {
            "campaign": "MITC4-LINEAR-V1",
            "profile": "engineering",
            "quick": self.quick,
            "source": git_source_state(PROJECT_ROOT),
            "static": {
                "status": "PASS" if all(result.passed for result in mechanical) else "FAIL",
                "checks": [
                    {
                        "name": result.name,
                        "value": float(result.value),
                        "limit": float(result.limit),
                        "passed": bool(result.passed),
                        "details": result.details,
                    }
                    for result in mechanical
                ],
            },
            "shear_locking": locking.to_dict(),
            "structural_convergence": structural,
            "structural_review": structural_review,
            "drilling_sensitivity": drilling,
            "modal": _modal_summary(modal),
            "free_free": free_free,
            "newmark": _dynamic_summary(dynamic, displacement_error=dynamic_error),
            "newmark_time_step_convergence": time_convergence,
            "damped_newmark": _dynamic_summary(damped),
            "abaqus_correlation": external_correlation,
            "review": _review_metadata(),
        }
        base_pass = all(
            (
                summary["static"]["status"] == "PASS",
                locking.status == "PASS",
                self.quick or all(run["status"] == "PASS" for run in structural.values()),
                drilling["status"] == "PASS",
                summary["modal"]["status"] == "PASS",
                summary["free_free"]["status"] == "PASS",
                summary["newmark"]["status"] == "PASS",
                summary["newmark_time_step_convergence"][-1]["period_return_error"] <= 0.02,
                summary["damped_newmark"]["status"] == "PASS",
            )
        )
        summary["status"] = (
            "FAIL"
            if not base_pass
            else "PASS_INTERNAL_WITH_WARNING"
            if structural_review["status"] == "WARNING"
            else "PASS_INTERNAL"
        )
        write_json_file(self.output / "campaign_summary.json", summary)
        self._write_reports(summary)
        _plot_locking(locking, self.output / "VNV-MITC4-SHEAR-LOCKING-001.png")
        for run in structural_runs.values():
            _plot_convergence(run, self.output / f"{run.identifier}.png")
        pinched_correlation = external_correlation.get("pinched_cylinder")
        if isinstance(pinched_correlation, dict) and pinched_correlation.get("status") in {"PASS", "FAIL"}:
            _plot_abaqus_comparison(
                pinched_correlation,
                self.output / "VNV-MITC4-PINCHED-001-ABAQUS.png",
            )
        _plot_mode(modal_model.nodes, quads, modal.modes[:, 0], modal.dofs, self.output / "VNV-MITC4-MODAL-001.png")
        _plot_history(dynamic, self.output / "VNV-MITC4-NEWMARK-001.png")
        _plot_history(damped, self.output / "VNV-MITC4-DAMPED-001.png")
        manifest = {
            "schema_version": 1,
            "campaign": "MITC4-LINEAR-V1",
            "source": git_source_state(PROJECT_ROOT),
            "files": discovered_file_entries(
                self.output,
                lambda relative: "mitc4_vnv_artifact",
                exclude_names=("vnv_manifest.json",),
            ),
        }
        write_json_file(self.output / "vnv_manifest.json", manifest)
        return summary

    def _locking_study(self) -> LockingCampaign:
        if not self.quick:
            return EnhancedShearLockingStudy().run()
        return EnhancedShearLockingStudy(
            meshes=((4, 1), (8, 2)),
            thickness_ratios=(1.0e-3, 1.0e-4),
            distortions=(0.0, 0.3),
        ).run()

    @staticmethod
    def _newmark_study(
        model: FiniteElementModel,
        modal: object,
        *,
        damped: bool,
        steps_per_period: int = 80,
        periods: int = 2,
    ) -> tuple[object, float]:
        frequency = float(modal.frequencies_hz[0])
        period = 1.0 / frequency
        mode = np.asarray(modal.modes[:, 0], dtype=float)
        mode *= 1.0e-4 / max(float(np.max(np.abs(mode))), 1.0e-30)
        initial = []
        for node, names in modal.dofs.node_dofs.items():
            for name in names:
                value = float(mode[modal.dofs.index(node, name)])
                if abs(value) > 1.0e-18:
                    initial.append({"node": node, "dof": name, "value": value})
        parameters: dict[str, object] = {
            "type": "transient_dynamic",
            "method": "newmark",
            "time_step": period / steps_per_period,
            "steps": periods * steps_per_period,
            "load_factors": [0.0],
            "initial_displacements": initial,
        }
        if damped:
            parameters["rayleigh_alpha"] = 2.0 * 0.02 * 2.0 * np.pi * frequency
        model.analysis = AnalysisSettings.from_raw(parameters)
        result = _solve_model(model)
        return result, float(np.linalg.norm(result.displacements - mode) / max(np.linalg.norm(mode), 1.0e-30))

    def _write_reports(self, summary: dict[str, Any]) -> None:
        static_checks = summary["static"]["checks"]
        rows = "\n".join(
            f"| {item['name']} | {item['value']:.6e} | {item['limit']:.6e} | "
            f"{'PASS' if item['passed'] else 'FAIL'} |"
            for item in static_checks
            if "locking" not in item["name"].lower() and "Scordelis" not in item["name"]
        )
        _write_report(
            self.output / "VNV-MITC4-PATCH-001.md",
            "VNV-MITC4-PATCH-001 - patchs elementaires",
            "| Controle | Valeur | Limite | Statut |\n| --- | ---: | ---: | --- |\n" + rows,
        )
        locking_rows = "\n".join(
            f"| {item['name']} | {item['value']:.6e} | {item['operator']} {item['limit']:.6e} | {item['status']} |"
            for item in summary["shear_locking"]["checks"]
        )
        _write_report(
            self.output / "VNV-MITC4-SHEAR-LOCKING-001.md",
            "VNV-MITC4-SHEAR-LOCKING-001",
            "| Critere | Valeur | Acceptation | Statut |\n| --- | ---: | --- | --- |\n"
            + locking_rows
            + "\n\n![Courbes de locking](VNV-MITC4-SHEAR-LOCKING-001.png)",
        )
        _write_report(
            self.output / "VNV-MITC4-MODAL-001.md",
            "VNV-MITC4-MODAL-001",
            _mapping_table(summary["modal"]) + "\n\n![Premier mode](VNV-MITC4-MODAL-001.png)",
        )
        _write_report(
            self.output / "VNV-MITC4-FREEFREE-001.md",
            "VNV-MITC4-FREEFREE-001",
            _mapping_table(summary["free_free"]),
        )
        _write_report(
            self.output / "VNV-MITC4-NEWMARK-001.md",
            "VNV-MITC4-NEWMARK-001",
            _mapping_table(summary["newmark"])
            + "\n\n## Convergence du pas\n\n"
            + _convergence_table(summary["newmark_time_step_convergence"])
            + "\n\n![Historique Newmark](VNV-MITC4-NEWMARK-001.png)",
        )
        _write_report(
            self.output / "VNV-MITC4-DAMPED-001.md",
            "VNV-MITC4-DAMPED-001",
            _mapping_table(summary["damped_newmark"]) + "\n\n![Historique amorti](VNV-MITC4-DAMPED-001.png)",
        )
        _write_report(
            self.output / "VNV-MITC4-DRILLING-001.md",
            "VNV-MITC4-DRILLING-001",
            _drilling_table(summary["drilling_sensitivity"]),
        )
        for name, identifier in (
            ("cook", "VNV-MITC4-COOK-001"),
            ("scordelis", "VNV-MITC4-SCORDELIS-001"),
            ("pinched", "VNV-MITC4-PINCHED-001"),
        ):
            run = summary["structural_convergence"].get(name)
            if run is None:
                body = "Etude reservee a la campagne complete; correlation Abaqus S4R en attente."
            else:
                body = _structural_table(run) + f"\n\n![Convergence]({identifier}.png)"
                if name == "pinched":
                    correlation = summary["abaqus_correlation"]["pinched_cylinder"]
                    body += (
                        "\n\n## Correlation externe Abaqus S4R\n\n"
                        + _abaqus_correlation_table(correlation)
                        + "\n\n![Comparaison Abaqus S4R]"
                        "(VNV-MITC4-PINCHED-001-ABAQUS.png)"
                    )
                if name == "cook":
                    body += "\n\n## Revue de convergence\n\n" + _structural_review_note(run)
            _write_report(self.output / f"{identifier}.md", identifier, body)
        for identifier, statement in (
            ("VNV-MITC4-LOADS-001", "Charges coherentes protegees par les tests de resultante et moment."),
            ("VNV-MITC4-STRESS-001", "Faces superieure/inferieure protegees par les tests de post-traitement."),
        ):
            _write_report(self.output / f"{identifier}.md", identifier, statement)


def _plate_model(analysis: dict[str, object], nx: int = 8, ny: int = 2) -> tuple[FiniteElementModel, np.ndarray]:
    mesh = MeshFactory.rectangular_plate(nx, ny, 1.0, 0.2)
    root = np.where(np.isclose(mesh.nodes[:, 0], 0.0))[0]
    model = FiniteElementModel.from_raw(
        analysis=analysis,
        nodes=mesh.nodes.tolist(),
        elements=[{"type": "MITC4", "nodes": quad.tolist(), "material": "skin"} for quad in mesh.quads],
        materials={
            "skin": {
                "type": "shell_isotropic",
                "E": 70.0e9,
                "nu": 0.3,
                "t": 0.01,
                "density": 2700.0,
                "drilling_scale": 1.0e-4,
            }
        },
        fixed_dofs=[
            {"node": int(node), "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]} for node in root
        ],
    )
    return model, mesh.quads


def _modal_summary(result: object) -> dict[str, object]:
    solver = result.solver
    status = "PASS" if solver["max_relative_residual"] <= 1.0e-8 and solver["mass_orthogonality_error"] <= 1.0e-8 else "FAIL"
    return {
        "status": status,
        "frequencies_hz": [float(value) for value in result.frequencies_hz],
        "max_relative_residual": float(solver["max_relative_residual"]),
        "mass_orthogonality_error": float(solver["mass_orthogonality_error"]),
        "stiffness_diagonal_error": float(solver["stiffness_diagonal_error"]),
        "condensed_drilling_dofs": solver["dynamic_reduction"]["condensed_drilling_dof_count"],
        "abaqus_correlation": "PENDING",
    }


def _free_free_summary() -> dict[str, object]:
    model, _ = _plate_model({"type": "modal", "method": "eigh", "modes": 12}, nx=2, ny=1)
    model.fixed_dofs = []
    dofs = model.dof_manager()
    assembler = GlobalAssembler()
    stiffness = assembler.assemble_stiffness(model, dofs)
    mass = assembler.assemble_mass(model, dofs)
    reducer = DynamicDofReducer.from_system(model, dofs, mass, stiffness, np.array([], dtype=int))
    eigenvalues = eigh(reducer.stiffness.toarray(), reducer.mass.toarray(), eigvals_only=True)
    threshold = max(float(np.max(np.abs(eigenvalues))) * 1.0e-10, 1.0e-10)
    rigid_count = int(np.count_nonzero(np.abs(eigenvalues) <= threshold))
    return {
        "status": "PASS" if rigid_count == 6 else "FAIL",
        "rigid_mode_count": rigid_count,
        "relative_threshold": 1.0e-10,
        "absolute_threshold": threshold,
        "maximum_rigid_eigenvalue_magnitude": float(np.max(np.abs(eigenvalues[:rigid_count]))),
        "first_elastic_eigenvalue": float(eigenvalues[rigid_count]),
        "condensed_drilling_dofs": reducer.diagnostics["condensed_drilling_dof_count"],
    }


def _dynamic_summary(result: object, *, displacement_error: float | None = None) -> dict[str, object]:
    history = result.solver["time_history"]
    maximum_drift = max(abs(float(row["relative_energy_drift"])) for row in history)
    maximum_residual = max(float(row["dynamic_residual_norm"]) for row in history)
    damped = float(result.solver["rayleigh_alpha"]) > 0.0
    energy_decrease = float(history[-1]["total_energy"] / history[0]["total_energy"])
    displacement_ok = displacement_error is None or displacement_error <= 0.02
    status = (
        "PASS"
        if maximum_residual <= 1.0e-7
        and displacement_ok
        and (energy_decrease < 1.0 if damped else maximum_drift <= 1.0e-4)
        else "FAIL"
    )
    return {
        "status": status,
        "time_step": result.solver["time_step"],
        "step_count": result.solver["step_count"],
        "maximum_relative_energy_drift": maximum_drift,
        "maximum_dynamic_residual_norm": maximum_residual,
        "final_to_initial_energy_ratio": energy_decrease,
        "rayleigh_alpha": result.solver["rayleigh_alpha"],
        "rayleigh_beta": result.solver["rayleigh_beta"],
        "period_return_error": displacement_error,
        "abaqus_correlation": "PENDING",
    }


def _plot_locking(campaign: LockingCampaign, path: Path) -> None:
    finest = max(case.nx for case in campaign.cases)
    figure, axis = plt.subplots(figsize=(7.0, 4.2))
    for element, style in (("MITC4", "o-"), ("Q4-full-shear", "s--")):
        selected = sorted(
            (
                case
                for case in campaign.cases
                if case.element == element and case.nx == finest and np.isclose(case.distortion, 0.0)
            ),
            key=lambda case: case.thickness_ratio,
        )
        axis.loglog([case.thickness_ratio for case in selected], [case.displacement_ratio for case in selected], style, label=element)
    axis.axhline(1.0, color="black", linewidth=0.8, label="Timoshenko")
    axis.set_xlabel("t/L")
    axis.set_ylabel("w FE / w reference")
    axis.grid(True, which="both", alpha=0.25)
    axis.legend()
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)


def _plot_mode(nodes: np.ndarray, quads: np.ndarray, mode: np.ndarray, dofs: object, path: Path) -> None:
    translated = np.array(
        [[mode[dofs.index(node, name)] for name in ("UX", "UY", "UZ")] for node in range(nodes.shape[0])]
    )
    scale = 0.15 / max(float(np.max(np.linalg.norm(translated, axis=1))), 1.0e-30)
    deformed = nodes + scale * translated
    figure = plt.figure(figsize=(7.0, 4.2))
    axis = figure.add_subplot(111, projection="3d")
    for quad in quads:
        closed = np.append(quad, quad[0])
        axis.plot(*nodes[closed].T, color="#8d99ae", linewidth=0.7)
        axis.plot(*deformed[closed].T, color="#006d77", linewidth=1.1)
    axis.set_title(f"Premier mode, facteur d'echelle {scale:.3e}")
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)


def _plot_history(result: object, path: Path) -> None:
    history = result.solver["time_history"]
    times = [row["time"] for row in history]
    initial = max(float(history[0]["total_energy"]), 1.0e-30)
    figure, axis = plt.subplots(figsize=(7.0, 4.2))
    axis.plot(times, [row["total_energy"] / initial for row in history], label="energie normalisee")
    axis.set_xlabel("temps (s)")
    axis.set_ylabel("E / E0")
    axis.grid(True, alpha=0.25)
    axis.legend()
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)


def _plot_convergence(run: object, path: Path) -> None:
    elements = [point.element_count for point in run.points]
    errors = [point.relative_error for point in run.points]
    figure, axis = plt.subplots(figsize=(7.0, 4.2))
    axis.loglog(elements, errors, "o-", color="#006d77", label="erreur relative")
    axis.axhline(run.error_limit, color="#ae2012", linestyle="--", label="limite")
    axis.set_xlabel("nombre d'elements")
    axis.set_ylabel("erreur relative")
    axis.grid(True, which="both", alpha=0.25)
    axis.legend()
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)


def _plot_abaqus_comparison(comparison: dict[str, object], path: Path) -> None:
    reference = float(comparison["reference_displacement"])
    qf = comparison["qf_solver"]
    abaqus = comparison["abaqus_s4r"]
    values = [float(qf["displacement"]) / reference, float(abaqus["displacement"]) / reference, 1.0]
    labels = ["QF_solver\nmaillage fin", "Abaqus S4R\n20x20 publie", "Lindberg\nreference"]
    figure, axis = plt.subplots(figsize=(7.0, 4.2))
    bars = axis.bar(labels, values, color=("#006d77", "#ca6702", "#6c757d"))
    axis.axhline(1.0, color="black", linewidth=0.8)
    axis.set_ylabel("deplacement / reference de Lindberg")
    axis.set_ylim(0.0, 1.1)
    axis.grid(True, axis="y", alpha=0.25)
    for bar, value in zip(bars, values, strict=True):
        axis.text(bar.get_x() + bar.get_width() / 2.0, value + 0.02, f"{value:.3f}", ha="center")
    axis.set_title("Comparaison de reponses convergentes; maillages non identiques")
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)


def _mapping_table(data: dict[str, object]) -> str:
    rows = "\n".join(f"| `{key}` | `{value}` |" for key, value in data.items())
    return "| Grandeur | Valeur |\n| --- | --- |\n" + rows


def _convergence_table(rows: list[dict[str, object]]) -> str:
    body = "\n".join(
        f"| {row['steps_per_period']} | {row['time_step']:.6e} | "
        f"{row['period_return_error']:.6e} | {row['maximum_energy_drift']:.6e} |"
        for row in rows
    )
    return (
        "| Pas/periode | Delta t | Erreur retour periode | Derive energie |\n"
        "| ---: | ---: | ---: | ---: |\n" + body
    )


def _structural_table(run: dict[str, object]) -> str:
    body = "\n".join(
        f"| {point['mesh'][0]}x{point['mesh'][1]} | {point['element_count']} | "
        f"{point['value']:.6e} | {point['reference']:.6e} | {point['relative_error']:.6e} |"
        for point in run["points"]
    )
    return (
        f"Statut: **{run['status']}**, limite finale: `{run['error_limit']}`.\n\n"
        f"Increment final: `{run['final_increment']:.6e}`; erreur minimale observee: "
        f"`{run['minimum_reference_error']:.6e}`; revue: **{run['review_status']}**.\n\n"
        "| Maillage | Elements | Valeur | Reference | Erreur relative |\n"
        "| --- | ---: | ---: | ---: | ---: |\n" + body
    )


def _drilling_table(run: dict[str, object]) -> str:
    body = "\n".join(
        f"| {point['drilling_scale']:.1e} | {point['tip_displacement']:.6e} | "
        f"{point['relative_change']:.6e} |"
        for point in run["points"]
    )
    return (
        f"Statut: **{run['status']}**, echelle retenue: `{run['selected_scale']}`.\n\n"
        "| drilling_scale | Deplacement Cook | Variation relative |\n"
        "| ---: | ---: | ---: |\n" + body
    )


def _external_static_correlation(structural: dict[str, dict[str, object]]) -> dict[str, object]:
    pinched = structural.get("pinched")
    if pinched is None:
        pinched_result: dict[str, object] = {
            "status": "NOT_RUN",
            "reason": "The quick campaign does not execute structural convergence studies.",
        }
    else:
        pinched_result = compare_pinched_cylinder(pinched)
    return {
        "status": "PARTIAL_PASS" if pinched_result["status"] == "PASS" else "PENDING",
        "provenance": "published_vendor_result_not_locally_executed",
        "pinched_cylinder": pinched_result,
        "cook": {
            "status": "NOT_APPLICABLE",
            "reason": "The official Abaqus Cook example is nonlinear hyperelastic and is not the linear shell case used here.",
        },
        "scordelis_lo": {
            "status": "REFERENCE_ONLY",
            "reason": "No official numeric Abaqus S4R table with matching mesh was identified.",
        },
        "final_same_mesh_correlation": "PENDING",
    }


def _structural_review(structural: dict[str, dict[str, object]]) -> dict[str, object]:
    warnings = [
        {
            "study": run["study_id"],
            "minimum_reference_error": run["minimum_reference_error"],
            "final_reference_error": run["points"][-1]["relative_error"],
            "recommendation": run["recommendation"],
        }
        for run in structural.values()
        if run["review_status"] == "WARNING"
    ]
    return {
        "status": "WARNING" if warnings else "PASS" if structural else "NOT_RUN",
        "findings": warnings,
    }


def _structural_review_note(run: dict[str, object]) -> str:
    return (
        f"Statut de revue: **{run['review_status']}**.\n\n"
        f"{run['recommendation']}\n\n"
        f"L'erreur minimale est `{run['minimum_reference_error']:.2%}` et l'erreur `64x64` "
        f"est `{run['points'][-1]['relative_error']:.2%}`. L'increment entre les deux "
        f"derniers maillages est `{run['final_increment']:.2%}`."
    )


def _review_metadata() -> dict[str, object]:
    path = PROJECT_ROOT / "qualification" / "vnv" / "mitc4_validation_scope.json"
    try:
        source = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"reviewer": "unknown", "mode": "unknown", "decision": "pending"}
    return {
        "reviewer": source.get("owner", "unknown"),
        "mode": source.get("review_mode", "unknown"),
        "decision": source.get("decision", "pending"),
        "decision_date": source.get("decision_date"),
        "use_class": source.get("use_class"),
        "internal_validation_status": source.get("internal_validation_status", "pending"),
        "review_record": source.get("review_record"),
    }


def _abaqus_correlation_table(correlation: dict[str, object]) -> str:
    qf = correlation["qf_solver"]
    abaqus = correlation["abaqus_s4r"]
    source = correlation["source"]
    limitations = "\n".join(f"- {item}" for item in correlation["limitations"])
    return (
        f"Statut: **{correlation['status']}**. Ecart QF_solver/Abaqus: "
        f"`{100.0 * float(correlation['relative_difference']):.2f} %` "
        f"(limite `{100.0 * float(correlation['relative_difference_limit']):.1f} %`).\n\n"
        "| Origine | Maillage | Valeur absolue |\n"
        "| --- | --- | ---: |\n"
        f"| QF_solver | {qf['mesh'][0]}x{qf['mesh'][1]} ({qf['element_count']} elements) | "
        f"{float(qf['displacement']):.6e} |\n"
        f"| Abaqus/Standard S4R | {abaqus['mesh']} ({abaqus['dofs']} ddl publies) | "
        f"{float(abaqus['displacement']):.6e} |\n"
        f"| Lindberg/Flugge | solution de reference | {float(correlation['reference_displacement']):.6e} |\n\n"
        f"Source officielle: [{source['title']}]({source['url']}).\n\n"
        "Cette comparaison est une preuve externe de support, pas une execution Abaqus locale:\n\n"
        + limitations
    )
def _write_report(path: Path, title: str, body: str) -> None:
    path.write_text(
        f"# {title}\n\nStatut documentaire: preuve interne; le statut de correlation externe est detaille dans le rapport.\n\n{body}\n",
        encoding="utf-8",
    )


def _solve_model(model: FiniteElementModel) -> object:
    """Resolve through the stable API without creating an import cycle."""
    from solveur.api.public import solve_model

    return solve_model(model)
