"""Build the review PDF for the TET10 stable-refinement evidence."""

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
EVIDENCE = ROOT / "qualification" / "vnv" / "tet10_stable_refinement" / "reference"
DEFAULT_OUTPUT = ROOT / "output" / "pdf" / "tet10_stable_refinement_owner_review.pdf"


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
        str(output),
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title="TET10 stable refinement owner review",
        author="QF_solver",
    )
    bending = summary["bending"]["families"]["TET10"]
    rows = bending["levels"]
    story: list[object] = [
        Paragraph("QF_solver - TET10 statique : campagne de raffinement stable", styles["Title"]),
        Paragraph("Scope : tet10-linear-static | Evidence ID : VNV-TET10-STABLE-REFINEMENT-002", styles["Normal"]),
        Spacer(1, 5 * mm),
        Paragraph(
            "Objectif : verifier la regle de promotion stable avec une erreur finale <= 1 % "
            "sur le deplacement de flexion Timoshenko, sans modifier les resultats precedents.",
            styles["BodyText"],
        ),
        Spacer(1, 4 * mm),
        _table(rows),
        Spacer(1, 5 * mm),
        Paragraph(
            f"Resultat final : {float(bending['finest_response_error']) * 100:.6f} % "
            f"avec {len(rows)} niveaux. Residu libre maximal : "
            f"{float(bending['maximum_free_relative_residual']):.3e}.",
            styles["Heading2"],
        ),
        Paragraph(
            "Le seuil technique de 1 % est passe pour cette campagne. La promotion de "
            "maturite reste interdite tant qu'une Owner Review datee avec "
            "promotion_target=stable n'est pas enregistree.",
            styles["BodyText"],
        ),
        Spacer(1, 5 * mm),
        Paragraph("Figures de controle", styles["Heading2"]),
        _scaled_image(EVIDENCE / "tet10_structural_convergence.png", 170),
        _scaled_image(EVIDENCE / "bending_tet10_deformation.png", 150),
    ]
    document.build(story)
    if not output.is_file() or output.stat().st_size < 1000 or not output.read_bytes().startswith(b"%PDF"):
        raise RuntimeError("Generated PDF is invalid or unexpectedly small.")


def _table(rows: list[dict[str, object]]) -> Table:
    data = [["Niveau", "h", "Elements", "Noeuds", "Erreur flexion", "Residu"]]
    for row in rows:
        data.append(
            [
                str(row["level"]),
                f"{float(row['mesh_size']):.2f}",
                str(row["element_count"]),
                str(row["node_count"]),
                f"{float(row['response_error']) * 100:.6f} %",
                f"{float(row['free_relative_residual']):.3e}",
            ]
        )
    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#b8c7d9")),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#edf3f8")]),
            ]
        )
    )
    return table


def _scaled_image(path: Path, width_mm: float) -> Image:
    with PilImage.open(path) as image:
        pixel_width, pixel_height = image.size
    width = width_mm * mm
    height = width * pixel_height / max(pixel_width, 1)
    return Image(str(path), width=width, height=height)


if __name__ == "__main__":
    raise SystemExit(main())
