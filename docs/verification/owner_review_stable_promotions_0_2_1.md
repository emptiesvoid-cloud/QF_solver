---

doc_id: DOC-OWNER-REVIEW-021-STABLE
revision: 0.1
status: ready_for_owner_review
applicable_version: 0.2.1a0
decision: pending
certification_claim: none
reviewer: ""
approver: ""
---

# Promotions techniquement pretes - QF_solver 0.2.1 alpha

Ce document est genere depuis les registres de maturite et ne contient aucune decision pre-remplie.
Une revue documentee ne vaut ni certification ni equivalence generale avec un autre solveur.

Nombre de scopes : **3**.

## `orthotropic-solid-tet4-tet10`

- Etat courant : `supplementary_scope`.
- Cible proposee : `stable`.
- Statut technique : `PASS`.
- Gate : `READY_FOR_OWNER_REVIEW`.
- Classification : `none`.

### Donnees numeriques a controler

| Fichier | Mesure | Valeur |
| --- | --- | ---: |
| `qualification/maturity_evidence_0_2_1/orthotropic.json` | `schema_version` | `1` |
| `qualification/maturity_evidence_0_2_1/orthotropic.json` | `scopes.orthotropic-solid-tet4-tet10.static.external_case_count` | `2` |
| `qualification/maturity_evidence_0_2_1/orthotropic.json` | `scopes.orthotropic-solid-tet4-tet10.static.calculix_displacement_l2_max` | `1.32142e-06` |
| `qualification/maturity_evidence_0_2_1/orthotropic.json` | `scopes.orthotropic-solid-tet4-tet10.static.code_aster_displacement_l2_max` | `4.17311e-12` |
| `qualification/maturity_evidence_0_2_1/orthotropic.json` | `scopes.orthotropic-solid-tet4-tet10.static.code_aster_von_mises_peak_difference_max` | `6.57877e-12` |
| `qualification/maturity_evidence_0_2_1/orthotropic.json` | `scopes.orthotropic-solid-tet4-tet10.static.tet4_convergence_level_count` | `9` |
| `qualification/maturity_evidence_0_2_1/orthotropic.json` | `scopes.orthotropic-solid-tet4-tet10.static.tet4_final_deflection_error` | `0.0282829` |
| `qualification/maturity_evidence_0_2_1/orthotropic.json` | `scopes.orthotropic-solid-tet4-tet10.static.tet4_final_energy_error` | `0.0285589` |

### Figures de preuve

![Figure de preuve](/qualification/vnv/orthotropic_solid_convergence/reference/orthotropic_convergence.png)
*qualification/vnv/orthotropic_solid_convergence/reference/orthotropic_convergence.png*  
![Figure de preuve](/qualification/vnv/orthotropic_solid_convergence_refined/reference/orthotropic_convergence.png)
*qualification/vnv/orthotropic_solid_convergence_refined/reference/orthotropic_convergence.png*  

### Criteres

| ID | Objet | Statut |
| --- | --- | --- |
| `ORTHO-STAT-C01` | Verification statique et correlation externe orthotrope | `PASS` |
| `ORTHO-STAT-C02` | Dossier statique, grand modele interne et limites | `PASS` |

### Questions

- **Q1** Les preuves du scope orthotropic-solid-tet4-tet10 couvrent-elles le domaine revendique ? Reponse : ____
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

## `orthotropic-solid-modal`

- Etat courant : `supplementary_scope`.
- Cible proposee : `stable`.
- Statut technique : `PASS`.
- Gate : `READY_FOR_OWNER_REVIEW`.
- Classification : `none`.

### Donnees numeriques a controler

| Fichier | Mesure | Valeur |
| --- | --- | ---: |
| `qualification/maturity_evidence_0_2_1/orthotropic.json` | `schema_version` | `1` |
| `qualification/maturity_evidence_0_2_1/orthotropic.json` | `scopes.orthotropic-solid-tet4-tet10.static.external_case_count` | `2` |
| `qualification/maturity_evidence_0_2_1/orthotropic.json` | `scopes.orthotropic-solid-tet4-tet10.static.calculix_displacement_l2_max` | `1.32142e-06` |
| `qualification/maturity_evidence_0_2_1/orthotropic.json` | `scopes.orthotropic-solid-tet4-tet10.static.code_aster_displacement_l2_max` | `4.17311e-12` |
| `qualification/maturity_evidence_0_2_1/orthotropic.json` | `scopes.orthotropic-solid-tet4-tet10.static.code_aster_von_mises_peak_difference_max` | `6.57877e-12` |
| `qualification/maturity_evidence_0_2_1/orthotropic.json` | `scopes.orthotropic-solid-tet4-tet10.static.tet4_convergence_level_count` | `9` |
| `qualification/maturity_evidence_0_2_1/orthotropic.json` | `scopes.orthotropic-solid-tet4-tet10.static.tet4_final_deflection_error` | `0.0282829` |
| `qualification/maturity_evidence_0_2_1/orthotropic.json` | `scopes.orthotropic-solid-tet4-tet10.static.tet4_final_energy_error` | `0.0285589` |

### Figures de preuve

![Figure de preuve](/qualification/vnv/orthotropic_modal_newmark/reference/code_aster_newmark.png)
*qualification/vnv/orthotropic_modal_newmark/reference/code_aster_newmark.png*  
![Figure de preuve](/qualification/vnv/orthotropic_modal_newmark/reference/modal_convergence.png)
*qualification/vnv/orthotropic_modal_newmark/reference/modal_convergence.png*  

### Criteres

