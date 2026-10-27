# WP12 — Index de consolidation documentaire

Date : 2026-10-26
Branche de revue : `emptiesvoids-cloud/wp12-dynamics-selective-integration`
Base : `emptiesvoids-cloud/0.2.12` à `98456355f0a85dff9edf7f37d53c7c6fff59bf37`

Cette page rassemble les rapports committés absents de la base et indique où la roadmap fournit déjà une synthèse. Les statuts ci-dessous restent ceux des campagnes et rapports d’origine. Ils ne sont pas des résultats nouvellement acquis sur la branche de consolidation et ne constituent pas une qualification formelle.

## Rapports ajoutés sans modifier leur conclusion

| Domaine | Source | Document repris | Statut et limite conservés |
|---|---|---|---|
| WP12-C, physique avancée et contact | `audit/wp12-advanced-physics` — `71461362e1a6f720aac6a9f854d67048f4d469b7` | [Audit avancé](../wp12_c_advanced_physics_audit.md) | C01 `CLOSED_NEGATIVE`, remédiation ouverte; C02 `CLOSED_BOUNDED` seulement pour AR/N03; E01 `OPEN_WITH_BOUNDED_CERTIFICATES`, avec échecs Newton et résultats globaux négatifs conservés; D01 `INCONCLUSIVE`. Audit documentaire, sans exécution FEM. |
| WP12-A, non-régression transversale | `verify/wp12-legacy-cross-route` — `e59298e2deef9df5dc612b7962ce12d823080217` | [Rapport](wp12_legacy_cross_route/LEGACY_CROSS_ROUTE_REPORT.md) et [matrice 20 lignes](wp12_legacy_cross_route/COVERAGE_MATRIX.tsv) | G03 et l’échec historique MITC4 restent `FAIL_PRESERVED`; WP-D01 reste `INCONCLUSIVE`; PASS de branches indépendantes ne valent pas PASS du candidat ni qualification formelle. La divergence des trois nodeids dynamiques est résolue ici par leur retour exact dans les modules de test, sans changement de politique. |
| WP12-B, éléments et chargements | `verify/wp12-elements-loads` — `06c147a98b4e70e7b5fe365f2e48eb16a3a9fd6f` | [Audit éléments et chargements](../../../docs/verification/wp12_b_elements_loads_audit.md) | Verdict `FAIL` du panneau composite déformé et avertissement de corrélation MITC3–CalculiX conservés. L’audit est surtout une revue de couverture et une proposition de sentinelles; aucun lancement FEM nouveau n’est impliqué. |
| WP12 TET4 | `experiment/wp12-tet4-convergence` — `9c48bd5559b898db3bb76bef05b9566302c613c8` | [Synthèse TET4](../../../experiments/wp12_tet4_convergence/report_consolide.md) | Six tentatives historiques `PASS` sur leurs fixtures, jusqu’à 9 963 DDL; résultat `PASS_BOUNDED` de développement uniquement. L’ordre asymptotique et la précision physique 3D restent non établis; aucun calcul F16 n’a été lancé. |
| WP12 dynamique | `codex/wp12-dynamic-harmonic-verification` — rapport au commit `630d22b7667a0d84dd7b136b9f8c7d89ae00fc66`; sources de tests au commit scientifique `d9deddbd6b42467c5fdc9e278bd54e97605f5738` | [Rapport dynamique](wp12_dynamics/DYNAMIC_HARMONIC_RESULTS_REPORT.md) | Sous-campagne `CLOSED_BOUNDED`; trois cas `DEVELOPMENT_PASS_BOUNDED`. Les limites Newmark SDOF, harmonique tronqué sans borne générale et excitation de base monoaxe demeurent explicites. La fermeture de sous-campagne n’est pas une qualification formelle. |

## Branches dont aucun rapport d’audit final n’est repris

| Branche | État des documents committés au HEAD examiné | Traitement |
|---|---|---|
| `verify/wp12-rotor-performance` — `4adc0c220369b7b8f257f604ca2bb9e89d12c1c3` | Le document WP12 distinct trouvé dans le diff est un plan de performance; aucun rapport final d’audit de résultats n’est committé. La roadmap courante maintient D01 `INCONCLUSIVE`. | Le plan n’est pas présenté comme un audit achevé ni comme une exécution. Les mesures et limites héritées de la rotordynamique restent dans la roadmap et les rapports de release concernés. |
| `test/wp12-fem-regressions` — `fa889f480766506787941617fa0db4124381c63b` | Les documents WP12 ajoutés sont un plan HEX8-SRI et une matrice de travail; aucun rapport final de clôture de la sous-campagne n’est committé dans cette branche. | Aucun brouillon n’est importé comme conclusion. La classification `CLOSED_NEGATIVE` des deux diagnostics HEX8-SRI et leurs `PYTEST_FAILED` historiques restent ceux déjà rapportés dans la roadmap; seuils et preuves demeurent inchangés. |

## WP12-B — lot d’éléments préparé, non autorisé

Le lot transmis au commit `8818b1b4095bd7f5c1303d640375c2c577bdc4d8` sur `verify/wp12-elements-loads` est consigné `PREPARED_NOT_AUTHORIZED` en attente d’une inscription conforme. Il comprend les cas proposés ci-dessous; budgets proposés : une tentative par cas, 300 s par tentative, RSS observée plafonnée à 4 096 MiB, trois tentatives au total.

| Nodeid exact | DDL | État |
|---|---:|---|
| `tests/unit/test_wp12b_beam2_continuity.py::test_wp12b_beam2_rotated_uniform_line_load` | 12 | `PREPARED_NOT_AUTHORIZED` |
| `tests/unit/test_wp12b_tet10_curved_load.py::test_wp12b_tet10_curved_face_pressure_solve` | 30 | `PREPARED_NOT_AUTHORIZED` |
| `tests/unit/test_wp12b_hex20_affine_patch.py::test_wp12b_hex20_uniaxial_traction_patch` | 60 | `PREPARED_NOT_AUTHORIZED` |

Le worktree observé `C:\Users\fari\.codex\worktrees\verify-wp12-elements-loads\qf_solver` et sa branche `verify/wp12-elements-loads` ne correspondent pas au scope historique enregistré `E:\QFSolverAgents\vv-elements` / `test/wp12-fem-regressions`. Le lot ne leur est donc pas rattaché et aucune autorisation existante n’est réutilisée. L’agent de configuration doit enregistrer l’identité scientifique réelle dans le contrôleur canonique avant de préparer de nouveaux manifestes et solliciter les décisions Owner. Aucun nodeid n’est inscrit ici; aucun manifeste ni calcul FEM n’a été créé ou lancé.

## Statuts à garder distincts

- `FAIL` et `CLOSED_NEGATIVE` restent des résultats négatifs; cette intégration documentaire ne les promeut pas.
- `INCONCLUSIVE` demeure inconclusif, notamment pour WP-D01 et la précision physique/convergence TET4.
- `PASS_BOUNDED` ou `DEVELOPMENT_PASS_BOUNDED` décrivent seulement les cas, versions, fixtures et oracles documentés.
- `NOT_RUN` sur le candidat reste `NOT_RUN`; les résultats d’une branche scientifique indépendante ne le remplacent pas.
- Aucun résultat de cette page n’est une qualification formelle ou une validation physique générale.

La [roadmap v0.2.12](../ROADMAP.md) conserve la synthèse de portefeuille déjà intégrée. Cette page n’en recopie pas les tableaux de capacités et ajoute les rapports détaillés manquants avec leur identité source. Aucune politique, aucun runner, aucun fichier solveur, seuil ou archive historique n’est modifié.
