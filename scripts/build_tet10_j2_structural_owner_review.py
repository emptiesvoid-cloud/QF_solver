"""Build the Owner-review PDF for the external TET10 J2 benchmark."""

from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
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
RESULTS = ROOT / "results" / "VNV-TET10-J2-CODEASTER-STRUCTURAL-025"
OUTPUT = ROOT / "output" / "pdf" / "tet10_j2_structural_code_aster_owner_review.pdf"


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "QFTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=19,
            leading=23,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#17324d"),
            spaceAfter=8 * mm,
        ),
        "subtitle": ParagraphStyle(
            "QFSubtitle",
            parent=base["Normal"],
            fontSize=10,
            leading=14,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#4b5d6b"),
            spaceAfter=8 * mm,
        ),
        "h1": ParagraphStyle(
            "QFH1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#17324d"),
            spaceBefore=4 * mm,
            spaceAfter=3 * mm,
        ),
        "h2": ParagraphStyle(
            "QFH2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#245b7a"),
            spaceBefore=3 * mm,
            spaceAfter=2 * mm,
        ),
        "body": ParagraphStyle(
            "QFBody",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.4,
            leading=13,
            alignment=TA_LEFT,
            spaceAfter=2.5 * mm,
        ),
        "small": ParagraphStyle(
            "QFSmall",
            parent=base["BodyText"],
            fontSize=7.8,
            leading=10,
            textColor=colors.HexColor("#4b5d6b"),
        ),
        "table": ParagraphStyle(
            "QFTable",
            parent=base["BodyText"],
            fontSize=7.4,
            leading=9,
        ),
        "table_head": ParagraphStyle(
            "QFTableHead",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7.2,
            leading=8.5,
            textColor=colors.white,
        ),
    }


def _p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text, style)


def _table(rows: list[list[str]], styles: dict[str, ParagraphStyle], widths: list[float]) -> Table:
    converted = []
    for row_index, row in enumerate(rows):
        row_style = styles["table_head"] if row_index == 0 else styles["table"]
        converted.append([_p(str(cell), row_style) for cell in row])
    table = Table(converted, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#245b7a")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#a9b7c1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef4f7")]),
            ]
        )
    )
    return table


