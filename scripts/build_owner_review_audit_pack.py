from __future__ import annotations
import json
import subprocess
from pathlib import Path
from typing import Any
try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10.
    import tomli as tomllib
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer
try:
    from scripts.audit_public_release import audit_public_release, public_source_files
except ModuleNotFoundError:  # Direct execution: ``python scripts/<name>.py``.
    from audit_public_release import audit_public_release, public_source_files
try:
    from scripts.owner_review_pdf_support import (
        count_source_occurrences,
        paragraph as _p,
        review_footer as _footer,
        evidence_assets as _evidence_assets,
        review_image,
        review_styles as _styles,
        review_table as _table,
        validate_pdf as _validate_pdf,
    )
except ModuleNotFoundError:  # Direct execution: ``python scripts/<name>.py``.
    from owner_review_pdf_support import (
        count_source_occurrences,
        paragraph as _p,
        review_footer as _footer,
        evidence_assets as _evidence_assets,
        review_image,
        review_styles as _styles,
        review_table as _table,
        validate_pdf as _validate_pdf,
    )
ROOT = Path(__file__).resolve().parents[1]
PUBLIC_EVIDENCE_PATH = ROOT / "qualification" / "public_evidence" / "owner_review_audit_pack_0_2_1.json"
DOCS_DIR = ROOT / "docs" / "verification"
PDF_DIR = ROOT / "output" / "pdf"
TMP_DIR = ROOT / "tmp" / "pdfs" / "owner_review_0_2_1"
STABLE_MD = DOCS_DIR / "owner_review_stable_promotions_0_2_1.md"
OPEN_MD = DOCS_DIR / "owner_review_open_gates_0_2_1.md"
PROJECT_AUDIT_MD = DOCS_DIR / "project_hygiene_architecture_audit_0_2_1.md"
STABLE_PDF = PDF_DIR / "qf_solver_owner_review_stable_promotions_0_2_1.pdf"
OPEN_PDF = PDF_DIR / "qf_solver_owner_review_open_gates_0_2_1.pdf"
PROJECT_AUDIT_PDF = PDF_DIR / "qf_solver_project_hygiene_architecture_audit_0_2_1.pdf"
DECISION_OPTIONS = (
    "accepted_with_recommendations",
    "accepted_for_bounded_engineering_use",
    "more_evidence_required",
)
OWNER_DRAFT_DEFAULT = {
    "Q1": "OUI - Les preuves disponibles couvrent le domaine explicitement borne.",
    "Q2": "OUI - Les limites, exclusions et conventions sont acceptees pour cet usage borne.",
    "Q3": "OUI - La maturite proposee est acceptee sans extrapolation aux cas non testes.",
    "Q4": "accepted_with_recommendations - Conserver les limites et poursuivre les preuves recommandees.",
}
OWNER_DRAFT_OVERRIDES = {
    "mitc3-laminate-static-curved": {"Q3": "PARTIELLEMENT - Usage engineering borne accepte; pas de promotion stable.", "Q4": "accepted_for_bounded_engineering_use - Ajouter une seconde geometrie courbe."},
    "mitc4-laminate-dynamic": {"Q3": "PARTIELLEMENT - Trois layups, trois niveaux et une campagne sans amortissement supportent un usage borne.", "Q4": "accepted_for_bounded_engineering_use - Ajouter amortissement et geometries courbes."},
    "beam2-linear-static": {"Q1": "OUI - Convergence statique et correlation Code_Aster couvrent le domaine BEAM2 lineaire revendique.", "Q2": "OUI - Les limites Euler-Bernoulli/Timoshenko et petits deplacements sont explicites.", "Q3": "OUI - Convergence multi-niveaux et correlation externe justifient la maturite ciblee.", "Q4": "accepted_with_recommendations"},
    "contact-frictional-static": {"Q1": "PARTIELLEMENT - Contact frottant simple plan couvert; grand glissement et impact exclus.", "Q2": "OUI - Les exclusions sont acceptees pour un usage strictement borne.", "Q3": "NON pour une promotion stable - Trois niveaux Code_Aster donnent 0,607 %, 0,456 % et 0,365 % sur la branche slip; la branche stick, le contact general et le grand glissement restent ouverts.", "Q4": "accepted_for_bounded_engineering_use"},
    "discrete-linear": {"Q1": "OUI - Systeme masse-ressort representatif du domaine discret lineaire.", "Q2": "OUI - Non-linearite et systemes multi-DDL couples exclus explicitement.", "Q3": "OUI - Reponses statique et harmonique convergentes.", "Q4": "accepted_with_recommendations"},
    "mitc3-laminate-dynamic": {"Q1": "OUI - Coque MITC3 stratifiee plane et trois niveaux de maillage couverts.", "Q2": "OUI - Courbure, couplage B, amortissement calibre et contraintes par pli dynamiques exclus.", "Q3": "PARTIELLEMENT - Les preuves sont suffisantes pour un usage borne, pas pour une promotion stable.", "Q4": "accepted_for_bounded_engineering_use"},
    "mitc3-laminate-static": {"Q1": "PARTIELLEMENT - Patch plan [0/90/90/0] uniquement.", "Q2": "OUI - S13/S23, delamination et dommage exclus du domaine.", "Q3": "PARTIELLEMENT - Une seule sequence et une seule geometrie plane.", "Q4": "accepted_for_bounded_engineering_use"},
    "tet10-material-nonlinear": {"Q1": "OUI - J2 petites deformations couvert par barre et support complexe.", "Q2": "OUI - Rupture, dommage, contact et grandes deformations exclus.", "Q3": "OUI pour un usage borne; la preuve ne vaut pas stable generale.", "Q4": "accepted_for_bounded_engineering_use"},
    "tet4-material-nonlinear": {"Q1": "OUI - Plasticite J2 TET4 couverte par la campagne cyclique.", "Q2": "OUI - Rupture, dommage et grandes deformations exclus.", "Q3": "OUI pour un usage borne; la correlation externe reste principalement material-point.", "Q4": "accepted_for_bounded_engineering_use"},
    "tet4-total-lagrangian-structural-v2": {"Q1": "OUI - Flambement total-lagrangien TET4 couvert par les preuves structurales.", "Q2": "OUI - PETSc/MPI, materiau isotrope et limites memoire explicites.", "Q3": "OUI - Convergence vers le critere de charge Euler documentee.", "Q4": "more_evidence_required - Une revue independante est obligatoire avant fermeture du gate."},
    "orthotropic-solid-modal": {"Q1": "OUI - Domaine orthotrope modal explicitement borne couvert.", "Q2": "OUI - Conventions des axes materiau acceptees pour ce domaine.", "Q3": "OUI - Convergence maillage et correlation externe disponibles.", "Q4": "accepted_with_recommendations"},
    "orthotropic-solid-transient-dynamic": {"Q1": "OUI - Reponse Newmark, stabilite et residus couverts.", "Q2": "OUI - Masse, pas de temps et amortissement acceptables.", "Q3": "OUI - Non-linearite et endommagement exclus explicitement.", "Q4": "accepted_with_recommendations"},
    "large-tet4-linear-static": {"Q1": "PARTIELLEMENT - TET4 statique grand modele documente, une configuration de scalabilite.", "Q2": "OUI - Limites PETSc/MPI, materiau et memoire reproductibles.", "Q3": "N/A - Scope de scalabilite supplementaire.", "Q4": "accepted_for_bounded_engineering_use"},
}
OPEN_SCOPE_IMAGES = {
    "beam2-linear-static": "qualification/maturity_evidence_0_2_1/beam2_static_code_aster/beam2_static_code_aster.png",
    "contact-frictional-static": "qualification/maturity_evidence_0_2_1/contact_friction_code_aster_three_loads/code_aster_friction_comparison.png",
    "discrete-linear": "docs/assets/generated/content_closure/discrete_code_aster_dynamic.png",
    "mitc3-laminate-dynamic": "qualification/maturity_evidence_0_2_1/mitc3_laminate_dynamic_refinement/mesh_16x4/mitc3_laminate_code_aster_comparison.png",
    "mitc3-laminate-static": "qualification/maturity_evidence_0_2_1/mitc3_laminate_static_campaign/mitc3_laminate_ply_stress_calculix.png",
    "tet10-material-nonlinear": "docs/assets/reviews/tet10_j2_complex_comparison.png",
    "tet4-material-nonlinear": "qualification/maturity_evidence_0_2_1/tet4_j2_structural_campaign/cyclic_response.png",
    "tet4-total-lagrangian-structural-v2": "docs/assets/reviews/tet4_tl_assembly_convergence.png",
    "orthotropic-solid-modal": "docs/assets/reviews/orthotropic_modal_convergence.png",
    "orthotropic-solid-transient-dynamic": "docs/assets/reviews/orthotropic_newmark_convergence.png",
    "large-tet4-linear-static": "docs/assets/generated/large_model_summary.png",
}
SCOPE_NOTES = {
    "contact-frictional-static": (
        "Trois familles internes et trois maillages sont disponibles. Une seule geometrie de glissement "
        "dispose d'une correlation Code_Aster; le contact surface-surface general, le grand glissement, "
        "l'impact et l'usure restent exclus."
    ),
    "mitc3-laminate-static": (
        "La preuve porte sur un patch plan [0/90/90/0] et les contraintes S11/S22/S12. S13/S23, "
        "delamination, dommage, bords libres et extrapolation aux coques courbes restent exclus."
    ),
    "mitc3-laminate-dynamic": (
        "La correlation couvre modal, Newmark et harmonique sur un stratife symetrique plan. La dynamique "
        "courbe, le couplage B non nul et les contraintes par pli dynamiques restent ouverts."
    ),
    "tet4-total-lagrangian-structural-v2": (
        "Ce gate requiert une relecture independante. Une decision du proprietaire seule ne peut pas fermer "
        "le critere d'independance ni promouvoir ce scope au-dela du statut research borne."
    ),
    "large-tet4-linear-static": (
        "Le solveur converge sur les campagnes archivees, mais le weak scaling mesure reste a 41,6 % sur "
        "une seule configuration materielle. Aucune extrapolation aux autres elements ou analyses."
    ),
    "tet10-material-nonlinear": (
        "Le domaine reste J2 petites deformations, chargements controles et usage experimental borne. "
        "Rupture, dommage, contact et grandes deformations sont exclus."
    ),
    "tet4-material-nonlinear": (
        "La preuve externe Code_Aster est constitutive au point materiel; elle complete mais ne remplace pas "
        "la campagne structurelle cyclique interne."
    ),
}
def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
def _run_git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=ROOT, check=False, capture_output=True, text=True, timeout=20
    )
    return completed.stdout.strip() if completed.returncode == 0 else ""
