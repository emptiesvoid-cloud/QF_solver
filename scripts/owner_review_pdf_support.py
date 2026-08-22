"""Shared presentation helpers for controlled Owner-review PDFs."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any, Iterable

from PIL import Image as PilImage
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, Table, TableStyle


def evidence_assets(root: Path, row: dict[str, Any], scope: str) -> tuple[list[tuple[Path, str]], list[list[object]]]:
    """Collect up to two figures and eight numeric values from evidence files."""
    images: list[tuple[Path, str]] = []
    numbers: list[list[object]] = [["Fichier", "Mesure", "Valeur"]]
    seen_images: set[Path] = set()
    for relative in row.get("evidence_paths", []):
        path = root / str(relative)
        candidates = [path] if path.suffix.lower() in {".png", ".jpg", ".jpeg"} else []
        if path.suffix.lower() == ".json":
            candidates.extend(sorted(path.parent.glob("*.png")))
            if path.is_file():
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    flat: list[tuple[str, object]] = []
                    def visit(value: object, prefix: str = "") -> None:
                        if len(flat) >= 8:
                            return
                        if isinstance(value, dict):
                            for key, item in value.items():
                                visit(item, f"{prefix}.{key}" if prefix else str(key))
                        elif isinstance(value, (int, float)) and not isinstance(value, bool):
                            flat.append((prefix, value))
                    visit(payload)
                    numbers.extend([[path.relative_to(root).as_posix(), key, f"{value:.6g}" if isinstance(value, float) else value] for key, value in flat[:8]])
                except (OSError, ValueError, TypeError):
                    pass
        for candidate in candidates:
            if candidate.is_file() and candidate not in seen_images:
                seen_images.add(candidate)
                images.append((candidate, candidate.relative_to(root).as_posix()))
    if not images:
        images = [(p, p.relative_to(root).as_posix()) for p in sorted((root / "results").glob(f"**/*{scope.replace('-', '_')}*.png"))[:2]]
    return images[:2], numbers[:9]


def review_styles() -> dict[str, ParagraphStyle]:
    """Return the compact engineering-document style set."""
    base = getSampleStyleSheet()
    common = {"parent": base["BodyText"], "fontName": "Helvetica"}
    return {
        "title": ParagraphStyle(
            "qf_title", parent=base["Title"], fontName="Helvetica-Bold", fontSize=20,
            leading=25, alignment=TA_CENTER, textColor=colors.HexColor("#123B4A"),
        ),
        "subtitle": ParagraphStyle(
            "qf_subtitle", **common, fontSize=10.5, leading=14, alignment=TA_CENTER,
            textColor=colors.HexColor("#425563"),
        ),
        "h1": ParagraphStyle(
            "qf_h1", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=14,
            leading=18, spaceBefore=7, spaceAfter=6, textColor=colors.HexColor("#123B4A"),
        ),
        "h2": ParagraphStyle(
            "qf_h2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=10.5,
            leading=13, spaceBefore=5, spaceAfter=4, textColor=colors.HexColor("#236177"),
        ),
        "body": ParagraphStyle("qf_body", **common, fontSize=8.8, leading=12.5, spaceAfter=5),
        "small": ParagraphStyle("qf_small", **common, fontSize=7.1, leading=9.2, spaceAfter=2),
        "note": ParagraphStyle(
            "qf_note", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=8.5,
            leading=12, textColor=colors.HexColor("#6A3900"), backColor=colors.HexColor("#FFF3DC"),
            borderPadding=6, spaceAfter=7,
        ),
        "pass": ParagraphStyle(
            "qf_pass", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=8.5,
            leading=12, textColor=colors.HexColor("#145A32"), backColor=colors.HexColor("#EAF7EF"),
            borderPadding=6, spaceAfter=7,
        ),
        "fail": ParagraphStyle(
            "qf_fail", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=8.5,
            leading=12, textColor=colors.HexColor("#7B241C"), backColor=colors.HexColor("#FDEDEC"),
            borderPadding=6, spaceAfter=7,
        ),
    }


def paragraph(value: object, style: ParagraphStyle) -> Paragraph:
    """Escape arbitrary evidence text before feeding it to ReportLab."""
    return Paragraph(escape(str(value)).replace("\n", "<br/>"), style)


def review_table(
    rows: list[list[object]], widths: list[float], styles: dict[str, ParagraphStyle]
) -> Table:
    """Build a repeatable, split-safe engineering table."""
    header = ParagraphStyle(
        "qf_table_header", parent=styles["small"], fontName="Helvetica-Bold", textColor=colors.white
    )
    body = ParagraphStyle("qf_table_body", parent=styles["small"], fontName="Helvetica")
    rendered = [
        [paragraph(cell, header if index == 0 else body) for cell in row]
        for index, row in enumerate(rows)
    ]
    result = Table(rendered, colWidths=widths, repeatRows=1, splitByRow=1)
    result.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#123B4A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#AAB7B8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), (colors.white, colors.HexColor("#F3F7F8"))),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return result


def review_footer(canvas: Any, document: Any) -> None:
    """Draw the controlled footer and page number."""
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#425563"))
    canvas.drawString(15 * mm, 9 * mm, "QF_solver 0.2.1a0 - dossier de decision - aucune certification revendiquee")
    canvas.drawRightString(A4[0] - 15 * mm, 9 * mm, f"Page {document.page}")
    canvas.restoreState()


def review_image(path: Path, cache: Path, *, max_height: float = 72 * mm) -> Image | None:
    """Normalize an evidence image and constrain it to the printable area."""
    if not path.is_file():
        return None
    cache.parent.mkdir(parents=True, exist_ok=True)
    with PilImage.open(path) as source:
        source.convert("RGB").save(cache, format="PNG")
    figure = Image(str(cache))
    figure._restrictSize(174 * mm, max_height)
    return figure


def validate_pdf(path: Path, phrases: Iterable[str], minimum_pages: int) -> None:
    """Check basic integrity, page count and required extracted text."""
    if not path.is_file() or path.stat().st_size < 4_000:
        raise RuntimeError(f"Incomplete PDF: {path}")
    reader = PdfReader(str(path))
    if len(reader.pages) < minimum_pages:
        raise RuntimeError(f"Unexpected page count for {path}: {len(reader.pages)}")
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    missing = [phrase for phrase in phrases if phrase not in text]
    if missing:
        raise RuntimeError(f"Missing PDF content in {path}: {missing}")


def count_source_occurrences(paths: Iterable[Path], value: str) -> int:
    """Count text sources containing a case-insensitive controlled value."""
    count = 0
    for path in paths:
        if path.suffix.lower() == ".pdf":
            continue
        try:
            count += value.casefold() in path.read_text(encoding="utf-8").casefold()
        except UnicodeDecodeError:
            continue
    return count
