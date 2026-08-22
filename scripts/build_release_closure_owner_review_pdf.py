"""Build the detailed Owner revalidation PDF for QF_solver 0.2.1a0."""

from __future__ import annotations

import json
from pathlib import Path
from xml.sax.saxutils import escape
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

try:
    from scripts.owner_review_pdf_support import (
        review_footer,
        review_styles,
        review_table,
        validate_pdf,
    )
except ModuleNotFoundError:
    from owner_review_pdf_support import review_footer, review_styles, review_table, validate_pdf


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "qf_solver_0_2_1_alpha_closure_owner_review_2026-08-22.pdf"
DECISIONS = ROOT / "qualification" / "reviews" / "owner_review_scope_decisions_2026-08-22.json"
STABLE = ROOT / "qualification" / "reviews" / "owner_stable_promotion_2026-08-21.json"
LARGE_SUMMARIES = [
    ROOT / "results" / "VNV-TET4-TL-PHASE2-LARGE-011" / "summary.json",
    ROOT / "results" / "VNV-TET4-TL-PHASE2-LARGE-012" / "summary.json",
]
RELEASE_VV = ROOT / "results" / "release_vv_0_2_1" / "release_vv_summary.json"


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _p(text: str, style: Any) -> Paragraph:
    return Paragraph(escape(text).replace("\n", "<br/>"), style)


def _scope_rows(payload: dict[str, Any]) -> list[list[str]]:
    rows = [["Scope", "Decision", "Technical status"]]
    rows.extend(
        [
            str(item["scope"]),
            str(item.get("owner_decision") or "HORS ACCEPTANCE"),
            str(item.get("technical_status", "")),
        ]
        for item in payload.get("scopes", [])
    )
    return [rows[0]] + [rows[index : index + 3] for index in range(1, len(rows), 3)]


def _stable_groups(scopes: list[str]) -> list[str]:
    groups = {
        "BEAM2 et discret": ["beam2-linear-static", "beam2-linear-dynamics", "discrete-linear", "discrete-linear-dynamics"],
        "MITC3 isotrope": ["mitc3-linear-static", "mitc3-modal", "mitc3-transient-dynamic", "mitc3-harmonic-response"],
        "MITC4": ["mitc4-linear-static", "mitc4-modal", "mitc4-transient-dynamic", "mitc4-harmonic-response", "mitc4-laminate-static", "mitc4-laminate-dynamic-refined-three-layups", "mitc4-orthotropic-homogeneous-ply"],
        "TET4": ["tet4-linear-static", "tet4-modal", "tet4-transient-dynamic", "tet4-harmonic-response"],
        "TET10": ["tet10-linear-static", "tet10-modal", "tet10-transient-dynamic", "tet10-harmonic-response"],
    }
    return [f"{title}: {', '.join(scope for scope in members if scope in scopes)}" for title, members in groups.items()]


def _release_scope_rows(release: dict[str, Any]) -> list[list[str]]:
    rows = [["Scope", "Matrice", "Cible", "Verdict", "Motif"]]
    for item in release.get("scopes", []):
        if item.get("status") == "PASS":
            continue
        rows.append(
            [
                str(item.get("id", "")),
                str(item.get("matrix_status", "")),
                str(item.get("target_status", "")),
                str(item.get("status", "")),
                str(item.get("detail", "")),
            ]
        )
    return rows


