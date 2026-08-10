---
doc_id: DOC-STATE-002
revision: 0.3
status: draft technique
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Capacites et maturite

La maturite affichee provient du registre
`qualification/requirements.json`, source autoritative. Elle qualifie le
niveau de preuve logiciel et mecanique disponible, pas la complexite de la
fonction.

| Capacite | Maturite courante | Usage recommande |
| --- | --- | --- |
| TET4 statique lineaire isotrope | `stable` | Cas bornes avec maillage et audit acceptes |
| MITC4 statique lineaire | `engineering_internal_validated_with_recommendations` | Domaine borne; reserve Cook et correlation Abaqus partielle |
| MITC3+ statique lineaire | `engineering_internal_validated` | Domaine borne accepte le 1er aout 2026; dynamique dans des scopes separes |
| MITC4 modal | `engineering_internal_provisional` | Masse coherente uniquement; revue independante ouverte |
| MITC4 Newmark | `engineering_internal_validated_with_recommendations` | Masse coherente, petit deplacement et pas justifie |
| MITC3+ modal/Newmark/harmonique | `verified_development` | Routes et invariants testes; campagnes analytiques et externes dediees encore requises |
| TET10 lineaire isotrope | `stable_after_reinforced_tests` | Validation interne avec recommandations; campagne complexe finale differee |
| Charges reparties coherentes | `stable_after_reinforced_tests` | Pression, traction, gravite avec controle de resultante |
| Modal lineaire | `stable_after_reinforced_tests` | Interpretation sous controle des residus et masses modales |
| Newmark lineaire | `stable_after_reinforced_tests` | Petits deplacements et pas de temps justifie |
| Harmonique direct | `stable_after_reinforced_tests` | Systeme lineaire et amortissement Rayleigh documente |
| Condensation harmonique MITC4 | `candidate_technique` | Rayleigh complet prouve; integree au scope accepte avec recommandations |
| Reponse harmonique MITC4 | `engineering_internal_validated_with_recommendations` | Large bande, contraintes complexes et NAFEMS 13H PASS |
| Non-lineaire materiau | `experimental` | Recherche et verification chemin par chemin |
| Arc-length | `experimental` | Cas pilotes, revue numerique obligatoire |
| Lamelle, CLT et MITC4 multicouche | `experimental` | Statique lineaire exploratoire, contraintes par pli |
| Solides orthotropes TET4/TET10 | `engineering_internal_validated_with_recommendations` | Statique lineaire borne; TET10 recommande en flexion, campagne complexe finale differee |
| Grand modele PETSc/MPI | `experimental` | Benchmark et developpement, environnement trace |
| Import Gmsh MSH 4.1 | `stable_after_reinforced_tests` | TET4/TET10/MITC4, groupes physiques stricts |
| BEAM2 Timoshenko 3D | `experimental` | Statique et six modes d'une poutre elancee correles a Code_Aster; cisaillement epais, amortissement et assemblages dynamiques ouverts |
| Ressorts et masses concentrees | `experimental` | SDOF statique/modal correle a Code_Aster; donnees physiques strictement validees, cas spatiaux avances ouverts |
| MPC et RBE2/RBE3 | `experimental` | Statique lineaire avec elimination affine, audit des reactions et correlation Code_Aster RBE2 bornee; RBE3/dynamique ouverts |
| Contact sans frottement borne | `engineering_ready_bounded` | Owner review acceptee; petites transformations, statique lineaire et active-set noeud-triangle, avec raffinement des transitions |
| Contact sans frottement generalise | `experimental` | Grand glissement, changement topologique et surface-surface restent hors du domaine accepte |
| Contact avec frottement | `experimental` | Coulomb regularise, adhesion/glissement et correlation Code_Aster en glissement sature; adhesion externe non comparable |
| Onze benchmarks mailles | maturite par cas | Regeneration obligatoire avant publication |

## Sens des niveaux

**Stable.** Fonction couverte par tests, audit et au moins une preuve
independante dans son perimetre borne.

**Stable apres tests renforces.** Fonction utilisable en profil engineering,
mais dont la campagne de references industrielles doit encore etre elargie.

**Experimental.** Implementation disponible et testee, mais preuve mecanique
insuffisante pour remplacer sans correlation un outil de reference.

**Research.** Fonction exploratoire sans domaine d'emploi industriel etabli.

La commande `qualification-readiness` reste l'autorite pour la completude des
exigences; cette page n'eleve jamais seule un niveau de maturite.
