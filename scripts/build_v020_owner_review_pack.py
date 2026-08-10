"""Build the remaining QF_solver 0.2.0-alpha Owner-review PDF pack."""

from __future__ import annotations

import json
from datetime import date
from html import escape
from pathlib import Path

from PIL import Image as PilImage
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "qf_solver_v020_alpha_owner_review_remaining.pdf"
MITC4_RESULTS = ROOT / "results" / "VNV-MITC4-LAMINATE-LAYUPS-CODEASTER-DST-021-20260809"


def main() -> int:
    """Generate and validate the portable release-review pack."""
    summary = json.loads((MITC4_RESULTS / "summary.json").read_text(encoding="utf-8"))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=17 * mm,
        rightMargin=17 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="QF_solver 0.2.0-alpha - Owner review restante",
        author="QF_solver",
    )
    styles = _styles()
    story = _cover(styles)
    story.extend(_mitc4_laminate_review(styles, summary))
    story.extend(_release_closure(styles))
    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    _validate(OUTPUT)
    print(OUTPUT)
    return 0


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title", parent=base["Title"], fontName="Helvetica-Bold", fontSize=21,
            leading=25, alignment=TA_CENTER, textColor=colors.HexColor("#17324d"),
        ),
        "subtitle": ParagraphStyle(
            "subtitle", parent=base["BodyText"], fontName="Helvetica", fontSize=10.5,
            leading=14, alignment=TA_CENTER, textColor=colors.HexColor("#38536a"),
        ),
        "h1": ParagraphStyle(
            "h1", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=15,
            leading=19, spaceBefore=6, spaceAfter=6, textColor=colors.HexColor("#17324d"),
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=11,
            leading=14, spaceBefore=6, spaceAfter=4, textColor=colors.HexColor("#245d78"),
        ),
        "body": ParagraphStyle(
            "body", parent=base["BodyText"], fontName="Helvetica", fontSize=9.2,
            leading=13, spaceAfter=5,
        ),
        "note": ParagraphStyle(
            "note", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=9.2,
            leading=13, textColor=colors.HexColor("#7a3e00"), backColor=colors.HexColor("#fff4df"),
            borderPadding=7, spaceAfter=7,
        ),
    }


def _cover(styles: dict[str, ParagraphStyle]) -> list[object]:
    return [
        Spacer(1, 36 * mm),
        Paragraph("QF_solver", styles["title"]),
        Spacer(1, 5 * mm),
        Paragraph("Paquet Owner Review restant - version 0.2.0-alpha", styles["subtitle"]),
        Spacer(1, 20 * mm),
        Paragraph("Objet", styles["h1"]),
        Paragraph(
            "Ce paquet contient la seule Owner Review actuellement prete a une decision "
            "mecanique : le domaine dynamique lineaire MITC4 multicouche. Il inclut les "
            "correlations Code_Aster relancees le 9 aout 2026 et la liste des points qui "
            "restent a construire avant la publication de la version alpha.",
            styles["body"],
        ),
        Paragraph(
            "Cette revue est une auto-revue Owner interne. Elle ne constitue ni une "
            "certification externe, ni une extension automatique des domaines mecaniques.",
            styles["note"],
        ),
        Spacer(1, 9 * mm),
        _table(
            [
                ["Champ", "Valeur"],
                ["Decision attendue", "accepted_for_bounded_engineering_use / accepted_with_recommendations / more_evidence_required / rejected"],
                ["Owner", "Quentin Farinazzo"],
                ["Date de preparation", str(date.today())],
                ["Evidence principale", "VNV-MITC4-LAMINATE-LAYUPS-CODEASTER-DST-021"],
            ],
            (48 * mm, 120 * mm),
        ),
        PageBreak(),
    ]


def _mitc4_laminate_review(styles: dict[str, ParagraphStyle], summary: dict[str, object]) -> list[object]:
    return [
        Paragraph("1. Owner Review - MITC4 multicouche dynamique lineaire", styles["h1"]),
        Paragraph(
            "Domaine soumis a decision : coque MITC4 Reissner-Mindlin plane, quatre plis "
            "symetriques, petits deplacements, masse coherente, condensation du drilling, "
            "modal, Newmark et harmonique lineaires. Trois orientations sont comparees.",
            styles["body"],
        ),
        Paragraph("Resultats de correlation Code_Aster DST", styles["h2"]),
        _table(
            [
                ["Empilement", "Amortissement cible", "Modal", "Newmark", "Harmonique", "Verdict"],
                *_layup_rows(summary),
            ],
            (31 * mm, 30 * mm, 25 * mm, 27 * mm, 28 * mm, 25 * mm),
        ),
        Spacer(1, 5 * mm),
        Paragraph(
            "Comparaison : meme maillage QUAD4, densite, blocages, grille temporelle, "
            "grille frequentielle et table de chargement. Les proprietes des plis sont "
            "identiques; seules les orientations changent. Code_Aster emploie "
            "DST / DEFI_COMPOSITE ; la comparaison est donc inter-formulations et non une "
            "egalite algebrique d'elements.",
            styles["body"],
        ),
        _figure(MITC4_RESULTS / "mitc4_laminate_layups_comparison.png"),
        Paragraph("Questions a renseigner", styles["h2"]),
        _table(
            [
                ["ID", "Question", "Reponse Owner", "Commentaire Owner"],
                ["Q1", "Domaine plan, quatre plis symetriques, masse coherente et drilling condense acceptes pour les trois empilements ?", "", ""],
                ["Q2", "Ecarts modal, Newmark et harmonique Code_Aster, dont le Newmark amorti, acceptables ?", "", ""],
                ["Q3", "Preuve statique d'axe projete sur coque courbe suffisante pour ce domaine dynamique plan borne ?", "", ""],
                ["Q4", "Exclusions dynamique courbe, B non nul, amortissement calibre, dommage et delaminage acceptables ?", "", ""],
                ["Q5", "Decision", "", ""],
            ],
            (12 * mm, 85 * mm, 29 * mm, 38 * mm),
        ),
        PageBreak(),
    ]


