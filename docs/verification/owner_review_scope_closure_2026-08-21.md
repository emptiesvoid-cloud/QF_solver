---
doc_id: DOC-OWNER-SCOPE-CLOSURE-2026-08-21
revision: 0.1
status: ready_for_owner_review
review_mode: pending_owner_decision
applicable_version: 0.2.1-alpha
---

# Dossier Owner Review - fermeture des scopes restants

**Document de preparation - aucune decision ni signature n'est enregistree ici.**

Ce dossier consolide les preuves deja archivees. Il ne lance aucun calcul, ne modifie aucune maturite et ne remplace pas les rapports V&V sources. La reponse Owner doit rester limitee au domaine, aux observables et aux exclusions de chaque section.

## Regle de lecture

Une valeur PASS technique n'est pas une promotion automatique. Pour passer vers stable, il faut une erreur primaire applicable inferieure ou egale a 1 %, des invariants numeriques satisfaits, une preuve externe comparable quand elle est requise et une decision Owner datee. Les scopes marques bornes ou bloques ne sont pas stables.

## Synthese

| Scope | Etat actuel | Cible proposee | Lecture rapide |
| --- | --- | --- | --- |
| mitc3-laminate-static | verified_development_external_correlation | owner_accepted | PASS_EXTERNAL_CORRELATION |
| mitc3-laminate-dynamic-thin-planar | verified_development_external_correlation | stable (sous-perimetre mince plane uniquement) | PASS_EXTERNAL_CORRELATION_DKT |
| mitc3-laminate-static-curved-mixed-transverse | owner_accepted_experimental_bounded_use | stable (sous-perimetre mixte/transverse borne) | PASS_WITH_AXIAL_EXCLUSION |
| mitc3-laminate-static-curved | owner_accepted_experimental_bounded_use | accepted_for_bounded_engineering_use (pas stable) | BLOCKED_EXTERNAL_COMPARABILITY |
| tet4-total-lagrangian-structural-v2 | owner_accepted / research | experimental borne (pas stable) | PASS_WITH_INDEPENDENT_REVIEW_REQUIRED |
| tet4-material-nonlinear | experimental | owner_accepted experimental borne | PASS_EXTERNAL_STRUCTURAL_BOUNDED |
| tet10-material-nonlinear | owner_accepted_experimental_bounded_use | owner_accepted experimental borne | PASS_EXTERNAL_STRUCTURAL_BOUNDED |
| orthotropic-solid-tet4-tet10 | supplementary_scope / accepted_with_recommendations | owner_accepted (borne) | PASS_EXTERNAL_CORRELATION |
| orthotropic-solid-modal | supplementary_scope / ready_for_owner_review | owner_accepted (borne) | PASS_EXTERNAL_CORRELATION |
| orthotropic-solid-transient-dynamic | supplementary_scope / ready_for_owner_review | owner_accepted (borne) | PASS_EXTERNAL_CORRELATION |
| contact-v1-linear-static-bounded | owner_accepted / engineering_ready_bounded | accepted_for_bounded_engineering_use (maintien) | PASS_EXTERNAL_CORRELATION |
| contact-frictional-static | experimental | owner_accepted experimental borne | PASS_EXTERNAL_CORRELATION_SLIP_ONLY |
| large-tet4-linear-static | experimental / PASS_INTERNAL_WITH_LIMITATIONS | accepted_for_bounded_engineering_use | PASS_SCALABLE_PIPELINE_WITH_LIMITED_SCALING |
| mitc4-orthotropic-curved-out-of-acceptance | out_of_acceptance | hors acceptance | DIAGNOSTIC_ONLY |

MITC4 orthotrope courbe est volontairement conserve hors acceptance et ne doit pas etre compte comme un scope a promouvoir.

## 1. MITC3 multicouche statique plane

- **Scope :** `mitc3-laminate-static`
- **Etat actuel :** `verified_development_external_correlation`
- **Cible proposee :** `owner_accepted`
- **Etat technique :** `PASS_EXTERNAL_CORRELATION`
- **Decision proposee, non enregistree :** `accepted_for_bounded_engineering_use`

Patch membrane plan [0/90/90/0] compare a CalculiX S6 COMPOSITE. La preuve porte sur les contraintes dans les axes materiau et non sur une coque courbe.

### Mesures disponibles

| Controle | Valeur | Limite | Statut |
| --- | --- | --- | --- |
| Ecart L2 contraintes par pli fin | 0,09625 % | 2 % | PASS |
| Erreur patch affine QF_solver | 2,278e-13 | 1e-10 | PASS |
| Dernier increment CalculiX | 0,07313 % | 0,2 % | PASS |

### Questions Owner

Q1 : Les preuves et le maillage 4x1 -> 8x2 -> 16x4 couvrent-ils le domaine plane declare ?

