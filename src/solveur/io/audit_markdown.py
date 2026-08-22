"""Write reader-oriented white-box audit Markdown reports."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class AuditMarkdownWriter:
    """Serialize a solver audit into a compact engineering report."""

    def write(self, source: object, path: str | Path) -> None:
        audit = getattr(source, "audit", source)
        if audit is None or not hasattr(audit, "to_dict"):
            raise ValueError("Object does not contain a solver audit.")
        source_data = source.to_dict() if hasattr(source, "to_dict") else {}
        solver = source_data.get("solver", {}) if isinstance(source_data, dict) else {}
        verdict = source_data.get("qualification_summary", {}) if isinstance(source_data, dict) else {}
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.render(audit.to_dict(), solver=solver, verdict=verdict), encoding="utf-8")

    def render(
        self,
        data: dict[str, Any],
        *,
        solver: dict[str, Any] | None = None,
        verdict: dict[str, Any] | None = None,
    ) -> str:
        lines: list[str] = ["# Audit boite blanche du solveur", ""]
        self._summary(lines, data, verdict or {})
        self._solver(lines, solver or {})
        self._checks(lines, data.get("checks", []))
        self._mesh(lines, data)
        self._boundary(lines, data)
        self._loads(lines, data.get("load_assembly", {}))
        self._matrices(lines, data.get("matrices", []), "Matrices globales")
        self._equilibrium(lines, data.get("equilibrium", {}))
        self._elements(lines, data.get("element_audits", []))
        self._post_results(lines, data.get("post_results", []))
        self._notes(lines, data.get("notes", []))
        return "\n".join(lines).rstrip() + "\n"

    def _summary(self, lines: list[str], data: dict[str, Any], verdict: dict[str, Any]) -> None:
        rows = [
            ("Analyse", data.get("analysis", "")),
            ("Methode", data.get("method", "")),
            ("Verdict global", verdict.get("run_verdict", verdict.get("status", ""))),
            ("Version solveur", data.get("qualification", {}).get("solver_version", "")),
            ("Schema JSON", data.get("qualification", {}).get("schema_version", "")),
            ("Profil verification", data.get("qualification", {}).get("verification_profile", "")),
            ("Unites", _join_mapping(data.get("qualification", {}).get("units", {}))),
            ("Maturite", data.get("qualification", {}).get("maturity", {}).get("overall", "")),
            ("Niveau de preuve", data.get("qualification", {}).get("evidence_level", "")),
            ("Statut maillage", data.get("mesh_status", "")),
            ("Noeuds", data.get("node_count", 0)),
            ("Elements", data.get("element_count", 0)),
            ("DDL", data.get("ndof", 0)),
            ("Types elements", _join_mapping(data.get("element_types", {}))),
            ("Materiaux", ", ".join(data.get("material_names", []))),
        ]
        lines.extend(["## Synthese", "", "| Champ | Valeur |", "| --- | --- |"])
        lines.extend(f"| {label} | {_cell(value)} |" for label, value in rows)
        lines.append("")

    def _solver(self, lines: list[str], solver: dict[str, Any]) -> None:
        if not solver or "method" not in solver:
            return
        rows = [
            ("Methode", solver.get("method", "")),
            ("Converge", solver.get("converged", "")),
            ("Iterations", solver.get("iterations", "")),
            ("Preconditionneur", solver.get("preconditioner", "")),
            ("Residu final", solver.get("residual_norm", "")),
        ]
        lines.extend(["## Solveur numerique", "", "| Champ | Valeur |", "| --- | ---: |"])
        lines.extend(f"| {label} | {_sci(value)} |" for label, value in rows)
        history = solver.get("residual_history", [])
        if history:
            lines.extend(["", "### Historique des residus", "", "| Iteration | Residu |", "| ---: | ---: |"])
            for index, value in enumerate(history):
                lines.append(f"| {index + 1} | {_sci(value)} |")
        lines.append("")

    def _checks(self, lines: list[str], checks: list[dict[str, Any]]) -> None:
        if not checks:
            return
        counts = {"PASS": 0, "WARNING": 0, "FAIL": 0}
        for check in checks:
            status = str(check.get("status", ""))
            if status in counts:
                counts[status] += 1
        lines.extend(["## Controles automatiques", ""])
        lines.append(
            f"PASS: {counts['PASS']} | WARNING: {counts['WARNING']} | FAIL: {counts['FAIL']}"
        )
        lines.extend(["", "| Statut | Controle | Valeur | Limite | Message |", "| --- | --- | ---: | --- | --- |"])
        for check in checks:
            lines.append(
                "| {status} | {name} | {value} | {limit} | {message} |".format(
                    status=_cell(check.get("status", "")),
                    name=_cell(check.get("name", "")),
                    value=_sci(check.get("value", "")),
                    limit=_cell(check.get("limit", "")),
                    message=_cell(check.get("message", "")),
                )
            )
        lines.append("")

    def _mesh(self, lines: list[str], data: dict[str, Any]) -> None:
        lines.extend(["## Maillage", ""])
        self._message_list(lines, "Erreurs", data.get("mesh_errors", []))
        self._message_list(lines, "Avertissements", data.get("mesh_warnings", []))
        details = data.get("mesh_details", {})
        if details:
            lines.extend(
                [
                    "### Topologie",
                    "",
                    f"- Composantes connectees: {details.get('component_count', 0)}",
                    f"- Noeuds isoles: {_short_list(details.get('isolated_nodes', []))}",
                    "",
                ]
            )
            components = details.get("components", [])
            if components:
                lines.extend(
                    [
                        "| # | Noeuds | Elements | DDL fixes | Noeuds translation fixes | Charges |",
                        "| ---: | --- | --- | ---: | ---: | ---: |",
                    ]
                )
                for component in components:
                    lines.append(
                        "| {index} | {nodes} | {elements} | {fixed} | {fixed_nodes} | {loads} |".format(
                            index=component.get("index", ""),
                            nodes=_short_list(component.get("nodes", []), limit=12),
                            elements=_short_list(component.get("elements", []), limit=12),
                            fixed=component.get("fixed_dof_count", 0),
                            fixed_nodes=component.get("fixed_translation_node_count", 0),
                            loads=component.get("load_count", 0),
                        )
                    )
                lines.append("")

    def _boundary(self, lines: list[str], data: dict[str, Any]) -> None:
        boundary = data.get("boundary", {})
        if not boundary:
            return
        fixed = boundary.get("fixed_indices", [])
        free = boundary.get("free_indices", [])
        lines.extend(["## DDL et conditions aux limites", ""])
        lines.extend(
            [
                f"- DDL fixes: {boundary.get('fixed_dof_count', 0)}",
                f"- DDL libres: {boundary.get('free_dof_count', 0)}",
                f"- Indices fixes: {_short_list(fixed)}",
                f"- Indices libres: {_short_list(free)}",
                "",
            ]
        )

    def _loads(self, lines: list[str], loads: dict[str, Any]) -> None:
        if not loads:
            return
        lines.extend(
            [
                "## Bilan des chargements",
                "",
                f"- Charges nodales: {loads.get('nodal_load_count', 0)}",
                f"- Charges reparties: {loads.get('distributed_load_count', 0)}",
                f"- Resultante globale: {_short_list(loads.get('resultant', []))}",
                f"- Moment a l'origine: {_short_list(loads.get('moment_about_origin', []))}",
                "",
            ]
        )
        contributions = loads.get("contributions", [])
        if not contributions:
            return
        lines.extend(
            [
                "| # | Type | Elements | Resultante | Moment origine | Norme | DDL non nuls |",
                "| ---: | --- | --- | --- | --- | ---: | ---: |",
            ]
        )
        for contribution in contributions:
            lines.append(
                "| {index} | {kind} | {elements} | {resultant} | {moment} | {norm} | {count} |".format(
                    index=contribution.get("index", ""),
                    kind=_cell(contribution.get("type", "")),
                    elements=_short_list(contribution.get("element_indices", [])),
                    resultant=_short_list(contribution.get("resultant", [])),
                    moment=_short_list(contribution.get("moment_about_origin", [])),
                    norm=_sci(contribution.get("vector_norm", 0.0)),
                    count=contribution.get("nonzero_dof_count", 0),
                )
            )
        lines.append("")

    def _matrices(self, lines: list[str], matrices: list[dict[str, Any]], title: str) -> None:
        if not matrices:
            return
        lines.extend(
            [
                f"## {title}",
                "",
                "| Nom | Taille | nnz | Densite | Norme | Symetrique | Rang | Cond. | Def. pos. |",
                "| --- | --- | ---: | ---: | ---: | --- | ---: | ---: | --- |",
            ]
        )
        for matrix in matrices:
            lines.append(
                "| {name} | {shape} | {nnz} | {density} | {norm} | {sym} | {rank} | {cond} | {pd} |".format(
                    name=_cell(matrix.get("name", "")),
                    shape=_shape(matrix.get("shape", [])),
                    nnz=matrix.get("nnz", 0),
                    density=_sci(matrix.get("density", 0.0)),
                    norm=_sci(matrix.get("data_norm", 0.0)),
                    sym="oui" if matrix.get("is_symmetric") else "non",
                    rank=matrix.get("rank_estimate", ""),
                    cond=_sci(matrix.get("condition_estimate", "")),
                    pd=_yes_no(matrix.get("positive_definite_estimate", "")),
                )
            )
        lines.append("")

    def _equilibrium(self, lines: list[str], equilibrium: dict[str, Any]) -> None:
        if not equilibrium:
            lines.extend(["## Equilibre", "", "Pas de bilan d'equilibre: le modele a ete inspecte sans resolution.", ""])
            return
        rows = [
            ("Facteur de charge", equilibrium.get("load_factor", 1.0)),
            ("Norme residu libre", equilibrium.get("free_residual_norm", 0.0)),
            ("Residu relatif libre", equilibrium.get("free_relative_residual", 0.0)),
            ("Norme reactions", equilibrium.get("fixed_reaction_norm", 0.0)),
            ("Norme force externe", equilibrium.get("external_load_norm", 0.0)),
            ("Norme force interne", equilibrium.get("internal_force_norm", 0.0)),
            ("Travail externe final", equilibrium.get("external_work_at_final_load", 0.0)),
            ("Energie interne secante", equilibrium.get("secant_internal_energy", 0.0)),
            ("Erreur energie lineaire", equilibrium.get("linear_energy_identity_relative_error", 0.0)),
        ]
        lines.extend(["## Equilibre", "", equilibrium.get("sign_convention", ""), ""])
        lines.extend(["| Grandeur | Valeur |", "| --- | ---: |"])
        lines.extend(f"| {label} | {_sci(value)} |" for label, value in rows)
        lines.append("")
        self._reactions(lines, equilibrium.get("reactions", []))

    def _reactions(self, lines: list[str], reactions: list[dict[str, Any]]) -> None:
        if not reactions:
            return
        lines.extend(["### Reactions", "", "| Index | Noeud | DDL | Valeur |", "| ---: | ---: | --- | ---: |"])
        for item in reactions[:40]:
            lines.append(
                f"| {item.get('index', '')} | {item.get('node', '')} | {_cell(item.get('dof', ''))} | {_sci(item.get('value', 0.0))} |"
            )
        if len(reactions) > 40:
            lines.append(f"| ... | ... | ... | {len(reactions) - 40} reactions masquees |")
        lines.append("")

    def _elements(self, lines: list[str], elements: list[dict[str, Any]]) -> None:
        if not elements:
            return
        lines.extend(["## Elements", "", "| # | Type | Materiau | Noeuds | Volume/Aire | Qualite | Matrice locale | Norme | Rang |", "| ---: | --- | --- | --- | ---: | ---: | --- | ---: | ---: |"])
        for element in elements:
            geometry = element.get("geometry", {})
            matrix = next(iter(element.get("matrices", [])), {})
            measure = geometry.get("signed_corner_volume", geometry.get("area", ""))
            quality = geometry.get("corner_quality", "")
            lines.append(
                "| {index} | {etype} | {material} | {nodes} | {measure} | {quality} | {mname} | {norm} | {rank} |".format(
                    index=element.get("index", ""),
                    etype=_cell(element.get("type", "")),
                    material=_cell(element.get("material", "")),
                    nodes=_short_list(element.get("nodes", []), limit=12),
                    measure=_sci(measure) if measure != "" else "",
                    quality=_sci(quality) if quality != "" else "",
                    mname=_cell(matrix.get("name", "")),
                    norm=_sci(matrix.get("data_norm", 0.0)),
                    rank=matrix.get("rank_estimate", ""),
                )
            )
        lines.append("")

    def _post_results(self, lines: list[str], results: list[dict[str, Any]]) -> None:
        if not results:
            return
        lines.extend(
            [
                "## Post-traitement par element",
                "",
                "| # | Type | Repere calcul | DDL globaux | Norme u calcul | Sorties |",
                "| ---: | --- | --- | --- | ---: | --- |",
            ]
        )
        output_keys = (
            "strain",
            "stress",
            "von_mises",
            "membrane_strain",
            "curvature",
            "shear_strain",
            "membrane_force",
            "bending_moment",
            "shear_force",
        )
        for result in results:
            available = [key for key in output_keys if key in result]
            lines.append(
                "| {index} | {etype} | {frame} | {dofs} | {norm} | {outputs} |".format(
                    index=result.get("element", ""),
                    etype=_cell(result.get("type", "")),
                    frame=_cell(result.get("calculation_frame", "")),
                    dofs=_short_list(result.get("global_dof_indices", []), limit=12),
                    norm=_sci(result.get("calculation_displacement_norm", 0.0)),
                    outputs=", ".join(available),
                )
            )
        lines.append("")

    def _notes(self, lines: list[str], notes: list[str]) -> None:
        if notes:
            lines.extend(["## Notes", ""])
            lines.extend(f"- {note}" for note in notes)
            lines.append("")

    @staticmethod
    def _message_list(lines: list[str], title: str, messages: list[str]) -> None:
        lines.append(f"### {title}")
        if messages:
            lines.extend(f"- {message}" for message in messages)
        else:
            lines.append("- Aucun.")
        lines.append("")


def _cell(value: object) -> str:
    return str(value).replace("|", "\\|")


def _sci(value: object) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.6e}"
    return _cell(value)


def _shape(shape: object) -> str:
    if isinstance(shape, list) and len(shape) == 2:
        return f"{shape[0]} x {shape[1]}"
    return _cell(shape)


def _yes_no(value: object) -> str:
    if value is True:
        return "oui"
    if value is False:
        return "non"
    return _cell(value)


def _short_list(values: object, limit: int = 24) -> str:
    if not isinstance(values, list):
        return _cell(values)
    shown = values[:limit]
    text = ", ".join(str(value) for value in shown)
    if len(values) > limit:
        text += f", ... (+{len(values) - limit})"
    return text


def _join_mapping(values: object) -> str:
    if not isinstance(values, dict):
        return _cell(values)
    return ", ".join(f"{key}: {value}" for key, value in values.items())
