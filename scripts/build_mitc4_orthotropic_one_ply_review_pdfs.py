"""Build the reviewable PDF set for the MITC4 one-ply orthotropic scope."""

from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "pdf"


def _load(relative: str) -> dict[str, object]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def _table(rows: list[list[object]], widths: list[float]) -> Table:
    table = Table(rows, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d9e8f5")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#708090")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def _document(path: Path, title: str) -> SimpleDocTemplate:
    return SimpleDocTemplate(
        str(path), pagesize=A4, rightMargin=15 * mm, leftMargin=15 * mm,
        topMargin=14 * mm, bottomMargin=14 * mm, title=title, author="QF_solver",
    )


def build_audit() -> Path:
    path = OUT / "mitc4_orthotropic_one_ply_completion_audit.pdf"
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="SmallAudit", parent=styles["BodyText"], fontSize=8, leading=10))
    audit = ROOT / "docs" / "verification" / "mitc4_stable_package" / "completion_audit.md"
    story: list[object] = [
        Paragraph("Audit de clôture - MITC4 orthotrope homogène à un pli", styles["Title"]),
        Paragraph("DOC-AUDIT-MITC4-ORTHO-ONE-PLY-CLOSURE-001 | revision 0.1 | ready_for_owner_review", styles["SmallAudit"]),
        Spacer(1, 5 * mm),
        Paragraph("Ce document présente les preuves disponibles, les limites et les conditions nécessaires avant promotion stable.", styles["BodyText"]),
        Spacer(1, 4 * mm),
        Paragraph("État des exigences", styles["Heading2"]),
        _table([
            ["Domaine", "Résultat", "État"],
            ["Statique plane", "Résidus 8,09e-12 à 2,39e-10", "PASS"],
            ["Statique courbe", "CalculiX S8R, UZ 0,012 %", "PASS externe"],
            ["Modal plan", "Erreurs externes finales 0,604 à 0,892 %", "PASS < 1 %"],
            ["Modal courbe", "Résidu interne 1,30e-10; externe 2,340 % à 16x8", "PASS borné"],
            ["Newmark courbe", "Interne 0,2623 %; externe 0,0786 %", "PASS"],
            ["Harmonique courbe", "Externe 0,118 % à 16x8; 16,30 % au diagnostic 32x16", "Limite ouverte"],
            ["Owner Review", "Décision et signature absentes", "OUVERT"],
        ], [45 * mm, 85 * mm, 40 * mm]),
        Spacer(1, 5 * mm),
        Paragraph("Décision attendue", styles["Heading2"]),
        Paragraph("Répondre aux questions Q1 à Q7 dans la revue Owner. Une promotion stable doit rester limitée aux plaques planes 0/45/90 degrés et aux panneaux courbes facettisés à orientation axiale 0 degré. Les orientations courbes non axiales, S13/S23, dommage, rupture, délamination et grandes déformations restent exclues.", styles["BodyText"]),
        Spacer(1, 4 * mm),
        Paragraph("Commentaires Owner : _______________________________________________<br/><br/>Nom : Quentin Farinazzo<br/>Signature : ________________________________   Date : ________________", styles["BodyText"]),
        Spacer(1, 4 * mm),
        Paragraph(f"Source Markdown : {audit}", styles["SmallAudit"]),
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    _document(path, "MITC4 orthotropic one-ply completion audit").build(story)
    return path


def build_results() -> Path:
    path = OUT / "mitc4_orthotropic_one_ply_technical_results.pdf"
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="SmallResults", parent=styles["BodyText"], fontSize=8, leading=10))
    static = _load("results/mitc4_orthotropic_one_ply_static_20260821/summary.json")
    internal = _load("results/mitc4_orthotropic_one_ply_internal_20260821/summary.json")
    curved = _load("results/mitc4_orthotropic_curved_dynamic_20260821/summary.json")
    story: list[object] = [
        Paragraph("Résultats techniques - MITC4 orthotrope homogène à un pli", styles["Title"]),
        Paragraph("DOC-VNV-MITC4-ORTHO-ONE-PLY-RESULTS-001 | revision 0.1 | unités SI", styles["SmallResults"]),
        Spacer(1, 4 * mm),
        Paragraph("Statique plane", styles["Heading2"]),
        _table([["Orientation", "UZ moyen [m]", "Résidu libre", "Verdict"]] + [
            [f"{row['angle_deg']:.0f}°", f"{row['tip_uz_m']:.6e}", f"{row['free_relative_residual']:.3e}", "PASS"]
            for row in static["rows"]
        ], [35 * mm, 50 * mm, 45 * mm, 25 * mm]),
        Spacer(1, 4 * mm),
        Paragraph("Dynamique plane", styles["Heading2"]),
        _table([["Orientation", "f1 [Hz]", "Résidu modal", "Newmark RMS", "Harmonique"]] + [
            [f"{row['angle_deg']:.0f}°", f"{row['frequency_hz']:.4f}", f"{row['modal_residual']:.3e}", f"{100*row['newmark_rms']:.4f} %", f"{100*row['harmonic_error']:.4e} %"]
            for row in internal["rows"]
        ], [28 * mm, 34 * mm, 40 * mm, 38 * mm, 40 * mm]),
        Spacer(1, 4 * mm),
        Paragraph("Dynamique courbe interne", styles["Heading2"]),
        _table([
            ["Contrôle", "Valeur", "Seuil", "Verdict"],
            ["Résidu modal", f"{curved['modal']['max_relative_residual']:.3e}", "1e-7", "PASS"],
            ["Newmark RMS final", f"{100*curved['newmark']['points'][-1]['normalized_rms_error']:.4f} %", "1 %", "PASS"],
            ["Dérive énergétique", f"{max(p['maximum_relative_energy_drift'] for p in curved['newmark']['points']):.3e}", "1e-4", "PASS"],
            ["Harmonique interne", f"{100*curved['harmonic']['maximum_relative_error']:.3e} %", "1e-6 relatif", "PASS"],
        ], [55 * mm, 48 * mm, 40 * mm, 30 * mm]),
        Spacer(1, 4 * mm),
        Paragraph("La corrélation Code_Aster/CalculiX et le diagnostic courbe 32x16 sont présentés dans l'audit de clôture. Le diagnostic harmonique 32x16 reste une limite ouverte et n'est pas une preuve de promotion.", styles["BodyText"]),
    ]
    figure = ROOT / "results" / "mitc4_orthotropic_curved_dynamic_20260821" / "curved_dynamic_convergence.png"
    if figure.is_file():
        story.extend([Spacer(1, 4 * mm), Paragraph("Figure de convergence courbe", styles["Heading2"]), Image(str(figure), width=170 * mm, height=64 * mm)])
    story.extend([Spacer(1, 4 * mm), Paragraph("Source complète : docs/verification/mitc4_stable_package/orthotropic_one_ply_results_2026-08-21.md", styles["SmallResults"])])
    OUT.mkdir(parents=True, exist_ok=True)
    _document(path, "MITC4 orthotropic one-ply technical results").build(story)
    return path


def main() -> None:
    from build_mitc4_orthotropic_one_ply_owner_review_pdf import build

    for path in (build(), build_audit(), build_results()):
        print(path)


if __name__ == "__main__":
    main()
