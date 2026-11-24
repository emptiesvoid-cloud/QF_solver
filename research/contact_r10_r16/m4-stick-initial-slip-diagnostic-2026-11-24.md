# Diagnostic R10 M4 stick — 24 novembre 2026

## Conclusion

Les six glissements du premier pas sont cohérents avec la loi de retour de Coulomb observée. Le premier chargement applique `250 N` suivant la normale et exactement `0 N` tangentiels, mais les six contacts ont un déplacement tangentiel local non nul et une force d'essai supérieure à `mu*p`. La projection renvoie une force de norme `mu*p` pour chacun.

La capture révèle aussi un défaut logiciel distinct, qui n'explique pas ces six états : le classificateur comparait un écart de force, en newtons, à `FrictionlessContact.gap_tolerance`, en mètres. Le patch local remplace cette bande par la tolérance de frottement sans dimension, mise à l'échelle en force. Les marges mesurées des six contacts sont de `1.15e-3` à `3.29e-2 N`, très au-dessus de la bande corrigée, voisine de `1e-9 N` pour ces états. Les six classifications ne changent donc pas à cause de ce correctif.

## Provenance et contrôle

- La tête distante `origin/0.3.0` a été relue à `57e04bf3e80e2846cb0f8d45a7dde40de917d2cf`. L'arbre `src` est `e8557508de5d3107df47accd3910448866773f8e`.
- Le constructeur du cas est `scripts/run_wp08_area_supported_m4_diagnostic_r1_10.py`, SHA-256 `77ef31587bd0761a78e5aeb4df2c3ce3ce29db58ad317021a3de5cfa7ae1d731`.
- Contrat `m4-stick-diagnostic-contract-2026-11-24.json`, SHA-256 `4ae66b754f7906f8b2dd8e1dbcfc172301ae88a2cffc04fc68972a953c0e33b1` ; nodeid exact `tests/verification/test_m4_stick_diagnostic_capture.py::test_instrumented_m4_stick_ramp`.
- Le premier collect-only, `pf-1cea1f47c60f`, avait collecté le nodeid mais son reçu n'a pas satisfait le validateur local de provenance du contrôleur. Aucune tentative n'a consommé ce reçu. Après correction du validateur M4 dans le contrôleur isolé, le collect-only exact `pf-052ee8254407` a passé ; SHA-256 du reçu `7a65a523236c5bfcdd11e8296164dae8c7aaab35f95ca1b42aa372f150c92f41`.
- Le ledger local `DEVELOPMENT_AUTONOMOUS-FEM-2026-11-24-m4-stick-diagnostic-v1`, série `dev-m4stick-diagnostic-20261124`, comporte une seule entrée, tentative 1 `PASS`. SHA-256 du ledger `4036788a2e2a0f8eba2b6f326beb04770d70f28062c639a00a7538a256269cea`. Aucun nouvel essai n'a été lancé.
- Le runner a importé `solveur` depuis le worktree produit exact au SHA `57e04bf3...`. La capture utilise l'API publique du solveur, sans cache LU du harnais ni modification du code mécanique pour l'essai.

Le verdict v2 reste inchangé : huit pas et contrôles locaux passés, préflight officiel `NOT_RUN`, reconstruction indépendante `NOT_RUN`. La présente capture v3 est une tentative distincte et ne réécrit pas ce statut.

## Mesures des six contacts au premier pas

Les indices sont l'ordre des opérateurs, à base zéro. La pression du solveur est un multiplicateur nodal en `N`, pas une pression en `Pa`. Le déplacement est le relatif tangentiel local par rapport à la référence de glissement. La colonne `marge` vaut `||f_trial|| - mu*p`.

| Opérateur / nœud esclave | `p` (N) | `mu*p` (N) | `||f_trial||` (N) | Force retournée (N) | Marge (N) | `||du_t||` (m) |
|---:|---:|---:|---:|---:|---:|---:|
| 0 / 16 | 0.49353046 | 0.14805914 | 0.16533003 | 0.14805914 | 0.01727089 | 2.3807e-5 |
| 8 / 152 | 0.19607873 | 0.05882362 | 0.08494752 | 0.05882362 | 0.02612391 | 2.4465e-5 |
| 9 / 169 | 0.75443155 | 0.22632946 | 0.22748326 | 0.22632946 | 0.00115380 | 2.1838e-5 |
| 63 / 1087 | 0.77665742 | 0.23299723 | 0.23444829 | 0.23299723 | 0.00145106 | 2.2507e-5 |
| 72 / 1240 | 0.18938258 | 0.05681478 | 0.08969311 | 0.05681478 | 0.03287834 | 2.5831e-5 |
| 80 / 1376 | 0.46432513 | 0.13929754 | 0.16583591 | 0.13929754 | 0.02653838 | 2.3880e-5 |

