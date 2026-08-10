"""Build the consolidated element and solver Owner-review PDF."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402
from PIL import Image as PilImage
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "qualification" / "documentation_review_pages.json"
REVIEW = ROOT / "docs" / "verification" / "owner_review_pages_techniques.md"
DEFAULT_OUTPUT = ROOT / "output" / "pdf" / "dossier_technique_elements_methodes_owner_review.pdf"
IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)(?:\{[^}]*\})?")
LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--legacy-reportlab",
        action="store_true",
        help="Use the deprecated ReportLab renderer for diagnostics only.",
    )
    args = parser.parse_args()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if args.legacy_reportlab:
        build_pdf(output)
    else:
        from scripts.build_technical_latex import build_manual

        build_manual(
            output=output,
            tex_output=ROOT / "tmp" / "pdfs" / "qf_solver_manual.tex",
            rebuild_assets=True,
        )
    print(f"PDF: {output}")
    return 0


def build_pdf(output: Path) -> None:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    regular, bold, mono = _register_fonts()
    styles = _styles(regular, bold, mono)
    document = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=18 * mm,
        bottomMargin=17 * mm,
        title="QF_solver - Dossier technique elements et methodes",
        author="QF_solver project",
        subject="Fiches techniques en attente d'Owner review",
    )
    story = _cover(payload, styles, regular, bold)
    for index, entry in enumerate(payload["pages"], start=1):
        story.extend(_render_page(index, entry, styles, regular, bold, mono))
    story.extend(_review_form(styles))
    document.build(
        story,
        onFirstPage=lambda canvas, doc: _footer(canvas, doc, regular),
        onLaterPages=lambda canvas, doc: _footer(canvas, doc, regular),
    )
    if not output.is_file() or output.stat().st_size < 100_000:
        raise RuntimeError("Technical PDF is missing or unexpectedly small.")
    _validate_page_counts(output, payload)


def _register_fonts() -> tuple[str, str, str]:
    pdfmetrics.registerFont(TTFont("QFArial", r"C:\Windows\Fonts\arial.ttf"))
    pdfmetrics.registerFont(TTFont("QFArialBold", r"C:\Windows\Fonts\arialbd.ttf"))
    pdfmetrics.registerFont(TTFont("QFConsolas", r"C:\Windows\Fonts\consola.ttf"))
    return "QFArial", "QFArialBold", "QFConsolas"


def _styles(regular: str, bold: str, mono: str) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "brand": ParagraphStyle("brand", parent=base["Title"], fontName=bold, fontSize=25, leading=29, textColor=colors.HexColor("#17324D")),
        "title": ParagraphStyle("title", parent=base["Title"], fontName=bold, fontSize=18, leading=23, alignment=TA_CENTER),
        "lead": ParagraphStyle("lead", parent=base["BodyText"], fontName=regular, fontSize=10.5, leading=15, textColor=colors.HexColor("#263746")),
        "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName=bold, fontSize=16, leading=20, spaceBefore=7, spaceAfter=7, textColor=colors.HexColor("#17324D")),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName=bold, fontSize=12.5, leading=16, spaceBefore=7, spaceAfter=5, textColor=colors.HexColor("#205B73")),
        "h3": ParagraphStyle("h3", parent=base["Heading3"], fontName=bold, fontSize=10.5, leading=14, spaceBefore=5, spaceAfter=3),
        "body": ParagraphStyle("body", parent=base["BodyText"], fontName=regular, fontSize=8.8, leading=12.3, spaceAfter=4),
        "small": ParagraphStyle("small", parent=base["BodyText"], fontName=regular, fontSize=7.4, leading=9.5),
        "code": ParagraphStyle("code", parent=base["Code"], fontName=mono, fontSize=6.8, leading=8.7, backColor=colors.HexColor("#F2F5F7"), borderPadding=5),
        "warning": ParagraphStyle("warning", parent=base["BodyText"], fontName=bold, fontSize=9.5, leading=13, textColor=colors.HexColor("#8A3B12"), backColor=colors.HexColor("#FFF3E8"), borderPadding=8),
    }


def _cover(payload: dict, styles: dict, regular: str, bold: str) -> list[object]:
    pages = payload["pages"]
    rows = [["Categorie", "Nombre", "Relecture"]]
    for kind, label in (("element", "Elements"), ("method", "Methodes")):
        count = sum(page["kind"] == kind for page in pages)
        rows.append([label, str(count), "pending_owner_review"])
    table = Table(rows, colWidths=[55 * mm, 30 * mm, 70 * mm])
    table.setStyle(_table_style(regular, bold))
    return [
        Spacer(1, 18 * mm),
        Paragraph("QF_solver", styles["brand"]),
        Spacer(1, 5 * mm),
        Paragraph("Dossier technique - elements et methodes", styles["title"]),
        Spacer(1, 9 * mm),
        Paragraph(
            "Version applicable 0.2.0. Ce PDF consolide les pages Markdown "
            "destinees a la relecture technique de l'Owner.",
            styles["lead"],
        ),
        Spacer(1, 8 * mm),
        table,
        Spacer(1, 10 * mm),
        Paragraph(
            "REGLE IMPERATIVE : une demonstration documentee ne vaut pas "
            "qualification. Les 21 fiches restent en attente d'Owner review. "
            "Aucune decision ni hausse de maturite n'est pre-remplie.",
            styles["warning"],
        ),
        Spacer(1, 10 * mm),
        Paragraph(
            "Contenu attendu par fiche : geometrie, DDL, formulation "
            "mathematique, integration, algorithme, exemple executable, "
            "maillage, chargement, conditions limites, tableau de resultats, "
            "figure de deformee, invariants, convergence, limites et references.",
            styles["lead"],
        ),
        PageBreak(),
    ]


def _render_page(
    index: int,
    entry: dict,
    styles: dict,
    regular: str,
    bold: str,
    mono: str,
) -> list[object]:
    path = ROOT / entry["path"]
    source = _expand_snippets(path.read_text(encoding="utf-8"))
    source = _strip_frontmatter(source)
    result: list[object] = [
        Paragraph(f"{index}. {html.escape(entry['id'])}", styles["h1"]),
        _metadata(entry, regular, bold),
        Spacer(1, 3 * mm),
    ]
    if entry["kind"] == "element":
        result.extend(
            [
                Paragraph("Lecture de la fiche", styles["h2"]),
                Paragraph(
                    "La fiche commence par le domaine, les DDL et un cas executable. "
                    "Les formulations detaillees sont placees ensuite en annexes pour "
                    "ne pas masquer le maillage, les chargements, les blocages, les "
                    "resultats et les limites de validite.",
                    styles["body"],
                ),
            ]
        )
    result.extend(_markdown_flowables(source, path.parent, styles, regular, bold, mono))
    for appendix_number, appendix_name in enumerate(entry.get("appendices", []), start=1):
        appendix = ROOT / appendix_name
        appendix_source = _strip_frontmatter(
            _expand_snippets(appendix.read_text(encoding="utf-8"))
        )
        result.extend(
            [
                PageBreak(),
                Paragraph(
                    f"Annexe {index}.{appendix_number} - "
                    f"{html.escape(appendix.stem.replace('_', ' '))}",
                    styles["h1"],
                ),
            ]
        )
        result.extend(
            _markdown_flowables(
                appendix_source,
                appendix.parent,
                styles,
                regular,
                bold,
                mono,
            )
        )
    result.append(PageBreak())
    return result


def _expand_snippets(source: str) -> str:
    pattern = re.compile(r'--8<--\s+"([^"]+)"')

    def replacement(match: re.Match[str]) -> str:
        path = ROOT / match.group(1)
        return path.read_text(encoding="utf-8") if path.is_file() else f"[Snippet absent: {path}]"

    return pattern.sub(replacement, source)


def _strip_frontmatter(source: str) -> str:
    if not source.startswith("---"):
        return source
    parts = source.split("---", 2)
    return parts[2].lstrip() if len(parts) == 3 else source


def _markdown_flowables(
    source: str,
    directory: Path,
    styles: dict,
    regular: str,
    bold: str,
    mono: str,
) -> list[object]:
    lines = source.splitlines()
    result: list[object] = []
    paragraph: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped:
            _flush_paragraph(result, paragraph, styles)
            index += 1
            continue
        if stripped.startswith("```"):
            _flush_paragraph(result, paragraph, styles)
            block, index = _collect_until(lines, index + 1, "```")
            result.append(Preformatted("\n".join(block), styles["code"]))
            continue
        if stripped in {"$$", r"\["}:
            _flush_paragraph(result, paragraph, styles)
            closing = "$$" if stripped == "$$" else r"\]"
            block, index = _collect_until(lines, index + 1, closing)
            result.extend(_equation_flowables("\n".join(block), styles))
            continue
        image_match = IMAGE_PATTERN.fullmatch(stripped)
        if image_match:
            _flush_paragraph(result, paragraph, styles)
            result.extend(_image_flowables(directory, image_match.group(2), image_match.group(1), styles))
            index += 1
            continue
        if stripped.startswith("|") and index + 1 < len(lines) and lines[index + 1].strip().startswith("|"):
            _flush_paragraph(result, paragraph, styles)
            table_lines = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index])
                index += 1
            result.append(_markdown_table(table_lines, regular, bold, styles))
            continue
        heading = re.match(r"^(#{1,3})\s+(.+)$", stripped)
        if heading:
            _flush_paragraph(result, paragraph, styles)
            level = len(heading.group(1))
            result.append(Paragraph(_inline(heading.group(2)), styles[f"h{level}"]))
            index += 1
            continue
        if stripped.startswith(("- ", "* ")):
            _flush_paragraph(result, paragraph, styles)
            result.append(Paragraph(f"- {_inline(stripped[2:])}", styles["body"]))
            index += 1
            continue
        paragraph.append(stripped)
        index += 1
    _flush_paragraph(result, paragraph, styles)
    return result


def _collect_until(lines: list[str], index: int, closing: str) -> tuple[list[str], int]:
    block = []
    while index < len(lines) and lines[index].strip() != closing:
        block.append(lines[index])
        index += 1
    return block, min(index + 1, len(lines))


def _flush_paragraph(result: list[object], paragraph: list[str], styles: dict) -> None:
    if paragraph:
        result.append(Paragraph(_inline(" ".join(paragraph)), styles["body"]))
        paragraph.clear()


def _inline(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value)
    value = IMAGE_PATTERN.sub(lambda match: match.group(1), value)
    value = LINK_PATTERN.sub(lambda match: f"{match.group(1)} ({match.group(2)})", value)
    value = re.sub(
        r"\$([^$]+)\$",
        lambda match: _inline_equation_text(match.group(1)),
        value,
    )
    value = value.replace("`", "").replace("$", "")
    return html.escape(value)


def _inline_equation_text(value: str) -> str:
    replacements = {
        r"\varnothing": " vide ",
        r"\rightarrow": " vers ",
        r"\partial": "frontiere ",
        r"\subset": " inclus dans ",
        r"\nabla": "grad ",
        r"\varepsilon": "epsilon",
        r"\epsilon": "epsilon",
        r"\boldsymbol": "",
        r"\mathbf": "",
        r"\mathbb": "",
        r"\mathcal": "",
        r"\overline": "",
        r"\Gamma": "Gamma",
        r"\Omega": "Omega",
        r"\sigma": "sigma",
        r"\theta": "theta",
        r"\lambda": "lambda",
        r"\gamma": "gamma",
        r"\kappa": "kappa",
        r"\nu": "nu",
        r"\rho": "rho",
        r"\mu": "mu",
        r"\in": " appartient a ",
        r"\cup": " union ",
        r"\cap": " intersection ",
        r"\cdot": ".",
        r"\times": " x ",
        r"\to": " vers ",
        r"\quad": " ",
        r"\,": " ",
    }
    text = value
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"\\text\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\(?:mathrm|operatorname)\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"[{}]", "", text)
    text = re.sub(r"\\([A-Za-z]+)", r"\1", text)
    return " ".join(text.split())


def _clean_equation(value: str) -> str:
    replacements = {
        r"\begin{bmatrix}": "[",
        r"\end{bmatrix}": "]",
        r"\begin{matrix}": "[",
        r"\end{matrix}": "]",
        r"\mathbf": "",
        r"\boldsymbol": "",
        r"\operatorname": "",
        r"\left": "",
        r"\right": "",
        r"\lVert": "||",
        r"\rVert": "||",
        r"\qquad": "    ",
        r"\quad": "  ",
        r"\,": " ",
        "&": "  ",
    }
    cleaned = value
    for old, new in replacements.items():
        cleaned = cleaned.replace(old, new)
    cleaned = cleaned.replace(r"\\", "\n")
    fraction = re.compile(r"\\t?frac\{([^{}]+)\}\{([^{}]+)\}")
    for _ in range(4):
        cleaned = fraction.sub(r"(\1)/(\2)", cleaned)
    cleaned = re.sub(r"\\([A-Za-z]+)", r"\1", cleaned)
    return cleaned.strip()


def _equation_flowables(value: str, styles: dict) -> list[object]:
    if r"\begin{" in value or r"\end{" in value:
        return [Preformatted(_clean_equation(value), styles["code"])]
    expressions = [
        expression.strip().rstrip(",")
        for expression in value.replace("\n", " ").split(r"\\")
        if expression.strip()
    ]
    result: list[object] = []
    for expression in expressions:
        try:
            path = _render_equation(expression)
            result.extend(_scaled_image(path, max_height=28 * mm))
        except (ValueError, RuntimeError):
            result.append(Preformatted(_clean_equation(expression), styles["code"]))
    return result


def _render_equation(expression: str) -> Path:
    expression = _mathtext_expression(expression)
    digest = hashlib.sha256(expression.encode("utf-8")).hexdigest()[:20]
    directory = ROOT / "tmp" / "pdfs" / "equations"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{digest}.png"
    if path.is_file():
        return path
    figure = plt.figure(figsize=(5.8, 0.48))
    figure.patch.set_alpha(0)
    figure.text(
        0.5,
        0.5,
        f"${expression}$",
        horizontalalignment="center",
        verticalalignment="center",
        fontsize=10,
        color="#172B3A",
    )
    try:
        figure.savefig(
            path,
            dpi=180,
            bbox_inches="tight",
            pad_inches=0.08,
            transparent=True,
        )
    finally:
        plt.close(figure)
    return path


def _mathtext_expression(expression: str) -> str:
    expression = re.sub(
        r"\\boldsymbol\\([A-Za-z]+)",
        r"\\boldsymbol{\\\1}",
        expression,
    )
    expression = re.sub(
        r"\\mathbf\s*([A-Za-z0-9])",
        r"\\mathbf{\1}",
        expression,
    )
    expression = re.sub(
        r"\\mathcal\s*([A-Za-z])",
        r"\\mathcal{\1}",
        expression,
    )
    expression = re.sub(
        r"\\mathbb\s*([A-Za-z])",
        r"\\mathbb{\1}",
        expression,
    )
    expression = re.sub(
        r"\\t?frac([0-9])([0-9])",
        r"\\frac{\1}{\2}",
        expression,
    )
    return expression


def _scaled_image(path: Path, *, max_height: float) -> list[object]:
    with PilImage.open(path) as image:
        width, height = image.size
    # Equations are supporting material: keep them narrower than the text
    # column so the reader retains the section hierarchy and visual rhythm.
    max_width = 125 * mm
    scale = min(max_width / width, max_height / height)
    return [Image(str(path), width=width * scale, height=height * scale), Spacer(1, 1 * mm)]


def _markdown_table(
    lines: list[str],
    regular: str,
    bold: str,
    styles: dict,
) -> Table:
    parsed = [[cell.strip() for cell in line.strip().strip("|").split("|")] for line in lines]
    if len(parsed) > 1 and all(set(cell) <= {"-", ":", " "} for cell in parsed[1]):
        parsed.pop(1)
    width = 180 * mm
    columns = max(len(row) for row in parsed)
    col_widths = [width / columns] * columns
    data = [
        [Paragraph(_inline(cell), styles["small"]) for cell in row] + [""] * (columns - len(row))
        for row in parsed
    ]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(_table_style(regular, bold))
    return table


def _table_style(regular: str, bold: str) -> TableStyle:
    return TableStyle(
        [
            ("FONTNAME", (0, 0), (-1, -1), regular),
            ("FONTNAME", (0, 0), (-1, 0), bold),
            ("FONTSIZE", (0, 0), (-1, -1), 7.2),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DCE8EF")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#17324D")),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#9EADB7")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]
    )


def _image_flowables(directory: Path, raw_path: str, caption: str, styles: dict) -> list[object]:
    clean_path = raw_path.split()[0].strip("<>")
    path = (directory / clean_path).resolve()
    if not path.is_file():
        return [Paragraph(f"Figure absente : {html.escape(str(path))}", styles["warning"])]
    if path.suffix.lower() == ".svg":
        return [
            Paragraph(
                f"Schema vectoriel disponible dans le site : {html.escape(caption)}",
                styles["small"],
            )
        ]
    with PilImage.open(path) as image:
        width, height = image.size
    max_width, max_height = 170 * mm, 95 * mm
    scale = min(max_width / width, max_height / height)
    return [
        Image(str(path), width=width * scale, height=height * scale),
        Paragraph(f"Figure - {html.escape(caption)}", styles["small"]),
        Spacer(1, 2 * mm),
    ]


def _metadata(entry: dict, regular: str, bold: str) -> Table:
    table = Table(
        [
            ["Type", entry["kind"], "Maturite actuelle", entry["current_maturity"]],
            ["Relecture", entry["review_status"], "Effet qualification", entry["qualification_effect"]],
        ],
        colWidths=[25 * mm, 42 * mm, 36 * mm, 72 * mm],
    )
    table.setStyle(_table_style(regular, bold))
    return table


def _review_form(styles: dict) -> list[object]:
    return [
        Paragraph("Formulaire global d'Owner review", styles["h1"]),
        Paragraph(
            "Utiliser une decision par page. Une acceptation documentaire ne "
            "change pas seule la maturite mecanique ou numerique.",
            styles["warning"],
        ),
        Spacer(1, 4 * mm),
        Preformatted(
            "OWNER-REVIEW-DOC <doc_id>\n"
            "Q1 Geometrie, DDL, reperes et signes : OUI/NON\n"
            "Q2 Formulation, integration et algorithme : OUI/NON\n"
            "Q3 Exemple, maillage, charges et blocages : OUI/NON\n"
            "Q4 Resultats, figure, invariants et convergence : OUI/NON\n"
            "Q5 Limites, references et tracabilite : OUI/NON\n"
            "DECISION accepted | accepted_with_recommendations | changes_required\n"
            "COMMENTS:\n",
            styles["code"],
        ),
        Spacer(1, 8 * mm),
        Paragraph("Owner : __________________________________________", styles["body"]),
        Paragraph("Date : ____________________________________________", styles["body"]),
        Paragraph("Signature : _________________________________________", styles["body"]),
    ]


def _footer(canvas, document, regular: str) -> None:
    canvas.saveState()
    canvas.setFont(regular, 7)
    canvas.setFillColor(colors.HexColor("#60717D"))
    canvas.drawString(15 * mm, 9 * mm, "QF_solver - dossier technique - Owner review requise")
    canvas.drawRightString(195 * mm, 9 * mm, f"Page {document.page}")
    canvas.restoreState()


def _validate_page_counts(output: Path, payload: dict) -> None:
    reader = PdfReader(output)
    texts = [page.extract_text() or "" for page in reader.pages]
    pages = payload["pages"]
    starts: dict[str, int] = {}
    for entry in pages:
        marker = entry["id"]
        starts[marker] = next(
            (index for index, text in enumerate(texts) if marker in text),
            -1,
        )
    report = {"schema_version": 1, "pdf": output.name, "elements": []}
    for index, entry in enumerate(pages):
        minimum = entry.get("minimum_pdf_pages")
        if minimum is None:
            continue
        start = starts[entry["id"]]
        if start < 0:
            raise RuntimeError(f"Unable to locate {entry['id']} in generated PDF.")
        next_start = (
            starts[pages[index + 1]["id"]]
            if index + 1 < len(pages)
            else len(texts)
        )
        count = next_start - start
        report["elements"].append(
            {
                "id": entry["id"],
                "pages": count,
                "minimum": minimum,
                "status": "PASS" if count >= minimum else "FAIL",
            }
        )
        if count < minimum:
            raise RuntimeError(
                f"{entry['id']} has {count} PDF pages; minimum is {minimum}."
            )
    report_path = output.with_name("dossier_technique_page_counts.json")
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
