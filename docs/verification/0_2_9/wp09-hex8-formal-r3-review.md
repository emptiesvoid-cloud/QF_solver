# WP09 HEX8 R3 — revue de requalification prospective

## Statut

`PASS_CANDIDATE` — aucune attribution officielle de points. `WP09 = 0/8` jusqu'à la décision Owner.

La campagne R3 a été exécutée après le gel du contrat R3. Les artefacts primaires H7/H8/H9 embarquent le SHA-256 du contrat, le digest de politique code et le digest de politique runtime.

## Provenance

- Branche : `codex/wp09-hex8-formal-r3`
- Contrat gelé avant calcul : commit `70a409ae7428c5c25fd8808dd497b3b972504f35`
- Runner primaire : commit `bb86e8a0a2b6b30945a610a8fb7770bae88beea5`
- Runner référence/replay compact : commit `a010a27eb9372309385b503a9e47967870e12b7e`
- Contrat SHA-256 : `c2439513909cc7c640c96878ad6673b8b0377fea15cb16d269df43adae128b0d`
- Policy code digest : `93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac`
- Runtime policy digest : `895d3c932278c0207b207318216c263a427636d57738bef730917fdc7d9b0ef5`
- Push/merge : non effectués

La correction du replay est strictement outillage : l'audit exhaustif n'est plus sérialisé dans les replay compacts ; les observables, checks et provenance sont conservés. Les audits complets restent présents dans les résultats primaires.

## Résultats primaires

| Niveau | Statut | DDL | Déplacement | Énergie | Von Mises | Résidu libre |
|---|---:|---:|---:|---:|---:|---:|
| H7 | PASS | 1536 | 0.02032819041322444 | 0.0019750043565815614 | 0.2952288249837135 | 5.540812125998602e-10 |
| H8 | PASS | 2187 | 0.021230343966417212 | 0.002093817249147815 | 0.3105744828392777 | 5.156625968710628e-10 |
| H9 | PASS | 3000 | 0.021897995446470694 | 0.0021872382555426255 | 0.32243677472830096 | 5.397144734866607e-10 |

Tous les niveaux ont 4 incréments acceptés, zéro rejet et zéro fallback. Les enveloppes de déformation et les équilibres force/moment passent.

## Référence indépendante et replay

- Référence indépendante HEX8 : `PASS_INDEPENDENT_REFERENCE`.
- Erreur relative maximale contrainte locale : `3.0352920503514236e-13`.
- La référence est une recomputation NumPy matériau/élément affine ; elle ne constitue pas un solveur global FEM/Newton indépendant.
- Replay déterministe : H7 `PASS`, H8 `PASS`, H9 `PASS`.
- Les deltas replay maximum sont nuls pour les observables comparées.
- Code_Aster : non exécuté et non requis pour ce gate interne ; aucune corrélation externe n'est revendiquée.

## Gate de maillage H8→H9

- Déplacement : `3.0489159689778222 %` — PASS sous 5 %.
- Réaction : `4.198019710006424e-11` — PASS.
- Énergie : `4.271185645097164 %` — PASS sous 5 %.
- Von Mises : `3.678951291774626 %` — PASS sous 10 %.

## Périmètre et limites

Cette preuve reste limitée à HEX8, formulation corotationnelle J2 bornée, petites déformations locales (`||U-I|| <= 0.05`), chargement et hiérarchie H7/H8/H9 gelés. Elle ne qualifie pas TET4, les grandes déformations générales, un solveur global indépendant, Code_Aster, MPI/PETSc, la dynamique ou une corrélation externe.

L'ancien R2 rétrospectif et l'essai de replay interrompu pour export d'audit sont conservés séparément et ne sont pas utilisés comme preuve R3.

## Conclusion

```text
WP09_R3_STATUS = PASS_CANDIDATE
WP09_OFFICIAL_POINTS = 0/8
OWNER_REVIEW_REQUIRED = YES
MERGE = NOT_PERFORMED
PUSH = NOT_PERFORMED
```
