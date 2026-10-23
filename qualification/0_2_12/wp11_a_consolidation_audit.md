# WP11-A — Audit de consolidation de la branche d’intégration

Date : 2026-10-23
Dépôt : emptiesvoid-cloud/QF_solver
Branche auditée : codex/v0.2.12-integration
HEAD vérifié avant l’audit : a0846af0249ac3f3a37ec4e9c4900f1311c86238
Tree vérifié avant l’audit : b3b9886b7aa96874e5dfade5ea0e1c22c3b137ca
Origin : https://github.com/emptiesvoid-cloud/QF_solver.git
État initial : propre.

## Conclusion

**WP11 reste OPEN.** La branche contient les contrats publics historiques et des intégrations bornées de D02 et E01-BC. Les tests ciblés de l’audit confirment la cohérence de l’inventaire d’API, des signatures publiques, des sérialiseurs unitaires et de certains contrats WP11. Ces résultats ne démontrent pas le « gate d’intégration complet » demandé par la roadmap.

Aucun défaut de formulation ou P0 n’a été identifié dans le périmètre intégré. L’examen indépendant considère l’intégration Hencky BC compatible avec son périmètre approuvé. Il relève néanmoins le gate WP11 encore ouvert et deux actions documentaires P2. Aucun calcul FEM qualifiant n’a été lancé pour cet audit.

La conclusion recommandée est donc : **conserver WP11 ouvert, préparer une matrice de clôture fondée sur les capacités effectivement retenues, puis fermer chaque lacune de contrat et de non-régression applicable.** Aucun nouveau gate de publication n’est ajouté ici.

## Référentiel de clôture applicable

Le document faisant foi pour le découpage opérationnel est qualification/0_2_12/owner_provided/QF_Solver_v0.2.12_roadmap_WPE01.md.

Il indique :

- WP11 : « Intégration, résultats, API et sérialisation », statut OPEN, « Gate d’intégration complet à démontrer » (ligne opérationnelle WP11).
- La séquence opérationnelle place D01/D02, puis E01 A–E, puis WP11 : « intégration, API, sortie et contrats de sérialisation des nouvelles fonctionnalités »; WP12 vient ensuite pour V&V intégrée, performances et périmètre de support (§4).
- L’étude prospective de la partie II réutilise les numéros WP11/WP12 pour generalized-alpha/coques. Ces numéros ne sont pas les packages opérationnels. L’audit applique le découpage opérationnel, conformément aux consignes de lecture de la roadmap.

La roadmap ne fournit pas de liste détaillée de tests d’acceptation ou de seuils propres à WP11. Le présent audit n’en invente pas : il relève les preuves disponibles et les lacunes pour le gate général formulé par l’Owner.

## Inventaire

Le checkout contient 1 688 fichiers Python :

| Racine | Fichiers |
|---|---:|
| src | 497 |
| tests | 665 |
| scripts | 505 |
| qualification | 14 |
| examples | 1 |
| tools | 3 |
| racine (main_solveur.py, mitc4_solver.py, qf_solver.py) | 3 |

src/solveur compte 496 modules répartis ainsi : root 3, api 2, benchmarks 13, cli 8, compat 14, compatibility 3, contact 8, core 106, elements 32, execution 3, io 24, large 31, loads 3, materials 11, mesh 16, post 10, verification 209. src/qf_solver contient la façade d’un module.

La liste complète et triée des modules Python présents est jointe dans wp11_a_python_module_inventory.txt, SHA-256 a8b0c0fd3c29a425f3382419acaef9547d2b5a0d1c70a2e67160d600a254a2cb. Les différences d’arbres exactes par rapport aux branches C02, D01 et E01 sont dans wp11_a_branch_tree_differences.tsv, SHA-256 b17645e005869ff59c920417886b240eea0f61e9619dce1094f4d72262e16f04.

## Matrice de consolidation

