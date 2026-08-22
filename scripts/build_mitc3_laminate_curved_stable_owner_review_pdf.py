"""Build the Owner review PDF for the refined MITC3 curved laminate campaign."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "mitc3_laminate_curved_stable_owner_review.pdf"


def main() -> int:
    styles = getSampleStyleSheet()
    styles["BodyText"].fontSize = 8.4
    styles["BodyText"].leading = 11.2
    data = [
        ["Grandeur", "Mixte", "Transverse", "Axiale", "Limite", "Verdict"],
        ["Ecart QF / Code_Aster a 64x32", "0,6090 %", "0,5278 %", "0,9066 %", "1 %", "PASS"],
        ["Increment QF 48x24 -> 64x32", "4,3269 %", "4,4486 %", "8,2619 %", "5 %", "FAIL axial"],
        ["Increment Code_Aster 48x24 -> 64x32", "4,6118 %", "4,7110 %", "7,8823 %", "5 %", "FAIL axial"],
        ["Residu libre QF", "4,525e-11", "2,636e-9", "4,739e-12", "1e-7", "PASS"],
    ]
    table = Table(data, colWidths=[44 * mm, 22 * mm, 24 * mm, 22 * mm, 18 * mm, 24 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9aa7b1")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
    ]))
    story = [
        Paragraph("Owner review — MITC3 multicouche courbe raffinée", styles["Title"]),
        Spacer(1, 4 * mm),
        Paragraph("DOC-OWNER-MITC3-LAM-CURVED-STABLE-001 | revision 0.1 | ready_for_owner_review | cible : stable", styles["BodyText"]),
        Spacer(1, 4 * mm),
        Paragraph("Panneau cylindrique facettisé, orientation projetée, [0/90/90/0], trois chargements et niveaux jusqu'à 64x32. Le deck Code_Aster utilise maintenant exactement les constantes matériau de QF_solver : E1=130 GPa, E2=9 GPa, nu12=0,28, G13=4 GPa, G23=3,5 GPa, rho=1550 kg/m3. Les trois corrélations principales sont <= 1 %, mais l'incrément axial dépasse encore 5 %.", styles["BodyText"]),
        Spacer(1, 4 * mm), table, Spacer(1, 4 * mm),
        Paragraph("Le raffinement axial ciblé 64x32 -> 96x48 -> 128x64 réduit l'incrément à 3,17 % côté QF_solver et 2,74 % côté Code_Aster, mais l'écart externe remonte à 1,336 % puis 1,570 %. Le désaccord axial n'est donc pas expliqué uniquement par le maillage.", styles["BodyText"]),
        Spacer(1, 4 * mm),
        Paragraph("Les exclusions restent strictes : autres géométries, stratifiés non symétriques, dynamique courbe, contraintes interlaminaires, dommage, rupture et délamination.", styles["BodyText"]),
        Spacer(1, 4 * mm),
        Paragraph("Q1 — Domaine suffisamment défini pour stable ? OUI / NON / PARTIELLEMENT.", styles["BodyText"]),
        Paragraph("Q2 — Les erreurs <= 1 % et les incréments axiaux > 5 % permettent-ils stable ? OUI / NON / PARTIELLEMENT.", styles["BodyText"]),
        Paragraph("Q3 — Exclusions acceptables ? OUI / NON / PARTIELLEMENT.", styles["BodyText"]),
        Paragraph("Q4 — Décision : stable / accepted_with_recommendations / accepted_for_bounded_engineering_use / more_evidence_required.", styles["BodyText"]),
        Spacer(1, 4 * mm),
        Paragraph("Signature Owner : ________________________    Date : __________________", styles["BodyText"]),
        Spacer(1, 4 * mm),
        Paragraph("Artefacts : qualification/vnv/external/code_aster_mitc3_curved_laminate_material_fix_033/reference/ (campagne finale 64x32) et qualification/vnv/external/code_aster_mitc3_curved_laminate_material_fix_034_axial/reference/ (raffinement axial)", styles["BodyText"]),
    ]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    SimpleDocTemplate(str(OUTPUT), pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=13 * mm, bottomMargin=13 * mm, title="MITC3 curved laminate stable Owner review", author="QF_solver").build(story)
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
