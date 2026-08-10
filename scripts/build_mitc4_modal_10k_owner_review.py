"""Build the owner-review Markdown and PDF for the 10k MITC4 modal run."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from solveur.verification.mitc4_laminate_dynamic import Mitc4LaminateDynamicStudy


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "VNV-MITC4-LAMINATE-MODAL-10K-CODEASTER-023-20260809"
PDF_DIR = ROOT / "output" / "pdf"
STUDY_ID = "VNV-MITC4-LAMINATE-MODAL-10K-CODEASTER-023"


ATTEMPTS = [
    ("eigh", "Refuse proprement : 51 000 ddl libres au-dessus de la limite dense 6 000.", "bloque"),
    ("eigsh shift-invert", "Factorisation sparse K consommee : MemoryError.", "bloque memoire"),
    ("eigsh SM + condensation lazy", "10 001 iterations, 0/4 vecteurs converges.", "non converge"),
    ("LOBPCG diagonal", "Residuel relatif final environ 1.167e-2 apres 10 000 iterations.", "echec"),
    ("LOBPCG spilu", "Preconditionnement non exploitable sur ce bloc : residuel environ 8.786e-1.", "echec"),
    ("LOBPCG SSOR", "Residuel relatif final environ 7.461e-6 apres 10 000 iterations.", "insuffisant"),
    ("LOBPCG SSOR 30k", "Residuel relatif final environ 7.383e-6 apres 30 000 iterations.", "insuffisant"),
]


def _load_reference() -> dict[str, object]:
    path = RESULTS / "code_aster_reference_summary.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _make_figures() -> dict[str, Path]:
    study = Mitc4LaminateDynamicStudy(mesh=(200, 50), layup=(45.0, -45.0, -45.0, 45.0))
    _, nodes = study.build_model()
    mesh_path = RESULTS / "mitc4_laminate_modal_10k_mesh.png"
    figure, axis = plt.subplots(figsize=(9.0, 3.8))
    for row in range(0, 51, 5):
        start = row * 201
        stop = start + 201
        axis.plot(nodes[start:stop, 0], nodes[start:stop, 1], color="#0072B2", linewidth=0.35)
    for column in range(0, 201, 10):
        axis.plot(nodes[column::201, 0], nodes[column::201, 1], color="#D55E00", linewidth=0.35)
    axis.set(xlabel="x [m]", ylabel="y [m]", title="MITC4 multicouche : maillage 200 x 50")
    axis.set_aspect("equal")
    axis.grid(alpha=0.2)
    figure.tight_layout()
    figure.savefig(mesh_path, dpi=200)
    plt.close(figure)

    reference = np.asarray(_load_reference()["code_aster_frequencies_hz"], dtype=float)
    frequency_path = RESULTS / "mitc4_laminate_modal_10k_code_aster_reference.png"
    figure, axis = plt.subplots(figsize=(8.0, 4.4))
    axis.bar(np.arange(1, len(reference) + 1), reference, color="#D55E00", alpha=0.9)
    axis.set(xlabel="Mode", ylabel="Frequence [Hz]", title="Reference Code_Aster sur 10 000 QUAD4")
    axis.grid(axis="y", alpha=0.25)
    figure.tight_layout()
    figure.savefig(frequency_path, dpi=200)
    plt.close(figure)

    convergence_path = RESULTS / "mitc4_laminate_modal_convergence_context.png"
    counts = np.asarray([36, 72, 144, 144], dtype=float)
    errors = np.asarray([5.528, 1.585, 1.771, 4.693], dtype=float)
    labels = ["36", "72", "144 eq.", "144 dir."]
    figure, axis = plt.subplots(figsize=(8.0, 4.4))
    axis.semilogx(counts, errors, "o-", color="#0072B2", label="QF_solver historique")
    for x, y, label in zip(counts, errors, labels):
        axis.annotate(label, (x, y), textcoords="offset points", xytext=(4, 5), fontsize=8)
    axis.axhline(10.0, color="#009E73", linestyle="--", label="seuil 10 %")
    axis.set(xlabel="Nombre de QUAD4", ylabel="Ecart modal relatif [%]", title="Contexte de convergence existant")
    axis.grid(alpha=0.25)
    axis.legend()
    figure.tight_layout()
    figure.savefig(convergence_path, dpi=200)
    plt.close(figure)
    return {"mesh": mesh_path, "frequency": frequency_path, "convergence": convergence_path}


def _markdown(reference: dict[str, object], figures: dict[str, Path]) -> str:
    frequencies = reference["code_aster_frequencies_hz"]
    lines = [
        f"---\ndoc_id: DOC-VNV-{STUDY_ID}\nrevision: 0.1\nstatus: ready_for_owner_review\nreview_mode: owner_review\nreviewer: Quentin Farinazzo\nreview_date: 2026-08-09\n---",
        "",
        "# Owner review - MITC4 multicouche modal a 10 000 QUAD4",
        "",
        "> **Verdict actuel : NON CLOTURE.** La reference Code_Aster est disponible, mais aucun calcul modal QF_solver n'a atteint le residu requis sur ce maillage. Il n'y a donc pas de correlation externe mode par mode.",
        "",
        "## 1. Objet et perimetre",
        "",
        "Cette campagne examine l'empilement `[45/-45/-45/45]` sur une plaque cantilever plane MITC4. Le maillage est `200 x 50`, soit `10 000` QUAD4 et environ `51 000` ddl libres apres blocage de l'encastrement. Le calcul demande les quatre premiers modes propres.",
        "",
        "Le cas reste dans le domaine lineaire, avec masse coherente et condensation exacte lazy des ddl de drilling. Il ne couvre ni dommage, ni delaminage, ni grandes deformations, ni coque courbe.",
        "",
        "## 2. Geometrie, maillage, blocage et chargement",
        "",
        "La plaque mesure `1.0 m x 0.2 m`. Le bord `x=0` est bloque sur `UX, UY, UZ, RX, RY, RZ`. Il s'agit d'une analyse modale sans chargement statique applique. Le fichier de maillage ASTER et le fichier de commande sont conserves dans le dossier de resultats.",
        "",
        f"![Maillage MITC4 10k]({figures['mesh'].name})",
        "",
        "## 3. Reference Code_Aster",
        "",
        "Code_Aster 18.1.0, image Docker epinglee, a calcule les quatre frequences avant son controle a posteriori. La sortie contient ensuite une alarme sur le mode 3 ; cette alarme est conservee dans `code_aster_stdout.log` et interdit de presenter cette execution comme une preuve externe parfaite.",
        "",
        "| Mode | Frequence Code_Aster [Hz] |",
        "| ---: | ---: |",
    ]
    for index, value in enumerate(frequencies, start=1):
        lines.append(f"| {index} | `{float(value):.8e}` |")
    lines.extend(
        [
            "",
            f"![Frequences Code_Aster]({figures['frequency'].name})",
            "",
            "## 4. Essais QF_solver et diagnostic",
            "",
            "Le seuil de residu modal demande est `1e-7`. Les essais suivants ont ete executes sur le chemin QF_solver ; aucun n'a produit quatre modes acceptables sur 10k elements.",
            "",
            "| Methode | Observation | Etat |",
            "| --- | --- | --- |",
        ]
    )
    for method, observation, status in ATTEMPTS:
        lines.append(f"| `{method}` | {observation} | **{status}** |")
    lines.extend(
        [
            "",
            "La condensation lazy a reduit l'empreinte de travail observee d'environ `5.3 GB` a environ `267 MB` lors de l'attaque `eigsh`, mais elle n'a pas resolu le probleme spectral. Le plateau LOBPCG SSOR autour de `7.38e-6` montre une limite du preconditionnement actuel, pas une preuve de defaillance de la formulation MITC4.",
            "",
            f"![Contexte de convergence historique]({figures['convergence'].name})",
            "",
            "## 5. Comparaison des modes",
            "",
            "La comparaison mode par mode QF_solver / Code_Aster est **non executable** pour cette campagne : la colonne QF_solver est absente car les vecteurs propres n'ont pas passe le critere de residu. Les frequences Code_Aster ci-dessus sont une reference externe seule et ne permettent pas de calculer un ecart relatif honnête.",
            "",
            "Le cas equilibre a `144` elements reste disponible dans la campagne precedente, avec un ecart modal QF_solver / Code_Aster de `1.771 %` pour ce meme empilement. Cette valeur ne doit pas etre extrapolee au maillage 10k.",
            "",
            "## 6. Decision Owner proposee",
            "",
            "- Statut de la campagne 10k : `more_evidence_required`.",
            "- La reference Code_Aster est archivee et reproductible avec Docker.",
            "- La preuve externe modal MITC4 multicouche a 10k elements reste ouverte.",
            "- Le perimetre modal precedent peut rester utilisable dans ses bornes documentees ; cette campagne lourde ne doit pas etre declaree PASS.",
            "",
            "## 7. Action de cloture recommandee",
            "",
            "Remplacer le backend spectral SciPy actuel par un chemin scalable de type PETSc/SLEPc ou un preconditionneur AMG adapte a la condensation des rotations de drilling. Rejouer ensuite exactement ce cas, verifier les quatre residus, les orthogonalites de masse et de raideur, puis seulement calculer les ecarts mode par mode.",
            "",
            "Aucune relaxation du seuil `1e-7` n'est recommandee pour fermer cette preuve.",
            "",
            "## 8. Artefacts",
            "",
            "- `code_aster_reference_summary.json` : frequences et version de reference ;",
            "- `code_aster_stdout.log` : sortie complete et alarme du mode 3 ;",
            "- `mitc4_laminate_modal_10k.mail` / `.comm` : maillage et commande Code_Aster ;",
            "- `mitc4_laminate_modal_10k_mesh.png` : maillage ;",
            "- `mitc4_laminate_modal_10k_code_aster_reference.png` : reference frequences ;",
            "- `mitc4_laminate_modal_convergence_context.png` : historique de convergence QF_solver ;",
            "- `qf_solver_mitc4_laminate_modal_10k_owner_review.pdf` : version PDF de cette revue.",
            "",
            "Cette note ne constitue pas une certification externe.",
        ]
    )
    return "\n".join(lines) + "\n"


def _pdf(path: Path, reference: dict[str, object], figures: dict[str, Path]) -> None:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    styles = getSampleStyleSheet()
    styles["Title"].alignment = TA_CENTER
    styles["BodyText"].leading = 13
    styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=8, leading=10))
    story = [
        Paragraph("QF_solver - Owner review MITC4 multicouche modal 10 000 QUAD4", styles["Title"]),
        Spacer(1, 0.25 * cm),
        Paragraph("DOC-VNV-VNV-MITC4-LAMINATE-MODAL-10K-CODEASTER-023 | Revision 0.1 | 2026-08-09", styles["Small"]),
        Spacer(1, 0.35 * cm),
        Paragraph("VERDICT : NON CLOTURE. Code_Aster a fourni une reference, mais le calcul QF_solver n'a pas atteint le residu modal requis. La correlation mode par mode n'est pas executable.", styles["BodyText"]),
        Spacer(1, 0.25 * cm),
        Paragraph("Perimetre", styles["Heading2"]),
        Paragraph("Empilement [45/-45/-45/45], plaque plane cantilever 1.0 x 0.2 m, maillage 200 x 50 = 10 000 QUAD4, environ 51 000 ddl libres, masse coherente, drilling condense, quatre premiers modes.", styles["BodyText"]),
        Spacer(1, 0.2 * cm),
        Image(str(figures["mesh"]), width=17 * cm, height=7.2 * cm),
        Spacer(1, 0.1 * cm),
        Paragraph("Le bord x=0 est bloque sur les six ddl. Aucun chargement statique n'est applique pour l'analyse modale.", styles["Small"]),
        Spacer(1, 0.25 * cm),
        Paragraph("Reference Code_Aster", styles["Heading2"]),
    ]
    reference_rows = [["Mode", "Frequence [Hz]"]]
    for index, value in enumerate(reference["code_aster_frequencies_hz"], start=1):
        reference_rows.append([str(index), f"{float(value):.8e}"])
    table = Table(reference_rows, colWidths=[3 * cm, 6 * cm])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D55E00")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), 0.4, colors.grey), ("ALIGN", (0, 0), (-1, -1), "RIGHT")]))
    story.extend([table, Spacer(1, 0.2 * cm), Image(str(figures["frequency"]), width=15.5 * cm, height=8.5 * cm), Spacer(1, 0.2 * cm)])
    story.extend(
        [
            Paragraph("Essais QF_solver", styles["Heading2"]),
            Paragraph("eigh : limite dense depassee. eigsh shift-invert : MemoryError pendant la factorisation. eigsh SM + condensation lazy : 10 001 iterations sans mode converge. LOBPCG diagonal : residu environ 1.167e-2. LOBPCG spilu : residu environ 8.786e-1. LOBPCG SSOR : plateau environ 7.383e-6 apres 30 000 iterations, au-dessus de 1e-7.", styles["BodyText"]),
            Spacer(1, 0.15 * cm),
            Paragraph("L'optimisation lazy a reduit l'empreinte observee d'environ 5.3 GB a 267 MB, mais le preconditionnement reste insuffisant.", styles["BodyText"]),
            Spacer(1, 0.15 * cm),
            Image(str(figures["convergence"]), width=15.5 * cm, height=8.5 * cm),
            Spacer(1, 0.2 * cm),
            Paragraph("Decision proposee", styles["Heading2"]),
            Paragraph("more_evidence_required. La reference Code_Aster est archivee ; aucune conclusion de correlation externe ni fermeture de la preuve 10k n'est prononcee. La prochaine action est un backend spectral scalable PETSc/SLEPc ou AMG, puis une relance avec residus et orthogonalites verifies.", styles["BodyText"]),
            Spacer(1, 0.2 * cm),
            Paragraph("Limites : pas de dommage, delaminage, rupture, grandes deformations, coque courbe ou calibration experimentale. Cette revue ne constitue pas une certification externe.", styles["Small"]),
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    SimpleDocTemplate(str(path), pagesize=A4, rightMargin=1.4 * cm, leftMargin=1.4 * cm, topMargin=1.3 * cm, bottomMargin=1.3 * cm).build(story)


def main() -> int:
    RESULTS.mkdir(parents=True, exist_ok=True)
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    reference = _load_reference()
    figures = _make_figures()
    markdown_path = RESULTS / "owner_review_modal_10k.md"
    pdf_path = PDF_DIR / "qf_solver_mitc4_laminate_modal_10k_owner_review.pdf"
    markdown_path.write_text(_markdown(reference, figures), encoding="utf-8")
    _pdf(pdf_path, reference, figures)
    manifest = {
        "study_id": STUDY_ID,
        "status": "ready_for_owner_review",
        "markdown": markdown_path.name,
        "pdf": str(pdf_path.relative_to(ROOT)),
        "sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in [markdown_path, pdf_path]},
    }
    (RESULTS / "owner_review_modal_10k_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(markdown_path)
    print(pdf_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