def _footer(canvas, document) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#a9b7c1"))
    canvas.line(16 * mm, 13 * mm, 194 * mm, 13 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#4b5d6b"))
    canvas.drawString(16 * mm, 8 * mm, "QF_solver - Owner review interne - aucune revendication de certification")
    canvas.drawRightString(194 * mm, 8 * mm, f"Page {document.page}")
    canvas.restoreState()


def build_pdf() -> Path:
    summary = json.loads((RESULTS / "summary.json").read_text(encoding="utf-8"))
    qf_rows = summary["qf_rows"]
    code_aster_rows = summary["code_aster_rows"]
    checks = summary["checks"]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    styles = _styles()
    document = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=15 * mm,
        bottomMargin=18 * mm,
        title="Owner review - Benchmark externe structurel TET10 J2",
        author="QF_solver",
    )
    story = [
        _p("Owner review - benchmark externe structurel TET10 J2", styles["title"]),
        _p(
            "DOC-VNV-TET10-J2-CODEASTER-STRUCTURAL-001 | Revision 0.1 | Version applicable 0.2.0-alpha<br/>"
            "Date de generation : 9 aout 2026 | Decision Owner : a renseigner",
            styles["subtitle"],
        ),
        _p("1. Objet de la revue", styles["h1"]),
        _p(
            "Cette fiche est soumise a la revue Owner de Quentin Farinazzo. Elle presente une correlation "
            "structurelle externe entre QF_solver TET10 et Code_Aster TETRA10 pour une plasticite J2 "
            "isotrope a ecrouissage lineaire. Le resultat est une preuve de developpement delimitee. "
            "Il ne vaut pas qualification generale de la plasticite, ni validation des grandes deformations, "
            "du cyclage ou des structures complexes.",
            styles["body"],
        ),
        _p("Verdict automatise : <b>PASS_EXTERNAL_CORRELATION</b>", styles["body"]),
        _p("Maturite proposee : <b>experimental</b> jusqu'a decision Owner.", styles["body"]),
        _p("2. Modele et hypothèses", styles["h1"]),
        _p(
            "La geometrie est une barre droite homogene de longueur 1,0 m et de section carree 0,2 m x 0,2 m. "
            "Le maillage est commun aux deux solveurs : 341 noeuds et 140 elements TET10/TETRA10. "
            "La face x=0 est encastree sur les trois translations. Une force axiale totale de 18 MN est "
            "repartie sur la face x=1,0 m.",
            styles["body"],
        ),
        _p(
            "Materiau : E = 210 GPa, nu = 0,30, limite d'elasticite = 250 MPa, module d'ecrouissage isotrope "
            "= 50 GPa. Le chemin monotone comporte les facteurs de charge 0,25, 0,50, 0,75, 1,00, 1,10 et 1,20.",
            styles["body"],
        ),
        _p("3. Comparaison des resultats", styles["h1"]),
    ]
    result_table = [["Facteur", "UX QF [m]", "UX Code_Aster [m]", "PEEQ QF", "PEEQ Code_Aster"]]
    for qf_row, code_aster_row in zip(qf_rows, code_aster_rows):
        result_table.append(
            [
                f"{qf_row['load_factor']:.2f}",
                f"{qf_row['tip_ux_m']:.6e}",
                f"{code_aster_row['tip_ux_m']:.6e}",
                f"{qf_row['equivalent_plastic_strain_mean']:.6e}",
                f"{code_aster_row['equivalent_plastic_strain']:.6e}",
            ]
        )
    story += [
        _table(result_table, styles, [18 * mm, 35 * mm, 39 * mm, 34 * mm, 39 * mm]),
        Spacer(1, 4 * mm),
        _p(
            "La PEEQ QF_solver est la moyenne des points d'integration TET10. Elle est comparee a la "
            "valeur moyenne extraite de Code_Aster, et non a un maximum ponctuel. Cette convention evite "
            "de comparer des statistiques spatiales differentes.",
            styles["small"],
        ),
        PageBreak(),
        _p("4. Figures de controle", styles["h1"]),
        _p(
            "Les deux courbes montrent l'accord sur le deplacement axial en bout et sur l'evolution de la "
            "deformation plastique equivalente. La seconde figure permet de verifier visuellement le maillage "
            "initial et la deformation amplifiee du modele QF_solver.",
            styles["body"],
        ),
    ]
    comparison = RESULTS / "comparison.png"
    deformation = RESULTS / "deformation.png"
    story += [
        Image(str(comparison), width=178 * mm, height=90 * mm),
        Spacer(1, 3 * mm),
        Image(str(deformation), width=150 * mm, height=106 * mm),
        PageBreak(),
        _p("5. Criteres d'acceptation numerique", styles["h1"]),
    ]
    checks_table = [["Controle", "Valeur", "Limite", "Statut"]]
    check_labels = {
        "tip_displacement_path_rms": "RMS chemin UX",
        "final_tip_displacement": "Ecart UX final",
        "qf_equivalent_plastic_strain_path": "RMS chemin PEEQ",
        "qf_max_step_residual": "Residu QF maximal",
    }
    for check in checks:
        value = check["value"]
        if "residual" in check["id"]:
            value_text = f"{value:.6e}"
            limit_text = f"{check['limit']:.1e}"
        else:
            value_text = f"{100 * value:.5f} %"
            limit_text = f"{100 * check['limit']:.2f} %"
        checks_table.append([check_labels.get(check["id"], check["id"]), value_text, limit_text, check["status"]])
    story += [
        _table(checks_table, styles, [65 * mm, 38 * mm, 35 * mm, 25 * mm]),
        Spacer(1, 5 * mm),
        _p("Conclusion technique", styles["h2"]),
        _p(
            "Les deplacements sont correles avec un ecart final de 0,03175 %. La deformation plastique "
            "equivalente presente un ecart RMS de 0,55084 %. Le residu QF_solver maximal vaut "
            "7,40079 x 10^-11. Les controles numeriques de cette campagne sont donc satisfaits.",
            styles["body"],
        ),
        _p("6. Limites de la preuve", styles["h1"]),
        _p(
            "La preuve ne couvre pas les inversions cycliques, la fatigue, les grandes deformations, le "
            "flambement, le contact, le dommage, la rupture, les singularites de contrainte ou les geometries "
            "complexes. Les contraintes ponctuelles pres d'une singularite restent informatives. Toute extension "
            "de perimetre necessite une campagne V&V distincte.",
            styles["body"],
        ),
        _p("7. Questions de validation Owner", styles["h1"]),
    ]
    review_rows = [
        ["Question", "Reponse Owner"],
        ["Q1. Le meme maillage TET10/TETRA10 et les memes chargements sont-ils suffisamment traces ?", "OUI / NON"],
        ["Q2. Les six facteurs de charge monotones sont-ils suffisants pour ce cas borne ?", "OUI / NON"],
        ["Q3. La comparaison UX finale a 0,03175 % est-elle acceptable ?", "OUI / NON"],
        ["Q4. La comparaison PEEQ moyenne a 0,55084 % est-elle acceptable avec cette convention ?", "OUI / NON"],
        ["Q5. Les limites de perimetre et le statut experimental sont-ils acceptes ?", "OUI / NON"],
        ["Q6. Decision globale", "accepted / accepted_with_recommendations / more_evidence_required / rejected"],
    ]
    story += [
        _table(review_rows, styles, [125 * mm, 53 * mm]),
        Spacer(1, 7 * mm),
        _p("Commentaires Owner :", styles["body"]),
        Spacer(1, 14 * mm),
        _p("Nom : Quentin Farinazzo    Signature : ____________________    Date : ____ / ____ / ______", styles["body"]),
        PageBreak(),
        _p("8. Traçabilite et reproduction", styles["h1"]),
        _p(
            "Commande de reproduction :", styles["body"]
        ),
        _p(
            "python .\\scripts\\run_code_aster_tet10_j2_structural_vnv.py --output "
            ".\\results\\VNV-TET10-J2-CODEASTER-STRUCTURAL-025",
            styles["small"],
        ),
        _p(
            "Les artefacts comprennent le modele JSON, le maillage MSH, le rapport Markdown, les resultats "
            "JSON, les sorties brutes Code_Aster, les figures, le VTU et le manifeste SHA-256. La copie de "
            "reference est archivee sous qualification/vnv/external/code_aster_tet10_j2_structural/reference/.",
            styles["body"],
        ),
        _p("References de fichiers", styles["h2"]),
        _p(
            "Etude : VNV-TET10-J2-CODEASTER-STRUCTURAL-025<br/>"
            "Rapport : results/VNV-TET10-J2-CODEASTER-STRUCTURAL-025/report.md<br/>"
            "Resume : results/VNV-TET10-J2-CODEASTER-STRUCTURAL-025/summary.json<br/>"
            "Page technique : docs/verification/tet10_j2_structural_code_aster.md",
            styles["body"],
        ),
    ]
    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return OUTPUT


if __name__ == "__main__":
    print(build_pdf())