Les six points sont sur les bords du patch de contact, près des arêtes `y` et des extrémités `z`. Le solide est comprimé suivant `x`, avec `nu=0.3` et une face maître fixe ; une expansion transverse de Poisson et la réponse de bord peuvent produire des déplacements locaux `y/z` même quand la résultante tangentielle imposée est nulle. Les champs capturés soutiennent ce mécanisme, mais aucun contrôle à `nu=0` ou autre expérience ne sépare ses contributions de celles des appuis et de la discrétisation.

Au premier état actif, les 81 normales sont actives ; 6 contacts glissent et 75 adhèrent. Les six glissements persistent jusqu'à la convergence du pas 1. Aux pas 2 à 8, les 81 contacts terminent en adhérence. La charge tangentielle globale ne commence qu'au pas 5.

## Statut de la rampe

| Pas | Résultante appliquée `(normal, tangentiel)` (N) | Ouverts / adhérence / glissement | Itérations | Équilibre libre relatif | Force globale relative | Moment global relatif | Pénétration max (m) | Résidu Coulomb réduit |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | (250, 0) | 0 / 75 / 6 | 20 | 4.21e-11 | 7.48e-12 | 6.53e-12 | 2.73e-16 | 1.39e-17 |
| 2 | (500, 0) | 0 / 81 / 0 | 3 | 3.68e-14 | 6.71e-15 | 3.42e-15 | 3.20e-16 | 0 |
| 3 | (750, 0) | 0 / 81 / 0 | 3 | 2.45e-14 | 4.47e-15 | 2.27e-15 | 3.20e-16 | 0 |
| 4 | (1000, 0) | 0 / 81 / 0 | 3 | 1.84e-14 | 3.34e-15 | 1.70e-15 | 3.20e-16 | 0 |
| 5 | (1000, 37.5) | 0 / 81 / 0 | 3 | 1.69e-14 | 3.50e-15 | 2.02e-15 | 2.43e-16 | 0 |
| 6 | (1000, 75) | 0 / 81 / 0 | 3 | 1.69e-14 | 4.01e-15 | 1.95e-15 | 1.81e-16 | 0 |
| 7 | (1000, 112.5) | 0 / 81 / 0 | 3 | 1.70e-14 | 5.55e-15 | 2.88e-15 | 2.51e-16 | 0 |
| 8 | (1000, 150) | 0 / 81 / 0 | 3 | 1.67e-14 | 6.07e-15 | 3.12e-15 | 2.38e-16 | 0 |

Runner : `PASS`; solveur : huit pas renvoyés et `RAMP_DIAGNOSTIC_PASS`; validateur d'archive : `VALID`, 22 tableaux, 8 pas, 81 contacts, 1381 nœuds et 6144 TET4. Le résultat compact est dans `m4-stick-diagnostic-result-2026-11-24.json`. Son archive source a le SHA-256 `ae0359fe71a3cbde7384e6896cacd50034fdbddddf38ba89451c97cb324c2973` ; les sorties NPZ et JSONL restent dans le magasin de runs local et ne sont pas ajoutées à la branche.

## Contrôle indépendant hors FEM

La reconstruction TET4 a recalculé les forces internes élémentaires à partir des coordonnées, connectivités, déplacements et constantes `E, nu`, avec une implémentation `B/D` indépendante de l'assemblage creux du solveur. La comparaison `charges - forces internes` contre les multiplicateurs normaux a un écart absolu maximal de `4.89e-14 N`. Les déterminants jacobiens des 6144 TET4 sont tous `+9.765625e-4 m^3` ; aucun nul, négatif ou proche de zéro n'a été trouvé. Les bilans indépendants du pas 1 sont `7.477984e-12` (force) et `6.529795e-12` (moment), relatifs.