Reponse : `

Commentaire : `

Q2 : Les observables S11/S22/S12 par pli sont-ils suffisants pour ce domaine ?

Reponse : `

Commentaire : `

Q3 : Les exclusions S13/S23, bords libres, dommage et delamination sont-elles acceptees ?

Reponse : `

Commentaire : `

Q4 : Decision Owner : accepted_for_bounded_engineering_use, accepted_with_recommendations ou more_evidence_required ?

Reponse : `

Commentaire : `

### Limites et exclusions

- Aucune revendication de certification externe.
- La decision doit rester limitee aux preuves et aux observables listes.
- Dommage, rupture et delamination restent hors scope sauf mention contraire.
- Une seule geometrie plane et un seul empilement symetrique sont compares.
- MITC3+ et CalculiX S6 ne sont pas la meme formulation elementaire.

### Preuves et artefacts

- `docs/verification/mitc3_laminate_dynamic.md`
- `qualification/maturity_evidence_0_2_1/mitc3_laminate_static_campaign/summary.json`
- `qualification/vnv/external/calculix_mitc3_laminate_ply_stress/reference/`

### Figures disponibles

- `qualification/maturity_evidence_0_2_1/mitc3_laminate_static_campaign/mitc3_laminate_ply_stress_calculix.png`

## 2. MITC3 multicouche dynamique mince plane

- **Scope :** `mitc3-laminate-dynamic-thin-planar`
- **Etat actuel :** `verified_development_external_correlation`
- **Cible proposee :** `stable (sous-perimetre mince plane uniquement)`
- **Etat technique :** `PASS_EXTERNAL_CORRELATION_DKT`
- **Decision proposee, non enregistree :** `stable`

La campagne DKT de Code_Aster fournit une reference de limite mince sur le meme stratife [0/90/90/0]. Elle est distincte de la comparaison DST, qui reste un diagnostic de difference de formulation.

### Mesures disponibles

| Controle | Valeur | Limite | Statut |
| --- | --- | --- | --- |
| Erreur modale fine 24x6 | 0,3940 % | 1 % | PASS |
| Erreur RMS Newmark fine | 0,1968 % | 1 % | PASS |
| Erreur harmonique fine | 0,0880 % | 1 % | PASS |
| Residu modal fin | 1,08e-08 | 1e-07 | PASS |

### Questions Owner

Q1 : Le domaine mince, symetrique et plan est-il suffisamment delimite ?

Reponse : `

Commentaire : `

Q2 : Les erreurs fines 0,3940 %, 0,1968 % et 0,0880 % sont-elles acceptees ?

Reponse : `

Commentaire : `

Q3 : Les niveaux intermediaires depassant parfois 1 % doivent-ils rester publies comme diagnostics ?

Reponse : `

Commentaire : `

Q4 : DKT est-il accepte comme oracle de limite mince sans pretendre a une identite MITC3/DKT ?

Reponse : `

Commentaire : `

Q5 : Decision Owner pour le sous-perimetre mince plane ?

Reponse : `

Commentaire : `

### Limites et exclusions

- Aucune revendication de certification externe.
- La decision doit rester limitee aux preuves et aux observables listes.
- Dommage, rupture et delamination restent hors scope sauf mention contraire.
- Coques epaisses, courbes, non symetriques, couplage B non nul et amortissement calibre exclus.
- La decision ne s'etend pas aux contraintes dynamiques par pli.

### Point de vigilance

La promotion depend d'une decision Owner ; aucune promotion automatique ne doit etre deduite du PASS technique.

### Preuves et artefacts

- `docs/verification/mitc3_laminate_dynamic_dkt_thin_owner_review.md`
- `qualification/vnv/external/code_aster_mitc3_laminate_dynamic_refinement_dkt_2026-08-21/reference/summary.json`
- `qualification/vnv/mitc3_laminate_temporal_refinement_2026-08-21/summary.json`

### Figures disponibles

- `qualification/vnv/external/code_aster_mitc3_laminate_dynamic_refinement_dkt_2026-08-21/reference/mitc3_laminate_dynamic_refinement.png`

## 3. MITC3 multicouche courbe : mixte et transverse

- **Scope :** `mitc3-laminate-static-curved-mixed-transverse`
- **Etat actuel :** `owner_accepted_experimental_bounded_use`
- **Cible proposee :** `stable (sous-perimetre mixte/transverse borne)`
- **Etat technique :** `PASS_WITH_AXIAL_EXCLUSION`
- **Decision proposee, non enregistree :** `stable`

Panneau cylindrique facettise, axes materiau projetes par facette et empilement [0/90/90/0]. Le sous-perimetre ne revendique pas le chargement axial.

### Mesures disponibles

