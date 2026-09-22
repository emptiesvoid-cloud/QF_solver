# WP09 HEX20 R2 — audit de la requalification par traction cohérente

## Verdict

`PASS_CANDIDATE_OWNER_REVIEW`

La campagne R2 HEX20 passe la qualification technique bornée définie dans son
contrat : H1, H2 et H3 passent leurs gates structurels, les trois replays
passent, la recomputation indépendante des observables passe et la gate de
maillage 3D H2→H3 passe. Cela reste une candidature d’extension : les points
WP09 officiels restent inchangés jusqu’à décision Owner.

## Ce qui a été changé

- transfert de charge cohérent sur les faces QUAD8 des HEX20, intégration de
  Gauss 2×2 ;
- hiérarchie 3D complète `1×1×1 → 2×2×2 → 3×3×3` ;
- aucune modification de mécanique de production, seuil, matériau, charge
  totale, tolérance, backend ou fallback ;
- correction post-exécution limitée aux annotations de typage du runner et à
  la protection Git des gros résultats bruts.

La comparaison avec R1 n’est pas une expérience à variable unique : R2 change
à la fois le transfert de charge et la hiérarchie de maillage. Elle montre
toutefois que le dépassement R1 `0,05089862 > 0,05` à H2 disparaît dans R2,
avec `0,03265916` à H2 et `0,03239869` à H3.

## Provenance

| Champ | Valeur |
|---|---|
| Branche | `codex/wp09-hex20-extension` |
| Base gouvernante | `cd5605ee7b77d119bbdb01ab9dbe9fa0c84331cf` |
| SHA réellement exécuté | `eea9b3b4f8e6e4b8bcce4626c7f301911aeb4f7e` |
| Contrat SHA-256 | `9fb5bfe23d2eb7cef4ffdbe76b0d9b70e89d9649ae27b9e98a1e9081ae9d07cb` |
| Policy digest | `93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac` |
| Correctif post-run | `3970612d` — typage uniquement, sans rerun numérique |
| Mécanique de production | inchangée |
| Push / merge | non effectués |

Le diff de `src/` entre la base gouvernante et le runner est vide. Le SHA
d’exécution est conservé séparément du HEAD contenant le correctif de typage.

## Définition gelée

- HEX20 corotationnel J2 borné, petite déformation locale ;
- charge totale `[0,25, 0, 0]` dans la direction `+UX` ;
- traction surfacique cohérente QUAD8, Gauss 2×2 ;
- résultante vérifiée `[0,25, 0, 0]` ; moment à l’origine vérifié
  `[0, 0,125, -0,125]` ;
- quatre incréments fixes, tolérance `1e-9`, borne locale `||U-I||F ≤ 0,05` ;
- aucune charge nodale à partage égal.

## Résultats structurels

| Niveau | Nœuds | Éléments | DDL | Déplacement sélectionné | Réaction | Énergie | Von Mises max | `max ||U-I||F` | `min det F` | Résidu libre | Force | Moment | Statut |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| H1 | 20 | 1 | 60 | 0,01786488 | 0,2500000000 | 0,00225643 | 0,18568491 | 0,03691176 | 0,99941633 | 2,66e-12 | 3,93e-13 | 2,65e-13 | PASS |
| H2 | 81 | 8 | 243 | 0,01935146 | 0,2500000000 | 0,00253858 | 0,26203910 | 0,03265916 | 0,99939859 | 3,93e-10 | 2,34e-11 | 1,66e-11 | PASS |
| H3 | 208 | 27 | 624 | 0,02008189 | 0,2500000000 | 0,00264320 | 0,26370640 | 0,03239869 | 0,99937412 | 1,91e-10 | 3,17e-11 | 2,24e-11 | PASS |

Chaque niveau a accepté 4/4 incréments, avec zéro rejet et zéro fallback.
Le solveur conserve néanmoins son `run_verdict = WARNING`, car le profil de
qualification reste expérimental et la traçabilité générique matériau-nonlinear
n’est pas un domaine certifiant. Ce warning n’est pas un échec d’un gate R2.

## Gate de maillage H2→H3

| Observable | Écart | Seuil | Résultat |
|---|---:|---:|---|
| Déplacement sélectionné | 3,6373 % | 5 % | PASS |
| Réaction | ~0 % | 5 % | PASS |
| Énergie | 3,9579 % | 5 % | PASS |
| Von Mises | 0,6323 % | 10 % | PASS |

## Replay et référence

- H1 replay : PASS ; écarts relatifs nuls.
- H2 replay : PASS ; écarts relatifs nuls.
- H3 replay : PASS ; écarts relatifs nuls.
- Référence : `PASS_INDEPENDENT_OBSERVABLE_RECOMPUTATION` pour H1/H2/H3,
  sans import de routine de production.

La référence recalcule les observables depuis les JSON bruts ; elle ne constitue
pas un second solve FEM/Newton global. Aucune corrélation Code_Aster ou autre
solveur externe n’est revendiquée.

## Validation outillage

`15 passed`, Ruff PASS, mypy PASS, compileall PASS, validation JSON PASS et
`git diff --check` PASS. La suite complète du dépôt n’a pas été exécutée.

Les gros JSON bruts restent dans le dossier local d’évidence et sont ignorés
par Git. Le manifeste machine et ce rapport sont les artefacts versionnables.

## Conclusion

R2 est suffisamment cohérent pour une revue Owner comme **extension HEX20
bornée candidate**. Il ne justifie pas encore une attribution automatique de
points WP09, ni une revendication générale de plasticité finie, ni une
validation HEX20 externe. La validation HEX8 officielle `8/8` reste inchangée.

`WP09_HEX20_CANDIDATE = PASS_CANDIDATE`

`WP09_OFFICIAL_POINTS = 8/8 HEX8 uniquement, extension HEX20 en attente Owner`

`NEXT_STEP = revue Owner ; aucun merge, push ou attribution automatique`
