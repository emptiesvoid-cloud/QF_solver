"""Build the consolidated PDF pack for TET10 J2 Owner review."""

from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
BAR = ROOT / "results" / "VNV-TET10-J2-CODEASTER-STRUCTURAL-025"
COMPLEX = ROOT / "results" / "VNV-TET10-J2-CODEASTER-COMPLEX-026"
OUTPUT = ROOT / "output" / "pdf" / "tet10_j2_owner_review_pack.pdf"


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("PackTitle", parent=base["Title"], fontSize=19, leading=23, alignment=TA_CENTER, textColor=colors.HexColor("#17324d"), spaceAfter=8 * mm),
        "subtitle": ParagraphStyle("PackSubtitle", parent=base["Normal"], fontSize=10, leading=14, alignment=TA_CENTER, textColor=colors.HexColor("#4b5d6b"), spaceAfter=8 * mm),
        "h1": ParagraphStyle("PackH1", parent=base["Heading1"], fontSize=14, leading=18, textColor=colors.HexColor("#17324d"), spaceBefore=3 * mm, spaceAfter=3 * mm),
        "h2": ParagraphStyle("PackH2", parent=base["Heading2"], fontSize=11, leading=14, textColor=colors.HexColor("#245b7a"), spaceBefore=3 * mm, spaceAfter=2 * mm),
        "body": ParagraphStyle("PackBody", parent=base["BodyText"], fontSize=9.2, leading=13, spaceAfter=2.5 * mm),
        "small": ParagraphStyle("PackSmall", parent=base["BodyText"], fontSize=7.8, leading=10, textColor=colors.HexColor("#4b5d6b")),
        "head": ParagraphStyle("PackHead", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=7.2, leading=8.5, textColor=colors.white),
        "table": ParagraphStyle("PackTable", parent=base["BodyText"], fontSize=7.2, leading=9),
    }


def _p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text, style)