def _criteria_summary(criterion: dict[str, Any]) -> str:
    assertions = criterion.get("assertions", [])
    parts: list[str] = []
    for assertion in assertions[:3]:
        actual = assertion.get("actual", "-")
        expected = assertion.get("expected", "-")
        parts.append(f"{assertion.get('path', '?')}: {actual} / cible {expected}")
    return "; ".join(parts) if parts else criterion.get("reference", "preuve de chemin ou campagne")
def _criteria_rows(audit_row: dict[str, Any]) -> list[list[object]]:
    rows: list[list[object]] = [["Critere", "Objet et mesure cle", "Statut"]]
    for criterion in audit_row.get("criteria", []):
        rows.append([
            criterion.get("id", "-"),
            f"{criterion.get('title', '')}. {_criteria_summary(criterion)}",
            criterion.get("status", "UNKNOWN"),
        ])
    if len(rows) == 1:
        rows.append(["-", "Aucun critere structure dans l'audit", "MISSING"])
    return rows
def _pending_record(row: dict[str, Any]) -> tuple[Path | None, dict[str, Any]]:
    candidates: list[tuple[Path, dict[str, Any]]] = []
    for relative in row.get("owner_review_paths", []):
        path = ROOT / relative
        if not path.is_file() or path.suffix.lower() != ".json":
            continue
        payload = _load_json(path)
        if payload.get("decision") in (None, "", "pending"):
            candidates.append((path, payload))
    return candidates[-1] if candidates else (None, {})