| Controle | Valeur | Limite | Statut |
| --- | --- | --- | --- |
| Ecart mixte QF / Code_Aster | 0,5780 % | 1 % | PASS |
| Ecart transverse QF / Code_Aster | 0,4975 % | 1 % | PASS |
| Increment mixte final | 4,4755 % | 5 % | PASS |
| Increment transverse final | 4,6023 % | 5 % | PASS |

### Questions Owner

Q1 : La geometrie, l'orientation projetee et l'empilement sont-ils assez definis ?

Reponse : `

Commentaire : `

Q2 : Les deux familles mixte et transverse sous 1 % sont-elles suffisantes pour ce sous-perimetre ?

Reponse : `

Commentaire : `

Q3 : L'exclusion axiale est-elle acceptee sans extrapolation ?

Reponse : `

Commentaire : `

Q4 : Les exclusions S13/S23, singularites, dommage et delamination sont-elles acceptees ?

Reponse : `

Commentaire : `

Q5 : Decision Owner : stable ou accepted_with_recommendations ?

Reponse : `

Commentaire : `

### Limites et exclusions

- Aucune revendication de certification externe.
- La decision doit rester limitee aux preuves et aux observables listes.
- Dommage, rupture et delamination restent hors scope sauf mention contraire.
- La preuve est limitee a une geometrie facettisee et un empilement.
- Le chargement axial n'est pas inclus dans ce sous-perimetre.

### Point de vigilance

Le sous-perimetre axial reste separe et bloque.

### Preuves et artefacts

- `docs/verification/mitc3_laminate_curved_mixed_transverse_stable_owner_review.md`
- `qualification/maturity_evidence_0_2_1/mitc3_laminate_curved_load_families/summary.json`
- `qualification/vnv/external/code_aster_mitc3_curved_laminate_refinement_027/reference/`

### Figures disponibles

- `qualification/maturity_evidence_0_2_1/mitc3_laminate_curved_load_families/curved_laminate_deformation_qf_code_aster.png`

## 4. MITC3 multicouche courbe : domaine axial complet

- **Scope :** `mitc3-laminate-static-curved`
- **Etat actuel :** `owner_accepted_experimental_bounded_use`
- **Cible proposee :** `accepted_for_bounded_engineering_use (pas stable)`
- **Etat technique :** `BLOCKED_EXTERNAL_COMPARABILITY`
- **Decision proposee, non enregistree :** `accepted_for_bounded_engineering_use`

Le cas axial est sous 1 % face a Code_Aster a 64x32, mais l'increment axial depasse 5 % et les references Code_Aster/CalculiX divergent. Le raffinement seul ne justifie pas une promotion stable.

### Mesures disponibles

| Controle | Valeur | Limite | Statut |
| --- | --- | --- | --- |
| Ecart axial QF / Code_Aster a 64x32 | 0,9066 % | 1 % | PASS |
| Increment QF axial 48x24 -> 64x32 | 8,2619 % | 5 % | FAIL |
| Ecart QF / CalculiX S6 a 64x32 | 6,420 % | 1 % | FAIL |
| Ecart Code_Aster / CalculiX | 7,591 % | information | WARNING |

### Questions Owner

Q1 : Le panneau axial peut-il etre accepte uniquement comme usage borne ?

Reponse : `

Commentaire : `

Q2 : L'increment axial et la dispersion des oracles interdisent-ils une promotion stable ?

Reponse : `

Commentaire : `

Q3 : Une seconde geometrie ou une reference de meme ordre doit-elle rester obligatoire ?

Reponse : `

Commentaire : `

Q4 : Decision Owner : accepted_for_bounded_engineering_use ou more_evidence_required ?

Reponse : `

Commentaire : `

### Limites et exclusions

- Aucune revendication de certification externe.
- La decision doit rester limitee aux preuves et aux observables listes.
- Dommage, rupture et delamination restent hors scope sauf mention contraire.
- La comparaison statique est sensible a la formulation externe DST/S6.
- Dynamique courbe, autres empilements et contraintes par pli d'acceptation exclus.

### Point de vigilance

Gate technique bloque par l'increment axial et la comparabilite externe.

### Preuves et artefacts

- `docs/verification/mitc3_laminate_curved_stable_owner_review.md`
- `qualification/vnv/external/mitc3_curved_axial_reference_audit_2026-08-21/`
- `qualification/vnv/external/calculix_mitc3_curved_laminate_axial_2026-08-21/reference/`

### Figures disponibles

- `qualification/maturity_evidence_0_2_1/mitc3_laminate_curved_load_families/convergence_qf_code_aster.png`

## 5. TET4 total-lagrangien structurel

- **Scope :** `tet4-total-lagrangian-structural-v2`
- **Etat actuel :** `owner_accepted / research`
- **Cible proposee :** `experimental borne (pas stable)`
- **Etat technique :** `PASS_WITH_INDEPENDENT_REVIEW_REQUIRED`
- **Decision proposee, non enregistree :** `more_evidence_required`

