---
doc_id: DOC-027-F3-PUBLIC-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# F3 - Audit des claims publics 0.2.7a0

> **CONTROLLED VIEW** - La source machine-readable est
> [`f3_public_claim_audit.json`](../../../qualification/0_2_7/f3_public_claim_audit.json).
> Cette page ne remplace ni les preuves d'execution ni le registry v2.

## Decision rule

F3 applique la hierarchie suivante : resultats executes, enregistrements de
qualification et registry, preuves V&V gelees, tests, documentation de
qualification, documentation utilisateur, puis metadata de package. En cas de
conflit, la preuve la plus proche de l'execution gagne et la documentation est
corrigee. Les snapshots historiques restent immuables.

Les mots sont distincts : `IMPLEMENTED`, `TESTED`, `VERIFIED`,
`EXTERNALLY_VALIDATED`, `QUALIFIED` et `EXPERIMENTAL`. Une API ou un exemple
teste ne vaut pas qualification generale.

## Current claim boundaries

- Le candidat `0.2.7a0` n'est ni tague ni publie sur PyPI.
- Le registry v2 au niveau combinaison est la source de verite des maturites.
- Linear static et J2 small-strain sont qualifies uniquement dans leurs
  domaines bornes documentes.
- WEDGE6 static reste `EXPERIMENTAL`; WEDGE6 modal est
  `QUALIFIED_BOUNDED` seulement pour les trois premiers modes du scope WP10.
- Les resultats 1.029M, 3M Silver/Gold Compute et 5M Silver sont des resultats
  bornes par workload, machine, image, MPI et options enregistres.
- Code_Aster/PENTA6 fournit une correlation externe bornee. CalculiX/C3D6
  reste `NOT_COMPARABLE` pour le contrat d'integration WEDGE6 considere.
- Aucun claim GPU, HPC general, scaling universel, restart Gold ou validation
  physique generale n'est publie.
- Les mixed meshes, WEDGE15, PYRAMID5 et les variantes HEX8 next-gen restent
  differes ou en recherche selon la decision LU2-WP08.

## Corrections F3

F3 a corrige les vues actives qui exposaient encore les comptages LU2
historiques, les anciens statuts WP04/WP05, des pointeurs 0.2.6 non qualifies,
une phrase de harness devenue obsolete, l'ambiguite des mesures P4 et les
bornes de performance insuffisamment explicites. Les anciennes valeurs et
preuves ne sont pas supprimees : elles sont marquees historiques.

Le champ composite historique de `progress.json` reste volontairement intact;
les lecteurs actifs utilisent `level_up_2_state.json` et
`level_up_2_index.json`. Cette clarification de forme de donnees est reportee,
sans impact sur le claim public courant.

## Audit results

`OVERCLAIMS_FOUND = 0` : aucune phrase active plus forte que la preuve n'a ete
retenue apres confrontation. Les huit findings documentaires P2 relevant de
la surface active ont ete corriges; un neuvieme finding P2 couvre 27 liens historiques vers des artefacts
generes/non suivis et reste differe avec un finding P3 de forme historique. Les limitations
WEDGE6, CalculiX, mixed mesh, nouvelles familles, non-lineaire, dynamique et
performance restent visibles.

Le scope actif 0.2.7 compte 366 liens locaux controles et aucune cassure. Les
27 liens historiques differes ne sont pas des sources des claims actifs et ne
sont pas convertis en preuves disponibles.

`Maturity promoted = NO`  
`Historical evidence modified = NO`  
`Numerical source changed = NO`

## Navigation

- [`Capability matrix 0.2.7`](0_2_7_capability_matrix.md)
- [`V&V harness v2`](0_2_7_vnv_harness_v2.md)
- [`3M ladder`](0_2_7_wp18_3m_ladder.md)
- [`5M closeout`](0_2_7_lu2_wp04_wp05_5m_closeout.md)
- [`LU2 state`](../../../qualification/0_2_7/level_up_2_state.json)
