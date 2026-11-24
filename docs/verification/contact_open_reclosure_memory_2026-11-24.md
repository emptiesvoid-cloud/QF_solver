# Ouverture et refermeture d'un contact frottant — 2026-11-24

## Portée et provenance

Cette note consigne une étude de développement sur un système ressort-contact sans élément FEM. Elle ne change aucun résultat historique et ne qualifie pas la route générale de contact.

- Base produit vérifiée : `origin/0.3.0` à `abc3403f2afdf3bbeb0e0bb1cf7d734268ff419e`.
- Branche isolée : `emptiesvoids-cloud/contact-opening-closure-20261124`, créée à cette base.
- Reproduction du comportement précédent : worktree propre au même SHA `abc3403f2afdf3bbeb0e0bb1cf7d734268ff419e`.
- Rampe M4 stick/slip archivée : source d'exécution `0ef2c9f6675af6f97465499b13ff5d5d03566774`, tête d'exécution `1a98cd5afe43e63191f0c013e7b09bdca8eb107d`, arbre `src` `38c8401ac42a9a61d455a6e9b9d6350ca17dbd35`.
- L'arbre `src` du produit de base est différent (`6e917a7c6f6c983d7a2b84fee5639ecf8e2637c1`). Le delta depuis la source M4 concerne le traitement de la faible compression dans les replis et le refus d'une tolérance booléenne. Ce lot ne modifie ni ce traitement ni les seuils de contact.

Les empreintes des neuf fichiers de sortie, des contrats, des préflights et des ledgers M4 ont été recalculées et concordent avec le résumé archivé. Les empreintes NPZ sont `ae0359fe71a3cbde7384e6896cacd50034fdbddddf38ba89451c97cb324c2973` (stick) et `7213ef4d071ed96d360afcb6693f37a8736555280228a684f3aa521a1aac1887` (slip). Les archives brutes ne sont pas ajoutées au dépôt.

La politique `AGENTS.md` ne contient aucun scope FEM M4 enregistré. Ce n'était pas nécessaire pour départager la mémoire de la loi : les expériences ci-dessous n'ont ni éléments ni assemblage FEM. Aucun calcul de rampe n'a été relancé.

## Modèle synthétique et convention

Le modèle reprend le fixture `test_frictional_contact.py` : trois sommets fixes définissent le plan maître, un nœud esclave est placé à `z = 0,1 m`, sans élément fini, avec `UX` et `UZ` libres et `UY` bloqué. Deux ressorts ont une raideur de `1000 N/m`; la raideur tangentielle du contact vaut `10000 N/m`; `μ = 0,5`. La fermeture sans contact aurait lieu à `100 N` de compression.

- `gap > 0` signifie séparation; `p > 0` signifie compression; le contact ouvert porte `p = 0`.
- La charge tangentielle positive est appliquée selon `+UX`. Avec les signes de sortie du solveur, les équilibres sont `1000 UX + t_x = F_x` et `1000 UZ - p = F_z`.
- Dans les branches adhérente et glissante, l'essai élastique est `t_trial = k_t (u_t - s_ref)` et la force est bornée par `||t|| ≤ μ max(p, 0)`.
- L'historique de charge applique successivement `[F_x,F_z]` avec les facteurs `[0,1]`, `[1,1]`, `[1,-1]`, `[0,-1]`, `[0,1]`, `[0,025,1]` sur les charges maximales `[200,-200] N`. Une seconde variante ajoute une étape ouverte `[0,5,-1]` avant `[0,-1]`.

Dans ce code à paire géométrique initiale fixe, `slip_reference` est l'origine de l'essai élastique, pas une mesure autonome de glissement cumulé ni une mémoire remappée sur une interface mobile. Tant que la paire est ouverte, aucun ressort tangentiel ne transmet de force. Avec cette représentation, le choix testé est de faire suivre `s_ref` au déplacement relatif courant pendant chaque état ouvert accepté; la refermeture ne doit donc pas convertir le déplacement libre de l'intervalle ouvert en traction élastique. Une loi qui veut conserver l'histoire matérielle de l'interface doit porter une variable d'histoire distincte et définir explicitement son transport/remappage.

