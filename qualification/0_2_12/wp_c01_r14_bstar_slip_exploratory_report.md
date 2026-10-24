# WP-C01-R14 — complément d'analyse du glissement B*

## Portée et provenance

Ce complément versionne la lecture mécanique des archives R14 sans réécrire leurs événements, sorties ou verdict initial. L'analyse porte uniquement sur `B_SLIP_R14`, une paire nœud esclave/triangle maître gelée, en petites rotations et avec `finite_sliding=false`.

- Manifeste consommé : SHA-256 `ed0f0970c139196d18305981079dcd65eafe0f3c264afe7addcf24078e9bf868`.
- Résultat solveur archivé : SHA-256 `ecaaf3480f0c29d209a1c68c063447bd335a7494901b7d1e23d3313e76cc56f9`.
- Configuration : SHA-256 `b74c57cae86d94b4cbfdae0c298ea98aa660f70159c72eb4b72f0ee4b5eee3e5`.
- Postprocesseur initial : SHA-256 `3f452c6ba4246d33261df09a0f29dc5fa0a8ef39b14fd146181ac5ba45715a29`; son verdict historique `B_STAR_SLIP_FAILED` est préservé. Ce complément ne le remplace pas.
- Réanalyse complémentaire versionnée : [wp_c01_r14_postprocess_supplemental.json](wp_c01_r14_postprocess_supplemental.json), SHA-256 `4549585f921bc665913db403a9e1cf2547e4c53f4b66e7989129ad3049092f6c`.

## Résultat archivé

Neuf paliers ont été acceptés. Les paliers 1–7 sont `stick`; les paliers 8–9 sont `slip`. Aux pas 8 et 9, la route active-set directe n'a pas convergé après 25 itérations; le fallback `active_slip_root` a ensuite fourni les états acceptés dans la même tentative, sans retry externe. La marge reportée ci-dessous est la marge d'essai élastique Coulomb, avant retour radial, reconstruite par le postprocesseur complémentaire :

\[
\mathbf F_t^{trial}=k_t(\mathbf B^*\mathbf u-\boldsymbol\xi_{prev}),\qquad
m=\lVert\mathbf F_t^{trial}\rVert-\mu p_{accepted}.
\]

`B*` est reconstruit depuis la géométrie initiale archivée, les barycentriques, gradients de forme du triangle et la normale. `u` vient du checkpoint accepté, `ξ_prev` du dernier état accepté, `k_t` de la configuration et `p_accepted` du multiplicateur normal accepté. La capacité varie donc avec la pression; elle n'est pas tenue constante. Les événements `CONTACT_STATE` des branches slip n'émettent pas la force d'essai ni cette marge : elles sont marquées comme **reconstruites**, et non présentées comme télémétrie directement enregistrée.

| Palier | État accepté | Marge Coulomb d'essai reconstruite (N) | Source |
|---:|---|---:|---|
| 7 | stick | −3.848349 | `B*`, déplacement accepté, référence slip précédente, `k_t`, pression acceptée |
| 8 | slip | +15494.836561 | même reconstruction; force d'essai pré-retour |
| 9 | slip | +15600.001459 | même reconstruction; force d'essai pré-retour |

Le moment global brut final vaut `2.57244e−12 N·m`, sous le seuil contractuel inchangé de `0.002 N·m`. Les résultantes indépendantes finales sont `4.9165e−12 N` et `1.8780e−12 N·m`. Ces valeurs documentent ce cas exploratoire et ne constituent pas une qualification générale.

## Correction postprocesseur

Le premier analyseur lisait certains champs d'équilibre au niveau JSON incorrect au lieu de `result.audit.equilibrium`; il exigeait également une marge trial dans les événements slip, où elle n'est pas émise. Le script complémentaire R14 lit le bilan au niveau `equilibrium`, reconstruit la marge uniquement quand les données sources sont disponibles, et écrit vers un nouveau chemin explicitement choisi. Il refuse les sorties historiques protégées et refuse d'écraser un fichier existant. Aucun `null` n'est assimilé à zéro.

L'ancien verdict `B_STAR_SLIP_FAILED` reste celui du postprocesseur lié à la campagne. La reconstruction complémentaire soutient l'observation `B_STAR_STICK_SLIP_VALIDATED_EXPLORATORY` selon le protocole R14; elle ne modifie pas rétroactivement le résultat archivé.

## Limites

- Le résultat couvre un seul chargement exploratoire et une paire maître-esclave gelée.
- La formulation est limitée aux petites rotations; une déformation maximale rapportée de l'esclave de `7.357 %` est présente dans l'archive et doit être gardée à l'esprit dans l'interprétation cinématique.
- Le runtime refuse les routes et projections hors contrat, mais n'impose pas de seuil numérique d'angle; les rotations reconstruites sont un diagnostic, pas une barrière automatique d'admissibilité.
- La tangente globale cohérente en slip n'est pas établie.
- Le glissement fini, la convergence spatiale et une supériorité de `dimensional_v1` ne sont pas démontrés.
