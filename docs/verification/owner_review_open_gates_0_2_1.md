---
doc_id: DOC-OWNER-REVIEW-021-OPEN
revision: 0.1
status: ready_for_owner_review
applicable_version: 0.2.1a0
decision: pending
certification_claim: none
reviewer: ''
approver: ''
---

# Gates Owner ouverts - QF_solver 0.2.1 alpha

Ce document est genere depuis les registres de maturite et ne contient aucune decision pre-remplie.
Une revue documentee ne vaut ni certification ni equivalence generale avec un autre solveur.

Nombre de scopes : **3**.

## `tet4-total-lagrangian-structural-v2`

- Etat courant : `research`.
- Cible proposee : `research`.
- Statut technique : `BLOCKED`.
- Gate : `BLOCKED_INDEPENDENT_REVIEW`.
- Classification : `owner_decision_pending`.

Ce gate requiert une relecture independante. Une decision du proprietaire seule ne peut pas fermer le critere d'independance ni promouvoir ce scope au-dela du statut research borne.

### Donnees numeriques a controler

| Fichier | Mesure | Valeur |
| --- | --- | ---: |
| `qualification/reviews/tet4_total_lagrangian_independent_review_pending.json` | `schema_version` | `1` |
| `qualification/reviews/tet4_total_lagrangian_independent_review_pending.json` | `technical_snapshot.constitutive_stress_error` | `8.54422e-05` |
| `qualification/reviews/tet4_total_lagrangian_independent_review_pending.json` | `technical_snapshot.imperfect_column_max_relative_difference` | `1.69299e-09` |
| `qualification/reviews/tet4_total_lagrangian_independent_review_pending.json` | `technical_snapshot.refined_buckling_euler_error` | `0.0189556` |
| `qualification/reviews/tet4_total_lagrangian_independent_review_pending.json` | `technical_snapshot.refined_qf_calculix_difference` | `0.000342738` |
| `qualification/reviews/tet4_total_lagrangian_independent_review_pending.json` | `technical_snapshot.newton_residual_max` | `7.97179e-11` |

### Figures de preuve

![Figure de preuve](/docs/assets/reviews/tet4_tl_assembly_convergence.png)
*docs/assets/reviews/tet4_tl_assembly_convergence.png*

### Criteres

| ID | Objet | Statut |
| --- | --- | --- |
| `TET4-TL-C01` | Verification TL et convergence. L erreur Euler de charge critique passe de 5.870 pour cent a 1.896 pour cent. | `PASS` |
| `TET4-TL-C02` | Correlation structurale externe | `PASS` |
| `TET4-TL-C03` | Dossier et tests | `PASS` |
| `TET4-TL-C04` | Relecture independante avant qualification externe | `FAIL` |

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
| `qualification/reviews/mitc3_laminate_dynamic_dkt_thin_owner_review_pending.json` | `schema_version` | `1` |
| `qualification/reviews/mitc3_laminate_dynamic_dkt_thin_owner_review_pending.json` | `scope_under_review.thickness_to_length_ratio` | `0.01` |

### Figures de preuve

![Figure de preuve](/docs/assets/reviews/mitc3_laminate_code_aster_comparison.png)
*docs/assets/reviews/mitc3_laminate_code_aster_comparison.png*

### Criteres

| ID | Objet | Statut |
| --- | --- | --- |
| `MITC3-LAM-DYN-THIN-C01` | Correlation DKT du sous-perimetre mince plan | `PASS` |
| `MITC3-LAM-DYN-THIN-C02` | Dossier de preuve et limites | `PASS` |
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

### Figures de preuve

![Figure de preuve](/docs/assets/reviews/mitc3_curved_laminate_code_aster_convergence.png)
*docs/assets/reviews/mitc3_curved_laminate_code_aster_convergence.png*
![Figure de preuve](/docs/assets/reviews/mitc3_curved_laminate_code_aster_deformation.png)
*docs/assets/reviews/mitc3_curved_laminate_code_aster_deformation.png*

### Criteres

| ID | Objet | Statut |
| --- | --- | --- |
| `MITC3-LAM-STAT-CURVE-MT-C01` | Correlation courbe mixte et transverse sous un pour cent | `PASS` |
| `MITC3-LAM-STAT-CURVE-MT-C02` | Artefacts de preuve du sous-scope courbe | `PASS` |
| `MITC3-LAM-STAT-CURVE-MT-C03` | Decision Owner du sous-scope courbe | `FAIL` |

### Questions

- **Q1** Les preuves courbes mixtes et transverses couvrent-elles le sous-domaine borne ? Reponse : ____
- **Q2** Les exclusions de chargement axial et de contraintes par pli sont-elles acceptables ? Reponse : ____
- **Q3** Les ecarts sous un pour cent et les increments finaux sont-ils suffisants ? Reponse : ____
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
