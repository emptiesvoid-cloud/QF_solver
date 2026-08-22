"""Build the compact PDF Owner review for refined TET10 J2 evidence."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "tet10_j2_complex_refined_owner_review.pdf"


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    styles["Title"].fontName = "Helvetica-Bold"
    styles["BodyText"].leading = 13
    styles["BodyText"].fontSize = 9
    doc = SimpleDocTemplate(str(OUTPUT), pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=13 * mm, bottomMargin=13 * mm, title="TET10 J2 refined Owner review", author="QF_solver")
    story = [
        Paragraph("Owner review — TET10 J2 complexe raffiné", styles["Title"]),
        Spacer(1, 5 * mm),
        Paragraph("DOC-OWNER-TET10-J2-REFINED-001 | revision 0.1 | ready_for_owner_review | promotion target: stable", styles["BodyText"]),
        Spacer(1, 4 * mm),
        Paragraph("Objet : équerre ré-entrante TET10 à charges combinées UX/UY, comparaison sur maillages identiques avec Code_Aster 18.1.0 (TETRA10, VMIS_ISOT_LINE). La règle QF_solver impose une erreur mécanique primaire inférieure ou égale à 1 %. L'observable primaire est le PEEQ RMS.", styles["BodyText"]),
        Spacer(1, 4 * mm),
    ]
    data = [
        ["Taille", "Éléments", "PEEQ RMS", "Déplacement RMS", "Résidu max"],
        ["0,32", "457", "1,8444 %", "0,01245 %", "1,972e-09"],
        ["0,24", "911", "1,4881 %", "0,02885 %", "4,917e-11"],
        ["0,16", "2217", "0,8867 %", "0,008997 %", "4,666e-11"],
    ]
    table = Table(data, colWidths=[22 * mm, 22 * mm, 27 * mm, 32 * mm, 28 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9aa7b1")),
        ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#e2f0d9")),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story += [table, Spacer(1, 4 * mm), Paragraph("Verdict technique : PASS pour le cas raffiné, car le PEEQ RMS fin vaut 0,8867 %, sous le seuil de 1 %. Cette preuve reste bornée au modèle, aux petites déformations, à la plasticité J2 isotrope et aux observables globales.", styles["BodyText"]), Spacer(1, 4 * mm)]
    questions = [
        "Q1 — Les trois niveaux de raffinement, les charges combinées et la comparaison Code_Aster couvrent-ils suffisamment le domaine TET10 J2 à petites déformations revendiqué ? Réponse : OUI / NON / PARTIELLEMENT.",
        "Q2 — Le PEEQ RMS fin de 0,8867 %, inférieur au seuil primaire de 1 %, est-il acceptable, avec les singularités ponctuelles hors critère ? Réponse : OUI / NON / PARTIELLEMENT.",
        "Q3 — Les exclusions grandes déformations, chargement cyclique, contact, rupture, dommage, flambement et singularités restent-elles acceptables ? Réponse : OUI / NON / PARTIELLEMENT.",
        "Q4 — Décision : accepted_with_recommendations / accepted_for_bounded_engineering_use / stable / more_evidence_required.",
    ]
    for question in questions:
        story += [Paragraph(question, styles["BodyText"]), Spacer(1, 2.5 * mm)]
    story += [Paragraph("Commentaire Owner : ________________________________________________", styles["BodyText"]), Spacer(1, 3 * mm), Paragraph("Signature : __________________________    Date : __________________", styles["BodyText"]), Spacer(1, 4 * mm), Paragraph("Artefacts : qualification/vnv/external/code_aster_tet10_j2_complex_refinement_strict/reference/ | Commande : python scripts/build_tet10_j2_refinement_evidence.py", styles["BodyText"])]
    doc.build(story)
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
