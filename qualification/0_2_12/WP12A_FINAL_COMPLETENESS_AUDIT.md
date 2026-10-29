# WP12-A — Audit final de complétude

**Verdict : `WP12A_PARTIALLY_CLOSED`.** La campagne de quatre expériences ciblées est terminée et sa clôture documentaire est approuvée. Le chantier WP12-A défini dans la roadmap 0.2.12 est plus large : ses capacités héritées, ses contrôles transversaux et ses exigences MUST ne sont pas tous démontrés sur une identité cible actuelle ni disposés par la décision Owner limitée aux quatre expériences. Il n’y a pas de contradiction qui bloque la conservation des résultats ; il manque une disposition de complétude du chantier plus large.

**WP12 reste `OPEN`. La qualification globale de QF Solver n’est pas acquise.** Aucun calcul scientifique, solveur, assemblage, réservation ou test de corps scientifique n’a été lancé dans cet audit.

## Identité examinée et méthode

- Branche de release : `emptiesvoids-cloud/0.2.12`.
- HEAD vérifié après intégration de la PR #69 : `baf4dc335d61e9a7b6d9289edd280bbb224d84b9`.
- Tree : `76b381aef94f8fa84fbbc818d402a9ee27b93f43`.
- La PR #69 ne modifie que `AGENTS.md` et les tests synthétiques de politique pour désigner le contrôleur HEX20. Elle ne modifie ni les sources scientifiques WP12-A ni les quatre documents de clôture.
- Définition du chantier : [roadmap 0.2.12, WP12-A](ROADMAP.md#wp12--vérification-des-capacités-héritées-et-campagnes-complémentaires) et matrice des capacités [WP12-62](vv_master_plan/WP12_62_CAPABILITY_AUDIT.md). WP12-A est un chantier interne, pas un WP officiel autonome. La matrice l’assigne aux méthodes partagées, à la dynamique, aux contraintes et aux interfaces.
- Critères de clôture généraux : [périmètre et acceptation WP12](wp12_preparation/wp12_scope_and_acceptance.md), section 5. Ils demandent notamment une décision Owner sur le périmètre et ses exclusions, la disposition des MUST sur une identité vérifiable, le traitement explicite des échecs/lacunes, la non-régression des interfaces et dépendances modifiées et une revue Owner.
- Documents examinés : PR #64 (`dfeaa5d18c853e0c9ccaec418b3de16fc29ba035`, quatre documents) et PR #65 (`5f6effa6bfb8d1fba4c6acd2f754de45775f02d0`, décision Owner). La release est depuis avancée au HEAD indiqué ci-dessus.
- Résultats documentaires vérifiés : les 31 artefacts référencés par la matrice de preuves #64 existent dans le dépôt d’évidence local et leurs SHA-256 correspondent. Les deux ledgers ont été lus sans modification. Les PR #64/#65 ont bien des blobs Git conformes aux empreintes archivées dans la décision.

Empreintes des documents intégrés (blobs Git) : rapport #64 `5942204b2cee427d49bdde4d2fe064b4a69a951071b4ba93722c6bc550149d1a`, matrice `119687f1de0a4e8a7fcbb7a52237ea30cf4bd2c18b77247c3de50ea632d449ac`, lacunes `82b3b871682e77ab2b8c5e9046c44492aacf3b44e165527626bac8023b745448`, readiness `b9b8da7941ff46d2a3c23184ddac981b399f39c6ce9d549363da0efcaf0481d5`, décision Owner #65 `b623dbc755383c15656857720038f8dfd9d30a6f1df5dd1e90e84b99329c95ad`.

## Les trois niveaux de complétude

| Niveau | Conclusion | Justification |
|---|---|---|
| 1 — Campagne scientifique ciblée | **ATTEINT** | Les quatre nodeids ciblés ont chacun un PASS de développement, une tentative retenue, des identités et des preuves traçables. La décision Owner ferme explicitement la documentation de ces quatre expériences. |
| 2 — Chantier WP12-A défini pour 0.2.12 | **NON DÉMONTRÉ — PARTIEL** | La roadmap inclut WP04–WP07, les opérateurs partagés, MPC/RBE et les interfaces. La matrice WP12-62 affecte 11 capacités P0/MUST, 8 P1/SHOULD et une P2/DEFERRED à WP12-A. Les quatre résultats couvrent des sentinelles étroites ; plusieurs contrôles MUST restent `NOT_RUN` sur l’identité candidate auditée dans la matrice, la projection WP04 n’est pas rejouée après sa modification et des dépendances/contrats plus larges demeurent seulement historiques ou bornés. La décision #65 ne dispose que les quatre expériences, pas tout le chantier. |
| 3 — Qualification physique générale | **NON ATTEINT, et non exigé pour la clôture documentaire ciblée** | Aucun niveau D de validation physique externe n’est acquis. Les références partagent certains opérateurs assemblés et les modèles sont petits. La roadmap classe la corrélation WP12-E comme optionnelle avant 0.2.12 ; elle ne doit pas être ajoutée comme gate autonome. |

## Résultats des quatre expériences retenues

| Cas | Résultat retenu | Identité scientifique / contrôleur | Niveau et limites |
|---|---|---|---|
| WP07 harmonique | `PASS`, série `dev-a3083df78b03` | Science `630d22b7667a0d84dd7b136b9f8c7d89ae00fc66`, fp `969dd027…`; contrôleur `148f850412c907e62ae899961afc8ce5b18d0ded` | SDOF BEAM2, un DDL libre. Assertions relatives/absolues et de signe ; sorties numériques brutes `NOT_EXPOSED`. Référence scalaire partage les matrices assemblées. |
| Newmark r3 | `PASS`, 34/34 assertions, `dev-b81ed5a46142` | Science `5f96dd604fe40279ead0186f49be77e7a0bbeac1`, fp `d4743785…`; contrôleur `b206e6f520e9b03c3c925c3bef20883f01aa9800` | BEAM2 SDOF libre et non amorti ; ordres de déplacement 1,99724 et 1,99931. Résidu réduit/modal et dérive énergétique bornés ; le travail extérieur n’est pas mesuré et le résidu n’est pas global FEM. |
| Harmonique réduit | `PASS`, 11/11 assertions, `dev-0dd64d435dd1` | Science `bf88803a8464a805e953013a2593fb06e6ea4659`, fp `dea993f9…`; contrôleur `d379820e794653bde65cae193c920b34d38a0fa3` | TET4 à 3 DDL. Écart relatif direct/base complète max `2,27963e-16`; résidu physique libre max `2,48253e-16 N`. La base tronquée donne réponse nulle, résidu modal nul, mais résidu physique libre de `1 N`. Cela ne constitue pas une borne de troncature. |
| Accélération de base complexe | `PASS`, 48/48 assertions, `dev-f5bae47755b8` | Science `7406e34efc28ed8f18c15440115595dfa3dd9ca5`, fp `a7dcb27d…`; contrôleur `1b8d6a76b062039566dbf0f2bd508b7990035dca` | BEAM2, un axe et un DDL libre ; `exp(+iωt)`, fréquence propre `8,717275 Hz`, balayage comprenant DC et points `0,98/1,02 f₁`. Résidu physique libre max `1,590e-15 N`. Référence conditionnelle aux opérateurs assemblés ; à DC, certains phasors absolus restent indisponibles et le phasor nul n’a pas de phase. |

Les quatre essais sont liés à quatre HEAD scientifiques et à plusieurs contrôleurs distincts. Ils ne prouvent pas une campagne exécutée sur un HEAD scientifique unique de release. Les contrôleurs et les sources restent néanmoins liés par les manifestes, préflights et décisions archivés ; aucune preuve n’est transférée à une autre identité.

## Anomalies et états conservés

- Les deux ledgers totalisent **10/130** tentatives Dynamics : ledger historique v1 SHA-256 `20670ceedfe1cc969ce614df13b8bd94b108f43e2e2892cf1601a8607a3dad37` (5 tentatives : 4 `PASS`, 1 `PYTEST_FAILED`) ; ledger v2 SHA-256 `01aec735ca1f7bfc06f4873df533089bda3f9253555911885ef5dc5b9ba9dd88` (5 tentatives : 4 `PASS`, 1 `PYTEST_FAILED`). Le v2 est lié au v1 par empreinte de prédécesseur.
- Le total est **8 PASS / 2 PYTEST_FAILED**. L’échec Newmark historique `dev-a81c2f0d9e74` reste conservé. L’échec d’infrastructure du writer `dev-301ba3b31a43` reste une tentative consommée ; son verdict mécanique n’est pas établi. Le PASS r3 ne requalifie pas ces tentatives.
- Les refus avant réservation, les préflights collect-only et les manifestes `PREPARED_NOT_AUTHORIZED` ne sont pas des tentatives scientifiques.
- L’ancien défaut de round-trip WP07 reste conservé pour son identité historique. Son correctif ne requalifie pas rétroactivement l’échec.
- Les deux échecs HEX8-SRI sont hors de WP12-A et restent `CLOSED_NEGATIVE`; ce document ne les rejuge pas.

## Contrôle de cohérence des clôtures #64 et #65

Les documents #64 exposent les limites importantes : WP07 `NOT_EXPOSED`, Newmark libre/non amorti et résidu réduit, harmonique direct/base complète à opérateurs partagés et réponse tronquée inadéquate, excitation de base un axe/une coordonnée, archives locales et identités distinctes. La matrice rattache aux rapports, `run.json`, stdout, préflights, manifestes, décisions et sidecars. Les 31 lignes d’artefacts vérifiées concordent.

La décision #65 approuve explicitement **la clôture documentaire des quatre expériences**, transcrit l’instruction Owner sans prétendre à une signature cryptographique, conserve WP12 `OPEN`, et nie la qualification globale. Elle n’affirme ni que les 20 capacités attribuées à WP12-A sont closes, ni que les quatre runs ont la même identité source. La formulation est donc cohérente avec le périmètre de PR #64 et ne vaut pas clôture complète du chantier WP12-A.

**Aucune correction des documents #64/#65 n’est requise pour les présenter comme clôture des quatre expériences.** Le présent audit ajoute la distinction explicite avec le chantier WP12-A plus large.

## Décision

Le verdict sans extension de portée est **`WP12A_PARTIALLY_CLOSED`**. La sous-campagne de quatre expériences est close documentairement ; le chantier WP12-A complet de la roadmap n’est pas démontré comme terminé au niveau 2. Ce verdict ne signifie pas que les quatre résultats sont invalides, ni qu’un défaut dynamique est démontré.

Pour les preuves et critères par capacité, voir [la matrice exigences→preuves](WP12A_REQUIREMENT_TO_EVIDENCE_MATRIX.md) et [les lacunes / impact release](WP12A_RESIDUAL_GAPS_AND_RELEASE_IMPACT.md). La recommandation de clôture distingue ce qui peut être considéré comme fini de ce qui demande encore une disposition : [WP12A_FINAL_CLOSURE_RECOMMENDATION.md](WP12A_FINAL_CLOSURE_RECOMMENDATION.md).
