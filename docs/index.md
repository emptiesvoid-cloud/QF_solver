---
doc_id: DOC-STATE-001
revision: 0.2
status: draft
applicable_version: 0.2.5a0
reviewer: ""
approver: ""
---

# QF Solver

## Tableau de bord mecanique et numerique

Ce site decrit les formulations, methodes numeriques, capacites et preuves de
QF Solver. Il ne declare ni certification externe ni aptitude generale a
dimensionner une structure sans revue independante.

!!! warning "Position d'utilisation"
    Un verdict numerique `PASS` signifie que les criteres du cas ont ete
    satisfaits. Il ne remplace ni la verification du modele par l'ingenieur,
    ni la decision de qualification du logiciel.

--8<-- "docs/generated/status.md"

La version candidate `0.2.5a0` est documentee par un scope Owner explicitement
borne. Les pages [capacites](etat/capacites.md) et
[limites](etat/limites.md) distinguent les claims qualifies, experimentaux,
de recherche et hors scope.

## Parcours recommande

1. Lire le [perimetre et la maturite](etat/capacites.md).
2. Verifier les [hypotheses de formulation](fondements/travaux_virtuels.md).
3. Examiner la page de l'[element fini](elements/index.md).
4. Controler le [solveur numerique](solveurs/index.md).
5. Reproduire une [demonstration](demonstrations/index.md).
6. Relire la [tracabilite V&V](verification/tracabilite.md) et les limites.

## Regle de confiance

| Information | Question |
| --- | --- |
| Formulation | Quelle equation discrete est resolue ? |
| Domaine | Quelles hypotheses bornent son emploi ? |
| Verification | Quel invariant ou quelle reference est satisfait ? |
| Maturite | Le chemin est-il qualifie, experimental, research ou hors scope ? |

Les chiffres generes sont toujours interpretes avec leur modele, leur
configuration, leur revision source et leur empreinte d'artefact.
