"""Rebuild all numerical, tabular and graphical evidence used by the local site."""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import numpy as np
from scripts.docs_benchmarks import MeshedBenchmarkDocumenter
from scripts.docs_assembly import publish_assembly_element_examples
from scripts.docs_content_closure import publish_technical_content_closure
from scripts.docs_mitc4_modal import publish_mitc4_modal_plate
from scripts.docs_shell_verification import publish_shell_verification
from scripts.docs_support import (
    plot_deformed_model,
    plot_dual_axis,
    plot_log_categories,
    plot_line_series,
    plot_mitc4_formulation,
    plot_tetra_formulation,
    write_json,
    write_markdown_table,
)
from scripts.docs_torsion import publish_torsion_stress_probe
from scripts.docs_models import DocumentationModelFactory, mean_tip_displacement, unit_tet10_coordinates
from scripts.docs_contact import publish_contact_verification
from scripts.docs_publication import DocumentationPublisher
from solveur.api import (
    generate_large_tet4_block,
    list_methods,
    load_model,
    save_result,
    solve_large_model,
    solve_model,
)
from solveur.core.analysis import AnalysisSettings
from solveur.elements.solid.tet10 import Tet10Element
from solveur.elements.solid.tet4 import Tet4Element
from solveur.io.manifest import git_source_state, sha256
from solveur.materials.solid import SolidMaterial
from solveur.verification.j2_structural import J2StructuralCyclicCampaign
@dataclass(frozen=True)
class DemoRecord:
    """Trace one published demonstration to its input and acceptance basis."""

    case_id: str
    family: str
    model_path: str
    input_sha256: str
    analysis: str
    method: str
    verdict: str
    maturity: str
    reference_type: str
    acceptance: str
