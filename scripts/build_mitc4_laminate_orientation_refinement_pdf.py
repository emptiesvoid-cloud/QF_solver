"""Build a compact PDF review for the oblique laminate refinement."""

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
EVIDENCE = ROOT / "qualification" / "vnv" / "external" / "calculix_curved_orientation_refinement_192" / "reference"
OUTPUT = ROOT / "output" / "pdf" / "mitc4_laminate_orientation_refinement_owner_review.pdf"


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    summary = json.loads((EVIDENCE / "summary.json").read_text(encoding="utf-8"))
    _build(summary)
    print(f"PDF: {OUTPUT}")
    return 0


def _build(summary: dict[str, object]) -> None:
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(OUTPUT), pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=13 * mm, bottomMargin=13 * mm, title="MITC4 laminate orientation refinement", author="QF_solver")
    data = [["Maillage", "Eléments", "Ecart vecteur", "Ecart UZ"]]
    for row in summary["rows"]:
        data.append([f"{row['nx']}x{row['ny']}", str(row["elements"]), f"{row['vector_difference'] * 100:.4f} %", f"{row['uz_difference'] * 100:.4f} %"])
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#7f1d1d")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#b9a4a4")),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fff5f5")]),
    ]))
    final = summary["rows"][-1]
    story: list[object] = [
        Paragraph("QF_solver - MITC4 multicouche courbe oblique", styles["Title"]),
        Paragraph("Refinement externe CalculiX S8R jusqu'à 18 432 éléments", styles["Normal"]),
        Spacer(1, 4 * mm),
        Paragraph(
            f"Résultat : l'écart vectoriel final est <b>{final['vector_difference'] * 100:.6f} %</b>. "
            "Il reste supérieur à la limite de 1 %; ce dossier ne permet donc pas une promotion stable.",
            styles["BodyText"],
        ),
        Paragraph("Le résultat négatif est conservé : il indique une différence de modèle entre MITC4 facettisé et CalculiX S8R, non un défaut masqué par manque de maillage.", styles["BodyText"]),
        Paragraph(
            "Sonde complémentaire : CalculiX 2.20 refuse l'option COMPOSITE avec S4 et ne l'autorise que pour S8R ou S6. "
            "Aucun oracle composite de même ordre n'est donc disponible dans cette campagne; cette sonde est exclue des critères d'acceptation.",
            styles["BodyText"],
        ),
        Spacer(1, 4 * mm), table, Spacer(1, 4 * mm),
        _image(EVIDENCE / "curved_orientation_correlation.png", 174),
        _image(EVIDENCE / "curved_orientation_deformation.png", 160),
    ]
    doc.build(story)
    if not OUTPUT.is_file() or OUTPUT.stat().st_size < 1000 or not OUTPUT.read_bytes().startswith(b"%PDF"):
        raise RuntimeError("Generated PDF is invalid or unexpectedly small.")


def _image(path: Path, width_mm: float) -> Image:
    with PilImage.open(path) as image:
        width_px, height_px = image.size
    width = width_mm * mm
    return Image(str(path), width=width, height=width * height_px / max(width_px, 1))


if __name__ == "__main__":
    raise SystemExit(main())
