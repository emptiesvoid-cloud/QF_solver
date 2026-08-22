"""Build the Owner review PDF for the MITC4 laminate dynamic layups."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "mitc4_laminate_dynamic_extended_owner_review.pdf"


def main() -> int:
    styles = getSampleStyleSheet()
    styles["BodyText"].fontSize = 8.5
    styles["BodyText"].leading = 11.5
    data = [
        ["Empilement", "Modal", "Newmark", "Harmonique", "Résidu modal"],
        ["[0/90/90/0]", "0,1303 %", "0,0272 %", "0,0144 %", "9,642e-09"],
        ["[45/-45/-45/45]", "0,3792 %", "0,4841 %", "0,2613 %", "7,409e-08"],
        ["[0/45/45/0] amorti", "0,1281 %", "0,0669 %", "0,0349 %", "2,163e-09"],
    ]
    table = Table(data, colWidths=[42 * mm, 28 * mm, 30 * mm, 32 * mm, 28 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9aa7b1")),
        ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#fce4d6")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
    ]))
    story = [
        Paragraph("Owner review — MITC4 multicouche dynamique", styles["Title"]),
        Spacer(1, 4 * mm),
        Paragraph("DOC-OWNER-MITC4-LAM-DYN-EXTENDED-001 | revision 0.2 | owner_reviewed | stable borné", styles["BodyText"]),
        Spacer(1, 4 * mm),
        Paragraph("Trois empilements symétriques MITC4 sont comparés à Code_Aster DST sur les niveaux 24x6, 36x9 et 48x12. Le tableau montre le niveau final ; la règle d'ingénierie impose <= 1 % sur les observables principaux.", styles["BodyText"]),
        Spacer(1, 4 * mm), table, Spacer(1, 4 * mm),
        Paragraph("Verdict technique : les trois empilements passent sous 1 % au niveau 48x12 et le résidu modal maximal vaut 7,409e-08. Le niveau intermédiaire 36x9 dépasse encore 1 % pour l'angle-ply en Newmark et harmonique ; le raffinement final est donc nécessaire. Décision Owner du 21/08/2026 : promotion stable pour le sous-périmètre plan documenté, avec exclusions conservées.", styles["BodyText"]),
        Spacer(1, 4 * mm),
        Paragraph("Q1 — Les trois empilements couvrent-ils le domaine dynamique plan déclaré ? OUI.", styles["BodyText"]),
        Paragraph("Q2 — Les trois empilements sont-ils acceptables au niveau final 48x12 malgré les dépassements observés au niveau intermédiaire 36x9 ? OUI.", styles["BodyText"]),
        Paragraph("Q3 — Les exclusions courbure, couplage B, amortissement calibré, dommage, rupture et délamination sont-elles acceptables ? OUI.", styles["BodyText"]),
        Paragraph("Q4 — Décision : STABLE pour le sous-périmètre déclaré ; registre machine-readable : accepted_with_recommendations, cible stable.", styles["BodyText"]),
        Spacer(1, 4 * mm),
        Paragraph("Owner : Quentin Farinazzo (déclaration électronique)    Date : 2026-08-21", styles["BodyText"]),
        Spacer(1, 4 * mm),
        Paragraph("Artefacts : qualification/vnv/external/code_aster_mitc4_laminate_dynamic_refinement_48x12_032/reference/ et le ledger de preuve 0.2.1.", styles["BodyText"]),
    ]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    SimpleDocTemplate(str(OUTPUT), pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=13 * mm, bottomMargin=13 * mm, title="MITC4 laminate dynamic extended Owner review", author="QF_solver").build(story)
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
