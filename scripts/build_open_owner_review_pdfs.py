"""Build the current QF_solver Owner-review PDFs from controlled evidence."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

from PIL import Image as PilImage
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output" / "pdf"
PENDING_CORRELATION_REVIEW = ROOT / "qualification" / "reviews" / "code_aster_correlation_owner_review_2026-08-14_pending.json"
FINAL_CORRELATION_REVIEW = ROOT / "qualification" / "reviews" / "code_aster_correlation_owner_review_2026-08-14.json"
CORRELATION_REVIEW = FINAL_CORRELATION_REVIEW if FINAL_CORRELATION_REVIEW.is_file() else PENDING_CORRELATION_REVIEW
CURVED_SUMMARY = ROOT / "results" / "VNV-MITC3-LAMINATE-CURVED-PROJECTED-CODEASTER-DST-025" / "summary.json"
CURVED_REFINED_SUMMARY = ROOT / "results" / "VNV-MITC3-LAMINATE-CURVED-PROJECTED-CODEASTER-DST-025-R1-96" / "summary.json"
HEMISPHERE_SUMMARY = ROOT / "qualification" / "vnv" / "external" / "code_aster_mitc3" / "hemisphere_v1" / "summary.json"
ORTHOTROPIC_EXTERNAL_SUMMARY = ROOT / "qualification" / "vnv" / "external" / "orthotropic_solids" / "reference" / "summary.json"
ORTHOTROPIC_DYNAMIC_SUMMARY = ROOT / "qualification" / "vnv" / "orthotropic_modal_newmark" / "reference" / "summary.json"
MANUAL_CLOSURE = ROOT / "qualification" / "reviews" / "technical_manual_content_closure_pending_2026-08-01.json"
RELEASE_REGISTER = ROOT / "qualification" / "release_vv_0_2_1.json"

CORRELATION_OUTPUT = OUTPUT_DIR / "owner_review_code_aster_correlations_2026-08-14_decision_record.pdf"
STATUS_OUTPUT = OUTPUT_DIR / "owner_review_status_2026-08-14_decision_record.pdf"


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title", parent=base["Title"], fontName="Helvetica-Bold", fontSize=20,
            leading=25, alignment=TA_CENTER, textColor=colors.HexColor("#123B4A"),
        ),
        "subtitle": ParagraphStyle(
            "subtitle", parent=base["BodyText"], fontName="Helvetica", fontSize=10.5,
            leading=14, alignment=TA_CENTER, textColor=colors.HexColor("#425563"),
        ),
        "h1": ParagraphStyle(
            "h1", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=14,
            leading=18, spaceBefore=7, spaceAfter=6, textColor=colors.HexColor("#123B4A"),
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=10.5,
            leading=13, spaceBefore=5, spaceAfter=4, textColor=colors.HexColor("#236177"),
        ),
        "body": ParagraphStyle(
            "body", parent=base["BodyText"], fontName="Helvetica", fontSize=9,
            leading=13, spaceAfter=5,
        ),
        "small": ParagraphStyle(
            "small", parent=base["BodyText"], fontName="Helvetica", fontSize=7.4,
            leading=9.5, spaceAfter=3,
        ),
        "note": ParagraphStyle(
            "note", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=8.7,
            leading=12, textColor=colors.HexColor("#733800"), backColor=colors.HexColor("#FFF3DC"),
            borderPadding=6, spaceAfter=7,
        ),
    }


def _paragraph(text: object, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(str(text)).replace("\n", "<br/>"), style)


def _display_decision(value: object) -> str:
    """Render machine-readable decision identifiers for an Owner-facing PDF."""
    return str(value).replace("_", " ")


def _table(rows: list[list[object]], widths: list[float], styles: dict[str, ParagraphStyle]) -> Table:
    header = ParagraphStyle("table_header", parent=styles["small"], fontName="Helvetica-Bold", textColor=colors.white)
    body = ParagraphStyle("table_body", parent=styles["small"], fontName="Helvetica")
    rendered = [
        [_paragraph(cell, header if row_number == 0 else body) for cell in row]
        for row_number, row in enumerate(rows)
    ]
    result = Table(rendered, colWidths=widths, repeatRows=1)
    result.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#123B4A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#AAB7B8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), (colors.white, colors.HexColor("#F3F7F8"))),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return result


def _image(path: Path, name: str, *, height: float = 75 * mm) -> Image:
    if not path.is_file():
        raise FileNotFoundError(path)
    cache = ROOT / "tmp" / "owner_review_pdf" / name
    cache.parent.mkdir(parents=True, exist_ok=True)
    with PilImage.open(path) as source:
        if source.mode in {"RGBA", "LA"}:
            background = PilImage.new("RGBA", source.size, "white")
            background.alpha_composite(source.convert("RGBA"))
            background.convert("RGB").save(cache)
        else:
            source.convert("RGB").save(cache)
    figure = Image(str(cache))
    figure._restrictSize(170 * mm, height)
    return figure


def _footer(canvas: object, document: object) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#425563"))
    canvas.drawString(16 * mm, 10 * mm, "QF_solver - Owner review interne - sans revendication de certification")
    canvas.drawRightString(A4[0] - 16 * mm, 10 * mm, f"Page {document.page}")
    canvas.restoreState()


def _checks(summary: dict[str, object]) -> list[list[object]]:
    rows: list[list[object]] = [["Controle", "Valeur", "Limite", "Statut"]]
    for check in summary["checks"]:
        value = float(check["value"])
        limit = float(check["limit"])
        value_text = f"{100.0 * value:.4g} %" if limit >= 1.0e-5 else f"{value:.3e}"
        limit_text = f"{100.0 * limit:.4g} %" if limit >= 1.0e-5 else f"{limit:.1e}"
        rows.append([check["id"], value_text, limit_text, check["status"]])
    return rows


def _question_rows(
    questions: list[str], first: int, last: int, answers: dict[str, object] | None = None
) -> list[list[object]]:
    rows: list[list[object]] = [["ID", "Question", "Reponse Owner", "Commentaire"]]
    for number in range(first, last + 1):
        question = questions[number - 1].split(": ", 1)[-1]
        answer = answers.get(f"Q{number}", {}) if answers else {}
        answer_dict = answer if isinstance(answer, dict) else {}
        rows.append([
            f"Q{number}",
            question,
            _display_decision(answer_dict.get("decision", "")),
            answer_dict.get("comment", ""),
        ])
    return rows


def _orthotropic_static_rows(summary: dict[str, object]) -> list[list[object]]:
    rows: list[list[object]] = [["Cas", "Noeuds / elements", "U CalculiX", "U Code_Aster", "VM Code_Aster"]]
    for case in summary["cases"]:
        rows.append([
            case["case"],
            f"{case['nodes']} / {case['elements']}",
            f"{100.0 * float(case['calculix_l2']):.4g} %",
            f"{100.0 * float(case['code_aster_l2']):.3e} %",
            f"{100.0 * float(case['code_aster_peak_stress']):.3e} %",
        ])
    return rows


def _orthotropic_dynamic_rows(summary: dict[str, object]) -> list[list[object]]:
    checks = {str(check["id"]): check for check in summary["checks"]}
    return [
        ["Controle", "Valeur", "Limite", "Statut"],
        ["Modal fin / theorie", f"{100.0 * float(checks['modal_fine_theory']['value']):.4g} %", "1 %", checks["modal_fine_theory"]["status"]],
        ["Residu modal", f"{float(checks['modal_residual']['value']):.3e}", "1e-8", checks["modal_residual"]["status"]],
        ["Orthogonalite masse", f"{float(checks['modal_mass_orthogonality']['value']):.3e}", "1e-8", checks["modal_mass_orthogonality"]["status"]],
        ["Raffinement Newmark", f"{100.0 * float(checks['newmark_time_refinement']['value']):.4g} %", "1 %", checks["newmark_time_refinement"]["status"]],
        ["Residu Newmark", f"{float(checks['newmark_residual']['value']):.3e}", "1e-7", checks["newmark_residual"]["status"]],
        ["Code_Aster modal", f"{float(checks['code_aster_modal']['value']):.3e}", "1e-6", checks["code_aster_modal"]["status"]],
        ["Code_Aster Newmark", f"{float(checks['code_aster_newmark']['value']):.3e}", "1e-5", checks["code_aster_newmark"]["status"]],
    ]


def _build_correlation_review(output: Path) -> Path:
    styles = _styles()
    review = json.loads(CORRELATION_REVIEW.read_text(encoding="utf-8"))
    answers = review.get("answers")
    answer_map = answers if isinstance(answers, dict) else None
    curved = json.loads(CURVED_SUMMARY.read_text(encoding="utf-8"))
    curved_refined = json.loads(CURVED_REFINED_SUMMARY.read_text(encoding="utf-8"))
    hemisphere = json.loads(HEMISPHERE_SUMMARY.read_text(encoding="utf-8"))
    orthotropic_external = json.loads(ORTHOTROPIC_EXTERNAL_SUMMARY.read_text(encoding="utf-8"))
    orthotropic_dynamic = json.loads(ORTHOTROPIC_DYNAMIC_SUMMARY.read_text(encoding="utf-8"))
    output.parent.mkdir(parents=True, exist_ok=True)
    story: list[object] = [
        Spacer(1, 26 * mm),
        Paragraph("QF_solver", styles["title"]),
        Spacer(1, 4 * mm),
        Paragraph(
            "Owner review - correlations Code_Aster - decision enregistree rev. " + str(review.get("revision", "0.1")),
            styles["subtitle"],
        ),
        Spacer(1, 13 * mm),
        Paragraph("Objet de la decision", styles["h1"]),
        Paragraph(
            "Ce dossier rassemble les preuves de correlation externe executees le 14 aout 2026 et la decision Owner enregistree. "
            "Cette decision confirme des domaines bornes et leurs exclusions; elle ne transforme pas automatiquement "
            "une fonctionnalite experimentale en fonctionnalite stable.",
            styles["body"],
        ),
        Paragraph(
            "Decision Owner enregistree : " + _display_decision(review.get("decision", "pending")) + ". "
            "Le gate release-vv reste une decision distincte.",
            styles["note"],
        ),
        _table([
            ["Document", "Statut", "Questions", "Evidence principale"],
            [review["review_id"] + " rev. " + str(review.get("revision", "0.1")), _display_decision(review["status"]), "Q1 a Q10", "Code_Aster 18.1.0 dans Docker, image epinglee"],
            ["Maturite", "Pas de promotion automatique", "Portee", "Composite, TET4 TL, orthotropie, MITC3 courbe"],
        ], [42 * mm, 38 * mm, 33 * mm, 57 * mm], styles),
        Spacer(1, 5 * mm),
        Paragraph("A lire avant de repondre : docs/verification/owner_review_code_aster_2026-08-14.md et les rapports references dans chaque section.", styles["small"]),
        PageBreak(),
        Paragraph("1. Composite NAFEMS R0031 / Code_Aster", styles["h1"]),
        Paragraph(
            "Bande stratifiee en flexion trois points : cinq maillages communs, comparaison du deplacement UZ au point E. "
            "L'image est epinglee par digest SHA-256 : simvia/code_aster@sha256:4629a21a109309bb97fbdc27d750445cc869e151e2e2ed6290f69539614e4435. "
            "L'ecart fin QF_solver / NAFEMS est 0.458 % et l'ecart QF_solver / Code_Aster est 0.251 %. "
            "La contrainte S11 est informative; S13, delaminage, rupture progressive et calibration d'essai sont exclus du domaine utilisateur composite.",
            styles["body"],
        ),
        Paragraph(
            "Lecture du graphe : la valeur publique NAFEMS -1.06 mm est une cible scalaire publiee, pas une solution de reference "
            "maillage par maillage. Apres 20 x 4, QF_solver et Code_Aster s'en eloignent legerement, mais leurs increments finaux "
            "sont respectivement 0.0967 % et 0.0920 %, tandis que leur ecart mutuel tombe a 0.2509 %. La campagne ne permet pas "
            "d'attribuer ce decalage a une formulation precise; le scalar NAFEMS est donc lu comme une tolerance, et non comme une asymptote exacte.",
            styles["note"],
        ),
        _image(ROOT / "docs" / "assets" / "reviews" / "nafems_r0031_convergence.png", "nafems_convergence.png", height=67 * mm),
        _table(_question_rows(review["questions"], 1, 4, answer_map), [12 * mm, 88 * mm, 29 * mm, 38 * mm], styles),
        PageBreak(),
        Paragraph("2. TET4 total-lagrangien", styles["h1"]),
        Paragraph(
            "La revue regroupe les controles noyau, assemblage multi-elements, sensibilite aux increments, contrainte, "
            "flambement et post-flambement, avec un raffinement final de 98 304 elements. Le resultat est propose pour "
            "un usage de recherche borne, non stable et sans extrapolation aux grandes rotations, au contact ou a la rupture.",
            styles["body"],
        ),
        _image(ROOT / "docs" / "assets" / "reviews" / "tet4_tl_assembly_convergence.png", "tet4_tl_assembly.png", height=66 * mm),
        _table(_question_rows(review["questions"], 5, 5, answer_map), [12 * mm, 88 * mm, 29 * mm, 38 * mm], styles),
        Spacer(1, 4 * mm),
        Paragraph("Reference : docs/verification/tet4_total_lagrangian_structural_v2.md", styles["small"]),
        PageBreak(),
        Paragraph("3. Solides orthotropes", styles["h1"]),
        Paragraph(
            "Les preuves rassemblent une eprouvette perforee et une equerre 3D en statique, ainsi que des campagnes "
            "modales et Newmark. La convention Voigt a cisaillements d'ingenieur et la projection global / materiau sont "
            "documentees. Le grand modele orthotrope, le chemin PETSc large-scale et MPC/RBE2 restent explicitement ouverts.",
            styles["body"],
        ),
        Paragraph("Correlations statiques sur maillage identique", styles["h2"]),
        _table(_orthotropic_static_rows(orthotropic_external), [43 * mm, 28 * mm, 31 * mm, 32 * mm, 32 * mm], styles),
        Spacer(1, 4 * mm),
        Paragraph("Verification modale et Newmark orthotrope TET4", styles["h2"]),
        _table(_orthotropic_dynamic_rows(orthotropic_dynamic), [58 * mm, 37 * mm, 32 * mm, 39 * mm], styles),
        Spacer(1, 3 * mm),
        _image(ROOT / "docs" / "assets" / "reviews" / "orthotropic_lbracket_code_aster.png", "orthotropic_lbracket.png", height=44 * mm),
        _table(_question_rows(review["questions"], 6, 7, answer_map), [12 * mm, 88 * mm, 29 * mm, 38 * mm], styles),
        PageBreak(),
        Paragraph("4. MITC3 multicouche courbe a orientation projetee", styles["h1"]),
        Paragraph(
            "Panneau cylindrique facettise, empilement [0/90/90/0], petit deplacement et direction globale projetee "
            "sur chaque facette. QF_solver MITC3+ est compare a Code_Aster DST / TRIA3 sur la meme connectivite.",
            styles["body"],
        ),
        _table(_checks(curved), [67 * mm, 34 * mm, 34 * mm, 32 * mm], styles),
        Spacer(1, 4 * mm),
        _image(ROOT / "results" / "VNV-MITC3-LAMINATE-CURVED-PROJECTED-CODEASTER-DST-025" / "convergence_qf_code_aster.png", "mitc3_curved_convergence.png", height=58 * mm),
        _image(ROOT / "results" / "VNV-MITC3-LAMINATE-CURVED-PROJECTED-CODEASTER-DST-025" / "curved_laminate_deformation_qf_code_aster.png", "mitc3_curved_deformation.png", height=58 * mm),
        PageBreak(),
        Paragraph("4.1 Suivi de raffinement MITC3 courbe : 96 x 48", styles["h1"]),
        Paragraph(
            "Une reprise controlee a 9 216 triangles (96 x 48) a ete executee en plus du niveau 64 x 32. Les increments spatiaux "
            "diminuent a 3.381 % pour QF_solver et 3.818 % pour Code_Aster, sous la limite de 5 %. L'ecart vectoriel QF_solver / "
            "Code_Aster passe de 0.578 % a 0.996 % : il reste sous 1 %, mais n'est pas monotone. Le resultat soutient une acceptation "
            "avec recommandation; il ne justifie pas de supprimer toute reserve sans niveau supplementaire ou extrapolation de Richardson.",
            styles["note"],
        ),
        _table(_checks(curved_refined), [67 * mm, 34 * mm, 34 * mm, 32 * mm], styles),
        Spacer(1, 4 * mm),
        _image(ROOT / "results" / "VNV-MITC3-LAMINATE-CURVED-PROJECTED-CODEASTER-DST-025-R1-96" / "convergence_qf_code_aster.png", "mitc3_curved_r1_convergence.png", height=66 * mm),
        _table(_question_rows(review["questions"], 8, 8, answer_map), [12 * mm, 88 * mm, 29 * mm, 38 * mm], styles),
        PageBreak(),
        Paragraph("5. MITC3 hemisphere pince", styles["h1"]),
        Paragraph(
            "Hemisphere pince avec ouverture de 18 degres, six niveaux de maillage et comparaison a Code_Aster DKT / TRIA3. "
            "Le dernier ecart vectoriel QF_solver / Code_Aster est 0.1536 %, l'erreur QF par rapport a la reference est 0.5912 % "
            "et l'increment final QF est 0.2605 %. Les contraintes au point de charge restent singulieres et ne sont pas des observables d'acceptation.",
            styles["body"],
        ),
        _table(_checks(hemisphere), [67 * mm, 34 * mm, 34 * mm, 32 * mm], styles),
        Spacer(1, 4 * mm),
        _image(ROOT / "qualification" / "vnv" / "external" / "code_aster_mitc3" / "hemisphere_v1" / "convergence_qf_code_aster.png", "mitc3_hemisphere_convergence.png", height=56 * mm),
        _image(ROOT / "qualification" / "vnv" / "external" / "code_aster_mitc3" / "hemisphere_v1" / "level_32" / "fine_deformation_qf_code_aster.png", "mitc3_hemisphere_deformation.png", height=56 * mm),
        _table(_question_rows(review["questions"], 9, 9, answer_map), [12 * mm, 88 * mm, 29 * mm, 38 * mm], styles),
        PageBreak(),
        Paragraph("6. Decision Owner", styles["h1"]),
        Paragraph(
            "La decision ci-dessous ferme uniquement cette revue. Elle ne ferme pas automatiquement le gate release-vv, "
            "qui exige toujours une maturite stable pour chaque scope requis et une decision de release distincte.",
            styles["body"],
        ),
        _table(_question_rows(review["questions"], 10, 10, answer_map), [12 * mm, 88 * mm, 29 * mm, 38 * mm], styles),
        Spacer(1, 12 * mm),
        Paragraph("Nom : " + str(review.get("owner", "Quentin Farinazzo")), styles["body"]),
        Paragraph("Date : " + str(review.get("decision_date", "2026-08-14")), styles["body"]),
        Paragraph("Signature : declared_owner_review (not_independent)", styles["body"]),
        Spacer(1, 6 * mm),
        Paragraph("References de preuve", styles["h2"]),
        Paragraph("- docs/verification/composite_code_aster_nafems_2026-08-14.md\n- docs/verification/code_aster_correlation_campaign_2026-08-14.md\n- docs/verification/mitc3_laminate_curved_code_aster.md\n- qualification/evidence/code_aster_correlation_campaign_2026-08-14/", styles["small"]),
    ]
    document = SimpleDocTemplate(
        str(output), pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm,
        topMargin=15 * mm, bottomMargin=17 * mm, title="QF_solver Owner review Code_Aster correlations",
    )
    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return output


def _build_status_review(output: Path) -> Path:
    styles = _styles()
    closure = json.loads(MANUAL_CLOSURE.read_text(encoding="utf-8"))
    release = json.loads(RELEASE_REGISTER.read_text(encoding="utf-8"))
    review = json.loads(CORRELATION_REVIEW.read_text(encoding="utf-8"))
    candidate = ROOT / closure["document"]["path"]
    output.parent.mkdir(parents=True, exist_ok=True)
    candidate_status = "available" if candidate.is_file() else "missing from current checkout"
    story: list[object] = [
        Spacer(1, 28 * mm),
        Paragraph("QF_solver", styles["title"]),
        Spacer(1, 4 * mm),
        Paragraph("Carte des Owner reviews et decisions", styles["subtitle"]),
        Spacer(1, 13 * mm),
        Paragraph("Etat des Owner reviews", styles["h1"]),
        _table([
            ["Priorite", "Document", "Decision attendue", "Etat"],
            ["1", "Correlations Code_Aster du 2026-08-14", "Decision " + _display_decision(review.get("decision", "pending")), "DECISION ENREGISTREE"],
            ["2", "Manuel technique revision 0.3", "Accepter le PDF exact et son empreinte", candidate_status],
            ["Apres", "Release V0.2.1a0", "Decision de gel distincte", "NE PAS VALIDER ENCORE"],
        ], [18 * mm, 58 * mm, 58 * mm, 43 * mm], styles),
        Spacer(1, 5 * mm),
        Paragraph(
            "La decision Code_Aster est enregistree avec recommandations et ne demande pas de nouvelle relecture immediate. "
            "Le manuel 0.3 est administratif : le registre pointe vers un PDF qui n'est pas present dans ce checkout, "
            "donc son empreinte ne peut pas etre revue ni fermee honnêtement aujourd'hui.",
            styles["note"],
        ),
        PageBreak(),
        Paragraph("Revues deja fermees : aucune relecture demandee", styles["h1"]),
        _table([
            ["Scope", "Decision enregistree", "Date", "Reservation principale"],
            ["TET4 modal / Newmark / harmonique", "accepted_for_bounded_engineering_use", "2026-08-02", "Raffinement 10k demande et trace"],
            ["TET10 modal / Newmark / harmonique", "accepted_for_bounded_engineering_use", "2026-08-02", "Raffinement Newmark 10k demande et trace"],
            ["MITC3 dynamique lineaire", "accepted_for_bounded_engineering_use", "2026-08-02", "Raffinement modal frequence conserve"],
            ["BEAM2 et discret dynamique", "accepted_for_bounded_engineering_use", "2026-08-02", "Domaine lineaire borne"],
            ["MITC3 multicouche courbe", "accepted_for_v020_alpha_experimental_bounded_use", "2026-08-09", "Courbe statique, facettes, petit deplacement"],
            ["TET10 J2 structurel", "accepted_with_recommendations", "2026-08-09", "J2 petite deformation monotone"],
            ["MITC4 multicouche dynamique", "accepted_for_bounded_engineering_use", "2026-08-10", "Backend modal 10k a renforcer"],
            ["Contact unilateral sans frottement", "accepted_for_bounded_engineering_use", "2026-07-29", "Pas de frottement ni grand glissement"],
            ["Contraintes singulieres orthotropes", "accepted_with_recommendations", "2026-07-29", "Chemins et moyennes de bande uniquement"],
            ["Documentation technique revision 0.2", "accepted", "2026-08-02", "Pas un argument de qualification mecanique"],
        ], [41 * mm, 51 * mm, 25 * mm, 60 * mm], styles),
        Spacer(1, 6 * mm),
        Paragraph("Le registre release-vv reste en attente : decision Owner = " + str(release["owner_review"]["decision"]) + ". Cela est attendu tant que la nouvelle revue Code_Aster et les gates de maturite ne sont pas fermes.", styles["body"]),
    ]
    document = SimpleDocTemplate(
        str(output), pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm,
        topMargin=15 * mm, bottomMargin=17 * mm, title="QF_solver Owner review status",
    )
    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return output


def _validate(path: Path, phrases: tuple[str, ...], minimum_pages: int) -> None:
    if not path.is_file() or path.stat().st_size < 4_000:
        raise RuntimeError(f"Incomplete PDF: {path}")
    reader = PdfReader(str(path))
    if len(reader.pages) < minimum_pages:
        raise RuntimeError(f"Unexpected page count in {path}")
    content = "\n".join(page.extract_text() or "" for page in reader.pages)
    missing = [phrase for phrase in phrases if phrase not in content]
    if missing:
        raise RuntimeError(f"Missing PDF text in {path}: {missing}")


def build() -> tuple[Path, Path]:
    """Build and validate the controlled PDFs for still-open Owner decisions."""
    correlation = _build_correlation_review(CORRELATION_OUTPUT)
    status = _build_status_review(STATUS_OUTPUT)
    _validate(correlation, ("Q1", "Q10", "MITC3 hemisphere pince", "accepted with recommendations"), 6)
    _validate(status, ("DECISION ENREGISTREE", "NE PAS VALIDER ENCORE", "Revues deja fermees"), 2)
    return correlation, status


if __name__ == "__main__":
    for built in build():
        print(built)
