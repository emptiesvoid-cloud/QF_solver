"""Build the controlled Owner-review PDF for orthotropic modal/Newmark promotion."""

from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, SimpleDocTemplate, Spacer

from owner_review_pdf_support import paragraph, review_footer, review_image, review_styles, review_table, validate_pdf


ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "qualification" / "vnv" / "orthotropic_modal_newmark" / "reference" / "summary.json"
OUTPUT = ROOT / "output" / "pdf" / "orthotropic_modal_newmark_stable_owner_review.pdf"


def main() -> int:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    styles = review_styles()
    checks = {str(row["id"]): row for row in summary["checks"]}
    rows = [["Controle", "Valeur", "Limite", "Statut"]]
    rows.extend(
        [
            ["Erreur modale fine / theorie", f"{100 * checks['modal_fine_theory']['value']:.6f} %", "<= 1 %", checks["modal_fine_theory"]["status"]],
            ["Raffinement Newmark final", f"{100 * checks['newmark_time_refinement']['value']:.6f} %", "<= 1 %", checks["newmark_time_refinement"]["status"]],
            ["Residu modal", f"{checks['modal_residual']['value']:.3e}", "<= 1e-8", checks["modal_residual"]["status"]],
            ["Orthogonalite de masse", f"{checks['modal_mass_orthogonality']['value']:.3e}", "<= 1e-8", checks["modal_mass_orthogonality"]["status"]],
            ["Residu dynamique", f"{checks['newmark_residual']['value']:.3e}", "<= 1e-7", checks["newmark_residual"]["status"]],
            ["Correlation frequence Code_Aster", f"{100 * checks['code_aster_modal']['value']:.3e} %", "<= 1 %", checks["code_aster_modal"]["status"]],
            ["Correlation RMS Newmark Code_Aster", f"{100 * checks['code_aster_newmark']['value']:.3e} %", "<= 1 %", checks["code_aster_newmark"]["status"]],
        ]
    )
    story = [
        paragraph("QF_solver - Owner review cible stable", styles["title"]),
        paragraph("Solide orthotrope TET4 : modal et Newmark", styles["subtitle"]),
        Spacer(1, 8 * mm),
        paragraph("Objet", styles["h1"]),
        paragraph(
            "Ce dossier presente la campagne raffinee de verification du domaine axial orthotrope TET4. "
            "Il ne constitue pas une promotion automatique : la decision Owner et la signature restent obligatoires.",
            styles["body"],
        ),
        paragraph("Resultat technique : PASS_TECHNICAL_VERIFICATION. Cible proposee : stable, uniquement dans le domaine declare.", styles["pass"]),
        paragraph("Mesures principales", styles["h1"]),
        review_table(rows, [68 * mm, 35 * mm, 28 * mm, 30 * mm], styles),
        Spacer(1, 5 * mm),
        paragraph(
            "Le modal utilise quatre niveaux de maillage, avec une erreur theorique fine de 0,00772 %. "
            "Le Newmark utilise huit pas, de 2e-4 s a 1,5625e-6 s; l'increment adjacent final vaut 0,1119 %. "
            "La correlation Code_Aster 18.1.0 est realisee sur la meme connectivite et la meme grille temporelle.",
            styles["body"],
        ),
        PageBreak(),
        paragraph("Questions Owner", styles["h1"]),
        review_table(
            [
                ["ID", "Question", "Reponse Owner"],
                ["Q1", "Les quatre niveaux de maillage et l'erreur modale fine <= 1 % couvrent-ils le domaine axial declare ?", ""],
                ["Q2", "La masse, les axes materiau, la correlation Code_Aster et les invariants sont-ils acceptables ?", ""],
                ["Q3", "Les huit niveaux Newmark et l'increment final 0,1119 % justifient-ils la cible stable ?", ""],
                ["Q4", "Les exclusions : courbure continue, dommage, plasticite anisotrope, grandes deformations et composite pli par pli, sont-elles maintenues ?", ""],
                ["Q5", "Decision Owner : accepted, accepted_with_recommendations ou more_evidence_required ?", ""],
            ],
            [15 * mm, 118 * mm, 28 * mm],
            styles,
        ),
        Spacer(1, 6 * mm),
        paragraph("Artefacts", styles["h1"]),
        paragraph(
            "qualification/vnv/orthotropic_modal_newmark/reference/summary.json; report.md; "
            "modal_convergence.png; newmark_convergence.png; code_aster_newmark.png; "
            "qualification/maturity_evidence_0_2_1/orthotropic.json.",
            styles["small"],
        ),
    ]
    figure = review_image(ROOT / "qualification" / "vnv" / "orthotropic_modal_newmark" / "reference" / "modal_convergence.png", ROOT / "tmp" / "orthotropic_modal_pdf_modal.png", max_height=60 * mm)
    if figure is not None:
        story.extend([Spacer(1, 4 * mm), figure])
    dynamic_figure = review_image(ROOT / "qualification" / "vnv" / "orthotropic_modal_newmark" / "reference" / "newmark_convergence.png", ROOT / "tmp" / "orthotropic_modal_pdf_newmark.png", max_height=60 * mm)
    if dynamic_figure is not None:
        story.extend([Spacer(1, 4 * mm), dynamic_figure])
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    SimpleDocTemplate(str(OUTPUT), pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=14 * mm, bottomMargin=14 * mm, title="Orthotropic stable owner review").build(story, onFirstPage=review_footer, onLaterPages=review_footer)
    validate_pdf(OUTPUT, ["Owner review cible stable", "Raffinement Newmark final", "Q5"], 2)
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