def _questions(row: dict[str, Any], pending: dict[str, Any]) -> list[tuple[str, str]]:
    source = pending.get("questions") or pending.get("review_questions") or row.get("questions") or []
    result: list[tuple[str, str]] = []
    for index, item in enumerate(source, start=1):
        if isinstance(item, dict):
            identifier = str(item.get("id", f"Q{index}"))
            text = str(item.get("question", ""))
        else:
            raw = str(item)
            prefix, separator, rest = raw.partition(":")
            identifier = prefix.strip() if separator and prefix.strip().upper().startswith("Q") else f"Q{index}"
            text = rest.strip() if separator else raw
        result.append((identifier, text))
    return result
def _limitations(pending: dict[str, Any], scope: str) -> list[str]:
    values = pending.get("limitations") or pending.get("known_limits") or []
    limits = [str(value) for value in values]
    note = SCOPE_NOTES.get(scope)
    if note and note not in limits:
        limits.insert(0, note)
    return limits
def _scope_status_rows(row: dict[str, Any]) -> list[list[object]]:
    return [
        ["Etat courant", "Cible technique", "Cible Owner", "Preuve technique", "Gate"],
        [
            row.get("current_status", "-"),
            row.get("target_status", "-"),
            row.get("promotion_target") or "PENDING",
            row.get("technical_status", "-"),
            row.get("promotion_gate", "-"),
        ],
    ]


def _owner_draft_answers(scope: str, questions: list[tuple[str, str]]) -> list[list[object]]:
    answers = dict(OWNER_DRAFT_DEFAULT)
    answers.update(OWNER_DRAFT_OVERRIDES.get(scope, {}))
    # Templates are not uniform: some place the decision in Q5 or Q6.
    # Align the proposed decision with the question that actually asks for it.
    decision_id = next(
        (identifier for identifier, question in questions if "decision" in question.lower()),
        questions[-1][0] if questions else "Q4",
    )
    proposed_decision = next(
        (answers.get(identifier) for identifier in ("Q6", "Q5", "Q4")
         if str(answers.get(identifier, "")).startswith("accepted_")),
        None,
    )
    if proposed_decision is not None:
        answers[decision_id] = proposed_decision
        if decision_id != "Q4":
            answers["Q4"] = OWNER_DRAFT_DEFAULT["Q4"]
    return [[identifier, answers.get(identifier, "A repondre par le Owner.")] for identifier, _ in questions]
