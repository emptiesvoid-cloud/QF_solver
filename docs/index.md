---
doc_id: DOC-STATE-001
revision: 0.1
status: draft technique
applicable_version: 0.2.5a0
reviewer: ""
approver: ""
---

# QF_solver

## Tableau de bord mecanique et numerique

Ce site decrit le comportement mecanique reel du solveur, ses formulations,
ses methodes numeriques et les preuves actuellement disponibles. Il ne declare
ni certification externe, ni aptitude generale a dimensionner une structure
aeronautique sans revue independante.

!!! warning "Position d'utilisation"
    Un verdict numerique `PASS` signifie que les criteres programmes du cas ont
    ete satisfaits. Il ne remplace ni la verification du modele par
    l'ingenieur, ni une decision de qualification du logiciel.

--8<-- "docs/generated/status.md"

Le candidat local `0.2.5a0` prolonge la baseline publiée `0.2.4a0` par un
chantier de mécanique non linéaire structurelle unifiée. Le [pack de
qualification](verification/0_2_5/README.md) sépare les preuves internes, les
corrélations externes, les limites et les gates ; aucune publication n'est
impliquée par sa présence dans le worktree.

## Lire ce site comme un ingenieur calcul

1. Verifier le [perimetre et la maturite](etat/capacites.md) de l'analyse.
2. Controler les [hypotheses de formulation](fondements/travaux_virtuels.md).
3. Examiner la page de l'[element fini](elements/index.md) utilise.
4. Verifier les criteres du [solveur numerique](solveurs/index.md).
5. Comparer le calcul aux [demonstrations executables](demonstrations/index.md).
6. Relire le [dossier de preuve](verification/tracabilite.md) et les limites.

## Regle de confiance

Une capacite est presentee avec quatre informations inseparables:

| Information | Question posee |
| --- | --- |
| Formulation | Quelle equation discrete est effectivement resolue ? |
| Domaine de validite | Quelles hypotheses rendent cette equation acceptable ? |
| Verification | Quelle reference independante ou quel invariant est satisfait ? |
| Maturite | Cette capacite est-elle stable, renforcee, experimentale ou de recherche ? |

Les chiffres de cette page sont regeneres par `scripts/build_docs.py`. Un
chiffre sans empreinte de modele ni revision source ne constitue pas une
preuve controlable.
