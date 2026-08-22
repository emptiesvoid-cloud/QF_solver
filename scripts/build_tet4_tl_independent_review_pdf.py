"""Build the independent-review packet for the TET4 Total-Lagrangian scope."""

from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "qf_solver_tet4_total_lagrangian_independent_review_0_2_1.pdf"


def _text(value: object) -> str:
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _summary(path: str) -> str:
    candidate = ROOT / path
    if not candidate.is_file():
        return "missing"
    try:
        data = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "invalid"
    return str(data.get("status", data.get("verdict", "available")))


def main() -> int:
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=8, leading=10))
    styles.add(ParagraphStyle(name="TitleQF", parent=styles["Title"], textColor=colors.HexColor("#123B4A")))
    story: list[object] = [
        Paragraph("QF_solver - Revue indépendante TET4 Total Lagrangian", styles["TitleQF"]),
        Spacer(1, 6 * mm),
        Paragraph("DOC-INDEPENDENT-REVIEW-TET4-TL-001 | Révision 0.1 | Statut : ready_for_independent_review", styles["Small"]),
        Spacer(1, 5 * mm),
        Paragraph("Ce document prépare une revue indépendante. Il ne constitue ni une décision Owner ni une promotion vers stable.", styles["BodyText"]),
        Spacer(1, 4 * mm),
        Paragraph("Périmètre : élasticité isotrope, formulation Total-Lagrangian, grandes rotations, flambement et post-flambement dans les cas référencés. Contact, rupture, dommage et plasticité sont exclus.", styles["BodyText"]),
        Spacer(1, 5 * mm),
        Paragraph("Preuves disponibles", styles["Heading2"]),
    ]
    evidence = [
        ("Formulation", "docs/verification/tet4_total_lagrangian_structural_v2.md", "document"),
        ("Noyau", "results/VNV-TET4-TL-KERNEL-001/summary.json", "kernel"),
        ("Assemblage", "results/VNV-TET4-TL-ASSEMBLY-002/summary.json", "assembly"),
        ("Incréments", "results/VNV-TET4-TL-STEPS-004/summary.json", "steps"),
        ("Contraintes", "results/VNV-TET4-TL-STRESS-005/summary.json", "stress"),
        ("Flambement", "results/VNV-TET4-TL-BUCKLING-H5-010/summary.json", "buckling"),
        ("Post-flambement", "results/VNV-TET4-TL-POSTBUCKLING-007/summary.json", "postbuckling"),
        ("Code_Aster", "qualification/vnv/external/code_aster_tl_structural/reference/summary.json", "oracle"),
    ]
    table = [["Preuve", "Artefact", "Présence / statut"]]
    for label, path, _ in evidence:
        table.append([label, path, _summary(path)])
    rendered = [[Paragraph(_text(cell), styles["Small"]) for cell in row] for row in table]
    evidence_table = Table(rendered, colWidths=[30 * mm, 112 * mm, 28 * mm], repeatRows=1)
    evidence_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#123B4A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#AAB7B8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), (colors.white, colors.HexColor("#F3F7F8"))),
    ]))
    story.extend([evidence_table, Spacer(1, 5 * mm), Paragraph("Questions de revue", styles["Heading2"])])
    questions = [
        "Le domaine et les exclusions sont-ils suffisamment précis ?",
        "Les déplacements, charges critiques et contraintes hors singularité sont-ils correctement définis ?",
        "Les raffinements montrent-ils une tendance vers une asymptote ?",
        "Les erreurs principales sont-elles inférieures ou égales à 1 % ?",
        "Les pics singuliers sont-ils séparés des observables d'acceptation ?",
        "Les imperfections et chemins de charge sont-ils suffisamment documentés ?",
        "Les exclusions contact, rupture et dommage sont-elles acceptables ?",
        "La recommandation de maintenir le statut research est-elle confirmée ?",
    ]
    qrows = [["ID", "Question", "Réponse"]]
    qrows.extend([[f"Q{i}", question, "________________"] for i, question in enumerate(questions, 1)])
    qtable = Table([[Paragraph(_text(cell), styles["Small"]) for cell in row] for row in qrows], colWidths=[12 * mm, 130 * mm, 28 * mm], repeatRows=1)
    qtable.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#123B4A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#AAB7B8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.extend([qtable, Spacer(1, 5 * mm), Paragraph("Décision : maintain_research / more_evidence_required / bounded_use", styles["BodyText"]), Paragraph("Nom, organisme, date et signature : ________________________________________________", styles["BodyText"])])
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    SimpleDocTemplate(str(OUTPUT), pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=14 * mm, bottomMargin=16 * mm, title="TET4 Total Lagrangian independent review").build(story)
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