Les formulations de contact publiées distinguent elles aussi l'état de contact, le remappage de points et l'état de glissement; elles donnent un contexte utile, mais ne prescrivent pas à elles seules une règle universelle de réinitialisation lors d'une séparation : [théorie du contact tangentiel avec frottement, COMSOL 6.4](https://doc.comsol.com/6.4/doc/com.comsol.help.sme/sme_ug_theory.06.088.html), [variables dépendantes du contact, COMSOL 6.3](https://doc.comsol.com/6.3/doc/com.comsol.help.sme/sme_ug_modeling.05.154.html).

## Reproduction avant/après

Le rejeu sans correction, sur le SHA exact de base, a donné :

| Étape | État | `gap` (m) | `p` (N) | `UX` (m) | `t_x` (N) | `s_ref,x` (m) |
|---|---|---:|---:|---:|---:|---:|
| Fermeture sans charge tangentielle | stick | ≈ 0 | 100 | 0 | 0 | 0 |
| Chargement tangentiel `200 N` | slip | ≈ 0 | 100 | 0,15 | +50 | 0,145 |
| Ouverture, déplacement tangent libre | open | 0,3 | 0 | 0,2 | 0 | 0,145 |
| Ouverture, retour tangent libre | open | 0,3 | 0 | 0 | 0 | 0,145 |
| Refermeture, `F_x = 0` | slip | ≈ 0 | 100 | 0,05 | −50 | 0,055 |
| Recharge `F_x = 5 N` | stick | ≈ 0 | 100 | 0,0504545 | −45,4545 | 0,055 |

L'équilibre est satisfait et la force de `50 N` respecte la capacité `μp = 50 N`; ce n'est donc pas un défaut d'équilibre ni une violation de Coulomb. Le résultat met en évidence une traction de contact au retour alors que la charge tangentielle externe est nulle. Elle vient de l'origine élastique conservée à travers le mouvement libre, que la paire fixe ne peut pas interpréter comme un déplacement de glissement sur une interface suivie.

Après rebasage durant l'ouverture, les pas ouverts ont toujours `p = 0`, `t = 0`, un gap positif et `s_ref = u_t`. La refermeture à `F_x = 0` revient à `UX = 0`, `t_x = 0`; la recharge à `5 N` donne `UX = 5/11000 = 0,000454545 m`, `t_x = 50/11 = 4,54545 N`, en adhérence. Les équilibres normaux et tangentiels et la complémentarité ont été vérifiés à chaque pas.

Le test couvre six variantes : deux historiques de mouvement ouvert et trois échelles de force/raideur co-multipliées (`10⁻³`, `1`, `10³`). Les états de fermeture et de recharge sont identiques dans la limite numérique à ces échelles. Cela teste une mise à l'échelle cohérente des coefficients SI, pas une conversion générale des unités ni une loi de contact sur maillage.

## Application aux chemins du solveur et limites

Le rebasage est appliqué à la mise à jour directe, au résultat du repli racine à état figé et à la projection couplée. Les refus post-racine vérifient également la référence libre attendue pour un contact ouvert ou de capacité nulle. Les tests distinguent `μ = 0` (pas de mutation de référence), `p = 0` (force nulle et capacité nulle), les petites pressions positives et le voisinage de fermeture.

Les chemins peuvent encore utiliser des étiquettes différentes à `p = 0` : la mise à jour directe peut signaler `slip` pour un essai non nul de capacité nulle, alors que les replis signalent `open`. Dans ces cas, la force est nulle et la référence suit le déplacement; ce lot harmonise le comportement de mémoire et ne redéfinit pas l'API des états. Cette différence de libellé reste à clarifier séparément.

