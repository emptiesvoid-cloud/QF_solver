"""Build the compact V&V PDF for MITC3, TET4 total-Lagrangian and orthotropy."""

from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, SimpleDocTemplate, Spacer

from owner_review_pdf_support import (
    paragraph,
    review_footer,
    review_image,
    review_styles,
    review_table,
    validate_pdf,
)


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "qualification" / "vnv" / "vnv_plan_mitc3_tet4_orthotropic_2026-08-22.json"
OUTPUT = ROOT / "output" / "pdf" / "qf_solver_vnv_mitc3_tet4_orthotropic_2026-08-22.pdf"


def pct(value: float) -> str:
    return f"{100.0 * value:.4f} %"


def build_story(registry: dict[str, object]) -> list[object]:
    styles = review_styles()
    scopes = {str(row["id"]): row for row in registry["scopes"]}  # type: ignore[index]
    dynamic = scopes["mitc3-laminate-dynamic-thin-planar"]
    curved = scopes["mitc3-laminate-static-curved-mixed-transverse"]
    tl = scopes["tet4-total-lagrangian-structural-v2"]
    ortho = scopes["orthotropic-solid-tet4-tet10-static"]
    dm = dynamic["measurements"]
    cm = curved["measurements"]
    tm = tl["measurements"]
    om = ortho["measurements"]
    story: list[object] = [
        paragraph("QF_solver - Plan V&V et preuves", styles["title"]),
        paragraph("MITC3 dynamique | MITC3 courbe | TET4 total-lagrangien | orthotropie statique", styles["subtitle"]),
        Spacer(1, 7 * mm),
        paragraph("Verdict technique : PASS avec perimetres bornes", styles["pass"]),
        paragraph(
            "Ce document consolide les campagnes executees. Il ne constitue ni une certification ni une promotion automatique. "
            "Le TET4 total-lagrangien reste au statut recherche et more_evidence_required.",
            styles["body"],
        ),
        paragraph("Campagnes executees", styles["h1"]),
        review_table(
            [
                ["Campagne", "Resultat"],
                ["V&V ciblee MITC3 / orthotropie / TET4-TL", "13 passed, 6 skipped"],
                ["TET4-TL flambement", "1 passed"],
                ["TET4-TL post-flambement", "1 passed"],
                ["Suite complete", "Non relancee dans cette etape"],
            ],
            [110 * mm, 63 * mm],
            styles,
        ),
        paragraph("Decisions de perimetre", styles["h1"]),
        review_table(
            [
                ["Scope", "Decision", "Etat"],
                ["MITC3 dynamique mince plan", "stable borne", "PASS"],
                ["MITC3 courbe mixte/transverse", "stable borne", "PASS, marge faible"],
                ["Orthotropie statique TET4/TET10", "stable homogene", "PASS"],
                ["TET4 total-lagrangien", "more_evidence_required", "research"],
            ],
            [75 * mm, 58 * mm, 40 * mm],
            styles,
        ),
        PageBreak(),
        paragraph("MITC3 dynamique mince plan", styles["h1"]),
        paragraph(
            "Sous-perimetre : stratifié [0/90/90/0], t/L=0,01, petits déplacements, modal, Newmark et harmonique. "
            "La reference est Code_Aster DKT/TRIA3 comme limite mince, pas une identité de formulation.",
            styles["body"],
        ),
        review_table(
            [
                ["Mesure fine", "Valeur", "Limite"],
                ["Erreur modale", pct(float(dm["fine_modal_error"])), "<= 1 %"],
                ["Erreur Newmark", pct(float(dm["fine_newmark_error"])), "<= 1 %"],
                ["Erreur harmonique", pct(float(dm["fine_harmonic_error"])), "<= 1 %"],
                ["Résidu modal", f"{float(dm['fine_modal_residual']):.3e}", "<= 1e-7"],
                ["Résidu dynamique", f"{float(dm['fine_dynamic_residual']):.3e}", "<= 1e-7"],
            ],
            [72 * mm, 45 * mm, 43 * mm],
            styles,
        ),
        paragraph(
            "Conclusion : stable dans le sous-perimetre mince, plan et symetrique. Le residu modal fin vaut 1,08e-8 : "
            "il passe le seuil de campagne 1e-7 mais doit être réduit si un profil strict 1e-8 est exigé.",
            styles["note"],
        ),
        paragraph("MITC3 courbe mixte et transverse", styles["h1"]),
        review_table(
            [
                ["Mesure", "Mixte", "Transverse", "Limite"],
                ["Ecart externe", pct(float(cm["mixed_external_error"])), pct(float(cm["transverse_external_error"])), "<= 1 %"],
                ["Incrément QF", pct(float(cm["mixed_qf_mesh_increment"])), pct(float(cm["transverse_qf_mesh_increment"])), "<= 5 %"],
                ["Incrément externe", pct(float(cm["mixed_external_mesh_increment"])), pct(float(cm["transverse_external_mesh_increment"])), "<= 5 %"],
                ["Résidu libre", f"{float(cm['mixed_free_residual']):.2e}", f"{float(cm['transverse_free_residual']):.2e}", "<= 1e-8"],
            ],
            [55 * mm, 35 * mm, 35 * mm, 32 * mm],
            styles,
        ),
        paragraph(
            "Conclusion : stable borne sur le panneau cylindrique facettise, l'empilement [0/90/90/0] et les deux charges. "
            "Le chargement axial reste exclu : son incrément atteint 8,47 % dans la campagne dédiée.",
            styles["pass"],
        ),
        PageBreak(),
        paragraph("TET4 total-lagrangien", styles["h1"]),
        paragraph(
            "Le kernel Green-Lagrange / Saint-Venant-Kirchhoff, le push-forward PK2-Cauchy, le determinant positif et la continuation "
            "arc-length sont verifies. La promotion stable reste bloquée.",
            styles["body"],
        ),
        review_table(
            [
                ["Mesure", "Valeur", "Lecture"],
                ["Erreur Euler h5", pct(float(tm["h5_euler_error"])), "> 1 %, <= 5 %"],
                ["Ecart QF / CalculiX", pct(float(tm["h5_qf_calculix_difference"])), "accord externe"],
                ["Résidu post-flambement", f"{float(tm['postbuckling_max_residual']):.3e}", "PASS recherche"],
                ["min det(F)", f"{float(tm['postbuckling_minimum_det_f']):.6f}", "> 0"],
                ["Pmax / Euler", f"{float(tm['postbuckling_max_load_over_euler']):.4f}", "branche post-critique"],
            ],
            [70 * mm, 45 * mm, 45 * mm],
            styles,
        ),
        paragraph(
            "Decision : more_evidence_required. Un maillage futur d'environ 1,2 million d'elements ne suffira pas seul : "
            "il faudra aussi mesurer la robustesse du chemin, les ressources, la positivité de F, une correlation et une revue independante.",
            styles["fail"],
        ),
        paragraph("Orthotropie statique TET4/TET10", styles["h1"]),
        review_table(
            [
                ["Famille", "Erreur déplacement", "Erreur énergie", "Résidu"],
                ["TET4, 564 525 éléments", pct(float(om["tet4_tip_error"])), pct(float(om["tet4_energy_error"])), f"{float(om['tet4_free_residual']):.2e}"],
                ["TET10, 2 607 éléments", pct(float(om["tet10_tip_error"])), pct(float(om["tet10_energy_error"])), f"{float(om['tet10_free_residual']):.2e}"],
            ],
            [65 * mm, 38 * mm, 38 * mm, 30 * mm],
            styles,
        ),
        paragraph(
            "Conclusion : stable dans le domaine homogène statique documente, avec orientation constante et sans extrapolation "
            "aux fibres courbes continues, au composite pli par pli ou au dommage.",
            styles["pass"],
        ),
        PageBreak(),
        paragraph("Preuves visuelles et traçabilité", styles["h1"]),
        paragraph(
            "Les figures ci-dessous sont les sorties des campagnes. Les fichiers JSON, rapports Markdown et tests sont les sources de mesure ; "
            "le PDF est une vue de revue et ne remplace pas les artefacts bruts.",
            styles["body"],
        ),
    ]
    images = [
        ROOT / "qualification" / "vnv" / "external" / "code_aster_mitc3_laminate_dynamic_refinement_dkt_2026-08-21" / "reference" / "mitc3_laminate_dynamic_refinement.png",
        ROOT / "qualification" / "vnv" / "external" / "code_aster_mitc3_curved_laminate_refinement_027" / "reference" / "convergence_qf_code_aster.png",
        ROOT / "qualification" / "vnv" / "orthotropic_solid_convergence_large_cg_006" / "reference" / "orthotropic_convergence.png",
        ROOT / "qualification" / "tet4_tl_buckling_h5" / "reference" / "buckling_h5_convergence.png",
        ROOT / "results" / "VNV-TET4-TL-POSTBUCKLING-007" / "postbuckling_paths.png",
    ]
    for index, path in enumerate(images, start=1):
        figure = review_image(path, ROOT / "tmp" / f"vnv_scope_{index}.png", max_height=52 * mm)
        if figure is not None:
            story.extend([Spacer(1, 3 * mm), figure])
    story.extend(
        [
            paragraph("Questions Owner", styles["h1"]),
            review_table(
                [
                    ["ID", "Question", "Réponse"],
                    ["Q1", "MITC3 dynamique mince plan stable dans son sous-perimetre ?", ""],
                    ["Q2", "MITC3 courbe mixte/transverse stable borne malgré la marge proche de 5 % ?", ""],
                    ["Q3", "Exclusions axial, courbure dynamique, S13/S23, dommage et delamination maintenues ?", ""],
                    ["Q4", "Orthotropie statique TET4/TET10 stable uniquement dans le domaine homogene ?", ""],
                    ["Q5", "TET4 total-lagrangien maintenu more_evidence_required jusqu'a la campagne 1,2 M et la revue independante ?", ""],
                ],
                [13 * mm, 130 * mm, 25 * mm],
                styles,
            ),
        ]
    )
    return story


def main() -> int:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(OUTPUT), pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm,
        topMargin=14 * mm, bottomMargin=14 * mm,
        title="QF_solver V&V MITC3 TET4 orthotropy",
    )
    document.build(build_story(registry), onFirstPage=review_footer, onLaterPages=review_footer)
    validate_pdf(OUTPUT, ["Plan V&V et preuves", "TET4 total-lagrangien", "more_evidence_required", "Questions Owner"], 4)
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
