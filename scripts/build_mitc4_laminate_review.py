"""Build a portable PDF review pack for the MITC4 laminate scope."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "assets" / "reviews" / "revue_mitc4_multicouche.pdf"
FIGURES = (
    ("Convergence structurelle multicouche", ROOT / "docs" / "assets" / "reviews" / "composite_structural_convergence.png"),
    ("Maillage et deformee multicouche", ROOT / "docs" / "assets" / "reviews" / "composite_bending_deformation.png"),
    ("Correlation CalculiX S8R", ROOT / "docs" / "assets" / "reviews" / "calculix_composite_correlation.png"),
    ("Benchmark NAFEMS et Code_Aster", ROOT / "docs" / "assets" / "reviews" / "nafems_r0031_convergence.png"),
)


def main() -> int:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    body = styles["BodyText"]
    body.leading = 14
    title = styles["Title"]
    subtitle = styles["Heading2"]
    story = [
        Paragraph("QF_solver - Revue mecanique MITC4 multicouche", title),
        Paragraph("Decision engineering interne : accepted_with_recommendations - 26 juillet 2026", subtitle),
        Spacer(1, 0.35 * cm),
        Paragraph(
            "Validateur : Quentin Farinazzo, auteur et validateur mecanique. "
            "Mode : self_review non independant. Aucune revendication de certification externe.",
            body,
        ),
        Spacer(1, 0.25 * cm),
        Paragraph("Domaine accepte", subtitle),
        Paragraph(
            "MITC4 multicouche lineaire en petits deplacements, proprietes pli par pli, "
            "resultantes A/B/D, contraintes aux faces de pli et indicateurs de premier pli. "
            "Le statut experimental est maintenu.",
            body,
        ),
        Spacer(1, 0.25 * cm),
        Paragraph("Synthese des preuves", subtitle),
        Table(
            [
                ["Campagne", "Verdict", "Indicateur"],
                ["Analytique A/B/D", "PASS", "six controles < 1e-12"],
                ["Convergence MITC4", "PASS", "residu libre max 6.22e-9"],
                ["CalculiX S8R", "PASS", "ecart fleche fin 0.0310 %"],
                ["NAFEMS / Code_Aster", "PASS", "QF/NAFEMS 0.458 %, QF/Aster 0.251 %"],
            ],
            colWidths=(5.3 * cm, 2.2 * cm, 8.0 * cm),
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e5f")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#7a8790")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            ),
        ),
        Spacer(1, 0.3 * cm),
        Paragraph("Recommandations et limites", subtitle),
        Paragraph(
            "Comparer les contraintes par pli hors zones singulieres. Conserver hors scope S13 de dimensionnement, "
            "delaminage, dommage progressif, Hashin, Puck, grandes rotations et fibres courbes continues.",
            body,
        ),
    ]
    for caption, path in FIGURES:
        if not path.is_file():
            raise FileNotFoundError(path)
        story.extend([PageBreak(), Paragraph(caption, subtitle), Spacer(1, 0.2 * cm)])
        image = Image(str(path))
        image._restrictSize(17.0 * cm, 21.5 * cm)
        story.append(image)
    document = SimpleDocTemplate(str(OUTPUT), pagesize=A4, rightMargin=1.6 * cm, leftMargin=1.6 * cm, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    document.build(story)
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
