# WP12-0 — Décisions Owner requises

**PREPARATION_ONLY** · **NUMERICAL_EXECUTION_NOT_PERFORMED** · **WP12_STATUS=OPEN**

Rien dans cette liste n'est présumé approuvé. Aucune campagne ou limite n'est autorisée par le commit documentaire WP12-0.

| ID | Décision explicite à consigner | Conséquence si non décidée |
|---|---|---|
| O-01 | Confirmer le périmètre WP12 de préparation : routes DYN/NL, expérimentales héritées, exclusions et niveaux MUST/SHOULD/DEFERRED. | Pas de campagne; les revendications obligatoires restent indéterminées. |
| O-02 | Approuver pour chaque campagne l'identité exacte du code cible (`branch`, commit, tree), l'état clean, les hashes sources/tests/fixtures et l'environnement. | Tout changement du code ou des tests exige revue/hash nouveaux; aucun résultat transférable. |
| O-03 | Approuver le manifeste et SHA-256 exacts, les commandes et nodeids individuels, les attentes de skips, la destination exclusive et la politique de tentatives. | `PREPARED_NOT_AUTHORIZED`; aucun lancement. |
| O-04 | Décider les limites CPU, RAM, nombre de threads, timeout, stockage/temp et environnement logiciel par lot; distinguer limites dures et contrôles observés. | Runner doit refuser; pas de budget extrapolé d'un autre WP. |
| O-05 | Revoir le runner WP12-R et décider du modèle d'approbation authentifiable (clé Owner protégée hors du checkout, règles de rotation/révocation) et de l'environnement d'isolation OS requis avant toute exécution. | Le runner reste en VALIDATE/SELF_TEST; EXECUTE est désactivé sans vérification cryptographique de confiance et limites OS dures adaptées. |
| O-06 | Décider si la non-régression C02 actuelle inclut M4 et M5 AR/N03 et, si oui, autoriser un overlay temporaire isolé du helper exact récupérable au commit `9e1cf9805b49c90a74006a39cb0ded640265f64f` (blob `c05a72879440081f0f4f725f72c0adaa09f66c99`, SHA-256 `7b14816b6ed6f6bed8aaa8e3bbde568251cf94332aa6c7b12765f389d6ae226e`). Pour l'exclusion, accepter explicitement l'absence de preuve courante et garder N13 comme preuve historique bornée. | Le helper exact est vérifié dans l'historique mais absent du tree candidat; M4/M5 restent bloqués jusqu'à l'approbation et la préparation du runner/overlay. Le statut C02 ne change pas automatiquement. |
| O-07 | Décider si la performance v0.2.12 est un critère d'acceptation ou une caractérisation descriptive et approuver, si nécessaire, les mesures/enveloppes avant le run. | Aucune conclusion pass/fail de performance; rapports historiques ne se généralisent pas. |
| O-08 | Définir les routes API/CLI rotor promises (ou confirmer une frontière API-only) et les éventuels replays complets GYRO-05/06. | Pas de revendication CLI ou de GYRO-06 actuelle sans preuve dédiée; la voie minimale n'est pas élargie arbitrairement. |
| O-09 | Confirmer le traitement des domaines D01, E01, C01 et des FAIL/INCONCLUSIVE/Docker non acquis comme exclusions bornées, sans promouvoir ni réouvrir leur statut par WP12. Pour inclure le contrôle de fixture C01 R19, décider aussi comment traiter l'écart entre digest attendu `b74c57ca…` et hash des octets actuels `a732254d…`. | L'acceptation WP12 ne peut être formulée sans périmètre scientifique non ambigu; le contrôle C01 de fixture reste non exécutable comme preuve intègre. |
| O-10 | Après réception des preuves, décider séparément `CLOSE` ou `OPEN_WITH_ACTIONS` pour WP12; ne pas confondre cette décision avec WP12-0 ou la préparation publication. | WP12 reste `OPEN`; aucun statut scientifique ou de release n'est changé. |
| O-11 | Après revue du runner, autoriser séparément une campagne et son unité exacte : SHA-256 du manifeste figé, commit/tree, nodeid/commande, environnement, budgets appliqués, tentative, destination et décision signée vérifiable. | Tous les manifestes WP12-0 restent `PREPARED_NOT_AUTHORIZED`; aucun lancement scientifique. |