def _table(rows: list[list[str]], styles: dict[str, ParagraphStyle], widths: list[float]) -> Table:
    data = []
    for index, row in enumerate(rows):
        style = styles["head"] if index == 0 else styles["table"]
        data.append([_p(str(cell), style) for cell in row])
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#245b7a")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#a9b7c1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef4f7")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def _footer(canvas, document) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#a9b7c1"))
    canvas.line(16 * mm, 13 * mm, 194 * mm, 13 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#4b5d6b"))
    canvas.drawString(16 * mm, 8 * mm, "QF_solver - dossier Owner review TET10 J2 - sans certification")
    canvas.drawRightString(194 * mm, 8 * mm, f"Page {document.page}")
    canvas.restoreState()


def _result_rows(summary: dict, *, complex_case: bool) -> list[list[str]]:
    rows = [
        ["Facteur", "UX QF", "UX Code_Aster", "UY QF", "UY Code_Aster", "PEEQ QF", "PEEQ Code_Aster"]
        if complex_case
        else ["Facteur", "UX QF", "UX Code_Aster", "PEEQ QF", "PEEQ Code_Aster"]
    ]
    for qf, aster in zip(summary["qf_rows"], summary["code_aster_rows"], strict=True):
        if complex_case:
            rows.append([
                f"{qf['load_factor']:.2f}", f"{qf['tip_ux_m']:.6e}", f"{aster['tip_ux_m']:.6e}",
                f"{qf['tip_uy_m']:.6e}", f"{aster['tip_uy_m']:.6e}",
                f"{qf['equivalent_plastic_strain_mean']:.6e}", f"{aster['equivalent_plastic_strain']:.6e}",
            ])
        else:
            rows.append([
                f"{qf['load_factor']:.2f}", f"{qf['tip_ux_m']:.6e}", f"{aster['tip_ux_m']:.6e}",
                f"{qf['equivalent_plastic_strain_mean']:.6e}", f"{aster['equivalent_plastic_strain']:.6e}",
            ])
    return rows


def build_pdf() -> Path:
    bar = json.loads((BAR / "summary.json").read_text(encoding="utf-8"))
    complex_case = json.loads((COMPLEX / "summary.json").read_text(encoding="utf-8"))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    styles = _styles()
    document = SimpleDocTemplate(str(OUTPUT), pagesize=A4, rightMargin=16 * mm, leftMargin=16 * mm, topMargin=15 * mm, bottomMargin=18 * mm, title="TET10 J2 Owner review pack", author="QF_solver")
    story = [
        _p("Dossier Owner review - TET10 J2", styles["title"]),
        _p("QF_solver 0.2.0-alpha | 9 aout 2026 | Quentin Farinazzo", styles["subtitle"]),
        _p("Objet du dossier", styles["h1"]),
        _p("Ce pack regroupe les preuves externes structurelles TET10 J2 disponibles pour la validation Owner. Le premier cas est deja accepte dans un perimetre borne. Le second cas, plus representatif, est soumis a ta nouvelle validation.", styles["body"]),
        _table([
            ["Etude", "Statut automatique", "Statut Owner", "Objet"],
            ["VNV-TET10-J2-CODEASTER-STRUCTURAL-025", bar["status"], "Acceptee le 09/08/2026", "Barre droite, charge axiale monotone"],
            ["VNV-TET10-J2-CODEASTER-COMPLEX-026", complex_case["status"], "A valider", "Support en L, charges combinees"],
        ], styles, [57 * mm, 37 * mm, 32 * mm, 52 * mm]),
        Spacer(1, 5 * mm),
        _p("Regle de maturite", styles["h2"]),
        _p("La correlation externe et la validation Owner restent bornees aux cas documentes. La famille TET10 J2 conserve la maturite <b>experimental</b> tant que les geometries complexes, les chargements combines et les chemins cycliques ne sont pas tous revus.", styles["body"]),
        PageBreak(),
        _p("1. Cas 025 - barre droite", styles["h1"]),
        _p("Ce cas a ete valide par l'Owner pour un usage interne experimental borne. Le meme maillage comporte 341 noeuds et 140 TET10/TETRA10. Le resultat final est un ecart UX de 0,03175 %, un ecart PEEQ RMS de 0,55084 % et un residu maximal de 7,40079e-11.", styles["body"]),
        _table(_result_rows(bar, complex_case=False), styles, [18 * mm, 39 * mm, 42 * mm, 36 * mm, 40 * mm]),
        Spacer(1, 4 * mm),
        Image(str(BAR / "comparison.png"), width=178 * mm, height=81 * mm),
        Spacer(1, 2 * mm),
        Image(str(BAR / "deformation.png"), width=145 * mm, height=96 * mm),
        PageBreak(),
        _p("2. Cas 026 - support en L a chargement combine", styles["h1"]),
        _p("La geometrie est un support en L obtenu par fusion de deux volumes. Le maillage commun comporte 1 039 noeuds et 457 TET10/TETRA10. La face superieure est encastree. La face terminale recoit FX = 3 MN et FY = -6 MN, repartis sur les noeuds de la face.", styles["body"]),
        _p("Les cinq facteurs de charge sont 0,25, 0,50, 0,75, 1,00 et 1,10. Le ratio deplacement final / longueur globale vaut 1,95357 %, ce qui maintient le cas dans la garde de petites deformations definie pour cette campagne.", styles["body"]),
        _table(_result_rows(complex_case, complex_case=True), styles, [15 * mm, 28 * mm, 31 * mm, 28 * mm, 31 * mm, 28 * mm, 31 * mm]),
        Spacer(1, 3 * mm),
        Image(str(COMPLEX / "comparison.png"), width=178 * mm, height=73 * mm),
        PageBreak(),
        _p("3. Controle et questions Owner - cas 026", styles["h1"]),
        _table([
            ["Controle", "Valeur", "Limite", "Statut"],
            ["RMS chemin deplacement combine", "0,01245 %", "10 %", "PASS"],
            ["Ecart final deplacement combine", "0,00227 %", "10 %", "PASS"],
            ["RMS chemin PEEQ moyen", "1,84443 %", "15 %", "PASS"],
            ["Ratio petites deformations", "1,95357 %", "10 %", "PASS"],
            ["Residu QF maximal", "1,97226e-09", "1e-7", "PASS"],
        ], styles, [69 * mm, 35 * mm, 35 * mm, 25 * mm]),
        Spacer(1, 5 * mm),
        _p("Questions a valider", styles["h2"]),
        _table([
            ["Question", "Reponse"],
            ["Q1. La geometrie en L et le maillage TET10 sont-ils suffisamment representatifs pour cette etape ?", "OUI / NON"],
            ["Q2. Les charges combinees FX = 3 MN et FY = -6 MN sont-elles correctement definies ?", "OUI / NON"],
            ["Q3. Les ecarts deplacement et PEEQ sont-ils acceptables ?", "OUI / NON"],
            ["Q4. Le controle de petites deformations est-il suffisant pour accepter ce cas borne ?", "OUI / NON"],
            ["Q5. Les contraintes aux angles rentrants restent-elles hors acceptance ponctuelle ?", "OUI / NON"],
            ["Q6. Decision sur le cas 026", "accepted / accepted_with_recommendations / more_evidence_required / rejected"],
        ], styles, [126 * mm, 52 * mm]),
        Spacer(1, 7 * mm),
        _p("Commentaires Owner :", styles["body"]),
        Spacer(1, 13 * mm),
        _p("Nom : Quentin Farinazzo    Signature : ____________________    Date : ____ / ____ / ______", styles["body"]),
        PageBreak(),
        _p("4. Limites et artefacts", styles["h1"]),
        _p("Les deux preuves utilisent une plasticite J2 isotrope a petites deformations et un ecrouissage isotrope lineaire. Elles ne couvrent pas le cyclage, les grandes deformations, le contact, le dommage, la rupture, le flambement ni l'acceptation des contraintes ponctuelles en singularite.", styles["body"]),
        _p("Reproduction du cas 026", styles["h2"]),
        _p("python .\\scripts\\run_code_aster_tet10_j2_complex_vnv.py --output .\\results\\VNV-TET10-J2-CODEASTER-COMPLEX-026", styles["small"]),
        _p("Artefacts : model.json, results.json, summary.json, report.md, deformation.vtu, maillage MSH, sorties Code_Aster, figures et manifeste SHA-256.", styles["body"]),
        _p("Documents associes", styles["h2"]),
        _p("docs/verification/tet10_j2_structural_code_aster.md<br/>docs/verification/tet10_j2_complex_code_aster.md<br/>qualification/reviews/tet10_j2_structural_code_aster_2026-08-09.json", styles["body"]),
    ]
    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return OUTPUT


if __name__ == "__main__":
    print(build_pdf())
