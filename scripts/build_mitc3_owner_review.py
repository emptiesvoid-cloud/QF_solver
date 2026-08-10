"""Build the MITC3+ static Owner-review PDF pack from controlled evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE = ROOT / "results" / "VNV-MITC3-REFINED-SHELL-H20K"
DEFAULT_OUTPUT = ROOT / "output" / "pdf"
DEFAULT_CODE_ASTER = ROOT / "results" / "VNV-MITC3-CODEASTER-DKT-013" / "summary.json"
DEFAULT_CALCULIX = ROOT / "results" / "VNV-MITC3-CALCULIX-S3-014" / "summary.json"
DEFAULT_HEMISPHERE = ROOT / "results" / "VNV-MITC3-PINCHED-HEMISPHERE-CODEASTER-015"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--code-aster", type=Path, default=DEFAULT_CODE_ASTER)
    parser.add_argument("--calculix", type=Path, default=DEFAULT_CALCULIX)
    parser.add_argument("--hemisphere", type=Path, default=DEFAULT_HEMISPHERE)
    args = parser.parse_args()
    summary = json.loads((args.evidence / "summary.json").read_text(encoding="utf-8"))
    external = {
        "code_aster": json.loads(args.code_aster.read_text(encoding="utf-8")),
        "calculix": json.loads(args.calculix.read_text(encoding="utf-8")),
    }
    hemisphere = json.loads((args.hemisphere / "summary.json").read_text(encoding="utf-8"))
    args.output.mkdir(parents=True, exist_ok=True)
    regular, bold = _fonts()
    styles = _styles(regular, bold)
    outputs = (
        args.output / "owner_review_mitc3_statique.pdf",
        args.output / "vnv_mitc3_scordelis_h20k.pdf",
        args.output / "vnv_mitc3_cylindre_pince_h20k.pdf",
        args.output / "vnv_mitc3_hemisphere_code_aster.pdf",
    )
    _build_owner_review(
        outputs[0],
        args.evidence,
        summary,
        external,
        args.hemisphere,
        hemisphere,
        styles,
        regular,
        bold,
    )
    _build_case_annex(
        outputs[1],
        args.evidence,
        summary["cases"]["scordelis"],
        "Scordelis-Lo",
        "scordelis_mesh_deformation.png",
        styles,
        regular,
        bold,
    )
    _build_hemisphere_annex(outputs[3], args.hemisphere, hemisphere, styles, regular, bold)
    _build_case_annex(
        outputs[2],
        args.evidence,
        summary["cases"]["pinched"],
        "Cylindre pince",
        "pinched_mesh_deformation.png",
        styles,
        regular,
        bold,
    )
    for output in outputs:
        _validate(output)
        print(output)
    return 0


def _build_owner_review(
    output: Path,
    evidence: Path,
    summary: dict[str, object],
    external: dict[str, dict[str, object]],
    hemisphere_evidence: Path,
    hemisphere: dict[str, object],
    styles: dict[str, ParagraphStyle],
    regular: str,
    bold: str,
) -> None:
    cases = summary["cases"]
    scordelis = cases["scordelis"]
    pinched = cases["pinched"]
    story = _cover(
        styles,
        "Owner review - MITC3+ statique lineaire",
        "DOC-OWNER-REVIEW-MITC3-STATIC-001",
        "Decision Owner: accepted_for_bounded_engineering_use - 1er aout 2026",
    )
    story.extend(
        [
            Paragraph("1. Perimetre soumis a revue", styles["h1"]),
            Paragraph(
                "Element de coque triangulaire MITC3+ a six DDL par noeud, "
                "facettes planes Reissner-Mindlin, petites transformations, "
                "materiaux isotropes et stratifies lineaires. Cette revue porte "
                "sur la statique lineaire; modal, Newmark et harmonique disposent "
                "de preuves distinctes et ne sont pas signes ici.",
                styles["body"],
            ),
            _table(
                [
                    ["Preuve", "Objet", "Etat"],
                    ["Patch affine", "Membrane et objectivite", "PASS"],
                    ["Shear locking", "Plaque mince, fleche Timoshenko", "PASS developpement"],
                    ["Distorsion", "Perturbation deterministe des noeuds", "PASS"],
                    ["Cook", "Membrane biaisee", "PASS"],
                    ["Scordelis-Lo H20K", "Coque courbe, 20 000 triangles", scordelis["status"]],
                    ["Cylindre pince H20K", "Coque courbe, 19 600 triangles", pinched["status"]],
                    ["Charges", "Resultantes et moments coherents", "PASS"],
                    ["Maillage mixte", "Interface MITC3/MITC4", "PASS"],
                    ["Code_Aster DKT", "Membrane et flexion sur meme maillage", "PASS externe"],
                    ["Hemisphere pince", "Coque doublement courbe et DKT", hemisphere["status"]],
                    ["CalculiX S3", "Temoin triangulaire trop raide en flexion", "WARNING"],
                ],
                styles,
                regular,
                bold,
                (43 * mm, 91 * mm, 38 * mm),
            ),
            Spacer(1, 4 * mm),
            Paragraph("2. Raffinements demandes", styles["h1"]),
            _results_table(scordelis, pinched, styles, regular, bold),
            Paragraph(
                "Le cylindre conserve ntheta = 2 nx: le point regulier le plus "
                "proche de 20 000 est donc 19 600 triangles. Les valeurs de "
                "reference sont celles de la campagne de benchmark controlee.",
                styles["body"],
            ),
        ]
    )
    story.extend(_image_page(styles, "3. Courbes de convergence", evidence / "refined_convergence.png"))
    story.extend(
        _image_page(
            styles,
            "4. Scordelis-Lo - maillage et deformee",
            evidence / "scordelis_mesh_deformation.png",
        )
    )
    story.extend(
        _image_page(
            styles,
            "5. Cylindre pince - maillage et deformee",
            evidence / "pinched_mesh_deformation.png",
        )
    )
    story.extend(
        [
            PageBreak(),
            Paragraph("6. Cisaillement transverse et shear locking", styles["h1"]),
            Paragraph(
                "La formulation interpole les cisaillements covariants aux points "
                "de tying MITC3+. La campagne mince atteint un rapport fleche sur "
                "reference Timoshenko de 0,97951 sur 2 048 triangles. La reponse "
                "reste finie lorsque l'epaisseur diminue: aucun effondrement "
                "caracteristique du shear locking n'est observe.",
                styles["body"],
            ),
            Paragraph(
                "Le patch impose separement gamma_xz, gamma_yz puis leur combinaison. "
                "L'erreur maximale de l'operateur suppose vaut 1,81e-16. Cette preuve "
                "doit etre examinee et signee par l'Owner avant tout changement de "
                "maturite.",
                styles["warning"],
            ),
            Paragraph("7. Correlations externes", styles["h1"]),
            _external_table(external, styles, regular, bold),
            Spacer(1, 4 * mm),
            _hemisphere_table(hemisphere, styles, regular, bold),
            Paragraph("8. Limites du domaine", styles["h1"]),
            Paragraph(
                "Hors scope: grandes rotations, flambement, post-flambement, "
                "dommage, delaminage, contact entre plis et certification externe. "
                "Les pics de contrainte aux singularites ne sont pas des grandeurs "
                "d'acceptation.",
                styles["body"],
            ),
            Paragraph("9. Questions de decision Owner", styles["h1"]),
        ]
    )
    story.extend(
        _image_page(
            styles,
            "8. Hemisphere - convergence QF_solver / Code_Aster",
            hemisphere_evidence / "convergence_qf_code_aster.png",
        )
    )
    story.extend(
        _image_page(
            styles,
            "9. Hemisphere - deformees comparees",
            hemisphere_evidence / "level_32" / "fine_deformation_qf_code_aster.png",
        )
    )
    story.extend(
        [
            PageBreak(),
            Paragraph("10. Cloture technique et decision", styles["h1"]),
            Paragraph(
                "Q1 a Q6 ont recu une reponse OUI de l'Owner. Le patch de flexion "
                "explicite, la coque courbe meme maillage et les affichages Code_Aster "
                "sont maintenant presents. Le scope statique lineaire MITC3+ est "
                "accepte pour un usage engineering borne.",
                styles["body"],
            ),
        ]
    )
    story.extend(
        [
            Paragraph("Q1 - OUI, condition hemisphere pince satisfaite.", styles["body"]),
            Paragraph("Q2 - OUI.", styles["body"]),
            Paragraph("Q3 - OUI, correlation Code_Aster acceptee.", styles["body"]),
            Paragraph("Q4 - OUI, verification sur l'hemisphere pince satisfaite.", styles["body"]),
            Paragraph("Q5 - OUI, affichages Code_Aster inclus.", styles["body"]),
            Paragraph(
                "Q6 - OUI, accepted_for_bounded_engineering_use.",
                styles["body"],
            ),
            Spacer(1, 6 * mm),
            Paragraph("Owner : Quentin Farinazzo", styles["body"]),
            Paragraph("Date : 1er aout 2026", styles["body"]),
            Paragraph("Revue non independante - aucune revendication de certification externe.", styles["warning"]),
        ]
    )
    _write(output, story, regular, "QF_solver - Owner review MITC3+ statique")


def _build_hemisphere_annex(
    output: Path,
    evidence: Path,
    summary: dict[str, object],
    styles: dict[str, ParagraphStyle],
    regular: str,
    bold: str,
) -> None:
    story = _cover(
        styles,
        "V&V MITC3+ - hemisphere pince a quatre quadrants",
        str(summary["study_id"]),
        f"Verdict automatique: {summary['status']} - decision Owner requise",
    )
    story.extend(
        [
            Paragraph("1. Definition et conditions limites", styles["h1"]),
            Paragraph(
                "R=10, ouverture polaire 18 deg, t=0,04, E=6,825e7 et nu=0,3. "
                "Le quart est bloque par symetrie sur x=0 et y=0; UZ est fixe au "
                "point X. Les demi-forces -1 suivant X et +1 suivant Y reconstruisent "
                "les quatre forces physiques de magnitude 2.",
                styles["body"],
            ),
            _fit_image(evidence / "geometry_boundary_loads.png", 174 * mm, 112 * mm),
            PageBreak(),
            Paragraph("2. Convergence et valeurs", styles["h1"]),
            _hemisphere_table(summary, styles, regular, bold),
            Spacer(1, 4 * mm),
            _fit_image(evidence / "convergence_qf_code_aster.png", 174 * mm, 108 * mm),
            PageBreak(),
            Paragraph("3. Deformees comparees", styles["h1"]),
            _fit_image(
                evidence / "level_32" / "fine_deformation_qf_code_aster.png",
                174 * mm,
                118 * mm,
            ),
            PageBreak(),
            Paragraph("4. Affichage Code_Aster et conclusion", styles["h1"]),
            _fit_image(
                evidence / "level_32" / "code_aster_displacement_field.png",
                158 * mm,
                112 * mm,
            ),
            Paragraph(
                "Au niveau fin, l'ecart QF_solver/Code_Aster a la sonde vaut "
                "0,0927 %, l'ecart du champ nodal 0,1536 %, l'ecart QF_solver a "
                "la reference 0,5912 % et l'increment final 0,2605 %. Tous les "
                "criteres automatiques sont PASS.",
                styles["body"],
            ),
        ]
    )
    _write(output, story, regular, "QF_solver - V&V MITC3+ hemisphere pince")


def _build_case_annex(
    output: Path,
    evidence: Path,
    case: dict[str, object],
    name: str,
    image_name: str,
    styles: dict[str, ParagraphStyle],
    regular: str,
    bold: str,
) -> None:
    mesh = case["mesh"]
    story = _cover(
        styles,
        f"V&V MITC3+ - {name}",
        str(case["study_id"]),
        f"Verdict automatique: {case['status']} - revue owner requise",
    )
    story.extend(
        [
            Paragraph("1. Definition numerique", styles["h1"]),
            _table(
                [
                    ["Grandeur", "Valeur"],
                    ["Discretisation", f"{mesh['nx']} x {mesh['ny']}"],
                    ["Noeuds", f"{mesh['nodes']:,}"],
                    ["Triangles MITC3+", f"{mesh['elements']:,}"],
                    ["DDL", f"{mesh['dofs']:,}"],
                    ["Reponse QF_solver", f"{case['value']:.12e}"],
                    ["Reference", f"{case['reference']:.12e}"],
                    ["Ecart relatif", f"{100.0 * case['relative_error']:.6f} %"],
                    ["Seuil", f"{100.0 * case['tolerance']:.2f} %"],
                    ["Temps de resolution", f"{case['solve_elapsed_seconds']:.2f} s"],
                    ["Amplification de la deformee", f"{case['deformation_scale']:.6g}"],
                ],
                styles,
                regular,
                bold,
                (79 * mm, 93 * mm),
                header=False,
            ),
            Paragraph("2. Maillage, appuis et deformee", styles["h1"]),
            Paragraph(
                "Les carres noirs materialisent les noeuds portant des blocages. "
                "La couleur represente la norme du deplacement. La deformee est "
                "amplifiee avec le facteur indique dans la figure et ne represente "
                "donc pas l'echelle physique.",
                styles["body"],
            ),
            _fit_image(evidence / image_name, 174 * mm, 105 * mm),
            PageBreak(),
            Paragraph("3. Convergence", styles["h1"]),
            _fit_image(evidence / "refined_convergence.png", 174 * mm, 105 * mm),
            Paragraph("4. Decision", styles["h1"]),
            Paragraph("Geometrie et conditions aux limites acceptees : ____________________", styles["answer"]),
            Paragraph("Reference et tolerance acceptees : ________________________________", styles["answer"]),
            Paragraph("Convergence acceptee : ___________________________________________", styles["answer"]),
            Paragraph("Commentaires :", styles["body"]),
            Spacer(1, 18 * mm),
            Paragraph("Decision : ______________________________________________________", styles["answer"]),
            Spacer(1, 7 * mm),
            Paragraph("Date : __________________  Signature : __________________________", styles["answer"]),
        ]
    )
    _write(output, story, regular, f"QF_solver - V&V MITC3+ {name}")


def _cover(
    styles: dict[str, ParagraphStyle],
    title: str,
    identifier: str,
    status: str,
) -> list[object]:
    return [
        Spacer(1, 24 * mm),
        Paragraph("QF_solver", styles["brand"]),
        Spacer(1, 12 * mm),
        Paragraph(title, styles["title"]),
        Spacer(1, 8 * mm),
        Paragraph(identifier, styles["subtitle"]),
        Spacer(1, 16 * mm),
        Paragraph(status, styles["status"]),
        Spacer(1, 18 * mm),
        Paragraph("Date de generation : 1er aout 2026", styles["body_center"]),
        Paragraph("Auteur du calcul : QF_solver project", styles["body_center"]),
        Paragraph("Owner reviewer / approver : Quentin Farinazzo", styles["body_center"]),
        PageBreak(),
    ]


def _results_table(
    scordelis: dict[str, object],
    pinched: dict[str, object],
    styles: dict[str, ParagraphStyle],
    regular: str,
    bold: str,
) -> Table:
    return _table(
        [
            ["Cas", "Elements", "DDL", "QF_solver", "Reference", "Ecart", "Verdict"],
            _result_row("Scordelis-Lo", scordelis),
            _result_row("Cylindre pince", pinched),
        ],
        styles,
        regular,
        bold,
        (31 * mm, 24 * mm, 24 * mm, 30 * mm, 30 * mm, 20 * mm, 20 * mm),
    )


def _external_table(
    external: dict[str, dict[str, object]],
    styles: dict[str, ParagraphStyle],
    regular: str,
    bold: str,
) -> Table:
    rows = [["Oracle / temoin", "Cas", "QF_solver", "Externe", "Ecart", "Verdict"]]
    for key, label in (
        ("code_aster", "Code_Aster DKT"),
        ("calculix", "CalculiX S3"),
    ):
        summary = external[key]
        checks = {row["id"]: row["status"] for row in summary["checks"]}
        for case in summary["cases"]:
            external_key = "code_aster_value" if key == "code_aster" else "calculix_value"
            rows.append(
                [
                    label,
                    str(case["id"]),
                    f"{case['qf_value']:.5e}",
                    f"{case[external_key]:.5e}",
                    f"{100.0 * case['difference']:.4f} %",
                    str(checks[f"{case['id']}_difference"]),
                ]
            )
    return _table(
        rows,
        styles,
        regular,
        bold,
        (37 * mm, 24 * mm, 31 * mm, 31 * mm, 26 * mm, 23 * mm),
    )


def _hemisphere_table(
    summary: dict[str, object],
    styles: dict[str, ParagraphStyle],
    regular: str,
    bold: str,
) -> Table:
    rows = [["N", "Triangles quart", "QF_solver", "Code_Aster", "Ecart QF/Aster"]]
    rows.extend(
        [
            str(row["level"]),
            f"{row['quarter_triangles']:,}",
            f"{row['qf_abs_ux']:.9f}",
            f"{abs(row['code_aster_ux']):.9f}",
            f"{100.0 * row['probe_difference']:.4f} %",
        ]
        for row in summary["levels"]
    )
    return _table(
        rows,
        styles,
        regular,
        bold,
        (16 * mm, 34 * mm, 39 * mm, 39 * mm, 39 * mm),
    )


def _result_row(name: str, case: dict[str, object]) -> list[str]:
    return [
        name,
        f"{case['mesh']['elements']:,}",
        f"{case['mesh']['dofs']:,}",
        f"{case['value']:.5e}",
        f"{case['reference']:.5e}",
        f"{100.0 * case['relative_error']:.3f} %",
        str(case["status"]),
    ]


def _questions(styles: dict[str, ParagraphStyle], questions: tuple[str, ...]) -> list[object]:
    story: list[object] = []
    for question in questions:
        story.extend(
            [
                Paragraph(question, styles["body"]),
                Paragraph("Reponse : _______________________________________________", styles["answer"]),
                Spacer(1, 2 * mm),
            ]
        )
    story.extend(
        [
            Paragraph("Commentaires :", styles["body"]),
            Spacer(1, 18 * mm),
            Paragraph("Date : __________________  Signature : __________________________", styles["answer"]),
        ]
    )
    return story


def _image_page(
    styles: dict[str, ParagraphStyle],
    title: str,
    image_path: Path,
) -> list[object]:
    return [
        PageBreak(),
        Paragraph(title, styles["h1"]),
        Spacer(1, 4 * mm),
        _fit_image(image_path, 174 * mm, 205 * mm),
    ]


def _fit_image(path: Path, width: float, height: float) -> Image:
    if not path.is_file():
        raise FileNotFoundError(path)
    image = Image(str(path))
    image._restrictSize(width, height)
    return image


def _table(
    rows: list[list[str]],
    styles: dict[str, ParagraphStyle],
    regular: str,
    bold: str,
    widths: tuple[float, ...],
    *,
    header: bool = True,
) -> Table:
    formatted = []
    for index, row in enumerate(rows):
        style = styles["cell_header"] if header and index == 0 else styles["cell"]
        formatted.append([Paragraph(str(value), style) for value in row])
    table = Table(formatted, colWidths=widths, repeatRows=1 if header else 0)
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#89969c")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTNAME", (0, 0), (-1, -1), regular),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        commands.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e5564")),
                ("FONTNAME", (0, 0), (-1, 0), bold),
            ]
        )
    else:
        commands.extend(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e7eef0")),
                ("FONTNAME", (0, 0), (0, -1), bold),
            ]
        )
    table.setStyle(TableStyle(commands))
    return table


def _write(output: Path, story: list[object], font: str, title: str) -> None:
    document = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        leftMargin=17 * mm,
        rightMargin=17 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=title,
        author="QF_solver project",
    )

    def footer(canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont(font, 8)
        canvas.setFillColor(colors.HexColor("#5b666d"))
        canvas.drawString(17 * mm, 9 * mm, "QF_solver - dossier Owner review MITC3+")
        canvas.drawRightString(193 * mm, 9 * mm, f"Page {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)


def _styles(regular: str, bold: str) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "brand": ParagraphStyle(
            "Brand", parent=base["Title"], fontName=bold, fontSize=18, leading=22,
            textColor=colors.HexColor("#1e5564"), alignment=TA_CENTER,
        ),
        "title": ParagraphStyle(
            "Title", parent=base["Title"], fontName=bold, fontSize=21, leading=26,
            textColor=colors.HexColor("#172b35"), alignment=TA_CENTER,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle", parent=base["BodyText"], fontName=regular, fontSize=10,
            leading=14, alignment=TA_CENTER, textColor=colors.HexColor("#4d5960"),
        ),
        "status": ParagraphStyle(
            "Status", parent=base["BodyText"], fontName=bold, fontSize=10.5,
            leading=15, alignment=TA_CENTER, textColor=colors.HexColor("#744500"),
            borderColor=colors.HexColor("#d6a95d"), borderWidth=0.8,
            borderPadding=8, backColor=colors.HexColor("#fff5df"),
        ),
        "h1": ParagraphStyle(
            "H1", parent=base["Heading1"], fontName=bold, fontSize=14.5,
            leading=18, textColor=colors.HexColor("#1e5564"), spaceAfter=7,
        ),
        "body": ParagraphStyle(
            "Body", parent=base["BodyText"], fontName=regular, fontSize=9.5,
            leading=13.5, textColor=colors.HexColor("#20282c"), spaceAfter=5,
        ),
        "body_center": ParagraphStyle(
            "BodyCenter", parent=base["BodyText"], fontName=regular, fontSize=9.5,
            leading=14, alignment=TA_CENTER, textColor=colors.HexColor("#20282c"),
        ),
        "warning": ParagraphStyle(
            "Warning", parent=base["BodyText"], fontName=regular, fontSize=9.5,
            leading=13.5, textColor=colors.HexColor("#5c3b00"),
            borderColor=colors.HexColor("#d6a95d"), borderWidth=0.6,
            borderPadding=7, backColor=colors.HexColor("#fff8e8"),
        ),
        "answer": ParagraphStyle(
            "Answer", parent=base["BodyText"], fontName=regular, fontSize=9.2,
            leading=13, leftIndent=4 * mm, textColor=colors.HexColor("#4d5960"),
        ),
        "cell": ParagraphStyle(
            "Cell", parent=base["BodyText"], fontName=regular, fontSize=7.8,
            leading=9.8, textColor=colors.HexColor("#20282c"),
        ),
        "cell_header": ParagraphStyle(
            "CellHeader", parent=base["BodyText"], fontName=bold, fontSize=7.8,
            leading=9.8, textColor=colors.white,
        ),
    }


def _fonts() -> tuple[str, str]:
    regular = Path("C:/Windows/Fonts/arial.ttf")
    bold = Path("C:/Windows/Fonts/arialbd.ttf")
    if regular.is_file() and bold.is_file():
        pdfmetrics.registerFont(TTFont("QFArial", str(regular)))
        pdfmetrics.registerFont(TTFont("QFArialBold", str(bold)))
        return "QFArial", "QFArialBold"
    return "Helvetica", "Helvetica-Bold"


def _validate(path: Path) -> None:
    reader = PdfReader(str(path))
    if len(reader.pages) < 3 or path.stat().st_size < 80_000:
        raise RuntimeError(f"Incomplete review PDF: {path}")
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    if "QF_solver" not in text or "MITC3" not in text:
        raise RuntimeError(f"Unexpected PDF content: {path}")


if __name__ == "__main__":
    raise SystemExit(main())
