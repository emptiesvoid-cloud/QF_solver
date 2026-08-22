---
doc_id: DOC-OWNER-REVIEW-021-OPEN
revision: 0.1
status: ready_for_owner_review
applicable_version: 0.2.1a0
decision: pending
certification_claim: none
---

# Gates Owner ouverts - QF_solver 0.2.1 alpha

Ce document est genere depuis les registres de maturite et ne contient aucune decision pre-remplie.
Une revue documentee ne vaut ni certification ni equivalence generale avec un autre solveur.

Nombre de scopes : **3**.

## `tet4-total-lagrangian-structural-v2`

- Etat courant : `research`.
- Cible proposee : `research`.
- Statut technique : `BLOCKED`.
- Gate : `BLOCKED_OWNER_REVIEW`.
- Classification : `owner_decision_pending`.

Ce gate requiert une relecture independante. Une decision du proprietaire seule ne peut pas fermer le critere d'independance ni promouvoir ce scope au-dela du statut research borne.

### Donnees numeriques a controler

| Fichier | Mesure | Valeur |
| --- | --- | ---: |
| `qualification/reviews/tet4_total_lagrangian_structural_v2_2026-07-18.json` | `schema_version` | `1` |
| `qualification/evidence/code_aster_correlation_campaign_2026-08-14/studies/tl_structural/summary.json` | `stress_patch.elements` | `96` |
| `qualification/evidence/code_aster_correlation_campaign_2026-08-14/studies/tl_structural/summary.json` | `stress_patch.boundary_nodes` | `42` |
| `qualification/evidence/code_aster_correlation_campaign_2026-08-14/studies/tl_structural/summary.json` | `stress_patch.relative_error` | `8.54422e-05` |
| `qualification/evidence/code_aster_correlation_campaign_2026-08-14/studies/tl_structural/summary.json` | `imperfect_column.elements` | `1536` |
| `qualification/evidence/code_aster_correlation_campaign_2026-08-14/studies/tl_structural/summary.json` | `imperfect_column.imperfection_ratio` | `0.005` |
| `qualification/evidence/code_aster_correlation_campaign_2026-08-14/studies/tl_structural/summary.json` | `imperfect_column.critical_load_qf` | `1115.47` |
| `qualification/evidence/code_aster_correlation_campaign_2026-08-14/studies/tl_structural/summary.json` | `imperfect_column.maximum_relative_difference` | `1.69299e-09` |

### Figures de preuve

![Figure de preuve](/qualification/evidence/code_aster_correlation_campaign_2026-08-14/studies/tl_structural/code_aster_column_path.png)
*qualification/evidence/code_aster_correlation_campaign_2026-08-14/studies/tl_structural/code_aster_column_path.png*  
![Figure de preuve](/qualification/evidence/code_aster_correlation_campaign_2026-08-14/studies/tl_structural/code_aster_stress_comparison.png)
*qualification/evidence/code_aster_correlation_campaign_2026-08-14/studies/tl_structural/code_aster_stress_comparison.png*  

### Criteres

| ID | Objet | Statut |
| --- | --- | --- |
| `TET4-TL-C01` | Verification TL, convergence et domaine | `PASS` |
| `TET4-TL-C01B` | Politique d'increments explicite | `PASS` |
| `TET4-TL-C02` | Correlation structurale Code_Aster | `PASS` |
| `TET4-TL-C03` | Dossier TL et tests | `PASS` |
| `TET4-TL-C04` | Revue independante avant qualification externe | `FAIL` |

### Questions

- **Q1** Le domaine total-lagrangien et les limites de grandes rotations sont-ils correctement delimites ? Reponse : ____
- **Q2** Les comparaisons, increments de chargement et imperfections sont-ils suffisants pour une relecture independante ? Reponse : ____
- **Q3** Les exclusions contact, rupture, endommagement et extrapolation hors des cas testes sont-elles acceptees ? Reponse : ____
- **Q4** La recommandation de maintenir le statut research est-elle confirmee ? Reponse : ____

### Reponses Owner proposees - brouillon non signe

| ID | Reponse |
| --- | --- |
| `Q1` | OUI - Flambement total-lagrangien TET4 couvert par les preuves structurales. |
| `Q2` | OUI - PETSc/MPI, materiau isotrope et limites memoire explicites. |
| `Q3` | OUI - Convergence vers le critere de charge Euler documentee. |
| `Q4` | more_evidence_required - Une revue independante est obligatoire avant fermeture du gate. |
Ces reponses facilitent la revue et ne modifient pas la maturite tant que la fiche signee n'est pas enregistree.

### Decision

Cette ligne exige une relecture independante; une auto-decision Owner ne ferme pas le critere.