Green-Lagrange, PK2/Cauchy, imperfection et flambement sont verifies jusqu'a 98 304 TET4. L'accord CalculiX est excellent, mais la revue independante et le post-flambement restent ouverts.

### Mesures disponibles

| Controle | Valeur | Limite | Statut |
| --- | --- | --- | --- |
| Erreur Euler h5, 98 304 TET4 | 1,896 % | information | WARNING |
| Ecart QF / CalculiX h5 | 0,0343 % | 1 % | PASS |
| Erreur PK2 Code_Aster | 8,54e-5 | 1e-3 | PASS |
| Erreur Cauchy CalculiX | 1,17e-7 | 1e-3 | PASS |

### Questions Owner

Q1 : Les preuves couvrent-elles le flambement pre-critique et la charge critique dans le domaine declare ?

Reponse : `

Commentaire : `

Q2 : Les trois imperfections et la limite de 98 304 TET4 sont-elles acceptees ?

Reponse : `

Commentaire : `

Q3 : La revue independante doit-elle rester obligatoire avant toute maturite superieure ?

Reponse : `

Commentaire : `

Q4 : Les exclusions pression suiveuse, contact, rupture et post-flambement complet sont-elles acceptees ?

Reponse : `

Commentaire : `

Q5 : Decision Owner : experimental borne ou more_evidence_required ?

Reponse : `

Commentaire : `

### Limites et exclusions

- Aucune revendication de certification externe.
- La decision doit rester limitee aux preuves et aux observables listes.
- Dommage, rupture et delamination restent hors scope sauf mention contraire.
- Pas de grandes deformations plastiques, contact, pression suiveuse ou rupture.
- La decision presente ne ferme pas le post-flambement general.

### Point de vigilance

La revue independante est un gate explicite.

### Preuves et artefacts

- `docs/verification/revue_tet4_total_lagrangian_structural_v2.md`
- `qualification/vnv/tet4_tl_buckling_h5/reference/summary.json`
- `qualification/reviews/tet4_total_lagrangian_independent_review_pending.json`

### Figures disponibles

- `docs/assets/reviews/tet4_tl_assembly_convergence.png`

## 6. TET4 J2 material nonlineaire

- **Scope :** `tet4-material-nonlinear`
- **Etat actuel :** `experimental`
- **Cible proposee :** `owner_accepted experimental borne`
- **Etat technique :** `PASS_EXTERNAL_STRUCTURAL_BOUNDED`
- **Decision proposee, non enregistree :** `accepted_for_bounded_engineering_use`

La campagne J2 isotrope monotone sur equerre rentrante utilise le meme maillage TET4/TETRA4 et les memes chargements que Code_Aster. La preuve structurelle est bonne mais le domaine reste petit deplacement et monotone.

### Mesures disponibles

| Controle | Valeur | Limite | Statut |
| --- | --- | --- | --- |
| Ecart RMS deplacement | 4,66e-14 | 1e-2 | PASS |
| Ecart RMS PEEQ | 2,89e-15 | 1e-2 | PASS |
| Residu relatif maximal | 1,36e-12 | 1e-7 | PASS |
| Elements de la correlation | 244 TET4 | cas documente | PASS |

### Questions Owner

Q1 : La geometrie rentrante et le chargement monotone couvrent-ils le domaine J2 revendique ?

Reponse : `

Commentaire : `

Q2 : Les limites petites deformations, isotropie et ecrouissage lineaire sont-elles acceptees ?

Reponse : `

Commentaire : `

Q3 : Une correlation structurelle cyclique externe est-elle requise avant toute promotion stable ?

Reponse : `

Commentaire : `

Q4 : Decision Owner : accepted_for_bounded_engineering_use ou more_evidence_required ?

Reponse : `

Commentaire : `

### Limites et exclusions

- Aucune revendication de certification externe.
- La decision doit rester limitee aux preuves et aux observables listes.
- Dommage, rupture et delamination restent hors scope sauf mention contraire.
- Chargement inverse, grandes deformations, contact, rupture et dommage exclus.
- La correlation externe ne couvre pas tous les chemins cycliques.

### Preuves et artefacts

- `docs/verification/tet4_j2_structural_code_aster.md`
- `qualification/maturity_evidence_0_2_1/tet4_j2.json`
- `qualification/vnv/external/code_aster_tet4_j2_complex/reference/`

### Figures disponibles

- `qualification/maturity_evidence_0_2_1/tet4_j2_structural_campaign/cyclic_response.png`

## 7. TET10 J2 material nonlineaire

