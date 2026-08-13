"""Markdown and convergence-curve output for controlled V&V studies."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from solveur.verification.vnv_types import VnvStudyRun


def write_vnv_report(run: VnvStudyRun, path: str | Path) -> Path | None:
    """Write the mandatory Markdown study report and optional convergence plot."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    convergence_plot = _plot_convergence(run.convergence, target.parent / "convergence.png")
    target.write_text(_markdown(run, convergence_plot), encoding="utf-8")
    return convergence_plot


def _markdown(run: VnvStudyRun, convergence_plot: Path | None) -> str:
    study = run.study
    validation = study.validation
    validator = validation["validator"]
    lines = [
        "---",
        f"study_id: {study.identifier}",
        f"scope: {study.scope}",
        f"automated_verdict: {run.automated_verdict}",
        f"human_decision: {run.human_decision}",
        "---",
        "",
        f"# {study.title}",
        "",
        "## Identification",
        "",
        "| Champ | Valeur |",
        "| --- | --- |",
        f"| Etude | `{study.identifier}` |",
        f"| Perimetre | `{study.scope}` |",
        f"| Sujet | {_cell(study.subject['kind'])} `{_cell(study.subject['name'])}` |",
        f"| Maturite annoncee | `{_cell(study.subject['maturity'])}` |",
        f"| Systeme d'unites | `{_cell(study.units_system)}` |",
        f"| Auteur | {_cell(study.author['name'])} - {_cell(study.author['role'])} |",
        f"| Validateur mecanique | {_cell(validator['name'])} - {_cell(validator['role'])} |",
        f"| Mode de revue | `{validation['mode']}` ({validation['independence']}) |",
        f"| Verdict automatique | **{run.automated_verdict}** |",
        f"| Decision Owner | **{run.human_decision}** |",
        "",
        "## Reference",
        "",
        "| Champ | Valeur |",
        "| --- | --- |",
        f"| Type | `{_cell(study.reference['kind'])}` |",
        f"| Solveur/reference | {_cell(study.reference['solver'])} {_cell(study.reference['version'])} |",
        f"| Cas | {_cell(study.reference['case'])} |",
        f"| Citation | {_cell(study.reference['manual_citation'])} |",
        "",
        "## Comparaison quantitative",
        "",
        "### Definitions d'extraction",
        "",
        "| Grandeur | Localisation | Composante | Reduction | Metrique |",
        "| --- | --- | --- | --- | --- |",
    ]
    for quantity in study.quantities:
        lines.append(
            f"| `{quantity.identifier}` | {_cell(quantity.extraction['location'])} | "
            f"{_cell(quantity.extraction['component'])} | {_cell(quantity.extraction['reduction'])} | "
            f"`{quantity.metric}` |"
        )
    lines.extend(
        [
        "",
        "### Resultats",
        "",
        "| Maillage | h | Grandeur | QF_solver | Reference | Unite | Erreur absolue | Erreur relative | Limite | Verdict |",
        "| --- | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for row in run.comparisons:
        lines.append(
            "| {level} | {h:.6e} | {label} | {qf:.9e} | {reference:.9e} | {unit} | "
            "{absolute_error:.6e} | {relative_error:.6e} | {limit:.6e} | {status} |".format(
                **{**row, "label": _cell(row["label"]), "unit": _cell(row["unit"])}
            )
        )
    lines.extend(["", "## Etude de convergence", ""])
    if run.convergence:
        lines.extend(
            [
                "| Grandeur | Erreur la plus fine | Ordre observe | Monotone | Verdict |",
                "| --- | ---: | ---: | :---: | --- |",
            ]
        )
        for row in run.convergence:
            order = "exact" if row["observed_order"] is None else f"{row['observed_order']:.6f}"
            lines.append(
                f"| `{row['quantity']}` | {row['finest_error']:.6e} | {order} | "
                f"{'oui' if row['monotonic'] else 'non'} | {row['status']} |"
            )
        if convergence_plot is not None:
            lines.extend(["", "![Courbes de convergence](convergence.png)"])
    else:
        lines.append("Aucun critere de convergence n'est declare pour cette etude.")
    lines.extend(["", "## Deformees et champs", ""])
    _append_deformations(lines, run)
    lines.extend(
        [
            "",
            "## Criteres automatiques",
            "",
            "| ID | Valeur | Limite/attendu | Verdict | Detail |",
            "| --- | ---: | --- | --- | --- |",
        ]
    )
    for check in run.checks:
        value = _number(check.get("value"))
        expected = _cell(str(check.get("limit", check.get("expected", ""))))
        lines.append(
            f"| `{check['id']}` | {value} | {expected} | {check['status']} | {_cell(check.get('detail', ''))} |"
        )
    lines.extend(
        [
            "",
            "## Owner review",
            "",
            f"- Validateur : **{validator['name']}**, {validator['role']}",
            f"- Mode : `{validation['mode']}`",
            f"- Independence : `{validation['independence']}`",
            f"- Decision : `{validation['decision']}`",
            f"- Date : `{validation.get('date') or 'a renseigner'}`",
            f"- Commentaires : {_cell(validation.get('comments') or 'a renseigner')}",
            "",
        ]
    )
    if validation["mode"] == "self_review":
        lines.extend(
            [
                "> Cette revue est une auto-revue : l'auteur et le validateur sont la meme personne. "
                "Elle formalise une decision engineering mais ne constitue pas une revue independante.",
                "",
            ]
        )
    lines.extend(
        [
            "Checklist de validation :",
            "",
            "- [ ] Geometrie, maillage, orientations et conditions aux limites relus.",
            "- [ ] Unites, signes et points d'extraction verifies.",
            "- [ ] Deformees QF_solver/reference comparees visuellement.",
            "- [ ] Courbes de convergence et grandeurs energie/deplacement/contrainte relues.",
            "- [ ] Ecarts hors tolerance traites dans le registre d'anomalies.",
            f"- [{'x' if validation['decision'] != 'pending' and validation.get('date') else ' '}] "
            "Decision, date et commentaires renseignes dans `study.json`.",
            "",
            "## Fichiers de preuve",
            "",
            "| Role | Fichier | SHA-256 |",
            "| --- | --- | --- |",
        ]
    )
    for item in run.artifacts:
        lines.append(f"| {item['role']} | [{item['path']}]({item['path']}) | `{item['sha256']}` |")
    return "\n".join(lines) + "\n"


def _append_deformations(lines: list[str], run: VnvStudyRun) -> None:
    by_level: dict[str, dict[tuple[str, str], str]] = {}
    for item in run.artifacts:
        if item["artifact_key"] in {"deformation_png", "deformation_vtu"}:
            by_level.setdefault(item["level"], {})[(item["producer_role"], item["artifact_key"])] = item["path"]
    if not by_level:
        lines.append("Aucun artefact graphique n'a ete fourni.")
        return
    for level in run.study.levels:
        files = by_level.get(level.identifier, {})
        qf_png = files.get(("qf", "deformation_png"))
        ref_png = files.get(("reference", "deformation_png"))
        qf_vtu = files.get(("qf", "deformation_vtu"))
        ref_vtu = files.get(("reference", "deformation_vtu"))
        if not any((qf_png, ref_png, qf_vtu, ref_vtu)):
            continue
        lines.extend([f"### {level.identifier} - h = {level.characteristic_size:.6e}", ""])
        metadata = next((item.get("visualization", {}) for item in run.artifacts if item["level"] == level.identifier), {})
        if metadata:
            lines.append(
                f"Amplification : `{metadata['deformation_scale']:.6g}`; champ : `{metadata['field']}`; "
                f"vue : `{metadata['view']}`."
            )
            lines.append("")
        if qf_png or ref_png:
            lines.extend(["| QF_solver | Reference |", "| --- | --- |"])
            lines.append(f"| {_image(qf_png, 'Deformee QF_solver')} | {_image(ref_png, 'Deformee reference')} |")
        links = []
        if qf_vtu:
            links.append(f"[VTU QF_solver]({qf_vtu})")
        if ref_vtu:
            links.append(f"[VTU reference]({ref_vtu})")
        if links:
            lines.extend(["", " - ".join(links)])
        lines.append("")


def _plot_convergence(rows: list[dict[str, Any]], output: Path) -> Path | None:
    if not rows:
        return None
    figure, axis = plt.subplots(figsize=(8.4, 5.2))
    for row in rows:
        series = row["series"]
        sizes = [float(item["h"]) for item in series]
        errors = [max(float(item["error"]), 1.0e-300) for item in series]
        axis.loglog(sizes, errors, marker="o", linewidth=1.5, label=str(row["quantity"]))
    axis.invert_xaxis()
    axis.set_xlabel("Taille caracteristique h")
    axis.set_ylabel("Erreur par rapport a la reference")
    axis.set_title("Convergence en h")
    axis.grid(True, which="both", linewidth=0.6, color="#d5dadd")
    axis.legend()
    figure.tight_layout()
    figure.savefig(output, dpi=180, bbox_inches="tight")
    plt.close(figure)
    return output


def _image(path: str | None, label: str) -> str:
    return f"![{label}]({path})" if path else "Non fourni"


def _cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _number(value: Any) -> str:
    if isinstance(value, (float, int)):
        return f"{float(value):.6e}"
    return _cell(value if value is not None else "-")