Une autorisation doit identifier le campaign ID et le hash manifeste, pas seulement l'intention générale de « lancer WP12 ». Une nouvelle hypothèse, une relance après FAIL, ou une modification de seuil/source nécessite une décision et un enregistrement propres.

## Décisions et actions ajoutées en WP12-R2

Ces actions ne sont pas présumées faites. L'authentification Ed25519 est implémentée mais sans trust root réel; le mode `EXECUTE` reste désactivé.

| ID | Action/décision Owner | Vérification exigée | Si absente |
|---|---|---|---|
| R2-O1 | Provisionner le trust store public Ed25519 hors checkout, son SHA-256 pin dans HKLM, des ACL NTFS et un compte runner standard dédié. Conserver la clé privée exclusivement sous contrôle Owner. | Vérifier le hash fichier/pin, le principal lié à la clé, la lecture par le compte runner et l'absence de droits d'écriture runner sur fichier et pin. Voir le bloc `OWNER_ACTION_REQUIRED` dans [revue sécurité R2](wp12_r2_runner_security_review.md). | Toutes décisions restent non authentifiées; `EXECUTE` refuse. |
| R2-O2 | Choisir le niveau d'isolation exigé pour CPU, stockage, threads et archives. Le Job Object WP12-R2 ne fournit pas de quota CPU dur, de plafond stockage/threads ni de sandbox fichier. | Documenter le compte, ACL, environnement/VM éventuel et vérifier que l'enfant ne peut pas écrire dans les archives gelées. | Refuser toute unité exigeant des limites dures non présentes. |
| R2-O3 | Revoir les chemins corrigés dans les révisions WP12-1..4 et confirmer le périmètre scientifique après inspection des mappings. | Comparer `path_resolution` de chaque manifeste R2 au tree `df4ec667...`; les chemins anciens restent dans l'index avec leur SHA original. | Aucun manifeste R2 n'est figé ni approuvable. |
| R2-O4 | Geler les bytes des entrées inline WP12-1/2 par une source déterministe et approuver le SHA résultant. Pour WP12-3, décider séparément du contrôle C01 divergent et de l'éventuel overlay C02. | SHA-256 et Git OID vérifiables; aucune modification des fixtures C01 ou preuve C02 historique. | Les unités concernées demeurent bloquées ou exclues explicitement. |
| R2-O5 | Finaliser les scénarios WP12-5, paramètres exacts, répétitions et instrumentation; déterminer si la performance est descriptive ou gate. | Manifeste complet et seuils approuvés avant le run, sans extrapolation à partir d'un workload unique. | WP12-5 reste préparatoire/NOT_RUN. |
| R2-O6 | Définir le candidat distant exact après le commit runner, demander un reçu SYNC frais et approuver le commit/tree scientifique et runner séparément. | Confirmer origin, branche, commit/tree, ascendance et checkout propre; la vérification SYNC n'a pas été faite sur GitHub dans R2. | Toute unité dépendante du distant reste bloquée. |
| R2-O7 | Revoir l'architecture du runner R2 puis autoriser séparément toute nouvelle implémentation qui activerait EXECUTE. | Contrôler l'authentification Owner, l'environnement isolé, l'inventaire, le ledger, la sélection réelle d'un nodeid et la réception d'un résultat avant activation. | EXECUTE reste un refus inconditionnel. |
| R2-O8 | Décider le stockage d'archive/ancrage externe des ledgers et reçus lorsque l'intégrité doit résister à un acteur ayant accès au même compte. | Démontrer une copie indépendante ou un service immuable/signature externe, et vérifier les hashes après archivage. | Les hashes courants détectent l'altération seulement si l'original externe est conservé. |

WP12-R2 ne fait pas ces décisions à la place de l'Owner. Toute campagne future doit avoir une décision signée distincte liant un manifeste figé, une tentative et une destination unique.
