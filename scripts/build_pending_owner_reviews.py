"""Build portable PDF packs for the two controlled Owner reviews."""

from __future__ import annotations

import shutil
from pathlib import Path

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
OUTPUT = ROOT / "output" / "pdf"
PUBLISHED = ROOT / "docs" / "assets" / "reviews"


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    PUBLISHED.mkdir(parents=True, exist_ok=True)
    regular, bold = _fonts()
    styles = _styles(regular, bold)
    contact = OUTPUT / "owner_review_contact_v1.pdf"
    singular = OUTPUT / "owner_review_contraintes_singulieres.pdf"
    _build_contact(contact, styles, regular, bold)
    _build_singular(singular, styles, regular, bold)
    for path in (contact, singular):
        shutil.copy2(path, PUBLISHED / path.name)
        _validate_pdf(path)
        print(path)
    return 0


def _build_contact(
    output: Path,
    styles: dict[str, ParagraphStyle],
    regular: str,
    bold: str,
) -> None:
    story = _cover(
        styles,
        "Owner review - Contact V1 borne",
        "OWNER-REVIEW-CONTACT-V1-2026-07-29",
        "Decision enregistree: accepted_for_bounded_engineering_use",
    )
    story.extend(
        [
            Paragraph("1. Perimetre soumis a decision", styles["h1"]),
            Paragraph(
                "Contact unilateral sans frottement, analyse statique lineaire, "
                "petites transformations, active-set noeud-triangle et surface "
                "maitre triangulee bornee. Le mode updated relocalise une facette "
                "sur de petites translations. Le statut reste experimental.",
                styles["body"],
            ),
            _table(
                [
                    ["Capacite", "Etat de preuve", "Decision attendue"],
                    ["Ouverture / fermeture", "Analytique et Code_Aster: PASS", "Accepter le comportement unilateral"],
                    ["Face TET4 deformable", "Transfert barycentrique: PASS", "Accepter le domaine borne"],
                    ["Surface pliee", "Recherche actualisee: PASS", "Accepter petites translations"],
                    ["Grand glissement", "Non demontre", "Maintenir hors scope"],
                    ["Frottement general", "Scope distinct experimental", "Maintenir hors decision"],
                ],
                styles,
                regular,
                bold,
                (48 * mm, 62 * mm, 62 * mm),
            ),
            Spacer(1, 5 * mm),
            Paragraph("2. Resultats essentiels", styles["h1"]),
            _table(
                [
                    ["Etude", "Resultat", "Verdict"],
                    ["TET4 structurel", "Convergence de la reaction normale", "PASS interne"],
                    ["LIAISON_UNIL", "Compression et separation identiques", "PASS externe"],
                    ["Face maitre TET4", "Ecart deplacement <= 1,39e-17", "PASS externe"],
                    ["Normale inclinee", "Ecart <= 1,11e-16", "PASS externe"],
                    ["Recherche sur pli", "Ecart moyen 0,1157 %, seuil 1 %", "PASS externe"],
                    ["Trois modeles ajoutes", "Coin, rampe et bloc TET4 deux esclaves", "PASS interne"],
                    ["Courbes 768 TET4", "Ecart QF/Aster 4,3400 %", "PASS externe"],
                    ["Confirmation 9 984 TET4", "Ecart QF/Aster 3,3029e-12 %", "PASS externe"],
                ],
                styles,
                regular,
                bold,
                (61 * mm, 76 * mm, 35 * mm),
            ),
        ]
    )
    story.extend(
        _figure_page(
            styles,
            "3. Convergence et deformee du contact structurel",
            ROOT / "results" / "VNV-CONTACT-V1-001" / "structural" / "contact_structural_convergence.png",
            ROOT / "results" / "VNV-CONTACT-V1-001" / "structural" / "contact_structural_deformation.png",
        )
    )
    story.extend(
        _figure_page(
            styles,
            "4. Recherche de facette et correlation Code_Aster",
            ROOT / "results" / "VNV-CONTACT-V1-001" / "master_surface" / "master_surface_folded_updated_switch.png",
            ROOT
            / "results"
            / "VNV-CONTACT-CODEASTER-LIAISON-UNIL-001"
            / "code_aster_contact_comparison.png",
        )
    )
    story.extend(
        _figure_page(
            styles,
            "5. Preuves complementaires demandees",
            ROOT / "docs" / "assets" / "reviews" / "contact_additional_models.png",
        )
    )
    story.extend(
        _figure_page(
            styles,
            "6. Confirmation QF_solver / Code_Aster sur 9 984 TET4",
            ROOT
            / "results"
            / "VNV-CONTACT-CODEASTER-ADDITIONAL-H10K-010"
            / "contact_code_aster_curves.png",
        )
    )
    story.extend(
        [
            PageBreak(),
            Paragraph("7. Decision Owner review enregistree", styles["h1"]),
            _table(
                [
                    ["Question", "Reponse"],
                    ["Q1 - preuves suffisantes", "OUI"],
                    ["Q2 - domaine et limites acceptes", "OUI"],
                    ["Q3 - statut apres tests", "engineering_ready_bounded"],
                    ["Q4 - decision", "accepted_for_bounded_engineering_use"],
                ],
                styles,
                regular,
                bold,
                (105 * mm, 67 * mm),
            ),
            Spacer(1, 8 * mm),
            Paragraph("Condition quantitative satisfaite", styles["h2"]),
            Paragraph(
                "L'ecart QF_solver/Code_Aster passe sous 5 % sur 768 TET4 "
                "(4,3400 %), puis est confirme sur 9 984 TET4 "
                "(3,3029e-12 %).",
                styles["body"],
            ),
            Paragraph("Recommandations maintenues", styles["h2"]),
            Paragraph(
                "- Raffiner explicitement les transitions de contact et verifier "
                "la sensibilite au maillage pour toute nouvelle topologie.",
                styles["body"],
            ),
            Paragraph(
                "- Ne pas etendre cette decision au frottement, grand glissement, "
                "impact ou usure.",
                styles["body"],
            ),
            Spacer(1, 14 * mm),
            Paragraph(
                "Quentin Farinazzo - Owner review interne - 29 juillet 2026",
                styles["answer"],
            ),
        ]
    )
    _write_pdf(output, story, regular, "QF_solver - Owner review contact V1")