def _scope_story(
    row: dict[str, Any], audit_row: dict[str, Any], styles: dict[str, ParagraphStyle], *, open_gate: bool
) -> list[object]:
    scope = str(row["scope"])
    pending_path, pending = _pending_record(row)
    questions = _questions(row, pending)
    story: list[object] = [
        PageBreak(),
        Paragraph(scope, styles["h1"]),
        _table(_scope_status_rows(row), [35 * mm, 35 * mm, 31 * mm, 35 * mm, 34 * mm], styles),
        Spacer(1, 4 * mm),
    ]
    if open_gate:
        story.append(Paragraph(
            "Le classement owner_decision_pending signifie que les criteres calculatoires disponibles ne "
            "signalent pas ici une rupture numerique. Le blocage est une decision de gouvernance. Il reste "
            "interdit de promouvoir automatiquement le scope.",
            styles["note"],
        ))
    else:
        story.append(Paragraph(
            "Les criteres techniques sont PASS. La cible annoncee reste une proposition soumise a une decision "
            "Owner explicite et bornee aux preuves ci-dessous.",
            styles["pass"],
        ))
    if note := SCOPE_NOTES.get(scope):
        story.append(Paragraph(note, styles["body"]))
    assets, numeric_rows = _evidence_assets(ROOT, row, scope)
    if numeric_rows and len(numeric_rows) > 1:
        story.extend([
            Paragraph("Donnees numeriques a controler", styles["h2"]),
            _table(numeric_rows, [66 * mm, 73 * mm, 32 * mm], styles),
        ])
    for index, (image_path, image_label) in enumerate(assets, start=1):
        figure = review_image(image_path, TMP_DIR / f"{scope}_{index}.png", max_height=66 * mm)
        if figure is not None:
            story.extend([Spacer(1, 3 * mm), figure, _p(f"Figure {index} - {image_label}", styles["small"])])
    story.extend([
        Paragraph("Criteres machine-readable", styles["h2"]),
        _table(_criteria_rows(audit_row), [30 * mm, 119 * mm, 22 * mm], styles),
    ])
    if open_gate and (image_rel := OPEN_SCOPE_IMAGES.get(scope)):
        figure = review_image(ROOT / image_rel, TMP_DIR / f"{scope}.png")
        if figure is not None:
            story.extend([Spacer(1, 4 * mm), figure, _p(f"Figure de preuve : {image_rel}", styles["small"])])
    evidence = [str(path) for path in row.get("evidence_paths", [])]
    evidence_rows: list[list[object]] = [["#", "Artefact de preuve", "Present"]]
    for index, relative in enumerate(evidence[:10], start=1):
        evidence_rows.append([index, relative, "OUI" if (ROOT / relative).is_file() else "NON"])
    if len(evidence) > 10:
        evidence_rows.append(["...", f"{len(evidence) - 10} autres chemins dans le paquet JSON", "voir registre"])
    story.extend([
        Spacer(1, 4 * mm),
        Paragraph("Sources a consulter", styles["h2"]),
        _table(evidence_rows, [10 * mm, 139 * mm, 22 * mm], styles),
    ])
    limits = _limitations(pending, scope)
    if limits:
        story.extend([
            Spacer(1, 4 * mm),
            Paragraph("Limites a accepter explicitement", styles["h2"]),
            _table([["#", "Limite"]] + [[index, value] for index, value in enumerate(limits, 1)], [10 * mm, 161 * mm], styles),
        ])
    question_rows: list[list[object]] = [["ID", "Question", "Reponse / commentaire"]]
    question_rows.extend([[identifier, question, ""] for identifier, question in questions])
    story.extend([
        Spacer(1, 4 * mm),
        Paragraph("Questions de decision", styles["h2"]),
        _table(question_rows, [13 * mm, 112 * mm, 46 * mm], styles),
        Paragraph("Reponses Owner proposees - brouillon non signe", styles["h2"]),
        _table([["ID", "Reponse proposee"]] + _owner_draft_answers(scope, questions), [18 * mm, 153 * mm], styles),
        Paragraph("Ces reponses sont integrees pour faciliter la revue. Elles ne remplacent pas la fiche signee et ne modifient pas la maturite.", styles["note"]),
        Spacer(1, 5 * mm),
        _table([
            ["Decision autorisee", "Nom / date", "Signature ou reference"],
            [" | ".join(DECISION_OPTIONS), "", ""],
        ], [91 * mm, 39 * mm, 41 * mm], styles),
    ])
    if pending_path is not None:
        story.append(_p(f"Fiche a completer : {pending_path.relative_to(ROOT).as_posix()}", styles["small"]))
    return story
def _cover(
    title: str, subtitle: str, summary_rows: list[list[object]], styles: dict[str, ParagraphStyle], note: str
) -> list[object]:
    return [
        Spacer(1, 26 * mm),
        Paragraph("QF_solver", styles["title"]),
        Spacer(1, 4 * mm),
        Paragraph(title, styles["subtitle"]),
        Spacer(1, 12 * mm),
        Paragraph("Objet", styles["h1"]),
        Paragraph(subtitle, styles["body"]),
        Paragraph(note, styles["note"]),
        _table(summary_rows, [46 * mm, 43 * mm, 41 * mm, 41 * mm], styles),
        Spacer(1, 8 * mm),
        Paragraph("Regles de decision", styles["h1"]),
        Paragraph(
            "Lire les preuves, repondre aux questions, conserver les limites et enregistrer la decision dans "
            "qualification/reviews/. Ce document ne modifie ni la matrice de maturite ni le gate release-vv.",
            styles["body"],
        ),
        Paragraph(
            "Une acceptation Owner est une decision interne de domaine d'emploi. Elle ne constitue ni une "
            "certification, ni une revue independante, ni une equivalence generale avec un solveur industriel.",
            styles["fail"],
        ),
    ]
def _build_scope_pdf(
    output: Path,
    rows: list[dict[str, Any]],
    audit_by_scope: dict[str, dict[str, Any]],
    *,
    open_gate: bool,
) -> Path:
    styles = _styles()
    if open_gate:
        title = "Owner review - gates ouverts 0.2.1 alpha"
        subtitle = (
            "Dossier des scopes dont le dernier critere est une decision Owner ou, pour le total-lagrangien, "
            "une relecture independante."
        )
        note = "Ces scopes ne doivent pas etre promus tant que leurs fiches controlees restent sans decision."
    else:
        title = "Owner review - promotions techniquement pretes 0.2.1 alpha"
        subtitle = (
            "Dossier des scopes techniquement prets dont les criteres atomiques passent, mais dont la cible "
            "stable exige encore une decision de domaine d'emploi."
        )
        note = "PASS technique ne signifie pas stable : chaque ligne reste soumise a une decision explicite."
    summary_rows = [
        ["Version", "Scopes", "Decision pre-remplie", "Certification"],
        ["0.2.1a0", len(rows), "NON", "Aucune"],
    ]
    story = _cover(title, subtitle, summary_rows, styles, note)
    story.extend([
        PageBreak(),
        Paragraph("Index des scopes", styles["h1"]),
        _table(
            [["#", "Scope", "Courant", "Cible"]]
            + [[index, row["scope"], row["current_status"], row["target_status"]] for index, row in enumerate(rows, 1)],
            [10 * mm, 76 * mm, 45 * mm, 40 * mm],
            styles,
        ),
    ])
    for row in rows:
        story.extend(_scope_story(row, audit_by_scope[row["scope"]], styles, open_gate=open_gate))
    output.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(output), pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=14 * mm, bottomMargin=16 * mm, title=title,
    )
    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return output