| Composant | Intégré | Tests / preuves disponibles | Preuves FEM | Maturité constatée | Action nécessaire |
|---|---|---|---|---|---|
| WP00–WP07 — contrats, analyses dynamiques préparées, excitation/réduction/Newmark | Oui, hérités de la branche d’intégration | Clôtures opérationnelles historiques rapportées; contrats d’API généraux présents | Preuves selon les clôtures historiques, non réexécutées ici | CLOSED selon la roadmap historique | Aucune action WP11 déduite par cet audit; conserver les limites de chaque clôture |
| WP08 — constitutif / contraintes / résultats non linéaires | Oui | Régressions ciblées et rapports WP08–WP10; 54 cas de non-régression choisis ont déjà passé dans l’intégration BC | V&V bornée à ses contrats | CLOSED_BOUNDED | Aucun élargissement de qualification; résultat et mesures gardent les contrats existants |
| WP09 — tangentes corotationnelles / robustesse NL | Oui | Régressions bornées historiques; incluses dans le batch antérieur de 54 cas décrit par BC | V&V bornée | CLOSED_BOUNDED | Pas de promotion à une tangente générale |
| WP10 — états internes / checkpoints / convergence NL | Oui | Contrats d’état/checkpoint existants; tests antérieurs ciblés dans le batch BC | V&V bornée, sans revendication Newton générale | CLOSED_BOUNDED | Conserver la version et la portée des checkpoints; ne pas assimiler au rollback général |
| WP-D02 — récupération de contraintes dynamiques solides | Oui : implémentation post-traitement et trois wrappers API provisoires | Rapport D02 : six batches, 53 nœuds uniques PASS; 15 nœuds API/sérialisation dans le candidat. Résumé courant décrit une dérivée assainie, les journaux/récépissés originaux étant archivés à part | Indépendance limitée aux fixtures documentées, notamment transitoire TET4; pas de contact/BEAM2 | CLOSED_BOUNDED selon le rapport de clôture; pas une qualification générale | Maintenir explicitement les limites. Clarifier la ligne D02 OPEN du snapshot Owner du 18/10 comme état historique |
| WP-E01-BC — Hencky matériel et tangente au point matériel | Oui, sélection minimale : deux kernels expérimentaux, deux modules de tests, registre NUMERICAL_UNIT, rapports et overlay | 41 cas matériau et 35 cas tangente bornés, réexécutés sur la cible BC; contrôles API non exposés; 76 cas E01 au total | Aucun assemblage FEM global Hencky; essais local force-only dans le scope 41 cas. Le certificat GF4 esclave est une preuve historique pour son gel exact | OPEN_WITH_BOUNDED_CERTIFICATES; matériau/tangente au point matériel VERIFIED_BOUNDED dans les scopes écrits | Garder les kernels opt-in; aucune exposition API/fabrique requise tant que l’intégration élément/global n’est pas autorisée |
| J2 global / tangent assemblée E01 | Non intégré | Échecs historiques et directions faibles toujours non résolus dans les rapports E01 | Pas de preuve globale indépendante | UNRESOLVED | Bloque toute revendication de tangente J2 globale, mais pas l’intégration BC du seul Hencky au point matériel |
| Newton/contact expérimental E01 et adaptateurs Hencky TET4/HEX8 | Non intégrés | Plusieurs campagnes historiques, résultats/scopes hétérogènes; exclus par le rapport BC | Le certificat BA est uniquement GF4 TET4 et sous-système esclave; le verdict brut global reste FAIL; le maître n’est pas vérifié | Non qualifié hors du certificat borné | Ne pas importer ces voies sans réconciliation des chemins partagés et nouvelle revue/autorisation |
| WP-C02 — contact/friction, géométrie, assemblage GF2–GF5 | Non intégré dans la branche d’intégration | Branche indépendante; 53 chemins de tests différents de l’intégration dans l’arbre comparé | Preuves C02 sur sa branche, sans transfert automatique au candidat commun | Expérimental / package encore séparé | Réconcilier avant toute intégration : partage de chemins contact avec E01 et plusieurs fichiers API/validation sont divergents |
| WP-D01 — flexibilité résiduelle dynamique / contrôleur WP04–WP05 | Non intégré dans le candidat actuel | Branche indépendante; 126 chemins de tests différents et 95 chemins src/solveur différents dans l’arbre comparé | Pas de transfert de preuve au candidat commun | OPEN selon la roadmap Owner du 18/10 | Suivre l’ordre de roadmap et décider si ses sorties entrent dans le scope WP11. Aucun défaut de code D01 n’est conclu à partir de cet audit |
| WP11 — intégration / résultats / API / sérialisation | Partiellement démontré par les contrats existants, le D02 borné et la documentation BC | API publique : 77 symboles, 30 stables/47 provisoires selon tests; signatures critiques; sérialisation nodale/modale; JSON d’entrée v1 seulement; résultats expérimentaux versionnés présents | Pas de nouveau FEM | OPEN | Produire la matrice de contrat manquante pour les capacités réellement incluses, résoudre les écarts doc/version et vérifier la non-régression sur le candidat complet |
| WP12 / WP13 | Non clos par cette branche ou cet audit | WP12 vise V&V intégrée/performance; WP13 packaging/docs/publication | Aucun claim nouveau | OPEN | WP12 doit consommer un contrat WP11 et un gel commun explicites; WP13 garde sa décision séparée |

