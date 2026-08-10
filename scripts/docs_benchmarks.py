"""Generate figures and tables for the controlled meshed benchmark catalog."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from scripts.docs_fields import publish_benchmark_fields
from scripts.docs_support import (
    markdown_value,
    plot_deformed_model,
    write_json,
)
from solveur.api import list_benchmarks, load_model, run_benchmark
from solveur.io.manifest import sha256


PRIMARY_PREFIX = {
    "BM-BEAM2-CANTILEVER-001": "static_n16",
    "BM-SOL-TET4-PATCH-001": "result",
    "BM-SOL-TET4-MEMBRANE-001": "traction_h5",
    "BM-SOL-TET4-TORSION-001": "h8",
    "BM-SOL-CANTILEVER-001": "tet10",
    "BM-SOL-TET10-LAME-001": "result",
    "BM-SHL-COOK-001": "result",
    "BM-SHL-SCORDELIS-001": "result",
    "BM-SHL-PINCHED-001": "result",
    "BM-DYN-CANTILEVER-001": "static",
    "BM-NL-J2-BAR-001": "result",
}


class MeshedBenchmarkDocumenter:
    """Execute all controlled benchmarks and derive publication-only assets."""

    def __init__(
        self,
        project_root: str | Path,
        output_root: str | Path,
        asset_root: str | Path,
        *,
        profile: str,
    ) -> None:
        self.root = Path(project_root).resolve()
        self.output = Path(output_root).resolve()
        self.assets = Path(asset_root).resolve()
        self.profile = profile

    def build(self) -> list[dict[str, Any]]:
        """Run every case, fail on acceptance errors, and return demo records."""
        self.output.mkdir(parents=True, exist_ok=True)
        self.assets.mkdir(parents=True, exist_ok=True)
        records: list[dict[str, Any]] = []
        campaign_rows: list[dict[str, Any]] = []
        for descriptor in list_benchmarks():
            run = run_benchmark(descriptor.identifier, self.output, profile=self.profile)
            if any(check["status"] != "PASS" for check in run.checks):
                raise RuntimeError(f"Meshed benchmark {descriptor.identifier} failed its controlled criteria.")
            expected = "WARNING" if descriptor.maturity in {"experimental", "research"} else "PASS"
            if run.status != expected:
                raise RuntimeError(
                    f"Meshed benchmark {descriptor.identifier} returned {run.status}; expected {expected}."
                )
            case_dir = self.output / descriptor.identifier
            prefix = PRIMARY_PREFIX[descriptor.identifier]
            model_path = case_dir / f"{prefix}.model.json"
            result_path = case_dir / f"{prefix}.json"
            mesh_path = _first_mesh(case_dir, prefix, fallback=model_path)
            setup_path = case_dir / f"{prefix}.setup.json"
            if not setup_path.is_file():
                setup_path = model_path
            model = load_model(model_path)
            result_data = json.loads(result_path.read_text(encoding="utf-8"))
            result = _result_adapter(model, result_data)
            slug = descriptor.identifier.lower()
            deformation_path = self.assets / f"{slug}_deformation.png"
            checks_path = self.assets / f"{slug}_checks.png"
            scale = plot_deformed_model(
                model,
                result,
                deformation_path,
                title=descriptor.title,
                color_label="Norme du deplacement [unite du modele]",
            )
            field_report = publish_benchmark_fields(
                model,
                result,
                result_data,
                self.assets / slug,
                descriptor.title,
                scale,
            )
            if descriptor.identifier == "BM-SOL-TET4-MEMBRANE-001":
                _write_compression_figures(case_dir, self.assets, descriptor.title)
            _plot_checks(run.checks, checks_path, descriptor.title)
            table_path = self.output / f"{slug}_results.md"
            _write_case_table(
                table_path,
                run.to_dict(),
                model,
                mesh_path,
                setup_path,
                model_path,
                result_path,
                scale,
            )
            _plot_special_case(run.to_dict(), case_dir, self.assets / f"{slug}_response.png")
            records.append(
                {
                    "case_id": descriptor.identifier,
                    "family": descriptor.family,
                    "model_path": model_path.relative_to(self.root).as_posix(),
                    "input_sha256": sha256(model_path),
                    "analysis": "+".join(descriptor.analyses),
                    "method": "controlled_campaign",
                    "verdict": run.status,
                    "maturity": descriptor.maturity,
                    "reference_type": descriptor.reference_type,
                    "acceptance": "; ".join(
                        f"{check['id']} {_operator_symbol(check)} {check['limit']:.6e}" for check in run.checks
                    ),
                }
            )
            campaign_rows.append(
                {
                    "id": descriptor.identifier,
                    "status": run.status,
                    "maturity": descriptor.maturity,
                    "mesh_sha256": sha256(mesh_path),
                    "result_sha256": sha256(result_path),
                    "checks": run.checks,
                    "field_artifacts": field_report["fields"],
                }
            )
        write_json(
            self.output / "campaign_summary.json",
            {"profile": self.profile, "status": "PASS", "case_count": len(campaign_rows), "cases": campaign_rows},
        )
        return records


def _result_adapter(model: object, data: dict[str, Any]) -> SimpleNamespace:
    dofs = model.dof_manager()
    vector = np.zeros(dofs.ndof, dtype=float)
    for row in data["displacements"]:
        node = int(row["node"])
        for name, value in row["dofs"].items():
            if dofs.has(node, name):
                vector[dofs.index(node, name)] = float(value)
    return SimpleNamespace(displacements=vector, dofs=dofs)


def _write_compression_figures(case_dir: Path, assets: Path, title: str) -> None:
    model = load_model(case_dir / "compression_h5.model.json")
    data = json.loads((case_dir / "compression_h5.json").read_text(encoding="utf-8"))
    result = _result_adapter(model, data)
    deformation = assets / "bm-sol-tet4-membrane-001_compression_deformation.png"
    scale = plot_deformed_model(
        model,
        result,
        deformation,
        title=f"{title} - compression",
        color_label="Norme du deplacement [unite du modele]",
    )
    publish_benchmark_fields(
        model,
        result,
        data,
        assets / "bm-sol-tet4-membrane-001_compression",
        f"{title} - compression",
        scale,
    )


def _first_mesh(case_dir: Path, prefix: str, *, fallback: Path) -> Path:
    preferred = sorted(case_dir.glob(f"{prefix}*.msh"))
    if not preferred and "_h" in prefix:
        preferred = sorted(case_dir.glob(f"{prefix.rsplit('_', 1)[-1]}*.msh"))
    candidates = preferred or sorted(case_dir.glob("*.msh"))
    if not candidates:
        return fallback
    return candidates[0]


def _plot_checks(checks: list[dict[str, Any]], output: Path, title: str) -> None:
    labels = [str(check["id"]) for check in checks]
    ratios = []
    for check in checks:
        value = max(float(check["value"]), 1.0e-300)
        limit = max(float(check["limit"]), 1.0e-300)
        ratio = limit / value if check.get("operator") == "greater_equal" else value / limit
        ratios.append(max(ratio, 1.0e-16))
    fig, axis = plt.subplots(figsize=(9.2, 5.2))
    positions = np.arange(len(labels))
    axis.bar(positions, ratios, color=["#18794e" if ratio <= 1.0 else "#b42318" for ratio in ratios])
    axis.axhline(1.0, color="#1f2933", linewidth=1.2, linestyle="--", label="limite d'acceptation")
    axis.set_yscale("log")
    axis.set_xticks(positions, labels, rotation=18, ha="right")
    axis.set_ylabel("Critere normalise (<= 1 accepte)")
    axis.set_title(f"{title} - criteres normalises")
    axis.grid(True, axis="y", which="both", color="#d5dadd", linewidth=0.6)
    axis.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output, dpi=180, bbox_inches="tight")
    plt.close(fig)


def _write_case_table(
    path: Path,
    run: dict[str, Any],
    model: object,
    mesh_path: Path,
    setup_path: Path,
    model_path: Path,
    result_path: Path,
    scale: float,
) -> None:
    lines = [
        "## Resultats regeneres",
        "",
        "| Propriete | Valeur |",
        "| --- | --- |",
        f"| Verdict | {run['status']} |",
        f"| Noeuds | {model.node_count} |",
        f"| Elements | {len(model.elements)} |",
        f"| Amplification graphique | {markdown_value(scale)} |",
        f"| Empreinte maillage/source | `{sha256(mesh_path)}` |",
        f"| Empreinte configuration/source | `{sha256(setup_path)}` |",
        f"| Empreinte modele | `{sha256(model_path)}` |",
        f"| Empreinte resultat | `{sha256(result_path)}` |",
        "",
        "### Criteres d'acceptation",
        "",
        "| Critere | Operateur | Valeur | Limite | Verdict |",
        "| --- | :---: | ---: | ---: | --- |",
    ]
    lines.extend(
        f"| {check['id']} | {_operator_symbol(check)} | {markdown_value(check['value'])} | "
        f"{markdown_value(check['limit'])} | {check['status']} |"
        for check in run["checks"]
    )
    lines.extend(["", "### Metriques principales", "", "| Metrique | Valeur |", "| --- | --- |"])
    for name, value in run["metrics"].items():
        if isinstance(value, (str, int, float, bool)):
            lines.append(f"| {name} | {markdown_value(value)} |")
        elif isinstance(value, list) and len(value) <= 12 and all(isinstance(item, (int, float, str)) for item in value):
            lines.append(f"| {name} | {markdown_value(value)} |")
    convergence = run["metrics"].get("tet4_h_convergence")
    if isinstance(convergence, list):
        lines.extend(
            [
                "",
                "### Convergence h TET4 calculee",
                "",
                "| Niveau | h nominal [m] | Noeuds | Elements | Uz bout [m] | Erreur relative | Residu libre |",
                "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        lines.extend(
            f"| {row['level']} | {markdown_value(row['mesh_size'])} | {row['node_count']} | "
            f"{row['element_count']} | {markdown_value(row['tip_uz'])} | "
            f"{markdown_value(row['relative_error'])} | {markdown_value(row['free_relative_residual'])} |"
            for row in convergence
        )
    beam = run["metrics"].get("convergence")
    if run["benchmark"]["identifier"] == "BM-BEAM2-CANTILEVER-001" and isinstance(beam, list):
        lines.extend(
            [
                "",
                "### Convergence BEAM2",
                "",
                "| Elements | Erreur statique | Frequence 1 [Hz] | Reference [Hz] | Erreur modale | Residu modal |",
                "| ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        lines.extend(
            f"| {row['element_count']} | {markdown_value(row['static_relative_error'])} | "
            f"{markdown_value(row['first_frequency_hz'])} | "
            f"{markdown_value(row['euler_bernoulli_frequency_hz'])} | "
            f"{markdown_value(row['modal_relative_error'])} | {markdown_value(row['modal_residual'])} |"
            for row in beam
        )
    membrane = run["metrics"].get("membrane_h_convergence")
    if isinstance(membrane, list):
        lines.extend(
            [
                "",
                "### Raffinement h du panneau membranaire",
                "",
                "| Niveau | h [m] | Noeuds | Elements | Ux face libre [m] | Erreur Ux | Erreur contrainte | Residu libre |",
                "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        lines.extend(
            f"| {row['level']} | {markdown_value(row['mesh_size'])} | {row['node_count']} | "
            f"{row['element_count']} | {markdown_value(row['mean_end_ux'])} | "
            f"{markdown_value(row['relative_displacement_error'])} | "
            f"{markdown_value(row['relative_stress_error'])} | {markdown_value(row['free_relative_residual'])} |"
            for row in membrane
        )
    compression = run["metrics"].get("compression_h_convergence")
    if isinstance(compression, list):
        lines.extend(
            [
                "",
                "### Raffinement h du panneau en compression",
                "",
                "| Niveau | h [m] | Noeuds | Elements | Ux face libre [m] | Erreur Ux | Erreur contrainte | Residu libre |",
                "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        lines.extend(
            f"| {row['level']} | {markdown_value(row['mesh_size'])} | {row['node_count']} | "
            f"{row['element_count']} | {markdown_value(row['mean_end_ux'])} | "
            f"{markdown_value(row['relative_displacement_error'])} | "
            f"{markdown_value(row['relative_stress_error'])} | {markdown_value(row['free_relative_residual'])} |"
            for row in compression
        )
    torsion = run["metrics"].get("torsion_h_convergence")
    if isinstance(torsion, list):
        lines.extend(
            [
                "",
                "### Convergence h en torsion",
                "",
                "| Niveau | h [m] | Noeuds | Elements | Rotation [rad] | Erreur rotation | Erreur contraintes L2 | Couple [N.m] | Residu libre |",
                "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        lines.extend(
            f"| {row['level']} | {markdown_value(row['mesh_size'])} | {row['node_count']} | "
            f"{row['element_count']} | {markdown_value(row['twist_angle'])} | "
            f"{markdown_value(row['relative_twist_error'])} | {markdown_value(row['relative_stress_l2_error'])} | "
            f"{markdown_value(row['applied_torque'])} | {markdown_value(row['free_relative_residual'])} |"
            for row in torsion
        )
    conclusion = _case_conclusion(run)
    if conclusion:
        lines.extend(["", "### Conclusion automatique", "", conclusion])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _plot_special_case(run: dict[str, Any], case_dir: Path, output: Path) -> None:
    identifier = run["benchmark"]["identifier"]
    if identifier == "BM-BEAM2-CANTILEVER-001":
        rows = run["metrics"]["convergence"]
        counts = np.asarray([row["element_count"] for row in rows], dtype=float)
        errors = np.asarray([row["modal_relative_error"] for row in rows], dtype=float)
        fig, axis = plt.subplots(figsize=(9.2, 5.2))
        axis.loglog(counts, errors, marker="o", color="#155e75", label="Erreur frequence 1")
        axis.set_xlabel("Nombre d'elements BEAM2")
        axis.set_ylabel("Erreur relative")
        axis.set_title("Convergence modale BEAM2 vers Euler-Bernoulli")
        axis.grid(True, which="both", color="#d5dadd", linewidth=0.6)
        axis.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(output, dpi=180, bbox_inches="tight")
        plt.close(fig)
    elif identifier == "BM-SOL-CANTILEVER-001":
        rows = run["metrics"]["tet4_h_convergence"]
        sizes = np.asarray([row["mesh_size"] for row in rows], dtype=float)
        errors = np.asarray([row["relative_error"] for row in rows], dtype=float)
        fig, axis = plt.subplots(figsize=(9.2, 5.2))
        axis.loglog(sizes, errors, marker="o", color="#155e75", label="Erreur de fleche TET4")
        axis.set_xlabel("Taille nominale h [m]")
        axis.set_ylabel("Erreur relative sur Uz bout")
        axis.set_title(f"Convergence h TET4 - ordre observe p={run['metrics']['tet4_h_observed_order']:.3f}")
        axis.grid(True, which="both", color="#d5dadd", linewidth=0.6)
        axis.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(output, dpi=180, bbox_inches="tight")
        plt.close(fig)
    elif identifier == "BM-SOL-TET4-MEMBRANE-001":
        _plot_axial_convergence(run["metrics"], output)
    elif identifier == "BM-SOL-TET4-TORSION-001":
        rows = run["metrics"]["torsion_h_convergence"]
        _plot_two_error_convergence(
            rows,
            output,
            title=f"Torsion TET4 - ordre rotation p={run['metrics']['observed_order']:.3f}",
            first=("relative_twist_error", "Erreur rotation"),
            second=("relative_stress_l2_error", "Erreur contraintes L2"),
        )
    elif identifier == "BM-DYN-CANTILEVER-001":
        metrics = run["metrics"]
        fig, axis = plt.subplots(figsize=(9.2, 5.2))
        axis.plot(
            metrics["harmonic_frequencies_hz"],
            metrics["harmonic_tip_amplitudes"],
            marker="o",
            color="#155e75",
        )
        axis.set_xlabel("Frequence [Hz]")
        axis.set_ylabel("Amplitude UZ au point de mesure")
        axis.set_title("Reponse harmonique du porte-a-faux maille")
        axis.grid(True, color="#d5dadd", linewidth=0.6)
        fig.tight_layout()
        fig.savefig(output, dpi=180, bbox_inches="tight")
        plt.close(fig)
    elif identifier == "BM-NL-J2-BAR-001":
        data = json.loads((case_dir / "result.json").read_text(encoding="utf-8"))
        steps = data["solver"]["steps"]
        fig, axis = plt.subplots(figsize=(9.2, 5.2))
        axis.semilogy(
            [step["step"] for step in steps],
            [max(float(step["relative_residual"]), 1.0e-18) for step in steps],
            marker="o",
            color="#b94b22",
        )
        axis.set_xlabel("Increment de charge")
        axis.set_ylabel("Residu relatif final")
        axis.set_title("Convergence Newton de la barre J2")
        axis.grid(True, which="both", color="#d5dadd", linewidth=0.6)
        fig.tight_layout()
        fig.savefig(output, dpi=180, bbox_inches="tight")
        plt.close(fig)


def _operator_symbol(check: dict[str, Any]) -> str:
    return ">=" if check.get("operator") == "greater_equal" else "<="


def _plot_two_error_convergence(
    rows: list[dict[str, Any]],
    output: Path,
    *,
    title: str,
    first: tuple[str, str],
    second: tuple[str, str],
) -> None:
    sizes = np.asarray([row["mesh_size"] for row in rows], dtype=float)
    fig, axis = plt.subplots(figsize=(9.2, 5.2))
    axis.loglog(sizes, [row[first[0]] for row in rows], marker="o", color="#155e75", label=first[1])
    axis.loglog(sizes, [row[second[0]] for row in rows], marker="s", color="#b94b22", label=second[1])
    axis.set_xlabel("Taille nominale h [m]")
    axis.set_ylabel("Erreur relative")
    axis.set_title(title)
    axis.grid(True, which="both", color="#d5dadd", linewidth=0.6)
    axis.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output, dpi=180, bbox_inches="tight")
    plt.close(fig)


def _plot_axial_convergence(metrics: dict[str, Any], output: Path) -> None:
    traction = metrics["membrane_h_convergence"]
    compression = metrics["compression_h_convergence"]
    sizes = np.asarray([row["mesh_size"] for row in traction], dtype=float)
    fig, axis = plt.subplots(figsize=(9.2, 5.2))
    series = (
        (traction, "relative_displacement_error", "Traction - deplacement", "o", "#155e75"),
        (traction, "relative_stress_error", "Traction - contrainte", "s", "#007f7b"),
        (compression, "relative_displacement_error", "Compression - deplacement", "^", "#b94b22"),
        (compression, "relative_stress_error", "Compression - contrainte", "d", "#7c3f00"),
    )
    for rows, key, label, marker, color in series:
        axis.loglog(sizes, [row[key] for row in rows], marker=marker, color=color, label=label)
    axis.set_xlabel("Taille nominale h [m]")
    axis.set_ylabel("Erreur relative")
    axis.set_title("Panneau mince TET4 - traction et compression affines")
    axis.grid(True, which="both", color="#d5dadd", linewidth=0.6)
    axis.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output, dpi=180, bbox_inches="tight")
    plt.close(fig)


def _case_conclusion(run: dict[str, Any]) -> str:
    identifier = run["benchmark"]["identifier"]
    metrics = run["metrics"]
    if identifier == "BM-SOL-CANTILEVER-001":
        rows = metrics["tet4_h_convergence"]
        return (
            "La fleche TET4 converge de facon monotone: l'erreur passe de "
            f"`{rows[0]['relative_error']:.3%}` a `{rows[-1]['relative_error']:.3%}` sur six maillages, "
            f"avec un ordre observe de `{metrics['tet4_h_observed_order']:.3f}`. Le critere de deplacement est "
            "satisfait dans l'intervalle teste; cette conclusion ne qualifie pas une contrainte locale de bord."
        )
    if identifier == "BM-SOL-TET4-MEMBRANE-001":
        return (
            "Les cinq maillages de traction et les cinq maillages de compression reproduisent le champ affine "
            f"a l'arrondi pres: erreur deplacement maximale `{metrics['max_relative_displacement_error']:.3e}` "
            f"et erreur contrainte maximale `{metrics['max_relative_stress_error']:.3e}`. Il s'agit d'un patch "
            "d'exactitude, pas d'une estimation d'ordre asymptotique."
        )
    if identifier == "BM-SOL-TET4-TORSION-001":
        rows = metrics["torsion_h_convergence"]
        return (
            "La rotation converge monotoniquement sur huit maillages: erreur de "
            f"`{rows[0]['relative_twist_error']:.3%}` a `{rows[-1]['relative_twist_error']:.3%}`, ordre observe "
            f"`{metrics['observed_order']:.3f}`. L'erreur L2 des contraintes diminue de "
            f"`{rows[0]['relative_stress_l2_error']:.3%}` a `{rows[-1]['relative_stress_l2_error']:.3%}`, "
            "mais reste trop elevee pour qualifier les contraintes locales de torsion."
        )
    return ""
