# WP12-A — Décision Owner de clôture documentaire des quatre expériences

**Date de consignation :** 2026-10-28.  
**État limité :** `WP12A_FOUR_EXPERIMENTS_DOCUMENTARY_CLOSED` (libellé descriptif de cette décision, sans promotion de qualification).  
**Source de la décision :** instruction explicite de l'Owner dans la conversation de travail, intitulée « Décision Owner — WP12-A / PR #64 ». Cet enregistrement est une transcription opérateur ; il ne constitue pas une signature cryptographique.

## Décision et portée

L'Owner approuve la clôture documentaire des quatre expériences ciblées WP12-A, en maintenant les limites scientifiques du dossier. Cette décision concerne exclusivement les résultats de développement suivants :

| Expérience | Tentative retenue | Résultat |
|---|---|---|
| WP07 harmonique | `dev-a3083df78b03` | PASS ; données numériques brutes NOT_EXPOSED |
| Newmark r3 | `dev-b81ed5a46142` | PASS ; convergence temporelle bornée |
| Harmonique réduit | `dev-0dd64d435dd1` | PASS ; base tronquée avec résidu physique libre de 1 N |
| Accélération de base complexe | `dev-f5bae47755b8` | PASS ; référence scalaire conditionnelle aux opérateurs assemblés |

L'Owner autorise aussi la fusion de la PR #64 sous réserve du HEAD exact `f6d70fb5304f76467b2e4117974f210b89e14ff0`, d'un diff limité aux quatre documents revus et du respect des protections GitHub. La PR a été fusionnée en `dfeaa5d18c853e0c9ccaec418b3de16fc29ba035`. Le diff vérifié contient uniquement ces quatre documents, dont les blobs Git sont identiques à ceux du HEAD revu.

## Documents approuvés

Les SHA-256 ci-dessous portent sur les **octets des blobs Git normalisés**, afin d'identifier les documents intégrés indépendamment de la matérialisation LF/CRLF d'un checkout Windows.

| Document | SHA-256 blob Git |
|---|---|
| [Rapport de clôture](WP12A_SCIENTIFIC_CLOSURE_REPORT.md) | `5942204b2cee427d49bdde4d2fe064b4a69a951071b4ba93722c6bc550149d1a` |
| [Matrice des preuves](WP12A_EVIDENCE_MATRIX.md) | `119687f1de0a4e8a7fcbb7a52237ea30cf4bd2c18b77247c3de50ea632d449ac` |
| [Lacunes de validation](WP12A_REMAINING_VALIDATION_GAPS.md) | `82b3b871682e77ab2b8c5e9046c44492aacf3b44e165527626bac8023b745448` |
| [Préparation release](WP12A_RELEASE_READINESS.md) | `b9b8da7941ff46d2a3c23184ddac981b399f39c6ce9d549363da0efcaf0481d5` |

Les empreintes fournies dans la revue antérieure étaient celles des fichiers matérialisés localement sous Windows ; elles ne sont pas des empreintes de blobs Git. Les preuves scientifiques et leurs empreintes externes restent celles de la matrice, inchangées.

## Limites maintenues et suites

Les quatre PASS ne démontrent pas une validation physique externe ni un résultat sur une identité scientifique unique du candidat courant. Les références partagent certains opérateurs assemblés. Les échecs historiques Newmark, le refus préalable à réservation et l'échec consommé du writer restent inchangés. Les ledgers ne sont ni modifiés ni réinitialisés.

**WP12 global reste OPEN ; la qualification globale de QF Solver n'est pas acquise par cette décision.** Cette clôture documentaire n'autorise aucun FEM, aucune réservation, aucun retry, aucune modification de seuil, aucune publication ni aucune autre fusion.

Priorités de validation futures : référence physique externe et incertitudes ; revue de continuité des identités scientifiques vers le candidat release ; stratégie de preuve prospective pour les valeurs WP07 non exposées ; étude des erreurs de troncature et des résidus physiques ; extension indépendante aux modèles multi-DDL, amortissements et régimes temporels et fréquentiels variés. Leur exécution exige les gates et décisions Owner applicables. L'intégration release est à apprécier par les gates WP12/WP13 distincts ; aucune lacune ne vaut automatiquement approbation ou refus de publication.