Les nombres de chemins de branches sont des différences entre les arbres complets, non des nombres de nouveaux modules. Les chemins partagés peuvent porter des contenus différents. L’inventaire joint conserve les statuts Git exacts et permet l’examen chemin par chemin.

## Cohérence API, résultats et sérialisation

La façade qf_solver est définie par src/qf_solver/__init__.py, src/solveur/api/public.py et les exports historiques. Les tests de contrat déclarent 77 exports, dont 30 stables et 47 provisoires; les wrappers de récupération de contraintes D02 sont provisoires. Les signatures principales (load_model, check_mesh, solve_model, save_result) sont contrôlées.

### Empreintes vérifiées

| Fichier | SHA-256 |
|---|---|
| src/solveur/api/public.py | 0630fd68ac6174e3d0e341caae45d7d9b6d02604e6db4e82f2b8462c12c9ad9a |
| src/solveur/api/__init__.py | c314ea7fb5877d4c0b564a71f2ffdc12f376ac339be5449b2a02106c9c757638 |
| src/qf_solver/__init__.py | 34a6db74234d4e52a90b7313fb78a009cd2af6eeb88f6969af2aa1821c6ac4d7 |
| src/solveur/core/results.py | 83ed02b68c8de953f50c2a4bae42ddc8180069e10b52876aee2e523e120b27fa |
| src/solveur/core/result_serialization.py | 83c8eaf0267179fefb2b5ceafbb25d38e6be99a05f59dce121d6535e58c392ea |
| src/solveur/io/schema.py | 310489312bea1ee99c253328adf792ff050185b917d6b8c70a565e9afeedcbd2 |
| src/solveur/post/dynamic_stress.py | aef4c4244a5c2490478cecefde6864a42c50ac2a71dfb42da77bce801163b0d1 |
| src/solveur/materials/finite_strain_hencky.py | b318dad553073f848b96528c61589ab2015c1eb1dd8fa52cb0bd52d13b09eab2 |
| src/solveur/materials/finite_strain_hencky_tangent.py | 31109bbbf2353f9bbd86b7a7b0e5fe776016fdd1638550848b58b8bd4afef135 |
| tests/unit/test_public_api_contract.py | 22f09695ae82c39c54ed577a5390e3b6b9a9552468e95f037ca4802a7794a2ce |
| tests/unit/test_result_serialization_contracts.py | b7de742efa0cb8ca23161ca74864049e143d0c6d678cc0cf4de1c9e05659652b |
| tests/unit/test_wp11_j2_closure.py | 9a753a551155341aab97aad0fd261f78c6eb23d22d85b2fa2c74207db94038db |
| tests/unit/test_wp11_multifamily.py | bb7a4bdbbb7c4b2cb0770a0d09d012d0cf92f1c6f7dbd069c4d2b5afde334e92 |
| tests/unit/test_wp_d02_dynamic_stress.py | c3b45ce5b7dbc3ead709f28638ef6f4d4101db23a36e46b4a231e4e7601e3e67 |
| tests/unit/test_wp_d02_roundoff_guard.py | 870e519c221aee54dd85a031a1e2c3dd592c7ad4e531e8d097e8b46fcbbb4bd6 |
| tests/unit/test_wp_e01m_hencky_material_point.py | cdd2651e9427c0e64284a75671d83d4f14cdd916a979759be0422f44dde84bfc |
| tests/unit/test_wp_e01q_hencky_tangent.py | a99bcc6ea32bff3e2a669d2923380033f23e587aab95f612ab4047f98b7d7b50 |
| tests/unit/conftest.py | 8763ea8cc581c376a667ea8ae3ded5958a2dd52d47e3106694b3f2374a219a52 |
| tests/conftest.py | d8c1cb0bfc88e7e35ba0868489a47401a69632c88ed2ce0b0802cca5c18504e0 |
| pyproject.toml | 5e2d09bfd4995659e8bcc83ba0c8a3d5b87b688f20f5842dc894ca2dccc59904 |
| docs/reference/qf_solver_api.md | 522adca6892170230682e662b45ea1caf5a692ec61c215fe7830fe252f381176 |
| docs/reference/api_stability.md | 12a5f16057e8e96ca38a65901410d9e9240e08f04a3b60c75559944c055936df |
| qualification/0_2_12/wp_d02_bounded_closure_report.md | c0e6c3b0e5f87375861b7df82e1b9038bf60cb5ac836c8d656888b1573ec1d05 |
| qualification/0_2_12/wp_d02_integration_validation_summary.json | b09789e7e3b1a37ef19c53e63c7eac7d9a7cd1df936c02469452354050264e2e |
| qualification/0_2_12/wp_e01_ba_bounded_slave_certificate_report.md | 7eace9f62649bd452b058ad318a2489682d22fe0eb1a9aec739c9b05df1f1fca |
| qualification/0_2_12/wp_e01_bb_global_scientific_audit_and_closure_readiness.md | c2e83b63128fa4a0cc985c516c75d7fcaeb54dfc252d4d47311afaef045cb88f |
| qualification/0_2_12/wp_e01_bc_integration_report.md | f7c8adb095d978dd44f2cb72b34c751c04817b6af609c0b8bffdf7bb333716ff |

