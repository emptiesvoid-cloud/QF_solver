# WP09 TET10 R2 — audit de l’extension par traction cohérente

## Verdict

`PASS_CANDIDATE_OWNER_REVIEW`

La campagne TET10 R2 passe les gates structurels H1, H2 et H3, les trois
replays et la gate de maillage 3D. La première recomputation indépendante a
été bloquée par un défaut du checker, sans défaut numérique des solves. Le
checker a été corrigé et relancé uniquement sur les JSON bruts immuables : les
trois niveaux passent avec des écarts nuls.

Les points officiels WP09 ne changent pas. Cette extension reste candidate,
bornée et soumise à Owner review.

## Cause du premier FAIL_CLOSED

Le runner sérialise correctement `metrics.status = PASS`, les déplacements sous
forme de lignes `{node, dofs}` et les équilibres dans `metrics.equilibrium`.
Le premier checker cherchait un champ `status` au niveau racine et supposait un
vecteur de déplacements numérique plat. Il a donc classé les trois résultats
`production_not_pass` avant de comparer les observables.

Cette erreur est une erreur d’outillage de preuve, pas une erreur du solveur.
Le résumé FAIL initial est conservé et n’a pas été écrasé. Après correction,
la recomputation a été exécutée sans relancer H1/H2/H3.

## Provenance

| Champ | Valeur |
|---|---|
| Branche | `codex/wp09-tet10-extension` |
| Base gouvernante résolue | `85bb719980705d8c7214ab56ab331c6a52aeae63` |
| SHA réellement exécuté | `338a75eaced8866b87f935ee5d7753a4bf8cc473` |
| Contrat SHA-256 | `4898e832040801ed940d747dd0cf71aaba34e0212a3269b0a021a646c5e3f441` |
| Correctif du checker | `404e35b55155f6bb5d1c116fda362831750609f3` |
| Policy digest | `93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac` |
| Mécanique de production | inchangée |
| Push / merge | non effectués |

Le diff de `src/` par rapport à la base est vide.

## Définition

- TET10 corotationnel J2 borné, petite déformation locale ;
- traction cohérente sur les faces triangulaires quadratiques `x=1` ;
- résultante `[0,25, 0, 0]` ; moment `[0, 0,125, -0,125]` ;
- hiérarchie 3D `1×1×1 → 2×2×2 → 3×3×3` ;
- quatre incréments fixes, tolérance `1e-9`, borne `||U-I||F ≤ 0,05` ;
- aucun partage égal des forces nodales.

## Résultats structurels

| Niveau | Nœuds | Éléments | DDL | Déplacement sélectionné | Réaction | Énergie | Von Mises max | `max ||U-I||F` | `min det F` | Résidu libre | Force | Moment | Statut |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| H1 | 26 | 5 | 78 | 0,02389634 | 0,2500000000 | 0,00241435 | 0,25129988 | 0,03472181 | 0,99935995 | 3,43e-11 | 1,27e-12 | 8,47e-13 | PASS |
| H2 | 117 | 40 | 351 | 0,02040792 | 0,2500000000 | 0,00257528 | 0,27198883 | 0,03362469 | 0,99938158 | 1,29e-10 | 1,14e-11 | 7,87e-12 | PASS |
| H3 | 316 | 135 | 948 | 0,02028209 | 0,2500000000 | 0,00265502 | 0,25942237 | 0,03379062 | 0,99926529 | 1,10e-10 | 2,75e-11 | 1,94e-11 | PASS |

Chaque niveau a accepté 4/4 incréments, sans rejet ni fallback.

## Gate de maillage H2→H3

| Observable | Écart | Seuil | Résultat |
|---|---:|---:|---|
| Déplacement sélectionné | 0,6165 % | 5 % | PASS |
| Réaction | ~0 % | 5 % | PASS |
| Énergie | 3,0033 % | 5 % | PASS |
| Von Mises | 4,6202 % | 10 % | PASS |

## Replay et référence

- H1, H2 et H3 replay : PASS ; écarts relatifs nuls.
- Référence corrigée : `PASS_INDEPENDENT_OBSERVABLE_RECOMPUTATION` sur les
  trois JSON bruts ; erreur absolue maximale `0`.
- Aucun import de production dans la référence.

Cette référence est une recomputation indépendante des observables, pas un
second solve FEM/Newton global. Aucune corrélation Code_Aster ou autre solveur
externe n’est revendiquée.

## Validation

`4 passed`, Ruff PASS, mypy PASS, compileall PASS, JSON PASS et diff-check
PASS. La suite complète du dépôt n’a pas été exécutée.

Les gros JSON sont conservés localement et ignorés par Git. Les rapports,
manifests et hashes restent versionnables.

## Conclusion

Le dossier TET10 est prêt pour Owner review comme extension HEX/TET bornée
candidate. Il ne doit pas encore être attribué officiellement et ne prétend
pas valider la plasticité finie générale, une convergence externe ou un autre
élément.

`WP09_TET10_CANDIDATE = PASS_CANDIDATE`

`WP09_OFFICIAL_POINTS = 8/8 HEX8 uniquement ; HEX20 et TET10 en attente Owner`

`NEXT_STEP = revue Owner globale ; aucun merge, push ou attribution automatique`