| ID | Objet | Statut |
| --- | --- | --- |
| `ORTHO-MOD-C01` | Verification modale interne orthotrope | `PASS` |
| `ORTHO-MOD-C02` | Correlation modale Code_Aster | `PASS` |
| `ORTHO-MOD-C03` | Dossier modal et tests | `PASS` |
| `ORTHO-MOD-C04` | Decision Owner dediee au modal | `PASS` |

### Questions

- **Q1** La masse, les frequences et les modes propres couvrent-ils le perimetre orthotrope modal teste, avec 4 niveaux de maillage et une erreur theorique fine de 0,00772 % ? Reponse : ____
- **Q2** Les conventions d'axes materiau, la positivite et les limites d'anisotropie sont-elles acceptables, avec une correlation Code_Aster de 1,20e-13 ? Reponse : ____
- **Q3** Le statut stable est-il approprie uniquement pour le domaine TET4 orthotrope modal axial teste, sans extrapolation aux structures composites pli par pli ? Reponse : ____
- **Q4** Decision Owner pour la cible stable : accepted, accepted_with_recommendations ou more_evidence_required ? Reponse : ____

### Reponses Owner proposees - brouillon non signe

| ID | Reponse |
| --- | --- |
| `Q1` | OUI - Domaine orthotrope modal explicitement borne couvert. |
| `Q2` | OUI - Conventions des axes materiau acceptees pour ce domaine. |
| `Q3` | OUI - Convergence maillage et correlation externe disponibles. |
| `Q4` | accepted_with_recommendations |
Ces reponses facilitent la revue et ne modifient pas la maturite tant que la fiche signee n'est pas enregistree.

### Decision

Decision : `__________`  Nom : `__________`  Date : `__________`  Signature : `__________`

Fiche controlee : `qualification/reviews/orthotropic_modal_owner_review_pending.json`.

## `orthotropic-solid-transient-dynamic`

- Etat courant : `supplementary_scope`.
- Cible proposee : `stable`.
- Statut technique : `PASS`.
- Gate : `READY_FOR_OWNER_REVIEW`.
- Classification : `none`.

### Donnees numeriques a controler

| Fichier | Mesure | Valeur |
| --- | --- | ---: |
| `qualification/maturity_evidence_0_2_1/orthotropic.json` | `schema_version` | `1` |
| `qualification/maturity_evidence_0_2_1/orthotropic.json` | `scopes.orthotropic-solid-tet4-tet10.static.external_case_count` | `2` |
| `qualification/maturity_evidence_0_2_1/orthotropic.json` | `scopes.orthotropic-solid-tet4-tet10.static.calculix_displacement_l2_max` | `1.32142e-06` |
| `qualification/maturity_evidence_0_2_1/orthotropic.json` | `scopes.orthotropic-solid-tet4-tet10.static.code_aster_displacement_l2_max` | `4.17311e-12` |
| `qualification/maturity_evidence_0_2_1/orthotropic.json` | `scopes.orthotropic-solid-tet4-tet10.static.code_aster_von_mises_peak_difference_max` | `6.57877e-12` |
| `qualification/maturity_evidence_0_2_1/orthotropic.json` | `scopes.orthotropic-solid-tet4-tet10.static.tet4_convergence_level_count` | `9` |
| `qualification/maturity_evidence_0_2_1/orthotropic.json` | `scopes.orthotropic-solid-tet4-tet10.static.tet4_final_deflection_error` | `0.0282829` |
| `qualification/maturity_evidence_0_2_1/orthotropic.json` | `scopes.orthotropic-solid-tet4-tet10.static.tet4_final_energy_error` | `0.0285589` |

### Figures de preuve

![Figure de preuve](/qualification/vnv/orthotropic_modal_newmark/reference/code_aster_newmark.png)
*qualification/vnv/orthotropic_modal_newmark/reference/code_aster_newmark.png*  
![Figure de preuve](/qualification/vnv/orthotropic_modal_newmark/reference/modal_convergence.png)
*qualification/vnv/orthotropic_modal_newmark/reference/modal_convergence.png*  

### Criteres

| ID | Objet | Statut |
| --- | --- | --- |
| `ORTHO-NEW-C01` | Verification Newmark interne orthotrope | `PASS` |
| `ORTHO-NEW-C02` | Correlation Newmark Code_Aster | `PASS` |
| `ORTHO-NEW-C03` | Dossier transitoire et tests | `PASS` |
| `ORTHO-NEW-C04` | Decision Owner dediee au transitoire | `PASS` |

### Questions

- **Q1** La reponse Newmark couvre-t-elle le perimetre orthotrope teste avec 8 niveaux de pas, un increment final de 0,1119 % et un residu maximal de 2,23e-10 ? Reponse : ____
- **Q2** Les choix de masse, pas de temps, amortissement nul et axes materiau sont-ils acceptables pour le domaine stable explicitement borne ? Reponse : ____
- **Q3** Les exclusions de non-linearite, endommagement, grandes deformations et composite pli par pli sont-elles maintenues ? Reponse : ____
- **Q4** Decision Owner pour la cible stable : accepted, accepted_with_recommendations ou more_evidence_required ? Reponse : ____

### Reponses Owner proposees - brouillon non signe

| ID | Reponse |
| --- | --- |
| `Q1` | OUI - Reponse Newmark, stabilite et residus couverts. |
| `Q2` | OUI - Masse, pas de temps et amortissement acceptables. |
| `Q3` | OUI - Non-linearite et endommagement exclus explicitement. |
| `Q4` | accepted_with_recommendations |
Ces reponses facilitent la revue et ne modifient pas la maturite tant que la fiche signee n'est pas enregistree.

### Decision

Decision : `__________`  Nom : `__________`  Date : `__________`  Signature : `__________`

Fiche controlee : `qualification/reviews/orthotropic_transient_dynamic_owner_review_pending.json`.