Les contrats de résultats se trouvent principalement dans src/solveur/core/results.py, src/solveur/core/result_serialization.py et les writers JSON/CSV/VTU/HDF5. ModalNewmarkResult est explicitement versionné qf-modal-newmark-result/v1 et conserve la maturité expérimentale et qualification_decision=NOT_ASSESSED. Le schéma d’entrée src/solveur/io/schema.py n’accepte actuellement que la version 1. Ces contrats ne démontrent pas à eux seuls une matrice de compatibilité complète entre chaque nouvelle capacité, ses métadonnées, sa sérialisation et son comportement de refus.

Le choix E01-BC est cohérent : les deux modules Hencky sont importables directement mais statiquement isolés des fabriques de matériaux, dispatchs d’éléments, API publique, assemblage global et Newton. Aucune classe de résultat ou route sérialisée Hencky n’est exposée; ce n’est pas un défaut d’API pour le périmètre approuvé, puisque ce périmètre ne comprend pas de solveur global Hencky.

Deux pages publiques (docs/reference/qf_solver_api.md, docs/reference/api_stability.md) s’identifient encore comme applicables à 0.2.11, alors que le checkout audité est le candidat 0.2.12 avec trois exports D02 provisoires. Les tests vérifient la liste et les catégories des exports mais ne vérifient pas que l’en-tête versionné de ces documents correspond à 0.2.12. C’est une action documentaire P2 à planifier avant toute présentation de contrat 0.2.12; aucune mise à jour n’est faite dans cet audit.

## D02, E01 et provenance

### D02

La closure D02 documente CLOSED_BOUNDED pour la récupération de contraintes dynamiques solides sur fixtures déclarées. Le résumé intégré mentionne six batches, 53 nœuds uniques tous passés, et un lot API/sérialisation de 15 nœuds. Il précise que le résumé est une dérivée assainie, pas le reçu original, et conserve les clés/digests des preuves originales. Les limites restent : matériaux linéaires isotropes, solides TET4/TET10/HEX8/HEX20, pas de contact ni BEAM2, pas de revendication de conversion générale d’unités ou de convergence globale.

La roadmap propriétaire fournie est un snapshot daté du 18/10 qui montre encore D02 OPEN; le rapport de fermeture ultérieur et l’intégration sont postérieurs. Ce n’est pas une raison de réécrire l’historique; l’overlay actuel devrait néanmoins rendre l’état temporel explicite.

### E01

La preuve PRODUCTION_ARMIJO_GF4_SLAVE_BOUNDED=VERIFIED_BOUNDED est limitée au scénario GF4 TET4 et au sous-système esclave, au HEAD source 524c15a0355a3033d92f7a723b27e1ca5752d3bd, tree 9d0820780d1499a8488d295c740f8debd767eeee et à l’image exacte enregistrée dans le rapport BA. Elle n’est pas un RUN du HEAD d’intégration courant. Le verdict brut global BA reste FAIL; l’équilibre maître/montage demeure NOT_VERIFIED.

