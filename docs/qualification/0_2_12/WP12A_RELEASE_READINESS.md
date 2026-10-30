# WP12-A — Préparation release 0.2.12

| Décision | Verdict proposé | Portée / réserve |
|---|---|---|
| Quatre expériences ciblées | PASS de développement acquis ; clôture proposée pour revue Owner | Quatre nodeids, identités et preuves distinctes ; ne réécrit aucun échec historique |
| Maturité scientifique WP12-A | PARTIELLE ; aucune promotion automatique | SDOF/3 DDL, opérateurs partagés, pas de validation externe D ; [lacunes](WP12A_REMAINING_VALIDATION_GAPS.md) |
| Intégration au candidat 0.2.12 | Documentation proposée pour revue | Tests et instrumentation intégrés aux commits historiques, mais exécutions sur HEAD scientifiques différents ; ne pas affirmer un nouveau PASS commun sur HEAD release |
| Qualification globale du solveur | NON QUALIFIÉE par ce dossier | WP12 reste OPEN et la décision release appartient à ses propres gates |

Les fonctionnalités implémentées comprennent les voies harmoniques, Newmark et excitation de base. Les quatre tests ont été exécutés et les cas numériques sont vérifiés dans les limites documentées. La comparaison analytique est conditionnelle aux opérateurs assemblés ; aucune validation externe de niveau D n'est démontrée. Ce dossier ne publie aucune release ni ne décide d'une maturité générale.

Voir [rapport](WP12A_SCIENTIFIC_CLOSURE_REPORT.md) et [matrice](WP12A_EVIDENCE_MATRIX.md). Les archives externes Windows doivent être rendues accessibles et conservées sous contrôle Owner pour une revue reproductible ; les hashes sont des contrôles d'intégrité, pas des signatures d'auteur.
