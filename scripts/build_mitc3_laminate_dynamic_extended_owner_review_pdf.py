"""Build the Owner review PDF for extended MITC3 laminate dynamics."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "mitc3_laminate_dynamic_extended_owner_review.pdf"


def main() -> int:
    styles = getSampleStyleSheet()
    styles["BodyText"].fontSize = 8.5
    styles["BodyText"].leading = 11.5
    data = [
        ["Maillage", "Tri", "Modal", "Newmark", "Harmonique"],
        ["8x2", "32", "7,5201 %", "1,7119 %", "0,9406 %"],
        ["12x3", "72", "3,9573 %", "2,3179 %", "1,3449 %"],
        ["16x4", "128", "2,5016 %", "3,4004 %", "1,9957 %"],
        ["24x6", "288", "1,7784 %", "5,5578 %", "3,2746 %"],
        ["32x8", "512", "2,0355 %", "7,2337 %", "4,2565 %"],
        ["48x12", "1152", "2,4476 %", "9,3150 %", "5,4589 %"],
        ["64x16", "2048", "2,6867 %", "10,4121 %", "6,0831 %"],
    ]
    table = Table(data, colWidths=[23 * mm, 20 * mm, 30 * mm, 30 * mm, 32 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9aa7b1")),
        ("BACKGROUND", (0, 7), (-1, 7), colors.HexColor("#fce4d6")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
    ]))
    story = [
        Paragraph("Owner review — MITC3 multicouche dynamique", styles["Title"]),
        Spacer(1, 4 * mm),
        Paragraph("DOC-OWNER-MITC3-LAM-DYN-EXTENDED-001 | revision 0.1 | ready_for_owner_review | cible : stable", styles["BodyText"]),
        Spacer(1, 4 * mm),
        Paragraph("Comparaison QF_solver MITC3+ / Code_Aster DST/TRIA3 sur le stratifié plan [0/90/90/0]. Les niveaux historiques sont complétés par les diagnostics 48x12 et 64x16.", styles["BodyText"]),
        Spacer(1, 4 * mm), table, Spacer(1, 4 * mm),
        Paragraph("Verdict technique : le niveau 64x16, avec 2048 triangles, reste au-dessus de 1 % pour les trois observables primaires (2,6867 % modal, 10,4121 % Newmark, 6,0831 % harmonique). Les résidus QF restent faibles, mais le raffinement massif ne suffit pas et l'écart est dominé par la différence de formulation MITC3+/DST. Le scope reste bloqué pour stable.", styles["BodyText"]),
        Spacer(1, 4 * mm),
        Paragraph("Q1 — Les sept niveaux, jusqu'à 64x16, couvrent-ils le domaine plan revendiqué ? OUI / NON / PARTIELLEMENT.", styles["BodyText"]),
        Paragraph("Q2 — Les écarts fins au-dessus de 1 % doivent-ils maintenir le scope hors stable ? OUI / NON / PARTIELLEMENT.", styles["BodyText"]),
        Paragraph("Q3 — Les exclusions courbure, couplage B, amortissement calibré, contraintes par pli, dommage et délamination sont-elles acceptables ? OUI / NON / PARTIELLEMENT.", styles["BodyText"]),
        Paragraph("Q4 — Décision : accepted_with_recommendations / accepted_for_bounded_engineering_use / stable / more_evidence_required.", styles["BodyText"]),
        Spacer(1, 4 * mm),
        Paragraph("Signature Owner : ________________________    Date : __________________", styles["BodyText"]),
        Spacer(1, 4 * mm),
        Paragraph("Artefacts : qualification/vnv/external/code_aster_mitc3_laminate_dynamic_refinement_037/reference/ et les campagnes historiques 021/022.", styles["BodyText"]),
    ]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    SimpleDocTemplate(str(OUTPUT), pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=13 * mm, bottomMargin=13 * mm, title="MITC3 laminate dynamic extended Owner review", author="QF_solver").build(story)
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