Les conditions permanentes de l’Owner BC restent : WP_E01=OPEN_WITH_BOUNDED_CERTIFICATES, tangente globale J2 non résolue, GENERAL_SCIENTIFIC_QUALIFICATION=NOT_ACQUIRED. Ni la clôture WP-E01 ni le certificat global n’est inféré.

## C02, D01 et E01 encore hors de la branche commune

Les branches examinées et leurs identités propres sont :

| Package | Branche / HEAD / tree | Écart de l’arbre comparé à l’intégration |
|---|---|---|
| C02 | codex/wp-c02-ar-spatial-convergence-20261023, cd02eef59d3345643d617035be96190811d370bb, 4d24fbebcc4c08f63d17f41c693394a01d040bd5 | 49 chemins src/solveur, 53 tests, 5 docs, 648 qualification différents |
| D01 | codex/wp-d01-bc-remediation-20261023, 27ab0f61d9f1deedaac6ed821de447f8539753a5, 4f1211ae520b78f89a3e0f1c1daeaa06228c554a | 95 chemins src/solveur, 126 tests, 81 docs, 1 722 qualification différents |
| E01 | emptiesvoids-cloud/wp-e01-ba-slave-bounded, 3dc2f423e82ddb12fd82b8f23e764e757bad8278, 212130de39ff9c59aa93ce652b67e8b2e1ce86c7 | 90 chemins src/solveur, 132 tests, 81 docs, 1 719 qualification différents |

C02 reste principalement une voie contact/friction/GF2–GF5. D01 apporte des chemins de dynamique/réduction/flexibilité résiduelle, checkpoints/contrôleur et leurs tests/supervision. E01 porte une grande branche expérimentale avec contact, Newton et global assembly; seule la sélection BC, les deux kernels Hencky, leurs tests et les archives/documentations prévues ont été intégrés. Les différences de contenu sur les chemins API/contact partagés sont un risque de réconciliation, pas une instruction d’import en bloc.

L’inventaire exact produit par git diff --name-status codex/v0.2.12-integration <branch> est fourni dans le TSV joint. Il comprend des changements, ajouts et suppressions entre les arbres, pas uniquement du nouveau code.

## Vérifications exécutées pour cet audit

Commande non qualifiante, un seul processus, BLAS/OpenMP limités à un thread :

python -m pytest -q tests/unit/test_public_api_contract.py tests/unit/test_result_serialization_contracts.py tests/unit/test_wp11_j2_closure.py tests/unit/test_wp11_multifamily.py -k 'not minimal_documented_workflow and not test_wp11_multifamily_build_and_solve_is_finite'

Résultat : **21 passed, 5 deselected, 7.97 s**.

Les 5 cas exclus sont le workflow documenté qui appelle solve_model et les quatre paramètres du test multifamille qui assemblent et résolvent le système. Les cas retenus contrôlent inventaire/signatures/stabilité de l’API, forwards D02 mockés, sérialiseurs vectoriels, catalogue/historique J2 et contrats géométriques multifamille. Le hook tests/conftest.py tente une simple détection de disponibilité Gmsh par import lors de la collection; aucun test Gmsh, solveur natif ou solve FEM n’a été sélectionné ni lancé.

Les tests numériques D02 et E01 ne sont pas répétés dans WP11-A. Les preuves historiques ciblées déjà inscrites dans les rapports de clôture sont citées avec leur portée. Les tests non exécutés ici ne sont pas présentés comme passés.

Aucun seuil ni aucune équation n’a été modifié. Avant création de ce rapport et des inventaires, le worktree était propre. Ces seuls fichiers d’audit sont les changements autorisés; aucun code de production n’a été modifié.

## Findings indépendants

Revue indépendante, lecture seule, sans exécution de test ni édition :

