# V&V contact avec frottement : bloc analytique

- Etude : `VNV-CONTACT-FRICTION-BLOCK-001`
- Verdict interne : `PASS_INTERNAL`
- Maturite : `experimental`
- Reference : bloc glissant a ressorts, solution analytique de la loi regularisee implementee.

## Criteres automatiques

| Critere | Valeur | Limite | Statut |
| --- | ---: | ---: | --- |
| analytical displacement | 0.000e+00 | 1.000e-10 | PASS |
| analytical tangential force | 0.000e+00 | 1.000e-10 | PASS |
| normal pressure | 0.000e+00 | 1.000e-10 | PASS |
| Coulomb cone excess | 0.000e+00 | 1.000e-10 | PASS |
| non-negative local friction work | 0.000e+00 | -1.000e-12 | PASS |
| stick/slip state mismatch count | 0.000e+00 | 0.000e+00 | PASS |
| reversed sliding symmetry | 0.000e+00 | 1.000e-10 | PASS |
| sliding regularization sensitivity | 0.000e+00 | 1.000e-10 | PASS |

## Lecture

La campagne couvre l'adherence, le glissement sature a la borne de Coulomb, le changement de signe et l'effet de la regularisation. Chaque point est toutefois une statique independante. La memoire incremental charge-decharge est verifiee par un test unitaire distinct; la convergence structurelle en glissement fort reste ouverte.

![Comparaison bloc rugueux](friction_block_comparison.png)
