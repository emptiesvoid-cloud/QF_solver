"""Write reader-oriented white-box audit Markdown reports."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from solveur.core.audit import validate_audit_detail
from solveur.core.audit_checks import _post_result_checks


DEFAULT_VALUES_WARNING_ROWS = 100_000

class AuditMarkdownWriter:
    """Serialize a solver audit into a compact engineering report."""

    def __init__(self, *, values_warning_rows: int = DEFAULT_VALUES_WARNING_ROWS) -> None:
        if values_warning_rows < 0:
            raise ValueError("values_warning_rows must be non-negative.")
        self.values_warning_rows = values_warning_rows

    def write(
        self,
        source: object,
        path: str | Path,
        *,
        detail: str = "summary",
        max_pass_rows: int | None = None,
    ) -> None:
        detail = validate_audit_detail(detail)
        _validate_max_pass_rows(max_pass_rows)
        audit = getattr(source, "audit", source)
        if audit is None or not hasattr(audit, "to_dict"):
            raise ValueError("Object does not contain a solver audit.")
        try:
            audit_data = audit.to_dict(detail=detail)
        except TypeError:
            audit_data = audit.to_dict()
        solver = getattr(source, "solver", {}) if source is not audit else {}
        verdict: dict[str, Any] = {}
        if source is not audit and hasattr(source, "run_verdict"):
            run_verdict = getattr(source, "run_verdict")
            verdict["run_verdict"] = getattr(run_verdict, "value", run_verdict)
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            self.render(
                audit_data,
                solver=solver,
                verdict=verdict,
                detail=detail,
                max_pass_rows=max_pass_rows,
            ),
            encoding="utf-8",
        )

    def render(
        self,
        data: dict[str, Any],
        *,
        solver: dict[str, Any] | None = None,
        verdict: dict[str, Any] | None = None,
        detail: str | None = None,
        max_pass_rows: int | None = None,
    ) -> str:
        detail = validate_audit_detail(detail or str(data.get("detail", "summary")))
        _validate_max_pass_rows(max_pass_rows)
        lines: list[str] = ["# Audit boite blanche du solveur", ""]
        self._export_warnings(lines, data, detail=detail, max_pass_rows=max_pass_rows)
        self._summary(lines, data, verdict or {})
        self._solver(lines, solver or {})
        self._checks(
            lines,
            data.get("checks", []),
            data.get("diagnostic", {}),
            detail=detail,
            max_pass_rows=max_pass_rows,
        )
        self._mesh(lines, data)
        self._boundary(lines, data)
        self._loads(lines, data.get("load_assembly", {}), detail=detail)
        self._matrices(lines, data.get("matrices", []), "Matrices globales")
        self._equilibrium(lines, data.get("equilibrium", {}))
        if detail == "diagnostic":
            self._diagnostic(lines, data.get("diagnostic", {}))
            self._elements(lines, data.get("element_audits", []), max_pass_rows=max_pass_rows)
            self._post_results_summary(
                lines,
                data.get("post_results", []),
                total_count=data.get("diagnostic", {}).get("post_result_count"),
            )
        elif detail == "values":
            self._elements(lines, data.get("element_audits", []), max_pass_rows=max_pass_rows)
            self._post_results(lines, data.get("post_results", []), max_pass_rows=max_pass_rows)
        else:
            self._post_results_summary(
                lines,
                data.get("post_results", []),
                total_count=data.get("diagnostic", {}).get("post_result_count"),
            )
        self._notes(lines, data.get("notes", []))
        return "\n".join(lines).rstrip() + "\n"

    def _export_warnings(
        self,
        lines: list[str],
        data: dict[str, Any],
        *,
        detail: str,
        max_pass_rows: int | None,
    ) -> None:
        estimate = _estimate_rows(data, detail=detail)
        messages: list[str] = []
        if detail == "values" and estimate > self.values_warning_rows:
            messages.append(
                "Le mode `values` est exhaustif : environ "
                f"{estimate:,} lignes Markdown sont estimees (seuil d'alerte "
                f"{self.values_warning_rows:,}; O(N elements x controles))."
            )
        if max_pass_rows is not None and estimate > max_pass_rows:
            messages.append(
                f"`max_pass_rows={max_pass_rows}` limite uniquement les lignes PASS de l'export Markdown; "
                "les WARNING/FAIL restent toujours exportes."
            )
        if not messages:
            return
        lines.extend(["## Avertissements d'export", ""])
        lines.extend(f"- {message}" for message in messages)
        lines.append("")

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

    def _checks(
        self,
        lines: list[str],
        checks: list[dict[str, Any]],
        diagnostic: dict[str, Any],
        *,
        detail: str,
        max_pass_rows: int | None,
    ) -> None:
        counts = {"PASS": 0, "WARNING": 0, "FAIL": 0}
        for check in checks:
            status = str(check.get("status", ""))
            if status in counts:
                counts[status] += 1
        stored_counts = diagnostic.get("automatic_checks", {})
        if detail in {"summary", "diagnostic"} and stored_counts:
            counts = {status: int(stored_counts.get(status, counts[status])) for status in counts}
        if not checks and not stored_counts:
            return
        lines.extend(["## Controles automatiques", ""])
        lines.append(
            f"PASS: {counts['PASS']} | WARNING: {counts['WARNING']} | FAIL: {counts['FAIL']}"
        )
        issue_checks = [check for check in checks if str(check.get("status", "")) != "PASS"]
        if detail in {"summary", "diagnostic"}:
            selected = issue_checks
        else:
            selected = _select_rows(checks, max_pass_rows=max_pass_rows, issue_key="status")
        if not selected:
            lines.extend(["", "Aucun WARNING/FAIL; les controles PASS individuels sont omis.", ""])
            return
        lines.extend(["", "| Statut | Controle | Valeur | Limite | Message |", "| --- | --- | ---: | --- | --- |"])
        for check in selected:
            lines.append(
                "| {status} | {name} | {value} | {limit} | {message} |".format(
                    status=_cell(check.get("status", "")),
                    name=_cell(check.get("name", "")),
                    value=_sci(check.get("value", "")),
                    limit=_cell(check.get("limit", "")),
                    message=_cell(check.get("message", "")),
                )
            )
        omitted = len(checks) - len(selected)
        if omitted > 0:
            lines.append(f"\n> {omitted} controles PASS individuels omis dans cet export.")
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

    def _loads(self, lines: list[str], loads: dict[str, Any], *, detail: str) -> None:
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
        if detail != "values":
            contribution_count = loads.get("contribution_count", len(contributions))
            if contribution_count:
                lines.append(
                    f"- Contributions detaillees omises: {contribution_count} "
                    "(utiliser detail=`values` pour le forensic)."
                )
                contribution_types = loads.get("contribution_types", [])
                if contribution_types:
                    lines.append(f"- Types de contributions: {_short_list(contribution_types)}")
            lines.append("")
            return
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

    def _elements(
        self,
        lines: list[str],
        elements: list[dict[str, Any]],
        *,
        max_pass_rows: int | None,
    ) -> None:
        if not elements:
            return
        lines.extend(["## Elements", "", "| # | Type | Materiau | Noeuds | Volume/Aire | Qualite | Matrice locale | Norme | Rang |", "| ---: | --- | --- | --- | ---: | ---: | --- | ---: | ---: |"])
        selected = elements if max_pass_rows is None else _select_rows(
            elements,
            max_pass_rows=max_pass_rows,
            issue_key="element_issue",
        )
        for element in selected:
            geometry = element.get("geometry", {})
            matrix: dict[str, Any] = next(iter(element.get("matrices", [])), {})
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
        omitted = len(elements) - len(selected)
        if omitted > 0:
            lines.append(f"\n> {omitted} lignes PASS d'elements omises dans cet export.")
        lines.append("")

    def _post_results(
        self,
        lines: list[str],
        results: list[dict[str, Any]],
        *,
        max_pass_rows: int | None,
    ) -> None:
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
        selected = results if max_pass_rows is None else _select_rows(
            results,
            max_pass_rows=max_pass_rows,
            issue_key="post_issue",
        )
        for result in selected:
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
        omitted = len(results) - len(selected)
        if omitted > 0:
            lines.append(f"\n> {omitted} lignes PASS de post-traitement omises dans cet export.")
        lines.append("")

    def _post_results_summary(
        self,
        lines: list[str],
        results: list[dict[str, Any]],
        *,
        total_count: int | None,
    ) -> None:
        if not results and not total_count:
            return
        by_type: dict[str, int] = {}
        for result in results:
            key = str(result.get("type", "UNKNOWN"))
            by_type[key] = by_type.get(key, 0) + 1
        lines.extend(
            [
                "## Post-traitement par element (resume)",
                "",
                f"- Resultats elements: {total_count if total_count is not None else len(results)}",
                f"- Resultats avec WARNING/FAIL conserves: {len(results)}",
                f"- Types conserves: {_join_mapping(by_type) if by_type else 'aucun WARNING/FAIL'}",
                "- Les valeurs individuelles sont omises; utiliser detail=`values` pour le forensic.",
                "",
            ]
        )

    def _diagnostic(self, lines: list[str], diagnostic: dict[str, Any]) -> None:
        if not diagnostic:
            return
        counts = diagnostic.get("automatic_checks", {})
        lines.extend(
            [
                "## Diagnostic compact",
                "",
                "### AUTOMATIC CHECKS",
                "",
                f"PASS: {counts.get('PASS', 0)}",
                f"WARNING: {counts.get('WARNING', 0)}",
                f"FAIL: {counts.get('FAIL', 0)}",
                "",
                "### Warnings / failures:",
            ]
        )
        issue_checks = diagnostic.get("issue_checks", [])
        if issue_checks:
            lines.extend(
                f"- {_cell(item.get('name', ''))}: {_sci(item.get('value', ''))} "
                f"(limite {_cell(item.get('limit', ''))}) — {_cell(item.get('message', ''))}"
                for item in issue_checks
            )
        else:
            lines.append("- Aucun.")
        lines.extend(["", "### Element quality summary:", ""])
        element_quality = diagnostic.get("element_quality", {})
        if element_quality:
            lines.extend(["| Type | Count | Volume min | Volume max | Qualite min | Qualite moyenne |", "| --- | ---: | ---: | ---: | ---: | ---: |"])
            for element_type, summary in element_quality.items():
                volume = summary.get("signed_corner_volume", {})
                quality = summary.get("corner_quality", {})
                lines.append(
                    f"| {_cell(element_type)} | {summary.get('count', 0)} | "
                    f"{_sci(volume.get('min', ''))} | {_sci(volume.get('max', ''))} | "
                    f"{_sci(quality.get('min', ''))} | {_sci(quality.get('mean', ''))} |"
                )
        else:
            lines.append("- Aucun agregat elementaire disponible.")
        lines.extend(["", "### Worst-N:", ""])
        worst = diagnostic.get("worst_n", {})
        for family, values in worst.items():
            lines.append(f"- {family}: {_worst_list(values)}")
        lines.extend(["", "### Matrix checks:", ""])
        matrix_stats = diagnostic.get("matrix_stats", {})
        if matrix_stats:
            for name, stats in matrix_stats.items():
                lines.append(
                    f"- {name}: norm {_metric_text(stats.get('data_norm', {}))}; "
                    f"symetrie {_metric_text(stats.get('symmetry_relative_error', {}))}; "
                    f"condition {_metric_text(stats.get('condition_estimate', {}))}"
                )
        else:
            lines.append("- Aucun agregat matriciel disponible.")
        result_stats = diagnostic.get("result_stats", {})
        if result_stats:
            lines.extend(["", "### Stress / resultats:", ""])
            for name, stats in result_stats.items():
                lines.append(f"- {name}: {_metric_text(stats)}")
        residual_stats = diagnostic.get("residual_stats", {})
        if residual_stats:
            lines.extend(["", "### Residus:", ""])
            for name, stats in residual_stats.items():
                lines.append(f"- {name}: {_metric_text(stats)}")
        lines.extend(["", "### Equilibrium:", ""])
        equilibrium = diagnostic.get("equilibrium", {})
        for key in (
            "free_relative_residual",
            "force_balance_relative_error",
            "moment_balance_relative_error",
            "linear_energy_identity_relative_error",
        ):
            if key in equilibrium:
                lines.append(f"- {key}: {_sci(equilibrium[key])}")
        constraints = equilibrium.get("constraint_forces", {})
        if constraints:
            lines.append(f"- constraint_forces: {_join_mapping(constraints)}")
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


def _validate_max_pass_rows(value: int | None) -> None:
    if value is not None and value < 0:
        raise ValueError("max_pass_rows must be non-negative or None.")


def _estimate_rows(data: dict[str, Any], *, detail: str) -> int:
    """Estimate Markdown rows before rendering, without materializing new data."""
    checks = data.get("checks", [])
    elements = data.get("element_audits", [])
    post_results = data.get("post_results", [])
    loads = data.get("load_assembly", {})
    contributions = loads.get("contributions", []) if isinstance(loads, dict) else []
    if isinstance(loads, dict):
        contribution_count = loads.get("contribution_count", len(contributions))
    else:
        contribution_count = 0
    if detail == "summary":
        return 80 + sum(str(item.get("status", "")) != "PASS" for item in checks)
    if detail == "diagnostic":
        worst = data.get("diagnostic", {}).get("worst_n", {})
        worst_count = sum(len(values) for values in worst.values() if isinstance(values, list))
        return 140 + len(checks) + len(elements) + worst_count + min(len(post_results), 20)
    return 120 + len(checks) + len(elements) + len(post_results) + int(contribution_count)


def _select_rows(
    rows: list[dict[str, Any]],
    *,
    max_pass_rows: int | None,
    issue_key: str,
) -> list[dict[str, Any]]:
    """Retain every issue row and at most max_pass_rows ordinary rows."""
    if max_pass_rows is None:
        return rows
    if issue_key == "status":
        issue_rows = [row for row in rows if str(row.get("status", "")) != "PASS"]
    elif issue_key == "element_issue":
        issue_rows = [row for row in rows if _element_row_is_issue(row)]
    elif issue_key == "post_issue":
        issue_rows = [
            row
            for row in rows
            if any(check.status != "PASS" for check in _post_result_checks(row))
        ]
    else:
        issue_rows = [row for row in rows if bool(row.get(issue_key, False))]
    pass_rows = [row for row in rows if row not in issue_rows]
    return issue_rows + pass_rows[:max_pass_rows]


def _element_row_is_issue(row: dict[str, Any]) -> bool:
    geometry = row.get("geometry", {})
    for key in ("signed_corner_volume", "area"):
        if key in geometry and (not _finite_number(geometry[key]) or float(geometry[key]) <= 1.0e-14):
            return True
    quality = geometry.get("corner_quality")
    if quality is not None and (not _finite_number(quality) or float(quality) < 0.05):
        return True
    for matrix in row.get("matrices", []):
        if not _finite_number(matrix.get("data_norm")):
            return True
        symmetry = matrix.get("symmetry_relative_error")
        if _finite_number(symmetry) and float(symmetry) > 1.0e-9:
            return True
        condition = matrix.get("condition_estimate")
        if _finite_number(condition) and float(condition) > 1.0e12:
            return True
    return False


def _finite_number(value: object) -> bool:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    return number == number and abs(number) != float("inf")


def _metric_text(metric: object) -> str:
    if not isinstance(metric, dict):
        return _sci(metric)
    return (
        f"min={_sci(metric.get('min', ''))}, "
        f"max={_sci(metric.get('max', ''))}, "
        f"mean={_sci(metric.get('mean', ''))}"
    )


def _worst_list(values: object) -> str:
    if not isinstance(values, list) or not values:
        return "aucun"
    return "; ".join(
        f"#{item.get('index', '?')}={_sci(item.get('value', ''))}"
        for item in values[:10]
        if isinstance(item, dict)
    )