- Aucun P0 trouvé.
- Aucun P1 dans l’intégration Hencky BC sélectionnée.
- P1 de statut global : le gate WP11 reste ouvert jusqu’à démonstration d’une matrice d’intégration et de contrats de sortie applicable au scope retenu; D01 reste également ouvert et précède WP11 dans la séquence Owner.
- P2 documentaire : les deux pages API se déclarent encore 0.2.11; le tableau owner fourni montre D02 OPEN car il est daté du 18/10, malgré la closure bornée ultérieure. Clarifier les versions/instantanés dans le travail documentaire.
- Les tests legacy test_wp11_j2_closure.py et test_wp11_multifamily.py ne constituent pas à eux seuls la fermeture opérationnelle WP11 : le premier pointe vers des preuves WP11 anciennes, le second inclut un solve linéaire isolé que cet audit a volontairement désélectionné.

La revue ne recommande pas de modifier la portée BC ni de réconcilier automatiquement les branches C02/D01/E01.

## Gates satisfaits et ouverts

**Démontrés dans ce checkout ou par les preuves exactes archivées :**

- Identité du HEAD et du tree d’intégration conformes à la baseline, origin attendu, worktree initial propre.
- Contrats d’exports/signatures API présents et 21 tests non qualifiants ciblés passés.
- Résultats/sérialisation existants et versionnement explicite de certains DTO expérimentaux.
- D02 intégré et CLOSED_BOUNDED à la portée écrite.
- E01-BC intégré à sa portée limitée, OPEN_WITH_BOUNDED_CERTIFICATES.
- Aucune dépendance de l’API publique ou du solveur global vers les kernels Hencky expérimentaux.
- Préservation des verdicts et limites négatifs historiques dans les rapports.

**Non démontrés / restant ouverts :**

- « Gate d’intégration complet » WP11 : pas de matrice consolidée approuvée reliant chaque capacité retenue, API, résultat, schéma/métadonnées, erreurs/refus, compatibilité et test sur le candidat commun.
- Actualisation/versionnement des deux pages API pour le candidat 0.2.12.
- Clarification de l’état D02 dans le statut courant sans réécrire le snapshot historique.
- Décision/documentation de l’inventaire de contrats de résultats réellement requis au-delà des tests ciblés.
- D01 OPEN dans la séquence propriétaire; l’Owner doit confirmer s’il est une dépendance dure pour le scope WP11 ou si son périmètre est explicitement reporté. Aucune dépendance de code directe n’a été démontrée par cet audit.
- WP12 et WP13 restent distincts et ouverts; l’audit ne conclut pas leur clôture.

## Actions nécessaires et proposition de clôture

1. WP11 dresse et fait approuver une matrice limitée au scope effectivement intégré (core WP00–WP10 retenu, D02 borné, E01-BC expérimental), sans importer les branches C02/D01/E01.
2. Pour chaque contrat de cette matrice, pointer vers API, type résultat/DTO, format et version de sérialisation, métadonnées de maturité/provenance, refus hors scope, tests associés et hash/provenance d’évidence.
3. Corriger ou explicitement marquer les pages API 0.2.11 comme historiques et publier le contrat applicable au candidat 0.2.12; clarifier D02 comme état postérieur au snapshot du 18/10.
4. Rejouer uniquement les tests de contrat/compatibilité non qualifiants nécessaires sur le candidat commun après toute modification documentaire ou d’API. Toute nouvelle V&V numérique demeure gouvernée par ses propres autorisations.
5. Faire confirmer par le propriétaire WP11 que le gate complet est satisfait et documenter le lien de séquencement avec D01 avant de déclarer WP11 CLOSED.
6. Proposition de séquencement, et non nouveau gate : WP12 peut préparer sa campagne lorsque les contrats d’interface et résultats qu’elle consommera sont identifiés et gelés. L’audit n’identifie pas un blocage de code direct autre que l’absence de cette base de contrat consolidée; D01 n’est un blocage WP12 que si son comportement fait partie du scope WP12 approuvé. Toute modification de l’ordre Owner doit être décidée par l’Owner.

**Décision proposée : WP11=OPEN.** La branche est consolidée pour les sélections D02 et E01-BC documentées, mais la preuve disponible ne satisfait pas encore le gate complet WP11 de l’Owner. WP12=OPEN, WP13=OPEN; WP_E01=OPEN_WITH_BOUNDED_CERTIFICATES; MASTER_ASSEMBLY_EQUILIBRIUM=NOT_VERIFIED; GENERAL_SCIENTIFIC_QUALIFICATION=NOT_ACQUIRED.

Aucun merge vers main, tag, publication ou nouveau RUN FEM qualifiant n’a été effectué.