Fiche controlee : `qualification/reviews/tet4_total_lagrangian_independent_review_pending.json`.

## `mitc3-laminate-dynamic-thin-planar`

- Etat courant : `supplementary_scope`.
- Cible proposee : `stable`.
- Statut technique : `BLOCKED`.
- Gate : `BLOCKED_OWNER_REVIEW`.
- Classification : `owner_decision_pending`.

### Donnees numeriques a controler

| Fichier | Mesure | Valeur |
| --- | --- | ---: |
| `qualification/vnv/external/code_aster_mitc3_laminate_dynamic_refinement_dkt_2026-08-21/reference/summary.json` | `schema_version` | `1` |
| `qualification/vnv/external/code_aster_mitc3_laminate_dynamic_refinement_dkt_2026-08-21/reference/summary.json` | `external_solver.shear_correction_factor` | `0.833333` |
| `qualification/vnv/external/code_aster_mitc3_laminate_dynamic_refinement_dkt_2026-08-21/reference/summary.json` | `mesh_level_count` | `3` |
| `qualification/vnv/external/code_aster_mitc3_laminate_dynamic_refinement_dkt_2026-08-21/reference/summary.json` | `comparison_basis.shear_correction_factor` | `0.833333` |
| `qualification/vnv/external/code_aster_mitc3_laminate_dynamic_refinement_dkt_2026-08-21/reference/vnv_manifest.json` | `schema_version` | `1` |
| `qualification/vnv/mitc3_laminate_temporal_refinement_2026-08-21/summary.json` | `model.element_count` | `32` |
| `qualification/vnv/mitc3_laminate_temporal_refinement_2026-08-21/summary.json` | `time_level_count` | `3` |
| `qualification/vnv/mitc3_mass_quadrature_audit_2026-08-21/summary.json` | `quadrature.reference_triangle_area` | `0.5` |

### Figures de preuve

![Figure de preuve](/qualification/vnv/external/code_aster_mitc3_laminate_dynamic_refinement_dkt_2026-08-21/reference/mitc3_laminate_dynamic_refinement.png)
*qualification/vnv/external/code_aster_mitc3_laminate_dynamic_refinement_dkt_2026-08-21/reference/mitc3_laminate_dynamic_refinement.png*  
![Figure de preuve](/qualification/vnv/mitc3_laminate_temporal_refinement_2026-08-21/VNV-MITC3-LAMINATE-TEMPORAL-REFINEMENT-001-convergence.png)
*qualification/vnv/mitc3_laminate_temporal_refinement_2026-08-21/VNV-MITC3-LAMINATE-TEMPORAL-REFINEMENT-001-convergence.png*  

### Criteres

| ID | Objet | Statut |
| --- | --- | --- |
| `MITC3-LAM-DYN-THIN-C01` | Correlation DKT du sous-perimetre mince plan | `PASS` |
| `MITC3-LAM-DYN-THIN-C02` | Dossier de preuve et limites du sous-perimetre | `PASS` |
| `MITC3-LAM-DYN-THIN-C03` | Decision Owner de promotion stable | `FAIL` |

### Questions

- **Q1** Le domaine mince, plan, symetrique et a petits deplacements est-il correctement borne ? Reponse : ____
- **Q2** Les ecarts au niveau fin (0,3940 % modal, 0,1968 % Newmark, 0,0880 % harmonique) sont-ils acceptables ? Reponse : ____
- **Q3** Les niveaux intermediaires, dont le modal reste au-dessus de 1 %, sont-ils suffisamment traces sans etre masques par le seul niveau final ? Reponse : ____
- **Q4** DKT est-il accepte comme reference de limite mince, distincte de DST, sans extrapolation aux coques epaisses ou courbes ? Reponse : ____
- **Q5** Les exclusions (courbure, epaisseur importante, couplage B non nul, dommage, delamination, contraintes dynamiques par pli) sont-elles acceptees ? Reponse : ____
- **Q6** stable pour ce sous-perimetre, accepted_with_recommendations, accepted_for_bounded_engineering_use ou more_evidence_required ? Reponse : ____

### Reponses Owner proposees - brouillon non signe

| ID | Reponse |
| --- | --- |
| `Q1` | OUI - Les preuves disponibles couvrent le domaine explicitement borne. |
| `Q2` | OUI - Les limites, exclusions et conventions sont acceptees pour cet usage borne. |
| `Q3` | OUI - La maturite proposee est acceptee sans extrapolation aux cas non testes. |
| `Q4` | accepted_with_recommendations - Conserver les limites et poursuivre les preuves recommandees. |
| `Q5` | A repondre par le Owner. |
| `Q6` | accepted_with_recommendations - Conserver les limites et poursuivre les preuves recommandees. |
Ces reponses facilitent la revue et ne modifient pas la maturite tant que la fiche signee n'est pas enregistree.

