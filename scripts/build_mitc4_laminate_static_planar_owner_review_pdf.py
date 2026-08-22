"""Build the Owner review PDF for the planar MITC4 laminate sub-scope."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "mitc4_laminate_static_planar_stable_owner_review.pdf"


def main() -> int:
    styles = getSampleStyleSheet()
    styles["BodyText"].fontSize = 8.5
    styles["BodyText"].leading = 11.5
    data = [
        ["Observable", "Valeur", "Limite", "Verdict"],
        ["Membrane, erreur L2", "0,00389 %", "1 %", "PASS"],
        ["Flexion, erreur L2", "0,25389 %", "1 %", "PASS"],
        ["Combiné, erreur L2", "0,03791 %", "1 %", "PASS"],
        ["QF / NAFEMS", "0,45761 %", "1 %", "PASS"],
        ["Code_Aster / NAFEMS", "0,71029 %", "1 %", "PASS"],
        ["QF / Code_Aster", "0,87852 %", "1 %", "PASS"],
        ["Résidu libre", "2,457e-10", "1e-8", "PASS"],
    ]
    table = Table(data, colWidths=[68 * mm, 32 * mm, 28 * mm, 24 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9aa7b1")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
    ]))
    story = [
        Paragraph("Owner review — MITC4 multicouche statique plan régulier", styles["Title"]),
        Spacer(1, 4 * mm),
        Paragraph("DOC-OWNER-MITC4-LAM-STAT-PLANAR-001 | revision 0.1 | ready_for_owner_review | cible : stable", styles["BodyText"]),
        Spacer(1, 4 * mm),
        Paragraph("Sous-périmètre : plaque plane MITC4 [0/90/90/0], petits déplacements, trois chargements et trois niveaux de maillage. La règle impose <= 1 % sur les observables principales.", styles["BodyText"]),
        Spacer(1, 4 * mm), table, Spacer(1, 4 * mm),
        Paragraph("Le cas courbe oblique à 2,043 % et le maillage distordu à 1,0557 % restent hors de ce sous-périmètre stable. Ils ne sont ni supprimés ni extrapolés.", styles["BodyText"]),
        Spacer(1, 4 * mm),
        Paragraph("Q1 — Le domaine plan régulier et ses trois chargements sont-ils suffisamment définis pour stable ? OUI / NON / PARTIELLEMENT.", styles["BodyText"]),
        Paragraph("Q2 — Les erreurs <= 1 % et le résidu 2,457e-10 sont-ils acceptables ? OUI / NON / PARTIELLEMENT.", styles["BodyText"]),
        Paragraph("Q3 — Les exclusions courbes, distordues, S13/S23, singularités, dommage et délamination sont-elles acceptables ? OUI / NON / PARTIELLEMENT.", styles["BodyText"]),
        Paragraph("Q4 — Décision : stable / accepted_with_recommendations / accepted_for_bounded_engineering_use / more_evidence_required.", styles["BodyText"]),
        Spacer(1, 4 * mm),
        Paragraph("Signature Owner : ________________________    Date : __________________", styles["BodyText"]),
        Spacer(1, 4 * mm),
        Paragraph("Artefacts : qualification/maturity_evidence_0_2_1/mitc4_laminate_static_planar.json", styles["BodyText"]),
    ]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    SimpleDocTemplate(
        str(OUTPUT), pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm,
        topMargin=13 * mm, bottomMargin=13 * mm,
        title="MITC4 laminate planar stable Owner review", author="QF_solver",
    ).build(story)
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
