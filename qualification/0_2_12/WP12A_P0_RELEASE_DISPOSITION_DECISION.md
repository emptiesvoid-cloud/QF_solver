# WP12-A — Projet de décision de clôture bornée pour 0.2.12 alpha

**Statut : PROPOSÉ — NON APPROUVÉ.** Ce texte prépare une décision Owner. Il ne modifie aucun statut historique et n’est ni une autorisation de calcul, ni un avis de publication.

## Fondement

- Les quatre expériences de développement antérieures sont closes documentairement par la décision PR #65, avec leurs limites et échecs conservés.
- La campagne `wp12a-p0-batch-20261029-r1` a exécuté six sentinelles : 6 PASS, six tentatives consommées, aucun retry. Contrat SHA-256 `59052cf36486a68d7f91f78972d92be3830970bb5384bf59faa108ed60747f9f` ; rapport SHA-256 `28c1fbf527ad2c86c211f64070f0eea01c046d26b96e1a93831da5af934c73ee`.
- La [matrice actualisée](WP12A_P0_RELEASE_DISPOSITION_MATRIX.md) présente les 20 capacités, dont 11 MUST. Les MUST exigent une disposition bornée traçable ; les PARTIAL et les exclusions ne sont pas des PASS complets.
- Les essais P0 utilisent la science `7406e34efc28ed8f18c15440115595dfa3dd9ca5`. La release `098382938df641751271acb62b7c8e666cfa8e09` diffère notamment dans l’intégration des charges de face QUAD8/HEX20. Les preuves ne sont pas réétiquetées comme exécutées sur cette release.

## Proposition soumise à l’Owner

> J’accepte la **clôture bornée de disposition WP12-A pour la release 0.2.12 alpha**, sur la base de la matrice de disposition après P0 et des dix résultats de développement enregistrés, dans les seuls domaines explicitement couverts. J’accepte pour cette disposition les statuts PARTIAL, INCONCLUSIVE, NOT_TESTED et DEFERRED qui subsistent et les limites ci-dessous ; ils ne deviennent pas des PASS de capacité générale.
>
> Je limite les revendications dynamiques aux petites fixtures et contrats effectivement testés. Les mesures P0 et WP07 qui ne sont pas archivées restent NOT_EXPOSED. Les cinq contrôles de symétrie spécifiques et le cas de famille WP00, le dispatch dynamique non démontré et la continuité des dépendances modifiées ne sont pas présentés comme vérifiés sur le HEAD release par les dix essais. L’assemblage et les réactions ne sont pas déclarés exhaustivement vérifiés ; les charges de face HEX20 sont suivies séparément. Le support dynamique MPC/RBE n’est pas revendiqué sur la foi des preuves statiques ou refus bornés. D01 reste INCONCLUSIVE et C4 NOT_ACQUIRED ; D02 reste CLOSED_BOUNDED ; HDF5 reste expérimental et DEFERRED pour la portée examinée.
>
> Je conserve sans requalification tous les FAIL et tentatives historiques, notamment WP07, Newmark et le writer. Je ne revendique ni validation physique générale, ni qualification générale du solveur. Cette disposition n’achève pas WP12 ou WP13, ne décide pas de la release ou de la publication et n’autorise aucun nouveau calcul.

## Lecture des critères

Sur la base des preuves examinées, aucune nouvelle expérience n’est **automatiquement** requise pour demander cette décision bornée : la matrice de release accepte qu’un MUST reçoive une disposition tracée, y compris PARTIAL avec restriction. Toutefois la recommandation de clôture globale WP12-0 prévoit également la revue Owner, le traitement des écarts, les dépendances touchées et la preuve API/IO/dispatch pour les routes revendiquées. Une approbation de cette proposition ne dispense pas les gates WP12-F et WP13, ni ne permet d’affirmer que chaque contrôle MUST de WP12 global est exécuté.

Si l’Owner refuse une exclusion ou souhaite revendiquer plus que le périmètre prouvé, établir d’abord si une preuve existante applicable suffit. Sinon préparer uniquement le contrôle de non-régression précis associé : projection symétrique/fallback/refus et famille WP00 ; chaîne API/CLI/DTO revendiquée ; ou continuité de la dépendance de charge modifiée, dans sa campagne compétente. Les nouveaux calculs scientifiques exigent des identités, budgets, manifestes et décisions distincts. Ne pas relancer par défaut les dix expériences.

## Effet de la décision

Avant approbation : `WP12A_PARTIALLY_CLOSED`, sous-campagne de quatre expériences `WP12A_FOUR_EXPERIMENTS_DOCUMENTARY_CLOSED`, P0 exécuté 6/6 PASS bornés. Après une approbation explicite de ce texte : `WP12A_CLOSED_BOUNDED_FOR_0_2_12_ALPHA` **comme disposition de scope acceptée**, distincte de la qualification et des gates WP12/WP13. Une fusion documentaire, si souhaitée, relève d’une décision Git distincte selon les protections applicables.
