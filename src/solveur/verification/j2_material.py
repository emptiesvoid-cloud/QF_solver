"""Auditable material-point verification campaign for the small-strain J2 law."""

from __future__ import annotations

from solveur.paths import project_root

import copy
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from solveur.materials.solid import VonMisesElastoplasticMaterial


@dataclass(frozen=True)
class J2VerificationCheck:
    """One measured acceptance criterion from the J2 campaign."""

    name: str
    value: float
    limit: float
    status: str
    criterion: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class J2MaterialVerificationCampaign:
    """Verify consistency and path-dependent invariants of the radial return."""

    campaign_id = "VNV-J2-MATERIAL-CYCLIC-001"

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir)

    def run(self) -> dict[str, object]:
        tangent_checks = self._tangent_checks()
        hardening_path, hardening_checks = self._cyclic_path(hardening=1000.0)
        perfect_path, perfect_checks = self._perfect_plasticity_path()
        non_proportional_path, non_proportional_checks = self._non_proportional_path()
        theory_path, theory_checks = self._bilinear_uniaxial_path()
        abaqus_correlation, abaqus_checks = self._abaqus_published_correlation()
        checks = tangent_checks + hardening_checks + perfect_checks + non_proportional_checks + theory_checks + abaqus_checks
        status = "PASS_INTERNAL" if all(check.status == "PASS" for check in checks) else "FAIL"
        summary: dict[str, object] = {
            "campaign_id": self.campaign_id,
            "status": status,
            "maturity": "experimental",
            "scope": "small_strain_j2_material_point",
            "formulation": "associative von Mises plasticity, radial return, isotropic hardening",
            "checks": [check.to_dict() for check in checks],
            "paths": {
                "isotropic_hardening_cycle": hardening_path,
                "perfect_plasticity": perfect_path,
                "non_proportional_cycle": non_proportional_path,
                "uniaxial_bilinear": theory_path,
            },
            "external_correlations": {"abaqus_published": abaqus_correlation},
            "limitations": [
                "Material-point evidence only; structural convergence is a separate P5.1 activity.",
                "Small strains and isotropic hardening only.",
                "No independent external review has been recorded.",
            ],
        }
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "results.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (self.output_dir / "report.md").write_text(self._markdown(summary), encoding="utf-8")
        self._plot_uniaxial(summary)
        return summary

    @staticmethod
    def _tangent_checks() -> list[J2VerificationCheck]:
        cases = [
            ("elastic uniaxial", 1000.0, np.array([1.0e-4, 0.0, 0.0, 0.0, 0.0, 0.0]), None),
            ("plastic uniaxial", 1000.0, np.array([5.0e-3, 0.0, 0.0, 0.0, 0.0, 0.0]), None),
            ("plastic multiaxial", 1000.0, np.array([3.0e-3, -1.0e-3, 0.0, 4.0e-3, 0.0, 2.0e-3]), None),
            ("perfect plasticity", 0.0, np.array([5.0e-3, 0.0, 0.0, 3.0e-3, 0.0, 0.0]), None),
        ]
        material_for_state = VonMisesElastoplasticMaterial(
            E=210000.0, nu=0.3, yield_stress=250.0, hardening_modulus=1000.0
        )
        _, _, committed = material_for_state.stress_tangent_state(
            np.array([4.0e-3, 0.0, 0.0, 0.0, 0.0, 0.0]), material_for_state.initial_state()
        )
        cases.append(
            (
                "plastic from committed state",
                1000.0,
                np.array([8.0e-3, -1.0e-3, 0.0, 2.0e-3, 0.0, 0.0]),
                committed,
            )
        )
        checks = []
        for name, hardening, strain, previous in cases:
            material = VonMisesElastoplasticMaterial(
                E=210000.0, nu=0.3, yield_stress=250.0, hardening_modulus=hardening
            )
            state = previous if previous is not None else material.initial_state()
            _, tangent, _ = material.stress_tangent_state(strain, state)
            finite_difference = _finite_difference_tangent(material, strain, state)
            denominator = max(float(np.linalg.norm(finite_difference)), np.finfo(float).tiny)
            error = float(np.linalg.norm(tangent - finite_difference) / denominator)
            checks.append(_upper_check(f"consistent tangent - {name}", error, 1.0e-6, "relative Frobenius error"))
        return checks

    @staticmethod
    def _cyclic_path(hardening: float) -> tuple[list[dict[str, object]], list[J2VerificationCheck]]:
        material = VonMisesElastoplasticMaterial(
            E=210000.0, nu=0.3, yield_stress=250.0, hardening_modulus=hardening
        )
        yield_amplitude = material.yield_stress / (3.0 * material.shear_modulus)
        direction = np.array([1.0, -0.5, -0.5, 0.0, 0.0, 0.0])
        amplitudes = np.array([0.0, 0.5, 1.2, 2.0, 3.0, 2.8, 2.5, 3.0, 3.8]) * yield_amplitude
        rows, metrics = _run_path(material, [amplitude * direction for amplitude in amplitudes])
        checks = _path_invariant_checks("isotropic hardening cycle", metrics)
        unloading_indices = (5, 6)
        loaded_eqp = float(rows[4]["equivalent_plastic_strain"])
        unloading_drift = max(
            abs(float(rows[index]["equivalent_plastic_strain"]) - loaded_eqp) for index in unloading_indices
        )
        checks.append(_upper_check("elastic unloading preserves plastic strain", unloading_drift, 1.0e-14, "absolute eqp drift"))
        reload_growth = float(rows[-1]["equivalent_plastic_strain"]) - loaded_eqp
        checks.append(_lower_check("reloading resumes plastic flow", reload_growth, 1.0e-12, "positive eqp increment"))
        return rows, checks

    @staticmethod
    def _perfect_plasticity_path() -> tuple[list[dict[str, object]], list[J2VerificationCheck]]:
        material = VonMisesElastoplasticMaterial(E=210000.0, nu=0.3, yield_stress=250.0, hardening_modulus=0.0)
        yield_amplitude = material.yield_stress / (3.0 * material.shear_modulus)
        direction = np.array([1.0, -0.5, -0.5, 0.0, 0.0, 0.0])
        amplitudes = np.linspace(0.0, 4.0 * yield_amplitude, 13)
        rows, metrics = _run_path(material, [amplitude * direction for amplitude in amplitudes])
        checks = _path_invariant_checks("perfect plasticity", metrics)
        plastic_q = [float(row["equivalent_stress"]) for row in rows if not bool(row["elastic"])]
        plateau_error = max(abs(value - material.yield_stress) for value in plastic_q) / material.yield_stress
        checks.append(_upper_check("perfect plasticity yield plateau", plateau_error, 1.0e-12, "relative q error"))
        return rows, checks

    @staticmethod
    def _non_proportional_path() -> tuple[list[dict[str, object]], list[J2VerificationCheck]]:
        material = VonMisesElastoplasticMaterial(
            E=210000.0, nu=0.3, yield_stress=250.0, hardening_modulus=1000.0
        )
        amplitude = material.yield_stress / (3.0 * material.shear_modulus)
        d1 = np.array([1.0, -0.5, -0.5, 0.0, 0.0, 0.0])
        d2 = np.array([0.0, 0.0, 0.0, 1.5, 0.0, 0.0])
        strains = [
            np.zeros(6),
            2.0 * amplitude * d1,
            2.0 * amplitude * d1 + 2.0 * amplitude * d2,
            0.7 * amplitude * d1 + 2.8 * amplitude * d2,
            2.8 * amplitude * d1 + 1.2 * amplitude * d2,
        ]
        rows, metrics = _run_path(material, strains)
        checks = _path_invariant_checks("non-proportional cycle", metrics)
        checks.append(
            _lower_check(
                "non-proportional path activates plasticity",
                float(rows[-1]["equivalent_plastic_strain"]),
                1.0e-12,
                "final equivalent plastic strain",
            )
        )
        return rows, checks

    @staticmethod
    def _bilinear_uniaxial_path() -> tuple[list[dict[str, object]], list[J2VerificationCheck]]:
        material = VonMisesElastoplasticMaterial(
            E=210000.0, nu=0.3, yield_stress=250.0, hardening_modulus=1000.0
        )
        targets = np.linspace(0.0, 2.5 * material.yield_stress, 81)
        rows = solve_uniaxial_stress_path(material, targets)
        errors = []
        lateral_stress = []
        for row in rows:
            stress = float(row["axial_stress"])
            analytical_strain = stress / material.E
            if stress > material.yield_stress:
                analytical_strain += (stress - material.yield_stress) / material.hardening_modulus
            row["analytical_axial_strain"] = analytical_strain
            row["analytical_axial_plastic_strain"] = max(
                (stress - material.yield_stress) / material.hardening_modulus, 0.0
            )
            errors.append(abs(float(row["axial_strain"]) - analytical_strain))
            lateral_stress.append(abs(float(row["lateral_stress"])))
        scale = max(float(rows[-1]["analytical_axial_strain"]), np.finfo(float).tiny)
        checks = [
            _upper_check("uniaxial bilinear analytical strain", max(errors) / scale, 1.0e-10, "relative error"),
            _upper_check(
                "uniaxial stress boundary condition",
                max(lateral_stress) / material.yield_stress,
                1.0e-10,
                "relative lateral stress",
            ),
        ]
        return rows, checks

    @staticmethod
    def _abaqus_published_correlation() -> tuple[dict[str, object], list[J2VerificationCheck]]:
        reference_path = (
            project_root()
            / "qualification"
            / "vnv"
            / "references"
            / "abaqus_j2_uniaxial_2024.json"
        )
        reference = json.loads(reference_path.read_text(encoding="utf-8"))
        material_data = reference["material"]
        material = VonMisesElastoplasticMaterial(
            E=float(material_data["E_mpa"]),
            nu=float(material_data["nu"]),
            yield_stress=float(material_data["initial_yield_stress_mpa"]),
            hardening_modulus=float(material_data["linear_hardening_modulus_mpa"]),
        )
        points = reference["monotonic_comparison_points"]
        rows = solve_uniaxial_stress_path(material, np.asarray([point["stress_mpa"] for point in points]))
        absolute_errors = []
        comparison = []
        for point, row in zip(points, rows, strict=True):
            expected = float(point["exact_axial_plastic_strain"])
            observed = float(row["axial_plastic_strain"])
            absolute_errors.append(abs(observed - expected))
            comparison.append(
                {
                    "increment": int(point["increment"]),
                    "stress_mpa": float(point["stress_mpa"]),
                    "abaqus_exact_axial_plastic_strain": expected,
                    "qf_solver_axial_plastic_strain": observed,
                    "absolute_error": abs(observed - expected),
                }
            )
        correlation = {
            "reference_id": reference["reference_id"],
            "title": reference["title"],
            "source_url": reference["source_url"],
            "input_url": reference["input_url"],
            "execution_status": reference["execution_status"],
            "comparison_scope": "monotonic increments 1-4 only",
            "comparison": comparison,
            "excluded_points": reference["excluded_points"],
            "maximum_absolute_plastic_strain_error": max(absolute_errors),
        }
        checks = [
            _upper_check(
                "Abaqus published monotonic plastic strain",
                max(absolute_errors),
                5.0e-7,
                "absolute strain error, compatible with published rounding",
            )
        ]
        return correlation, checks

    def _plot_uniaxial(self, summary: dict[str, object]) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        path = summary["paths"]["uniaxial_bilinear"]
        abaqus = summary["external_correlations"]["abaqus_published"]["comparison"]
        strain = np.asarray([row["axial_strain"] for row in path], dtype=float)
        analytical = np.asarray([row["analytical_axial_strain"] for row in path], dtype=float)
        stress = np.asarray([row["axial_stress"] for row in path], dtype=float)
        figure, axes = plt.subplots(1, 2, figsize=(11.0, 4.4), constrained_layout=True)
        axes[0].plot(1.0e3 * analytical, stress, color="#c92a2a", linewidth=2.4, label="Theorie bilineaire")
        axes[0].plot(1.0e3 * strain, stress, "--", color="#0b7285", linewidth=1.8, label="QF_solver J2")
        axes[0].set(xlabel="Deformation axiale [1e-3]", ylabel="Contrainte axiale [MPa]", title="Traction monotone")
        axes[0].legend()
        axes[0].grid(alpha=0.25)
        abaqus_qf_plastic = [1.0e3 * row["qf_solver_axial_plastic_strain"] for row in abaqus]
        abaqus_stress = [row["stress_mpa"] for row in abaqus]
        axes[1].plot(
            abaqus_qf_plastic,
            abaqus_stress,
            color="#0b7285",
            linewidth=2.0,
            marker="o",
            markersize=4,
            label="QF_solver, parametres Abaqus",
        )
        axes[1].scatter(
            [1.0e3 * row["abaqus_exact_axial_plastic_strain"] for row in abaqus],
            abaqus_stress,
            color="#c92a2a",
            marker="x",
            s=55,
            label="Abaqus exact publie",
            zorder=3,
        )
        axes[1].set(
            xlabel="Deformation plastique axiale [1e-3]",
            ylabel="Contrainte axiale [MPa]",
            title="Correlation externe monotone",
        )
        axes[1].legend()
        axes[1].grid(alpha=0.25)
        figure.suptitle("VNV J2 - theorie analytique et reference Abaqus publiee")
        figure.savefig(self.output_dir / "uniaxial_comparison.png", dpi=180)
        plt.close(figure)

    @staticmethod
    def _markdown(summary: dict[str, object]) -> str:
        lines = [
            f"# {J2MaterialVerificationCampaign.campaign_id}",
            "",
            "## Verdict",
            "",
            f"- Statut : **{summary['status']}**",
            "- Maturite : `experimental`",
            "- Perimetre : loi J2 au point materiel, petites deformations",
            "- Revue independante : non realisee",
            "",
            "Le retour radial impose la condition q = sigma_y + H p apres chaque correction plastique. ",
            "La tangente algorithmique est comparee a une derivee numerique centree en conservant le meme etat commite.",
            "",
            "## Criteres mesures",
            "",
            "| Verification | Valeur | Limite | Statut |",
            "| --- | ---: | ---: | --- |",
        ]
        for check in summary["checks"]:
            lines.append(
                f"| {check['name']} | {float(check['value']):.6e} | {float(check['limit']):.6e} | {check['status']} |"
            )
        lines.extend(
            [
                "",
                "## Chemins verifies",
                "",
                "Les historiques numeriques complets sont stockes dans `results.json`. Ils comprennent la deformation, ",
                "la contrainte, la contrainte equivalente, la limite courante, la deformation plastique cumulee et la dissipation incrementale.",
                "",
                "## Correlation analytique et Abaqus",
                "",
                "La traction monotone est comparee a la loi bilineaire exacte. Les quatre premiers increments monotones du benchmark ",
                "Abaqus *Uniformly loaded, elastic-plastic plate* sont aussi compares a leurs deformations plastiques exactes publiees.",
                "",
                "![Comparaison uniaxiale](uniaxial_comparison.png)",
                "",
                "Les increments 5 a 10 du benchmark Abaqus ne sont pas compares : le fichier officiel emploie un ecrouissage cinematique, ",
                "alors que QF_solver implemente actuellement un ecrouissage isotrope. Abaqus n'a pas ete execute localement; son alias 2019 est casse.",
                "",
                "## Conclusion et limites",
                "",
                "Un verdict positif prouve la coherence locale de l'integration constitutive pour les chemins testes. ",
                "Il ne qualifie pas encore la convergence d'une structure non lineaire, la gestion des increments rejetes, ",
                "les grandes transformations ni une utilisation industrielle sans revue independante.",
                "",
            ]
        )
        return "\n".join(lines)


