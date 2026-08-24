"""Build the complete QF Solver 0.2.4a0 nonlinear Owner-review PDF."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, SimpleDocTemplate, Spacer

try:
    from scripts.owner_review_pdf_support import paragraph, review_image, review_styles, review_table, validate_pdf
except ImportError:  # pragma: no cover - direct script execution
    from owner_review_pdf_support import paragraph, review_image, review_styles, review_table, validate_pdf


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "qualification" / "vnv" / "robustness_nonlinear_solids_024" / "reference"
SUMMARY_PATH = REFERENCE / "summary.json"
DIGEST_PATH = ROOT / "qualification" / "external_reference_digests" / "robustness_nonlinear_solids_024.json"
GATE_PATH = ROOT / "qualification" / "reviews" / "qf_solver_0_2_4a0_gate_status.json"
AUDIT_PATH = ROOT / "qualification" / "publication_audit_0_2_1.json"
OUTPUT = ROOT / "output" / "pdf" / "qf_solver_0_2_4a0_nonlinear_solids_owner_review.pdf"
CACHE = ROOT / "tmp" / "pdfs" / "qf_solver_0_2_4a0"


def footer(canvas: Any, document: Any) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#425563"))
    canvas.drawString(15 * mm, 9 * mm, "QF Solver 0.2.4a0 - revue Owner - accepted_with_recommendations")
    canvas.drawRightString(A4[0] - 15 * mm, 9 * mm, f"Page {document.page}")
    canvas.restoreState()


def _status(value: object) -> str:
    return str(value).replace("_", " ")


def _campaign_rows(summary: dict[str, Any]) -> list[list[object]]:
    rows = [["Élément", "Points Gauss", "Distorsion", "DDL", "Newton", "Résidu max", "PEEQ final", "Temps s", "Statut"]]
    for row in summary["element_matrix"]["rows"]:
        global_row = next(item for item in summary["common_global_benchmark"]["rows"] if item["element"] == row["element"])
        rows.append([
            row["element"], row["integration_points"], "Oui" if row["distorted"] else "Non", global_row["dof_count"],
            global_row["newton_iterations"], f"{global_row['maximum_relative_residual']:.3e}",
            f"{global_row['final_peeq']:.3f}", f"{global_row['elapsed_seconds']:.3f}", global_row["status"],
        ])
    return rows


def _questions() -> list[list[object]]:
    return [
        ["ID", "Question Owner", "État proposé"],
        ["Q1", "Le périmètre J2 small-strain sur TET4, TET10, HEX8 et HEX20 est-il accepté ?", "OUI"],
        ["Q2", "Le tangent cohérent est-il suffisamment vérifié par différences finies ?", "OUI"],
        ["Q3", "Les chemins traction, cisaillement, déchargement, rechargement et non proportionnel sont-ils suffisants ?", "OUI"],
        ["Q4", "Les contrats trial / commit / rollback sont-ils acceptables ?", "OUI"],
        ["Q5", "Les HEX8/HEX20 distordus peuvent-ils rester dans le périmètre interne ?", "OUI"],
        ["Q6", "Le benchmark commun et ses courbes force-déplacement sont-ils exploitables ?", "OUI"],
        ["Q7", "Le comportement Full Newton est-il le seul chemin qualifié ?", "OUI"],
        ["Q8", "La corrélation externe J2 doit-elle être exigée avant fermeture ?", "CONDITIONNEL"],
        ["Q9", "Les corrélations linéaires CalculiX HEX8/HEX20 sont-elles acceptées comme preuves partielles ?", "OUI"],
        ["Q10", "Les limites small-strain, one-element et absence de claim multi-million sont-elles claires ?", "OUI"],
        ["Q11", "Le pipeline de readiness peut-il être adopté comme procédure de release ?", "OUI"],
        ["Q12", "La release 0.2.4a0 peut-elle être préparée sans publication automatique ?", "OUI"],
    ]


def _gate_rows(gates: dict[str, str]) -> list[list[object]]:
    labels = {
        "NL-G01": "Architecture approuvée",
        "NL-G02": "Vérification constitutive J2",
        "NL-G03": "Contrat élément non linéaire",
        "NL-G04": "Vérification Newton",
        "NL-G05": "Commit / rollback",
        "NL-G06": "Incrémentation contrôlée",
        "NL-G07": "Benchmarks analytiques",
        "NL-G08": "Corrélations externes",
        "NL-G09": "Sensibilités maillage / pas",
        "NL-G10": "Performance sanity",
        "NL-G11": "Non-régression 0.2.3",
        "NL-G12": "Documentation et SHA",
        "NL-G13": "Revue Owner",
        "RQ-G01": "Scope robustness",
        "RQ-G02": "Tangent FD",
        "RQ-G03": "Chemins multiaxiaux",
        "RQ-G04": "Transactions état",
        "RQ-G05": "HEX distordus",
        "RQ-G06": "Benchmark commun",
        "RQ-G07": "Taux Newton",
        "RQ-G08": "Corrélation J2 externe",
        "RQ-G09": "Readiness pipeline",
        "RQ-G10": "Owner sign-off",
    }
    rows = [["Gate", "Sujet", "Statut", "Interprétation"]]
    for key, value in gates.items():
        interpretation = "Preuve interne disponible" if "PASS" in value else "Décision ou preuve supplémentaire requise"
        if key == "RQ-G08":
            interpretation = "Corrélation plastique commune bornée PASS; extension multi-éléments hors scope"
        if key in {"NL-G11", "NL-G12"}:
            interpretation = "Preuve présente, SHA final encore absent"
        rows.append([key, labels.get(key, ""), _status(value), interpretation])
    return rows


def build() -> Path:
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    digest = json.loads(DIGEST_PATH.read_text(encoding="utf-8"))
    gate = json.loads(GATE_PATH.read_text(encoding="utf-8"))
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    styles = review_styles()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUTPUT), pagesize=A4, rightMargin=15 * mm, leftMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=16 * mm,
        title="QF Solver 0.2.4a0 - Nonlinear Solids Owner Review", author="QF Solver",
    )
    story: list[object] = [
        paragraph("Revue Owner - Unified Nonlinear Solid Mechanics", styles["title"]),
        Spacer(1, 3 * mm),
        paragraph("QF Solver 0.2.4a0 | Robustness Qualification - Nonlinear Solids | DOC-NL-024-002", styles["subtitle"]),
        Spacer(1, 5 * mm),
        paragraph(
            "Dossier de décision technique construit à partir de la campagne VNV-ROBUSTNESS-NONLINEAR-SOLIDS-024. "
            "Il rassemble les résultats internes, les figures, les preuves Docker disponibles, les limites et les questions ouvertes. "
            "La décision Owner est enregistrée comme accepted_with_recommendations pour le périmètre expérimental. "
            "RQ-G08 est fermée pour la corrélation externe bornée; aucun tag, commit, push ou upload PyPI n'est déclenché par ce document.", styles["note"]),
        paragraph("1. Synthèse exécutive", styles["h1"]),
        paragraph(
            "Le moteur non linéaire commun a été exercé sur TET4, TET10, HEX8 et HEX20 avec une loi J2 small-strain à écrouissage isotrope. "
            "Les chemins constitutifs multiaxiaux, le tangent cohérent, les transactions trial/commit/rollback, les éléments distordus et le benchmark global passent en preuve interne. "
            "Full Newton est le chemin qualifié; Modified Newton est caractérisé mais non convergent dans cette campagne. "
            "La corrélation externe J2 commune est PASS pour le périmètre borné du patch affine à un élément. Les corrélations multi-éléments, cycliques et physiques restent hors scope.", styles["body"]),
        paragraph("2. Périmètre, méthode et exclusions", styles["h1"]),
        review_table([
            ["Rubrique", "État"],
            ["Matériau", "J2 isotrope small-strain avec écrouissage isotrope"],
            ["Éléments", "TET4, TET10, HEX8 et HEX20"],
            ["Chemins", "Constitutif, élémentaire, assemblage global et Newton"],
            ["Distorsion", "HEX8 et HEX20 testés avec géométrie distordue"],
            ["Claim grande échelle", "Exclu: aucun claim multi-million DDL"],
            ["Validation physique", "Non revendiquée; il s'agit de vérification numérique"],
            ["Maturité", "Experimental / PASS_INTERNAL, décision Owner requise"],
        ], [45 * mm, 135 * mm], styles),
        paragraph("3. Résultats de la campagne", styles["h1"]),
        review_table([
            ["Contrôle", "Résultat", "Seuil / commentaire"],
            ["Chemins constitutifs", "PASS", "Traction-déchargement-rechargement, cisaillement pur, chemin non proportionnel"],
            ["Tangent cohérent FD", "PASS", f"Erreur max {summary['consistent_tangent']['maximum_relative_error']:.3e}, limite {summary['consistent_tangent']['limit']:.1e}"],
            ["Trial / commit / rollback", "PASS", "Rollback inchangé; commit modifie l'état"],
            ["Matrice élémentaire", "PASS", "4 éléments; HEX distordus; 1 / 4 / 8 / 27 points de Gauss"],
            ["Benchmark global", "PASS", "4 éléments, historique de charge commun, réactions cohérentes"],
            ["Taux Newton", "PASS_CHARACTERIZED", "Full Newton passe; Modified Newton non convergent explicitement"],
        ], [45 * mm, 38 * mm, 97 * mm], styles),
        PageBreak(),
        paragraph("4. Benchmark commun TET4 / TET10 / HEX8 / HEX20", styles["h1"]),
        paragraph("Même historique de charge [0,25; 0,50; 0,75; 1,00], mêmes contrôles de déplacement et même matériau. Les valeurs PEEQ et déplacements sont des résultats de la campagne, pas des seuils de validation physique.", styles["body"]),
        review_table(_campaign_rows(summary), [22 * mm, 18 * mm, 20 * mm, 14 * mm, 18 * mm, 25 * mm, 20 * mm, 18 * mm, 25 * mm], styles),
        paragraph("Observations", styles["h2"]),
        paragraph(
            "Les réactions finales sont proches de 5 pour les quatre formulations. Les résidus restent très faibles pour TET4/TET10 et sous 1e-9 pour HEX8/HEX20 dans ce cas. "
            "Le coût HEX20 est nettement supérieur dans cette configuration unitaire; aucune extrapolation de performance n'est autorisée.", styles["body"]),
        paragraph("5. Figures et historiques", styles["h1"]),
    ]
    for filename, caption in (("force_displacement.png", "Figure 1 - Courbes force-déplacement du benchmark commun"), ("newton_rate.png", "Figure 2 - Comparaison Full Newton / Modified Newton")):
        image = review_image(REFERENCE / filename, CACHE / filename)
        if image is not None:
            story.append(image)
            story.append(paragraph(caption, styles["small"]))
            story.append(Spacer(1, 3 * mm))
    story.extend([
        PageBreak(),
        paragraph("6. Corrélations externes et portée des preuves", styles["h1"]),
        review_table([
            ["Preuve", "Statut", "Portée"],
            ["CalculiX HEX8 / C3D8", "PASS_EXTERNAL_CORRELATION", "Corrélation linéaire; même maillage, BC, matériau et chargement"],
            ["CalculiX HEX20 / C3D20", "PASS_EXTERNAL_CORRELATION", "Corrélation linéaire; même maillage, BC, matériau et chargement"],
            ["CalculiX J2 existant", "BOUNDED / PARTIAL", "Preuve bornée existante, pas le benchmark commun quatre éléments"],
            ["J2 externe commun", "PASS_EXTERNAL_CORRELATION_BOUNDED", "80 contrôles sur TET4/TET10/HEX8/HEX20; patch affine à un élément"],
            ["Code_Aster J2 commun", "PASS_EXTERNAL_CORRELATION_BOUNDED", "Image 18.1.0 épinglée; écart maximal < 2.7e-15"],
        ], [45 * mm, 45 * mm, 90 * mm], styles),
        paragraph("7. Limites obligatoires", styles["h1"]),
        review_table([["Limite", "Conséquence"]] + [[item, "Ne pas présenter comme capacité qualifiée au-delà du périmètre interne."] for item in digest["limitations"]], [85 * mm, 95 * mm], styles),
        paragraph("La corrélation est une preuve numérique externe bornée. Elle ne constitue pas une validation physique et ne couvre pas les cas multi-éléments ou cycliques.", styles["fail"]),
        paragraph("8. Gates de release et de robustesse", styles["h1"]),
        review_table(_gate_rows(gate["gates"]), [19 * mm, 44 * mm, 42 * mm, 75 * mm], styles),
        PageBreak(),
        paragraph("9. Questions ouvertes pour l'Owner", styles["h1"]),
        paragraph("Pour chaque question, inscrire OUI, NON ou CONDITIONNELLEMENT et ajouter une justification. Les points marqués Point bloquant doivent être traités explicitement avant toute fermeture de gate.", styles["note"]),
        review_table(_questions(), [12 * mm, 132 * mm, 36 * mm], styles),
        paragraph("10. Décision Owner", styles["h1"]),
        review_table([
            ["Champ", "À renseigner"],
            ["Décision", "accepted_with_recommendations"],
            ["Périmètre", "Experimental / PASS_INTERNAL uniquement; aucune promotion externe ou physique"],
            ["RQ-G08", "PASS_EXTERNAL_CORRELATION_BOUNDED; patch affine à un élément fermé, extensions hors scope"],
            ["Conditions", "Full Newton seul chemin qualifié; Modified Newton hors production; pas de publication automatique"],
            ["Recommandations", "RQ-NL-11 à RQ-NL-14 pour la promotion multi-éléments/cyclique; aucune validation physique revendiquée"],
            ["Nom / rôle", "Owner"],
            ["Date", "2026-08-24"],
            ["Signature", "Décision approuvée par l'Owner"],
        ], [45 * mm, 135 * mm], styles),
        paragraph("11. Traçabilité des artefacts", styles["h1"]),
        review_table([
            ["Artefact", "Chemin"],
            ["Résumé VNV", "qualification/vnv/robustness_nonlinear_solids_024/reference/summary.json"],
            ["Corrélation RQ-G08", "qualification/external_reference_digests/rqg08_j2_common_024.json et docs/verification/rqg08_external_j2_common_024.md"],
            ["Rapport markdown", "qualification/vnv/robustness_nonlinear_solids_024/reference/report.md"],
            ["Digest", "qualification/external_reference_digests/robustness_nonlinear_solids_024.json"],
            ["État des gates", "qualification/reviews/qf_solver_0_2_4a0_gate_status.json"],
            ["Audit public", f"qualification/publication_audit_0_2_1.json - {audit.get('checks', [{}])[0].get('detail', 'audit PASS')}"],
            ["Pipeline readiness", "scripts/release_readiness_pipeline.py - dry-run / Owner-only publication"],
        ], [55 * mm, 125 * mm], styles),
        paragraph("Conclusion: le périmètre expérimental est accepté avec recommandations et RQ-G08 est fermée pour le patch affine borné. Les work packages RQ-NL-11 à RQ-NL-14 restent requis avant toute promotion multi-éléments, cyclique ou physique.", styles["note"]),
    ])
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    validate_pdf(OUTPUT, ["QF Solver 0.2.4a0", "accepted_with_recommendations", "RQ-G08", "PASS_EXTERNAL_CORRELATION_BOUNDED", "force-déplacement", "Signature"], 5)
    return OUTPUT


if __name__ == "__main__":
    print(build())
