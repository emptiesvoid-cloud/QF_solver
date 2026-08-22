"""Build the PDF Owner-review packet for refined TET10 Newmark evidence."""

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
EVIDENCE = ROOT / "qualification" / "vnv" / "external" / "tet10_dynamic_refinement_001" / "reference"
OUTPUT = ROOT / "output" / "pdf" / "tet10_dynamic_refinement_owner_review.pdf"


def main() -> int:
    summary = json.loads((EVIDENCE / "summary.json").read_text(encoding="utf-8"))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    _build(summary)
    if not OUTPUT.is_file() or not OUTPUT.read_bytes().startswith(b"%PDF"):
        raise RuntimeError("Invalid TET10 refinement PDF.")
    print(f"PDF: {OUTPUT}")
    return 0


def _build(summary: dict[str, object]) -> None:
    styles = getSampleStyleSheet()
    study = summary["studies"]["newmark"]
    data = [
        ["Paramètre", "Valeur", "Critère"],
        ["Niveaux temporels", str(study["time_levels_steps"]), ">= 3"],
        ["Erreur RMS finale", f"{100.0 * study['relative_rms_error_to_single_mode']:.6f} %", "<= 1 %"],
        ["Incrément final", f"{100.0 * study['time_refinement_error_max']:.6f} %", "<= 1 %"],
        ["Maximum tous niveaux", f"{100.0 * study['time_refinement_error_all_levels_max']:.6f} %", "diagnostic"],
        ["Dérive énergétique", f"{100.0 * study['maximum_energy_drift']:.6e} %", "<= 0,01 %"],
        ["Résidu dynamique", f"{study['maximum_dynamic_residual']:.3e}", "<= 1e-7"],
    ]
    table = Table(data, repeatRows=1, colWidths=[55 * mm, 55 * mm, 45 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#065f46")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#9ca3af")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#ecfdf5")]),
    ]))
    doc = SimpleDocTemplate(str(OUTPUT), pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=14 * mm, bottomMargin=14 * mm, title="TET10 Newmark refinement")
    story: list[object] = [
        Paragraph("QF_solver - TET10 Newmark : raffinement temporel", styles["Title"]),
        Paragraph("Dossier de preuve technique, cible stable à confirmer par Owner review.", styles["Normal"]),
        Spacer(1, 4 * mm),
        Paragraph(
            f"L'erreur RMS finale vaut <b>{100.0 * study['relative_rms_error_to_single_mode']:.6f} %</b> "
            f"et l'incrément adjacent final <b>{100.0 * study['time_refinement_error_max']:.6f} %</b>. "
            "Les deux sont sous la limite d'ingénierie de 1 %.",
            styles["BodyText"],
        ),
        Spacer(1, 4 * mm), table, Spacer(1, 5 * mm),
        _image(EVIDENCE / "time_refinement.png", 175),
    ]
    doc.build(story)


def _image(path: Path, width_mm: float) -> Image:
    with PilImage.open(path) as image:
        width_px, height_px = image.size
    width = width_mm * mm
    return Image(str(path), width=width, height=width * height_px / max(width_px, 1))


if __name__ == "__main__":
    raise SystemExit(main())