def _release_closure(styles: dict[str, ParagraphStyle]) -> list[object]:
    return [
        Paragraph("2. Etat de fermeture avant publication alpha", styles["h1"]),
        Paragraph(
            "Les correlations prioritaires relancees le 9 aout 2026 passent : MITC4 "
            "multicouche dynamique, MITC3+ multicouche dynamique, solides orthotropes "
            "complexes contre CalculiX et Code_Aster, composite courbe et orientation "
            "projetee. Les rapports et manifestes sont disponibles dans results/.",
            styles["body"],
        ),
        _table(
            [
                ["Etat", "Point", "Action"],
                ["Pret Owner", "MITC4 multicouche dynamique", "Signer Q1 a Q5 et la decision de la page precedente."],
                ["A construire", "MITC3+ multicouche courbe a orientation projetee", "Nouveau cas externe et Owner Review dediee."],
                ["A construire", "TET10 J2 non-lineaire structurel", "Benchmark structurel externe, puis Owner Review."],
                ["A construire", "Orthotropie cylindrique/conique TET4/TET10", "Raffinement et oracle externe."],
                ["Hors V0.2.0-alpha", "Dynamique non-lineaire, dommage, delaminage, grand glissement", "Conserver experimental/research, sans promesse d'usage."],
                ["Release", "Confidentialite, licence, depots et tag Git", "Audit public, choix SPDX, campagne complete puis tag v0.2.0-alpha."],
            ],
            (31 * mm, 58 * mm, 75 * mm),
        ),
        Spacer(1, 6 * mm),
        Paragraph("Declaration Owner", styles["h2"]),
        Paragraph("Owner : Quentin Farinazzo", styles["body"]),
        Paragraph("Date : ____________________", styles["body"]),
        Paragraph("Decision : ____________________________________________________________", styles["body"]),
        Paragraph("Signature : __________________________________________________________", styles["body"]),
    ]


def _check_row(check: dict[str, object]) -> list[str]:
    return [
        str(check["id"]),
        f"{100.0 * float(check['value']):.3f} %" if float(check["limit"]) > 1.0e-5 else f"{float(check['value']):.3e}",
        f"{100.0 * float(check['limit']):.3f} %" if float(check["limit"]) > 1.0e-5 else f"{float(check['limit']):.1e}",
        str(check["status"]),
    ]


def _layup_rows(summary: dict[str, object]) -> list[list[str]]:
    rows: list[list[str]] = []
    for case in summary["cases"]:
        checks = {str(row["id"]): row for row in case["summary"]["checks"]}
        layup = "/".join(f"{float(angle):g}" for angle in case["layup_deg"])
        damping = f"{100.0 * float(case['damping_ratio']):.1f} %"
        values = [
            f"{100.0 * float(checks['modal_frequencies']['value']):.3f} %",
            f"{100.0 * float(checks['newmark_tip_history']['value']):.3f} %",
            f"{100.0 * float(checks['harmonic_tip_response']['value']):.3f} %",
        ]
        if "newmark_damped_decay" in checks:
            values[1] += f"; decay {float(checks['newmark_damped_decay']['value']):.3f}"
        verdict = "PASS" if all(row["status"] == "PASS" for row in checks.values()) else "FAIL"
        rows.append([f"[{layup}]", damping, *values, verdict])
    return rows


def _table(rows: list[list[str]], widths: tuple[float, ...]) -> Table:
    header_style = ParagraphStyle(
        "owner_review_header",
        fontName="Helvetica-Bold",
        fontSize=7.8,
        leading=10,
        textColor=colors.white,
    )
    cell_style = ParagraphStyle(
        "owner_review_cell",
        fontName="Helvetica",
        fontSize=7.8,
        leading=10,
    )
    rendered = [
        [Paragraph(escape(str(cell)), header_style if row_index == 0 else cell_style) for cell in row]
        for row_index, row in enumerate(rows)
    ]
    table = Table(rendered, colWidths=widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324d")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.8),
                ("LEADING", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#9eabb5")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _figure(path: Path) -> Image:
    flattened = ROOT / "tmp" / "pdf_owner_review_render" / "mitc4_laminate_comparison_flattened.png"
    flattened.parent.mkdir(parents=True, exist_ok=True)
    with PilImage.open(path) as source:
        if source.mode in {"RGBA", "LA"}:
            background = PilImage.new("RGBA", source.size, "white")
            background.alpha_composite(source.convert("RGBA"))
            background.convert("RGB").save(flattened)
        else:
            source.convert("RGB").save(flattened)
    image = Image(str(flattened))
    image._restrictSize(174 * mm, 95 * mm)
    return image


def _footer(canvas: object, document: object) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#526674"))
    canvas.drawString(17 * mm, 10 * mm, "QF_solver - Owner review interne - sans revendication de certification externe")
    canvas.drawRightString(193 * mm, 10 * mm, f"Page {document.page}")
    canvas.restoreState()


def _validate(path: Path) -> None:
    reader = PdfReader(str(path))
    if len(reader.pages) < 3 or path.stat().st_size < 40_000:
        raise RuntimeError("Owner-review PDF is incomplete.")
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    for required in ("MITC4 multicouche", "Questions a renseigner", "Etat de fermeture"):
        if required not in text:
            raise RuntimeError(f"Owner-review PDF is missing: {required}")


if __name__ == "__main__":
    raise SystemExit(main())
