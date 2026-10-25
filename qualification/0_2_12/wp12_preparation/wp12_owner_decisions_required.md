# WP12-0 — Décisions Owner requises

**PREPARATION_ONLY** · **NUMERICAL_EXECUTION_NOT_PERFORMED** · **WP12_STATUS=OPEN**

Rien dans cette liste n'est présumé approuvé. Aucune campagne ou limite n'est autorisée par le commit documentaire WP12-0.

| ID | Décision explicite à consigner | Conséquence si non décidée |
|---|---|---|
| O-01 | Confirmer le périmètre WP12 de préparation : routes DYN/NL, expérimentales héritées, exclusions et niveaux MUST/SHOULD/DEFERRED. | Pas de campagne; les revendications obligatoires restent indéterminées. |
| O-02 | Approuver pour chaque campagne l'identité exacte du code cible (`branch`, commit, tree), l'état clean, les hashes sources/tests/fixtures et l'environnement. | Tout changement du code ou des tests exige revue/hash nouveaux; aucun résultat transférable. |
| O-03 | Approuver le manifeste et SHA-256 exacts, les commandes et nodeids individuels, les attentes de skips, la destination exclusive et la politique de tentatives. | `PREPARED_NOT_AUTHORIZED`; aucun lancement. |
| O-04 | Décider les limites CPU, RAM, nombre de threads, timeout, stockage/temp et environnement logiciel par lot; distinguer limites dures et contrôles observés. | Runner doit refuser; pas de budget extrapolé d'un autre WP. |
| O-05 | Autoriser ou demander l'implémentation/revue d'un runner de qualification WP12 avec les garde-fous décrits ici. | Aucun runner existant n'est réputé directement adapté; seules les lectures statiques restent possibles. |
| O-06 | Décider si la non-régression C02 actuelle inclut M4 et M5 AR/N03 et, si oui, autoriser un overlay temporaire isolé du helper exact récupérable au commit `9e1cf9805b49c90a74006a39cb0ded640265f64f` (blob `c05a72879440081f0f4f725f72c0adaa09f66c99`, SHA-256 `7b14816b6ed6f6bed8aaa8e3bbde568251cf94332aa6c7b12765f389d6ae226e`). Pour l'exclusion, accepter explicitement l'absence de preuve courante et garder N13 comme preuve historique bornée. | Le helper exact est vérifié dans l'historique mais absent du tree candidat; M4/M5 restent bloqués jusqu'à l'approbation et la préparation du runner/overlay. Le statut C02 ne change pas automatiquement. |
| O-07 | Décider si la performance v0.2.12 est un critère d'acceptation ou une caractérisation descriptive et approuver, si nécessaire, les mesures/enveloppes avant le run. | Aucune conclusion pass/fail de performance; rapports historiques ne se généralisent pas. |
| O-08 | Définir les routes API/CLI rotor promises (ou confirmer une frontière API-only) et les éventuels replays complets GYRO-05/06. | Pas de revendication CLI ou de GYRO-06 actuelle sans preuve dédiée; la voie minimale n'est pas élargie arbitrairement. |
| O-09 | Confirmer le traitement des domaines D01, E01, C01 et des FAIL/INCONCLUSIVE/Docker non acquis comme exclusions bornées, sans promouvoir ni réouvrir leur statut par WP12. Pour inclure le contrôle de fixture C01 R19, décider aussi comment traiter l'écart entre digest attendu `b74c57ca…` et hash des octets actuels `a732254d…`. | L'acceptation WP12 ne peut être formulée sans périmètre scientifique non ambigu; le contrôle C01 de fixture reste non exécutable comme preuve intègre. |
| O-10 | Après réception des preuves, décider séparément `CLOSE` ou `OPEN_WITH_ACTIONS` pour WP12; ne pas confondre cette décision avec WP12-0 ou la préparation publication. | WP12 reste `OPEN`; aucun statut scientifique ou de release n'est changé. |

Une autorisation doit identifier le campaign ID et le hash manifeste, pas seulement l'intention générale de « lancer WP12 ». Une nouvelle hypothèse, une relance après FAIL, ou une modification de seuil/source nécessite une décision et un enregistrement propres.
