"""Build the current element-family Owner review PDFs.

The pack is deliberately evidence-led: it reports the recorded Owner
decisions, the numerical values used for the decision, and the exclusions that
remain binding. It does not promote a scope automatically.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output" / "pdf"
DATE = "2026-08-21"


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "pack_title", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=19, leading=23, alignment=1, textColor=colors.HexColor("#123B4A"),
        ),
        "subtitle": ParagraphStyle(
            "pack_subtitle", parent=base["BodyText"], fontName="Helvetica",
            fontSize=9.5, leading=12, alignment=1, textColor=colors.HexColor("#425563"),
        ),
        "h1": ParagraphStyle(
            "pack_h1", parent=base["Heading1"], fontName="Helvetica-Bold",
            fontSize=14, leading=17, spaceBefore=5, spaceAfter=6,
            textColor=colors.HexColor("#123B4A"),
        ),
        "h2": ParagraphStyle(
            "pack_h2", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=10.5, leading=13, spaceBefore=5, spaceAfter=4,
            textColor=colors.HexColor("#236177"),
        ),
        "body": ParagraphStyle(
            "pack_body", parent=base["BodyText"], fontName="Helvetica",
            fontSize=8.5, leading=11.5, spaceAfter=4,
        ),
        "small": ParagraphStyle(
            "pack_small", parent=base["BodyText"], fontName="Helvetica",
            fontSize=7.2, leading=9, spaceAfter=2,
        ),
        "note": ParagraphStyle(
            "pack_note", parent=base["BodyText"], fontName="Helvetica-Bold",
            fontSize=8.2, leading=11, textColor=colors.HexColor("#733800"),
            backColor=colors.HexColor("#FFF3DC"), borderPadding=5, spaceAfter=6,
        ),
    }


def _p(value: object, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(str(value)).replace("\n", "<br/>"), style)


def _table(rows: list[list[object]], widths: list[float], styles: dict[str, ParagraphStyle]) -> Table:
    header = ParagraphStyle("pack_table_header", parent=styles["small"], fontName="Helvetica-Bold", textColor=colors.white)
    cell = ParagraphStyle("pack_table_cell", parent=styles["small"], fontName="Helvetica")
    rendered = [
        [_p(value, header if index == 0 else cell) for value in row]
        for index, row in enumerate(rows)
    ]
    table = Table(rendered, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#123B4A")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#AAB7B8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), (colors.white, colors.HexColor("#F3F7F8"))),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def _footer(canvas: Any, document: Any) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#425563"))
    canvas.drawString(15 * mm, 9 * mm, "QF_solver - Owner review interne - aucune certification externe revendiquee")
    canvas.drawRightString(A4[0] - 15 * mm, 9 * mm, f"Page {document.page}")
    canvas.restoreState()


def _load(relative: str) -> dict[str, Any]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def _decision(relative: str) -> tuple[str, str, str]:
    data = _load(relative)
    decision = str(data.get("decision", "pending"))
    target = str(data.get("promotion_target", data.get("maturity_target", "-")))
    status = str(data.get("status", "-"))
    return status, decision, target


def _common_header(
    title: str,
    scope: str,
    status: str,
    decision: str,
    target: str,
    styles: dict[str, ParagraphStyle],
) -> list[object]:
    return [
        Paragraph("QF_solver", styles["title"]),
        Spacer(1, 3 * mm),
        Paragraph(title, styles["subtitle"]),
        Spacer(1, 5 * mm),
        _table([
            ["Scope", "Statut de fiche", "Decision machine", "Cible"],
            [scope, status, decision, target],
        ], [49 * mm, 38 * mm, 51 * mm, 32 * mm], styles),
        Spacer(1, 4 * mm),
    ]


def _questions(
    questions: list[tuple[str, str]],
    styles: dict[str, ParagraphStyle],
) -> list[object]:
    rows = [["ID", "Question", "Reponse Owner"]]
    rows.extend([[identifier, question, answer] for identifier, question, answer in questions])
    return [Paragraph("Questions et decisions", styles["h2"]), _table(rows, [14 * mm, 121 * mm, 35 * mm], styles)]


def _limits(values: list[str], styles: dict[str, ParagraphStyle]) -> list[object]:
    rows = [["#", "Limite obligatoire"]]
    rows.extend([[index, value] for index, value in enumerate(values, 1)])
    return [Spacer(1, 3 * mm), Paragraph("Limites a conserver", styles["h2"]), _table(rows, [10 * mm, 160 * mm], styles)]


def _evidence(values: list[str], styles: dict[str, ParagraphStyle]) -> list[object]:
    rows = [["#", "Artefact de preuve"]]
    rows.extend([[index, value] for index, value in enumerate(values, 1)])
    return [Spacer(1, 3 * mm), Paragraph("Tracabilite", styles["h2"]), _table(rows, [10 * mm, 160 * mm], styles)]


def _section(
    title: str,
    scope: str,
    review_json: str,
    intro: str,
    result_rows: list[list[object]],
    questions: list[tuple[str, str, str]],
    limits: list[str],
    evidence: list[str],
    styles: dict[str, ParagraphStyle],
) -> list[object]:
    status, decision, target = _decision(review_json)
    story = _common_header(title, scope, status, decision, target, styles)
    story.extend([
        Paragraph(intro, styles["body"]),
        Paragraph(
            "Lecture : la cible stable est bornee aux hypotheses et observables enumeres. "
            "Les valeurs intermediaires et les diagnostics non acceptes restent consultables dans les artefacts.",
            styles["note"],
        ),
        Paragraph("Resultats de decision", styles["h2"]),
        _table(result_rows, [64 * mm, 45 * mm, 30 * mm, 31 * mm], styles),
    ])
    story.extend(_questions([(item[0], item[1], item[2]) for item in questions], styles))
    story.extend(_limits(limits, styles))
    story.extend(_evidence(evidence, styles))
    story.extend([
        Spacer(1, 4 * mm),
        Paragraph(
            "Owner enregistre : Quentin Farinazzo, declaration electronique du " + DATE + ". "
            "Cette declaration n'est pas une revue independante et ne constitue pas une certification externe.",
            styles["small"],
        ),
    ])
    return story


def _mitc3(styles: dict[str, ParagraphStyle]) -> list[object]:
    return _section(
        "Owner review - MITC3 isotrope classique",
        "mitc3-modal / mitc3-transient-dynamic / mitc3-harmonic-response",
        "qualification/reviews/mitc3_classic_stable_owner_review_pending.json",
        "Promotion stable enregistree pour le MITC3 isotrope plan classique. La preuve couvre une progression 8x2, 16x4 et 24x6 avec une correlation Code_Aster DKT/TRIA3.",
        [
            ["Niveau", "Triangles", "Modal", "Newmark"],
            ["8x2", "32", "7,719395 %", "1,453716 %"],
            ["16x4", "128", "1,736652 %", "0,549633 %"],
            ["24x6", "288", "0,673329 %", "0,174158 %"],
            ["Harmonique final", "-", "0,096638 %", "PASS"],
        ],
        [
            ("Q1", "Les trois niveaux couvrent-ils le cas isotrope plan borne ?", "OUI"),
            ("Q2", "Erreur modale finale, residus et orthogonalites acceptables ?", "OUI"),
            ("Q3", "Newmark, harmonique et energie acceptables ?", "OUI"),
            ("Q4", "Correlation Code_Aster acceptable comme oracle complementaire ?", "OUI"),
            ("Q5", "Exclusions courbe, stratifie, non-lineaire et singulieres acceptees ?", "OUI"),
            ("Q6", "Decision", "STABLE"),
        ],
        [
            "Coques planes isotropes, petits deplacements, epaisseur constante.",
            "Pas de geometrie courbe, stratifies, contact, dommage ou grandes rotations.",
            "Les contraintes aux singularites restent informatives.",
        ],
        [
            "docs/verification/mitc3_classic_stable_owner_review.md",
            "qualification/maturity_evidence_0_2_1/mitc3_dynamic_refinement/summary.json",
            "qualification/evidence/code_aster_correlation_campaign_2026-08-14/studies/mitc3_dynamic/summary.json",
        ],
        styles,
    )


def _mitc4_classic(styles: dict[str, ParagraphStyle]) -> list[object]:
    return _section(
        "Owner review - MITC4 isotrope classique",
        "mitc4-linear-static / mitc4-modal / mitc4-transient-dynamic / mitc4-harmonic-response",
        "qualification/reviews/mitc4_classic_stable_owner_review_pending.json",
        "Le MITC4 isotrope classique est stable dans le domaine des coques facettisees admissibles, avec statique, dix modes, Newmark et harmonique. Les ecarts spatiaux externes conserves sont des diagnostics de formulation et non des observables primaires de promotion.",
        [
            ["Scope", "Observable primaire", "Valeur", "Limite"],
            ["Statique", "Code_Aster deplacement", "0,726108 %", "1 %"],
            ["Modal", "frequence max 10 modes", "0,782014 %", "1 %"],
            ["Modal", "MAC minimal", "0,99999981", "0,95"],
            ["Newmark", "RMS", "0,09867227 %", "1 %"],
            ["Harmonique", "erreur finale", "0,547102 %", "1 %"],
        ],
        [
            ("Q1", "Statique et correlation sous 1 % suffisantes ?", "OUI"),
            ("Q2", "Dix frequences, MAC et residus suffisants ?", "OUI"),
            ("Q3", "Newmark et stabilite energetique acceptables ?", "OUI"),
            ("Q4", "Harmonique et limite 0 Hz acceptables ?", "OUI"),
            ("Q5", "Exclusions clairement acceptees ?", "OUI"),
            ("Q6", "Decision", "STABLE"),
        ],
        [
            "MITC4 isotrope homogene, petits deplacements, epaisseur constante.",
            "Stratifies, grandes rotations, contact, dommage, delamination exclus.",
            "Singularites ponctuelles non utilisees comme critere de contrainte.",
        ],
        [
            "docs/verification/mitc4_classic_stable_owner_review.md",
            "output/pdf/mitc4_static_code_aster_refinement_owner_review.pdf",
            "output/pdf/mitc4_modal_refinement_owner_review.pdf",
            "output/pdf/mitc4_harmonic_refinement_owner_review.pdf",
        ],
        styles,
    )


def _mitc4_laminate_static(styles: dict[str, ParagraphStyle]) -> list[object]:
    return _section(
        "Owner review - MITC4 multicouche statique",
        "mitc4-laminate-static",
        "qualification/reviews/mitc4_laminate_static_stable_owner_review_pending.json",
        "Le sous-perimetre stable est la plaque plane reguliere symetrique [0/90/90/0] sous membrane, flexion et chargement combine. Le probe courbe oblique est volontairement conserve hors de cette promotion.",
        [
            ["Observable", "Valeur fine", "Limite", "Statut"],
            ["Membrane contraintes par pli", "0,00389 %", "1 %", "PASS"],
            ["Flexion contraintes par pli", "0,25389 %", "1 %", "PASS"],
            ["Combine contraintes par pli", "0,03791 %", "1 %", "PASS"],
            ["QF / NAFEMS", "0,45761 %", "1 %", "PASS"],
            ["QF / Code_Aster", "0,87852 %", "1 %", "PASS"],
        ],
        [
            ("Q1", "Domaine plan et trois chargements suffisamment definis ?", "OUI"),
            ("Q2", "Erreurs principales et residu 2,457e-10 acceptables ?", "OUI"),
            ("Q3", "Courbure oblique, distorsion, S13/S23 et dommage exclus ?", "OUI"),
            ("Q4", "Decision", "STABLE"),
        ],
        [
            "Plaque plane reguliere [0/90/90/0], elasticite lineaire.",
            "Coques courbes obliques et maillages distordus exclus.",
            "S13/S23, singularites, dommage, rupture et delamination exclus.",
        ],
        [
            "docs/verification/mitc4_laminate_static_planar_stable_owner_review.md",
            "qualification/vnv/mitc4_laminate_static_planar_stable_001/reference/nafems_vnv_manifest.json",
            "output/pdf/mitc4_laminate_static_planar_stable_owner_review.pdf",
        ],
        styles,
    )


def _mitc4_laminate_dynamic(styles: dict[str, ParagraphStyle]) -> list[object]:
    return _section(
        "Owner review - MITC4 multicouche dynamique",
        "mitc4-laminate-dynamic-refined-three-layups",
        "qualification/reviews/mitc4_laminate_dynamic_refined_three_layups_stable_owner_review_pending.json",
        "La cloture porte sur trois empilements symetriques plans et les routes modale, Newmark et harmonique. Le cas [0/45/45/0] inclut un amortissement proportionnel a la masse. Le niveau 48x12 est obligatoire pour le layup angle-ply.",
        [
            ["Empilement", "Modal", "Newmark", "Harmonique"],
            ["[0/90/90/0]", "0,1303 %", "0,0272 %", "0,0144 %"],
            ["[45/-45/-45/45]", "0,3792 %", "0,4841 %", "0,2613 %"],
            ["[0/45/45/0] amorti", "0,1281 %", "0,0669 %", "0,0349 %"],
            ["Maximum final", "0,3792 %", "0,4841 %", "0,2613 %"],
        ],
        [
            ("Q1", "Trois layups et niveaux couvrent-ils le domaine plan ?", "OUI"),
            ("Q2", "Le niveau final 48x12 sous 1 % est-il acceptable ?", "OUI"),
            ("Q3", "Les exclusions courbure, B non nul, dommage et rupture sont-elles acceptees ?", "OUI"),
            ("Q4", "Decision", "STABLE"),
        ],
        [
            "Stable seulement pour les trois layups plans declares et les analyses couvertes.",
            "Le niveau intermediaire 36x9 reste publie, meme lorsqu'il depasse 1 %.",
            "Coques courbes dynamiques, layups non symetriques, grandes deformations et amortissement calibre exclus.",
            "Dommage, rupture et delamination exclus; le cas reserve 10 000 QUAD4 reste hors acceptance.",
        ],
        [
            "docs/verification/mitc4_laminate_dynamic_refined_three_layups_stable_owner_review.md",
            "qualification/vnv/external/code_aster_mitc4_laminate_dynamic_refinement_48x12_032/reference/",
            "output/pdf/mitc4_laminate_dynamic_extended_owner_review.pdf",
        ],
        styles,
    )


def _tet4(styles: dict[str, ParagraphStyle]) -> list[object]:
    data = _load("qualification/reviews/tet4_stable_promotion_owner_review_pending.json")
    metrics = data["key_metrics_for_review"]
    rows = [["Cas", "Elements", "Modal", "Newmark"]]
    for name, values in metrics.items():
        rows.append([
            name,
            values.get("elements", "-"),
            f"{float(values['modal_frequency_error_max']):.4e}",
            f"{float(values['newmark_history_error_max']):.4e}",
        ])
    return _section(
        "Owner review - TET4 isotrope",
        "tet4-linear-static / tet4-modal / tet4-transient-dynamic / tet4-harmonic-response",
        "qualification/reviews/tet4_stable_promotion_owner_review_pending.json",
        "Le TET4 isotrope est promu stable dans le domaine documente : trois geometries, routes statique/modal/Newmark/harmonique et correlations Code_Aster meme-maillage. Les valeurs ci-dessous sont les fractions d'erreur conservees par le registre.",
        rows,
        [
            ("Q1", "Trois geometries et quatre routes couvrent-elles le domaine ?", "OUI"),
            ("Q2", "Correlations, residus et invariants acceptables ?", "OUI"),
            ("Q3", "Raffinement epais avec increment statique 4,972 % suffisant ?", "OUI"),
            ("Q4", "Isotropie, petits deplacements, sans amortissement/non-linearite ?", "OUI"),
            ("Q5", "Stable acceptable sans extrapolation ?", "OUI"),
            ("Q6", "Decision", "STABLE"),
        ],
        [
            "TET4 isotrope, petits deplacements et analyses lineaires declarees.",
            "Non-linearite, contact, amortissement general et grandes transformations exclus.",
            "Le raffinement final reste une recommandation de suivi, non un changement de domaine.",
        ],
        [
            "docs/verification/tet4_stable_promotion_owner_review_0_2_1.md",
            "qualification/maturity_evidence_0_2_1/tet4_stable_batch_01/report.md",
            "qualification/maturity_evidence_0_2_1/tet4_stable_batch_01/code_aster_tet4_cylinder_dynamic/summary.json",
        ],
        styles,
    )


def _mitc4_orthotropic(styles: dict[str, ParagraphStyle]) -> list[object]:
    return _section(
        "Owner review - MITC4 orthotrope homogene mono-pli",
        "mitc4-orthotropic-homogeneous-ply",
        "qualification/reviews/mitc4_orthotropic_one_ply_stable_pending.json",
        "Le sous-perimetre orthotrope utilise une lamelle unique via shell_laminate. La promotion stable est bornee aux axes 0/45/90 sur plaques planes et a l'orientation axiale 0 degre sur panneau courbe facettise. Elle ne constitue pas une qualification composite pli par pli.",
        [
            ["Cas", "Observable", "Ecart", "Statut"],
            ["Statique 0/45/90", "residus libres", "8,09e-12 a 2,39e-10", "PASS"],
            ["Modal plan 0 deg", "Code_Aster", "0,892 %", "PASS"],
            ["Modal plan 45 deg", "Code_Aster", "0,884 %", "PASS"],
            ["Modal plan 90 deg", "Code_Aster", "0,604 %", "PASS"],
            ["Newmark plan 45 deg", "Code_Aster", "0,413 %", "PASS"],
            ["Harmonique plan 45 deg", "Code_Aster", "0,251 %", "PASS"],
            ["Courbe dynamique 32x16", "harmonique", "16,30 %", "DIAGNOSTIC"],
        ],
        [
            ("Q1", "Geometrie, axes, projection et aires de reference correctement decrits ?", "OUI"),
            ("Q2", "Masse coherente, invariants et transformation globale/materiau acceptables ?", "OUI"),
            ("Q3", "Correlation Code_Aster et CalculiX coherente dans le domaine borne ?", "OUI"),
            ("Q4", "Rupture, dommage, delamination et orientation courbe non axiale exclus ?", "OUI"),
            ("Q5", "Decision", "STABLE borne"),
        ],
        [
            "Une seule lamelle orthotrope homogene via shell_laminate.",
            "Pas de qualification composite pli par pli, rupture, dommage ou delamination.",
            "Orientation continue non axiale sur surface courbe exclue.",
            "Le diagnostic courbe dynamique 32x16 (16,30 % harmonique) est hors acceptance et reste visible.",
        ],
        [
            "docs/verification/mitc4_stable_package/orthotropic_one_ply_results_2026-08-21.md",
            "docs/verification/mitc4_stable_package/completion_audit.md",
            "qualification/reviews/mitc4_orthotropic_one_ply_stable_pending.json",
            "output/pdf/mitc4_orthotropic_one_ply_technical_results.pdf",
        ],
        styles,
    )


def _tet10(styles: dict[str, ParagraphStyle]) -> list[object]:
    return _section(
        "Owner review - TET10 isotrope",
        "tet10-linear-static / tet10-modal / tet10-transient-dynamic / tet10-harmonic-response",
        "qualification/reviews/tet10_stable_promotion_owner_review_pending.json",
        "Le TET10 isotrope est promu stable dans le domaine lineaire documente. Le dossier combine CalculiX C3D10, Code_Aster TETRA10, trois geometries, une preuve amortie et des sondes de contraintes interieures hors singularites.",
        [
            ["Route", "Reference", "Ecart max", "Statut"],
            ["Statique", "CalculiX C3D10", "6,840e-05", "PASS"],
            ["Statique same-mesh", "Code_Aster TETRA10", "3,872e-09 %", "PASS"],
            ["Modal", "Code_Aster TETRA10", "3,225e-11", "PASS"],
            ["Newmark", "Code_Aster TETRA10", "5,779e-12", "PASS"],
            ["Harmonique", "Code_Aster TETRA10", "6,190e-12", "PASS"],
            ["Sonde cylindre", "Champ interieur", "0,43619 %", "PASS"],
        ],
        [
            ("Q1", "Preuves statiques et dynamiques couvrent-elles le domaine ?", "OUI"),
            ("Q2", "Correlations CalculiX et Code_Aster acceptables ?", "OUI"),
            ("Q3", "Raffinements spatiaux/temporels suffisants ?", "OUI"),
            ("Q4", "Limites amortissement, non-linearite, contact et grandes transformations ?", "OUI"),
            ("Q5", "Preuve amortie proportionnelle suffisante ?", "OUI"),
            ("Q6", "Stable pour le domaine borne ?", "OUI"),
            ("Q7", "Sondes interieures hors singularite suffisantes ?", "OUI"),
            ("Q8", "Decision", "STABLE"),
        ],
        [
            "TET10 isotrope, petits deplacements, analyses lineaires.",
            "Rayleigh massique cible 2 % couvert; amortissement non proportionnel exclu.",
            "Pics ponctuels aux blocages, charges et angles rentrants informatifs seulement.",
            "Non-linearite, contact, grandes transformations, dommage et rupture exclus.",
        ],
        [
            "docs/verification/tet10_stable_promotion_owner_review_0_2_1.md",
            "qualification/maturity_evidence_0_2_1/tet10_stable_batch_01/report.md",
            "qualification/vnv/external/code_aster_tet10_static_reference_001/report.md",
            "qualification/stress_observable_policy_0_2_1.json",
        ],
        styles,
    )


def _cover(styles: dict[str, ParagraphStyle]) -> list[object]:
    return [
        Spacer(1, 22 * mm),
        Paragraph("QF_solver", styles["title"]),
        Spacer(1, 5 * mm),
        Paragraph("Pack Owner validation - MITC3, MITC4, TET4 et TET10", styles["subtitle"]),
        Spacer(1, 12 * mm),
        Paragraph("Objet", styles["h1"]),
        Paragraph(
            "Ce dossier regroupe les fiches de promotion des principales familles d'elements. "
            "La decision stable est bornee aux domaines, observables, maillages et exclusions enumeres dans chaque section.",
            styles["body"],
        ),
        Paragraph(
            "Etat au 21/08/2026 : MITC3 classique, MITC4 classique, MITC4 multicouche plan statique, "
            "MITC4 multicouche plan dynamique, TET4 isotrope et TET10 isotrope disposent d'une decision Owner "
            "enregistree avec cible stable. L'orthotrope MITC4 mono-pli possede un dossier stable borne separe. "
            "Les variantes courbes non alignees, J2, contact, grandes deformations et grand modele ne sont pas promues par ce pack.",
            styles["note"],
        ),
        _table([
            ["Famille", "Decision", "Nature de la preuve"],
            ["MITC3 classique", "stable borne", "Code_Aster DKT/TRIA3 + convergence"],
            ["MITC4 classique", "stable borne", "Code_Aster + theorie + invariants"],
            ["MITC4 multicouche", "stable borne", "NAFEMS/Code_Aster + trois layups"],
            ["TET4 / TET10", "stable borne", "Code_Aster/CalculiX + raffinements"],
        ], [47 * mm, 43 * mm, 80 * mm], styles),
        Spacer(1, 10 * mm),
        Paragraph(
            "Regle : une decision Owner n'est pas une certification externe. Les exclusions sont contraignantes et "
            "les diagnostics qui depassent 1 % restent visibles dans les historiques.",
            styles["body"],
        ),
    ]


def _build(path: Path, sections: list[list[object]], styles: dict[str, ParagraphStyle]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    story: list[object] = []
    for index, section in enumerate(sections):
        if index:
            story.append(PageBreak())
        story.extend(section)
    SimpleDocTemplate(
        str(path), pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=13 * mm, bottomMargin=14 * mm, title=path.stem, author="QF_solver",
    ).build(story, onFirstPage=_footer, onLaterPages=_footer)
    return path


def main() -> int:
    styles = _styles()
    sections = [_mitc3(styles), _mitc4_classic(styles), _mitc4_laminate_static(styles), _mitc4_laminate_dynamic(styles), _mitc4_orthotropic(styles), _tet4(styles), _tet10(styles)]
    outputs = [
        _build(OUTPUT_DIR / "qf_solver_owner_review_elements_20260821.pdf", [_cover(styles)] + sections, styles),
        _build(OUTPUT_DIR / "qf_solver_owner_review_mitc3_classic_stable_20260821.pdf", [_cover(styles), sections[0]], styles),
        _build(OUTPUT_DIR / "qf_solver_owner_review_mitc4_classic_stable_20260821.pdf", [_cover(styles), sections[1]], styles),
        _build(OUTPUT_DIR / "qf_solver_owner_review_mitc4_laminate_static_stable_20260821.pdf", [_cover(styles), sections[2]], styles),
        _build(OUTPUT_DIR / "qf_solver_owner_review_mitc4_laminate_dynamic_stable_20260821.pdf", [_cover(styles), sections[3]], styles),
        _build(OUTPUT_DIR / "qf_solver_owner_review_tet4_stable_20260821.pdf", [_cover(styles), sections[4]], styles),
        _build(OUTPUT_DIR / "qf_solver_owner_review_tet10_stable_20260821.pdf", [_cover(styles), sections[5]], styles),
    ]
    for output in outputs:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
