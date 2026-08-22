"""Build the dated Owner decision register for the 0.2.1a0 stable scopes."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "qualification" / "reviews" / "owner_stable_promotion_2026-08-21.json"
AUDIT = ROOT / "results" / "maturity_promotion_final_20260821_v19" / "maturity_promotion_audit.json"
OUTPUT = ROOT / "output" / "pdf" / "qf_solver_owner_decision_register_stable_0_2_1_20260821.pdf"


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("Title", parent=base["Title"], fontName="Helvetica-Bold", fontSize=20, leading=25, textColor=colors.HexColor("#17365D")),
        "h1": ParagraphStyle("H1", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=14, leading=18, textColor=colors.HexColor("#17365D"), spaceBefore=8, spaceAfter=5),
        "body": ParagraphStyle("Body", parent=base["BodyText"], fontName="Helvetica", fontSize=9, leading=13, spaceAfter=5),
        "note": ParagraphStyle("Note", parent=base["BodyText"], fontName="Helvetica-Oblique", fontSize=8, leading=11, textColor=colors.HexColor("#555555")),
    }


def _table(rows: list[list[str]], widths: list[float]) -> Table:
    body = ParagraphStyle("TableBody", fontName="Helvetica", fontSize=7.2, leading=8.8, wordWrap="CJK")
    header = ParagraphStyle("TableHeader", parent=body, fontName="Helvetica-Bold", textColor=colors.white)
    wrapped = [
        [Paragraph(escape(str(value)), header if index == 0 else body) for value in row]
        for index, row in enumerate(rows)
    ]
    table = Table(wrapped, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17365D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#A8B7C9")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F6F9")]),
    ]))
    return table


def _footer(canvas: Any, document: Any) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#555555"))
    canvas.drawString(15 * mm, 10 * mm, "QF_solver | Owner decision register | 2026-08-21 | Internal V&V record")
    canvas.drawRightString(A4[0] - 15 * mm, 10 * mm, f"Page {document.page}")
    canvas.restoreState()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build() -> Path:
    review = _load(REVIEW)
    audit = _load(AUDIT)
    rows = {str(row["scope"]): row for row in audit["scopes"]}
    accepted = [str(scope) for scope in review["scope"]]
    retained = review["retained_non_stable_scopes"]
    open_rows = [
        row for row in audit["scopes"]
        if row["promotion_gate"].startswith("BLOCKED")
    ]
    styles = _styles()
    story: list[Any] = [
        Spacer(1, 28 * mm),
        Paragraph("QF_solver", styles["title"]),
        Spacer(1, 5 * mm),
        Paragraph("Registre de decisions Owner - promotion stable 0.2.1a0", styles["h1"]),
        Paragraph("Decision enregistree le 21 aout 2026. Ce document est un registre interne de maturite; il ne constitue ni une certification externe ni une equivalence generale avec un autre solveur.", styles["body"]),
        Spacer(1, 5 * mm),
        _table([
            ["Owner", "Decision", "Cible", "Scopes promus"],
            [review["owner"], review["decision"], review["promotion_target"], str(len(accepted))],
        ], [40 * mm, 55 * mm, 27 * mm, 45 * mm]),
        Spacer(1, 8 * mm),
        Paragraph("Decision", styles["h1"]),
        Paragraph("Les scopes ci-dessous sont promus vers stable dans leurs domaines explicitement documentes. Les limites, exclusions, observables d'acceptation et maillages de reference restent obligatoires.", styles["body"]),
    ]
    promoted_rows = [["Scope", "Etat audit", "Gate", "Decision"]]
    for scope in accepted:
        row = rows[scope]
        promoted_rows.append([scope, row["current_status"], row["promotion_gate"], "stable accepte"])
    story.append(_table(promoted_rows, [63 * mm, 31 * mm, 42 * mm, 31 * mm]))
    story.extend([PageBreak(), Paragraph("Conditions et exclusions conservees", styles["h1"])])
    for index, condition in enumerate(review["conditions"], start=1):
        story.append(Paragraph(f"{index}. {condition}", styles["body"]))
    story.extend([Spacer(1, 4 * mm), Paragraph("Scopes explicitement non promus vers stable", styles["h1"])])
    story.append(_table(
        [["Scope", "Statut conserve", "Motif"]] + [[item["scope"], item["status"], item["reason"]] for item in retained],
        [52 * mm, 48 * mm, 67 * mm],
    ))
    story.extend([Spacer(1, 6 * mm), Paragraph("Gates ouverts vers stable", styles["h1"]), Paragraph("Les gates ci-dessous ne sont pas couverts par cette decision et restent ouverts jusqu'a fermeture de leurs preuves techniques ou de leur revue requise.", styles["body"])])
    story.append(_table(
        [["Scope", "Gate", "Motif"]] + [
            [row["scope"], row["promotion_gate"], ", ".join(row["blocking_criteria"]) or "decision Owner requise"]
            for row in open_rows
        ],
        [65 * mm, 44 * mm, 58 * mm],
    ))
    story.extend([
        Spacer(1, 8 * mm),
        Paragraph("Signature enregistree", styles["h1"]),
        Paragraph(
            f"{review['signature']['name']} | {review['signature']['date']} | "
            f"{review['signature']['type']} | independance : {review['signature']['independence']}",
            styles["body"],
        ),
        Paragraph("Sources controlees : qualification/reviews/owner_stable_promotion_2026-08-21.json et results/maturity_promotion_final_20260821_v19/maturity_promotion_audit.json.", styles["note"]),
    ])
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(str(OUTPUT), pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm, bottomMargin=17 * mm, title="QF_solver Owner stable decision register")
    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    reader = PdfReader(str(OUTPUT))
    text = "".join(page.extract_text() or "" for page in reader.pages)
    if len(reader.pages) < 2 or "Gates ouverts vers stable" not in text or "stable accepte" not in text:
        raise RuntimeError("Owner decision register PDF validation failed.")
    return OUTPUT


if __name__ == "__main__":
    print(build())