- **Scope :** `tet10-material-nonlinear`
- **Etat actuel :** `owner_accepted_experimental_bounded_use`
- **Cible proposee :** `owner_accepted experimental borne`
- **Etat technique :** `PASS_EXTERNAL_STRUCTURAL_BOUNDED`
- **Decision proposee, non enregistree :** `accepted_for_bounded_engineering_use`

Le support en L quadratique et la loi J2 sont compares a Code_Aster sur cinq facteurs de charge. Les observables globales sont coherentes, mais les limites de petites deformations et de materiau isotrope restent strictes.

### Mesures disponibles

| Controle | Valeur | Limite | Statut |
| --- | --- | --- | --- |
| Ecart RMS deplacement | 0,01245 % | 10 % | PASS |
| Ecart final deplacement | 0,00227 % | 10 % | PASS |
| Ecart RMS PEEQ | 1,84443 % | 15 % | PASS |
| Residu QF maximal | 1,97e-09 | 1e-7 | PASS |

### Questions Owner

Q1 : Le support en L et les facteurs 0,25 a 1,10 couvrent-ils le domaine J2 borne ?

Reponse : `

Commentaire : `

Q2 : Les exclusions rupture, dommage, contact et grandes deformations sont-elles acceptees ?

Reponse : `

Commentaire : `

Q3 : Une preuve structurelle sur un second chemin de chargement est-elle necessaire avant stable ?

Reponse : `

Commentaire : `

Q4 : Decision Owner : accepted_for_bounded_engineering_use ou more_evidence_required ?

Reponse : `

Commentaire : `

### Limites et exclusions

- Aucune revendication de certification externe.
- La decision doit rester limitee aux preuves et aux observables listes.
- Dommage, rupture et delamination restent hors scope sauf mention contraire.
- Une seule geometrie structurelle externe est disponible.
- Les seuils historiques de 10/15 % ne constituent pas la regle stable generale a 1 %.

### Preuves et artefacts

- `docs/verification/tet10_j2_complex_code_aster.md`
- `qualification/maturity_evidence_0_2_1/tet10_j2.json`
- `qualification/vnv/external/code_aster_tet10_j2_complex/reference/`

### Figures disponibles

- `docs/assets/reviews/tet10_j2_complex_comparison.png`

## 8. Solides orthotropes statiques TET4/TET10

- **Scope :** `orthotropic-solid-tet4-tet10`
- **Etat actuel :** `supplementary_scope / accepted_with_recommendations`
- **Cible proposee :** `owner_accepted (borne)`
- **Etat technique :** `PASS_EXTERNAL_CORRELATION`
- **Decision proposee, non enregistree :** `accepted_with_recommendations`

Les noyaux orthotropes et les correlations externes sont PASS. Le TET4 passe le gate technique sous 1 % sur la campagne CG raffinee; le TET10 est sous 1 % sur sa campagne de reference.

### Mesures disponibles

| Controle | Valeur | Limite | Statut |
| --- | --- | --- | --- |
| TET4 erreur deplacement, CG fin | 0,8772 % | 1 % | PASS |
| TET4 erreur energie, CG fin | 0,8647 % | 1 % | PASS |
| TET10 erreur deplacement | 0,2918 % | 1 % | PASS |
| Residue TET4 CG fin | 9,963e-09 | 1e-8 | WARNING |

### Questions Owner

Q1 : Les conventions E1/E2/E3, Poisson, cisaillements et axes locaux sont-elles acceptees ?

Reponse : `

Commentaire : `

Q2 : Les campagnes TET4/TET10 et les deux correlations externes couvrent-elles le domaine statique borne ?

Reponse : `

Commentaire : `

Q3 : Les singularites, l'orientation continue courbe, le composite pli par pli et la plasticite anisotrope restent-ils exclus ?

Reponse : `

Commentaire : `

Q4 : Decision Owner : owner_accepted, accepted_with_recommendations ou more_evidence_required ?

Reponse : `

Commentaire : `

### Limites et exclusions

- Aucune revendication de certification externe.
- La decision doit rester limitee aux preuves et aux observables listes.
- Dommage, rupture et delamination restent hors scope sauf mention contraire.
- Le champ d'orientation continue sur courbe et le composite pli par pli sont exclus.
- Verifier la coherence entre l'ancien texte 1,3293 % et la campagne CG actuelle 0,8772 % avant signature.

### Point de vigilance

Une incoherence documentaire ancienne doit etre confirmee par la source archivee avant fermeture.

### Preuves et artefacts

- `docs/verification/orthotropic_static_extended_owner_review.md`
- `qualification/maturity_evidence_0_2_1/orthotropic.json`
- `qualification/vnv/external/orthotropic_solids/reference/summary.json`

### Figures disponibles

- `qualification/vnv/orthotropic_solid_convergence_large_cg_006/reference/orthotropic_convergence.png`

