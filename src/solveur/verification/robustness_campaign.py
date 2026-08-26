# ruff: noqa: F401, F403, F405

"""Implementation group for the nonlinear robustness campaign: robustness_campaign."""

from __future__ import annotations

from solveur.verification.robustness_support import *  # noqa: F401,F403
from solveur.verification.robustness_foundations import *  # noqa: F401,F403
from solveur.verification.robustness_mesh import *  # noqa: F401,F403
from solveur.verification.robustness_geometric import *  # noqa: F401,F403
from solveur.verification.robustness_buckling import *  # noqa: F401,F403
from solveur.verification.robustness_arc_length import *  # noqa: F401,F403
from solveur.verification.robustness_contact import *  # noqa: F401,F403
from solveur.verification.robustness_coupling import *  # noqa: F401,F403



class RobustnessQualificationCampaign:
    """Produce the internal evidence package for the robustness work packages."""

    campaign_id = CAMPAIGN_ID

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir).resolve()

    def run(self) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        constitutive = run_constitutive_paths()
        tangent = tangent_finite_difference()
        transactions = transaction_check()
        elements = run_element_matrix()
        benchmark = run_common_global_benchmark()
        multi_element = run_multi_element_benchmark()
        energy_balance = run_energy_balance_benchmark()
        adversarial_rollback = run_adversarial_rollback_benchmark()
        mesh_refinement = run_mesh_refinement_benchmark()
        cyclic = run_cyclic_load_benchmark()
        buckling = run_linear_buckling_benchmark(ELEMENT_TYPES)
        buckling_mesh_sensitivity = run_buckling_mesh_sensitivity_benchmark()
        euler_buckling = run_euler_buckling_benchmark(self.output_dir / "euler_buckling")
        arc_length = run_arc_length_benchmark()
        fem_arc_length = run_fem_arc_length_benchmark()
        finite_kinematic_arc_length = run_finite_kinematic_arc_length_benchmark()
        shallow_arch = run_shallow_arch_arc_length_benchmark()
        contact = run_common_contact_benchmark()
        contact_tangent_fd = run_contact_tangent_fd_benchmark()
        contact_recontact = run_contact_recontact_benchmark()
        contact_penalty_sensitivity = run_contact_penalty_sensitivity_benchmark()
        contact_surface_search = run_contact_surface_search_benchmark()
        contact_updated_sliding = run_contact_updated_sliding_benchmark()
        contact_finite_sliding = run_contact_finite_sliding_benchmark()
        geometric_contact = run_geometric_contact_benchmark()
        multifamily_coupled_geometry = run_multifamily_coupled_geometry_benchmark()
        multifamily_coupled_contact = run_multifamily_coupled_contact_benchmark()
        coupling = run_coupling_benchmark()
        finite_kinematic = run_finite_kinematic_j2_benchmark()
        finite_kinematic_limit = run_finite_kinematic_limit_recovery_benchmark()
        geometric_high_order = run_high_order_geometric_benchmark()
        large_rotation = run_large_rotation_geometric_benchmark()
        large_rotation_mesh_sensitivity = run_large_rotation_mesh_sensitivity_benchmark()
        high_order_large_rotation_mesh_sensitivity = run_large_rotation_mesh_sensitivity_benchmark(
            ("TET10", "HEX20"),
            load_increments=20,
            load_scale=0.25,
        )
        failure_campaign = run_failure_campaign()
        external = _archived_external_correlation()
        internal_items = (constitutive, tangent, transactions, elements, benchmark, multi_element, energy_balance, adversarial_rollback, mesh_refinement, cyclic, buckling, buckling_mesh_sensitivity, euler_buckling, arc_length, fem_arc_length, finite_kinematic_arc_length, shallow_arch, contact, contact_tangent_fd, contact_recontact, contact_penalty_sensitivity, contact_surface_search, contact_updated_sliding, contact_finite_sliding, geometric_contact, multifamily_coupled_geometry, multifamily_coupled_contact, coupling, finite_kinematic, finite_kinematic_limit, geometric_high_order, large_rotation, large_rotation_mesh_sensitivity, high_order_large_rotation_mesh_sensitivity, failure_campaign)
        summary: dict[str, Any] = {
            "campaign_id": self.campaign_id,
            "status": "PASS_INTERNAL" if all(str(item["status"]).startswith("PASS") for item in internal_items) else "FAIL",
            "maturity": "experimental",
            "scope": {"elements": list(ELEMENT_TYPES), "material": "small-strain J2 isotropic hardening", "external_correlation": external["status"], "large_scale_claim": False},
            "constitutive_paths": constitutive,
            "consistent_tangent": tangent,
            "transactions": transactions,
            "element_matrix": elements,
            "common_global_benchmark": benchmark,
            "multi_element_benchmark": multi_element,
            "energy_balance": energy_balance,
            "adversarial_rollback": adversarial_rollback,
            "mesh_refinement_benchmark": mesh_refinement,
            "cyclic_load_benchmark": cyclic,
            "buckling_benchmark": buckling,
            "buckling_mesh_sensitivity_benchmark": buckling_mesh_sensitivity,
            "euler_buckling_benchmark": euler_buckling,
            "arc_length_benchmark": arc_length,
            "fem_arc_length_benchmark": fem_arc_length,
            "finite_kinematic_arc_length_benchmark": finite_kinematic_arc_length,
            "shallow_arch_arc_length_benchmark": shallow_arch,
            "common_contact_benchmark": contact,
            "contact_tangent_fd_benchmark": contact_tangent_fd,
            "contact_recontact_benchmark": contact_recontact,
            "contact_penalty_sensitivity_benchmark": contact_penalty_sensitivity,
            "contact_surface_search_benchmark": contact_surface_search,
            "contact_updated_sliding_benchmark": contact_updated_sliding,
            "contact_finite_sliding_benchmark": contact_finite_sliding,
            "geometric_contact_benchmark": geometric_contact,
            "multifamily_coupled_geometry_benchmark": multifamily_coupled_geometry,
            "multifamily_coupled_contact_benchmark": multifamily_coupled_contact,
            "coupling_benchmark": coupling,
            "finite_kinematic_j2_benchmark": finite_kinematic,
            "finite_kinematic_limit_recovery_benchmark": finite_kinematic_limit,
            "high_order_geometric_benchmark": geometric_high_order,
            "large_rotation_geometric_benchmark": large_rotation,
            "large_rotation_mesh_sensitivity_benchmark": large_rotation_mesh_sensitivity,
            "high_order_large_rotation_mesh_sensitivity_benchmark": high_order_large_rotation_mesh_sensitivity,
            "failure_campaign": failure_campaign,
            "external_correlations": external,
            "limitations": ["Small-strain J2 only.", "Mesh refinement and cyclic paths are internal evidence and require Owner acceptance bands before gate closure.", "The bounded RQ-G08 external archive remains one affine element per family.", "No physical validation claim is made."],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._write_report(summary)
        self._write_plots(summary)
        return summary

    def _write_report(self, summary: dict[str, Any]) -> None:
        lines = [f"# {self.campaign_id}", "", f"Statut interne : **{summary['status']}**", "", "## Matrice elementaire", "", "| Element | Points Gauss | Distordu | Statut |", "| --- | ---: | --- | --- |"]
        for row in summary["element_matrix"]["rows"]:
            lines.append(f"| {row['element']} | {row['integration_points']} | {row['distorted']} | {row['status']} |")
        lines.extend(["", "## Benchmark global", "", "| Element | Iterations Newton | Residu max | PEEQ final | Reaction | Temps (s) |", "| --- | ---: | ---: | ---: | ---: | ---: |"])
        for row in summary["common_global_benchmark"]["rows"]:
            lines.append(f"| {row['element']} | {row['newton_iterations']} | {row['maximum_relative_residual']:.3e} | {row['final_peeq']:.3e} | {row['reaction_norm']:.3e} | {row['elapsed_seconds']:.3f} |")
        lines.extend(["", "## Taux de convergence Newton observe", "", "Les ratios sont calcules entre residus consecutifs. Les ordres observes sont descriptifs et ne constituent pas un seuil de qualification.", "", "| Element | Historiques | Monotone | Ratio final max | Ordre observe |", "| --- | ---: | --- | ---: | ---: |"])
        for row in summary["common_global_benchmark"]["rows"]:
            metrics = row["rate_metrics"]
            orders = [value for history in metrics["observed_order_estimates"] for value in history]
            final_ratios = [value for value in metrics["final_reduction_ratios"] if value is not None]
            lines.append(f"| {row['element']} | {metrics['history_count']} | {metrics['monotone_nonincreasing']} | {max(final_ratios, default=float('nan')):.3e} | {max(orders, default=float('nan')):.3f} |")
        lines.extend(["", "| Element | Full Newton | Modified Newton |", "| --- | --- | --- |"])
        for row in summary["common_global_benchmark"]["newton_rate_study"]["rows"]:
            lines.append(f"| {row['element']} | {row['full_newton']['status']} ({row['full_newton']['iterations']} iter.) | {row['modified_newton']['status']} ({row['modified_newton']['iterations']} iter.) |")
        lines.extend(["", "## Benchmark global multi-element", "", "| Element | Noeuds | Elements | DDL | Iterations Newton | Residu max | PEEQ final | Dissipation plastique |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"])
        for row in summary["multi_element_benchmark"]["rows"]:
            lines.append(f"| {row['element']} | {row['node_count']} | {row['element_count']} | {row['dof_count']} | {row['newton_iterations']} | {row['maximum_relative_residual']:.3e} | {row['final_peeq']:.3e} | {row['final_plastic_dissipation']:.3e} |")
        lines.extend(["", "## Bilan energetique", "", "| Element | W externe | U elastique | D plastique | Erreur relative | Dissipation non negative |", "| --- | ---: | ---: | ---: | ---: | --- |"])
        for row in summary["energy_balance"]["rows"]:
            lines.append(f"| {row['element']} | {row['total_external_work']:.6e} | {row['elastic_strain_energy']:.6e} | {row['plastic_dissipation']:.6e} | {row['relative_balance_error']:.3e} | {row['nonnegative_dissipation']} |")
        lines.extend(["", "## Rollback adversarial", "", f"Statut : **{summary['adversarial_rollback']['status']}**", "", f"Retry propre : `{summary['adversarial_rollback']['clean_retry']}`", f"Increments rejetes : `{summary['adversarial_rollback']['rejected_increments']}`", f"Erreur displacement vs reference : `{summary['adversarial_rollback']['final_displacement_relative_error']:.3e}`", f"Erreur PEEQ finale vs reference : `{summary['adversarial_rollback']['final_peeq_absolute_error']:.3e}`"])
        lines.extend(["", "## Raffinement maillage", "", "Les variations coarse/fine sont archivees sans seuil automatique.", ""])
        for family in summary["mesh_refinement_benchmark"]["rows"]:
            finest = family["levels"][-1]
            lines.append(f"- {family['element']}: niveaux {[row['cells_x'] for row in family['levels']]}, DDL fin {finest['dof_count']}, variation coarse/fine deplacement `{finest['change_from_coarse']['tip_displacement_norm']:.3e}`")
        lines.extend(["", "## Chargement cyclique", "", "| Element | PEEQ final | Dissipation finale | Residu max |", "| --- | ---: | ---: | ---: |"])
        for row in summary["cyclic_load_benchmark"]["rows"]:
            lines.append(f"| {row['element']} | {row['final_peeq']:.3e} | {row['final_plastic_dissipation']:.3e} | {row['maximum_relative_residual']:.3e} |")
        lines.extend(["", "## Stabilité, continuation et contact", "", f"Buckling : **{summary['buckling_benchmark']['status']}**", "", "| Element | Facteur critique | Formulation | Bracket relatif | Résidu mode | Tangente initiale nnz |", "| --- | ---: | --- | ---: | ---: | ---: |"])
        for row in summary["buckling_benchmark"]["rows"]:
            lines.append(f"| {row['element']} | {row['critical_factor']:.6e} | {row['eigen_formulation']} | {row['relative_bracket_width']:.3e} | {row['critical_mode_residual_relative']:.3e} | {row['initial_tangent_nnz']} |")
        buckling_trend = summary["buckling_mesh_sensitivity_benchmark"]
        trend_changes = {
            row["element"]: row["levels"][-1].get("critical_factor_relative_change")
            for row in buckling_trend["rows"]
        }
        lines.append(
            f"Sensibilite maillage buckling : **{buckling_trend['status']}**, "
            f"niveaux `{buckling_trend['levels']}`, variation facteur coarse/medium `{trend_changes}`."
        )
        multifamily_coupling = summary["multifamily_coupled_geometry_benchmark"]
        lines.append(
            f"Couplage J2/geometrie quatre familles : **{multifamily_coupling['status']}**, "
            f"familles `{[row['element'] for row in multifamily_coupling['rows']]}`, "
            f"residu max `{max(row['maximum_relative_residual'] for row in multifamily_coupling['rows']):.3e}`."
        )
        lines.extend(["", f"Euler TET4 : **{summary['euler_buckling_benchmark']['status']}**, niveaux `{[row['cells'] for row in summary['euler_buckling_benchmark']['levels']]}`, erreur Euler finale `{100 * summary['euler_buckling_benchmark']['levels'][-1]['euler_relative_error']:.2f} %`.", f"Arc-length commun : **{summary['arc_length_benchmark']['status']}**, etapes `{summary['arc_length_benchmark']['step_count']}`, cible atteinte `{summary['arc_length_benchmark']['reached_target']}`.", f"Arc-length FEM TET4 : **{summary['fem_arc_length_benchmark']['status']}**, etapes `{summary['fem_arc_length_benchmark']['step_count']}`, facteur `{summary['fem_arc_length_benchmark']['load_factor_range']}`, residu `{summary['fem_arc_length_benchmark']['maximum_relative_residual']:.3e}`.", f"Shallow arch reduit : **{summary['shallow_arch_arc_length_benchmark']['status']}**, point limite observe `{summary['shallow_arch_arc_length_benchmark']['limit_point_observed']}`, branches `{summary['shallow_arch_arc_length_benchmark']['branch_turn_count']}`.", f"Contact commun : **{summary['common_contact_benchmark']['status']}**, tangent ouverte `{summary['common_contact_benchmark']['open_tangent_nnz']}`, tangent fermee `{summary['common_contact_benchmark']['closed_tangent_nnz']}`.", f"Recontact : **{summary['contact_recontact_benchmark']['status']}**, sequence `{summary['contact_recontact_benchmark']['active_by_step']}`.", f"Sensibilite penalty : **{summary['contact_penalty_sensitivity_benchmark']['status']}**, tendance penetration monotone `{summary['contact_penalty_sensitivity_benchmark']['penetration_monotone_nonincreasing']}`.", f"Recherche surface multi-face : **{summary['contact_surface_search_benchmark']['status']}**, faces `{summary['contact_surface_search_benchmark']['selected_face_indices']}`.", f"Couplages : **{summary['coupling_benchmark']['status']}**, driver commun `{summary['coupling_benchmark']['shared_driver']}`.", f"J2 finite-kinematic : **{summary['finite_kinematic_j2_benchmark']['status']}**, familles `{[row['element'] for row in summary['finite_kinematic_j2_benchmark']['rows']]}`.", f"Geometrie haut ordre : **{summary['high_order_geometric_benchmark']['status']}**, familles `{[row['element'] for row in summary['high_order_geometric_benchmark']['rows']]}`."])
        lines.append(
            f"Contact tangent FD : **{summary['contact_tangent_fd_benchmark']['status']}**, "
            f"erreur relative maximale `{summary['contact_tangent_fd_benchmark']['maximum_relative_error']:.3e}`."
        )
        lines.append(
            f"Glissement mis a jour : **{summary['contact_updated_sliding_benchmark']['status']}**, "
            f"sequence `{summary['contact_updated_sliding_benchmark']['face_sequence']}`."
        )
        lines.append(
            f"Geometrie + contact : **{summary['geometric_contact_benchmark']['status']}**, "
            f"contacts actifs `{summary['geometric_contact_benchmark']['contact'].get('active_contacts', [])}`, "
            f"penetration `{summary['geometric_contact_benchmark']['contact'].get('maximum_penetration', 0.0):.3e}`."
        )
        lines.append(
            f"Grande rotation : **{summary['large_rotation_geometric_benchmark']['status']}**, "
            f"angles `{[round(row['end_line_angle_deg'], 2) for row in summary['large_rotation_geometric_benchmark']['rows']]}` deg."
        )
        lines.append(
            f"Sensibilite maillage grande rotation : **{summary['large_rotation_mesh_sensitivity_benchmark']['status']}**, "
            f"niveaux `{summary['large_rotation_mesh_sensitivity_benchmark']['levels']}`, "
            f"variations `{[row['coarse_to_refined'] for row in summary['large_rotation_mesh_sensitivity_benchmark']['rows']]}`."
        )
        lines.append(
            f"Sensibilite maillage grande rotation haut ordre : **{summary['high_order_large_rotation_mesh_sensitivity_benchmark']['status']}**, "
            f"charge `{summary['high_order_large_rotation_mesh_sensitivity_benchmark']['load_scale']}`, "
            f"familles `{[row['element'] for row in summary['high_order_large_rotation_mesh_sensitivity_benchmark']['rows']]}`."
        )
        lines.append(
            f"Couplage contact quatre familles : **{summary['multifamily_coupled_contact_benchmark']['status']}**, "
            f"familles `{[row['element'] for row in summary['multifamily_coupled_contact_benchmark']['rows']]}`, "
            f"contacts actifs `{[row.get('active_step_count', 0) for row in summary['multifamily_coupled_contact_benchmark']['rows']]}`."
        )
        lines.append(
            f"Recuperation small-strain/finite-kinematic : **{summary['finite_kinematic_limit_recovery_benchmark']['status']}**, "
            f"ecarts `{[row['relative_displacement_error'] for row in summary['finite_kinematic_limit_recovery_benchmark']['rows']]}`."
        )
        lines.append(
            f"Failure contract : **{summary['failure_campaign']['status']}**, "
            f"cas principaux `{len(summary['failure_campaign']['cases'])}`, "
            f"retries `{len(summary['failure_campaign']['retry_cases'])}`."
        )
        lines.append(
            f"Arc-length J2 finite-kinematic : **{summary['finite_kinematic_arc_length_benchmark']['status']}**, "
            f"facteur final `{summary['finite_kinematic_arc_length_benchmark']['final_load_factor']:.6e}`, "
            f"residu `{summary['finite_kinematic_arc_length_benchmark']['maximum_relative_residual']:.3e}`."
        )
        lines.extend(
            [
                "",
                "### Arc-length J2 finite-kinematic par famille",
                "",
                "| Element | Etapes | Plage facteur | Plage rayon | Residu max | Statut |",
                "| --- | ---: | --- | --- | ---: | --- |",
            ]
        )
        for row in summary["finite_kinematic_arc_length_benchmark"]["rows"]:
            lines.append(
                f"| {row['element']} | {row['step_count']} | {row['load_factor_range']} | "
                f"{row['radius_range']} | {row['maximum_relative_residual']:.3e} | {row['status']} |"
            )
        lines.append("")
        lines.append("Le bilan travail externe/interne est enregistre dans `summary.json` avec l'imbalance relative par increment.")
        lines.extend(["", "## Robustesse", "", f"Tangent FD max : `{summary['consistent_tangent']['maximum_relative_error']:.3e}`", f"Transactions : **{summary['transactions']['status']}**", "", "![Force displacement](force_displacement.png)", "", "![Newton rate](newton_rate.png)", "", f"Correlation externe : **{summary['external_correlations']['status']}**", ""])
        (self.output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")

    def _write_plots(self, summary: dict[str, Any]) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        figure, axes = plt.subplots(1, 2, figsize=(10.0, 4.2), constrained_layout=True)
        for row in summary["element_matrix"]["rows"]:
            factors = [item["factor"] for item in row["history"]]
            axes[0].plot(factors, [item["reaction_norm"] for item in row["history"]], marker="o", label=row["element"])
        axes[0].set(xlabel="Facteur de charge", ylabel="Norme force interne", title="Force-deplacement borne")
        for row in summary["common_global_benchmark"]["rows"]:
            axes[1].bar(row["element"], row["newton_iterations"])
        axes[1].set(ylabel="Iterations Newton", title="Cout Newton par element")
        axes[0].legend()
        for axis in axes:
            axis.grid(alpha=0.25)
        figure.savefig(self.output_dir / "force_displacement.png", dpi=160)
        plt.close(figure)
        figure, axis = plt.subplots(figsize=(6.4, 4.0))
        for row in summary["common_global_benchmark"]["rows"]:
            for index, history in enumerate(row["residual_histories"]):
                axis.semilogy(range(1, len(history) + 1), history, marker="o", markersize=2, alpha=0.65, label=row["element"] if index == 0 else None)
        axis.set(xlabel="Iteration Newton", ylabel="Residu relatif", title="Historiques de convergence Newton")
        axis.grid(alpha=0.25)
        axis.legend()
        figure.savefig(self.output_dir / "newton_rate.png", dpi=160)
        plt.close(figure)
        figure, axis = plt.subplots(figsize=(6.4, 4.0))
        arch = summary["shallow_arch_arc_length_benchmark"]
        steps = arch["steps"]
        axis.plot(
            [row["displacement"] for row in steps],
            [row["load_factor"] for row in steps],
            "o-",
            label="arc-length",
            markersize=3,
        )
        u_reference = np.linspace(-1.05, 1.05, 300)
        axis.plot(u_reference, u_reference - u_reference**3, "--", label="reference")
        axis.set(xlabel="Deplacement reduit", ylabel="Facteur de charge", title="Shallow arch: suivi de branche")
        axis.grid(alpha=0.25)
        axis.legend()
        figure.savefig(self.output_dir / "shallow_arch_arc_length.png", dpi=160)
        plt.close(figure)
        figure, axes = plt.subplots(2, 1, figsize=(7.0, 6.0), sharex=False)
        arc = summary["finite_kinematic_arc_length_benchmark"]
        for row in arc["rows"]:
            axes[0].plot(row["load_factor"], marker=".", linewidth=1.0, label=row["element"])
            if row["radius_history"]:
                axes[1].semilogy(
                    range(1, len(row["radius_history"]) + 1),
                    row["radius_history"],
                    marker=".",
                    linewidth=1.0,
                    label=row["element"],
                )
        axes[0].set(xlabel="Etape", ylabel="Facteur de charge", title="Arc-length J2 finite-kinematic")
        axes[1].set(xlabel="Etape", ylabel="Rayon arc-length", title="Adaptation du rayon")
        for axis in axes:
            axis.grid(alpha=0.25)
            axis.legend()
        figure.tight_layout()
        figure.savefig(self.output_dir / "finite_kinematic_arc_length.png", dpi=160)
        plt.close(figure)


__all__ = [name for name in globals() if not name.startswith("__")]
