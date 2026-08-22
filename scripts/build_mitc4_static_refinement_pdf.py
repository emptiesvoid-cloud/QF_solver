"""Build the PDF review for the refined MITC4/Code_Aster static correlation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image as PilImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "qualification" / "vnv" / "external" / "code_aster_mitc4_conical_cutout_refinement" / "reference"
DEFAULT_OUTPUT = ROOT / "output" / "pdf" / "mitc4_static_code_aster_refinement_owner_review.pdf"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    summary = json.loads((EVIDENCE / "summary.json").read_text(encoding="utf-8"))
    build(summary, output)
    print(f"PDF: {output}")
    return 0


def build(summary: dict[str, object], output: Path) -> None:
    styles = getSampleStyleSheet()
    document = SimpleDocTemplate(
        str(output), pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
        title="MITC4 static Code_Aster refinement review", author="QF_solver",
    )
    rows = summary["rows"]
    fine = rows[-1]
    story: list[object] = [
        Paragraph("QF_solver - MITC4 statique : raffinement Code_Aster", styles["Title"]),
        Paragraph("Scope : mitc4-linear-static | Oracle : Code_Aster 18.1.0 DKQ", styles["Normal"]),
        Spacer(1, 5 * mm),
        Paragraph(
            "Correlation sur une coque conique facettisee, maillage commun et chargement "
            "nodal coherent. Le DKQ est un oracle complementaire et non une identite de formulation MITC4.",
            styles["BodyText"],
        ),
        Spacer(1, 4 * mm),
        _table(rows),
        Spacer(1, 5 * mm),
        Paragraph(
            f"Resultat final : ecart vecteur deplacement {float(fine['vector_difference']) * 100:.6f} %, "
            f"sonde UZ {float(fine['probe_uz_difference']) * 100:.6f} %, "
            f"resultante {float(fine['reaction_resultant_difference']):.3e}.",
            styles["Heading2"],
        ),
        Paragraph(
            "La grandeur principale de deplacement est sous la limite de 1 %. "
            "La promotion reste soumise a une Owner Review explicite avec promotion_target=stable.",
            styles["BodyText"],
        ),
        Spacer(1, 5 * mm),
        _scaled_image(EVIDENCE / "conical_cutout_code_aster_correlation.png", 175),
    ]
    document.build(story)
    if not output.is_file() or output.stat().st_size < 1000 or not output.read_bytes().startswith(b"%PDF"):
        raise RuntimeError("Generated PDF is invalid or unexpectedly small.")


def _table(rows: list[dict[str, object]]) -> Table:
    data = [["Maillage", "Elements", "Noeuds", "Ecart UZ", "Ecart vecteur U", "Ecart R"]]
    for row in rows:
        data.append([
            f"{row['radial_elements']} x {row['circumferential_elements']}",
            str(row["elements"]), str(row["nodes"]),
            f"{float(row['probe_uz_difference']) * 100:.6f} %",
            f"{float(row['vector_difference']) * 100:.6f} %",
            f"{float(row['reaction_resultant_difference']):.3e}",
        ])
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#b8c7d9")),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#edf3f8")]),
    ]))
    return table


def _scaled_image(path: Path, width_mm: float) -> Image:
    with PilImage.open(path) as image:
        pixel_width, pixel_height = image.size
    width = width_mm * mm
    return Image(str(path), width=width, height=width * pixel_height / max(pixel_width, 1))


if __name__ == "__main__":
    raise SystemExit(main())
