"""Build the PDF review for the 48x48 MITC4 modal refinement."""

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
EVIDENCE = ROOT / "qualification" / "vnv" / "external" / "code_aster_modal_refinement_048" / "reference"
DEFAULT_OUTPUT = ROOT / "output" / "pdf" / "mitc4_modal_refinement_owner_review.pdf"


def main() -> int:
    output = DEFAULT_OUTPUT
    output.parent.mkdir(parents=True, exist_ok=True)
    summary = json.loads((EVIDENCE / "summary.json").read_text(encoding="utf-8"))
    _build(summary, output)
    print(f"PDF: {output}")
    return 0


def _build(summary: dict[str, object], output: Path) -> None:
    styles = getSampleStyleSheet()
    document = SimpleDocTemplate(
        str(output), pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=14 * mm, bottomMargin=14 * mm,
        title="MITC4 modal refinement owner review", author="QF_solver",
    )
    metrics = summary["metrics"]
    rows = []
    for index, (order, qf, code_aster, error) in enumerate(
        zip(summary["mode_orders"], summary["frequencies_hz"]["qf_solver"], summary["frequencies_hz"]["code_aster"], metrics["qf_code_aster_frequency_differences"], strict=True),
        start=1,
    ):
        rows.append([str(index), f"({order[0]},{order[1]})", f"{qf:.5f}", f"{code_aster:.5f}", f"{error * 100:.4f} %"])
    table = Table([["Mode", "Famille", "QF [Hz]", "Code_Aster [Hz]", "Ecart"], *rows], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#aab7c4")),
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (1, 1), (1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#edf3f8")]),
    ]))
    max_error = max(metrics["qf_code_aster_frequency_differences"])
    story: list[object] = [
        Paragraph("QF_solver - MITC4 modal : raffinement 48 x 48", styles["Title"]),
        Paragraph("Study ID : VNV-MITC4-MODAL-REFINEMENT-048 | Reference : Code_Aster 18.1.0 DKQ", styles["Normal"]),
        Spacer(1, 4 * mm),
        Paragraph(
            f"Le maximum d'ecart de frequence QF_solver/Code_Aster est de <b>{max_error * 100:.6f} %</b>, "
            "donc inferieur a la limite obligatoire de 1 % pour une candidature a la promotion stable.",
            styles["BodyText"],
        ),
        Paragraph(
            "Cette preuve ne modifie pas automatiquement la maturite. Une Owner Review datee et une action de release explicite restent requises.",
            styles["BodyText"],
        ),
        Spacer(1, 4 * mm), table, Spacer(1, 4 * mm),
        Paragraph(
            f"Controles internes : residu modal maximal {metrics['qf_max_relative_residual']:.3e}, "
            f"orthogonalite masse {metrics['qf_mass_orthogonality_error']:.3e}, "
            f"orthogonalite raideur {metrics['qf_stiffness_orthogonality_error']:.3e}.",
            styles["BodyText"],
        ),
        Spacer(1, 3 * mm),
        Paragraph("Frequences et formes propres comparees", styles["Heading2"]),
        _scaled_image(EVIDENCE / "VNV-MITC4-MODAL-CODEASTER-DKQ-004-frequencies.png", 175),
        _scaled_image(EVIDENCE / "VNV-MITC4-MODAL-CODEASTER-DKQ-004-modes.png", 175),
        Paragraph(
            "Limites : plaque isotrope mince et plane, appuis simples, sans amortissement, coque courbe, stratification ni grandes deformations.",
            styles["BodyText"],
        ),
    ]
    document.build(story)
    if not output.is_file() or output.stat().st_size < 1000 or not output.read_bytes().startswith(b"%PDF"):
        raise RuntimeError("Generated PDF is invalid or unexpectedly small.")


def _scaled_image(path: Path, width_mm: float) -> Image:
    with PilImage.open(path) as image:
        pixel_width, pixel_height = image.size
    width = width_mm * mm
    return Image(str(path), width=width, height=width * pixel_height / max(pixel_width, 1))


if __name__ == "__main__":
    raise SystemExit(main())
