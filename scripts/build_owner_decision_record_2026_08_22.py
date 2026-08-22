"""Regenerate the Owner decision record declared on 2026-08-22.

The record is explicit and dated. Applying it to the maturity registers remains
separate from a release tag, a commit, a push, or an external certification.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

try:
    from scripts.owner_review_pdf_support import review_footer, review_styles, review_table, validate_pdf
except ModuleNotFoundError:
    from owner_review_pdf_support import review_footer, review_styles, review_table, validate_pdf

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "qualification" / "reviews" / "owner_review_scope_closure_2026-08-21.json"
OUTPUT_JSON = ROOT / "qualification" / "reviews" / "owner_review_scope_decisions_2026-08-22.json"
OUTPUT_MD = ROOT / "docs" / "verification" / "owner_review_scope_decisions_2026-08-22.md"
OUTPUT_PDF = ROOT / "output" / "pdf" / "qf_solver_owner_review_scope_decisions_2026-08-22.pdf"

DECISIONS: dict[str, dict[str, Any]] = {
    "mitc3-laminate-static": {
        "decision": "accepted_for_bounded_engineering_use",
        "observation": "Patch plan [0/90/90/0] accepte dans son domaine; pas de promotion stable.",
        "next": "Ajouter au moins deux layups symetriques : [0/45/45/0] et [45/0/0/45].",
    },
    "mitc3-laminate-dynamic-thin-planar": {
        "decision": "stable",
        "observation": "Stable uniquement pour le sous-perimetre mince, plan, symetrique et sans dommage.",
        "next": "Conserver les niveaux intermediaires >1 % visibles dans la publication.",
    },
    "mitc3-laminate-static-curved-mixed-transverse": {
        "decision": "stable",
        "observation": "Stable comme sous-perimetre borne mixte/transverse; les increments proches de 5 % restent une recommandation.",
        "next": "Ajouter une geometrie courbe et un raffinement avant toute extension generale.",
    },
    "mitc3-laminate-static-curved": {
        "decision": "accepted_for_bounded_engineering_use",
        "observation": "Domaine axial complet accepte comme usage borne, sans promotion stable.",
        "next": "Ajouter des geometries et une reference externe de formulation comparable.",
    },
    "tet4-total-lagrangian-structural-v2": {
        "decision": "more_evidence_required",
        "observation": "Le scope reste research / more_evidence_required. Deux sondes a 1 152 000 TET4 ont ete arretees pour limite de ressources avant production d'un resultat mecanique.",
        "next": "Implementer une assemblage par blocs, matrix-free ou distribue avant une nouvelle sonde; conserver une revue independante avant toute promotion.",
    },
    "tet4-material-nonlinear": {
        "decision": "accepted_for_bounded_engineering_use",
        "observation": "J2 petites deformations accepte en usage borne.",
        "next": "Planifier chargement, decharge, rechargement, cyclage et correlation structurelle externe pour une version ulterieure.",
    },
    "tet10-material-nonlinear": {
        "decision": "accepted_for_bounded_engineering_use",
        "observation": "J2 TET10 accepte en usage borne, sans extension rupture/dommage/contact.",
        "next": "Ajouter des chemins cycliques et une seconde structure avant une cible stable.",
    },
    "orthotropic-solid-tet4-tet10": {
        "decision": "stable",
        "observation": "Stable dans le domaine statique orthotrope homogene documente, apres reconciliation de la valeur historique.",
        "next": "Corriger le document qui cite 1,3293 % et conserver 0,8772 % comme resultat de la campagne CG finale source.",
    },
    "orthotropic-solid-modal": {
        "decision": "stable",
        "observation": "Stable pour le domaine modal TET4 orthotrope homogene teste.",
        "next": "Maintenir les exclusions composite pli par pli, orientation courbe continue et dommage.",
    },
    "orthotropic-solid-transient-dynamic": {
        "decision": "stable",
        "observation": "Stable pour le domaine Newmark orthotrope homogene teste.",
        "next": "Conserver les limites sur amortissement, non-linearite, dommage et orientation variable.",
    },
    "contact-v1-linear-static-bounded": {
        "decision": "accepted_for_bounded_engineering_use",
        "observation": "Contact sans frottement accepte en domaine borne.",
        "next": "Ajouter des geometries, branches et validations avant toute stabilite generale.",
    },
    "contact-frictional-static": {
        "decision": "accepted_for_bounded_engineering_use",
        "observation": "Frottement accepte en domaine borne, principalement sur la branche slip corrélee.",
        "next": "Renforcer stick, grand glissement, normales actualisees et seconde correlation externe.",
    },
    "large-tet4-linear-static": {
        "decision": "accepted_for_bounded_engineering_use",
        "observation": "Grand modele TET4 accepte pour la configuration PETSc/MPI mesuree.",
        "next": "Reporter l'optimisation weak scaling, memoire, partitionnement et plusieurs configurations materielle.",
    },
    "mitc4-orthotropic-curved-out-of-acceptance": {
        "decision": None,
        "observation": "Hors acceptance; aucune promotion ni decision de maturite.",
        "next": "Conserver uniquement comme diagnostic experimental interne, non publie comme preuve d'acceptation.",
    },
}


def _load() -> dict[str, Any]:
    return json.loads(SOURCE.read_text(encoding="utf-8"))


def _build_payload(source: dict[str, Any]) -> dict[str, Any]:
    scopes: list[dict[str, Any]] = []
    for item in source["scopes"]:
        decision = DECISIONS[item["scope"]]
        scopes.append({
            "scope": item["scope"],
            "current_status": item["current_status"],
            "technical_status": item["technical_status"],
            "owner_decision": decision["decision"],
            "owner_observation": decision["observation"],
            "next_action": decision["next"],
            "evidence": item["evidence"],
            "recorded_answers": None,
        })
    return {
        "schema_version": 1,
        "review_id": "OWNER-REVIEW-SCOPE-DECISIONS-2026-08-22",
        "source_review": "qualification/reviews/owner_review_scope_closure_2026-08-21.json",
        "revision": "0.2.1-alpha",
        "status": "owner_decisions_applied_pending_release_audit",
        "automatic_promotion": False,
        "owner": "Quentin Farinazzo",
        "recording_mode": "user_declared_owner_decision_applied_without_handwritten_signature",
        "decision_date": "2026-08-22",
        "application": {
            "date": "2026-08-22",
            "applied_to": [
                "qualification/element_analysis_matrix.json",
                "qualification/maturity_promotion_0_2_1.json",
                "docs/verification/release_vv_0_2_1_closure_package_2026-08-22.md"
            ],
            "release_commit_created": False,
            "release_tag_created": False,
            "public_push_done": False,
            "note": "Application de la decision dans les registres de maturite; la revalidation finale Owner et l'audit de release restent ouverts."
        },
        "certification_claim": "none",
        "scopes": scopes,
        "global_notes": [
            "Les reponses detaillees Q1...Qn restent a revalider dans les fiches individuelles et le PDF de cloture.",
            "Les niveaux intermediaires superieurs a 1 % restent publies et ne sont pas masques.",
            "MITC4 orthotrope courbe reste hors acceptance et sans decision de promotion.",
            "Les registres de maturite ont ete synchronises manuellement avec ce record; aucune promotion automatique n'est autorisee.",
        ],
    }


def _write_json(payload: dict[str, Any]) -> None:
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_markdown(payload: dict[str, Any]) -> None:
    rows = [["Scope", "Decision Owner", "Etat technique"]]
    lines = [
        "---", "doc_id: DOC-OWNER-DECISIONS-2026-08-22", "revision: 0.1",
        "status: owner_decisions_recorded_pending_audit", "review_mode: owner_declared", "---", "",
        "# Decisions Owner - 22 aout 2026", "",
        "Ces decisions sont la transcription de la declaration Owner fournie le 22 aout 2026. Elles ne constituent pas une signature manuscrite, une revue independante ou une certification. Le registre technique ne sera synchronise qu'apres audit.", "",
        "## Synthese", "",
    ]
    for item in payload["scopes"]:
        rows.append([item["scope"], item["owner_decision"] or "hors acceptance", item["technical_status"]])
    lines.extend([_table_md(rows), "", "## Observations et actions", ""])
    for index, item in enumerate(payload["scopes"], start=1):
        lines.extend([
            f"### {index}. `{item['scope']}`", "",
            f"- Decision : `{item['owner_decision'] or 'hors acceptance / aucune promotion'}`",
            f"- Observation : {item['owner_observation']}",
            f"- Action suivante : {item['next_action']}", "",
        ])
    lines.extend([
        "## DKT", "",
        "DKT signifie *Discrete Kirchhoff Triangle*. C'est un element triangulaire mince de type Kirchhoff-Love qui impose discretement un cisaillement transverse quasi nul. Il sert ici de reference de limite mince; ce n'est pas la meme formulation que MITC3+ Reissner-Mindlin et il ne valide pas les coques epaisses ou courbes en general.", "",
        "## Actions futures", "",
        "- MITC3 statique : ajouter les layups symetriques `[0/45/45/0]` et `[45/0/0/45]`.",
        "- TET4 total-lagrangien : preparer une campagne cible autour de 1,2 million d'elements, puis verifier convergence, memoire et independance de revue.",
        "- J2 : planifier chargement/decharge/rechargement, cyclage, multiaxialite et correlation structurelle externe.",
        "- KSP/PC et increments non lineaires : analyser pas de charge, line-search, residus, tangent consistante et choix du sous-solveur avant promotion stable.",
        "",
        "## Trace", "",
        "- Source : `qualification/reviews/owner_review_scope_closure_2026-08-21.json`",
        "- Record : `qualification/reviews/owner_review_scope_decisions_2026-08-22.json`",
        "- Date : `2026-08-22`",
    ])
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _table_md(rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(rows[0]) + " |", "| --- | --- | --- |"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows[1:])
    return "\n".join(lines)


def _write_pdf(payload: dict[str, Any]) -> None:
    OUTPUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    styles = review_styles()
    story: list[Any] = [
        Paragraph("QF_solver - Decisions Owner", styles["title"]),
        Spacer(1, 5 * mm),
        Paragraph("Transcription du 22 aout 2026 - application apres audit", styles["subtitle"]),
        Spacer(1, 8 * mm),
        Paragraph("Ces decisions sont enregistrees comme declaration Owner electronique. Aucune promotion technique n'est appliquee automatiquement.", styles["note"]),
        review_table(
            [["Champ", "Valeur"], ["Owner", payload["owner"]], ["Date", payload["decision_date"]], ["Scopes", str(len(payload["scopes"]))], ["Calculs relances", "0"], ["Certification", "aucune"]],
            [55 * mm, 105 * mm], styles,
        ),
    ]
    for index, item in enumerate(payload["scopes"], start=1):
        story.append(PageBreak())
        decision = item["owner_decision"] or "HORS ACCEPTANCE - AUCUNE PROMOTION"
        story.extend([
            Paragraph(f"{index}. {item['scope']}", styles["h1"]),
            review_table(
                [["Champ", "Valeur"], ["Decision Owner", decision], ["Etat technique", item["technical_status"]], ["Etat courant", item["current_status"]]],
                [55 * mm, 105 * mm], styles,
            ),
            Spacer(1, 5 * mm),
            Paragraph(item["owner_observation"], styles["body"]),
            Paragraph("Action suivante", styles["h2"]),
            Paragraph(item["next_action"], styles["body"]),
            Paragraph("Preuves principales", styles["h2"]),
        ])
        for evidence in item["evidence"][:5]:
            story.append(Paragraph(f"- {evidence}", styles["small"]))
    story.extend([
        PageBreak(), Paragraph("Note DKT", styles["h1"]),
        Paragraph("DKT signifie Discrete Kirchhoff Triangle. C'est un element triangulaire mince de type Kirchhoff-Love qui impose discretement un cisaillement transverse quasi nul. Il sert ici de reference de limite mince; ce n'est pas la meme formulation que MITC3+ Reissner-Mindlin et il ne valide pas les coques epaisses ou courbes en general.", styles["body"]),
        Paragraph("Application", styles["h2"]),
        Paragraph("Les decisions seront synchronisees dans les registres de maturite uniquement apres l'audit des preuves, la correction de l'incoherence orthotrope 1,3293 % / 0,8772 % et la verification des exclusions.", styles["body"]),
    ])
    document = SimpleDocTemplate(str(OUTPUT_PDF), pagesize=A4, rightMargin=16 * mm, leftMargin=16 * mm, topMargin=15 * mm, bottomMargin=16 * mm, title="QF_solver - Decisions Owner 2026-08-22")
    document.build(story, onFirstPage=review_footer, onLaterPages=review_footer)
    validate_pdf(OUTPUT_PDF, ["Decisions Owner", "DKT", "AUCUNE PROMOTION"], 8)


def main() -> int:
    payload = _build_payload(_load())
    _write_json(payload)
    _write_markdown(payload)
    _write_pdf(payload)
    print(OUTPUT_JSON)
    print(OUTPUT_MD)
    print(OUTPUT_PDF)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
