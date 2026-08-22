"""Build the Owner review PDF for the extended orthotropic static campaign."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "orthotropic_static_extended_owner_review.pdf"


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    styles["BodyText"].fontSize = 9
    styles["BodyText"].leading = 12
    story = [
        Paragraph("Owner review — orthotropie statique TET4/TET10", styles["Title"]),
        Spacer(1, 4 * mm),
        Paragraph("DOC-OWNER-ORTHO-STATIC-EXTENDED-001 | revision 0.1 | ready_for_owner_review | cible : stable", styles["BodyText"]),
        Spacer(1, 4 * mm),
        Paragraph("Extension : niveau TET4 vectorisé large h=0,020 m, onze niveaux au total. La référence reste le TET10 h=0,09 m. Le gate d'ingénierie impose une erreur principale finale <= 1 %.", styles["BodyText"]),
        Spacer(1, 4 * mm),
    ]
    data = [
        ["Famille", "Niveau", "Éléments", "Déplacement", "Énergie", "Résidu"],
        ["TET4", "h=0,020 m", "564525", "0,8772 %", "0,8647 %", "9,963e-9"],
        ["TET10", "h=0,13 m", "2607", "0,2918 %", "0,3027 %", "7,263e-12"],
    ]
    table = Table(data, colWidths=[22 * mm, 28 * mm, 25 * mm, 28 * mm, 24 * mm, 25 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9aa7b1")),
        ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#e2f0d9")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
    ]))
    story += [table, Spacer(1, 4 * mm), Paragraph("Verdict technique : TET10 et TET4 passent sous 1 %. Le niveau TET4 h=0,020 m utilise l'assemblage vectorisé large et CG/Jacobi, avec 2 510 itérations et un résidu libre de 9,963e-9. La promotion reste soumise à la décision Owner.", styles["BodyText"]), Spacer(1, 4 * mm)]
    questions = [
        "Q1 — Les onze niveaux TET4 et quatre niveaux TET10 montrent-ils une convergence suffisante dans le domaine orthotrope déclaré ? OUI / NON / PARTIELLEMENT.",
        "Q2 — Les erreurs TET4 (0,8772 % déplacement, 0,8647 % énergie) et TET10 sous 1 % sont-elles acceptables pour le périmètre statique déclaré ? OUI / NON / PARTIELLEMENT.",
        "Q3 — Les exclusions orientation courbe continue, composite pli par pli, dommage, plasticité anisotrope et singularités sont-elles acceptables ? OUI / NON / PARTIELLEMENT.",
        "Q4 — Décision : accepted_with_recommendations / accepted_for_bounded_engineering_use / stable / more_evidence_required.",
    ]
    for question in questions:
        story += [Paragraph(question, styles["BodyText"]), Spacer(1, 2.5 * mm)]
    story += [Paragraph("Commentaire Owner : ____________________________________________", styles["BodyText"]), Spacer(1, 3 * mm), Paragraph("Signature : ________________________    Date : __________________", styles["BodyText"]), Spacer(1, 4 * mm), Paragraph("Artefacts : qualification/vnv/orthotropic_solid_convergence_large_cg_006/reference/", styles["BodyText"])]
    SimpleDocTemplate(str(OUTPUT), pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=13 * mm, bottomMargin=13 * mm, title="Orthotropic static extended Owner review", author="QF_solver").build(story)
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
