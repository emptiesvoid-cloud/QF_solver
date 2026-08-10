"""Build a compact PDF review package for the curved MITC3+ correlation."""

from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "results" / "VNV-MITC3-LAMINATE-CURVED-PROJECTED-CALCULIX-S6-024"
DEFAULT_OUTPUT = ROOT / "output" / "pdf" / "mitc3_curved_projected_correlation_owner_review.pdf"


def main() -> int:
    output = DEFAULT_OUTPUT
    output.parent.mkdir(parents=True, exist_ok=True)
    summary = json.loads((STUDY / "summary.json").read_text(encoding="utf-8"))
    _register_fonts()
    styles = _styles()
    document = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        rightMargin=17 * mm,
        leftMargin=17 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title="QF_solver - Correlation MITC3+ courbe projetee",
        author="QF_solver project",
    )
    document.build(_story(summary, styles), onFirstPage=_footer, onLaterPages=_footer)
    if not output.exists() or output.stat().st_size < 50_000 or not output.read_bytes().startswith(b"%PDF"):
        raise RuntimeError("The MITC3+ correlation PDF was not generated correctly.")
    print(f"PDF: {output}")
    return 0


def _register_fonts() -> None:
    regular = Path("C:/Windows/Fonts/arial.ttf")
    bold = Path("C:/Windows/Fonts/arialbd.ttf")
    if regular.exists() and bold.exists():
        pdfmetrics.registerFont(TTFont("QFArial", str(regular)))
        pdfmetrics.registerFont(TTFont("QFArialBold", str(bold)))


def _styles() -> dict[str, ParagraphStyle]:
    font = "QFArial" if "QFArial" in pdfmetrics.getRegisteredFontNames() else "Helvetica"
    bold = "QFArialBold" if "QFArialBold" in pdfmetrics.getRegisteredFontNames() else "Helvetica-Bold"
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=base["Title"], fontName=bold, fontSize=18, leading=22, alignment=TA_CENTER, textColor=colors.HexColor("#17324d"), spaceAfter=9),
        "subtitle": ParagraphStyle("subtitle", parent=base["Normal"], fontName=font, fontSize=9, leading=12, alignment=TA_CENTER, textColor=colors.HexColor("#40566b"), spaceAfter=12),
        "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName=bold, fontSize=14, leading=17, textColor=colors.HexColor("#17324d"), spaceBefore=3, spaceAfter=8),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName=bold, fontSize=11, leading=14, textColor=colors.HexColor("#1e6f8f"), spaceBefore=5, spaceAfter=5),
        "body": ParagraphStyle("body", parent=base["BodyText"], fontName=font, fontSize=9, leading=12, textColor=colors.HexColor("#202c36"), spaceAfter=6),
        "small": ParagraphStyle("small", parent=base["BodyText"], fontName=font, fontSize=7.5, leading=9.5, textColor=colors.HexColor("#202c36")),
        "cell": ParagraphStyle("cell", parent=base["BodyText"], fontName=font, fontSize=7.2, leading=8.5, alignment=TA_LEFT),
        "cell_center": ParagraphStyle("cell_center", parent=base["BodyText"], fontName=font, fontSize=7.2, leading=8.5, alignment=TA_CENTER),
    }