## 9. Solide orthotrope modal

- **Scope :** `orthotropic-solid-modal`
- **Etat actuel :** `supplementary_scope / ready_for_owner_review`
- **Cible proposee :** `owner_accepted (borne)`
- **Etat technique :** `PASS_EXTERNAL_CORRELATION`
- **Decision proposee, non enregistree :** `accepted_with_recommendations`

La masse coherente, les frequences, les residus et l'orthogonalite sont verifies sur quatre niveaux de maillage, avec une correlation Code_Aster sur la meme grille.

### Mesures disponibles

| Controle | Valeur | Limite | Statut |
| --- | --- | --- | --- |
| Erreur frequence theorie fine | 0,007717 % | 1 % | PASS |
| Residu modal fin | 2,625e-12 | 1e-8 | PASS |
| Orthogonalite masse | 1,122e-16 | 1e-8 | PASS |
| Ecart frequence Code_Aster | 1,205e-13 | 1e-6 | PASS |

### Questions Owner

Q1 : Les quatre niveaux de maillage et la masse coherente couvrent-ils le domaine modal orthotrope teste ?

Reponse : `

Commentaire : `

Q2 : Les axes materiau, l'invariance de masse et les residus sont-ils acceptables ?

Reponse : `

Commentaire : `

Q3 : Les exclusions composite pli par pli, dommage et grandes deformations sont-elles maintenues ?

Reponse : `

Commentaire : `

Q4 : Decision Owner : owner_accepted ou accepted_with_recommendations ?

Reponse : `

Commentaire : `

### Limites et exclusions

- Aucune revendication de certification externe.
- La decision doit rester limitee aux preuves et aux observables listes.
- Dommage, rupture et delamination restent hors scope sauf mention contraire.
- Modele axial 3D borne; pas de champ d'orientation variable ni de dynamique distribuee generale.

### Preuves et artefacts

- `qualification/vnv/orthotropic_modal_newmark/reference/summary.json`
- `qualification/reviews/orthotropic_modal_owner_review_pending.json`
- `tests/verification/test_orthotropic_modal_newmark_vnv.py`

### Figures disponibles

- `qualification/vnv/orthotropic_modal_newmark/reference/modal_convergence.png`

## 10. Solide orthotrope transitoire Newmark

- **Scope :** `orthotropic-solid-transient-dynamic`
- **Etat actuel :** `supplementary_scope / ready_for_owner_review`
- **Cible proposee :** `owner_accepted (borne)`
- **Etat technique :** `PASS_EXTERNAL_CORRELATION`
- **Decision proposee, non enregistree :** `accepted_with_recommendations`

La reponse Newmark est verifiee sur huit pas de temps avec zero derive energetique archivee et une correlation Code_Aster sur la meme grille temporelle.

### Mesures disponibles

| Controle | Valeur | Limite | Statut |
| --- | --- | --- | --- |
| Erreur de raffinement temporel | 0,1119 % | 1 % | PASS |
| Residu dynamique maximal | 2,228e-10 | 1e-7 | PASS |
| Derive energetique | 0 | 1e-4 | PASS |
| Ecart historique Code_Aster | 6,254e-14 | 1e-5 | PASS |

### Questions Owner

Q1 : Les huit niveaux de pas et le schema Newmark couvrent-ils le domaine transitoire orthotrope teste ?

Reponse : `

Commentaire : `

Q2 : La masse, l'amortissement nul et les conventions d'axes sont-ils acceptables ?

Reponse : `

Commentaire : `

Q3 : Les exclusions non-linearite, dommage, grandes deformations et pli-par-pli sont-elles maintenues ?

Reponse : `

Commentaire : `

Q4 : Decision Owner : owner_accepted ou accepted_with_recommendations ?

Reponse : `

Commentaire : `

### Limites et exclusions

- Aucune revendication de certification externe.
- La decision doit rester limitee aux preuves et aux observables listes.
- Dommage, rupture et delamination restent hors scope sauf mention contraire.
- La validation ne couvre pas l'endommagement ni le composite pli par pli.
- La dynamique courbe et distribuee reste hors du perimetre.

### Preuves et artefacts

- `qualification/vnv/orthotropic_modal_newmark/reference/summary.json`
- `qualification/reviews/orthotropic_transient_dynamic_owner_review_pending.json`
- `tests/verification/test_orthotropic_modal_newmark_vnv.py`

### Figures disponibles

- `qualification/vnv/orthotropic_modal_newmark/reference/newmark_convergence.png`

## 11. Contact unilateral sans frottement

- **Scope :** `contact-v1-linear-static-bounded`
- **Etat actuel :** `owner_accepted / engineering_ready_bounded`
- **Cible proposee :** `accepted_for_bounded_engineering_use (maintien)`
- **Etat technique :** `PASS_EXTERNAL_CORRELATION`
- **Decision proposee, non enregistree :** `accepted_for_bounded_engineering_use`