La distribution globale des forces de contact pour ce bilan réutilise le constructeur de vecteurs de contact produit ; cette partie n'est donc pas indépendante de la géométrie d'assemblage du contact. La vérification des forces internes TET4 et la comparaison des multiplicateurs nodaux sont les contrôles séparés les plus forts. La capture a été validée par SHA-256 et son schéma ; elle n'est pas incluse dans ce lot.

## Défaut de tolérance et correction préparée

Sur le code capturé, `_operator` copie `gap_tolerance` (m) dans `operator.tolerance`; `_friction_update` s'en servait pour les comparaisons `||f_trial||` et `mu*p` (N). La configuration fournit `contact_friction_tolerance=1e-9`, sans dimension, utilisée ailleurs comme tolérance relative sur les forces, mais non transmise à cette classification. Il s'agit d'une incohérence d'unités démontrée dans le code. Les six marges étant de 1.15e-3 à 3.29e-2 N, cette incohérence ne cause pas leur glissement.

Le lot local corrige le calcul de la bande de force en `eps_f * max(mu*max(p,0), 1 N)`, transmis à la classification directe et aux classifications/contrôles tangentiel racine et projection couplée. La bande d'hystérésis du glissement utilise la même échelle. Les seuils du contrat, les critères de gap et les gardes n'ont pas été modifiés. Les deux nouvelles régressions échouaient sur la base `57e04bf3` (argument `friction_tolerance` absent), puis passent après le correctif ; elles vérifient l'indépendance vis-à-vis de `gap_tolerance`, la variation de `contact_friction_tolerance` et l'hystérésis autour de la limite de Coulomb. Une régression additionnelle couvre le classificateur post-racine.

Cette correction n'a pas été exécutée dans la rampe FEM : le ledger autorisait une tentative unique, déjà consommée. Elle reste un correctif local à revoir et n'est pas une preuve que les résultats du M4 stick changeraient. Les comparaisons normales pression/gap-tol dans d'autres gardes sont hors de ce correctif ciblé et méritent une revue séparée.

## Comparaisons et portée

Le run v2 portait sur le même cas nominal et les mêmes critères, mais son archive brute manque ; sa comparaison demeure agrégée. Le M4 slip historique appliquait `450 N` tangentiels au total contre `150 N` pour ce stick et utilisait une source antérieure au garde de récupération de débordement. Ce n'est pas un avant/après strict. La rampe M4 stick confirme seulement ce cas sur la source produit `57e04bf3`; elle ne qualifie pas toute la route de contact.

La capture complète a duré `32.68 s` côté runner, dont `27.89 s` solveur, avec un pic RSS observé de `510590976` octets et `6.22 MB` de sorties locales. Les limites RSS/stockage sont des observations souples du runner, pas des quotas OS.

## Vérifications du lot local

- Tests unitaires ciblés WP08-B/C/D, contacts frottants, contrôles structurels et validateur de capture : `82 passed`.
- Régressions du correctif avant/après ajout : deux `FAIL` attendus sur la base (signature sans tolérance de frottement), puis `2 passed`; le test post-racine ajouté passe aussi dans la sélection finale.
- Ruff `0.15.20`, `py_compile` sur les modules/test modifiés et `git diff --check` : passés.
- Non exécutés : nouvelle rampe après correctif, suite complète, CI GitHub protégée, qualification générale de contact.

## Intégration locale

Le lot est préparé sur `emptiesvoids-cloud/m4-stick-followup-20261124`, créé depuis le SHA distant vérifié `57e04bf3e80e2846cb0f8d45a7dde40de917d2cf`. Il contient les preuves compactes, le contrat, le validateur synthétique et le correctif/test ciblé. Les logs bruts, la capture NPZ, les chemins privés, les reçus complets et le code runner instrumenté volumineux ne sont pas intégrés. Le nodeid FEM reste dans le worktree isolé de diagnostic ; aucune politique publique d'exécution n'a été ajoutée ici.

Aucun push, merge, tag, release ou publication n'a été effectué. Le prochain contrôle utile est une revue du correctif tangentiel sur les autres chemins de classification, puis une nouvelle campagne seulement avec une autorisation/scope distincte et un ledger neuf.