### Decision

Decision : `__________`  Nom : `__________`  Date : `__________`  Signature : `__________`

Fiche controlee : `qualification/reviews/mitc3_laminate_dynamic_dkt_thin_owner_review_pending.json`.

## `mitc3-laminate-static-curved-mixed-transverse`

- Etat courant : `supplementary_scope`.
- Cible proposee : `stable`.
- Statut technique : `BLOCKED`.
- Gate : `BLOCKED_OWNER_REVIEW`.
- Classification : `owner_decision_pending`.

### Donnees numeriques a controler

| Fichier | Mesure | Valeur |
| --- | --- | ---: |
| `qualification/maturity_evidence_0_2_1/mitc3_laminate.json` | `schema_version` | `1` |
| `qualification/maturity_evidence_0_2_1/mitc3_laminate.json` | `scopes.mitc3-laminate-static.internal_and_external_campaign.mesh_level_count` | `3` |
| `qualification/maturity_evidence_0_2_1/mitc3_laminate.json` | `scopes.mitc3-laminate-static.internal_and_external_campaign.qf_affine_patch_error_max` | `2.27842e-13` |
| `qualification/maturity_evidence_0_2_1/mitc3_laminate.json` | `scopes.mitc3-laminate-static.internal_and_external_campaign.qf_final_stress_increment` | `1.19796e-14` |
| `qualification/maturity_evidence_0_2_1/mitc3_laminate.json` | `scopes.mitc3-laminate-static.internal_and_external_campaign.calculix_final_stress_increment` | `0.000731343` |
| `qualification/maturity_evidence_0_2_1/mitc3_laminate.json` | `scopes.mitc3-laminate-static.internal_and_external_campaign.fine_material_ply_stress_difference` | `0.000962468` |
| `qualification/maturity_evidence_0_2_1/mitc3_laminate.json` | `scopes.mitc3-laminate-static-curved.internal_and_external_campaign.geometry_count` | `1` |
| `qualification/maturity_evidence_0_2_1/mitc3_laminate.json` | `scopes.mitc3-laminate-static-curved.internal_and_external_campaign.load_family_count` | `2` |

### Figures de preuve

![Figure de preuve](/qualification/maturity_evidence_0_2_1/mitc3_laminate_curved_load_families/convergence_qf_code_aster.png)
*qualification/maturity_evidence_0_2_1/mitc3_laminate_curved_load_families/convergence_qf_code_aster.png*  
![Figure de preuve](/qualification/maturity_evidence_0_2_1/mitc3_laminate_curved_load_families/convergence_qf_code_aster_transverse.png)
*qualification/maturity_evidence_0_2_1/mitc3_laminate_curved_load_families/convergence_qf_code_aster_transverse.png*  

### Criteres

| ID | Objet | Statut |
| --- | --- | --- |
| `MITC3-LAM-STAT-CURVE-MT-C01` | Correlation courbe mixte et transverse sous 1 pour cent | `PASS` |
| `MITC3-LAM-STAT-CURVE-MT-C02` | Artefacts de preuve du sous-scope courbe | `PASS` |
| `MITC3-LAM-STAT-CURVE-MT-C03` | Decision Owner du sous-scope courbe | `FAIL` |

### Questions

- **Q1** Les preuves du scope mitc3-laminate-static-curved-mixed-transverse couvrent-elles le domaine revendique ? Reponse : ____
- **Q2** Les limites, exclusions, singularites et conventions sont-elles acceptables ? Reponse : ____
- **Q3** La maturite ciblee est-elle appropriee sans extrapolation aux cas non testes ? Reponse : ____
- **Q4** Quelle decision Owner doit etre enregistree pour ce scope ? Reponse : ____

### Reponses Owner proposees - brouillon non signe

| ID | Reponse |
| --- | --- |
| `Q1` | OUI - Les preuves disponibles couvrent le domaine explicitement borne. |
| `Q2` | OUI - Les limites, exclusions et conventions sont acceptees pour cet usage borne. |
| `Q3` | OUI - La maturite proposee est acceptee sans extrapolation aux cas non testes. |
| `Q4` | accepted_with_recommendations - Conserver les limites et poursuivre les preuves recommandees. |
Ces reponses facilitent la revue et ne modifient pas la maturite tant que la fiche signee n'est pas enregistree.

### Decision

Decision : `__________`  Nom : `__________`  Date : `__________`  Signature : `__________`

Fiche controlee : `qualification/reviews/mitc3_laminate_curved_mixed_transverse_stable_owner_review_pending.json`.