def _run_path(
    material: VonMisesElastoplasticMaterial,
    strains: list[np.ndarray],
) -> tuple[list[dict[str, object]], dict[str, float]]:
    state = material.initial_state()
    rows: list[dict[str, object]] = []
    minimum_dissipation = float("inf")
    maximum_yield_error = 0.0
    maximum_eqp_decrease = 0.0
    maximum_state_mutation = 0.0
    for index, strain in enumerate(strains):
        previous = copy.deepcopy(state)
        previous_plastic = np.asarray(previous.get("plastic_strain", [0.0] * 6), dtype=float)
        previous_eqp = float(previous.get("equivalent_plastic_strain", 0.0))
        stress, _, updated = material.stress_tangent_state(np.asarray(strain, dtype=float), state)
        maximum_state_mutation = max(maximum_state_mutation, _state_distance(state, previous))
        plastic = np.asarray(updated["plastic_strain"], dtype=float)
        dissipation = float(stress @ (plastic - previous_plastic))
        minimum_dissipation = min(minimum_dissipation, dissipation)
        eqp = float(updated["equivalent_plastic_strain"])
        maximum_eqp_decrease = max(maximum_eqp_decrease, previous_eqp - eqp)
        if not bool(updated["elastic"]):
            scale = max(abs(float(updated["yield_stress"])), np.finfo(float).tiny)
            maximum_yield_error = max(
                maximum_yield_error,
                abs(float(updated["equivalent_stress"]) - float(updated["yield_stress"])) / scale,
            )
        rows.append(
            {
                "step": index,
                "strain": np.asarray(strain, dtype=float).tolist(),
                "stress": np.asarray(stress, dtype=float).tolist(),
                "elastic": bool(updated["elastic"]),
                "equivalent_stress": float(updated["equivalent_stress"]),
                "yield_stress": float(updated["yield_stress"]),
                "equivalent_plastic_strain": eqp,
                "plastic_dissipation_increment": dissipation,
            }
        )
        state = updated
    return rows, {
        "minimum_dissipation": minimum_dissipation,
        "maximum_yield_error": maximum_yield_error,
        "maximum_eqp_decrease": maximum_eqp_decrease,
        "maximum_state_mutation": maximum_state_mutation,
    }