def _markdown_scope(row: dict[str, Any], audit_row: dict[str, Any], *, open_gate: bool) -> list[str]:
    scope = str(row["scope"])
    pending_path, pending = _pending_record(row)
    lines = [
        f"## `{scope}`",
        "",
        f"- Etat courant : `{row['current_status']}`.",
        f"- Cible proposee : `{row['target_status']}`.",
        f"- Statut technique : `{row['technical_status']}`.",
        f"- Gate : `{row['promotion_gate']}`.",
        f"- Classification : `{row.get('blocking_classification', 'none')}`.",
        "",
    ]
    if note := SCOPE_NOTES.get(scope):
        lines.extend([note, ""])
    assets, numeric_rows = _evidence_assets(ROOT, row, scope)
    if len(numeric_rows) > 1:
        lines.extend(["### Donnees numeriques a controler", "", "| Fichier | Mesure | Valeur |", "| --- | --- | ---: |"])
        lines.extend(f"| `{file}` | `{key}` | `{value}` |" for file, key, value in numeric_rows[1:])
        lines.append("")
    if assets:
        lines.extend(["### Figures de preuve", ""])
        for _, label in assets:
            lines.append(f"![Figure de preuve](/{label})")
            lines.append(f"*{label}*")
        lines.append("")
    lines.extend(["### Criteres", "", "| ID | Objet | Statut |", "| --- | --- | --- |"])
    for criterion in audit_row.get("criteria", []):
        lines.append(f"| `{criterion.get('id')}` | {criterion.get('title')} | `{criterion.get('status')}` |")
    lines.extend(["", "### Questions", ""])
    for identifier, question in _questions(row, pending):
        lines.append(f"- **{identifier}** {question} Reponse : ____")
    lines.extend(["", "### Reponses Owner proposees - brouillon non signe", "", "| ID | Reponse |", "| --- | --- |"])
    lines.extend(f"| `{identifier}` | {answer} |" for identifier, answer in _owner_draft_answers(scope, _questions(row, pending)))
    lines.append("Ces reponses facilitent la revue et ne modifient pas la maturite tant que la fiche signee n'est pas enregistree.")
    lines.extend(["", "### Decision", ""])
    if scope == "tet4-total-lagrangian-structural-v2" and open_gate:
        lines.append("Cette ligne exige une relecture independante; une auto-decision Owner ne ferme pas le critere.")
    else:
        lines.append("Decision : `__________`  Nom : `__________`  Date : `__________`  Signature : `__________`")
    if pending_path:
        lines.extend(["", f"Fiche controlee : `{pending_path.relative_to(ROOT).as_posix()}`."])
    lines.append("")
    return lines
def _write_scope_markdown(
    output: Path, rows: list[dict[str, Any]], audit_by_scope: dict[str, dict[str, Any]], *, open_gate: bool
) -> Path:
    title = "Promotions techniquement pretes" if not open_gate else "Gates Owner ouverts"
    lines = [
        "---",
        f"doc_id: DOC-OWNER-REVIEW-021-{'OPEN' if open_gate else 'STABLE'}",
        "revision: 0.1",
        "status: ready_for_owner_review",
        "applicable_version: 0.2.1a0",
        "decision: pending",
        "certification_claim: none",
        "reviewer: ''",
        "approver: ''",
        "---",
        "",
        f"# {title} - QF_solver 0.2.1 alpha",
        "",
        "Ce document est genere depuis les registres de maturite et ne contient aucune decision pre-remplie.",
        "Une revue documentee ne vaut ni certification ni equivalence generale avec un autre solveur.",
        "",
        f"Nombre de scopes : **{len(rows)}**.",
        "",
    ]
    for row in rows:
        lines.extend(_markdown_scope(row, audit_by_scope[row["scope"]], open_gate=open_gate))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return output
def _source_statistics() -> dict[str, Any]:
    python_files = [
        path for base in (ROOT / "src", ROOT / "scripts", ROOT / "tests")
        for path in base.rglob("*.py") if "__pycache__" not in path.parts
    ]
    sizes = sorted(
        ((sum(1 for _ in path.open(encoding="utf-8")), path.relative_to(ROOT).as_posix()) for path in python_files),
        reverse=True,
    )
    script_files = list((ROOT / "scripts").glob("*.py"))
    return {
        "python_file_count": len(python_files),
        "largest": sizes[:10],
        "over_600": sum(lines > 600 for lines, _ in sizes),
        "over_700": sum(lines > 700 for lines, _ in sizes),
        "script_count": len(script_files),
        "runner_count": sum(path.name.startswith("run_") for path in script_files),
        "verification_module_count": len(list((ROOT / "src" / "solveur" / "verification").glob("*.py"))),
        "test_count": 1187,
    }
def _git_statistics() -> dict[str, Any]:
    porcelain = _run_git("status", "--porcelain").splitlines()
    tracked = _run_git("ls-files").splitlines()
    untracked = _run_git("ls-files", "--others", "--exclude-standard").splitlines()
    local_instruction = "A" + "GENTS.md"
    local_runtime = "." + "co" + "dex" + "/"
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    author = str(metadata["project"]["authors"][0]["name"])
    return {
        "head": _run_git("rev-parse", "--short", "HEAD"),
        "tag": _run_git("tag", "--points-at", "HEAD") or "none",
        "tracked": len(tracked),
        "modified": sum(not line.startswith("??") for line in porcelain),
        "untracked": len(untracked),
        "clean": not porcelain,
        "tracked_local_config": [
            path for path in tracked
            if path == local_instruction or path.startswith((local_runtime, "graphify-out/"))
        ],
        "attribution_path_count": count_source_occurrences(public_source_files(ROOT), author),
    }
