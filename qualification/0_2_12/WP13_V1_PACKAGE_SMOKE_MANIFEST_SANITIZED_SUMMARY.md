# Manifeste smoke v1 — note d’archive expurgée

**Statut :** `SANITIZED_DERIVATIVE_NON_EXECUTABLE_SUMMARY`
**Source examinée :** PR #114, commit `a4fe5cea5edaf31dbfa13e1e9e1295a45b2fbf8a`, Git blob `389c0f54c69a04586f0714b08f2dbe6c3f9906f9`.
**SHA-256 des octets originaux :** `dea2c6f6d72bbd7303f23b6cff6b9809be471513dffa639990d13313dee9086b`. Le sidecar présent dans la PR source correspond à ces octets. Ces identités ne décrivent que l’objet original; la note présente n’est pas le manifeste original et ne peut pas être passée au contrôleur.

## Motif et portée

Le manifeste original v1 est exclu de l’arbre squash proposé avec son sidecar, car il contient 11 chemins absolus liés aux environnements, archives et preuves d’une exécution antérieure. Aucun de ces chemins n’est reproduit ici. Les octets originaux restent dans la PR source publique; ils n’ont pas été modifiés. Cette note ne remplace pas les preuves brutes ou le ledger externe.

Le manifeste est un artefact de préparation v6 (`QF-0212-WP13-SELECTED-CANDIDATE-20261031-06`), lié à la source package `2865587a44f9e461a0b4e4286c912c17e4f04be5` et au contrat `f33a72b182439774828f8e604d6ab234bbf206c697c0f1082d7bc0ef81003db9`. Il identifie des artefacts antérieurs au candidat v7; leurs hashes ne sont pas ceux du wheel et de la sdist v7.

## Identités historiques conservées

| Artefact v6 | SHA-256 original |
|---|---|
| wheel | `ae5211136a2eab912cdb73222937a84b1cec75f7af0a425f1162b288b39c287a` |
| sdist | `15c838af12c8401b61c561f5f079debc702e072241e9ee8c17cd5861cbf082e5` |

| Cas v6 | Entrée | SHA-256 entrée |
|---|---|---|
| STATIC-01 | `tet4_static.json` | `5296102b955ae4ac83b341178a8a555feb87faa0e9a30abe9f77c29df21988b8` |
| MODAL-01 | `tet4_modal_unit.json` | `0d40df125888b467017d053795336cb8960f643c95a209c3c96379a50c689750` |
| DYNAMIC-01 | `tet4_dynamic_sdof_free_vibration.json` | `b40d7188143e4bcc73ee63407f426633490921075990bcad47bd25c9a188480b` |

Les trois entrées sont les mêmes entrées référencées par le dossier smoke v7; les artefacts v6 ci-dessus ne sont pas réutilisés dans les résultats v7. Le dossier et le rapport d’exécution v7 restent les références actuelles pour les six tentatives `EXECUTION_PASS` / `NUMERICAL_ORACLE_PASS`.

## Contrôles historiques

Le premier préflight v1 s’est arrêté `CONTROLLER_PREFLIGHT_FAIL_CLOSED` avant les sondes de package, toute réservation et tout FEM. Le rapport de cette tentative a enregistré une erreur de répertoire invalide et une commande initiale dont le digest attendu différait du digest sidecar. Après correction du contrôleur, le préflight sans FEM et le préflight synthétique ont passé avec le manifeste original et son SHA-256 `dea2c6f6d72bbd7303f23b6cff6b9809be471513dffa639990d13313dee9086b`. Le dossier historique indique zéro réservation réelle et zéro FEM sous cette décision v6.

Le contrôleur actif exige le contrat et la source v7 et rejette une identité de source v6. La présente note n’est ni un manifeste v1 valide, ni une approbation, ni une autorisation d’exécution. Le manifeste v7 reste externe et son identité figure dans le dossier Owner final WP13.
