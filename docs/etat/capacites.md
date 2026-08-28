---
doc_id: DOC-STATE-002
revision: 0.4
status: draft
applicable_version: 0.2.5a0
reviewer: ""
approver: ""
---

# Capacites et maturite

Cette page resume la maturite observable dans le depot. Elle ne remplace pas
les matrices V&V de chaque release. `QUALIFIED / BOUNDED` signifie que les
preuves et les gates sont fermees dans une enveloppe explicitement limitee ;
cela ne constitue pas une qualification generale.

## Release 0.2.5a0

| Statut | Capacite | Enveloppe de preuve |
| --- | --- | --- |
| `QUALIFIED / BOUNDED` | J2 small-strain | TET4, TET10, HEX8 et HEX20 ; chemins et correlation Code_Aster documentes |
| `QUALIFIED / BOUNDED` | Elasticite Total-Lagrangian | TET4 et HEX8, domaine pre-limite avec `det(F) > 0` |
| `QUALIFIED / BOUNDED` | Flambement lineaire sparse | Premier seuil d'instabilite tangentielle, evidence Euler et correlation TET4 bornee |
| `QUALIFIED / BOUNDED` | Contact sans frottement | Noeud/patch vers surface triangulee, recherche et transitions dans le contrat G05 |
| `QUALIFIED / BOUNDED` | Performance | Caracterisation reproductible des chemins mesures, sans claim HPC general |
| `QUALIFIED / BOUNDED` | Modes d'echec | Diagnostics structures et transactions d'etat pour la matrice G09 |
| `EXPERIMENTAL / NOT QUALIFIED` | Arc-length FEM complet | Branche et point limite observes, mais pas de claim qualifie 0.2.5a0 |
| `EXPERIMENTAL / NOT QUALIFIED` | J2 finite-kinematic | Implementation de recherche, formulation et correlation externe non qualifiees |
| `EXPERIMENTAL / NOT QUALIFIED` | Couplages non lineaires | J2 + geometrie, geometrie + contact et couplage triple hors claims qualifies |
| `NOT IN RELEASE SCOPE` | Contact avec frottement | G07 non promue dans cette release |

## Autres capacites documentees

| Capacite | Maturite | Restriction principale |
| --- | --- | --- |
| TET4/TET10 lineaires | `stable_after_reinforced_tests` | Domaine de maillage et de chargement documente |
| HEX8/HEX20 lineaires | `accepted_for_release_0_2_3` | Scope 0.2.3a0, sans promotion stable generale |
| MITC3+/MITC4 | `engineering_internal_validated` ou `with_recommendations` | Voir les pages element et les revues Owner |
| BEAM2 et entites discretes | `experimental` ou scope borne | Assemblages et domaines dynamiques avances ouverts |
| Grands modeles PETSc/MPI | `experimental` | Environnement et tailles qualifies separement |
| Import Gmsh MSH 4.1 | `stable_after_reinforced_tests` | Familles et groupes physiques supportes explicitement |

Les gates, exigences et preuves faisant foi pour 0.2.5a0 sont dans le
[pack de qualification](../verification/0_2_5/README.md). Le registre
machine-readable reste la source d'autorite pour les scopes individuels.

## Vocabulaire

- `QUALIFIED / BOUNDED` : exigences obligatoires fermees dans un domaine borne.
- `EXPERIMENTAL / NOT QUALIFIED` : code ou essais disponibles, preuve de
  release insuffisante pour une revendication qualifiee.
- `RESEARCH` : voie exploratoire sans domaine d'emploi qualifie.
- `NOT IN RELEASE SCOPE` : explicitement exclu de la release.

Une comparaison avec un solveur externe est une correlation numerique. Elle ne
constitue pas, a elle seule, une validation physique.
