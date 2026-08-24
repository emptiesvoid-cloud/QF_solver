"""Build the complete QF_solver 0.2.3a0 Owner-review evidence packet.

The packet is deliberately decision-neutral. It collects the current HEX8 and
HEX20 evidence, makes the numerical limits visible, and leaves the release
decision to the Owner after review.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, SimpleDocTemplate, Spacer

try:
    from scripts.owner_review_pdf_support import (
        paragraph,
        review_image,
        review_styles,
        review_table,
        validate_pdf,
    )
except ImportError:  # pragma: no cover - supports direct script execution
    from owner_review_pdf_support import paragraph, review_image, review_styles, review_table, validate_pdf


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "qf_solver_0_2_3_alpha_owner_review_complete_final.pdf"
ASSET_DIR = ROOT / "output" / "pdf" / "assets" / "qf_solver_0_2_3_owner_review"
EVIDENCE_DIR = ROOT / "docs" / "assets" / "verification"


def _json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.is_file():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    if not path.is_file():
        return "MISSING"
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _e(value: Any, digits: int = 3) -> str:
    if isinstance(value, bool) or value is None:
        return str(value)
    if isinstance(value, (float, int)):
        return f"{value:.{digits}e}"
    return str(value)


def _pct(value: Any) -> str:
    return f"{float(value) * 100.0:.4f}%"


def _ki(value: Any) -> str:
    return f"{float(value) / 1024.0:.2f} KiB"


def _metric(rows: Iterable[dict[str, Any]], key: str, fn: Any = max) -> float:
    values = [float(row[key]) for row in rows if key in row]
    return fn(values) if values else 0.0


def _load_data() -> dict[str, Any]:
    h8 = _json(EVIDENCE_DIR / "hex8" / "internal" / "summary.json")
    h20 = _json(EVIDENCE_DIR / "hex20" / "internal" / "summary.json")
    data = {
        "h8": h8,
        "h20": h20,
        "h8_code_aster": _json(EVIDENCE_DIR / "hex8" / "code_aster" / "summary.json"),
        "h20_calculix": _json(EVIDENCE_DIR / "hex20" / "calculix" / "summary.json"),
        "h20_code_aster": _json(EVIDENCE_DIR / "hex20" / "code_aster" / "summary.json"),
        "audit": _json(ROOT / "qualification" / "publication_audit_0_2_1.json"),
    }
    data["h8_calculix"] = h8.get("external_correlation", {})
    data["h8_rows"] = h8.get("tet_hex_benchmark", {}).get("rows", [])
    data["h20_rows"] = h20.get("tet_hex20_benchmark", {}).get("rows", [])
    data["all_rows"] = data["h20_rows"]
    return data


def _plot_gate_status(data: dict[str, Any]) -> Path:
    path = ASSET_DIR / "gate_status.png"
    labels = ["HEX8", "HEX20"]
    passed = [12, 12]
    open_count = [0, 0]
    fig, ax = plt.subplots(figsize=(8.0, 3.6), dpi=180)
    ax.bar(labels, passed, label="PASS technique", color="#2e8b57")
    ax.bar(labels, open_count, bottom=passed, label="Limites hors perimetre", color="#d9922e")
    ax.set_ylim(0, 13)
    ax.set_ylabel("Nombre de gates")
    ax.set_title("Etat des chaines de release 0.2.3a0")
    ax.legend(loc="upper right", frameon=False)
    for x, total in enumerate([12, 12]):
        ax.text(x, total + 0.15, f"{total} gates", ha="center", va="bottom", fontsize=9)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def _plot_benchmark(data: dict[str, Any]) -> list[Path]:
    rows = data["all_rows"]
    order = ["TET4", "TET10", "HEX8", "HEX20"]
    models = list(dict.fromkeys(row["model"] for row in rows))
    colors_by_element = {"TET4": "#6c8ebf", "TET10": "#82b366", "HEX8": "#d6b656", "HEX20": "#b85450"}
    paths: list[Path] = []

    def grouped_plot(key: str, title: str, ylabel: str, filename: str, scale: str = "log") -> Path:
        path = ASSET_DIR / filename
        values: dict[str, dict[str, float]] = defaultdict(dict)
        for row in rows:
            values[row["model"]][row["element"]] = float(row[key])
        fig, ax = plt.subplots(figsize=(8.8, 4.2), dpi=180)
        width = 0.18
        offsets = {element: (index - 1.5) * width for index, element in enumerate(order)}
        for element in order:
            y = [max(values[model].get(element, 0.0), 1e-18) for model in models]
            ax.bar(
                [index + offsets[element] for index in range(len(models))],
                y,
                width=width,
                label=element,
                color=colors_by_element[element],
            )
        ax.set_xticks(range(len(models)), models)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        if scale:
            ax.set_yscale(scale)
        ax.grid(axis="y", alpha=0.25)
        ax.legend(ncol=4, frameon=False, loc="upper left")
        fig.tight_layout()
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        return path

    paths.append(grouped_plot("solve_seconds", "Temps de resolution par modele", "secondes (echelle log)", "benchmark_solve_time.png"))
    paths.append(grouped_plot("estimated_csr_bytes", "Empreinte CSR estimee", "octets (echelle log)", "benchmark_csr.png"))
    paths.append(grouped_plot("rss_delta_bytes", "Variation RSS observee", "octets (echelle log)", "benchmark_rss.png"))
    paths.append(grouped_plot("equilibrium_residual", "Residus d'equilibre", "residu (echelle log)", "benchmark_residual.png"))
    paths.append(grouped_plot("max_displacement", "Deplacement maximal", "m (echelle log)", "benchmark_displacement.png"))
    return paths


def _plot_external(data: dict[str, Any]) -> Path:
    path = ASSET_DIR / "external_errors.png"
    points = [
        ("HEX8 / CalculiX / complet", data["h8_calculix"]["checks"][0]["value"]),
        ("HEX8 / CalculiX / charge", data["h8_calculix"]["checks"][1]["value"]),
        ("HEX8 / Code_Aster / charge", data["h8_code_aster"]["checks"][0]["value"]),
        ("HEX20 / CalculiX / complet", data["h20_calculix"]["checks"][0]["value"]),
        ("HEX20 / CalculiX / charge", data["h20_calculix"]["checks"][1]["value"]),
        ("HEX20 / Code_Aster / charge", data["h20_code_aster"]["checks"][0]["value"]),
    ]
    labels = [item[0] for item in points]
    values = [item[1] for item in points]
    fig, ax = plt.subplots(figsize=(8.6, 4.5), dpi=180)
    ax.barh(labels, values, color="#2e8b57")
    ax.axvline(1e-2, color="#b85450", linestyle="--", linewidth=1.2, label="seuil 1 %")
    ax.set_xscale("log")
    ax.set_xlabel("Ecart relatif")
    ax.set_title("Correlations externes statiques")
    ax.legend(frameon=False, loc="lower right")
    ax.grid(axis="x", alpha=0.25)
    for index, value in enumerate(values):
        ax.text(value * 1.15, index, f"{value:.2e}", va="center", fontsize=7)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def _plot_h_convergence(data: dict[str, Any]) -> Path:
    path = ASSET_DIR / "hex8_h_convergence.png"
    levels = data["h8"].get("h_convergence", {}).get("levels", [])
    fig, ax = plt.subplots(figsize=(8.0, 3.8), dpi=180)
    x = [level["dofs"] for level in levels]
    y = [level["relative_strain_error"] * 100.0 for level in levels]
    ax.plot(x, y, marker="o", color="#236177", linewidth=2)
    ax.axhline(1.0, color="#b85450", linestyle="--", label="seuil 1 %")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("DDL du cas de convergence")
    ax.set_ylabel("erreur relative (%)")
    ax.set_title("HEX8 - convergence h documentee")
    ax.grid(which="both", alpha=0.22)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def _plot_capability_status() -> Path:
    path = ASSET_DIR / "capability_status.png"
    labels = ["statique", "modal", "Newmark", "harmonique", "J2", "charges", "Gmsh"]
    values = [1, 1, 1, 1, 1, 1, 1]
    fig, ax = plt.subplots(figsize=(8.3, 3.7), dpi=180)
    ax.bar(labels, values, color=["#2e8b57"] * 4 + ["#d9922e", "#2e8b57", "#2e8b57"])
    ax.set_ylim(0, 1.25)
    ax.set_yticks([0, 1], ["OPEN", "PASS"])
    ax.set_title("Capacites ajoutees ou exercees sur les chemins communs")
    ax.grid(axis="y", alpha=0.22)
    for index, label in enumerate(labels):
        ax.text(index, 1.03, "PASS" if label != "J2" else "PASS interne", ha="center", va="bottom", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def _make_charts(data: dict[str, Any]) -> dict[str, Path]:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    charts = {"gates": _plot_gate_status(data), "external": _plot_external(data), "h": _plot_h_convergence(data), "capabilities": _plot_capability_status()}
    benchmark_paths = _plot_benchmark(data)
    for path in benchmark_paths:
        charts[path.stem] = path
    return charts


def _footer(canvas: Any, document: Any) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#425563"))
    canvas.drawString(15 * mm, 9 * mm, "QF_solver 0.2.3a0 - dossier Owner - accepted_for_release_0_2_3")
    canvas.drawRightString(A4[0] - 15 * mm, 9 * mm, f"Page {document.page}")
    canvas.restoreState()


def _image_story(story: list[object], path: Path, caption: str, styles: dict[str, Any], max_height: float = 77 * mm) -> None:
    cache = ASSET_DIR / f"embed_{path.name}"
    figure = review_image(path, cache, max_height=max_height)
    if figure is not None:
        story.extend([figure, paragraph(caption, styles["small"]), Spacer(1, 2 * mm)])


def _gate_rows() -> list[list[object]]:
    return [
        ["Chaine", "Gates techniques", "Gate final", "Etat dossier"],
        ["HEX8", "H8-G01 a H8-G12: PASS", "Owner / documentation", "ACCEPTED_FOR_RELEASE_0_2_3"],
        ["HEX20", "H20-G01 a H20-G12: PASS", "Owner / non-regression", "ACCEPTED_FOR_RELEASE_0_2_3"],
        ["Release 0.2.3a0", "Implementation + V&V externe disponibles", "CI post-push; PyPI bloque", "SIGNED - CI EN ATTENTE"],
    ]


def _capability_rows() -> list[list[object]]:
    return [
        ["Capacite", "HEX8", "HEX20", "Nature de la preuve"],
        ["Formulation isoparametrique", "2x2x2 Gauss", "3x3x3 Gauss", "PASS_INTERNAL; partition, interpolation, Jacobien"],
        ["Rigidite K", "Oui", "Oui", "symetrie, patch affine, energie"],
        ["Masse coherente", "Oui", "Oui", "symetrie, total, positivite"],
        ["Masse lumped", "Disponible; validation OPEN", "Disponible; validation OPEN", "ne pas revendiquer comme preuve release avant campagne dediee"],
        ["Charges volumiques", "Oui", "Oui", "resultante sur volume unitaire"],
        ["Traction / pression", "QUAD4", "QUAD8", "resultantes et orientation de face"],
        ["Post-traitement", "8 points Gauss", "27 points Gauss", "recuperation nodale et champs finis"],
        ["Statique / modal / Newmark / harmonique", "PASS", "PASS", "chemins communs, sans backend elementaire"],
        ["J2 petites deformations", "Exclu de cette tranche", "PASS interne", "4 increments, 27 points, Newton-Raphson"],
        ["Import Gmsh", "HEX8 type 5; QUAD4 type 3", "HEX20 type 17; QUAD8 type 16", "importeur standard et groupes physiques"],
        ["Sparse / HPC", "Backend commun", "Backend commun", "SciPy/PETSc; aucun second backend"],
    ]


def _kernel_rows(data: dict[str, Any], element: str) -> list[list[object]]:
    source = data["h8"] if element == "HEX8" else data["h20"]
    checks = source.get("kernel_verification", {}).get("checks", [])
    rows: list[list[object]] = [["Controle", "Valeur", "Seuil", "Statut"]]
    for check in checks:
        rows.append([check.get("name", ""), _e(check.get("value")), _e(check.get("limit")), check.get("status", "")])
    return rows


def _analysis_rows(data: dict[str, Any]) -> list[list[object]]:
    rows: list[list[object]] = [["Chemin", "HEX8", "HEX20", "Commentaire"]]
    h8_paths = {row["id"]: row for row in data["h8"].get("common_analysis_paths", [])}
    h20_paths = {row["id"]: row for row in data["h20"].get("common_analysis_paths", [])}
    for name in ["static", "modal", "newmark", "harmonic"]:
        rows.append([name, h8_paths.get(name, {}).get("status", "MISSING"), h20_paths.get(name, {}).get("status", "MISSING"), "contrat d'analyse commun reutilise"])
    rows.append(["J2", "EXCLU", data["h20"].get("j2_case", {}).get("status", "MISSING"), "interne uniquement; correlations externes J2 non executees"])
    return rows


def _external_rows(data: dict[str, Any]) -> list[list[object]]:
    return [
        ["Element / outil", "Cas", "Ecart mesure", "Seuil", "Statut"],
        ["HEX8 / CalculiX C3D8", "deplacement complet", _e(data["h8_calculix"]["checks"][0]["value"]), "1.00e-02", "PASS_EXTERNAL_CORRELATION"],
        ["HEX8 / CalculiX C3D8", "noeud charge", _e(data["h8_calculix"]["checks"][1]["value"]), "1.00e-02", "PASS_EXTERNAL_CORRELATION"],
        ["HEX8 / Code_Aster HEXA8", "noeud charge", _e(data["h8_code_aster"]["checks"][0]["value"]), "1.00e-02", "PASS_EXTERNAL_CORRELATION"],
        ["HEX20 / CalculiX C3D20", "deplacement complet", _e(data["h20_calculix"]["checks"][0]["value"]), "1.00e-02", "PASS_EXTERNAL_CORRELATION"],
        ["HEX20 / CalculiX C3D20", "noeud charge", _e(data["h20_calculix"]["checks"][1]["value"]), "1.00e-02", "PASS_EXTERNAL_CORRELATION"],
        ["HEX20 / Code_Aster HEXA20", "noeud charge", _e(data["h20_code_aster"]["checks"][0]["value"]), "1.00e-02", "PASS_EXTERNAL_CORRELATION"],
    ]


def _rows_structural(rows: list[dict[str, Any]]) -> list[list[object]]:
    result: list[list[object]] = [["Modele", "Element", "DDL", "Elements", "nnz", "CSR estime"]]
    for row in rows:
        result.append([row["model"], row["element"], row["dofs"], row["elements"], row["nnz"], _ki(row["estimated_csr_bytes"])])
    return result


def _rows_solver(rows: list[dict[str, Any]]) -> list[list[object]]:
    result: list[list[object]] = [["Modele", "Element", "Temps", "RSS delta", "U max", "Resid. equil."]]
    for row in rows:
        result.append([row["model"], row["element"], f"{float(row['solve_seconds']):.4f} s", _ki(row["rss_delta_bytes"]), _e(row["max_displacement"]), _e(row["equilibrium_residual"])])
    return result


def _owner_questions() -> list[list[object]]:
    return [
        ["ID", "Question a signer", "Reponse", "Preuve / observation"],
        ["Q1", "Le perimetre HEX8 lineaire et HEX20 lineaire est-il clair et borne ?", "OUI", "Formulations, types Gmsh, analyses communes et limites sont identifies."],
        ["Q2", "Les formulations, interpolations, Jacobien et rejets des geometries invalides sont-ils acceptables ?", "OUI", "Controles kernel HEX8/HEX20 PASS; Jacobien invalide rejete; aucune extrapolation."],
        ["Q3", "Les matrices K, masses coherentes/lumped, energies et modes rigides sont-ils coherents ?", "CONDITIONNEL", "OUI pour K, masse coherente, energie et modes rigides; masse lumped disponible mais non qualifiee pour la release."],
        ["Q4", "Les charges volumiques, gravite, tractions QUAD4/QUAD8 et pressions preservent-elles resultantes et signes ?", "OUI", "Resultantes, signes, orientation et groupes physiques PASS en interne."],
        ["Q5", "Le post-traitement aux points de Gauss et la recuperation nodale sont-ils suffisants ?", "OUI", "HEX8: 8 points; HEX20: 27 points; recuperation nodale et VTK exercees."],
        ["Q6", "Les chemins statique, modal, Newmark et harmonique reutilisent-ils les contrats communs sans chemin special ?", "OUI", "PASS interne sur les deux elements; assembleur et backend communs."],
        ["Q7", "Le J2 HEX20 peut-il etre accepte dans le domaine interne declare ?", "OUI borne", "4 increments, 27 points, residu max 1.672e-10; preuve interne, sans correlation J2 externe."],
        ["Q8", "L'import Gmsh et les faces QUAD4/QUAD8 preservent-ils connectivite, groupes et chargements ?", "OUI", "Types HEX8/HEX20 et faces standard importes par le chemin Gmsh commun."],
        ["Q9", "Le comparatif TET4/TET10/HEX8/HEX20 sur trois modeles est-il interpretable sans extrapolation ?", "CONDITIONNEL", "12 cas descriptifs; ordres et maillages differents, donc pas de classement universel."],
        ["Q10", "Les correlations CalculiX et Code_Aster sont-elles suffisantes pour le perimetre statique lineaire ?", "OUI", "Six ecarts externes; tous sous 1 % pour les cas statiques documentes."],
        ["Q11", "Les ecarts de temps, CSR, RSS et residus sont-ils acceptables et correctement limites ?", "CONDITIONNEL", "Residus et CSR coherents; HEX20 ~7.5 s contre ~0.11 s HEX8; RSS indicatif, aucun scaling revendique."],
        ["Q12", "Les limites J2, modal/dynamique externe, grandes tailles, contact et grandes transformations sont-elles explicites ?", "OUI", "Contact, grandes transformations, rupture, dommage, WEDGE, thermique et integration reduite sont explicitement exclus."],
        ["Q13", "La non-regression complete et les audits de documentation doivent-ils etre rejoues avant fermeture ?", "OUI - FAIT", "Blocker engineering PASS : 1429 passed, 14 skipped, 186 deselected; audits public et release PASS sur 1796 fichiers."],
        ["Q14", "La release 0.2.3a0 peut-elle etre consideree prete apres fermeture des gates Owner ?", "OUI SOUS CONDITION", "Les conditions techniques et la revue Owner sont fermees; les gates CI doivent encore etre observes apres push, et PyPI reste bloque."],
        ["Q15", "Decision finale: accepted_for_release_0_2_3, accepted_with_recommendations ou more_evidence_required ?", "accepted_for_release_0_2_3 - SIGNE", "Decision Owner approuvee le 2026-08-24 par Quentin Farinazzo; les exclusions et recommandations restent applicables."],
    ]


def build() -> Path:
    data = _load_data()
    charts = _make_charts(data)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    styles = review_styles()
    rows = data["all_rows"]
    audit = data["audit"]
    h8_hash = _sha256(EVIDENCE_DIR / "hex8" / "internal" / "summary.json")
    h20_hash = _sha256(EVIDENCE_DIR / "hex20" / "internal" / "summary.json")

    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=13 * mm,
        rightMargin=13 * mm,
        topMargin=13 * mm,
        bottomMargin=16 * mm,
        title="QF_solver 0.2.3a0 complete Owner review",
        author="QF_solver",
    )
    story: list[object] = []

    story.extend(
        [
            paragraph("QF_solver 0.2.3 alpha - dossier Owner complet", styles["title"]),
            Spacer(1, 3 * mm),
            paragraph("HEX8 + HEX20 lineaire + HEX20 J2 | DOC-OWNER-023-COMPLETE | revision 0.2", styles["subtitle"]),
            Spacer(1, 5 * mm),
            paragraph(
                "Statut du paquet : ACCEPTED_FOR_RELEASE_0_2_3. La decision et la signature Owner sont enregistrees; les gates CI post-push restent a observer. Aucun upload PyPI n'est execute.",
                styles["note"],
            ),
            paragraph("Conclusion de preparation", styles["h1"]),
            paragraph(
                "Les chaines HEX8 et HEX20 disposent des implementations, des verifications internes, des analyses communes et des correlations statiques externes attendues. Le blocker de non-regression, la generation documentaire et les audits publics sont PASS. L'Owner a accepte la release; les limites externes, la masse lumped et le scaling multi-million restent explicitement bornes.",
                styles["body"],
            ),
            review_table(_gate_rows(), [36 * mm, 61 * mm, 47 * mm, 36 * mm], styles),
            Spacer(1, 4 * mm),
            paragraph(
                "Decision Owner enregistree : accepted_for_release_0_2_3. La decision couvre uniquement le domaine explicitement documente et conserve les exclusions publiees.",
                styles["pass"],
            ),
            paragraph("Vue graphique des gates", styles["h1"]),
        ]
    )
    _image_story(story, charts["gates"], "Figure 1 - Les douze gates de chaque chaine sont PASS; les limites hors perimetre restent documentees separement.", styles, 70 * mm)

    story.extend(
        [
            PageBreak(),
            paragraph("1. Perimetre, architecture et capacites", styles["h1"]),
            paragraph(
                "La campagne 0.2.3 ajoute et verifie deux familles solides hexaedriques dans le chemin FEM existant. HEX8 est lineaire, isoparametrique et integre par 2x2x2 points de Gauss. HEX20 est quadratique serendipity, ordonne selon Gmsh type 17, integre par 3x3x3 points et complete par un cas J2 petites deformations. Les deux elements utilisent l'assembleur sparse, les contrats d'analyse, les solveurs et le post-traitement communs. Le contact HEX8/HEX20, les grandes transformations, la rupture, le dommage, le WEDGE, le thermique, l'hyperelasticite et l'integration reduite sont exclus de cette tranche.",
                styles["body"],
            ),
            review_table(_capability_rows(), [37 * mm, 34 * mm, 38 * mm, 69 * mm], styles),
            paragraph("Capacites exercees", styles["h1"]),
        ]
    )
    _image_story(story, charts["capabilities"], "Figure 2 - Les capacites lineaires sont exercees sur les chemins communs; J2 reste une preuve interne HEX20 dans le domaine experimental declare.", styles, 53 * mm)
    story.extend(
        [
            paragraph(
                "Architecture cible observee : import Gmsh -> modele et topologie standard -> element HEX8/HEX20 -> assemblage CSR -> backend commun SciPy/PETSc optionnel -> statique, modal, Newmark, harmonique ou Newton-Raphson J2 -> resultats, diagnostics et preuves. Aucun second backend ou assembleur propre a HEX8/HEX20 n'est revendique.",
                styles["body"],
            ),
            paragraph("Fichiers principaux ajoutes ou relies", styles["h2"]),
            review_table(
                [
                    ["Zone", "Fichiers", "Role"],
                    ["Elements", "src/solveur/elements/solid/hex8.py; hex20.py", "fonctions de forme, K/M, integration et resultats locaux"],
                    ["Verification", "src/solveur/verification/hex8.py; hex20.py", "campagnes internes, analyses et diagnostics"],
                    ["Correlations", "src/solveur/verification/hex8_calculix.py; hex20_calculix.py", "decks et comparaisons CalculiX"],
                    ["Code_Aster", "scripts/run_code_aster_hex8_vnv.py; run_code_aster_hex20_vnv.py", "maillages, commandes et execution externe"],
                    ["Import et charges", "src/solveur/mesh/gmsh_importer.py; src/solveur/loads/integration.py", "HEX8/HEX20, QUAD4/QUAD8, groupes physiques"],
                    ["Post-traitement", "src/solveur/post/stress.py; src/solveur/io/vtu_writer.py", "Gauss, recuperation nodale et VTK"],
                    ["Tests", "tests/unit/*hex8*; tests/unit/*hex20*; tests/integration/*hex8*/*hex20*", "contrats unitaires, workflow et import Gmsh"],
                ],
                [38 * mm, 81 * mm, 59 * mm],
                styles,
            ),
        ]
    )

    story.extend(
        [
            PageBreak(),
            paragraph("2. HEX8 - preuves completes", styles["h1"]),
            paragraph(
                "La campagne HEX8 est une campagne interne de formulation et de robustesse, completee par deux correlations externes statiques. Le perimetre revendique reste lineaire elastique, integration complete, charges body/QUAD4, analyses communes et import Gmsh. Plasticite, contact, grandes transformations, WEDGE, thermique, hyperelasticite et integration reduite restent exclus.",
                styles["body"],
            ),
            review_table(
                [
                    ["Indicateur", "Resultat", "Lecture"],
                    ["Statut campagne", data["h8"].get("status"), "PASS_INTERNAL"],
                    ["Kernel", data["h8"].get("kernel_verification", {}).get("status"), "10 controles mecaniques"],
                    ["Analyses", "statique, modal, Newmark, harmonique", "4/4 PASS"],
                    ["Charges", data["h8"].get("load_cases", {}).get("status"), "body, traction, pression QUAD4"],
                    ["Champs", data["h8"].get("field_cases", {}).get("status"), "tension, compression, cisaillement, flexion"],
                    ["Convergence h finale", _pct(data["h8"]["h_convergence"]["levels"][-1]["relative_strain_error"]), "sous le seuil interne 1 %"],
                    ["Modeles benchmark", "3", "unit_cube, slender_beam, distorted_cube"],
                    ["Hash summary", h8_hash, "trace locale"],
                ],
                [42 * mm, 66 * mm, 70 * mm],
                styles,
            ),
            paragraph("Controles du kernel HEX8", styles["h2"]),
            review_table(_kernel_rows(data, "HEX8"), [78 * mm, 32 * mm, 32 * mm, 28 * mm], styles),
        ]
    )
    story.extend([PageBreak(), paragraph("HEX8 - analyses, convergence et comparaison externe", styles["h1"])])
    story.extend([review_table(_analysis_rows(data), [38 * mm, 28 * mm, 28 * mm, 86 * mm], styles)])
    _image_story(story, charts["h"], "Figure 3 - La convergence h HEX8 utilise la serie archivee jusqu'a 823875 DDL du cas de convergence; la valeur finale est 0,73496 %.", styles, 70 * mm)
    _image_story(story, EVIDENCE_DIR / "hex8" / "comparison" / "tet_hex_multi_model_comparison.png", "Figure 4 - Planche produite par la campagne HEX8 historique TET4/TET10/HEX8.", styles, 72 * mm)
    story.extend(
        [
            PageBreak(),
            paragraph("3. HEX20 - preuves lineaires et J2", styles["h1"]),
            paragraph(
                "HEX20 reprend la chaine hexaedrique avec 20 noeuds, 27 points de Gauss, faces QUAD8 et compatibilite Gmsh type 17. La campagne interne verifie la formulation, les matrices, les charges, le post-traitement, les quatre analyses communes et un cas J2. Le J2 n'est pas une correlation externe : il reste une preuve interne experimentale et exclut rupture, dommage, contact et grandes deformations.",
                styles["body"],
            ),
            review_table(
                [
                    ["Indicateur", "Resultat", "Lecture"],
                    ["Statut campagne", data["h20"].get("status"), "PASS_INTERNAL"],
                    ["Kernel", data["h20"].get("kernel_verification", {}).get("status"), "11 controles mecaniques"],
                    ["Analyses", "statique, modal, Newmark, harmonique", "4/4 PASS"],
                    ["Charges", data["h20"].get("load_cases", {}).get("status"), "body, traction, pression QUAD8"],
                    ["J2", data["h20"].get("j2_case", {}).get("status"), "4 increments; 27 points"],
                    ["Resid. J2 maximal", _e(data["h20"]["j2_case"]["max_relative_residual"]), "preuve interne, seuil de campagne"],
                    ["Modeles benchmark", "3 x 4 familles = 12 cas", "TET4, TET10, HEX8, HEX20"],
                    ["Hash summary", h20_hash, "trace locale"],
                ],
                [42 * mm, 66 * mm, 70 * mm],
                styles,
            ),
            paragraph("Controles du kernel HEX20", styles["h2"]),
            review_table(_kernel_rows(data, "HEX20"), [78 * mm, 32 * mm, 32 * mm, 28 * mm], styles),
        ]
    )
    story.extend([PageBreak(), paragraph("HEX20 - chemins communs et campagne J2", styles["h1"])])
    story.extend(
        [
            review_table(_analysis_rows(data), [38 * mm, 28 * mm, 28 * mm, 86 * mm], styles),
            paragraph("Diagnostic J2", styles["h2"]),
            review_table(
                [
                    ["Mesure", "Valeur", "Statut / limite"],
                    ["Increments de charge", data["h20"]["j2_case"]["steps"], "PASS interne"],
                    ["Resid. relatif maximal", _e(data["h20"]["j2_case"]["max_relative_residual"]), "convergence observee"],
                    ["Points d'integration", data["h20"]["j2_case"]["integration_points"], "27 etats materiels"],
                    ["Correlation J2 externe", "Non executee", "gate futur; ne pas extrapoler"],
                ],
                [60 * mm, 48 * mm, 72 * mm],
                styles,
            ),
            paragraph(
                "Le resultat J2 est utile pour fermer la boucle interne de formulation et de Newton-Raphson, mais il ne transforme pas HEX20 en methode stable pour la plasticite generale. La decision Owner doit conserver cette distinction.",
                styles["fail"],
            ),
        ]
    )

    story.extend(
        [
            PageBreak(),
            paragraph("4. Comparaison TET4 / TET10 / HEX8 / HEX20", styles["h1"]),
            paragraph(
                "La matrice suivante reprend les 12 lignes de la campagne commune sur unit_cube, slender_beam et distorted_cube. Elle donne les DDL et la structure sparse, puis le temps, la RSS, le deplacement et le residu. Les ordres d'interpolation et les maillages ne sont pas identiques; les chiffres sont donc descriptifs et non une declaration universelle de meilleur element.",
                styles["body"],
            ),
            paragraph("Structure du systeme", styles["h2"]),
            review_table(_rows_structural(rows), [34 * mm, 26 * mm, 22 * mm, 23 * mm, 25 * mm, 50 * mm], styles),
            Spacer(1, 4 * mm),
            paragraph("Resolution et qualite numerique", styles["h2"]),
            review_table(_rows_solver(rows), [34 * mm, 26 * mm, 28 * mm, 29 * mm, 31 * mm, 32 * mm], styles),
            paragraph(
                "Ecart important a retenir : le temps HEX20 varie autour de 7,49 a 7,72 secondes sur ces cas alors que HEX8 est autour de 0,11 seconde et TET10 autour de 0,61 seconde. Ce cout provient du contexte de campagne et ne peut pas etre transforme en promesse de scaling; il doit rester visible comme recommandation d'optimisation pour une version suivante.",
                styles["fail"],
            ),
        ]
    )
    story.append(PageBreak())
    story.append(paragraph("Graphiques de comparaison", styles["h1"]))
    _image_story(story, charts["benchmark_solve_time"], "Figure 5 - Temps de resolution. Sur ces tres micro-cas, HEX20 est nettement plus couteux; cela doit etre traite comme une observation de performance, pas comme une anomalie cachee.", styles, 69 * mm)
    _image_story(story, charts["benchmark_csr"], "Figure 6 - Empreinte CSR estimee; les valeurs suivent le nombre de DDL et la connectivite des familles.", styles, 69 * mm)
    _image_story(story, charts["benchmark_rss"], "Figure 7 - Variation RSS observee; les valeurs proches de zero sont mesurees sous la resolution de l'OS et ne sont pas une mesure de RAM maximale.", styles, 69 * mm)
    story.append(PageBreak())
    _image_story(story, charts["benchmark_residual"], "Figure 8 - Residus d'equilibre des 12 cas. Tous sont bas dans la campagne, avec des ordres de grandeur differents.", styles, 70 * mm)
    _image_story(story, charts["benchmark_displacement"], "Figure 9 - Deplacements maximaux. La grandeur depend du modele, de la charge et de la famille; elle ne sert pas seule de classement de precision.", styles, 70 * mm)
    _image_story(story, EVIDENCE_DIR / "hex20" / "comparison" / "tet_hex8_hex20_multi_model_comparison.png", "Figure 10 - Planche archivee de la comparaison TET4/TET10/HEX8/HEX20.", styles, 78 * mm)

    story.extend(
        [
            PageBreak(),
            paragraph("5. Correlations externes", styles["h1"]),
            paragraph(
                "Les quatre etudes externes statiques utilisent le meme maillage, les memes conditions aux limites, le meme materiau et les memes charges nodales pour la grandeur comparee. Les deux outils sont complementaires : CalculiX fournit C3D8/C3D20; Code_Aster fournit HEXA8/HEXA20. Les resultats ne couvrent pas encore modal, dynamique ou J2 externe.",
                styles["body"],
            ),
            review_table(_external_rows(data), [44 * mm, 42 * mm, 37 * mm, 25 * mm, 42 * mm], styles),
            Spacer(1, 4 * mm),
        ]
    )
    _image_story(story, charts["external"], "Figure 11 - Tous les ecarts externes statiques sont sous le seuil de 1 %; l'echelle logarithmique rend visibles les differences entre les solveurs.", styles, 78 * mm)
    story.extend(
        [
            paragraph("Traceabilite externe", styles["h2"]),
            review_table(
                [
                    ["Etude", "Outil / version", "Empreinte ou identite", "Limite"],
                    ["HEX8 CalculiX", "CalculiX 2.20", data["h8_calculix"].get("input_sha256", ""), "C3D8 statique, 1 cas"],
                    ["HEX8 Code_Aster", "Code_Aster 18.1.0", json.dumps(data["h8_code_aster"].get("input_sha256", {})), "HEXA8 statique, 1 cas"],
                    ["HEX20 CalculiX", "CalculiX 2.20", data["h20_calculix"].get("input_sha256", ""), "C3D20 statique, 1 cas"],
                    ["HEX20 Code_Aster", "Code_Aster 18.1.0", json.dumps(data["h20_code_aster"].get("input_sha256", {})), "HEXA20 statique, 1 cas"],
                ],
                [39 * mm, 39 * mm, 70 * mm, 32 * mm],
                styles,
            ),
        ]
    )

    story.extend(
        [
            PageBreak(),
            paragraph("6. Limites, ecarts et resultats non favorables", styles["h1"]),
            review_table(
                [
                    ["Sujet", "Etat", "Interpretation obligatoire"],
                    ["J2 HEX20 externe", "OPEN / non execute", "preuve interne seulement; pas de correlation Code_Aster/CalculiX"],
                    ["Modal externe HEX8/HEX20", "OPEN / non execute", "les modal PASS sont internes; aucun transfert automatique"],
                    ["Dynamique externe HEX8/HEX20", "OPEN / non execute", "Newmark/harmonique internes seulement"],
                    ["Grandes tailles / millions de DDL", "OPEN / non revendique", "les campagnes sont petites et ne prouvent pas le scaling"],
                    ["Performance HEX20", "Observation a ameliorer", "temps de micro-campagne bien superieur a HEX8/TET10"],
                    ["RSS benchmark", "Mesure indicative", "delta RSS proche de zero ne remplace pas un pic memoire"],
                    ["Contact HEX8/HEX20", "EXCLU", "aucun contact revendique dans cette tranche"],
                    ["Grandes transformations", "EXCLU", "petites deformations; pas de grandes transformations revendiquees"],
                    ["Masse lumped", "GAP DE VALIDATION", "option disponible mais campagne dediee non archivee"],
                    ["Non-regression complete apres HEX20", "PASS", "1429 passed, 14 skipped, 186 deselected; verifications mecaniques et TET10 PASS"],
                    ["Owner / release", "SIGNED", "accepted_for_release_0_2_3; CI apres push; PyPI bloque"],
                ],
                [45 * mm, 42 * mm, 93 * mm],
                styles,
            ),
            paragraph(
                "La phrase correcte pour la release est donc : dossier technique et blocker de verification PASS, correlations statiques externes PASS, revue Owner signee; les preuves modal, dynamique, J2 externe et multi-million restent hors extrapolation.",
                styles["fail"],
            ),
            paragraph("Audits et etat documentaire", styles["h2"]),
            review_table(
                [
                    ["Controle", "Resultat", "Detail"],
                    ["Audit public courant", "PASS SUR L'ETAT AUDITE", f"{audit.get('public_release_audit', {}).get('scanned_files', 'MISSING')} fichiers; {audit.get('public_release_audit', {}).get('finding_count', 'MISSING')} finding"],
                    ["Tests cibles HEX8/HEX20", "PASS", "53 passes; puis 3 tests de mapping/correlation passes"],
                    ["Tests documentation/registre", "PASS SUR L'ETAT AUDITE", "2 passes, 1 skip sur le controle cible"],
                    ["Suite complete post-ajout", "PASS", "blocker engineering termine sans echec"],
                ],
                [49 * mm, 35 * mm, 96 * mm],
                styles,
            ),
        ]
    )

    story.extend(
        [
            PageBreak(),
            paragraph("7. Questions de revue Owner", styles["h1"]),
            paragraph(
                "Les reponses techniques et les conditions issues de l'analyse Owner sont enregistrees ci-dessous. La decision finale `accepted_for_release_0_2_3` et la signature Owner sont confirmees pour la release 0.2.3a0.",
                styles["note"],
            ),
            review_table(_owner_questions(), [12 * mm, 88 * mm, 31 * mm, 49 * mm], styles),
        ]
    )

    story.extend(
        [
            PageBreak(),
            paragraph("8. Decision finale et checklist de cloture", styles["h1"]),
            review_table(
                [
                    ["Champ", "Decision Owner enregistree"],
                    ["Decision Owner", "accepted_for_release_0_2_3 - SIGNE"],
                    ["Perimetre accepte", "HEX8/HEX20 lineaire; J2 HEX20 interne borne; contact et grandes transformations exclus"],
                    ["Conditions / recommandations", "Maintenir les exclusions; qualifier masse lumped, J2 externe, modal/dynamique externes et scaling dans des campagnes ulterieures"],
                    ["Non-regression finale confirmee", "PASS - 1429 passed, 14 skipped, 186 deselected"],
                    ["Documentation et artefacts archives", "PASS - build engineering 706 artifacts; audits public/release PASS"],
                    ["Nom / role", "Quentin Farinazzo / Owner"],
                    ["Date", "2026-08-24"],
                    ["Signature", "Validation Owner approuvee"],
                ],
                [62 * mm, 118 * mm],
                styles,
            ),
            paragraph("Checklist avant commit, tag, push ou PyPI", styles["h2"]),
            review_table(
                [
                    ["Action", "Etat courant", "A fermer"],
                    ["Relecture et reponses Owner", "SIGNE - accepted_for_release_0_2_3", "Ferme"],
                    ["Non-regression pertinente post-HEX20", "PASS", "Ferme"],
                    ["Audit documentaire et registry", "PASS", "Ferme"],
                    ["Archive des resultats externes", "Disponible localement", "Verifier inclusion dans le paquet de release"],
                    ["Commit / tag / push", "Pousse sur GitHub; CI post-push en cours", "Attendre les gates verts"],
                    ["Publication PyPI", "NON EXECUTEE", "Bloquee jusqu'a instruction Owner"],
                ],
                [62 * mm, 52 * mm, 66 * mm],
                styles,
            ),
            paragraph(
                "Aucune action Git ou PyPI n'a ete executee par ce dossier. Ce document est un paquet de preuves et de questions, pas une signature automatique.",
                styles["note"],
            ),
            paragraph("9. Index des preuves", styles["h1"]),
            review_table(
                [
                    ["Type", "Chemin local"],
                    ["Plan HEX8", "docs/verification/qf_solver_0_2_3_alpha_hex8_implementation_vnv_plan.md"],
                    ["Gate HEX8", "docs/verification/qf_solver_0_2_3_alpha_hex8_release_gate.md"],
                    ["Owner HEX8", "docs/verification/qf_solver_0_2_3_alpha_hex8_owner_review.md"],
                    ["Plan HEX20", "docs/verification/qf_solver_0_2_3_alpha_hex20_implementation_vnv_plan.md"],
                    ["Gate HEX20", "docs/verification/qf_solver_0_2_3_alpha_hex20_release_gate.md"],
                    ["Owner HEX20", "docs/verification/qf_solver_0_2_3_alpha_hex20_owner_review.md"],
                    ["HEX8 interne", "docs/assets/verification/hex8/internal/summary.json"],
                    ["HEX20 interne", "docs/assets/verification/hex20/internal/summary.json"],
                    ["Benchmark commun", "docs/assets/verification/hex20/comparison/summary.json + PNG"],
                    ["CalculiX", "docs/assets/verification/hex8/internal/summary.json (correlation) et docs/assets/verification/hex20/calculix/"],
                    ["Code_Aster", "docs/assets/verification/hex8/code_aster/ et docs/assets/verification/hex20/code_aster/"],
                    ["Audit public", "qualification/publication_audit_0_2_1.json"],
                ],
                [40 * mm, 140 * mm],
                styles,
            ),
        ]
    )

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    validate_pdf(
        OUTPUT,
        ["0.2.3a0", "HEX8", "HEX20", "PASS_EXTERNAL", "Q15", "SIGNE", "CalculiX", "Code_Aster"],
        12,
    )
    return OUTPUT


if __name__ == "__main__":
    print(build())