def solve_uniaxial_stress_path(
    material: VonMisesElastoplasticMaterial,
    target_stresses: np.ndarray,
) -> list[dict[str, object]]:
    state = material.initial_state()
    unknowns = np.zeros(2, dtype=float)
    rows: list[dict[str, object]] = []
    for index, target in enumerate(np.asarray(target_stresses, dtype=float)):
        for iteration in range(30):
            strain = np.array([unknowns[0], unknowns[1], unknowns[1], 0.0, 0.0, 0.0])
            stress, tangent, _ = material.stress_tangent_state(strain, state)
            residual = np.array([stress[0] - target, stress[1]])
            if float(np.linalg.norm(residual)) <= 1.0e-11 * max(abs(float(target)), 1.0):
                break
            jacobian = np.array(
                [
                    [tangent[0, 0], tangent[0, 1] + tangent[0, 2]],
                    [tangent[1, 0], tangent[1, 1] + tangent[1, 2]],
                ]
            )
            unknowns -= np.linalg.solve(jacobian, residual)
        else:
            raise RuntimeError(f"Uniaxial material-point solve did not converge at target {target}.")
        strain = np.array([unknowns[0], unknowns[1], unknowns[1], 0.0, 0.0, 0.0])
        stress, _, updated = material.stress_tangent_state(strain, state)
        rows.append(
            {
                "step": index,
                "target_stress": float(target),
                "axial_stress": float(stress[0]),
                "lateral_stress": float(max(abs(stress[1]), abs(stress[2]))),
                "axial_strain": float(strain[0]),
                "lateral_strain": float(strain[1]),
                "axial_plastic_strain": float(updated["plastic_strain"][0]),
                "equivalent_plastic_strain": float(updated["equivalent_plastic_strain"]),
                "elastic": bool(updated["elastic"]),
                "iterations": iteration + 1,
            }
        )
        state = updated
    return rows