class DocumentationAssetBuilder:
    """Run official models and write every generated site artifact."""

    def __init__(self, project_root: str | Path, *, profile: str = "engineering") -> None:
        self.root = Path(project_root).resolve()
        self.profile = profile
        self.docs = self.root / "docs"
        self.generated = self.docs / "generated"
        self.assets = self.docs / "assets" / "generated"
        self.models = self.generated / "models"
        self.results = self.generated / "results"
        self.records: list[DemoRecord] = []
        self.model_factory = DocumentationModelFactory(self.root, self.models)
        self.scales: dict[str, float] = {}

    def build(self) -> dict[str, Any]:
        # Capture provenance before resetting generated outputs, which makes the
        # working tree dirty during a normal documentation build.
        source_state = git_source_state(self.root)
        self._reset_outputs()
        self._build_formulation_figures()
        self._build_static_examples()
        self._build_solid_convergence()
        publish_assembly_element_examples(self.root, self.generated, self.assets)
        self._build_linear_methods()
        self._build_modal()
        publish_mitc4_modal_plate(self.generated, self.assets)
        self._build_newmark()
        self._build_harmonic()
        self._build_nonlinear()
        publish_contact_verification(self.generated, self.assets)
        publish_shell_verification(self.generated, self.assets)
        self._build_large_model()
        self._build_meshed_benchmarks()
        publish_technical_content_closure(self.root, self.generated, self.assets)
        return DocumentationPublisher(
            self.root,
            profile=self.profile,
            records=self.records,
            scales=self.scales,
            source_state=source_state,
        ).publish()

    def _build_meshed_benchmarks(self) -> None:
        records = MeshedBenchmarkDocumenter(
            self.root,
            self.generated / "benchmarks",
            self.assets / "benchmarks",
            profile=self.profile,
        ).build()
        self.records.extend(DemoRecord(**record) for record in records)
        publish_torsion_stress_probe(self.root, self.generated, self.assets)

    def _reset_outputs(self) -> None:
        for target in (self.generated, self.assets):
            resolved = target.resolve()
            if self.docs.resolve() not in resolved.parents:
                raise RuntimeError(f"Refusing to reset generated path outside docs: {resolved}")
            if target.exists():
                shutil.rmtree(target)
            target.mkdir(parents=True, exist_ok=True)
        self.models.mkdir(parents=True, exist_ok=True)
        self.results.mkdir(parents=True, exist_ok=True)

    def _build_formulation_figures(self) -> None:
        plot_tetra_formulation(self.assets / "tet4_formulation.svg", quadratic=False)
        plot_tetra_formulation(self.assets / "tet10_formulation.svg", quadratic=True)
        plot_mitc4_formulation(self.assets / "mitc4_formulation.svg")

    def _build_static_examples(self) -> dict[str, tuple[object, object, dict[str, Any]]]:
        cases: dict[str, tuple[object, object, dict[str, Any]]] = {}
        for name, case_id in (
            ("tet4_static.json", "DOC-TET4-STATIC-001"),
            ("tet4_compression.json", "DOC-TET4-COMPRESSION-001"),
            ("tet4_body_force.json", "DOC-TET4-BODY-FORCE-001"),
            ("tet10_static.json", "DOC-TET10-STATIC-001"),
            ("mitc4_shell_static.json", "DOC-MITC4-MEMBRANE-001"),
            ("tet4_pressure.json", "DOC-TET4-PRESSURE-001"),
        ):
            cases[name] = self._solve_official(name, case_id)

        tet4_model, tet4_result, tet4_data = cases["tet4_static.json"]
        self.scales["tet4_static"] = plot_deformed_model(
            tet4_model,
            tet4_result,
            self.assets / "tet4_deformation.png",
            title="TET4 unitaire - traction UX",
        )
        self._write_static_table("tet4_results.md", tet4_data, self.scales["tet4_static"])

        compression_model, compression_result, compression_data = cases["tet4_compression.json"]
        self.scales["tet4_compression"] = plot_deformed_model(
            compression_model,
            compression_result,
            self.assets / "tet4_compression.png",
            title="TET4 unitaire - compression UX",
        )
        self._write_static_table(
            "tet4_compression_results.md",
            compression_data,
            self.scales["tet4_compression"],
        )

        body_force_data = cases["tet4_body_force.json"][2]
        body_equilibrium = body_force_data["audit"]["equilibrium"]
        body_external = body_equilibrium["external_resultant"]
        body_reaction = body_equilibrium["reaction_resultant"]
        force_error = body_equilibrium["force_balance_relative_error"]
        moment_error = body_equilibrium["moment_balance_relative_error"]
        write_markdown_table(
            self.generated / "tet4_body_force_results.md",
            ("Grandeur", "Calcule", "Reference", "Verdict"),
            [
                ("Resultante charge [N]", _vector(body_external), "[1000, 0, 0]", np.allclose(body_external, [1000.0, 0.0, 0.0], atol=1.0e-12)),
                ("Resultante reactions [N]", _vector(body_reaction), "[-1000, 0, 0]", np.allclose(body_reaction, [-1000.0, 0.0, 0.0], atol=1.0e-12)),
                ("Erreur bilan forces", force_error, "<= 1e-12", force_error <= 1.0e-12),
                ("Erreur bilan moments", moment_error, "<= 1e-12", moment_error <= 1.0e-12),
            ],
        )

        tet10_model, tet10_result, tet10_data = cases["tet10_static.json"]
        self.scales["tet10_static"] = plot_deformed_model(
            tet10_model,
            tet10_result,
            self.assets / "tet10_deformation.png",
            title="TET10 unitaire - traction UX",
        )
        self._write_static_table("tet10_results.md", tet10_data, self.scales["tet10_static"])

        pressure_data = cases["tet4_pressure.json"][2]
        balance = pressure_data["solver"]["load_assembly"]
        resultant = balance["resultant"]
        moment = balance["moment_about_origin"]
        expected = (-500.0, -500.0, -500.0)
        error = max(abs(float(value) - reference) for value, reference in zip(resultant, expected))
        write_markdown_table(
            self.generated / "tet4_pressure_results.md",
            ("Grandeur", "Calcule", "Reference", "Erreur max", "Verdict"),
            [
                ("Resultante [N]", _vector(resultant), _vector(expected), error, error <= 1.0e-10),
                ("Moment origine [N.m]", _vector(moment), "[0, 0, 0]", max(abs(float(v)) for v in moment), max(abs(float(v)) for v in moment) <= 1.0e-10),
            ],
        )

        shell_model, shell_path = self.model_factory.mitc4_plate()
        shell_result = solve_model(shell_model)
        shell_data = shell_result.to_dict()
        save_result(shell_result, self.results / "mitc4_plate_bending.json")
        self.scales["mitc4_plate"] = plot_deformed_model(
            shell_model,
            shell_result,
            self.assets / "mitc4_deformation.png",
            title="Plaque MITC4 encastree - flexion",
        )
        self._record(
            "DOC-MITC4-BENDING-001",
            "MITC4",
            shell_path,
            shell_model,
            shell_data,
            "benchmark_energetique",
            "residu relatif <= 1e-7; convergence maillage requise",
        )
        mitc4_data = cases["mitc4_shell_static.json"][2]
        element = mitc4_data["element_results"][0]
        write_markdown_table(
            self.generated / "mitc4_results.md",
            ("Grandeur", "Valeur", "Unite/interpretation"),
            [
                ("Verdict", mitc4_data["run_verdict"], "profil engineering"),
                ("Deplacement maximal", mitc4_data["max_displacement"], "m"),
                ("Resultante membrane Nx", element["membrane_force"][0], "N/m"),
                ("von Mises face superieure", element["shell_faces"][1]["von_mises"], "Pa"),
                ("Residu relatif libre", mitc4_data["audit"]["equilibrium"]["free_relative_residual"], "sans dimension"),
                ("Facteur figure de flexion", self.scales["mitc4_plate"], "affichage uniquement"),
            ],
        )
        return cases

    def _solve_official(self, name: str, case_id: str) -> tuple[object, object, dict[str, Any]]:
        model_path = self.root / "examples" / name
        model = load_model(model_path)
        model.verification_profile = "engineering"
        result = solve_model(model)
        data = result.to_dict()
        save_result(result, self.results / name)
        reference_type = {
            "tet4_static.json": "analytic",
            "tet4_compression.json": "analytic",
            "tet4_body_force.json": "equilibrium_closed_form",
            "tet4_pressure.json": "equilibrium_closed_form",
            "tet10_static.json": "non_regression_and_patch",
            "mitc4_shell_static.json": "equilibrium_closed_form",
        }.get(name, "verification")
        self._record(case_id, _family(model), model_path, model, data, reference_type, "criteres de qualification/campaign.json")
        return model, result, data

    def _write_static_table(self, name: str, data: dict[str, Any], scale: float) -> None:
        element = data["element_results"][0]
        equilibrium = data["audit"]["equilibrium"]
        rows = [
            ("Verdict", data["run_verdict"], "profil engineering"),
            ("Noeuds / elements / ddl", f"{data['node_count']} / {data['element_count']} / {data['ndof']}", "comptage"),
            ("Deplacement maximal", data["max_displacement"], "m"),
            ("von Mises elementaire", element["von_mises"], "Pa"),
            ("Residu relatif libre", equilibrium["free_relative_residual"], "sans dimension"),
            ("Erreur identite energie", equilibrium["linear_energy_identity_relative_error"], "sans dimension"),
            ("Facteur de deformee", scale, "affichage uniquement"),
        ]
        write_markdown_table(self.generated / name, ("Grandeur", "Valeur", "Unite/interpretation"), rows)

    def _build_solid_convergence(self) -> None:
        material = SolidMaterial(E=1000.0, nu=0.25)
        tet4 = Tet4Element(material)
        tet10 = Tet10Element(material)
        sizes = np.asarray([1.0, 0.5, 0.25, 0.125])
        tet4_errors: list[float] = []
        tet10_errors: list[float] = []
        for size in sizes:
            quadratic = unit_tet10_coordinates() * size
            exact = 0.5 * size
            corner_u = np.zeros(12)
            corner_u[0::3] = quadratic[:4, 0] ** 2
            quadratic_u = np.zeros(30)
            quadratic_u[0::3] = quadratic[:, 0] ** 2
            tet4_errors.append(abs(float(tet4.strain(quadratic[:4], corner_u)[0]) - exact))
            tet10_errors.append(abs(float(tet10.strain(quadratic, quadratic_u)[0]) - exact))

        beam_rows = []
        finest: tuple[object, object] | None = None
        for refinement in (1, 2, 3):
            model, model_path = self.model_factory.tet4_cantilever(refinement)
            result = solve_model(model)
            tip = mean_tip_displacement(model, result, component="UZ")
            euler = -1000.0 * 4.0**3 / (3.0 * 70.0e9 * (1.0 * 1.0**3 / 12.0))
            beam_rows.append((refinement, len(model.elements), result.dofs.ndof, tip, euler, abs((tip - euler) / euler)))
            save_result(result, self.results / f"tet4_cantilever_r{refinement}.json")
            if refinement == 3:
                finest = (model, result)
                self._record(
                    "DOC-TET4-CANTILEVER-001",
                    "TET4",
                    model_path,
                    model,
                    result.to_dict(),
                    "engineering_beam_reference",
                    "tendance sous raffinement; reference poutre non qualifiante",
                )
        if finest is not None:
            plot_deformed_model(
                finest[0],
                finest[1],
                self.assets / "tet4_cantilever.png",
                title="Bloc TET4 multi-elements en flexion",
            )

        plot_line_series(
            self.assets / "solid_convergence.png",
            [
                {"x": sizes, "y": tet4_errors, "label": "TET4 - erreur de deformation"},
                {"x": sizes, "y": np.maximum(tet10_errors, 1.0e-16), "label": "TET10 - erreur numerique"},
            ],
            title="Reproduction du champ quadratique $u_x=x^2$",
            xlabel="Taille h",
            ylabel="Erreur sur epsilon_x au barycentre",
            yscale="log",
        )
        rows = [
            (float(size), tet4_error, tet10_error, tet4_error <= 0.51 * size, tet10_error <= 1.0e-12)
            for size, tet4_error, tet10_error in zip(sizes, tet4_errors, tet10_errors)
        ]
        write_markdown_table(
            self.generated / "solid_convergence_results.md",
            ("h", "Erreur TET4", "Erreur TET10", "Ordre TET4 attendu", "TET10 exact"),
            rows,
        )
        write_markdown_table(
            self.generated / "tet4_cantilever_results.md",
            ("Raffinement", "Elements", "Ddl", "Uz moyen bout [m]", "Euler-Bernoulli [m]", "Ecart indicatif"),
            beam_rows,
        )

        tet10_model, tet10_path = self.model_factory.tet10_cantilever()
        tet10_result = solve_model(tet10_model)
        save_result(tet10_result, self.results / "tet10_cantilever.json")
        plot_deformed_model(
            tet10_model,
            tet10_result,
            self.assets / "tet10_cantilever.png",
            title="Bloc TET10 multi-elements en flexion",
        )
        self._record(
            "DOC-TET10-CANTILEVER-001",
            "TET10",
            tet10_path,
            tet10_model,
            tet10_result.to_dict(),
            "engineering_comparison",
            "illustration experimentale; patch quadratique separe",
        )

    def _build_linear_methods(self) -> None:
        rows = []
        residuals = []
        method_names = []
        for method in ("direct", "cg", "gmres", "bicgstab", "minres"):
            model = load_model(self.root / "examples" / "tet4_static.json")
            parameters: dict[str, object] = {"type": "linear_static", "method": method, "rtol": 1.0e-12, "maxiter": 200}
            if method == "cg":
                # This fully Dirichlet-constrained, positive-elasticity example has a reduced SPD stiffness matrix.
                parameters["assume_spd"] = True
            model.analysis = AnalysisSettings.from_raw(
                parameters
            )
            result = solve_model(model)
            info = result.to_dict()["solver"]
            history = [max(float(value), 1.0e-30) for value in info["residual_history"]]
            method_names.append(method)
            residuals.append(history[-1])
            rows.append((method, info["preconditioner"], info["iterations"], info["residual_norm"], info["converged"]))
        plot_log_categories(
            self.assets / "linear_solver_residuals.png",
            method_names,
            residuals,
            title="Residus finaux des solveurs sur le cas TET4 officiel",
            ylabel="Norme du residu final",
        )
        write_markdown_table(
            self.generated / "linear_solver_results.md",
            ("Methode", "Preconditionneur", "Iterations", "Residu final", "Converge"),
            rows,
        )
        method_rows = []
        for analysis, methods in sorted(list_methods().items()):
            method_rows.append((analysis, ", ".join(methods)))
        write_markdown_table(self.generated / "solver_matrix.md", ("Analyse", "Methodes publiees par l'API"), method_rows)

    def _build_modal(self) -> None:
        model_path = self.root / "examples" / "tet4_modal_unit.json"
        model = load_model(model_path)
        result = solve_model(model)
        data = result.to_dict()
        save_result(result, self.results / "tet4_modal_unit.json")
        scale = plot_deformed_model(
            model,
            result,
            self.assets / "modal_mode_1.png",
            title="TET4 - premiere forme propre",
            vector=result.modes[:, 0],
            color_label="Amplitude modale normalisee",
        )
        diagnostics = data["solver"]
        rows = []
        for mode, residual, modal_mass in zip(data["modes"], diagnostics["relative_residuals"], diagnostics["modal_masses"]):
            rows.append((mode["index"], mode["frequency_hz"], residual, modal_mass))
        rows.extend(
            [
                ("Orthogonalite M", diagnostics["mass_orthogonality_error"], "-", "-"),
                ("Diagonalisation K", diagnostics["stiffness_diagonal_error"], "-", "-"),
                ("Facteur figure", scale, "-", "affichage"),
            ]
        )
        write_markdown_table(
            self.generated / "modal_results.md",
            ("Mode/controle", "Frequence ou valeur", "Residu relatif", "Masse modale"),
            rows,
        )
        self._record(
            "DOC-MODAL-SDOF-001",
            "Modal",
            model_path,
            model,
            data,
            "analytic",
            "frequence analytique et residu propre <= 1e-10",
        )

    def _build_newmark(self) -> None:
        model_path = self.root / "examples" / "tet4_dynamic_sdof_free_vibration.json"
        model = load_model(model_path)
        result = solve_model(model)
        data = result.to_dict()
        save_result(result, self.results / "tet4_dynamic_sdof_free_vibration.json")
        history = data["solver"]["time_history"]
        times = [row["time"] for row in history]
        displacement = [row["max_displacement"] for row in history]
        energy = [row["relative_energy_drift"] for row in history]
        plot_dual_axis(
            self.assets / "newmark_history.png",
            times,
            displacement,
            energy,
            title="Oscillateur TET4 libre - Newmark acceleration moyenne",
            xlabel="Temps [s]",
            left_label="|u|max [m]",
            right_label="Derive relative d'energie",
        )
        write_markdown_table(
            self.generated / "newmark_results.md",
            ("Grandeur", "Valeur", "Critere"),
            [
                ("Pas de temps [s]", data["solver"]["time_step"], "positif"),
                ("Nombre de pas", data["solver"]["step_count"], "40"),
                ("Beta / gamma", f"{data['solver']['newmark_beta']} / {data['solver']['newmark_gamma']}", "1/4 et 1/2"),
                ("Derive energie max", max(abs(float(value)) for value in energy), "<= 1e-8"),
                ("Residu dynamique max", max(data["solver"]["residual_history"]), "seuil du profil"),
                ("Factorisation reutilisee", data["solver"]["effective_factorization_reused"], "attendu en direct"),
            ],
        )
        self._record(
            "DOC-NEWMARK-SDOF-001",
            "Newmark",
            model_path,
            model,
            data,
            "analytic",
            "frequence fermee et derive energie <= 1e-8",
        )

    def _build_harmonic(self) -> None:
        model_path = self.root / "examples" / "tet4_harmonic_sdof_response.json"
        model = load_model(model_path)
        frequencies = np.linspace(0.0, 20.0, 81)
        parameters = dict(model.analysis.parameters)
        parameters["frequencies_hz"] = frequencies.tolist()
        model.analysis = AnalysisSettings("harmonic_response", "direct_frequency", parameters)
        result = solve_model(model)
        data = result.to_dict()
        save_result(result, self.results / "tet4_harmonic_sweep.json")
        index = result.dofs.index(1, "UX")
        responses = np.asarray([response[index] for response in result.responses], dtype=complex)
        amplitude = np.abs(responses)
        phase = np.degrees(np.angle(responses))
        plot_dual_axis(
            self.assets / "harmonic_response.png",
            frequencies,
            amplitude,
            phase,
            title="Reponse harmonique TET4 1 ddl",
            xlabel="Frequence [Hz]",
            left_label="Amplitude UX [m]",
            right_label="Phase [deg]",
        )
        peak = int(np.argmax(amplitude))
        write_markdown_table(
            self.generated / "harmonic_results.md",
            ("Grandeur", "Valeur", "Reference/critere"),
            [
                ("Amplitude a 0 Hz", amplitude[0], "statique"),
                ("Frequence du pic [Hz]", frequencies[peak], "proche du mode 1"),
                ("Amplitude au pic", amplitude[peak], "finie avec amortissement"),
                ("Phase au pic [deg]", phase[peak], "transition autour de la resonance"),
                ("Residu max", data["solver"]["max_residual_norm"], "seuil du profil"),
            ],
        )
        self._record(
            "DOC-HARMONIC-SDOF-001",
            "Harmonique",
            model_path,
            model,
            data,
            "analytic",
            "fonction de transfert fermee; limite 0 Hz statique",
        )

    def _build_nonlinear(self) -> None:
        model_path = self.root / "examples" / "tet4_elastoplastic_static.json"
        model = load_model(model_path)
        result = solve_model(model)
        data = result.to_dict()
        save_result(result, self.results / "tet4_elastoplastic_static.json")
        steps = data["solver"]["steps"]
        plot_line_series(
            self.assets / "nonlinear_convergence.png",
            [
                {"x": [row["load_factor"] for row in steps], "y": [max(row["relative_residual"], 1.0e-30) for row in steps], "label": "residu relatif"},
                {"x": [row["load_factor"] for row in steps], "y": [row["iterations"] for row in steps], "label": "iterations"},
            ],
            title="Convergence du cas elastoplastique TET4",
            xlabel="Facteur de charge",
            ylabel="Residus / iterations (echelles partagees)",
            yscale="log",
        )
        final_states = data.get("material_states", {})
        write_markdown_table(
            self.generated / "nonlinear_results.md",
            ("Grandeur", "Valeur", "Statut"),
            [
                ("Methode", data["method"], "experimental"),
                ("Pas converges", len(steps), "tous requis"),
                ("Iterations max", max(row["iterations"] for row in steps), "<= max_iterations"),
                ("Residu relatif final", steps[-1]["relative_residual"], "<= tolerance"),
                ("Etats materiau committes", len(final_states), "chemin-dependants"),
                ("Verdict engineering", data["run_verdict"], "WARNING attendu"),
            ],
        )
        self._record(
            "DOC-NONLINEAR-J2-001",
            "Non-lineaire",
            model_path,
            model,
            data,
            "experimental",
            "convergence et tangente FD; aucune aptitude materiau revendiquee",
        )
        tet10_campaign = J2StructuralCyclicCampaign(
            self.generated / "tet10_nonlinear_j2",
            element_type="TET10",
        )
        tet10_summary = tet10_campaign.run()
        if tet10_summary["status"] != "PASS_INTERNAL":
            raise RuntimeError("TET10 committed-state J2 documentation evidence did not pass.")
        shutil.copy2(
            self.generated / "tet10_nonlinear_j2" / "cyclic_response.png",
            self.assets / "tet10_j2_cyclic_response.png",
        )

    def _build_large_model(self) -> None:
        model_path = self.models / "large_block_documentation.npz"
        model = generate_large_tet4_block(model_path, nx=4, ny=3, nz=3, length=4.0, height=1.0, depth=1.0)
        result = solve_large_model(model, self.generated / "large_run", solver_backend="matrix_free", chunk_size=256)
        data = result.to_dict()
        write_json(self.results / "large_block_documentation.json", data)
        solver = data["summary"]["solver"]
        sizes = [24, model.ndof, 1_000_000]
        memory = [24 * 8 * 30, data["summary"]["estimated_core_memory_bytes"], 1_000_000 * 8 * 8]
        plot_line_series(
            self.assets / "large_model_summary.png",
            [{"x": sizes, "y": memory, "label": "ordre de grandeur memoire coeur"}],
            title="Croissance de la memoire minimale documentee",
            xlabel="Nombre de ddl",
            ylabel="Octets (estimation, hors preconditionneur)",
            yscale="log",
        )
        write_markdown_table(
            self.generated / "large_model_results.md",
            ("Grandeur", "Valeur", "Interpretation"),
            [
                ("Backend", data["backend"], "matrix-free structure"),
                ("Noeuds / elements / ddl", f"{model.node_count} / {model.element_count} / {model.ndof}", "cas documentaire"),
                ("Iterations", solver["iterations"], "CG"),
                ("Residu", solver["residual_norm"], "controle solveur"),
                ("Memoire coeur estimee [octets]", data["summary"]["estimated_core_memory_bytes"], "hors environnement"),
                ("Jalon 1M", "non execute par le site", "campagne PETSc separee"),
            ],
        )
        synthetic = _LargeDocumentationModel(model)
        self._record(
            "DOC-LARGE-BLOCK-001",
            "Grand modele",
            model_path,
            synthetic,
            {"analysis": "linear_static", "method": "matrix_free", "run_verdict": data["status"], "qualification_summary": {"maturity": {"overall": "experimental"}}},
            "cross_backend_invariant",
            "residu fini et sorties fichier; 1M non execute",
        )

    def _record(
        self,
        case_id: str,
        family: str,
        model_path: Path,
        model: object,
        data: dict[str, Any],
        reference_type: str,
        acceptance: str,
    ) -> None:
        qualification = data.get("qualification_summary", {})
        maturity = qualification.get("maturity", {}).get("overall", "experimental")
        self.records.append(
            DemoRecord(
                case_id=case_id,
                family=family,
                model_path=model_path.resolve().relative_to(self.root).as_posix(),
                input_sha256=sha256(model_path),
                analysis=str(data.get("analysis", getattr(getattr(model, "analysis", None), "type", ""))),
                method=str(data.get("method", getattr(getattr(model, "analysis", None), "method", ""))),
                verdict=str(data.get("run_verdict", data.get("status", "UNKNOWN"))),
                maturity=str(maturity),
                reference_type=reference_type,
                acceptance=acceptance,
            )
        )
class _LargeDocumentationModel:
    def __init__(self, model: object) -> None:
        self.analysis, self.node_count = AnalysisSettings.from_raw({"type": "linear_static", "method": "cg"}), model.node_count
def _family(model: object) -> str:
    types = sorted({str(element.type) for element in model.elements})
    return "+".join(types)


def _vector(values: Any) -> str:
    return "[" + ", ".join(f"{float(value):.6g}" for value in values) + "]"
