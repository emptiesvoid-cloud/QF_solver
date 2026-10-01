# WP14 — dossier prêt pour revue Owner (portée limitée)

**État du dossier : READY_FOR_SCOPED_OWNER_REVIEW.**

**WP14 officiel : HOLD, 0/1 point ; total officiel : 95/100.**

Périmètre présenté : G03 borné R4.4, G06 R2.2 et G08, candidat technique d4decf99ab5bfe96a54f17835b35e6eb8c5c49cc sur codex/wp14-g03-g06-g08-remediation. Ce dossier ne clôt pas WP14 et n'autorise ni release ni attribution de point.

| Sujet | Résultat | Limite |
|---|---|---|
| G03 public borné | R4.4 PASS_WITH_LIMITATIONS / PASS_CANDIDATE_PACKAGE_ONLY : 551 sources + 745 documents, zéro constat. Wheel/sdist construits et scannés (551/559 fichiers, zéro constat), 473 modules, sondes installées dedans/dehors PASS. | Les scans du dépôt entier restent FAIL ; 206 pièces contrôlées et les binaires sont hors périmètre. Le paquet est en version 0.2.8, sans claim de release 0.2.9. |
| G06 documentation | R2.2 PASS_WITH_LIMITATIONS : 22/22 documents du périmètre Owner-review complets. Backlog séparé : 89 documents, 86 sans reviewer, 89 sans approver ; advisory/non-bloquant pour les états de cycle de vie suivant la politique R2.2 choisie par l'Owner. Tests docs 62 passés/6 ignorés, MkDocs strict sans warning/error, packaging ciblé 13 passés. | Les états revendiquant une approbation Owner doivent garder les métadonnées requises. Attribution de rôle auto-attestée depuis la conversation, sans signature numérique/indépendance. Un erratum séparé corrige le hash de politique mal transcrit ; reçu historique préservé. |
| G08 CI | [Run quality.yml 36552758385](https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/36552758385), succès sur le SHA candidat d4decf99ab5bfe96a54f17835b35e6eb8c5c49cc. Les 4 jambes Ubuntu/Windows × Python 3.10/3.13 PASS ; chaque jambe : 3 287 passés, 22 ignorés, 107 désélectionnés ; couverture 85,47 % Ubuntu et 85,50 % Windows, seuil CI 80 %. Vérifications ciblées de preuves : 9 passées. | Le rapport local G06 R2.2 garde G08=NOT_RUN, exact à sa date ; le run GitHub est une preuve ultérieure, séparée. |
| Campagne ingénierie du run | 3 643 passés, 36 ignorés, 206 désélectionnés, 14 avertissements, 0 échec ; compileall, verify --quick (QF et MITC4) et verify-tet10 PASS. Le lot documentaire benchmark a 23 passés/1 ignoré. | Les ignorés/désélectionnés ne sont pas des PASS ; ce n'est pas une qualification de release. |
| G04/G05/G07/G09 | Recheck conservé : G04 PASS (86,19 %, seuil 84 %) et G05 PASS (5/5 commandes). R4.4 démontre le build/sondage du candidat. | G04/G05 conservent les limites de périmètre de leurs rapports. Version/release 0.2.9 et décision de gouvernance G09 restent ouvertes. |

## Décisions Owner proposées

1. Accepter G03 R4.4 uniquement pour le périmètre public sélectionné, en maintenant les FAIL dépôt-entier.
2. Confirmer que G06 R2.2 traite le backlog indiqué comme advisory/non-bloquant pour les états concernés.
3. Enregistrer G08 PASS pour le SHA candidat d4decf99ab5bfe96a54f17835b35e6eb8c5c49cc, sans réécrire le rapport R2.2.
4. Maintenir WP14 à HOLD jusqu'aux décisions restantes de dépôt entier/release et au traitement séparé des preuves historiques manquantes.

Les seuils n'ont pas changé ; les FAIL historiques et absences de données sont conservés. Entre la base G03 a4a64123ec38304f2d1aa02bc3cd0617d31bbb5c et le SHA CI d4decf99ab5bfe96a54f17835b35e6eb8c5c49cc, aucun changement n'est présent dans src/, docs/, pyproject.toml, requirements/ ou .github/workflows/. Les pièces de ce dossier sont des ajouts documentaires postérieurs au run, pas du code prétendument retesté. Aucun ledger, point, tag ou publication n'est modifié.
