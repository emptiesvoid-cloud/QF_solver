"""Build the PDF owner-review pack for MITC4 harmonic refinement."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image as PilImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "qualification" / "vnv" / "external" / "mitc4_harmonic_refinement_005" / "reference"
OUTPUT = ROOT / "output" / "pdf" / "mitc4_harmonic_refinement_owner_review.pdf"


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    summary = json.loads((EVIDENCE / "summary.json").read_text(encoding="utf-8"))
    _build(summary)
    print(f"PDF: {OUTPUT}")
    return 0


def _build(summary: dict[str, object]) -> None:
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(OUTPUT), pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=14 * mm, bottomMargin=14 * mm, title="MITC4 harmonic refinement owner review", author="QF_solver")
    rows = summary["rows"]
    table_data = [["Maillage", "Eléments", "U", "f", "S11", "Max"]]
    for row in rows:
        table_data.append([
            f"{row['mesh_size']}x{row['mesh_size']}", str(row["element_count"]),
            f"{row['peak_displacement_error'] * 100:.4f} %", f"{row['peak_frequency_error'] * 100:.4f} %",
            f"{row['peak_stress_error'] * 100:.4f} %", f"{row['max_primary_error'] * 100:.4f} %",
        ])
    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#aab7c4")),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#edf3f8")]),
    ]))
    final = rows[-1]
    story: list[object] = [
        Paragraph("QF_solver - MITC4 harmonique : raffinement", styles["Title"]),
        Paragraph("Study ID : VNV-MITC4-HARMONIC-REFINEMENT-005 | Théorie : Kirchhoff-Love / NAFEMS 13H", styles["Normal"]),
        Spacer(1, 4 * mm),
        Paragraph(
            f"La campagne conserve trois niveaux. Le maillage final {final['mesh_size']}x{final['mesh_size']} atteint "
            f"une erreur primaire maximale de <b>{final['max_primary_error'] * 100:.6f} %</b>, sous la limite de 1 %.",
            styles["BodyText"],
        ),
        Paragraph("Les dépassements intermédiaires sont visibles et ne sont pas supprimés. Une Owner Review reste nécessaire avant toute promotion stable.", styles["BodyText"]),
        Spacer(1, 4 * mm), table, Spacer(1, 4 * mm),
        Paragraph("Courbe de convergence", styles["Heading2"]),
        _scaled_image(EVIDENCE / "VNV-MITC4-HARMONIC-REFINEMENT-005-convergence.png", 175),
        Paragraph("La contrainte est mesurée au centre de la face supérieure, hors singularité ponctuelle; les pics singuliers ne sont pas utilisés comme critère.", styles["BodyText"]),
    ]
    doc.build(story)
    if not OUTPUT.is_file() or OUTPUT.stat().st_size < 1000 or not OUTPUT.read_bytes().startswith(b"%PDF"):
        raise RuntimeError("Generated PDF is invalid or unexpectedly small.")


def _scaled_image(path: Path, width_mm: float) -> Image:
    with PilImage.open(path) as image:
        width_px, height_px = image.size
    width = width_mm * mm
    return Image(str(path), width=width, height=width * height_px / max(width_px, 1))


if __name__ == "__main__":
    raise SystemExit(main())
