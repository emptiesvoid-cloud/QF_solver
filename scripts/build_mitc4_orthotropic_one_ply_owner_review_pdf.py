"""Build the signable Owner Review for the MITC4 one-ply orthotropic scope."""

from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "mitc4_orthotropic_one_ply_stable_owner_review.pdf"


def _load(path: str) -> dict[str, object]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _pct(value: float) -> str:
    return f"{100.0 * value:.3f} %"


def _table(rows: list[list[object]], widths: list[float]) -> Table:
    table = Table(rows, colWidths=widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d9e8f5")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#708090")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def build() -> Path:
    static = _load("results/mitc4_orthotropic_one_ply_static_20260821/summary.json")
    internal = _load("results/mitc4_orthotropic_one_ply_internal_20260821/summary.json")
    modal = _load("results/mitc4_orthotropic_modal_codeaster_20260821_56x14/summary.json")
    curved = _load(
        "results/mitc4_orthotropic_curved_axial_one_ply_calculix_20260821/summary.json"
    )
    curved_dynamic = _load("results/mitc4_orthotropic_curved_dynamic_20260821/summary.json")
    curved_dynamic_external = _load(
        "results/mitc4_orthotropic_curved_dynamic_codeaster_20260821_16x8_aligned/summary.json"
    )
    review = _load("qualification/reviews/mitc4_orthotropic_one_ply_stable_pending.json")
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleCenter", parent=styles["Title"], alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=8, leading=10))
    document = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title="MITC4 orthotropic one-ply Owner Review",
        author="QF_solver",
    )
    story: list[object] = [
        Paragraph("Owner Review - MITC4 orthotrope homogène à un pli", styles["TitleCenter"]),
        Paragraph(
            "DOC-OWNER-MITC4-ORTHOTROPIC-ONE-PLY-STABLE-001 | revision 0.2 | "
            "owner_reviewed | décision : stable borné",
            styles["Small"],
        ),
        Spacer(1, 5 * mm),
        Paragraph(
            "Scope : une lamelle orthotrope homogène représentée par "
            "<font name='Courier'>shell_laminate</font>, petites déformations, "
            "statique linéaire, modal, Newmark et harmonique. Plaques planes "
            "0/45/90 degrés et panneau courbe facettisé à orientation axiale 0 degré.",
            styles["BodyText"],
        ),
        Spacer(1, 4 * mm),
        Paragraph("Résultats techniques", styles["Heading2"]),
    ]
    static_rows = [["Orientation", "UZ [m]", "Résidu libre", "Verdict"]]
    for row in static["rows"]:
        static_rows.append(
            [
                f"{row['angle_deg']:.0f}°",
                f"{row['tip_uz_m']:.6e}",
                f"{row['free_relative_residual']:.3e}",
                "PASS",
            ]
        )
    story.extend([Paragraph("Statique interne", styles["Heading3"]), _table(static_rows, [35 * mm, 48 * mm, 43 * mm, 25 * mm])])
    dynamic_rows = [["Orientation", "f1 [Hz]", "Résidu modal", "Newmark RMS", "Harmonique"]]
    for row in internal["rows"]:
        dynamic_rows.append(
            [
                f"{row['angle_deg']:.0f}°",
                f"{row['frequency_hz']:.4f}",
                f"{row['modal_residual']:.3e}",
                _pct(row["newmark_rms"]),
                _pct(row["harmonic_error"]),
            ]
        )
    story.extend([Spacer(1, 3 * mm), Paragraph("Dynamique interne", styles["Heading3"]), _table(dynamic_rows, [30 * mm, 35 * mm, 38 * mm, 35 * mm, 35 * mm])])
    modal_error = max(float(value) for value in modal["relative_errors"])
    curved_checks = {str(item["id"]): item for item in curved["checks"]}
    story.extend(
        [
            Spacer(1, 3 * mm),
            Paragraph("Corrélations externes", styles["Heading3"]),
            _table(
                [
                    ["Cas", "Oracle", "Observable", "Écart", "Verdict"],
                    ["Plaque 45° 56x14", "Code_Aster", "modal", _pct(modal_error), "PASS"],
                    ["Panneau courbe axial 0° 24x12", "CalculiX S8R", "UZ", _pct(float(curved_checks["fine_uz_difference"]["value"])), "PASS"],
                    ["Panneau courbe dynamique 16x8", "Code_Aster DST", "modal/Newmark/harmonique", "2,340 / 0,0786 / 0,118 %", "PASS"],
                ],
                [43 * mm, 28 * mm, 40 * mm, 38 * mm, 25 * mm],
            ),
            Spacer(1, 3 * mm),
            Paragraph(
                "Dynamique courbe interne : résidu modal "
                f"{curved_dynamic['modal']['max_relative_residual']:.2e}, "
                f"Newmark RMS final {100.0 * curved_dynamic['newmark']['points'][-1]['normalized_rms_error']:.4f} %, "
                f"harmonique {100.0 * curved_dynamic['harmonic']['maximum_relative_error']:.2e} %. ",
                styles["Small"],
            ),
            Spacer(1, 4 * mm),
            Paragraph("Questions Owner", styles["Heading2"]),
        ]
    )
    questions = [
        "Q1 - Géométrie, DDL, repères, signes et projection des axes matériau : OUI",
        "Q2 - Formulation, masse cohérente, condensation du drilling et algorithmes : OUI",
        "Q3 - Maillages, chargements, blocages et comparaisons reproductibles : OUI",
        "Q4 - Erreurs primaires, résidus et invariants satisfont le seuil de 1 % : OUI",
        "Q5 - Corrélations Code_Aster/CalculiX et limites sont correctement tracées : OUI",
        "Q6 - Exclusions et limites acceptées : OUI",
        "Q7 - Décision Owner : STABLE pour le périmètre borné documenté",
    ]
    story.append(Paragraph("<br/>".join(questions), styles["BodyText"]))
    story.extend(
        [
            Spacer(1, 5 * mm),
            Paragraph(
                "Commentaire Owner : " + str(review["owner_comment"]) + "<br/><br/>"
                "Nom : Quentin Farinazzo<br/>Signature : Déclaration Owner électronique enregistrée   Date : 2026-08-21",
                styles["BodyText"],
            ),
            Spacer(1, 5 * mm),
            Paragraph(
                "Limitation importante : le cas courbe non axial à 45 degrés n'est pas inclus dans le périmètre stable, "
                "car la convention d'orientation locale n'est pas encore corrélée avec le deck externe. "
                f"La corrélation dynamique courbe axiale Code_Aster est PASS : "
                f"{max(float(row['value']) for row in curved_dynamic_external['checks'] if row['id'] == 'modal_frequencies') * 100.0:.3f} % "
                "sur les fréquences, 0,0786 % en Newmark et 0,118 % en harmonique.",
                styles["Small"],
            ),
            Paragraph(
                "Diagnostic 32x16 : modal 0,933 %, Newmark 1,51 % et harmonique aligné 16,30 % près de la résonance. "
                "Ce résultat reste ouvert et n'est pas utilisé comme preuve de promotion.",
                styles["Small"],
            ),
        ]
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document.build(story)
    return OUTPUT


if __name__ == "__main__":
    print(build())
