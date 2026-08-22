"""Rendering and Owner-packet helpers for maturity promotion audits."""

from __future__ import annotations

from typing import Any


def build_owner_review_packet(report: dict[str, Any]) -> dict[str, Any]:
    """Build an Owner packet without making or inferring any decision."""
    scopes: list[dict[str, Any]] = []
    for row in report.get("scopes", []):
        gate = str(row.get("promotion_gate", ""))
        blocking = set(str(identifier) for identifier in row.get("blocking_criteria", []))
        pending_blockers = {
            str(criterion.get("id"))
            for criterion in row.get("criteria", [])
            if str(criterion.get("id")) in blocking and criterion.get("kind") == "pending"
        }
        technical_ready = gate in {"READY_FOR_OWNER_REVIEW", "BLOCKED_OWNER_REVIEW"}
        owner_only_block = bool(blocking) and blocking == pending_blockers
        if gate == "NO_PROMOTION_REQUIRED" or not (technical_ready or owner_only_block):
            continue
        scopes.append(
            {
                "scope": row["scope"],
                "current_status": row["current_status"],
                "target_status": row["target_status"],
                "technical_status": row["criteria_status"],
                "promotion_gate": gate,
                "blocking_criteria": sorted(blocking),
                "blocking_classification": row.get("blocking_classification", "none"),
                "evidence_paths": row.get("evidence_paths", []),
                "owner_review_paths": row.get("owner_review_paths", []),
                "promotion_target": None,
                "next_action": row.get("next_action", ""),
                "decision": None,
                "signature": None,
                "questions": _owner_questions(row),
            }
        )
    return {
        "schema_version": 1,
        "packet_id": "QF-MATURITY-OWNER-PACKET-021-001",
        "status": "PENDING_OWNER_REVIEW",
        "audit_id": report.get("audit_id"),
        "policy": {
            "automatic_maturity_promotion": False,
            "decision_required_per_scope": True,
            "technical_failures_excluded": True,
            "decision_values": [
                "accepted_with_recommendations",
                "accepted_for_bounded_engineering_use",
                "more_evidence_required",
            ],
        },
        "summary": {
            "scope_count": len(scopes),
            "technical_ready_count": sum(item["technical_status"] == "PASS" for item in scopes),
            "owner_only_gate_count": sum(bool(item["blocking_criteria"]) for item in scopes),
            "owner_decision_pending_count": sum(
                item["blocking_classification"] == "owner_decision_pending" for item in scopes
            ),
        },
        "scopes": scopes,
    }


def _owner_questions(row: dict[str, Any]) -> list[dict[str, Any]]:
    scope = str(row["scope"])
    return [
        {"id": "Q1", "question": f"Les preuves du scope {scope} couvrent-elles le domaine revendique ?", "answer": None},
        {"id": "Q2", "question": "Les limites, exclusions, singularites et conventions sont-elles acceptables ?", "answer": None},
        {"id": "Q3", "question": "La maturite ciblee est-elle appropriee sans extrapolation aux cas non testes ?", "answer": None},
        {"id": "Q4", "question": "Quelle decision Owner doit etre enregistree pour ce scope ?", "answer": None},
    ]


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Audit de promotion des maturites QF_solver 0.2.1a0",
        "",
        f"Statut de l'audit : **{report['status']}**.",
        "",
        "Cet audit controle les entrees du plan. Il ne modifie pas la matrice et",
        "ne transforme pas une preuve automatique en decision de maturite.",
        "",
        f"- scopes audites : {summary['scope_count']}",
        f"- scopes bloques : {summary['blocked_scope_count']}",
        f"- chemins d'evidence presents : {summary['path_integrity_pass_count']}",
        f"- owner reviews acceptees detectees : {summary['owner_review_present_count']}",
        f"- scopes bloques uniquement par une decision Owner : {summary['owner_decision_pending_scope_count']}",
        "",
        "| Scope | Actuel | Cible | Technique | Decision Owner | Readiness release | Blocage | Gate |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in report["scopes"]:
        lines.append(
            f"| `{row['scope']}` | `{row['current_status']}` | `{row['maturity_target']}` | "
            f"`{row['technical_status']}` | `{row['owner_decision']}` | "
            f"`{row['release_readiness']}` | `{row['blocking_classification']}` | "
            f"`{row['promotion_gate']}` |"
        )
    lines.extend(["", "## Actions", ""])
    for row in report["scopes"]:
        if row["promotion_gate"] != "NO_PROMOTION_REQUIRED":
            lines.append(f"- `{row['scope']}` : {row['next_action']}")
    lines.append("")
    return "\n".join(lines)


def render_owner_packet(packet: dict[str, Any]) -> str:
    summary = packet["summary"]
    lines = [
        "# Paquet Owner de promotion des maturites QF_solver 0.2.1a0",
        "",
        "Statut : **PENDING_OWNER_REVIEW**.",
        "",
        "Ce document est genere depuis l'audit de promotion. Il ne modifie pas",
        "la matrice et ne renseigne aucune decision ou signature.",
        "",
        f"- scopes soumis a lecture : {summary['scope_count']}",
        f"- scopes techniquement prets : {summary['technical_ready_count']}",
        f"- gates limitees a une decision Owner : {summary['owner_only_gate_count']}",
        f"- scopes bloques uniquement par une decision Owner : {summary['owner_decision_pending_count']}",
        "",
        "| Scope | Actuel | Cible technique | Cible Owner | Technique | Blocage | Gate | Decision |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in packet["scopes"]:
        lines.append(
            f"| `{item['scope']}` | `{item['current_status']}` | `{item['target_status']}` | "
            f"`PENDING` | `{item['technical_status']}` | `{item['blocking_classification']}` | "
            f"`{item['promotion_gate']}` | `PENDING` |"
        )
    lines.extend(["", "## Regle de decision", ""])
    lines.append(
        "Pour chaque scope, lire les chemins d'evidence listes dans le JSON, repondre aux quatre questions, puis enregistrer une decision datee et signee dans un fichier de revue dedie."
    )
    lines.extend(["", "## Valeurs autorisees", ""])
    lines.extend(f"- `{value}`" for value in packet["policy"]["decision_values"])
    lines.append("")
    return "\n".join(lines)