def _path_invariant_checks(name: str, metrics: dict[str, float]) -> list[J2VerificationCheck]:
    return [
        _upper_check(f"{name} - yield consistency", metrics["maximum_yield_error"], 1.0e-12, "relative error"),
        _upper_check(f"{name} - nonnegative dissipation", -metrics["minimum_dissipation"], 1.0e-12, "negative part"),
        _upper_check(f"{name} - monotone equivalent plastic strain", metrics["maximum_eqp_decrease"], 1.0e-14, "decrease"),
        _upper_check(f"{name} - previous state immutability", metrics["maximum_state_mutation"], 0.0, "state drift"),
    ]


def _finite_difference_tangent(
    material: VonMisesElastoplasticMaterial,
    strain: np.ndarray,
    state: dict[str, object],
) -> np.ndarray:
    step = 1.0e-7 * max(float(np.linalg.norm(strain)), 1.0)
    tangent = np.zeros((6, 6), dtype=float)
    for column in range(6):
        increment = np.zeros(6, dtype=float)
        increment[column] = step
        plus, _, _ = material.stress_tangent_state(strain + increment, state)
        minus, _, _ = material.stress_tangent_state(strain - increment, state)
        tangent[:, column] = (plus - minus) / (2.0 * step)
    return tangent


def _state_distance(left: dict[str, object], right: dict[str, object]) -> float:
    left_plastic = np.asarray(left.get("plastic_strain", [0.0] * 6), dtype=float)
    right_plastic = np.asarray(right.get("plastic_strain", [0.0] * 6), dtype=float)
    return max(
        abs(float(left.get("equivalent_plastic_strain", 0.0)) - float(right.get("equivalent_plastic_strain", 0.0))),
        float(np.max(np.abs(left_plastic - right_plastic))),
    )


def _upper_check(name: str, value: float, limit: float, criterion: str) -> J2VerificationCheck:
    passed = np.isfinite(value) and value <= limit
    return J2VerificationCheck(name, float(value), float(limit), "PASS" if passed else "FAIL", criterion)


def _lower_check(name: str, value: float, limit: float, criterion: str) -> J2VerificationCheck:
    passed = np.isfinite(value) and value >= limit
    return J2VerificationCheck(name, float(value), float(limit), "PASS" if passed else "FAIL", criterion)
