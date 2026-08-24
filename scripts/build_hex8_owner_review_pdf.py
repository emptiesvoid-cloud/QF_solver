"""Build the controlled HEX8 Owner-review PDF for QF_solver 0.2.3a0."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, SimpleDocTemplate, Spacer

try:
    from scripts.owner_review_pdf_support import (
        paragraph,
        review_styles,
        review_table,
        validate_pdf,
    )
except ImportError:  # pragma: no cover - supports direct script execution
    from owner_review_pdf_support import paragraph, review_styles, review_table, validate_pdf


ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "results" / "hex8_full_campaign" / "summary.json"
CODE_ASTER_SUMMARY = ROOT / "results" / "hex8_code_aster_external" / "summary.json"
GATE = ROOT / "docs" / "verification" / "qf_solver_0_2_3_alpha_hex8_release_gate.md"
OUTPUT = ROOT / "output" / "pdf" / "qf_solver_0_2_3_alpha_hex8_owner_review.pdf"


def _footer(canvas: Any, document: Any) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#425563"))
    canvas.drawString(
        15 * mm,
        9 * mm,
        "QF_solver 0.2.3a0 - revue Owner HEX8 - decision non renseignee",
    )
    canvas.drawRightString(A4[0] - 15 * mm, 9 * mm, f"Page {document.page}")
    canvas.restoreState()


def _gate_rows() -> list[list[object]]:
    return [
        ["Gate", "Statut", "Preuve / limite"],
        ["H8-G01 Formulation", "PASS_INTERNAL", "Fonctions de forme, Jacobien, gradients, Gauss et orientations invalides."],
        ["H8-G02 K + M", "PASS_INTERNAL", "Rigidite, masse coherente et lumped, symetrie et energie."],
        ["H8-G03 Chargements", "PASS_INTERNAL", "Force volumique, traction et pression QUAD4 avec resultantes."],
        ["H8-G04 Post-traitement", "PASS_INTERNAL", "Champs de Gauss, contraintes et recuperation nodale."],
        ["H8-G05 Analyses", "PASS_INTERNAL", "Statique, modal, Newmark et harmonique sur les chemins communs."],
        ["H8-G06 Import Gmsh", "PASS_INTERNAL", "HEX8, QUAD4, orientation et groupes physiques."],
        ["H8-G07 Sparse/HPC", "PASS_INTERNAL", "Backend commun SciPy/PETSc; aucun solveur propre a HEX8."],
        ["H8-G08 V&V interne", "PASS_INTERNAL", "Patch, charges, distorsion, h final 0,735 %, modal, dynamique et nu."],
        ["H8-G09 Externe", "PASS_EXTERNAL_CORRELATION", "CalculiX C3D8 + Code_Aster HEXA8; ecarts 1,20e-6, 1,96e-6 et 4,18e-16."],
        ["H8-G10 TET/HEX", "PASS_INTERNAL", "81 DDL comparables; temps, nnz, CSR, RSS et residus."],
        ["H8-G11 Regression", "PASS", "1349 passed, 107 deselected; tests rapides hors campagnes longues."],
        ["H8-G12 Owner", "OPEN", "Reponses Owner et decision finale a renseigner."],
    ]


def _owner_rows() -> list[list[object]]:
    return [
        ["ID", "Question", "Reponse Owner"],
        ["Q1", "Formulation et orientations invalides couvrent-elles le domaine revendique ?", "A COMPLETER"],
        ["Q2", "K/M et chargements sont-ils coherents avec les conventions documentees ?", "A COMPLETER"],
        ["Q3", "Import Gmsh HEX8/QUAD4 et groupes physiques sont-ils preserves ?", "A COMPLETER"],
        ["Q4", "Gauss et recuperation nodale sont-ils verifies sans masquer les singularites ?", "A COMPLETER"],
        ["Q5", "Les quatre analyses reutilisent-elles les contrats communs ?", "A COMPLETER"],
        ["Q6", "La couche sparse/HPC et SciPy sans PETSc restent-elles fonctionnelles ?", "A COMPLETER"],
        ["Q7", "Les cas V&V ont-ils une erreur finale <= 1 % dans le domaine declare ?", "A COMPLETER"],
        ["Q8", "La correlation externe utilise-t-elle geometrie, BC, materiau et charge identiques ?", "A COMPLETER"],
        ["Q9", "Le benchmark TET/HEX publie-t-il precision, temps, RAM, DDL et nnz ?", "A COMPLETER"],
        ["Q10", "Les exclusions et limites sont-elles visibles et non extrapolees ?", "A COMPLETER"],
    ]


def build() -> Path:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    external = summary["external_correlation"]
    code_aster = json.loads(CODE_ASTER_SUMMARY.read_text(encoding="utf-8"))
    benchmark = summary["tet_hex_benchmark"]["rows"]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    styles = review_styles()
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=16 * mm,
        title="QF_solver 0.2.3a0 HEX8 Owner Review",
        author="QF_solver",
    )
    story: list[object] = [
        paragraph("Revue Owner HEX8 - QF_solver 0.2.3a0", styles["title"]),
        Spacer(1, 3 * mm),
        paragraph("DOC-HEX8-023-003 | revision 0.2 | dossier a signer", styles["subtitle"]),
        Spacer(1, 5 * mm),
        paragraph(
            "Objet : examiner la chaine HEX8 complete avant toute preparation de release. "
            "La campagne technique est documentee; la decision Owner reste volontairement vide.",
            styles["note"],
        ),
        paragraph("Perimetre et regle de release", styles["h1"]),
        paragraph(
            "Le perimetre couvre HEX8 elastique lineaire isoparametrique, integration complete 2x2x2, "
            "masse coherente/lumped, chargements volumiques et faces QUAD4, analyses statique/modale/Newmark/harmonique, "
            "import Gmsh standard et backend sparse commun. Sont exclus : WEDGE, thermique, contact HEX8, plasticite, "
            "hyperelasticite et integration reduite C3D8R. La v0.2.3a0 ne doit pas etre taggee ou publiee tant que H8-G12 n'est pas PASS.",
            styles["body"],
        ),
        paragraph("Etat des gates", styles["h1"]),
        review_table(_gate_rows(), [39 * mm, 39 * mm, 102 * mm], styles),
        PageBreak(),
        paragraph("Preuves quantitatives", styles["h1"]),
        review_table(
            [
                ["Indicateur", "Valeur", "Interpretation"],
                ["Statut campagne interne", summary["status"], "PASS_INTERNAL"],
                ["Convergence h finale", f"{summary['h_convergence']['levels'][-1]['relative_strain_error']:.6%}", "Sous le seuil de 1 % dans le cas declare."],
                ["Correlation externe", external["status"], "CalculiX 2.20, C3D8, meme maillage/BC/materiau/charges."],
                ["Ecart deplacement complet", f"{external['checks'][0]['value']:.6e}", f"Seuil {external['checks'][0]['limit']:.2e}"],
                ["Ecart noeud charge", f"{external['checks'][1]['value']:.6e}", f"Seuil {external['checks'][1]['limit']:.2e}"],
                ["Code_Aster HEXA8", code_aster["status"], f"Ecart noeud charge {code_aster['checks'][0]['value']:.6e}; seuil 1e-2."],
                ["Non-regression", "1349 passed, 107 deselected", "Filtre explicite hors benchmark/large/evidence."],
            ],
            [43 * mm, 48 * mm, 89 * mm],
            styles,
        ),
        paragraph("Comparatif TET / HEX8 sur trois modeles", styles["h1"]),
        review_table(
            [["Modele", "Element", "DDL", "Elements", "Temps s", "nnz", "RSS delta"]]
            + [[
                row["model"], row["element"], row["dofs"], row["elements"], f"{row['solve_seconds']:.4f}",
                row["nnz"], f"{row['rss_delta_bytes'] / 1024:.1f} KiB",
            ] for row in benchmark],
            [30 * mm, 20 * mm, 15 * mm, 22 * mm, 23 * mm, 20 * mm, 40 * mm],
            styles,
        ),
        paragraph(
            "Cette comparaison mesure uniquement le cas unitaire documente; elle ne constitue pas une generalisation de performance.",
            styles["note"],
        ),
        PageBreak(),
        paragraph("Questions a renseigner par l'Owner", styles["h1"]),
        paragraph(
            "Inscrire OUI, NON ou CONDITIONNELLEMENT et ajouter une observation courte. Toute condition doit rester compatible avec le perimetre et les exclusions du gate.",
            styles["note"],
        ),
        review_table(_owner_rows(), [14 * mm, 126 * mm, 40 * mm], styles),
        Spacer(1, 7 * mm),
        paragraph("Decision finale", styles["h1"]),
        review_table(
            [
                ["Champ", "A renseigner"],
                ["Decision Owner", "accepted_for_release_0_2_3 / accepted_with_recommendations / more_evidence_required"],
                ["Justification", ""],
                ["Conditions ou recommandations", ""],
                ["Nom / role", ""],
                ["Date", ""],
                ["Signature", ""],
            ],
            [52 * mm, 128 * mm],
            styles,
        ),
        paragraph(
            "Rappel : ce PDF est un dossier de revue. Il ne signe pas automatiquement la release et ne declenche aucun commit, tag, push ou depot PyPI.",
            styles["fail"],
        ),
    ]
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    validate_pdf(OUTPUT, ["QF_solver 0.2.3a0", "H8-G12", "A COMPLETER", "CalculiX", "Code_Aster"], 3)
    return OUTPUT


if __name__ == "__main__":
    print(build())