def _story(summary: dict, styles: dict[str, ParagraphStyle]) -> list[object]:
    checks = summary["checks"]
    fine = summary["rows"][-1]
    story: list[object] = [
        Paragraph("QF_solver", styles["title"]),
        Paragraph("Correlation MITC3+ multicouche courbe a orientation projetee", styles["title"]),
        Paragraph(f"{summary['study_id']} - Owner accepted experimental - 2026-08-09", styles["subtitle"]),
        Paragraph("Decision automatique", styles["h1"]),
        Paragraph(
            f"Statut : <b>{summary['status']}</b>. Maturite : <b>{summary['maturity']}</b>. "
            f"Le maillage final {fine['nx']} x {fine['ny']} atteint un ecart vectoriel "
            f"UX/UZ de <b>{100.0 * fine['vector_difference']:.4f} %</b>.",
            styles["body"],
        ),
        Paragraph(
            "Cette preuve externe est reproductible et acceptee pour la V0.2.0-alpha au statut experimental. "
            "Elle ne constitue pas une certification et ne ferme pas les contraintes par pli, "
            "les quantites interlaminaires ou la dynamique courbe.",
            styles["body"],
        ),
        _key_value_table(summary, styles),
        PageBreak(),
        Paragraph("Convergence des deplacements", styles["h1"]),
        Paragraph(
            "Le panneau cylindrique facettise est calcule avec MITC3+ dans QF_solver et S6 COMPOSITE dans CalculiX. "
            "Les deux solveurs utilisent les memes noeuds de coin, les memes triangles, les memes charges et le meme empilement [0/90/90/0].",
            styles["body"],
        ),
        _convergence_table(summary, styles),
        Spacer(1, 5 * mm),
        _image(STUDY / "mitc3_curved_composite_calculix_correlation.png", 175 * mm, 75 * mm),
        PageBreak(),
        Paragraph("Geometrie et deformee", styles["h1"]),
        Paragraph(
            "La generatrice gauche est encastree sur les six DDL. La generatrice droite recoit +1000 N selon UX et -20 N selon UZ. "
            "La deformee est amplifiee uniquement pour la lecture graphique ; les valeurs numeriques restent celles du calcul.",
            styles["body"],
        ),
        _image(STUDY / "mitc3_curved_composite_deformation.png", 175 * mm, 105 * mm),
        PageBreak(),
        Paragraph("Orientation projetee et controles", styles["h1"]),
        Paragraph(
            "La direction globale (0.7, 1.0, 0.2) est projetee dans le plan tangent de chaque facette. "
            "Le controle angulaire est recalcule independamment avant comparaison au repere stocke.",
            styles["body"],
        ),
        _image(STUDY / "mitc3_curved_composite_projected_orientation.png", 150 * mm, 75 * mm),
        Spacer(1, 4 * mm),
        _checks_table(checks, styles),
        PageBreak(),
        Paragraph("Limites et decision Owner", styles["h1"]),
        Paragraph(
            "Le resultat montre une convergence monotone vers la reponse CalculiX : 4.7270 % a 80 x 40, "
            "3.4437 % a 96 x 48 et 2.0738 % a 128 x 64. Les premiers maillages restent presentes comme diagnostic "
            "et ne sont pas utilises pour rejeter le niveau fin.",
            styles["body"],
        ),
        Paragraph("Decision Owner du 2026-08-09 :", styles["h2"]),
        Paragraph(
            "Le perimetre est accepte pour la V0.2.0-alpha au statut experimental."
            "<br/>La maturite stable n'est pas revendiquee."
            "<br/>Les geometries courbes supplementaires, les contraintes par pli et la dynamique courbe restent recommandes.",
            styles["body"],
        ),
        Paragraph(
            "Artefacts : summary.json, report.md, vnv_manifest.json, fichiers INP/FRD/LOG/STA et PNG dans le dossier de campagne. "
            "La revue Markdown complete est disponible dans docs/verification/mitc3_laminate_curved_projected.md.",
            styles["small"],
        ),
    ]
    return story


def _key_value_table(summary: dict, styles: dict[str, ParagraphStyle]) -> Table:
    fine = summary["rows"][-1]
    rows = [
        ["Modele", "Panneau cylindrique 60 deg, L=1.0 m, R=0.5 m"],
        ["Empilement", "[0/90/90/0], 4 plis de 2.0 mm"],
        ["Maillage final", f"{fine['nx']} x {fine['ny']} - {fine['mitc3_elements']} triangles MITC3+"],
        ["Ecart final", f"{100.0 * fine['vector_difference']:.4f} % UX/UZ"],
        ["Residu QF_solver", f"{summary['checks'][3]['value']:.4e}"],
        ["Oracle externe", "CalculiX 2.20 - S6 COMPOSITE - Docker"],
    ]
    table = Table([[Paragraph(str(a), styles["cell"]), Paragraph(str(b), styles["cell"])] for a, b in rows], colWidths=[42 * mm, 128 * mm])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8f0f4")), ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#aab9c2")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    return table


def _convergence_table(summary: dict, styles: dict[str, ParagraphStyle]) -> Table:
    data = [["Maillage", "Tri", "UZ QF [m]", "UZ CCX [m]", "Ecart UX/UZ"]]
    for row in summary["rows"]:
        data.append([f"{row['nx']} x {row['ny']}", f"{row['mitc3_elements']}", f"{row['qf_uz']:.6e}", f"{row['calculix_uz']:.6e}", f"{100.0 * row['vector_difference']:.4f} %"])
    table = Table([[Paragraph(str(value), styles["cell_center"]) for value in row] for row in data], colWidths=[29 * mm, 22 * mm, 39 * mm, 39 * mm, 35 * mm], repeatRows=1)
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324d")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#aab9c2")), ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e7f3ea")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return table


def _checks_table(checks: list[dict], styles: dict[str, ParagraphStyle]) -> Table:
    data = [["Controle", "Valeur", "Limite", "Statut"]]
    for check in checks:
        data.append([check["id"], f"{check['value']:.6e}", f"{check['limit']:.6e}", check["status"]])
    table = Table([[Paragraph(str(value), styles["cell_center"]) for value in row] for row in data], colWidths=[75 * mm, 32 * mm, 32 * mm, 25 * mm], repeatRows=1)
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324d")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#aab9c2")), ("BACKGROUND", (-1, 1), (-1, -1), colors.HexColor("#e7f3ea")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return table


def _image(path: Path, width: float, height: float) -> Image:
    if not path.is_file() or path.stat().st_size == 0:
        raise FileNotFoundError(path)
    image = Image(str(path), width=width, height=height)
    image.hAlign = "CENTER"
    return image


def _footer(canvas, document) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#5d6c76"))
    canvas.drawString(17 * mm, 9 * mm, "QF_solver - correlation MITC3+ courbe - document de revue Owner")
    canvas.drawRightString(193 * mm, 9 * mm, f"Page {document.page}")
    canvas.restoreState()


if __name__ == "__main__":
    raise SystemExit(main())
