# WP12-V — Audit scientifique du FAIL U3

**Date :** 2026-10-26. **Mode :** audit du code et des preuves en lecture seule; nouveaux documents seulement.
**WP11 :** CLOSED. **WP12 :** OPEN. **WP13 :** OPEN.

Ce dossier examine le résultat conservé FAIL de TET4-ROUTE-CROSSCHECK-001. Il distingue le critère qui a échoué, le mécanisme possible de production de l'écart, l'accord numérique du système discret et les questions de précision mécanique encore ouvertes. Aucun pytest, solveur, kernel élémentaire, nouvel assemblage ou benchmark QF Solver n'a été lancé pendant WP12-V. Les recalculs sont des post-traitements des matrices, vecteurs et fractions déjà archivés.

## Lecture

| Document | Objet |
|---|---|
| [SCIENTIFIC_AUDIT_SUMMARY.md](SCIENTIFIC_AUDIT_SUMMARY.md) | Verdict A–E et limites causales |
| [U3_FAILURE_ROOT_CAUSE.md](U3_FAILURE_ROOT_CAUSE.md) | Assertion, paire, contributions et chemin source |
| [MATRIX_SYMMETRY_FLOATING_POINT_AUDIT.md](MATRIX_SYMMETRY_FLOATING_POINT_AUDIT.md) | Symétries locales/globales, SciPy et réduction |
| [MATRIX_FREE_DIRECT_EVIDENCE_REVIEW.md](MATRIX_FREE_DIRECT_EVIDENCE_REVIEW.md) | Métriques recalculées, résidus, réactions, énergies et portée |
| [NUMERICAL_CRITERION_PROPOSAL.md](NUMERICAL_CRITERION_PROPOSAL.md) | Borne prospective d'arrondi et comparaison des corrections |
| [PROSPECTIVE_V2_TEST_PLAN.md](PROSPECTIVE_V2_TEST_PLAN.md) | Une expérience minimale proposée, non autorisée |

Les règles applicables restent [AGENTS.md](../../../../AGENTS.md), la politique [QUALIFICATION_LOCAL_VV](../LOCAL_VV_POLICY.md) et la [roadmap](../../ROADMAP.md). Le contexte antérieur est le [rapport WP12-T](../wp12_t_audit/SCIENTIFIC_AUDIT_SUMMARY.md).

## Identités vérifiées

Le checkout d'intégration était sur emptiesvoids-cloud/0.2.12, HEAD `7990c45026450be1c2d184571317c15138adcd3a`, tree `1148a4b12743e1c50c9570743a288d457bf7baa2`. Le HEAD distant obtenu par git ls-remote correspondait à ce commit avant intervention. Les documents d'audit forment une identité documentaire ultérieure; ils ne remplacent aucune identité scientifique.

| Rôle | Commit | Tree | État lors de l'audit |
|---|---|---|---|
| Science | `00428adf38e9397340ac136f6f503a268eb671da` | `df4ec667bf746b042c900fad1f86bf542e1a437b` | CLEAN |
| Runner local | `0bd8ebb5a886ac89a8216e65ff37d59fb510fb61` | `e31931fefb7012171e7e1a9f03511cd1c9987eda` | CLEAN |
| Tests U | `9c7df65403fc15dc6d12365534172eac87f2ee70` | `c936f1c843e571396add05bba75a3f808c2d7dc3` | CLEAN |

Les 36 fichiers uniques des inventaires U ont été vérifiés par SHA-256 des octets locaux et OID du blob au commit déclaré. Les 15 sorties référencées par les trois reçus ont été rehashées; aucun écart n'a été trouvé. Les reçus eux-mêmes correspondent à leurs fichiers receipt.sha256.json. Ceci vérifie la cohérence locale présente; ce n'est ni une signature d'auteur ni une preuve d'immuabilité externe.

## Preuves primaires

Racine externe : `E:\QFSolverWP12B\wp12-local-vv-evidence\WP12-U-TARGETED-001`.

| Cas | Run ID | Statut conservé | SHA-256 receipt.json |
|---|---|---|---|
| U1 | 20261026T120140Z-49ca8fb4ee0d | PYTEST_PASS_ONLY | `409d8caf79621b9a94792080f49ad784523c3e5087d22018b1934ca25b6d729f` |
| U2 | 20261026T120231Z-ba477b0a779b | PYTEST_PASS_ONLY | `c5be56b7af3496ec6c34017bea42e452e5f1f44e2c984f48948bc0dc6aea2475` |
| U3 | 20261026T120509Z-3a69e91f9b42 | FAIL | `c47a566d97998746a58823ce3f88b5f4950b7cf597bf62129f72aa54c3956542` |

Chaque chemin est construit comme racine/case_id/run_id. Le manifeste analysé est lié au SHA-256 `3f10c7156c6f4e5eaf07f0bf66a92fe3f7cc6ef9031c200c1e41ca1087bf2a1c`. Les décisions locales distinctes restent des enregistrements non cryptographiques de la décision Owner. Elles n'autorisent aucun calcul WP12-V.

## Documents WP12-U locaux et non suivis

Au début de l'audit, le seul état Git non propre était le dossier non suivi qualification/0_2_12/vv_local/wp12_u/. Il a été préservé et exclu du commit WP12-V. Il ne faut pas supposer que ces fichiers sont récupérables depuis la branche GitHub. Les citations de ces chemins désignent les octets locaux identifiés ici.

| Document local sous wp12_u/ | SHA-256 |
|---|---|
| WP12_U_MANIFEST.json | `3f10c7156c6f4e5eaf07f0bf66a92fe3f7cc6ef9031c200c1e41ca1087bf2a1c` |
| WP12_U_EXECUTION_REPORT.md | `9258d9d25757480e8842892f4ae27b297ca23bb31b183119f77ee4fd5c1f729c` |
| OWNER_EXECUTION_DECISION.md | `2870cacb07ac88a17b55df14ba685991e0710bd2e1ea7b400a9a499e182b0eaf` |
| TET4_ROUTE_CROSSCHECK_REPORT.md | `3e2a53af9e85c2d5d5c452febe7e8d7d330738e86f492a35e0f435f13f8da8a3` |
| TET4_AFFINE_ORACLE_REPORT.md | `4cb39b5d23db82b2ade803f2947bd45629bf42b6d3b4aa519b5b86cfdea464cb` |
| SCIENTIFIC_RESULTS_SUMMARY.md | `97fad8a2c68ce7940f53859cc21aba97b54480ce19e7a9f81fcd5191a1940e41` |
| WP12_U_CAMPAIGN_PLAN.md | `6e7a7994cddb8acda5151b84e672893995d32b1bf327dcd214952a0e717d8cfe` |
| README.md | `a0233d9e5aa0d932d85115be46f492ba5ad252775745018016cf8a539ae3182e` |
| NEXT_EXPERIMENT_DECISION.md | `f5a1033f38182e2387046f89acce593eed3e16a82b9b4a6b95f95d4c813f966e` |
| MODAL_CRITERION_VERIFICATION.md | `88b83cac5c5fc22b6c77090879558d57507249a73fa1a5f91f833eb1736c9874` |

Les pages préparatoires U portent encore NOT_RUN ou NUMERICAL_EXECUTION_NOT_PERFORMED. Ce sont des snapshots pré-exécution; les reçus primaires et WP12_U_EXECUTION_REPORT.md sont les références pour les résultats ultérieurs. Cette différence temporelle est explicitée ici, sans réécriture des fichiers U. La disponibilité de ces données externes est nécessaire pour reproduire intégralement les post-traitements; le seul clone des sept rapports V ne contient pas les preuves primaires.