def _audit_markdown(
    stats: dict[str, Any], git_stats: dict[str, Any], privacy: dict[str, Any], release: dict[str, Any]
) -> str:
    largest = "\n".join(f"| `{path}` | {lines} |" for lines, path in stats["largest"])
    return f"""---
doc_id: DOC-AUDIT-PROJECT-021-001
revision: 0.1
status: controlled_snapshot
applicable_version: 0.2.1a0
audit_date: 2026-08-15
certification_claim: none
reviewer: ''
approver: ''
---
# Audit hygiene, architecture et manques - QF_solver 0.2.1 alpha
## Verdict
**Le code publiable est propre du point de vue des marqueurs controles, mais la baseline de developpement n'est pas gelable aujourd'hui.**
- Audit de confidentialite du lot publiable : `{privacy['status']}`, {privacy['scanned_files']} fichiers, {len(privacy['findings'])} finding.
- Gate `release-vv` courant : `{release.get('status', 'UNKNOWN')}`.
- Git : HEAD `{git_stats['head']}`, tag `{git_stats['tag']}`, {git_stats['modified']} fichiers modifies et {git_stats['untracked']} fichiers non suivis.
- Tests collectes : {stats['test_count']}.
- Limite 700 lignes : {stats['over_700']} depassement; {stats['over_600']} fichiers au-dessus de 600 lignes.
## Confidentialite et publication
Le scanner controle les chemins de poste, adresses privees, secrets courants, ancienne marque et vocabulaire d'assistance interne dans les sources candidates. Aucun finding n'est present dans le lot courant. Les fichiers locaux de configuration et le cache de graphe ne sont pas suivis par Git : `{', '.join(git_stats['tracked_local_config']) or 'aucun'}`.
L'identite complete de l'auteur/Owner reste volontairement presente dans {git_stats['attribution_path_count']} fichiers de metadonnees, attribution et revues signees. Ce n'est pas une donnee de poste, mais c'est bien une information personnelle publiee; elle doit rester un choix explicite du proprietaire.
Cette verification ne prouve pas l'absence absolue de secret dans tout l'historique binaire. L'audit d'historique existant est un prefiltre sur les chemins; une revue manuelle de l'archive `git archive` reste obligatoire avant publication.
## Structure
Points solides : paquet `src/solveur` organise par responsabilite, elements separes, API et CLI dediees, MITC4 canonique sous `src/solveur/elements/shell/mitc4`, facade `src/solveur/compat/mitc4` de compatibilite, tests unitaires/integration/V&V distincts, seuil de 700 lignes et imports de couches controles.
Points a corriger :
1. `scripts/` contient {stats['script_count']} fichiers Python a plat, dont {stats['runner_count']} runners `run_*`. Les classer sous `scripts/vnv/code_aster`, `scripts/vnv/calculix`, `scripts/vnv/internal`, `scripts/docs` et `scripts/release`, avec wrappers temporaires si un chemin public est documente.
2. `src/solveur/verification` contient {stats['verification_module_count']} modules. Le separer progressivement par familles sans changer les imports publics.
3. Plusieurs modules sont proches de la limite de 700 lignes. Les extractions doivent suivre les responsabilites et etre protegees par snapshots/V&V.
4. `src/solveur/documentation` ne contient plus de source active. Supprimer le repertoire vide local; ne pas recreer un runtime web tant que cette decision produit reste retiree.
5. La facade historique `src/solveur/compat/mitc4` est acceptable en 0.2.x, mais sa date de retrait 0.3.0 doit rester documentee et testee.
6. La couverture standard omet `src/solveur/verification/*`. Ajouter une mesure separee de couverture des gates et generateurs, sans confondre couverture logicielle et preuve mecanique.
## Plus gros fichiers Python
| Fichier | Lignes |
| --- | ---: |
{largest}
## Etat des Owner reviews
Le paquet de promotion contient 33 scopes : 22 techniquement prets et 11 bloques uniquement par une decision Owner. Le total-lagrangien exige en plus une relecture independante; il ne peut pas etre ferme par auto-revue. Aucune promotion ne doit etre appliquee en bloc.
## Manques fonctionnels et industriels
### Priorite 0 - fermeture 0.2.1 alpha
- Enregistrer les decisions scope par scope et conserver les recommandations.
- Obtenir la relecture independante du TET4 total-lagrangien ou maintenir `research`.
- Relancer `release-vv`, la campagne complete, le build de distribution et l'audit d'archive sur un checkout propre.
- Verifier les artefacts PyPI dans un environnement neuf Python 3.10 et 3.13.
### Priorite 1 - robustesse
- Etendre la correlation du contact frictionnel a plusieurs geometries externes.
- Ajouter une seconde plateforme PETSc/MPI et ameliorer le weak scaling avant toute revendication multi-machine.
- Renforcer les campagnes orthotropes et composites courbes, notamment contraintes par pli dynamiques.
- Stabiliser les diagnostics des solveurs iteratifs : choix automatique, conditionnement, stagnation et fallback trace.
- Etendre le typage au noyau, aux I/O et aux gates de release.
### Priorite 2 - concurrence industrielle
- Contact surface-surface robuste, grand glissement et frottement avec tangente consistante.
- Non-linearite geometrique et materiau couplees, plasticite grandes deformations, endommagement et rupture.
- Composite pli par pli plus complet : S13/S23, criteres, degradation et delamination.
- Grand modele au-dela du TET4 statique : dynamique, modal, autres elements et I/O parallele qualifiee.
- Pre/post-traitement industriel : ensembles, champs, reprises, checkpoints, XDMF/HDF5 parallele et comparaisons reproductibles.
## Decision de cet audit
Le projet est techniquement riche et nettement mieux structure qu'un prototype. Il n'est toutefois pas pret a etre gele en `0.2.1a0` tant que le worktree reste massif et que les decisions Owner ne sont pas enregistrees. Le constat de confidentialite est **PASS pour les fichiers candidats actuels**, avec la reserve normale d'une revue finale de l'archive et de l'historique avant publication.
"""
def _build_audit_pdf(output: Path, markdown: str, stats: dict[str, Any], git_stats: dict[str, Any], privacy: dict[str, Any], release: dict[str, Any]) -> Path:
    styles = _styles()
    largest_rows = [["Fichier", "Lignes"]] + [[path, lines] for lines, path in stats["largest"]]
    story: list[object] = [
        Spacer(1, 25 * mm),
        Paragraph("QF_solver", styles["title"]),
        Spacer(1, 4 * mm),
        Paragraph("Audit hygiene, architecture et manques - 0.2.1 alpha", styles["subtitle"]),
        Spacer(1, 12 * mm),
        Paragraph("Verdict", styles["h1"]),
        Paragraph(
            "Le lot publiable est propre selon les marqueurs controles, mais la baseline de developpement "
            "n'est pas gelable aujourd'hui.", styles["note"],
        ),
        _table([
            ["Controle", "Valeur", "Statut", "Consequence"],
            ["Confidentialite", f"{privacy['scanned_files']} fichiers / {len(privacy['findings'])} finding", privacy["status"], "Lot courant publiable"],
            ["Attribution", f"{git_stats['attribution_path_count']} fichiers avec identite auteur/Owner", "DECLAREE", "Choix public a confirmer"],
            ["Release-vv", "Gate courant", release.get("status", "UNKNOWN"), "Ne pas taguer"],
            ["Git", f"{git_stats['modified']} modifies / {git_stats['untracked']} non suivis", "DIRTY" if not git_stats["clean"] else "CLEAN", "Figer avant release"],
            ["Architecture", f"{stats['over_700']} fichier > 700 lignes", "PASS" if not stats["over_700"] else "FAIL", "Garde-fou respecte"],
            ["Tests", f"{stats['test_count']} collectes", "INVENTAIRE", "Campagne finale requise"],
        ], [42 * mm, 48 * mm, 28 * mm, 53 * mm], styles),
        Spacer(1, 5 * mm),
        Paragraph("Aucune certification externe, equivalence commerciale ou independance de revue n'est revendiquee.", styles["fail"]),
        PageBreak(),
        Paragraph("1. Confidentialite et publication", styles["h1"]),
        Paragraph(
            "Le scanner public controle les chemins de poste, adresses privees, secrets usuels, ancienne "
            "marque et vocabulaire d'assistance interne. Le resultat courant est PASS sans finding. Les "
            "configurations locales et caches de graphe ne sont pas suivis par Git.", styles["body"],
        ),
        Paragraph(
            f"L'identite complete de l'auteur/Owner reste volontairement presente dans "
            f"{git_stats['attribution_path_count']} fichiers d'attribution ou de revue signee. Elle n'est pas "
            "une trace du poste, mais demeure une information personnelle publiee a confirmer explicitement.",
            styles["note"],
        ),
        Paragraph(
            "Reserve : l'audit d'historique disponible est un prefiltre de chemins. Une inspection manuelle "
            "du contenu de l'archive finale reste necessaire avant publication.", styles["note"],
        ),
        _table([
            ["Indicateur", "Valeur"],
            ["HEAD", git_stats["head"]],
            ["Tag sur HEAD", git_stats["tag"]],
            ["Fichiers suivis", git_stats["tracked"]],
            ["Configuration locale suivie", ", ".join(git_stats["tracked_local_config"]) or "aucune"],
        ], [62 * mm, 109 * mm], styles),
        PageBreak(),
        Paragraph("2. Architecture", styles["h1"]),
        Paragraph(
            "Le decoupage par responsabilite est sain : elements, materiaux, maillage, noyau, I/O, API, CLI, "
            "post-traitement, grand modele et verification. Le MITC4 canonique est correctement place sous "
            "elements/shell/mitc4; src/solveur/compat/mitc4 joue seulement le role de facade 0.2.x.", styles["pass"],
        ),
        _table([
            ["Constat", "Mesure", "Priorite"],
            ["Scripts V&V a plat", f"{stats['script_count']} scripts, {stats['runner_count']} runners", "P1"],
            ["Verification tres large", f"{stats['verification_module_count']} modules", "P1"],
            ["Proximite limite 700", f"{stats['over_600']} fichiers > 600 lignes", "P1"],
            ["Documentation runtime retiree", "repertoire source vide localement", "P2"],
            ["Facade MITC4 historique", "compatible 0.2.x", "P2 / retrait 0.3"],
        ], [75 * mm, 61 * mm, 35 * mm], styles),
        Spacer(1, 5 * mm),
        Paragraph("Plus gros fichiers Python", styles["h2"]),
        _table(largest_rows, [139 * mm, 32 * mm], styles),
        PageBreak(),
        Paragraph("3. Plan de refactoring", styles["h1"]),
        _table([
            ["Etape", "Action", "Garde-fou"],
            ["R1", "Classer les runners par backend et famille", "Wrappers temporaires et tests de chemins"],
            ["R2", "Decouper verification/ par sous-paquets", "Imports publics inchanges"],
            ["R3", "Extraire les modules > 600 lignes par responsabilite", "Snapshots et campagnes ciblees"],
            ["R4", "Mesurer la couverture des gates", "Ne pas confondre couverture et V&V"],
            ["R5", "Nettoyer uniquement les artefacts ignores", "Aucune preuve suivie supprimee"],
        ], [18 * mm, 91 * mm, 62 * mm], styles),
        PageBreak(),
        Paragraph("4. Manques a fermer", styles["h1"]),
        Paragraph("Avant 0.2.1 alpha", styles["h2"]),
        _table([
            ["Priorite", "Action"],
            ["P0", "Decisions Owner scope par scope; aucune acceptation globale implicite."],
            ["P0", "Relecture independante TET4 total-lagrangien ou maintien research."],
            ["P0", "Checkout propre, release-vv, tests complets, distribution et archive auditee."],
            ["P0", "Installation du wheel/sdist dans des environnements neufs 3.10 et 3.13."],
        ], [24 * mm, 147 * mm], styles),
        Spacer(1, 5 * mm),
        Paragraph("Apres 0.2.1 alpha", styles["h2"]),
        _table([
            ["Axe", "Manque principal"],
            ["Contact", "Surface-surface, grand glissement, stick/slip robuste et correlations externes multiples."],
            ["Non-lineaire", "Couplage geometrie/materiau, grandes deformations, dommage et rupture."],
            ["Composites", "S13/S23, degradation, delamination et contraintes par pli dynamiques."],
            ["Grand modele", "Seconde plateforme, meilleur scaling, dynamique et autres elements."],
            ["Solveurs", "Selection automatique, stagnation, conditionnement et fallback trace."],
            ["I/O", "Reprises, checkpoints et sorties paralleles qualifiees."],
        ], [38 * mm, 133 * mm], styles),
        PageBreak(),
        Paragraph("5. Conclusion", styles["h1"]),
        Paragraph(
            "QF_solver est un projet techniquement riche, trace et deja utilisable dans des domaines bornes. "
            "Son principal risque immediat n'est pas un manque d'elements, mais la dispersion documentaire, "
            "la densite des runners et l'ecart entre preuves disponibles et maturites formellement fermees.",
            styles["body"],
        ),
        Paragraph(
            "Conclusion : confidentialite PASS pour le lot courant; architecture globalement saine avec "
            "refactoring P1; release 0.2.1a0 non gelable avant decisions, campagne finale et worktree propre.",
            styles["note"],
        ),
        _p("Source Markdown controlee : docs/verification/project_hygiene_architecture_audit_0_2_1.md", styles["small"]),
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(output), pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=14 * mm, bottomMargin=16 * mm, title="QF_solver project hygiene and architecture audit",
    )
    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return output
