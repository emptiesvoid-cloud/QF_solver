# G08 : comparaison contrôlée des maillages transverses

Les deux scopes one-shot sont consommés. La préparation et les preuves locales sont résumées dans [controlled-run-2026-11-22.json](results/controlled-run-2026-11-22.json). Elles restent des résultats de développement, sans statut de qualification.

| Scope | Source | Maillage | Ledger et verdict |
|---|---|---|---|
| Avant | `9f50ed064fa6a330a0c926d6c1a097b279966f69` | 117 nœuds, 40 TET10, 276 DDL libres; 48 faces internes non appariées, 8 composantes et 12 alias de nœuds milieux | Une tentative consommée; le wrapper a échoué à l’appel de `solve_model` avant la précharge. Aucun résultat spectral. |
| Après | `6dd15ea007439a37327298690232cf81bf4c7f69` | 125 nœuds, 48 TET10, 300 DDL libres; aucune face interne ouverte, une composante et aucun alias | Une tentative; runner `PASS`, précharge convergée, archive `VALID`, résultat spectral `COMPUTED`. |

Le correctif du harnais est ciblé : `case.solve_one` appelle désormais `solve_model(model)` sans transmettre `source_sha`, qui n’est pas accepté par la route de flambement. Un test synthétique verrouille cette signature. La tentative avant ayant échoué est conservée et son ledger ne peut pas être réutilisé; aucun A/B mécanique n’est donc calculable dans cette mission.

Pour le maillage après, le facteur calculé est `869.9805921314434`, la charge signée `-869.9805921314434`, le résidu relatif de paire propre `5.078786081630351e-11` et l’écart au repère Euler `8.3156 %`. La formulation réellement utilisée est `generalized_eigs_shift_invert`, avec le backend `scipy.sparse.linalg.eigs` et le crochet `[869.9375, 870.0]`. Le criblage numérique est `SCREEN_PASS`; cela ne valide pas la charge critique physique.

Le premier mode reste `FIRST_MODE_NOT_ESTABLISHED`. Aucun élément de preuve séparé sur la positivité de `K0` et les comptages d’inertie avec bornes d’erreur n’a été produit. Une comparaison future inclura ensemble le changement de connectivité et celui de discrétisation, car le nombre de DDL libres diffère de 276 à 300.

Le contrat fixe le même solide nominal 4 × 0,5 × 0,5, le même matériau, les mêmes appuis et une résultante compressive `UX=-1`. Les deux sources partagent l’arbre `src` `7d6d5da910dc5387eb554c00dcbb3f5ae5f0ddf5`; la branche produit de base `7a375db1630354e3f32d5b457870faa89b22c8cc` contient le même arbre solveur et le même blob du générateur corrigé que la source après.

Les reçus officiels, les ledgers one-shot, les journaux supervisés, le XML pytest et les archives numériques restent dans le store local privé. Le résumé versionné conserve leurs SHA-256 et les métriques revues; les archives brutes ne sont pas incluses dans cette branche produit.

La politique est marquée `DEVELOPMENT_ATTEMPTS_CONSUMED`. Tout nouvel essai avant nécessite une nouvelle portée et une autorisation distincte. Les résultats présents ne qualifient ni le rang du mode, ni le flambement, ni une release.