def _build_singular(
    output: Path,
    styles: dict[str, ParagraphStyle],
    regular: str,
    bold: str,
) -> None:
    story = _cover(
        styles,
        "Owner review - Contraintes orthotropes proches des singularites",
        "REV-ORTHOTROPIC-SINGULAR-STRESS-2026-07-29",
        "Decision enregistree: accepted_with_recommendations",
    )
    story.extend(
        [
            Paragraph("1. Methode soumise a decision", styles["h1"]),
            Paragraph(
                "La grandeur acceptee est S11 dans les axes materiau, mesuree sur "
                "des chemins a distances physiques fixes et sur des moyennes de "
                "bande. Un pic ponctuel au coin rentrant n'entre jamais dans le "
                "verdict. Huit maillages sont utilises pour chaque geometrie.",
                styles["body"],
            ),
            _table(
                [
                    ["Cas", "Maillage fin", "Incr. chemin", "Incr. bande", "Oracle Code_Aster"],
                    ["Trou de rayon fini", "86 469 TET4", "1,342 %", "0,125 %", "< 6,0e-11 %"],
                    ["Angle rentrant", "237 358 TET4", "1,625 %", "3,420 %", "< 5,4e-9 %"],
                ],
                styles,
                regular,
                bold,
                (43 * mm, 34 * mm, 31 * mm, 31 * mm, 36 * mm),
            ),
            Spacer(1, 5 * mm),
            Paragraph("2. Politique des oracles", styles["h1"]),
            Paragraph(
                "Code_Aster aux points d'integration est l'oracle bloquant et passe "
                "a la precision numerique. CalculiX extrapole ses contraintes aux "
                "noeuds: l'ecart de bande au coin rentrant vaut 6,357 % et reste un "
                "WARNING diagnostique. Son ecart de chemin fin vaut 0,306 %.",
                styles["body"],
            ),
            Paragraph("Preuves complementaires demandees", styles["h2"]),
            _table(
                [
                    ["Nouvelle piece", "TET4 fin", "Incr. chemin", "Incr. bande", "Code_Aster"],
                    ["Encoche arrondie", "55 935", "0,611 %", "0,868 %", "PASS"],
                    ["Deux trous", "54 342", "4,404 %", "0,556 %", "PASS"],
                ],
                styles,
                regular,
                bold,
                (43 * mm, 32 * mm, 34 * mm, 34 * mm, 30 * mm),
            ),
        ]
    )
    story.extend(
        _figure_page(
            styles,
            "3. Convergence des chemins de contrainte",
            ROOT
            / "results"
            / "VNV-ORTHOTROPIC-SINGULAR-STRESS-005-REFINED-H8-LARGE"
            / "stress_paths.png",
        )
    )
    story.extend(
        _figure_page(
            styles,
            "4. Geometries et champs compares",
            ROOT / "docs" / "assets" / "reviews" / "orthotropic_perforated_qf.png",
            ROOT / "docs" / "assets" / "reviews" / "orthotropic_lbracket_code_aster.png",
        )
    )
    story.extend(
        _figure_page(
            styles,
            "5. Deux nouvelles pieces - convergence et champs S11",
            ROOT / "docs" / "assets" / "reviews" / "additional_stress_convergence.png",
            ROOT / "docs" / "assets" / "reviews" / "additional_stress_fields.png",
        )
    )
    story.extend(
        [
            PageBreak(),
            Paragraph("6. Decision Owner review enregistree", styles["h1"]),
            _table(
                [
                    ["Question", "Reponse"],
                    ["Q1 - deux nouvelles pieces", "OUI"],
                    ["Q2 - increments inferieurs a 5 %", "OUI"],
                    ["Q3 - cartes S11 QF_solver/Code_Aster", "OUI"],
                    ["Q4 - lecture hors pics singuliers", "OUI"],
                    ["Q5 - decision", "accepted_with_recommendations"],
                ],
                styles,
                regular,
                bold,
                (105 * mm, 67 * mm),
            ),
            Spacer(1, 8 * mm),
            Paragraph("Recommandations maintenues", styles["h2"]),
            Paragraph(
                "- Ne jamais utiliser le pic singulier comme valeur de dimensionnement.",
                styles["body"],
            ),
            Paragraph(
                "- Conserver visible le WARNING CalculiX de 6,357 %.",
                styles["body"],
            ),
            Paragraph(
                "- S11 ne remplace pas un critere de rupture anisotrope.",
                styles["body"],
            ),
            Spacer(1, 14 * mm),
            Paragraph(
                "Quentin Farinazzo - Owner review interne - 29 juillet 2026",
                styles["answer"],
            ),
        ]
    )
    _write_pdf(output, story, regular, "QF_solver - Revue contraintes singulieres")


