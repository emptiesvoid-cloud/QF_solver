"""Build the printable Owner-review pack for open linear-dynamic scopes."""

from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "owner_review_dynamique_lineaire.pdf"
CASES = (
    (
        "TET4 dynamique lineaire",
        ("tet4-modal", "tet4-transient-dynamic", "tet4-harmonic-response"),
        ROOT / "qualification/vnv/tet4_dynamic_code_aster/reference/summary.json",
        ROOT / "qualification/vnv/tet4_dynamic_code_aster/reference/comparison.png",
    ),
    (
        "TET10 dynamique lineaire",
        ("tet10-modal", "tet10-transient-dynamic", "tet10-harmonic-response"),
        ROOT / "qualification/vnv/tet10_dynamic_code_aster/reference/summary.json",
        ROOT / "qualification/vnv/tet10_dynamic_code_aster/reference/comparison.png",
    ),
    (
        "MITC3+ dynamique lineaire",
        ("mitc3-modal", "mitc3-transient-dynamic", "mitc3-harmonic-response"),
        ROOT / "qualification/vnv/mitc3_dynamic_code_aster/reference/summary.json",
        ROOT / "qualification/vnv/mitc3_dynamic_code_aster/reference/comparison.png",
    ),
    (
        "BEAM2 dynamique lineaire",
        ("beam2-linear-dynamics",),
        ROOT / "qualification/vnv/external/code_aster_beam2_transverse/reference/summary.json",
        ROOT / "qualification/vnv/external/code_aster_beam2_transverse/reference/comparison.png",
    ),
    (
        "Ressort et masse SDOF",
        ("discrete-linear-dynamics",),
        ROOT / "qualification/vnv/external/code_aster_discrete/reference/summary.json",
        None,
    ),
)


def _styles() -> dict[str, ParagraphStyle]:
    styles = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=19, leading=23, textColor=colors.HexColor("#123B4A"), alignment=TA_CENTER),
        "h1": ParagraphStyle("h1", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=14, leading=18, textColor=colors.HexColor("#123B4A"), spaceBefore=8, spaceAfter=6),
        "body": ParagraphStyle("body", parent=styles["BodyText"], fontName="Helvetica", fontSize=9, leading=13),
        "small": ParagraphStyle("small", parent=styles["BodyText"], fontName="Helvetica", fontSize=7.5, leading=10),
    }


def _table(rows: list[list[str]], widths: list[float]) -> Table:
    table = Table(rows, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#123B4A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("LEADING", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#AAB7B8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), (colors.white, colors.HexColor("#F4F7F7"))),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def _check_rows(summary: dict[str, object]) -> list[list[str]]:
    rows = [["Controle", "Valeur", "Limite", "Statut"]]
    for check in summary.get("checks", []):
        value = 100.0 * float(check["value"])
        limit = 100.0 * float(check["limit"])
        rows.append([str(check["id"]), f"{value:.5g} %", f"{limit:.5g} %", str(check["status"])])
    return rows


def _footer(canvas, document) -> None:  # type: ignore[no-untyped-def]
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#425563"))
    canvas.drawString(1.6 * cm, 1.0 * cm, "QF_solver - dossier Owner review dynamique lineaire - non certifiant")
    canvas.drawRightString(A4[0] - 1.6 * cm, 1.0 * cm, f"Page {document.page}")
    canvas.restoreState()


def build(output: Path = OUTPUT) -> Path:
    """Build a static PDF; all decision cells intentionally remain blank."""
    output.parent.mkdir(parents=True, exist_ok=True)
    styles = _styles()
    story = [
        Spacer(1, 1.5 * cm),
        Paragraph("Dossier Owner review - dynamique lineaire", styles["title"]),
        Spacer(1, 0.5 * cm),
        Paragraph("Ce dossier rassemble les preuves automatiques disponibles. Aucune maturite n'est modifiee et aucune decision n'est pre-remplie.", styles["body"]),
        Spacer(1, 0.4 * cm),
        _table([["Famille", "Scopes a decider", "Oracle"], *[[title, ", ".join(scopes), "Code_Aster 18.1.0 Docker" if path.exists() else "non disponible"] for title, scopes, path, _ in CASES]], [4.5 * cm, 7.4 * cm, 5.0 * cm]),
        PageBreak(),
    ]
    for index, (title, scopes, path, figure) in enumerate(CASES):
        summary = json.loads(path.read_text(encoding="utf-8"))
        story.extend([
            Paragraph(title, styles["h1"]),
            Paragraph(f"Etude: <b>{summary.get('study_id', 'non declaree')}</b>. Statut automatise: <b>{summary.get('status', 'non declare')}</b>.", styles["body"]),
            Spacer(1, 0.2 * cm),
            _table(_check_rows(summary), [7.5 * cm, 3.0 * cm, 3.0 * cm, 2.2 * cm]),
            Spacer(1, 0.2 * cm),
            Paragraph("Limites: " + " ".join(str(item) for item in summary.get("limitations", [])), styles["small"]),
            Spacer(1, 0.25 * cm),
        ])
        if figure and figure.is_file():
            image = Image(str(figure))
            image._restrictSize(16.0 * cm, 8.8 * cm)
            story.extend([image, Spacer(1, 0.2 * cm)])
        story.extend([
            Paragraph("Decision Owner", styles["h1"]),
            _table([["Scope", "Decision", "Domaine accepte / exclusions / recommandations"], *[[scope, "a renseigner", "a renseigner"] for scope in scopes]], [4.7 * cm, 4.4 * cm, 6.6 * cm]),
            Paragraph("Decision admise: accepted_for_bounded_engineering_use, accepted_with_recommendations, more_evidence_required ou rejected.", styles["small"]),
        ])
        if index != len(CASES) - 1:
            story.append(PageBreak())
    document = SimpleDocTemplate(str(output), pagesize=A4, rightMargin=1.6 * cm, leftMargin=1.6 * cm, topMargin=1.4 * cm, bottomMargin=1.7 * cm, title="QF_solver - Owner review dynamique lineaire")
    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    if not output.is_file() or output.stat().st_size < 10_000:
        raise RuntimeError(f"Incomplete review PDF: {output}")
    return output


if __name__ == "__main__":
    print(build())
