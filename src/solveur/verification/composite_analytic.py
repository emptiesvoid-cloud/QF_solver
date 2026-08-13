"""Controlled analytical verification of linear laminate mechanics and criteria."""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, radians, sin
from pathlib import Path

import numpy as np

from solveur.io.manifest import write_json_file
from solveur.materials.composite import OrthotropicLamina
from solveur.materials.failure import CompositeFailureEvaluator, PlyStrengths
from solveur.materials.laminate import ClassicalLaminate, LaminaPly
from solveur.verification.vnv_manifest import write_vnv_manifest


@dataclass(frozen=True)
class CompositeReferenceData:
    E1: float = 135.0e9
    E2: float = 10.0e9
    nu12: float = 0.3
    G12: float = 5.0e9
    ply_thickness: float = 0.125e-3


class CompositeAnalyticalCampaign:
    """Check CLT and first-ply criteria against independent closed forms."""

    study_id = "VNV-COMP-ANALYTIC-001"

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir).resolve()
        self.data = CompositeReferenceData()
        self.material = OrthotropicLamina(
            self.data.E1,
            self.data.E2,
            self.data.nu12,
            self.data.G12,
            density=1600.0,
            G13=4.5e9,
            G23=3.8e9,
        )
        self.strengths = PlyStrengths(1500.0e6, 1200.0e6, 50.0e6, 200.0e6, 75.0e6)

    def run(self) -> dict[str, object]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        cases = [
            self._single_ply_case(),
            self._symmetric_cross_ply_case(),
            self._balanced_angle_ply_case(),
            self._off_axis_traction_case(),
            self._pure_bending_case(),
            self._failure_boundary_case(),
        ]
        checks = [
            _upper("single_ply_closed_form", float(cases[0]["maximum_relative_error"]), 1.0e-12),
            _upper("symmetric_laminate_B", float(cases[1]["relative_B_norm"]), 1.0e-12),
            _upper("balanced_laminate_A16_A26", float(cases[2]["relative_coupling_norm"]), 1.0e-12),
            _upper("off_axis_material_stress", float(cases[3]["relative_stress_error"]), 1.0e-12),
            _upper("pure_bending_decoupling", float(cases[4]["maximum_relative_error"]), 1.0e-12),
            _upper("failure_surface_axis_intercepts", float(cases[5]["maximum_index_error"]), 1.0e-12),
        ]
        passed = all(check["status"] == "PASS" for check in checks)
        summary: dict[str, object] = {
            "study_id": self.study_id,
            "status": "PASS_TECHNICAL_VERIFICATION" if passed else "FAIL",
            "maturity": "experimental",
            "purpose": "Analytical verification of CLT and non-degrading first-ply indicators",
            "cases": cases,
            "checks": checks,
            "scope_limit": (
                "Linear elastic plane-stress plies. Failure indices are indicators only; "
                "no stiffness degradation, damage, delamination or progressive failure."
            ),
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._plot_failure_envelopes()
        self._write_report(summary)
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary

    def _single_ply_case(self) -> dict[str, object]:
        thickness = self.data.ply_thickness
        laminate = self._laminate([0.0])
        q = _closed_reduced_stiffness(self.data)
        errors = (
            _relative_error(laminate.extensional_matrix, q * thickness),
            _relative_error(laminate.coupling_matrix, np.zeros((3, 3))),
            _relative_error(laminate.bending_matrix, q * thickness**3 / 12.0),
        )
        return {
            "id": "COMP-CLT-0-PLY",
            "layup": "[0]",
            "maximum_relative_error": max(errors),
            "A_error": errors[0],
            "B_absolute_norm": float(np.linalg.norm(laminate.coupling_matrix)),
            "D_error": errors[2],
        }

    def _symmetric_cross_ply_case(self) -> dict[str, object]:
        laminate = self._laminate([0.0, 90.0, 90.0, 0.0])
        scale = max(float(np.linalg.norm(laminate.extensional_matrix) * laminate.thickness), 1.0)
        return {
            "id": "COMP-CLT-CROSS-PLY",
            "layup": "[0/90]s",
            "relative_B_norm": float(np.linalg.norm(laminate.coupling_matrix) / scale),
            "is_symmetric": laminate.is_symmetric(),
        }

    def _balanced_angle_ply_case(self) -> dict[str, object]:
        laminate = self._laminate([45.0, -45.0, -45.0, 45.0])
        matrix = laminate.extensional_matrix
        coupling = np.array([matrix[0, 2], matrix[1, 2]])
        return {
            "id": "COMP-CLT-ANGLE-PLY",
            "layup": "[+45/-45]s",
            "relative_coupling_norm": float(np.linalg.norm(coupling) / np.linalg.norm(matrix)),
            "is_balanced": laminate.is_balanced(),
        }

    def _off_axis_traction_case(self) -> dict[str, object]:
        angle = 30.0
        membrane_force = np.array([80.0e3, 0.0, 0.0])
        laminate = self._laminate([angle])
        strain, curvature = laminate.generalized_strains(membrane_force, np.zeros(3))
        point = laminate.ply_results(strain, curvature)[1]
        sigma_x = membrane_force[0] / laminate.thickness
        theta = radians(angle)
        m, n = cos(theta), sin(theta)
        expected = np.array([m * m * sigma_x, n * n * sigma_x, -m * n * sigma_x])
        return {
            "id": "COMP-OFF-AXIS-TRACTION",
            "layup": "[30]",
            "relative_stress_error": _relative_error(point.stress_material, expected),
            "material_stress": point.stress_material.tolist(),
            "closed_form_stress": expected.tolist(),
        }

    def _pure_bending_case(self) -> dict[str, object]:
        laminate = self._laminate([0.0, 90.0, 90.0, 0.0])
        moment = np.array([120.0, 0.0, 0.0])
        strain, curvature = laminate.generalized_strains(np.zeros(3), moment)
        expected_curvature = np.linalg.solve(laminate.bending_matrix, moment)
        recovered_force, recovered_moment = laminate.resultants(strain, curvature)
        errors = (
            float(np.linalg.norm(strain)),
            _relative_error(curvature, expected_curvature),
            float(np.linalg.norm(recovered_force) / max(np.linalg.norm(moment), 1.0)),
            _relative_error(recovered_moment, moment),
        )
        return {
            "id": "COMP-SYMMETRIC-BENDING",
            "layup": "[0/90]s",
            "maximum_relative_error": max(errors),
            "midplane_strain_norm": errors[0],
            "curvature": curvature.tolist(),
        }

    def _failure_boundary_case(self) -> dict[str, object]:
        states = {
            "Xt": np.array([self.strengths.Xt, 0.0, 0.0]),
            "Xc": np.array([-self.strengths.Xc, 0.0, 0.0]),
            "Yt": np.array([0.0, self.strengths.Yt, 0.0]),
            "Yc": np.array([0.0, -self.strengths.Yc, 0.0]),
            "S12+": np.array([0.0, 0.0, self.strengths.S12]),
            "S12-": np.array([0.0, 0.0, -self.strengths.S12]),
        }
        rows = []
        errors = []
        for name, stress in states.items():
            results = (
                CompositeFailureEvaluator.maximum_stress(stress, self.strengths),
                CompositeFailureEvaluator.tsai_hill(stress, self.strengths),
                CompositeFailureEvaluator.tsai_wu(stress, self.strengths),
            )
            indices = {result.criterion: result.index for result in results}
            errors.extend(abs(value - 1.0) for value in indices.values())
            rows.append({"state": name, "stress": stress.tolist(), "indices": indices})
        return {
            "id": "COMP-FAILURE-INTERCEPTS",
            "maximum_index_error": max(errors),
            "states": rows,
        }

    def _laminate(self, angles: list[float]) -> ClassicalLaminate:
        return ClassicalLaminate(
            tuple(
                LaminaPly(
                    self.material,
                    self.data.ply_thickness,
                    angle,
                    name=f"ply-{index + 1}",
                    strengths=self.strengths,
                )
                for index, angle in enumerate(angles)
            )
        )

    def _plot_failure_envelopes(self) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        angles = np.linspace(0.0, 2.0 * np.pi, 721)
        scale1 = 0.5 * (self.strengths.Xt + self.strengths.Xc)
        scale2 = 0.5 * (self.strengths.Yt + self.strengths.Yc)
        hill_points: list[np.ndarray] = []
        wu_points: list[np.ndarray] = []
        for angle in angles:
            direction = np.array([scale1 * np.cos(angle), scale2 * np.sin(angle), 0.0])
            hill_reserve = CompositeFailureEvaluator.tsai_hill(direction, self.strengths).reserve_factor
            wu_reserve = CompositeFailureEvaluator.tsai_wu(direction, self.strengths).reserve_factor
            if hill_reserve is not None:
                hill_points.append(direction[:2] * hill_reserve / 1.0e6)
            if wu_reserve is not None:
                wu_points.append(direction[:2] * wu_reserve / 1.0e6)
        hill_curve = np.asarray(hill_points)
        wu_curve = np.asarray(wu_points)
        figure, axis = plt.subplots(figsize=(7.8, 5.2))
        axis.plot(hill_curve[:, 0], hill_curve[:, 1], color="#3a6ea5", label="Tsai-Hill")
        axis.plot(wu_curve[:, 0], wu_curve[:, 1], color="#bc4749", label="Tsai-Wu")
        axis.axhline(0.0, color="#777777", linewidth=0.7)
        axis.axvline(0.0, color="#777777", linewidth=0.7)
        axis.set(xlabel="Contrainte sigma1 [MPa]", ylabel="Contrainte sigma2 [MPa]")
        axis.grid(True, alpha=0.2)
        axis.legend()
        figure.tight_layout()
        figure.savefig(self.output_dir / "composite_failure_envelopes.png", dpi=180)
        plt.close(figure)

    def _write_report(self, summary: dict[str, object]) -> None:
        lines = [
            f"# {self.study_id}",
            "",
            f"Statut automatise : **{summary['status']}**",
            "",
            "Cette campagne confronte la theorie classique des stratifies et les criteres",
            "de premier pli a des expressions analytiques calculees independamment.",
            "",
            "| Cas | Mesure principale | Valeur |",
            "| --- | --- | ---: |",
        ]
        labels = (
            ("[0]", "erreur A/B/D", "maximum_relative_error"),
            ("[0/90]s", "norme relative B", "relative_B_norm"),
            ("[+45/-45]s", "couplage relatif A16/A26", "relative_coupling_norm"),
            ("traction [30]", "erreur contrainte materiau", "relative_stress_error"),
            ("flexion [0/90]s", "erreur decouplage/resultantes", "maximum_relative_error"),
            ("intercepts de rupture", "erreur indice unitaire", "maximum_index_error"),
        )
        for case, (label, measure, key) in zip(summary["cases"], labels, strict=True):
            lines.append(f"| {label} | {measure} | {float(case[key]):.3e} |")
        lines.extend(
            [
                "",
                "Les indices sont des indicateurs sans degradation de rigidite. Une valeur",
                "superieure a 1 ne simule ni propagation, ni delaminage, ni rupture progressive.",
                "",
                "![Enveloppes de rupture](composite_failure_envelopes.png)",
                "",
            ]
        )
        (self.output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def _closed_reduced_stiffness(data: CompositeReferenceData) -> np.ndarray:
    nu21 = data.nu12 * data.E2 / data.E1
    denominator = 1.0 - data.nu12 * nu21
    return np.array(
        [
            [data.E1 / denominator, data.nu12 * data.E2 / denominator, 0.0],
            [data.nu12 * data.E2 / denominator, data.E2 / denominator, 0.0],
            [0.0, 0.0, data.G12],
        ]
    )


def _relative_error(value: np.ndarray, reference: np.ndarray) -> float:
    scale = max(float(np.linalg.norm(reference)), 1.0)
    return float(np.linalg.norm(np.asarray(value) - np.asarray(reference)) / scale)


def _upper(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if value <= limit else "FAIL"}