def _cover(
    styles: dict[str, ParagraphStyle],
    title: str,
    review_id: str,
    status: str,
) -> list[object]:
    return [
        Spacer(1, 22 * mm),
        Paragraph("QF_solver", styles["brand"]),
        Spacer(1, 6 * mm),
        Paragraph(title, styles["title"]),
        Spacer(1, 10 * mm),
        Paragraph(status, styles["status"]),
        Spacer(1, 14 * mm),
        _table(
            [
                ["Identifiant", review_id],
                ["Version applicable", "0.2.0"],
                ["Proprietaire-validateur", "Quentin Farinazzo"],
                ["Mode", "self_review - non independant"],
                ["Decision / date / signature", "Enregistrees le 29 juillet 2026"],
                ["Certification revendiquee", "Aucune"],
            ],
            styles,
            "QFArial",
            "QFArialBold",
            (55 * mm, 112 * mm),
            header=False,
        ),
        Spacer(1, 12 * mm),
        Paragraph(
            "Ce document presente les preuves, les limites et la decision Owner "
            "review enregistree. Il ne revendique aucune certification.",
            styles["warning"],
        ),
        PageBreak(),
    ]


def _decision_page(
    styles: dict[str, ParagraphStyle],
    questions: list[str],
    recommendations: list[str],
    *,
    section_number: int = 6,
) -> list[object]:
    story: list[object] = [
        PageBreak(),
        Paragraph(f"{section_number}. Decision Owner", styles["h1"]),
    ]
    story.append(Paragraph("Questions a repondre", styles["h2"]))
    for question in questions:
        story.extend([Paragraph(question, styles["body"]), Paragraph("Reponse : ________________________________", styles["answer"])])
    story.append(Paragraph("Recommandations techniques", styles["h2"]))
    for item in recommendations:
        story.append(Paragraph(f"- {item}", styles["body"]))
    story.extend(
        [
            Spacer(1, 8 * mm),
            Paragraph("Commentaires :", styles["body"]),
            Spacer(1, 18 * mm),
            Paragraph("Decision : ______________________________________________", styles["answer"]),
            Spacer(1, 8 * mm),
            Paragraph("Date : ____________________    Signature : ______________________________", styles["answer"]),
        ]
    )
    return story


def _figure_page(
    styles: dict[str, ParagraphStyle],
    title: str,
    *paths: Path,
) -> list[object]:
    story: list[object] = [PageBreak(), Paragraph(title, styles["h1"]), Spacer(1, 3 * mm)]
    available = [path for path in paths if path.is_file()]
    if len(available) != len(paths):
        missing = [str(path) for path in paths if not path.is_file()]
        raise FileNotFoundError(", ".join(missing))
    max_height = 92 * mm if len(paths) > 1 else 190 * mm
    for path in paths:
        image = Image(str(path))
        image._restrictSize(174 * mm, max_height)
        story.extend([image, Spacer(1, 4 * mm)])
    return story


