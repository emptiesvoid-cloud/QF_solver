"""Build the self-contained TET10 linear mechanical review PDF."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from PIL import Image as PilImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "assets" / "reviews"
DEFAULT_OUTPUT = ROOT / "output" / "pdf" / "revue_mecanique_tet10_lineaire.pdf"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    build_review(output)
    published = ASSETS / output.name
    published.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(output, published)
    print(f"PDF: {output}")
    print(f"Published PDF: {published}")
    return 0


def build_review(output: Path) -> None:
    regular, bold = _fonts()
    styles = _styles(regular, bold)
    document = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=18 * mm,
        bottomMargin=17 * mm,
        title="QF_solver - Revue mecanique TET10 lineaire",
        author="QF_solver project",
    )
    story = _cover(styles)
    story.extend(_scope(styles))
    story.extend(_models(styles, regular, bold))
    story.extend(_evidence(styles, regular, bold))
    story.extend(_review(styles, regular, bold))
    document.build(
        story,
        onFirstPage=lambda canvas, doc: _page(canvas, doc, regular, first=True),
        onLaterPages=lambda canvas, doc: _page(canvas, doc, regular, first=False),
    )
    if output.stat().st_size < 300_000 or not output.read_bytes().startswith(b"%PDF"):
        raise RuntimeError("The generated TET10 review PDF is missing or unexpectedly small.")


def _cover(styles: dict[str, ParagraphStyle]) -> list[object]:
    return [
        Spacer(1, 20 * mm),
        Paragraph("QF_solver", styles["brand"]),
        Spacer(1, 5 * mm),
        Paragraph("Revue mecanique TET10 lineaire", styles["title"]),
        Spacer(1, 9 * mm),
        _status_box(styles),
        Spacer(1, 12 * mm),
        Paragraph(
            "Dossier de verification en petites deformations: geometrie courbe, "
            "quadrature, convergence structurelle, masse coherente, modal, charges "
            "quadratiques, correlation CalculiX et quasi-incompressibilite.",
            styles["lead"],
        ),
        Spacer(1, 14 * mm),
        _metadata_table(styles),
        Spacer(1, 14 * mm),
        Paragraph(
            "Decision du 18 juillet 2026 : accepted_with_recommendations. "
            "Cette auto-revue signee par Quentin Farinazzo ne constitue ni une "
            "certification ni une revue independante.",
            styles["warning"],
        ),
        PageBreak(),
    ]


def _scope(styles: dict[str, ParagraphStyle]) -> list[object]:
    return [
        Paragraph("1. Objet et domaine propose", styles["h1"]),
        Paragraph(
            "Le perimetre propose couvre le TET10 isoparametrique, l'elasticite "
            "lineaire isotrope, les petits deplacements, les geometries droites ou "
            "courbes admissibles, la statique, la masse coherente et le modal lineaire.",
            styles["body"],
        ),
        _bullet("Hammer-4 pour les elements geometriquement droits.", styles),
        _bullet("Duffy-64 positive pour les geometries courbes admissibles.", styles),
        _bullet("Charges coherentes de volume et de face quadratique T6.", styles),
        _bullet("Recuperation nodale interpretee hors singularites.", styles),
        Spacer(1, 3 * mm),
        Paragraph("Exclusions maintenues", styles["h2"]),
        _bullet("Incompressibilite exacte et formulation mixte deplacement-pression.", styles),
        _bullet("Plasticite TET10 courbe et grandes transformations TET10.", styles),
        _bullet("Usage industriel autonome et revendication de certification.", styles),
        Spacer(1, 5 * mm),
    ]


def _models(
    styles: dict[str, ParagraphStyle],
    regular: str,
    bold: str,
) -> list[object]:
    rows = [
        ["ID", "Modele", "Maillages", "Conditions", "Oracle"],
        ["011", "TET10 isole droit/courbe/distordu", "1 element par cas", "Champ affine et modes rigides", "Duffy ordre 8"],
        ["012-T", "Prisme 2 x 1 x 0,5 m", "78/107/172/215 TET4 et TET10", "Symetries; traction 10 MPa", "Hooke"],
        ["012-B", "Porte-a-faux 8 x 1 x 1 m", "163/211/272/370 TET4 et TET10", "Pied fixe; tz=-1000 Pa", "Timoshenko"],
        ["012-R, 014", "Arbre L=3 m, R=0,5 m", "151/272/531/1063 TET4 et TET10", "Pied fixe; T=1000 N.m", "Saint-Venant; C3D10"],
        ["013-A", "TET10 et face T6 courbes", "1 element", "p=2 Pa; champ affine; rho=7800", "Quadrature haute precision"],
        ["013-M", "Porte-a-faux modal 8 x 1 x 1 m", "370 TET10; 841 noeuds; 2523 DDL", "Pied fixe; vibration libre", "Euler-Bernoulli"],
        ["015", "Porte-a-faux quasi-incompressible", "163/260/370 elements par famille", "nu=0,30 a 0,499; tz=-1000 Pa", "Timoshenko; TET4 temoin"],
    ]
    table = Table(
        [[Paragraph(str(cell), styles["cell"]) for cell in row] for row in rows],
        colWidths=[18 * mm, 39 * mm, 40 * mm, 45 * mm, 30 * mm],
        repeatRows=1,
    )
    table.setStyle(_table_style(regular, bold, font_size=7.0))
    return [
        Paragraph("2. Modeles reellement calcules", styles["h1"]),
        Paragraph(
            "Les maillages structures sont generes de maniere deterministe avec Gmsh. "
            "Les TET4 servent de temoins de convergence ou de verrouillage; la preuve "
            "du TET10 utilise les memes tailles nominales et nombres d'elements.",
            styles["body"],
        ),
        table,
        Spacer(1, 4 * mm),
        PageBreak(),
    ]


def _evidence(
    styles: dict[str, ParagraphStyle],
    regular: str,
    bold: str,
) -> list[object]:
    geometry = _load("tet10_geometry_quadrature")
    structural = _load("tet10_structural_convergence")
    mass = _load("tet10_mass_modal_loads")
    external = _load("external/calculix_tet10")
    incompressible = _load("tet10_near_incompressible")
    story: list[object] = [Paragraph("3. Synthese des preuves", styles["h1"])]
    story.append(_summary_table(geometry, structural, mass, external, incompressible, styles, regular, bold))
    story.extend(
        _study_block(
            "3.1 Jacobien et quadrature",
            "La regle automatique utilise 4 points sur l'element droit et 64 points "
            "sur l'element courbe. L'erreur matricielle courbe vaut 7,51e-7 face a "
            "Duffy ordre 8; un Jacobien echantillonne non positif est refuse.",
            "tet10_quadrature_convergence.png",
            styles,
        )
    )
    story.extend(
        _study_block(
            "3.2 Convergence en traction, flexion et torsion",
            "Le patch de traction est exact au bruit machine. Le TET10 fin atteint "
            "1,179 % d'erreur en flexion, 0,00250 % sur la rotation de torsion et "
            "0,991 % sur la contrainte de torsion.",
            "tet10_structural_convergence.png",
            styles,
        )
    )
    story.extend(_two_images("bending_tet10_deformation.png", "torsion_tet10_deformation.png", styles))
    story.extend(
        _study_block(
            "3.3 Masse coherente et modal",
            "La masse courbe est verifiee a 3,57e-16. La premiere paire modale "
            "12,7961/12,7965 Hz differe de 0,434 % au maximum de la reference "
            "Euler-Bernoulli 12,8519 Hz.",
            "tet10_modal_mode1.png",
            styles,
        )
    )
    story.extend(
        _study_block(
            "3.4 Correlation externe CalculiX",
            "Sur 1063 C3D10 et 1992 noeuds strictement identiques, l'ecart relatif "
            "du champ complet vaut 6,84e-5 et celui de la rotation terminale 6,45e-5.",
            "calculix_c3d10_deformation.png",
            styles,
        )
    )
    story.extend(
        _study_block(
            "3.5 Quasi-incompressibilite",
            "A nu=0,499, le TET10 conserve 94,83 % de la compliance de Timoshenko, "
            "contre 8,48 % pour le TET4 temoin. Le resultat est favorable mais ne "
            "qualifie pas nu=0,5.",
            "tet10_near_incompressible.png",
            styles,
        )
    )
    story.extend(_single_image("tet10_nu0499_deformation.png", "Deformee TET10 a nu=0,499", styles))
    return story


def _review(
    styles: dict[str, ParagraphStyle],
    regular: str,
    bold: str,
) -> list[object]:
    checklist = [
        "Ordre nodal, mapping isoparametrique et controle des Jacobiennes.",
        "Hammer-4 sur elements droits et Duffy-64 sur geometries courbes admissibles.",
        "Convergence en traction, flexion et torsion dans le domaine documente.",
        "Masse coherente, modal lineaire et charges de face T6.",
        "Correlation CalculiX C3D10 sur maillage identique.",
        "Caracterisation jusqu'a nu=0,499 avec exclusion de nu=0,5.",
        "Limites de post-traitement et statut experimental pour l'usage autonome.",
    ]
    rows = [["Decision", "Point examine"]] + [["[x]", item] for item in checklist]
    table = Table(
        [[Paragraph(str(cell), styles["cell"]) for cell in row] for row in rows],
        colWidths=[22 * mm, 150 * mm],
        repeatRows=1,
    )
    table.setStyle(_table_style(regular, bold, font_size=8.3))
    return [
        PageBreak(),
        Paragraph("4. Checklist de Owner review", styles["h1"]),
        table,
        Spacer(1, 7 * mm),
        Paragraph("Recommandation avant acceptation totale", styles["h2"]),
        Paragraph(
            "En toute fin du developpement, executer une campagne beaucoup plus "
            "complete que les cas elementaires actuels: pieces et assemblages "
            "complexes, maillages importants, chargements combines, concentrations "
            "de contraintes et correlations independantes avec plusieurs codes, "
            "notamment Conastin, CalculiX et Code_Aster. La designation et la version "
            "de Conastin seront precisees avant cette campagne finale.",
            styles["warning"],
        ),
        Paragraph(
            "REC-TET10-001 ne bloque pas l'acceptation interne actuelle. Elle bloque "
            "l'acceptation totale ou la qualification externe tant qu'elle n'est pas "
            "executee et revue.",
            styles["body"],
        ),
        Paragraph("Decision", styles["h2"]),
        Paragraph("[x] accepted_with_recommendations    [ ] rejected", styles["body"]),
        Spacer(1, 8 * mm),
        Paragraph("Validateur et signataire : Quentin Farinazzo", styles["body"]),
        Paragraph("Date : 18 juillet 2026", styles["body"]),
        Paragraph(
            "Signature : declaration electronique self_review - Quentin Farinazzo - 2026-07-18",
            styles["body"],
        ),
        Spacer(1, 8 * mm),
        Paragraph("5. Reproductibilite", styles["h1"]),
        Paragraph(
            "Commandes principales : run_tet10_geometry_quadrature_vnv.py, "
            "run_tet10_structural_convergence_vnv.py, run_tet10_mass_modal_loads_vnv.py, "
            "run_calculix_tet10_vnv.py et run_tet10_near_incompressible_vnv.py.",
            styles["body"],
        ),
        Paragraph(
            "Les resultats controles et manifestes SHA-256 sont ranges sous "
            "qualification/vnv/. Le registre de revue machine-readable signe est "
            "qualification/reviews/tet10_linear_2026-07-18.json.",
            styles["body"],
        ),
    ]


def _status_box(styles: dict[str, ParagraphStyle]) -> Table:
    table = Table(
        [[Paragraph("DECISION", styles["box_head"]), Paragraph("ACCEPTED WITH RECOMMENDATIONS", styles["box_value"])]],
        colWidths=[55 * mm, 105 * mm],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#123b4a")),
                ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#d8eee8")),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#123b4a")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def _metadata_table(styles: dict[str, ParagraphStyle]) -> Table:
    rows = [
        ["Document", "DOC-REV-TET10-LIN-001"],
        ["Version applicable", "QF_solver 0.2.0"],
        ["Scope", "tet10-linear-static"],
        ["Mode de revue", "self_review - non independante"],
        ["Decision", "accepted_with_recommendations - 2026-07-18"],
    ]
    table = Table(
        [[Paragraph(cell, styles["cell"]) for cell in row] for row in rows],
        colWidths=[50 * mm, 110 * mm],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e7eff1")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#aabcc1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _summary_table(
    geometry: dict[str, object],
    structural: dict[str, object],
    mass: dict[str, object],
    external: dict[str, object],
    incompressible: dict[str, object],
    styles: dict[str, ParagraphStyle],
    regular: str,
    bold: str,
) -> Table:
    rows = [
        ["Etude", "Preuve", "Indicateur", "Verdict"],
        [geometry["study_id"], "Jacobien et quadrature", "Erreur courbe 7,51e-7", "PASS"],
        [structural["study_id"], "Convergence h", "Flexion 1,179 %", "PASS"],
        [mass["study_id"], "Masse/modal/charges", "Frequence 0,434 %", "PASS"],
        [external["study_id"], "CalculiX meme maillage", "Champ 6,84e-5", "PASS"],
        [incompressible["study_id"], "Sensibilite a nu", "Compliance 94,83 %", "PASS caract."],
    ]
    table = Table(
        [[Paragraph(str(cell), styles["cell"]) for cell in row] for row in rows],
        colWidths=[51 * mm, 46 * mm, 43 * mm, 32 * mm],
        repeatRows=1,
    )
    table.setStyle(_table_style(regular, bold, font_size=7.5))
    return table


def _study_block(
    title: str,
    text: str,
    image_name: str,
    styles: dict[str, ParagraphStyle],
) -> list[object]:
    return [
        PageBreak(),
        Paragraph(title, styles["h1"]),
        Paragraph(text, styles["body"]),
        Spacer(1, 3 * mm),
        _image(ASSETS / image_name, 174 * mm, 205 * mm),
        Paragraph(f"Figure integree : {image_name}", styles["caption"]),
    ]


def _single_image(name: str, caption: str, styles: dict[str, ParagraphStyle]) -> list[object]:
    return [
        PageBreak(),
        Paragraph(caption, styles["h2"]),
        _image(ASSETS / name, 174 * mm, 210 * mm),
        Paragraph(f"Figure integree : {name}", styles["caption"]),
    ]


def _two_images(first: str, second: str, styles: dict[str, ParagraphStyle]) -> list[object]:
    return [
        PageBreak(),
        Paragraph("Deformees structurelles", styles["h2"]),
        KeepTogether([_image(ASSETS / first, 174 * mm, 92 * mm), Paragraph("Flexion TET10", styles["caption"])]),
        Spacer(1, 4 * mm),
        KeepTogether([_image(ASSETS / second, 174 * mm, 92 * mm), Paragraph("Torsion TET10", styles["caption"])]),
    ]


def _image(path: Path, maximum_width: float, maximum_height: float) -> Image:
    if not path.is_file():
        raise FileNotFoundError(f"Missing review image: {path}")
    with PilImage.open(path) as image:
        width, height = image.size
    scale = min(maximum_width / width, maximum_height / height)
    return Image(str(path), width=width * scale, height=height * scale)


def _bullet(text: str, styles: dict[str, ParagraphStyle]) -> Paragraph:
    return Paragraph(f"- {text}", styles["bullet"])


def _load(relative: str) -> dict[str, object]:
    path = ROOT / "qualification" / "vnv" / relative / "reference" / "summary.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _fonts() -> tuple[str, str]:
    regular = Path(r"C:\Windows\Fonts\arial.ttf")
    bold = Path(r"C:\Windows\Fonts\arialbd.ttf")
    if regular.is_file() and bold.is_file():
        pdfmetrics.registerFont(TTFont("QFArial", regular))
        pdfmetrics.registerFont(TTFont("QFArialBold", bold))
        return "QFArial", "QFArialBold"
    return "Helvetica", "Helvetica-Bold"


def _styles(regular: str, bold: str) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "brand": ParagraphStyle("brand", parent=base["Title"], fontName=bold, fontSize=15, textColor=colors.HexColor("#0b7285"), alignment=TA_CENTER),
        "title": ParagraphStyle("title", parent=base["Title"], fontName=bold, fontSize=25, leading=29, textColor=colors.HexColor("#123b4a"), alignment=TA_CENTER),
        "lead": ParagraphStyle("lead", parent=base["BodyText"], fontName=regular, fontSize=11, leading=16, alignment=TA_CENTER, textColor=colors.HexColor("#34484f")),
        "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName=bold, fontSize=16, leading=20, textColor=colors.HexColor("#0b5668"), spaceBefore=5 * mm, spaceAfter=3 * mm),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName=bold, fontSize=12, leading=15, textColor=colors.HexColor("#244c56"), spaceBefore=4 * mm, spaceAfter=2 * mm),
        "body": ParagraphStyle("body", parent=base["BodyText"], fontName=regular, fontSize=9.5, leading=13.5, textColor=colors.HexColor("#172126"), spaceAfter=2.5 * mm),
        "bullet": ParagraphStyle("bullet", parent=base["BodyText"], fontName=regular, fontSize=9.2, leading=12.5, leftIndent=5 * mm, firstLineIndent=-3 * mm, spaceAfter=1.5 * mm),
        "cell": ParagraphStyle("cell", parent=base["BodyText"], fontName=regular, fontSize=7.5, leading=9.2, textColor=colors.HexColor("#172126")),
        "caption": ParagraphStyle("caption", parent=base["BodyText"], fontName=regular, fontSize=7.5, leading=9, alignment=TA_CENTER, textColor=colors.HexColor("#51656c"), spaceBefore=1.5 * mm),
        "warning": ParagraphStyle("warning", parent=base["BodyText"], fontName=bold, fontSize=9.5, leading=13, textColor=colors.HexColor("#8a3b12"), backColor=colors.HexColor("#fff1df"), borderPadding=8),
        "box_head": ParagraphStyle("box_head", parent=base["BodyText"], fontName=bold, fontSize=8.5, textColor=colors.white),
        "box_value": ParagraphStyle("box_value", parent=base["BodyText"], fontName=bold, fontSize=10.5, textColor=colors.HexColor("#135f49"), alignment=TA_LEFT),
    }


def _table_style(regular: str, bold: str, *, font_size: float) -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dcecef")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#123b4a")),
            ("FONTNAME", (0, 0), (-1, 0), bold),
            ("FONTNAME", (0, 1), (-1, -1), regular),
            ("FONTSIZE", (0, 0), (-1, -1), font_size),
            ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#9eb2b7")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f8f9")]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
    )


def _page(canvas: object, document: object, font: str, *, first: bool) -> None:
    canvas.saveState()
    canvas.setFont(font, 7.5)
    canvas.setFillColor(colors.HexColor("#607078"))
    if not first:
        canvas.drawString(16 * mm, A4[1] - 10 * mm, "QF_solver - Revue mecanique TET10 lineaire")
    canvas.drawRightString(A4[0] - 16 * mm, 9 * mm, f"Page {document.page}")
    canvas.restoreState()


if __name__ == "__main__":
    raise SystemExit(main())