Les cas ouverture/fermeture, face TET4 deformable, surface pliee et confirmation 9 984 TET4 sont documentes. Le resultat ne qualifie pas le contact general.

### Mesures disponibles

| Controle | Valeur | Limite | Statut |
| --- | --- | --- | --- |
| Ecart final sur 9 984 TET4 | 3,3029e-12 % | 5 % | PASS |
| Jeu final maximal | 9,7145e-16 m | 1e-8 m | PASS |
| Ecart moyen recherche de pli | 0,1157 % | 1 % | PASS |

### Questions Owner

Q1 : Les preuves de contact unilateral et les modeles complementaires couvrent-ils le domaine borne ?

Reponse : `

Commentaire : `

Q2 : Les gaps, reactions, normales et active-set sont-ils correctement interpretes ?

Reponse : `

Commentaire : `

Q3 : Les limites surface-surface general, grand glissement, impact et usure sont-elles acceptees ?

Reponse : `

Commentaire : `

Q4 : Decision Owner : maintenir accepted_for_bounded_engineering_use ou demander plus d'evidence ?

Reponse : `

Commentaire : `

### Limites et exclusions

- Aucune revendication de certification externe.
- La decision doit rester limitee aux preuves et aux observables listes.
- Dommage, rupture et delamination restent hors scope sauf mention contraire.
- Contact surface-surface general, grand glissement, impact et usure exclus.
- La decision ne s'etend pas au frottement.

### Preuves et artefacts

- `docs/verification/revue_contact_v1.md`
- `qualification/reviews/contact_v1_linear_static_bounded_2026-07-29.json`
- `results/VNV-CONTACT-ADDITIONAL-MODELS-008/`

### Figures disponibles

- `docs/assets/reviews/contact_code_aster_additional_curves.png`
- `docs/assets/reviews/contact_additional_models.png`

## 12. Contact statique avec frottement

- **Scope :** `contact-frictional-static`
- **Etat actuel :** `experimental`
- **Cible proposee :** `owner_accepted experimental borne`
- **Etat technique :** `PASS_EXTERNAL_CORRELATION_SLIP_ONLY`
- **Decision proposee, non enregistree :** `accepted_for_bounded_engineering_use`

Trois familles internes et trois niveaux par famille sont verifies. Code_Aster est compare sur trois charges tangentielles, uniquement sur la branche slip.

### Mesures disponibles

| Controle | Valeur | Limite | Statut |
| --- | --- | --- | --- |
| Ecart UX Code_Aster, charge 200 N | 0,607 % | 5 % | PASS |
| Ecart UX Code_Aster, charge 250 N | 0,456 % | 5 % | PASS |
| Ecart UX Code_Aster, charge 300 N | 0,365 % | 5 % | PASS |
| Families internes | 3 x 3 niveaux | preuve interne | PASS |

### Questions Owner

Q1 : Les trois familles et les trois niveaux de maillage sont-ils suffisants pour la branche slip ?

Reponse : `

Commentaire : `

Q2 : Le cone de Coulomb, les gaps et la dissipation sont-ils correctement verifies ?

Reponse : `

Commentaire : `

Q3 : La correlation Code_Aster slip est-elle acceptee comme preuve externe partielle ?

Reponse : `

Commentaire : `

Q4 : La branche stick, le grand glissement et le contact surface-surface general restent-ils hors scope ?

Reponse : `

Commentaire : `

Q5 : Decision Owner : owner_accepted experimental borne ou more_evidence_required ?

Reponse : `

Commentaire : `

### Limites et exclusions

- Aucune revendication de certification externe.
- La decision doit rester limitee aux preuves et aux observables listes.
- Dommage, rupture et delamination restent hors scope sauf mention contraire.
- La branche stick n'est pas fermee par correlation externe.
- Grand glissement, normales actualisees, impacts, usure et contact dynamique exclus.

### Preuves et artefacts

- `docs/verification/contact_frottement_vnv.md`
- `qualification/maturity_evidence_0_2_1/contact_frictional_static.json`
- `qualification/maturity_evidence_0_2_1/contact_frictional_family_survey/summary.json`

### Figures disponibles

- `qualification/maturity_evidence_0_2_1/contact_friction_code_aster_three_loads/code_aster_friction_comparison.png`
- `qualification/maturity_evidence_0_2_1/contact_frictional_family_survey/frictional_contact_family_survey.png`

## 13. Grand modele TET4 statique lineaire PETSc/MPI