def _build_story() -> list[Any]:
    decisions = _read(DECISIONS)
    stable = _read(STABLE)
    summaries = [_read(path) for path in LARGE_SUMMARIES if path.is_file()]
    release = _read(RELEASE_VV) if RELEASE_VV.is_file() else {}
    styles = review_styles()
    stable_scopes = [str(scope) for scope in stable.get("scope", [])]
    scopes = decisions.get("scopes", [])
    accepted = sum(item.get("owner_decision") == "accepted_for_bounded_engineering_use" for item in scopes)
    stable_pending = sum(item.get("owner_decision") == "stable" for item in scopes)
    story: list[Any] = [
        Paragraph("QF_solver 0.2.1a0", styles["title"]),
        Spacer(1, 4 * mm),
        Paragraph("Revue Owner de cloture V&V et revalidation avant release", styles["subtitle"]),
        Spacer(1, 6 * mm),
        _p("Document detaille genere le 22 aout 2026. Il consolide les decisions exprimees, mais ne constitue ni une certification externe, ni un commit, ni un tag, ni un push.", styles["note"]),
        review_table(
            [
                ["Champ", "Etat"],
                ["Version cible", "0.2.1a0"],
                ["Owner", "Quentin Farinazzo"],
                ["Stable deja enregistre", str(len(stable_scopes)) + " sous-perimetres"],
                ["Decisions appliquees dans ce paquet", str(len(scopes))],
                ["Decisions stable dans le paquet", str(stable_pending)],
                ["Decisions bounded", str(accepted)],
                ["TET4 TL phase 2", "research / more_evidence_required"],
                ["Certification", "aucune"],
            ],
            [70 * mm, 90 * mm],
            styles,
        ),
        PageBreak(),
        Paragraph("1. Perimetres stables deja enregistres", styles["h1"]),
        _p("Le registre Owner du 21 aout 2026 est termine. Il porte une revue declaree du proprietaire, pas une revue independante. La stabilite reste bornee au domaine documente de chaque scope.", styles["body"]),
    ]
    for group in _stable_groups(stable_scopes):
        story.append(_p(group, styles["body"]))
    story.extend(
        [
            Spacer(1, 4 * mm),
            _p("Exclusions communes conservees : grandes deformations non demontrees, contact, dommage, rupture, delamination, contraintes ponctuelles exactement singulieres et extrapolation hors geometries ou maillages documentes.", styles["note"]),
            PageBreak(),
            Paragraph("2. Decisions de scope resynchronisees", styles["h1"]),
            _p("Les 14 decisions du 22 aout sont maintenant reportees dans le registre de decision et les matrices de maturite. Elles restent identifiees comme declarations electroniques Owner sans signature manuscrite. La revalidation finale de ce PDF demeure ouverte.", styles["body"]),
            review_table(_scope_rows(decisions), [70 * mm, 48 * mm, 42 * mm], styles),
        ]
    )
    for index, item in enumerate(scopes, start=1):
        story.extend(
            [
                PageBreak(),
                Paragraph(f"3.{index} {item['scope']}", styles["h1"]),
                review_table(
                    [
                        ["Champ", "Valeur"],
                        ["Decision Owner", str(item.get("owner_decision") or "HORS ACCEPTANCE")],
                        ["Etat technique", str(item.get("technical_status", ""))],
                        ["Etat avant application", str(item.get("current_status", ""))],
                    ],
                    [60 * mm, 100 * mm],
                    styles,
                ),
                Spacer(1, 3 * mm),
                _p(str(item.get("owner_observation", "")), styles["body"]),
                Paragraph("Action restante", styles["h2"]),
                _p(str(item.get("next_action", "")), styles["body"]),
                Paragraph("Preuves principales", styles["h2"]),
            ]
        )
        for evidence in item.get("evidence", []):
            story.append(_p(f"- {evidence}", styles["small"]))
    story.extend(
        [
            PageBreak(),
            Paragraph("4. Snapshot release-vv resynchronise", styles["h1"]),
            _p("Le dernier controle release-vv a ete relance apres la synchronisation du registre des exigences. Il ne lance pas la campagne lourde et ne cree ni commit ni tag.", styles["body"]),
            review_table(
                [
                    ["Indicateur", "Valeur"],
                    ["Scopes PASS", str(sum(item.get("status") == "PASS" for item in release.get("scopes", [])))],
                    ["Scopes FAIL", str(sum(item.get("status") == "FAIL" for item in release.get("scopes", [])))],
                    ["Campagne", str(release.get("campaign", {}).get("readiness_status", "n/a"))],
                    ["Owner review", str(release.get("owner_review", {}).get("status", "n/a"))],
                    ["Source checkout", str(next((item.get("status") for item in release.get("checks", []) if item.get("id") == "SOURCE-CLEAN"), "n/a"))],
                ],
                [70 * mm, 90 * mm],
                styles,
            ),
            Spacer(1, 4 * mm),
            _p("Les lignes suivantes sont les blocages de perimetre, et non des regressions du noyau stable. Elles correspondent aux domaines que la decision Owner conserve bornes ou en recherche.", styles["note"]),
            review_table(_release_scope_rows(release), [48 * mm, 36 * mm, 25 * mm, 22 * mm, 29 * mm], styles),
            PageBreak(),
            Paragraph("5. TET4 total-lagrangien phase 2", styles["h1"]),
            _p("Le TET4 total-lagrangien conserve le statut research / more_evidence_required. Les preuves precedentes de formulation, de Green-Lagrange, de PK2/Cauchy, de flambement borne, de post-flambement et de correlations externes restent archivees. La sonde a environ 1,2 million d'elements n'a pas fourni de resultat mecanique.", styles["body"]),
            review_table(
                [["Tentative", "Elements", "Statut", "Memoire privee", "Verdict mecanique"]]
                + [
                    [
                        path.parent.name,
                        f"{summary.get('elements', 0):,}".replace(",", " "),
                        str(summary.get("status")),
                        f"{summary.get('execution', {}).get('observed_private_memory_gb_before_stop', 'n/a')} Go",
                        "Aucun resultat",
                    ]
                    for path, summary in zip(LARGE_SUMMARIES, summaries)
                ],
                [48 * mm, 25 * mm, 40 * mm, 28 * mm, 29 * mm],
                styles,
            ),
            Spacer(1, 4 * mm),
            _p("Interpretation : l'arret est une limite de ressources du chemin d'assemblage tangent dense. Il ne permet pas de conclure que la formulation mecanique est fausse ou vraie a cette echelle. Aucune promotion stable n'est deduite.", styles["note"]),
            Paragraph("Decision a revalider", styles["h2"]),
            _p("Maintenir research / more_evidence_required. Implementer une assemblage par blocs, matrix-free ou distribue avant toute nouvelle sonde et conserver une revue independante avant toute promotion.", styles["body"]),
            PageBreak(),
            Paragraph("6. Ce qui reste ouvert avant le push", styles["h1"]),
        ]
    )
    blockers = [
        "Remplir et revalider la fiche Owner TET4 phase 2.",
        "Relire les fiches individuelles des 14 decisions appliquees et confirmer les limites.",
        "Relire le dernier release-vv : 28 scopes PASS et 8 scopes FAIL correspondant aux perimetres bornes ou en recherche.",
        "Relancer la suite complete de tests apres les dernieres modifications.",
        "Auditer un checkout propre, les fichiers suivis, l'archive Git, les secrets et les informations personnelles.",
        "Verifier le paquet Python dans des environnements neufs avant toute publication.",
        "Obtenir une revision Git propre; aucun commit, tag ou push n'est cree par ce document.",
    ]
    for blocker in blockers:
        story.append(_p(f"- {blocker}", styles["body"]))
    story.extend(
        [
            Spacer(1, 5 * mm),
            Paragraph("7. Decision Owner a renseigner", styles["h1"]),
            review_table(
                [
                    ["Question", "Reponse"],
                    ["Les decisions appliquees correspondent-elles a tes validations ?", "________________"],
                    ["Le TET4 TL doit-il rester research / more_evidence_required ?", "________________"],
                    ["Les exclusions sont-elles maintenues ?", "________________"],
                    ["Autorises-tu la fermeture documentaire sans push ?", "________________"],
                    ["Nom / date / signature", "________________"],
                ],
                [95 * mm, 65 * mm],
                styles,
            ),
            Spacer(1, 5 * mm),
            _p("Verdict de preparation : les decisions connues sont resynchronisees, mais la release n'est pas declaree prete a pousser tant que la revalidation Owner et l'audit final ne sont pas termines.", styles["note"]),
        ]
    )
    return story


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=15 * mm,
        bottomMargin=16 * mm,
        title="QF_solver 0.2.1a0 - Owner closure review",
    )
    document.build(_build_story(), onFirstPage=review_footer, onLaterPages=review_footer)
    validate_pdf(OUTPUT, ["QF_solver 0.2.1a0", "TET4 total-lagrangien", "more_evidence_required", "Scopes PASS"], 10)
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