Le correctif ne change pas le critère normal ni sa tolérance historique. La possibilité déjà documentée d'une faible réaction de traction numérique conservée dans un ensemble normal actif demeure distincte et non corrigée ici. La mise à jour de référence pendant l'ouverture ne compte pas l'énergie tangentielle élastique éventuellement relâchée à la séparation dans `cumulative_local_dissipation`; cette métrique ne doit donc pas être lue comme un bilan énergétique complet ouverture/fermeture.

Les archives M4 confirment huit incréments réussis pour chaque cas. Le cas stick garde 81 contacts adhérents après le premier pas; le cas slip passe de 81 contacts glissants au pas 7 à 63 glissants et 18 ouverts au pas 8. Aucun contact qui s'était ouvert ne se referme ensuite dans ces rampes. L'archive slip peut donc montrer l'ouverture terminale, mais pas l'effet sur une refermeture ultérieure. Les résultats M4 restent attribués à leur source antérieure et ne sont ni rejoués ni requalifiés par cette étude.

## Tests et décision

Résultat local : 38 cas de test réussis sur les tests exacts des chemins direct, racine/couplé, adhérence, glissement, ouverture, pression nulle, faible compression et redémarrage. Les tests incluent l'équilibre, l'admissibilité Coulomb, `gap × p`, le cas sans frottement et le cas à capacité nulle. Le rejeu de référence sur l'ancien SHA reproduit l'effet avant correction.

La correction est ciblée sur la sémantique actuelle de `slip_reference`. Elle modifie les valeurs exportées dans l'historique d'incréments et les états de reprise pour les contacts ouverts; elle ne change pas les seuils ni les équations en contact fermé. Elle est préparée sur la branche de travail locale, sans push. Ruff, `py_compile`, `git diff --check` et le contrôle des chemins privés/indicateurs de secrets ont réussi sur les fichiers modifiés.

À faire avant toute généralisation : décider si les consommateurs exigent une mesure distincte du glissement cumulé; décider si le rebasage doit être accompagné d'une métrique d'énergie de séparation; clarifier le libellé de capacité nulle. Aucun verdict historique ni statut de qualification n'a été modifié.

## Revue complémentaire : itérations et reprise

Les références sont copiées et restent figées pendant les itérations d'un incrément; seule la solution acceptée est écrite dans la transaction et le checkpoint. Un essai répété à état identique retourne les mêmes forces et références sans modifier son entrée. Un échec injecté après modification de la copie d'essai laisse intact le checkpoint du pas ouvert précédent; la reprise de cet état redonne les résultats de l'exécution continue, avec et sans déplacement tangentiel pendant l'ouverture. Le test de repli racine échoué confirme également que la référence fournie en entrée reste inchangée. La recherche linéaire est examinée par lecture du code : ses candidats sont locaux; aucune campagne FEM ni test de cutback de cette route n'a été exécuté. La route étudiée ne met pas en œuvre de cutback automatique.

La lecture des checkpoints accepte désormais un contact normalement actif, mais tangentiellement ouvert, si sa pression est non positive et sa force tangentielle nulle. Cela couvre l'étiquette produite par les replis à capacité nulle. Le calcul suivant réinitialise les états d'itération; cette étiquette reste visible dans l'archive mais ne fournit pas une mémoire d'itération au redémarrage.

Le format de checkpoint passe à la version 2 car la référence d'un contact ouvert a changé de sens. La version 1 est refusée explicitement : poursuivre avec l'ancien solveur ou rejouer le chemin de charge avec la nouvelle version pour créer un checkpoint version 2. Aucune conversion automatique d'une référence ouverte ancienne n'est proposée. Les fichiers historiques restent inchangés.

La règle utilise les états acceptés aux bornes d'incréments. Si l'ouverture, le déplacement libre et la refermeture surviennent entre deux états acceptés, la position exacte de refermeture n'est pas connue par ce modèle discret. Étudier la convergence en pas de charge ou une localisation d'événement si cette précision est nécessaire. Ce comportement ne démontre pas à lui seul la validité d'un modèle d'interface avec transport géométrique.
