"""Build the controlled Owner-review PDF for the 0.2.2 alpha backend campaign."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import PageBreak, SimpleDocTemplate, Spacer
from reportlab.lib.units import mm

try:
    from scripts.owner_review_pdf_support import (
        paragraph,
        review_styles,
        review_table,
        validate_pdf,
    )
except ImportError:
    from owner_review_pdf_support import paragraph, review_styles, review_table, validate_pdf


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "qf_solver_0_2_2_alpha_backend_owner_review.pdf"


def backend_footer(canvas: Any, document: Any) -> None:
    """Draw a footer whose package version matches this review."""
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#425563"))
    canvas.drawString(
        15 * mm,
        9 * mm,
        "QF_solver 0.2.2a0 - dossier de decision - aucune certification revendiquee",
    )
    canvas.drawRightString(A4[0] - 15 * mm, 9 * mm, f"Page {document.page}")
    canvas.restoreState()


def build() -> Path:
    """Build the review PDF from the controlled revision 0.2 content."""
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    styles = review_styles()
    story = [
        paragraph("Owner review - backend numerique et scaling 0.2.2a0", styles["title"]),
        Spacer(1, 3 * mm),
        paragraph(
            "DOC-OWNER-BACKEND-022-001 | revision 0.3 | owner_accepted_with_recommendations | owner signed",
            styles["subtitle"],
        ),
        Spacer(1, 5 * mm),
        paragraph(
            "Objet : statuer sur la fermeture du gate technique backend dans un perimetre de developpement borne. Cette revue ne vaut ni decision de release, ni tag Git, ni publication PyPI.",
            styles["note"],
        ),
        paragraph(
            "La campagne agregee est PASS_BOUNDED_BACKEND_CAMPAIGN. Les resultats sont presentes avec leurs limites et ne sont pas extrapoles aux cas non executes.",
            styles["body"],
        ),
        paragraph("Identite et versioning", styles["h1"]),
        review_table(
            [
                ["Identite", "Valeur", "Role"],
                ["Package", "QF_solver 0.2.2a0", "base de code applicable"],
                ["Image d'execution", "qf-solver-large:0.2.0", "tag historique de l'environnement"],
                ["Digest image", "sha256:f2a7931d...6848a49c8", "identite immuable"],
                ["Digest de base", "sha256:2ae4bfbc...69bd56fa8", "trace de l'image"],
                ["Revision dynamique", "f5061fe5260e42582dc5f3202ccf3f626cd00ded", "revision des manifestes"],
            ],
            [35 * mm, 92 * mm, 55 * mm],
            styles,
        ),
        paragraph(
            "Le tag Docker 0.2.0 identifie l'environnement d'execution et ne constitue pas une release 0.2.0 du package. Le dossier historique results_large/qualification_matrix_free_1m est exclu : il correspond a un ancien calcul PETSc/GAMG de 1 029 000 DDL en 0.2.1a0, pas a une preuve matrix-free 1M.",
            styles["fail"],
        ),
        paragraph("Perimetre accepte", styles["h1"]),
        review_table(
            [
                ["Chemin", "Couverture executee", "Limite principale"],
                ["Statique contigu", "2 044 416 et 4 102 893 DDL; PETSc CG/GAMG/BAIJ", "une machine; pas de generalisation HPC"],
                ["Statique graphe", "2 044 416 DDL; PT-Scotch; 2 et 4 rangs", "chemin contigu reste le defaut"],
                ["Matrix-free", "107 811 DDL; CG; bloc-Jacobi nodal", "tentative 1M incomplete"],
                ["Coherence backend", "1 029 DDL; SciPy, matrix-free, PETSc", "pas de conclusion grande echelle"],
                ["Modal", "1 029 et 107 811 DDL; 3 modes; SLEPc", "modal 2M bloque par ressource"],
                ["Newmark", "2 044 416 DDL; 10 pas; dt 1e-4 s", "seuil borne 1e-5; calibration production requise"],
            ],
            [35 * mm, 91 * mm, 56 * mm],
            styles,
        ),
    ]

    story.extend(
        [
            PageBreak(),
            paragraph("Criteres quantitatifs et environnement", styles["h1"]),
            review_table(
                [
                    ["Famille", "Critere", "Resultat"],
                    ["Statique contigu", "DDL >= 2M; residu relatif <= 1e-8; efficacite forte >= 0,60", "0,651 a 2M; 0,615 a 4M : PASS"],
                    ["Statique graphe", "convergence et efficacite forte >= 0,60", "0,621 : PASS borne"],
                    ["Comparaison", "ecart de deplacement <= 1e-7", "< 1,5e-13 : PASS"],
                    ["Matrix-free", "convergence et residu observe; aucun seuil 1M", "1,104e-12 a 107811 : PASS borne"],
                    ["Modal SLEPc", "residu physique <= 1e-8", "2,789e-12 a 107811 : PASS borne"],
                    ["Newmark", "KSP 1e-8; residu physique <= 1e-5; seuil borne separe", "1,968e-6 : PASS borne, R2 fermee"],
                ],
                [35 * mm, 93 * mm, 54 * mm],
                styles,
            ),
            paragraph(
                "Environnement trace : Python 3.12.3, NumPy 2.4.6, SciPy 1.17.1, petsc4py 3.25.1, slepc4py 3.25.1, OpenBLAS 0.3.31.188.0 et OPENBLAS_NUM_THREADS=1. Le profil R1 archive le CPU visible AMD Ryzen 5 5500, 12 coeurs logiques et 46,97 GiB de memoire visible dans qualification/benchmarks/qf_solver_0_2_2_backend_campaign/runtime_profile.json. Ces valeurs sont propres au conteneur au moment du probe et ne constituent pas une generalisation de performance.",
                styles["body"],
            ),
            paragraph(
                "Les audits publics executes par scripts/audit_public_documents.py et scripts/audit_public_release.py ont inspecte 1754 fichiers et produit 0 finding. Leur revision est celle du depot ; aucun numero de version independant n'est revendique.",
                styles["body"],
            ),
            paragraph(
                "La regression locale utilise Python 3.13.1, pytest 8.4.1 et SciPy 1.15.2. Les 107 tests deselected viennent du filtre explicite -m not benchmark and not large and not evidence : ce sont les campagnes longues, benchmarks et evidences exclus de la regression rapide, pas des echecs masques.",
                styles["body"],
            ),
            paragraph("Resultats echoues ou incomplets", styles["h1"]),
            review_table(
                [
                    ["Test", "Tentative", "Cause, observable et verdict"],
                    ["Modal SLEPc 2M", "Oui; 3 modes; 2 rangs", "signal 9 pendant shift-invert; environ 33,5 GiB; BLOCKED_RESOURCE_LIMIT, pas PASS"],
                    ["Matrix-free 1M", "Oui; timeout 900 s", "31 points telemetry a 30 s; RSS proche de 293,95 MiB; aucun resume ni residu; BLOCKED_TIMEOUT"],
                ],
                [34 * mm, 47 * mm, 101 * mm],
                styles,
            ),
            paragraph(
                "La relance matrix-free 1M n'est pas qualifiee de FAIL numerique : le timeout controle n'a montre aucune divergence, mais aucun resume solveur ni residu final n'a ete produit. Le dossier R3 conserve le timeout, la telemetry et le journal du runner.",
                styles["fail"],
            ),
        ]
    )

    story.extend(
        [
            PageBreak(),
            paragraph("Resultats, architecture et synthese Go/No-Go", styles["h1"]),
            review_table(
                [
                    ["Campagne", "Mesure observee", "Statut"],
                    ["PETSc contigu", "efficacites 0,651 et 0,615; residus converges", "PASS borne"],
                    ["PETSc graphe/PT-Scotch", "efficacite 0,621; manifestes PASS", "PASS borne"],
                    ["Matrix-free", "residu relatif 1,104e-12 a 107811 DDL", "PASS borne"],
                    ["Comparaison backend", "ecarts 1,087e-13 et 1,417e-13 vs SciPy", "PASS"],
                    ["Modal SLEPc", "residu maximal 2,789e-12 a 107811 DDL", "PASS borne"],
                    ["Newmark PETSc/GAMG", "10 pas; 222 iterations; residu max 1,968e-6", "PASS borne; R2 fermee sous 1e-5"],
                ],
                [38 * mm, 99 * mm, 45 * mm],
                styles,
            ),
            paragraph("Architecture du chemin graphe", styles["h1"]),
            paragraph(
                "Le chemin PT-Scotch est relie a src/solveur/large/partitioning.py et appele depuis src/solveur/large/distributed_model.py. Les manifestes conservent la commande --partition-strategy graph --graph-partitioner ptscotch, le nombre de rangs et la strategie. La reference d'architecture est docs/architecture.md, completee par le plan V&V multi-million.",
                styles["body"],
            ),
            paragraph("Synthese pre-decision", styles["h1"]),
            paragraph(
                "GO technique borne : les chemins statique, graphe, comparaison, matrix-free intermediaire, modal intermediaire et Newmark ont des resultats exploitables, avec sept manifestes verifies. R2 dynamique fermee pour le gate borne : residu Newmark 1,968e-6 sous le seuil 1e-5 ; calibration production a maintenir. NO-GO pour toute extrapolation : modal 2M bloque par ressource et matrix-free 1M bloque par timeout controle. RISQUE principal : la campagne ne couvre qu'une machine, une image et une topologie non demontree.",
                styles["pass"],
            ),
            paragraph(
                "Decision Owner enregistree : accepted_with_recommendations. La condition R1 de Q8 est fermee par l'addendum de profil (slepc4py 3.25.1, AMD Ryzen 5 5500, 12 coeurs logiques, 46,97 GiB visibles). La confirmation Owner est enregistree le 2026-08-23. Cette decision ne vaut ni stable, ni release, ni publication.",
                styles["note"],
            ),
            paragraph("Recommandations ouvertes avant archivage final", styles["h2"]),
            paragraph(
                "1. R1 FERMEE : version slepc4py et profil CPU/RAM archives dans runtime_profile.json.\n2. R2 FERMEE pour le gate borne : seuil Newmark 1e-5 ; calibration par domaine avant production.\n3. R3 EXECUTEE : matrix-free 1M bloque par timeout 900 s, avec telemetry ; poursuivre en v0.3.0 avec une strategie de performance dediee.\n4. R4 v0.3.0 : ne pas presenter le modal 2M comme PASS tant qu'une strategie de memoire ou une configuration adaptee n'est pas documentee.",
                styles["body"],
            ),
        ]
    )

    story.extend(
        [
            PageBreak(),
            paragraph("Questions Owner - Q1 a Q5", styles["h1"]),
            paragraph(
                "Repondre OUI, NON ou CONDITIONNELLEMENT. Une reponse conditionnelle doit preciser la condition. Les questions portent uniquement sur le gate backend borne.",
                styles["note"],
            ),
            paragraph("Q1 - Fermeture du gate technique", styles["h2"]),
            paragraph(
                "Acceptez-vous de fermer le gate backend uniquement pour le perimetre numerique explicitement liste, avec ses seuils et exclusions ?\nReponse : OUI / NON / CONDITIONNELLEMENT.",
                styles["body"],
            ),
            paragraph("Reponse Owner : OUI - perimetre clair, exclusions assumees.", styles["pass"]),
            paragraph("Q2 - Scalabilite statique contigue", styles["h2"]),
            paragraph(
                "Acceptez-vous la preuve statique jusqu'a 2 044 416 et 4 102 893 DDL sur architecture contigue, avec residu relatif <= 1e-8, efficacite forte >= 0,60 a 2 et 4 rangs, une seule machine et une seule image ?\nReponse : OUI / NON / CONDITIONNELLEMENT.",
                styles["body"],
            ),
            paragraph("Reponse Owner : CONDITIONNELLEMENT - efficacites 0,651 et 0,615 superieures a 0,60; verifier le calcul.", styles["pass"]),
            paragraph("Q3 - Partitionnement PT-Scotch", styles["h2"]),
            paragraph(
                "Acceptez-vous le chemin graphe comme preuve bornee, avec efficacite 0,621, commande PT-Scotch tracee dans les manifestes et chemin contigu conserve comme defaut ?\nReponse : OUI / NON / CONDITIONNELLEMENT.",
                styles["body"],
            ),
            paragraph("Reponse Owner : OUI - PT-Scotch accepte et chemin optionnel.", styles["pass"]),
            paragraph("Q4 - Matrix-free et coherence backend", styles["h2"]),
            paragraph(
                "Acceptez-vous la coherence SciPy/matrix-free/PETSc sur 1 029 DDL (ecarts <= 1e-7) et la preuve matrix-free a 107 811 DDL (residu 1,104e-12), sans revendiquer la relance matrix-free 1M bloquee par timeout ?\nReponse : OUI / NON / CONDITIONNELLEMENT.",
                styles["body"],
            ),
            paragraph("Reponse Owner : CONDITIONNELLEMENT - coherence validee; relance 1M executee et classee BLOCKED_TIMEOUT, sans PASS.", styles["pass"]),
            paragraph("Q5 - Modal SLEPc", styles["h2"]),
            paragraph(
                "Acceptez-vous le modal SLEPc jusqu'a 107 811 DDL, trois modes et residu 2,789e-12 pour une tolerance configuree 1e-8, sans couverture modale 2M ?\nReponse : OUI / NON / CONDITIONNELLEMENT.",
                styles["body"],
            ),
            paragraph("Reponse Owner : CONDITIONNELLEMENT - modal accepte jusqu'a 107k DDL; 2M reste inconnu et hors revendication.", styles["pass"]),
        ]
    )

    story.extend(
        [
            PageBreak(),
            paragraph("Questions Owner - Q6 a Q9 et signature", styles["h1"]),
            paragraph("Q6 - Newmark", styles["h2"]),
            paragraph(
                "Acceptez-vous la preuve Newmark a 2 044 416 DDL, dix pas et 222 iterations, avec residu physique relatif maximal 1,968e-6 et seuil borne 1e-5 pour cette observable ?\nReponse : OUI / NON / CONDITIONNELLEMENT.",
                styles["body"],
            ),
            paragraph("Reponse Owner : CONDITIONNELLEMENT - seuil borne 1e-5 defini et respecte; calibration production a maintenir.", styles["pass"]),
            paragraph("Q7 - Echecs et limites", styles["h2"]),
            paragraph(
                "Acceptez-vous de classer le modal 2M comme BLOCKED_RESOURCE_LIMIT et le matrix-free 1M comme BLOCKED_TIMEOUT, plutot que de les presenter comme des PASS ou des echecs numeriques ?\nReponse : OUI / NON / CONDITIONNELLEMENT.",
                styles["body"],
            ),
            paragraph("Reponse Owner : OUI - classification honnete, BLOCKED_RESOURCE_LIMIT et BLOCKED_TIMEOUT, pas FAIL numerique.", styles["pass"]),
            paragraph("Q8 - Environnement et tracabilite", styles["h2"]),
            paragraph(
                "Acceptez-vous l'archivage avec package 0.2.2a0, image d'execution taguee 0.2.0 mais epinglee par digest, versions PETSc/SciPy/SLEPc capturees, profil hardware archive, et 107 tests exclus par filtre explicite ?\nReponse : OUI / NON / CONDITIONNELLEMENT.",
                styles["body"],
            ),
            paragraph("Reponse Owner : CONDITIONNELLEMENT - R1 est maintenant satisfaite par l'addendum de profil ; confirmation Owner enregistree le 2026-08-23.", styles["pass"]),
            paragraph("Q9 - Decision Owner", styles["h2"]),
            paragraph(
                "Choisir une seule decision pour le gate backend, sans promotion stable :\naccepted_with_recommendations / accepted_for_bounded_engineering_use / more_evidence_required\n\nDecision Owner : accepted_with_recommendations",
                styles["body"],
            ),
            paragraph("Commentaire Owner :", styles["h2"]),
            paragraph(
                "R1 FERMEE : slepc4py et le profil CPU/RAM sont archives dans runtime_profile.json. R2 FERMEE pour le gate borne : seuil Newmark 1e-5, calibration production requise.\nR3 EXECUTEE : matrix-free 1M bloque par timeout 900 s avec telemetry. R4 v0.3.0 : strategie memoire modal 2M ou limite 107k documentee.",
                styles["body"],
            ),
            Spacer(1, 4 * mm),
            paragraph("Signature Owner : Owner - confirmation explicite enregistree    Date : 2026-08-23", styles["body"]),
            Spacer(1, 5 * mm),
            paragraph(
                "Rappel : une reponse favorable ferme uniquement le gate technique borne. Elle ne vaut ni qualification stable, ni decision de release, ni autorisation de publication.",
                styles["note"],
            ),
        ]
    )

    document = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=13 * mm,
        bottomMargin=15 * mm,
        title="QF_solver 0.2.2a0 backend Owner review",
        author="QF_solver",
    )
    document.build(story, onFirstPage=backend_footer, onLaterPages=backend_footer)
    validate_pdf(OUTPUT, ["0.2.2a0", "BLOCKED_RESOURCE_LIMIT", "Q9"], 5)
    return OUTPUT


if __name__ == "__main__":
    print(build())
