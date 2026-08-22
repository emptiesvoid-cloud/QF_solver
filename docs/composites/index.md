---
doc_id: DOC-COMP-000
revision: 0.4
status: engineering_internal_validated_with_recommendations
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Composites et stratifies

Le composite fait partie du perimetre fonctionnel **V1** de QF_solver. Le
developpement couvre la loi de lamelle, la theorie classique des stratifies,
les MITC4 et MITC3+ multicouches statiques et des indicateurs de rupture de premier pli.
Le MITC4 multicouche statique est accepte pour un usage engineering interne
borne avec recommandations. Les criteres de rupture, extensions dynamiques,
dommage et delaminage restent `experimental` ou hors scope; cette inclusion
V1 ne constitue pas une certification.

> **Limite de dimensionnement composite.** La campagne NAFEMS R0031/1 accepte
> le deplacement `UZ(E)` comme observable global et `S11` comme indicateur de
> champ. La recuperation interlaminaire `S13`, le delaminage, la rupture
> progressive et la calibration sur essais sont hors du domaine V1 : ils ne
> doivent pas etre utilises pour une decision de dimensionnement.

| Capacite | Etat | Utilisation autorisee |
| --- | --- | --- |
| Axes materiau `1-2-3` | implemente et teste | calcul constitutif isole |
| Matrice reduite `Q` | implemente et teste | contraintes planes |
| Matrice transformee `Qbar` | implemente et teste | orientation d'une lamelle |
| Matrices de stratifie `A/B/D` | implemente et teste | calcul CLT constitutif isole |
| MITC4 multicouche | borne avec recommandations | statique lineaire bornee |
| MITC3+ multicouche, statique/modal/Newmark/harmonique | `verified_development` | preuve interne plane symetrique seulement |
| Contrainte/deformation maximale | implemente, `experimental` | indicateur sans degradation |
| Tsai-Hill et Tsai-Wu | implemente, `experimental` | indicateur sans degradation |
| V&V analytique | campagne `001` PASS | verification technique |
| Convergence structurelle | campagne `002` PASS | verification technique |
| Correlation CalculiX S8R | campagne `003` PASS | correlation croisee, elements differents |
| NAFEMS R0031/1 + Code_Aster DST | campagne `004` PASS | correlation externe meme maillage |
| Solides orthotropes TET4/TET10 | noyau `001`, externe `002`, convergence `003`, performance `004` PASS | usage engineering interne borne |

La [theorie classique des stratifies](theorie_stratifies.md) definit les plis,
interfaces, matrices `A/B/D`, resultantes et contraintes par pli. Le
[MITC4 multicouche](mitc4_multicouche.md) integre `A/B/D`, le cisaillement
transverse et les contraintes par pli. Les campagnes analytique, structurelle,
CalculiX et NAFEMS/Code_Aster sont passees. La revue existante accepte la
statique lineaire bornee avec recommandations; des cas plus complexes restent
obligatoires avant toute extension de domaine.
Le [MITC3+ multicouche en statique et dynamique](mitc3_multicouche_dynamique.md)
dispose d'un patch membranaire analytique et d'invariants dynamiques internes;
une correlation externe par pli et une Owner review restent necessaires.
Les [criteres de premier pli](criteres_rupture.md) et leur
[verification analytique](verification_composites.md) sont documentes
separement.

Les materiaux orthotropes 3D sont implementes pour TET4 et TET10. La
[specification et les preuves solides](solides_orthotropes.md) documentent les
patchs affines et les comparaisons sur geometries complexes avec Code_Aster et
CalculiX. Ce perimetre est maintenant
`engineering_internal_validated_with_recommendations` : la
[revue des solides orthotropes](../verification/revue_solides_orthotropes.md)
est signee pour l'usage interne borne. Il ne doit pas etre confondu avec le
MITC4 multicouche ni presente comme certifie.

## Convention d'epaisseur des coques

La normale locale $\mathbf e_3$ fixe l'orientation de l'epaisseur. Les trois
selecteurs publics de post-traitement sont :

| Selecteur | Position | Interpretation |
| --- | ---: | --- |
| `shell_down` | $z=-t/2$ | peau exterieure opposee a $+\mathbf e_3$ |
| `shell_middle` | $z=0$ | plan moyen geometrique |
| `shell_up` | $z=+t/2$ | peau exterieure suivant $+\mathbf e_3$ |

Dans un stratifie, une contrainte peut etre discontinue a une interface. Si le
plan moyen coincide avec une interface, `shell_middle` retourne donc les deux
limites materielles, sans moyenne artificielle. Les resultats JSON publient
egalement `axis: local_e3`, `z`, le numero de pli et les contraintes dans les
axes elementaires et materiau.

## Contrat documentaire et demonstration

| Rubrique exigee | Contenu et preuve |
| --- | --- |
| Geometrie et DDL | Coques MITC4/MITC3+, normale locale et empilement ordonne suivant $\mathbf e_3$. |
| Formulation mathematique | Lamelle orthotrope, transformations, matrices $A/B/D/A_s$ et couplage membrane-flexion. |
| Integration et algorithme | Integration par pli, tying MITC et assemblage des rigidites generalisees. |
| Exemple executable | `python .\qf_solver.py solve --input .\examples\mitc4_laminate_static.json --output .\results\composite.json` |
| Maillage | Panneaux plans, coques cylindriques facettisees et assemblages plies. |
| Chargement et conditions limites | Flexion, membrane, appuis simples, encastrement et chargements NAFEMS. |
| Tableau de resultats | Matrices $A/B/D$, resultantes et contraintes `shell_down/middle/up` par pli. |
| Figure de deformee | Deformees QF_solver et correlations CalculiX/Code_Aster dans les pages de verification. |
| Invariants | Symetrie, rotation des axes, energie, resultantes et empilements symetriques. |
| Convergence | Raffinement des panneaux plans, courbes et coniques. |
| Limites et references | Pas de dommage/delaminage; Jones, Azzi-Tsai, Tsai-Wu, NAFEMS et oracles externes. |

Owner review requise pour toute extension de maturite au-dela du perimetre
statique borne deja accepte.