- **Scope :** `large-tet4-linear-static`
- **Etat actuel :** `experimental / PASS_INTERNAL_WITH_LIMITATIONS`
- **Cible proposee :** `accepted_for_bounded_engineering_use`
- **Etat technique :** `PASS_SCALABLE_PIPELINE_WITH_LIMITED_SCALING`
- **Decision proposee, non enregistree :** `accepted_for_bounded_engineering_use`

Le chemin HDF5, MPI, assembleur par blocs, AIJ/BAIJ et KSP GAMG est verifie jusqu'a 3 millions de DDL. La mesure de scaling reste limitee a une station et une image conteneur.

### Mesures disponibles

| Controle | Valeur | Limite | Statut |
| --- | --- | --- | --- |
| Cas 1 M DDL | 1 029 000 DDL / 1 971 054 TET4 | PASS | PASS |
| Cas 3 M DDL | 3 000 000 DDL / 5 821 794 TET4 | PASS | PASS |
| Residue 3 M DDL | 8,997e-19 | diagnostic | PASS |
| Weak scaling, 4 rangs | 41,6 % | 60 % | WARNING |

### Questions Owner

Q1 : Les cas 100 k, 1 M et 3 M DDL demontrent-ils le perimetre TET4 isotrope statique ?

Reponse : `

Commentaire : `

Q2 : Les limites de machine, memoire, image Docker, PETSc/MPI et scaling sont-elles acceptables ?

Reponse : `

Commentaire : `

Q3 : Le statut bounded est-il prefere a une revendication HPC generale ?

Reponse : `

Commentaire : `

Q4 : Decision Owner : accepted_for_bounded_engineering_use ou more_evidence_required ?

Reponse : `

Commentaire : `

### Limites et exclusions

- Aucune revendication de certification externe.
- La decision doit rester limitee aux preuves et aux observables listes.
- Dommage, rupture et delamination restent hors scope sauf mention contraire.
- Une seule configuration materielle est mesuree; weak scaling 4 rangs sous le seuil provisoire.
- MITC4, TET10, non-lineaire, modal et transitoire grand modele exclus.

### Preuves et artefacts

- `qualification/maturity_evidence_0_2_1/large_tet4_linear_static.json`
- `results_large/qualification_matrix_free_1m/large_readiness.md`
- `tests/integration/test_large_model.py`

### Figures disponibles

- `docs/assets/generated/large_model_summary.png`

## 14. MITC4 orthotrope courbe

- **Scope :** `mitc4-orthotropic-curved-out-of-acceptance`
- **Etat actuel :** `out_of_acceptance`
- **Cible proposee :** `hors acceptance`
- **Etat technique :** `DIAGNOSTIC_ONLY`
- **Decision proposee, non enregistree :** `no_decision`

Ce cas est conserve comme diagnostic, pas comme dossier de promotion. L'orientation non axiale projetee sur une surface courbe n'est pas encore comparable de facon suffisante pour une acceptation.

### Mesures disponibles

| Controle | Valeur | Limite | Statut |
| --- | --- | --- | --- |
| Courbe mono-pli 0 deg, UZ | 0,012 % | diagnostic | PASS |
| Orientation courbe non axiale | preuve incomplete | hors acceptance | WARNING |
| Dommage / rupture / delamination | non traite | hors acceptance | WARNING |

### Questions Owner

Q1 : Confirmer que ce cas reste explicitement hors acceptance.

Reponse : `

Commentaire : `

Q2 : Confirmer qu'aucune preuve des solides orthotropes n'est reutilisee pour ce cas MITC4 courbe.

Reponse : `

Commentaire : `

Q3 : Confirmer que l'orientation continue courbe fera l'objet d'une campagne distincte.

Reponse : `

Commentaire : `

Q4 : Decision : hors acceptance, sans promotion.

Reponse : `

Commentaire : `

### Limites et exclusions

- Aucune revendication de certification externe.
- La decision doit rester limitee aux preuves et aux observables listes.
- Dommage, rupture et delamination restent hors scope sauf mention contraire.
- Orientation non axiale projetee sur surface courbe non qualifiee.
- Ce dossier ne doit pas etre compte parmi les scopes stables.

### Point de vigilance

Ce perimetre reste volontairement exclu et ne doit pas etre promu.

### Preuves et artefacts

- `docs/verification/mitc4_stable_package/owner_review.md`
- `qualification/studies/mitc4_stable_package_2026-08-21/study.json`
- `docs/verification/mitc4_same_order_oracle_probe.md`

### Figures disponibles

- `results/mitc4_orthotropic_curved_projected_one_ply_calculix_20260821/curved_orientation_correlation.png`

## Decision finale a completer par le Owner

- Nom du Owner :
- Date :
- Decision globale : `accepted_with_recommendations` / `accepted_for_bounded_engineering_use` / `more_evidence_required`
- Commentaire :

Cette page ne constitue pas une certification, une revue independante ou une promotion automatique.