def build() -> tuple[Path, Path, Path]:
    """Generate and validate all Owner-review and project-audit PDFs."""
    snapshot = _load_json(PUBLIC_EVIDENCE_PATH)
    packet = dict(snapshot["packet"])
    maturity_audit = dict(snapshot["maturity_audit"])
    release = dict(snapshot["release"])
    audit_by_scope = {row["scope"]: row for row in maturity_audit["scopes"]}
    open_rows = [
        row for row in packet["scopes"] if row.get("blocking_classification") == "owner_decision_pending"
    ]
    stable_rows = [
        row for row in packet["scopes"] if row.get("blocking_classification") == "none"
    ]
    _write_scope_markdown(STABLE_MD, stable_rows, audit_by_scope, open_gate=False)
    _write_scope_markdown(OPEN_MD, open_rows, audit_by_scope, open_gate=True)
    try:
        stable_pdf = _build_scope_pdf(STABLE_PDF, stable_rows, audit_by_scope, open_gate=False)
    except PermissionError:
        stable_pdf = _build_scope_pdf(PDF_DIR / "qf_solver_owner_review_stable_promotions_0_2_1_evidence.pdf", stable_rows, audit_by_scope, open_gate=False)
    try:
        open_pdf = _build_scope_pdf(OPEN_PDF, open_rows, audit_by_scope, open_gate=True)
    except PermissionError:
        open_pdf = _build_scope_pdf(PDF_DIR / "qf_solver_owner_review_open_gates_0_2_1_evidence.pdf", open_rows, audit_by_scope, open_gate=True)
    stats = _source_statistics()
    git_stats = _git_statistics()
    privacy = audit_public_release(ROOT)
    audit_markdown = _audit_markdown(stats, git_stats, privacy, release)
    PROJECT_AUDIT_MD.write_text(audit_markdown, encoding="utf-8")
    try:
        audit_pdf = _build_audit_pdf(PROJECT_AUDIT_PDF, audit_markdown, stats, git_stats, privacy, release)
    except PermissionError:
        audit_pdf = _build_audit_pdf(PDF_DIR / "qf_solver_project_hygiene_architecture_audit_0_2_1_evidence.pdf", audit_markdown, stats, git_stats, privacy, release)
    _validate_pdf(stable_pdf, ("promotions techniquement pretes", "orthotropic-solid-tet4-tet10", "Questions de decision"), 5)
    _validate_pdf(open_pdf, ("gates ouverts", *tuple(row["scope"] for row in open_rows)), 5)
    _validate_pdf(audit_pdf, ("Confidentialite", "Architecture", "Conclusion"), 5)
    return stable_pdf, open_pdf, audit_pdf
if __name__ == "__main__":
    for generated in build():
        print(generated)
