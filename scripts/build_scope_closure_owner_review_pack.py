"""Build the pending Owner Review pack from archived evidence only."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer
try:
    from scripts.owner_review_pdf_support import (
        review_footer,
        review_image,
        review_styles,
        review_table,
        validate_pdf,
    )
except ModuleNotFoundError:
    from owner_review_pdf_support import (
        review_footer,
        review_image,
        review_styles,
        review_table,
        validate_pdf,
    )
ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output" / "pdf"
DOC_DIR = ROOT / "docs" / "verification"
REVIEW_DIR = ROOT / "qualification" / "reviews"
PDF_PATH = OUTPUT_DIR / "qf_solver_owner_review_scope_closure_2026-08-21.pdf"
MD_PATH = DOC_DIR / "owner_review_scope_closure_2026-08-21.md"
JSON_PATH = REVIEW_DIR / "owner_review_scope_closure_2026-08-21.json"
TMP_DIR = ROOT / "tmp" / "pdfs" / "scope_closure_owner_review"
def _metric(name: str, value: str, limit: str, status: str = "PASS") -> dict[str, str]:
    return {"name": name, "value": value, "limit": limit, "status": status}
def _scope(
    scope: str,
    title: str,
    current: str,
    target: str,
    technical: str,
    proposal: str,
    summary: str,
    metrics: list[dict[str, str]],
    questions: list[str],
    limitations: list[str],
    evidence: list[str],
    images: list[str],
    blocker: str = "",
) -> dict[str, Any]:
    return {
        "scope": scope,
        "title": title,
        "current_status": current,
        "target_status": target,
        "technical_status": technical,
        "proposed_decision": proposal,
        "summary": summary,
        "metrics": metrics,
        "questions": questions,
        "limitations": limitations,
        "evidence": evidence,
        "images": images,
        "blocker": blocker,
        "owner_decision": None,
        "owner_comment": "",
        "owner_name": "",
        "owner_date": "",
    }
COMMON_LIMITS = [
    "Aucune revendication de certification externe.",
    "La decision doit rester limitee aux preuves et aux observables listes.",
    "Dommage, rupture et delamination restent hors scope sauf mention contraire.",
]
SCOPES: list[dict[str, Any]] = [
    _scope(
        "mitc3-laminate-static",
        "MITC3 multicouche statique plane",
        "verified_development_external_correlation",
        "owner_accepted",
        "PASS_EXTERNAL_CORRELATION",
        "accepted_for_bounded_engineering_use",
        "Patch membrane plan [0/90/90/0] compare a CalculiX S6 COMPOSITE. La preuve porte sur les contraintes dans les axes materiau et non sur une coque courbe.",
        [
            _metric("Ecart L2 contraintes par pli fin", "0,09625 %", "2 %"),
            _metric("Erreur patch affine QF_solver", "2,278e-13", "1e-10"),
            _metric("Dernier increment CalculiX", "0,07313 %", "0,2 %"),
        ],
        [
            "Q1 : Les preuves et le maillage 4x1 -> 8x2 -> 16x4 couvrent-ils le domaine plane declare ?",
            "Q2 : Les observables S11/S22/S12 par pli sont-ils suffisants pour ce domaine ?",
            "Q3 : Les exclusions S13/S23, bords libres, dommage et delamination sont-elles acceptees ?",
            "Q4 : Decision Owner : accepted_for_bounded_engineering_use, accepted_with_recommendations ou more_evidence_required ?",
        ],
        COMMON_LIMITS + [
            "Une seule geometrie plane et un seul empilement symetrique sont compares.",
            "MITC3+ et CalculiX S6 ne sont pas la meme formulation elementaire.",
        ],
        [
            "docs/verification/mitc3_laminate_dynamic.md",
            "qualification/maturity_evidence_0_2_1/mitc3_laminate_static_campaign/summary.json",
            "qualification/vnv/external/calculix_mitc3_laminate_ply_stress/reference/",
        ],
        ["qualification/maturity_evidence_0_2_1/mitc3_laminate_static_campaign/mitc3_laminate_ply_stress_calculix.png"],
    ),
    _scope(
        "mitc3-laminate-dynamic-thin-planar",
        "MITC3 multicouche dynamique mince plane",
        "verified_development_external_correlation",
        "stable (sous-perimetre mince plane uniquement)",
        "PASS_EXTERNAL_CORRELATION_DKT",
        "stable",
        "La campagne DKT de Code_Aster fournit une reference de limite mince sur le meme stratife [0/90/90/0]. Elle est distincte de la comparaison DST, qui reste un diagnostic de difference de formulation.",
        [
            _metric("Erreur modale fine 24x6", "0,3940 %", "1 %"),
            _metric("Erreur RMS Newmark fine", "0,1968 %", "1 %"),
            _metric("Erreur harmonique fine", "0,0880 %", "1 %"),
            _metric("Residu modal fin", "1,08e-08", "1e-07"),
        ],
        [
            "Q1 : Le domaine mince, symetrique et plan est-il suffisamment delimite ?",
            "Q2 : Les erreurs fines 0,3940 %, 0,1968 % et 0,0880 % sont-elles acceptees ?",
            "Q3 : Les niveaux intermediaires depassant parfois 1 % doivent-ils rester publies comme diagnostics ?",
            "Q4 : DKT est-il accepte comme oracle de limite mince sans pretendre a une identite MITC3/DKT ?",
            "Q5 : Decision Owner pour le sous-perimetre mince plane ?",
        ],
        COMMON_LIMITS + [
            "Coques epaisses, courbes, non symetriques, couplage B non nul et amortissement calibre exclus.",
            "La decision ne s'etend pas aux contraintes dynamiques par pli.",
        ],
        [
            "docs/verification/mitc3_laminate_dynamic_dkt_thin_owner_review.md",
            "qualification/vnv/external/code_aster_mitc3_laminate_dynamic_refinement_dkt_2026-08-21/reference/summary.json",
            "qualification/vnv/mitc3_laminate_temporal_refinement_2026-08-21/summary.json",
        ],
        ["qualification/vnv/external/code_aster_mitc3_laminate_dynamic_refinement_dkt_2026-08-21/reference/mitc3_laminate_dynamic_refinement.png"],
        "La promotion depend d'une decision Owner ; aucune promotion automatique ne doit etre deduite du PASS technique.",
    ),
    _scope(
        "mitc3-laminate-static-curved-mixed-transverse",
        "MITC3 multicouche courbe : mixte et transverse",
        "owner_accepted_experimental_bounded_use",
        "stable (sous-perimetre mixte/transverse borne)",
        "PASS_WITH_AXIAL_EXCLUSION",
        "stable",
        "Panneau cylindrique facettise, axes materiau projetes par facette et empilement [0/90/90/0]. Le sous-perimetre ne revendique pas le chargement axial.",
        [
            _metric("Ecart mixte QF / Code_Aster", "0,5780 %", "1 %"),
            _metric("Ecart transverse QF / Code_Aster", "0,4975 %", "1 %"),
            _metric("Increment mixte final", "4,4755 %", "5 %"),
            _metric("Increment transverse final", "4,6023 %", "5 %"),
        ],
        [
            "Q1 : La geometrie, l'orientation projetee et l'empilement sont-ils assez definis ?",
            "Q2 : Les deux familles mixte et transverse sous 1 % sont-elles suffisantes pour ce sous-perimetre ?",
            "Q3 : L'exclusion axiale est-elle acceptee sans extrapolation ?",
            "Q4 : Les exclusions S13/S23, singularites, dommage et delamination sont-elles acceptees ?",
            "Q5 : Decision Owner : stable ou accepted_with_recommendations ?",
        ],
        COMMON_LIMITS + [
            "La preuve est limitee a une geometrie facettisee et un empilement.",
            "Le chargement axial n'est pas inclus dans ce sous-perimetre.",
        ],
        [
            "docs/verification/mitc3_laminate_curved_mixed_transverse_stable_owner_review.md",
            "qualification/maturity_evidence_0_2_1/mitc3_laminate_curved_load_families/summary.json",
            "qualification/vnv/external/code_aster_mitc3_curved_laminate_refinement_027/reference/",
        ],
        ["qualification/maturity_evidence_0_2_1/mitc3_laminate_curved_load_families/curved_laminate_deformation_qf_code_aster.png"],
        "Le sous-perimetre axial reste separe et bloque.",
    ),
    _scope(
        "mitc3-laminate-static-curved",
        "MITC3 multicouche courbe : domaine axial complet",
        "owner_accepted_experimental_bounded_use",
        "accepted_for_bounded_engineering_use (pas stable)",
        "BLOCKED_EXTERNAL_COMPARABILITY",
        "accepted_for_bounded_engineering_use",
        "Le cas axial est sous 1 % face a Code_Aster a 64x32, mais l'increment axial depasse 5 % et les references Code_Aster/CalculiX divergent. Le raffinement seul ne justifie pas une promotion stable.",
        [
            _metric("Ecart axial QF / Code_Aster a 64x32", "0,9066 %", "1 %"),
            _metric("Increment QF axial 48x24 -> 64x32", "8,2619 %", "5 %", "FAIL"),
            _metric("Ecart QF / CalculiX S6 a 64x32", "6,420 %", "1 %", "FAIL"),
            _metric("Ecart Code_Aster / CalculiX", "7,591 %", "information", "WARNING"),
        ],
        [
            "Q1 : Le panneau axial peut-il etre accepte uniquement comme usage borne ?",
            "Q2 : L'increment axial et la dispersion des oracles interdisent-ils une promotion stable ?",
            "Q3 : Une seconde geometrie ou une reference de meme ordre doit-elle rester obligatoire ?",
            "Q4 : Decision Owner : accepted_for_bounded_engineering_use ou more_evidence_required ?",
        ],
        COMMON_LIMITS + [
            "La comparaison statique est sensible a la formulation externe DST/S6.",
            "Dynamique courbe, autres empilements et contraintes par pli d'acceptation exclus.",
        ],
        [
            "docs/verification/mitc3_laminate_curved_stable_owner_review.md",
            "qualification/vnv/external/mitc3_curved_axial_reference_audit_2026-08-21/",
            "qualification/vnv/external/calculix_mitc3_curved_laminate_axial_2026-08-21/reference/",
        ],
        ["qualification/maturity_evidence_0_2_1/mitc3_laminate_curved_load_families/convergence_qf_code_aster.png"],
        "Gate technique bloque par l'increment axial et la comparabilite externe.",
    ),
    _scope(
        "tet4-total-lagrangian-structural-v2",
        "TET4 total-lagrangien structurel",
        "owner_accepted / research",
        "experimental borne (pas stable)",
        "PASS_WITH_INDEPENDENT_REVIEW_REQUIRED",
        "more_evidence_required",
        "Green-Lagrange, PK2/Cauchy, imperfection et flambement sont verifies jusqu'a 98 304 TET4. L'accord CalculiX est excellent, mais la revue independante et le post-flambement restent ouverts.",
        [
            _metric("Erreur Euler h5, 98 304 TET4", "1,896 %", "information", "WARNING"),
            _metric("Ecart QF / CalculiX h5", "0,0343 %", "1 %"),
            _metric("Erreur PK2 Code_Aster", "8,54e-5", "1e-3"),
            _metric("Erreur Cauchy CalculiX", "1,17e-7", "1e-3"),
        ],
        [
            "Q1 : Les preuves couvrent-elles le flambement pre-critique et la charge critique dans le domaine declare ?",
            "Q2 : Les trois imperfections et la limite de 98 304 TET4 sont-elles acceptees ?",
            "Q3 : La revue independante doit-elle rester obligatoire avant toute maturite superieure ?",
            "Q4 : Les exclusions pression suiveuse, contact, rupture et post-flambement complet sont-elles acceptees ?",
            "Q5 : Decision Owner : experimental borne ou more_evidence_required ?",
        ],
        COMMON_LIMITS + [
            "Pas de grandes deformations plastiques, contact, pression suiveuse ou rupture.",
            "La decision presente ne ferme pas le post-flambement general.",
        ],
        [
            "docs/verification/revue_tet4_total_lagrangian_structural_v2.md",
            "qualification/vnv/tet4_tl_buckling_h5/reference/summary.json",
            "qualification/reviews/tet4_total_lagrangian_independent_review_pending.json",
        ],
        ["docs/assets/reviews/tet4_tl_assembly_convergence.png"],
        "La revue independante est un gate explicite.",
    ),
    _scope(
        "tet4-material-nonlinear",
        "TET4 J2 material nonlineaire",
        "experimental",
        "owner_accepted experimental borne",
        "PASS_EXTERNAL_STRUCTURAL_BOUNDED",
        "accepted_for_bounded_engineering_use",
        "La campagne J2 isotrope monotone sur equerre rentrante utilise le meme maillage TET4/TETRA4 et les memes chargements que Code_Aster. La preuve structurelle est bonne mais le domaine reste petit deplacement et monotone.",
        [
            _metric("Ecart RMS deplacement", "4,66e-14", "1e-2"),
            _metric("Ecart RMS PEEQ", "2,89e-15", "1e-2"),
            _metric("Residu relatif maximal", "1,36e-12", "1e-7"),
            _metric("Elements de la correlation", "244 TET4", "cas documente"),
        ],
        [
            "Q1 : La geometrie rentrante et le chargement monotone couvrent-ils le domaine J2 revendique ?",
            "Q2 : Les limites petites deformations, isotropie et ecrouissage lineaire sont-elles acceptees ?",
            "Q3 : Une correlation structurelle cyclique externe est-elle requise avant toute promotion stable ?",
            "Q4 : Decision Owner : accepted_for_bounded_engineering_use ou more_evidence_required ?",
        ],
        COMMON_LIMITS + [
            "Chargement inverse, grandes deformations, contact, rupture et dommage exclus.",
            "La correlation externe ne couvre pas tous les chemins cycliques.",
        ],
        [
            "docs/verification/tet4_j2_structural_code_aster.md",
            "qualification/maturity_evidence_0_2_1/tet4_j2.json",
            "qualification/vnv/external/code_aster_tet4_j2_complex/reference/",
        ],
        ["qualification/maturity_evidence_0_2_1/tet4_j2_structural_campaign/cyclic_response.png"],
    ),
    _scope(
        "tet10-material-nonlinear",
        "TET10 J2 material nonlineaire",
        "owner_accepted_experimental_bounded_use",
        "owner_accepted experimental borne",
        "PASS_EXTERNAL_STRUCTURAL_BOUNDED",
        "accepted_for_bounded_engineering_use",
        "Le support en L quadratique et la loi J2 sont compares a Code_Aster sur cinq facteurs de charge. Les observables globales sont coherentes, mais les limites de petites deformations et de materiau isotrope restent strictes.",
        [
            _metric("Ecart RMS deplacement", "0,01245 %", "10 %"),
            _metric("Ecart final deplacement", "0,00227 %", "10 %"),
            _metric("Ecart RMS PEEQ", "1,84443 %", "15 %"),
            _metric("Residu QF maximal", "1,97e-09", "1e-7"),
        ],
        [
            "Q1 : Le support en L et les facteurs 0,25 a 1,10 couvrent-ils le domaine J2 borne ?",
            "Q2 : Les exclusions rupture, dommage, contact et grandes deformations sont-elles acceptees ?",
            "Q3 : Une preuve structurelle sur un second chemin de chargement est-elle necessaire avant stable ?",
            "Q4 : Decision Owner : accepted_for_bounded_engineering_use ou more_evidence_required ?",
        ],
        COMMON_LIMITS + [
            "Une seule geometrie structurelle externe est disponible.",
            "Les seuils historiques de 10/15 % ne constituent pas la regle stable generale a 1 %.",
        ],
        [
            "docs/verification/tet10_j2_complex_code_aster.md",
            "qualification/maturity_evidence_0_2_1/tet10_j2.json",
            "qualification/vnv/external/code_aster_tet10_j2_complex/reference/",
        ],
        ["docs/assets/reviews/tet10_j2_complex_comparison.png"],
    ),
    _scope(
        "orthotropic-solid-tet4-tet10",
        "Solides orthotropes statiques TET4/TET10",
        "supplementary_scope / accepted_with_recommendations",
        "owner_accepted (borne)",
        "PASS_EXTERNAL_CORRELATION",
        "accepted_with_recommendations",
        "Les noyaux orthotropes et les correlations externes sont PASS. Le TET4 passe le gate technique sous 1 % sur la campagne CG raffinee; le TET10 est sous 1 % sur sa campagne de reference.",
        [
            _metric("TET4 erreur deplacement, CG fin", "0,8772 %", "1 %"),
            _metric("TET4 erreur energie, CG fin", "0,8647 %", "1 %"),
            _metric("TET10 erreur deplacement", "0,2918 %", "1 %"),
            _metric("Residue TET4 CG fin", "9,963e-09", "1e-8", "WARNING"),
        ],
        [
            "Q1 : Les conventions E1/E2/E3, Poisson, cisaillements et axes locaux sont-elles acceptees ?",
            "Q2 : Les campagnes TET4/TET10 et les deux correlations externes couvrent-elles le domaine statique borne ?",
            "Q3 : Les singularites, l'orientation continue courbe, le composite pli par pli et la plasticite anisotrope restent-ils exclus ?",
            "Q4 : Decision Owner : owner_accepted, accepted_with_recommendations ou more_evidence_required ?",
        ],
        COMMON_LIMITS + [
            "Le champ d'orientation continue sur courbe et le composite pli par pli sont exclus.",
            "Verifier la coherence entre l'ancien texte 1,3293 % et la campagne CG actuelle 0,8772 % avant signature.",
        ],
        [
            "docs/verification/orthotropic_static_extended_owner_review.md",
            "qualification/maturity_evidence_0_2_1/orthotropic.json",
            "qualification/vnv/external/orthotropic_solids/reference/summary.json",
        ],
        ["qualification/vnv/orthotropic_solid_convergence_large_cg_006/reference/orthotropic_convergence.png"],
        "Une incoherence documentaire ancienne doit etre confirmee par la source archivee avant fermeture.",
    ),
    _scope(
        "orthotropic-solid-modal",
        "Solide orthotrope modal",
        "supplementary_scope / ready_for_owner_review",
        "owner_accepted (borne)",
        "PASS_EXTERNAL_CORRELATION",
        "accepted_with_recommendations",
        "La masse coherente, les frequences, les residus et l'orthogonalite sont verifies sur quatre niveaux de maillage, avec une correlation Code_Aster sur la meme grille.",
        [
            _metric("Erreur frequence theorie fine", "0,007717 %", "1 %"),
            _metric("Residu modal fin", "2,625e-12", "1e-8"),
            _metric("Orthogonalite masse", "1,122e-16", "1e-8"),
            _metric("Ecart frequence Code_Aster", "1,205e-13", "1e-6"),
        ],
        [
            "Q1 : Les quatre niveaux de maillage et la masse coherente couvrent-ils le domaine modal orthotrope teste ?",
            "Q2 : Les axes materiau, l'invariance de masse et les residus sont-ils acceptables ?",
            "Q3 : Les exclusions composite pli par pli, dommage et grandes deformations sont-elles maintenues ?",
            "Q4 : Decision Owner : owner_accepted ou accepted_with_recommendations ?",
        ],
        COMMON_LIMITS + [
            "Modele axial 3D borne; pas de champ d'orientation variable ni de dynamique distribuee generale.",
        ],
        [
            "qualification/vnv/orthotropic_modal_newmark/reference/summary.json",
            "qualification/reviews/orthotropic_modal_owner_review_pending.json",
            "tests/verification/test_orthotropic_modal_newmark_vnv.py",
        ],
        ["qualification/vnv/orthotropic_modal_newmark/reference/modal_convergence.png"],
    ),
    _scope(
        "orthotropic-solid-transient-dynamic",
        "Solide orthotrope transitoire Newmark",
        "supplementary_scope / ready_for_owner_review",
        "owner_accepted (borne)",
        "PASS_EXTERNAL_CORRELATION",
        "accepted_with_recommendations",
        "La reponse Newmark est verifiee sur huit pas de temps avec zero derive energetique archivee et une correlation Code_Aster sur la meme grille temporelle.",
        [
            _metric("Erreur de raffinement temporel", "0,1119 %", "1 %"),
            _metric("Residu dynamique maximal", "2,228e-10", "1e-7"),
            _metric("Derive energetique", "0", "1e-4"),
            _metric("Ecart historique Code_Aster", "6,254e-14", "1e-5"),
        ],
        [
            "Q1 : Les huit niveaux de pas et le schema Newmark couvrent-ils le domaine transitoire orthotrope teste ?",
            "Q2 : La masse, l'amortissement nul et les conventions d'axes sont-ils acceptables ?",
            "Q3 : Les exclusions non-linearite, dommage, grandes deformations et pli-par-pli sont-elles maintenues ?",
            "Q4 : Decision Owner : owner_accepted ou accepted_with_recommendations ?",
        ],
        COMMON_LIMITS + [
            "La validation ne couvre pas l'endommagement ni le composite pli par pli.",
            "La dynamique courbe et distribuee reste hors du perimetre.",
        ],
        [
            "qualification/vnv/orthotropic_modal_newmark/reference/summary.json",
            "qualification/reviews/orthotropic_transient_dynamic_owner_review_pending.json",
            "tests/verification/test_orthotropic_modal_newmark_vnv.py",
        ],
        ["qualification/vnv/orthotropic_modal_newmark/reference/newmark_convergence.png"],
    ),
    _scope(
        "contact-v1-linear-static-bounded",
        "Contact unilateral sans frottement",
        "owner_accepted / engineering_ready_bounded",
        "accepted_for_bounded_engineering_use (maintien)",
        "PASS_EXTERNAL_CORRELATION",
        "accepted_for_bounded_engineering_use",
        "Les cas ouverture/fermeture, face TET4 deformable, surface pliee et confirmation 9 984 TET4 sont documentes. Le resultat ne qualifie pas le contact general.",
        [
            _metric("Ecart final sur 9 984 TET4", "3,3029e-12 %", "5 %"),
            _metric("Jeu final maximal", "9,7145e-16 m", "1e-8 m"),
            _metric("Ecart moyen recherche de pli", "0,1157 %", "1 %"),
        ],
        [
            "Q1 : Les preuves de contact unilateral et les modeles complementaires couvrent-ils le domaine borne ?",
            "Q2 : Les gaps, reactions, normales et active-set sont-ils correctement interpretes ?",
            "Q3 : Les limites surface-surface general, grand glissement, impact et usure sont-elles acceptees ?",
            "Q4 : Decision Owner : maintenir accepted_for_bounded_engineering_use ou demander plus d'evidence ?",
        ],
        COMMON_LIMITS + [
            "Contact surface-surface general, grand glissement, impact et usure exclus.",
            "La decision ne s'etend pas au frottement.",
        ],
        [
            "docs/verification/revue_contact_v1.md",
            "qualification/reviews/contact_v1_linear_static_bounded_2026-07-29.json",
            "results/VNV-CONTACT-ADDITIONAL-MODELS-008/",
        ],
        ["docs/assets/reviews/contact_code_aster_additional_curves.png", "docs/assets/reviews/contact_additional_models.png"],
    ),
    _scope(
        "contact-frictional-static",
        "Contact statique avec frottement",
        "experimental",
        "owner_accepted experimental borne",
        "PASS_EXTERNAL_CORRELATION_SLIP_ONLY",
        "accepted_for_bounded_engineering_use",
        "Trois familles internes et trois niveaux par famille sont verifies. Code_Aster est compare sur trois charges tangentielles, uniquement sur la branche slip.",
        [
            _metric("Ecart UX Code_Aster, charge 200 N", "0,607 %", "5 %"),
            _metric("Ecart UX Code_Aster, charge 250 N", "0,456 %", "5 %"),
            _metric("Ecart UX Code_Aster, charge 300 N", "0,365 %", "5 %"),
            _metric("Families internes", "3 x 3 niveaux", "preuve interne"),
        ],
        [
            "Q1 : Les trois familles et les trois niveaux de maillage sont-ils suffisants pour la branche slip ?",
            "Q2 : Le cone de Coulomb, les gaps et la dissipation sont-ils correctement verifies ?",
            "Q3 : La correlation Code_Aster slip est-elle acceptee comme preuve externe partielle ?",
            "Q4 : La branche stick, le grand glissement et le contact surface-surface general restent-ils hors scope ?",
            "Q5 : Decision Owner : owner_accepted experimental borne ou more_evidence_required ?",
        ],
        COMMON_LIMITS + [
            "La branche stick n'est pas fermee par correlation externe.",
            "Grand glissement, normales actualisees, impacts, usure et contact dynamique exclus.",
        ],
        [
            "docs/verification/contact_frottement_vnv.md",
            "qualification/maturity_evidence_0_2_1/contact_frictional_static.json",
            "qualification/maturity_evidence_0_2_1/contact_frictional_family_survey/summary.json",
        ],
        ["qualification/maturity_evidence_0_2_1/contact_friction_code_aster_three_loads/code_aster_friction_comparison.png", "qualification/maturity_evidence_0_2_1/contact_frictional_family_survey/frictional_contact_family_survey.png"],
    ),
    _scope(
        "large-tet4-linear-static",
        "Grand modele TET4 statique lineaire PETSc/MPI",
        "experimental / PASS_INTERNAL_WITH_LIMITATIONS",
        "accepted_for_bounded_engineering_use",
        "PASS_SCALABLE_PIPELINE_WITH_LIMITED_SCALING",
        "accepted_for_bounded_engineering_use",
        "Le chemin HDF5, MPI, assembleur par blocs, AIJ/BAIJ et KSP GAMG est verifie jusqu'a 3 millions de DDL. La mesure de scaling reste limitee a une station et une image conteneur.",
        [
            _metric("Cas 1 M DDL", "1 029 000 DDL / 1 971 054 TET4", "PASS"),
            _metric("Cas 3 M DDL", "3 000 000 DDL / 5 821 794 TET4", "PASS"),
            _metric("Residue 3 M DDL", "8,997e-19", "diagnostic"),
            _metric("Weak scaling, 4 rangs", "41,6 %", "60 %", "WARNING"),
        ],
        [
            "Q1 : Les cas 100 k, 1 M et 3 M DDL demontrent-ils le perimetre TET4 isotrope statique ?",
            "Q2 : Les limites de machine, memoire, image Docker, PETSc/MPI et scaling sont-elles acceptables ?",
            "Q3 : Le statut bounded est-il prefere a une revendication HPC generale ?",
            "Q4 : Decision Owner : accepted_for_bounded_engineering_use ou more_evidence_required ?",
        ],
        COMMON_LIMITS + [
            "Une seule configuration materielle est mesuree; weak scaling 4 rangs sous le seuil provisoire.",
            "MITC4, TET10, non-lineaire, modal et transitoire grand modele exclus.",
        ],
        [
            "qualification/maturity_evidence_0_2_1/large_tet4_linear_static.json",
            "results_large/qualification_matrix_free_1m/large_readiness.md",
            "tests/integration/test_large_model.py",
        ],
        ["docs/assets/generated/large_model_summary.png"],
    ),
    _scope(
        "mitc4-orthotropic-curved-out-of-acceptance",
        "MITC4 orthotrope courbe",
        "out_of_acceptance",
        "hors acceptance",
        "DIAGNOSTIC_ONLY",
        "no_decision",
        "Ce cas est conserve comme diagnostic, pas comme dossier de promotion. L'orientation non axiale projetee sur une surface courbe n'est pas encore comparable de facon suffisante pour une acceptation.",
        [
            _metric("Courbe mono-pli 0 deg, UZ", "0,012 %", "diagnostic"),
            _metric("Orientation courbe non axiale", "preuve incomplete", "hors acceptance", "WARNING"),
            _metric("Dommage / rupture / delamination", "non traite", "hors acceptance", "WARNING"),
        ],
        [
            "Q1 : Confirmer que ce cas reste explicitement hors acceptance.",
            "Q2 : Confirmer qu'aucune preuve des solides orthotropes n'est reutilisee pour ce cas MITC4 courbe.",
            "Q3 : Confirmer que l'orientation continue courbe fera l'objet d'une campagne distincte.",
            "Q4 : Decision : hors acceptance, sans promotion.",
        ],
        COMMON_LIMITS + [
            "Orientation non axiale projetee sur surface courbe non qualifiee.",
            "Ce dossier ne doit pas etre compte parmi les scopes stables.",
        ],
        [
            "docs/verification/mitc4_stable_package/owner_review.md",
            "qualification/studies/mitc4_stable_package_2026-08-21/study.json",
            "docs/verification/mitc4_same_order_oracle_probe.md",
        ],
        ["results/mitc4_orthotropic_curved_projected_one_ply_calculix_20260821/curved_orientation_correlation.png"],
        "Ce perimetre reste volontairement exclu et ne doit pas etre promu.",
    ),
]
def _write_json() -> None:
    payload = {
        "schema_version": 1,
        "review_id": "OWNER-REVIEW-SCOPE-CLOSURE-2026-08-21",
        "revision": "0.2.1-alpha",
        "status": "pending_owner_review",
        "review_mode": "pending_owner_decision",
        "automatic_promotion": False,
        "owner": None,
        "decision_date": None,
        "certification_claim": "none",
        "purpose": "Consolider les preuves existantes des scopes restants avant revue Owner.",
        "scope_count": len(SCOPES),
        "scopes": SCOPES,
    }
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)
def _write_markdown() -> None:
    lines = [
        "---",
        "doc_id: DOC-OWNER-SCOPE-CLOSURE-2026-08-21",
        "revision: 0.1",
        "status: ready_for_owner_review",
        "review_mode: pending_owner_decision",
        "applicable_version: 0.2.1-alpha",
        "---",
        "",
        "# Dossier Owner Review - fermeture des scopes restants",
        "",
        "**Document de preparation - aucune decision ni signature n'est enregistree ici.**",
        "",
        "Ce dossier consolide les preuves deja archivees. Il ne lance aucun calcul, ne modifie aucune maturite et ne remplace pas les rapports V&V sources. La reponse Owner doit rester limitee au domaine, aux observables et aux exclusions de chaque section.",
        "",
        "## Regle de lecture",
        "",
        "Une valeur PASS technique n'est pas une promotion automatique. Pour passer vers stable, il faut une erreur primaire applicable inferieure ou egale a 1 %, des invariants numeriques satisfaits, une preuve externe comparable quand elle est requise et une decision Owner datee. Les scopes marques bornes ou bloques ne sont pas stables.",
        "",
        "## Synthese",
        "",
        _md_table(
            ["Scope", "Etat actuel", "Cible proposee", "Lecture rapide"],
            [[item["scope"], item["current_status"], item["target_status"], item["technical_status"]] for item in SCOPES],
        ),
        "",
        "MITC4 orthotrope courbe est volontairement conserve hors acceptance et ne doit pas etre compte comme un scope a promouvoir.",
        "",
    ]
    for index, item in enumerate(SCOPES, start=1):
        lines.extend(
            [
                f"## {index}. {item['title']}",
                "",
                f"- **Scope :** `{item['scope']}`",
                f"- **Etat actuel :** `{item['current_status']}`",
                f"- **Cible proposee :** `{item['target_status']}`",
                f"- **Etat technique :** `{item['technical_status']}`",
                f"- **Decision proposee, non enregistree :** `{item['proposed_decision']}`",
                "",
                item["summary"],
                "",
                "### Mesures disponibles",
                "",
                _md_table([["Controle", "Valeur", "Limite", "Statut"]][0], [[m["name"], m["value"], m["limit"], m["status"]] for m in item["metrics"]]),
                "",
                "### Questions Owner",
                "",
            ]
        )
        lines.extend(f"{question}\n\nReponse : `\n\nCommentaire : `\n" for question in item["questions"])
        lines.extend(["### Limites et exclusions", "", *[f"- {limit}" for limit in item["limitations"]], ""])
        if item["blocker"]:
            lines.extend([f"### Point de vigilance\n\n{item['blocker']}\n"])
        lines.extend(["### Preuves et artefacts", "", *[f"- `{path}`" for path in item["evidence"]], ""])
        if item["images"]:
            lines.extend(["### Figures disponibles", "", *[f"- `{path}`" for path in item["images"]], ""])
    lines.extend(
        [
            "## Decision finale a completer par le Owner",
            "",
            "- Nom du Owner :",
            "- Date :",
            "- Decision globale : `accepted_with_recommendations` / `accepted_for_bounded_engineering_use` / `more_evidence_required`",
            "- Commentaire :",
            "",
            "Cette page ne constitue pas une certification, une revue independante ou une promotion automatique.",
            "",
        ]
    )
    MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    MD_PATH.write_text("\n".join(lines), encoding="utf-8")
def _pdf_story(styles: dict[str, Any]) -> list[Any]:
    story: list[Any] = [
        Paragraph("QF_solver - Dossier Owner Review", styles["title"]),
        Spacer(1, 5 * mm),
        Paragraph("Scopes restants a borner ou promouvoir - 2026-08-21", styles["subtitle"]),
        Spacer(1, 8 * mm),
        Paragraph("Document de preparation. Aucune decision, signature ou promotion n'est enregistree par ce generation.", styles["note"]),
        Paragraph("Objectif : permettre une relecture Owner scope par scope avec les chiffres existants, les figures disponibles, les limites et les questions a repondre.", styles["body"]),
        review_table(
            [["Categorie", "Nombre"], ["Sections consolidees", str(len(SCOPES))], ["Calculs relances", "0"], ["Promotions automatiques", "0"], ["Scopes explicitement hors acceptance", "1"]],
            [105 * mm, 55 * mm],
            styles,
        ),
    ]
    for index, item in enumerate(SCOPES, start=1):
        story.append(PageBreak())
        story.extend(
            [
                Paragraph(f"{index}. {item['title']}", styles["h1"]),
                review_table(
                    [["Champ", "Valeur"], ["Scope", item["scope"]], ["Etat actuel", item["current_status"]], ["Cible", item["target_status"]], ["Etat technique", item["technical_status"]], ["Decision proposee", item["proposed_decision"]]],
                    [48 * mm, 112 * mm],
                    styles,
                ),
                Spacer(1, 4 * mm),
                Paragraph(item["summary"], styles["body"]),
                Paragraph("Mesures archivees", styles["h2"]),
                review_table(
                    [["Controle", "Valeur", "Limite", "Statut"]] + [[m["name"], m["value"], m["limit"], m["status"]] for m in item["metrics"]],
                    [66 * mm, 31 * mm, 31 * mm, 32 * mm],
                    styles,
                ),
                Spacer(1, 3 * mm),
                Paragraph("Questions Owner", styles["h2"]),
            ]
        )
        for question in item["questions"]:
            story.append(Paragraph(question, styles["body"]))
            story.append(Paragraph("Reponse Owner : OUI / NON / PARTIELLEMENT / decision a preciser", styles["small"]))
        story.append(Paragraph("Limites et exclusions", styles["h2"]))
        for limit in item["limitations"]:
            story.append(Paragraph(f"- {limit}", styles["small"]))
        if item["blocker"]:
            story.append(Paragraph(f"Point de vigilance : {item['blocker']}", styles["note"]))
        for image_index, relative in enumerate(item["images"], start=1):
            figure = review_image(ROOT / relative, TMP_DIR / f"{index}_{image_index}.png", max_height=58 * mm)
            if figure is not None:
                story.extend([Spacer(1, 2 * mm), figure, Paragraph(f"Figure {image_index} - {relative}", styles["small"])])
    story.extend(
        [
            PageBreak(),
            Paragraph("Reponse Owner a reporter", styles["h1"]),
            Paragraph("Pour chaque section, reporter la decision dans le JSON associe et dans le rapport de revue apres lecture. Ne pas utiliser ce paquet pour signer automatiquement.", styles["body"]),
            review_table(
                [["Scope", "Decision Owner", "Date", "Commentaire"]] + [[item["scope"], "", "", ""] for item in SCOPES],
                [57 * mm, 40 * mm, 24 * mm, 39 * mm],
                styles,
            ),
            Spacer(1, 8 * mm),
            Paragraph("MITC4 orthotrope courbe : decision predefinie de preparation = hors acceptance. Aucune promotion ne doit etre signee sur cette base.", styles["note"]),
        ]
    )
    return story
def _write_pdf() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    styles = review_styles()
    document = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=15 * mm,
        bottomMargin=16 * mm,
        title="QF_solver - Owner Review scope closure",
        author="QF_solver project",
    )
    document.build(_pdf_story(styles), onFirstPage=review_footer, onLaterPages=review_footer)
    validate_pdf(PDF_PATH, ["Scopes restants", "Questions Owner", "MITC4 orthotrope courbe"], 8)
def main() -> int:
    _write_json()
    _write_markdown()
    _write_pdf()
    print(f"Markdown: {MD_PATH}")
    print(f"Review JSON: {JSON_PATH}")
    print(f"PDF: {PDF_PATH}")
    print(f"Scope count: {len(SCOPES)}")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