def _table(
    rows: list[list[str]],
    styles: dict[str, ParagraphStyle],
    regular: str,
    bold: str,
    widths: tuple[float, ...],
    *,
    header: bool = True,
) -> Table:
    formatted_rows = []
    for row_index, row in enumerate(rows):
        style = styles["cell_header"] if header and row_index == 0 else styles["cell"]
        formatted_rows.append([Paragraph(str(value), style) for value in row])
    table = Table(
        formatted_rows,
        colWidths=widths,
        repeatRows=1 if header else 0,
    )
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#8a959c")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTNAME", (0, 0), (-1, -1), regular),
        ("FONTSIZE", (0, 0), (-1, -1), 8.3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        commands.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e5564")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
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


def _write_pdf(output: Path, story: list[object], font: str, title: str) -> None:
    document = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        leftMargin=17 * mm,
        rightMargin=17 * mm,
        topMargin=17 * mm,
        bottomMargin=16 * mm,
        title=title,
        author="QF_solver project",
    )

    def page(canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont(font, 8)
        canvas.setFillColor(colors.HexColor("#5b666d"))
        canvas.drawString(17 * mm, 9 * mm, "QF_solver - dossier Owner review")
        canvas.drawRightString(193 * mm, 9 * mm, f"Page {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=page, onLaterPages=page)


def _styles(regular: str, bold: str) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "brand": ParagraphStyle(
            "Brand", parent=base["Title"], fontName=bold, fontSize=17, leading=20,
            textColor=colors.HexColor("#1e5564"), alignment=TA_CENTER,
        ),
        "title": ParagraphStyle(
            "TitleQF", parent=base["Title"], fontName=bold, fontSize=22, leading=27,
            textColor=colors.HexColor("#172b35"), alignment=TA_CENTER,
        ),
        "status": ParagraphStyle(
            "Status", parent=base["BodyText"], fontName=bold, fontSize=11, leading=15,
            textColor=colors.HexColor("#8a4f00"), alignment=TA_CENTER,
            borderColor=colors.HexColor("#d6a95d"), borderWidth=0.8,
            borderPadding=8, backColor=colors.HexColor("#fff5df"),
        ),
        "warning": ParagraphStyle(
            "Warning", parent=base["BodyText"], fontName=regular, fontSize=10,
            leading=14, textColor=colors.HexColor("#5c3b00"),
            borderColor=colors.HexColor("#d6a95d"), borderWidth=0.6,
            borderPadding=8, backColor=colors.HexColor("#fff8e8"),
        ),
        "h1": ParagraphStyle(
            "H1QF", parent=base["Heading1"], fontName=bold, fontSize=15, leading=19,
            textColor=colors.HexColor("#1e5564"), spaceAfter=7,
        ),
        "h2": ParagraphStyle(
            "H2QF", parent=base["Heading2"], fontName=bold, fontSize=11.5, leading=15,
            textColor=colors.HexColor("#263a43"), spaceBefore=7, spaceAfter=5,
        ),
        "body": ParagraphStyle(
            "BodyQF", parent=base["BodyText"], fontName=regular, fontSize=9.6,
            leading=14, textColor=colors.HexColor("#20282c"), spaceAfter=5,
        ),
        "answer": ParagraphStyle(
            "Answer", parent=base["BodyText"], fontName=regular, fontSize=9.3,
            leading=13, textColor=colors.HexColor("#4d5960"), leftIndent=5 * mm,
            spaceAfter=5,
        ),
        "cell": ParagraphStyle(
            "Cell", parent=base["BodyText"], fontName=regular, fontSize=8.3,
            leading=10.5, textColor=colors.HexColor("#20282c"),
        ),
        "cell_header": ParagraphStyle(
            "CellHeader", parent=base["BodyText"], fontName=bold, fontSize=8.3,
            leading=10.5, textColor=colors.white,
        ),
    }


def _fonts() -> tuple[str, str]:
    regular_path = Path("C:/Windows/Fonts/arial.ttf")
    bold_path = Path("C:/Windows/Fonts/arialbd.ttf")
    if regular_path.is_file() and bold_path.is_file():
        pdfmetrics.registerFont(TTFont("QFArial", str(regular_path)))
        pdfmetrics.registerFont(TTFont("QFArialBold", str(bold_path)))
        return "QFArial", "QFArialBold"
    return "Helvetica", "Helvetica-Bold"


def _validate_pdf(path: Path) -> None:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    if len(reader.pages) < 4 or path.stat().st_size < 100_000:
        raise RuntimeError(f"Review PDF is incomplete: {path}")


if __name__ == "__main__":
    raise SystemExit(main())
