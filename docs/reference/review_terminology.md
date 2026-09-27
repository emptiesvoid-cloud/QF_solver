---
doc_id: DOC-GOV-REV-TERMS-001
revision: 0.3
status: controlled
applicable_version: 0.2.1a0
reviewer: ""
approver: ""
---

# Terminologie De Revue Et D'Audit

## Objet

Cette politique fixe les termes utilises dans les documents, rapports,
manifestes et interfaces de QF_solver. Une verification reproductible ne vaut
pas une decision de maturite : la responsabilite de chaque conclusion doit
rester explicite.

## Termes Controles

| Terme | Responsabilite | Preuve minimale | Effet sur la maturite |
| --- | --- | --- | --- |
| `automated_verification` | Test, calcul ou campagne reproductible | commande, entree, environnement, resultat et verdict | aucun, sans decision explicite |
| `analyzer_report` / rapport analyseur | Representation des controles par l'analyseur | source, entrees, metriques et verdicts traces | aucun ; les donnees brutes restent prioritaires |
| `owner_analysis` / analyse Owner | Analyse preparatoire des preuves pour le proprietaire | perimetre, donnees, ecarts et limites | aucun ; ce n'est pas une acceptation |
| `owner_review` | Proprietaire du projet | identite, date, scope, decision et commentaires | peut accepter un domaine interne borne |
| `external_audit` | Relecteur ou organisme independant | auteur, independance, version, perimetre et artefacts | peut completer une evidence, sans certification implicite |

`self_review` est un mode de `owner_review` : l'auteur et le proprietaire de
la decision sont la meme personne. Il doit rester declare comme non
independant. `independent_review` designe une revue par une personne distincte
et tracee.

## Schema V&V

Les nouveaux rapports V&V emploient la cle `owner_decision` et le schema de
sortie `2`. Les entrees d'etude conservent `validation.decision`, car ce champ
porte la decision de l'owner de maniere explicite dans son contexte.

Une decision `pending` conserve le statut `PENDING_REVIEW` meme si tous les
controles automatiques sont `PASS`. Une decision `accepted` ne masque jamais
un verdict automatique `FAIL`.

## Archives

Les resultats numeriques, les decisions et les liaisons d'execution des archives
restent traces. Les copies courantes appliquent egalement la terminologie
analyseur apres migration explicite. Les hashes originaux ne sont pas
remplaces retroactivement par ceux des copies migrees. Tout rapport nouveau
identifie clairement les artefacts d'archive qu'il reference.

La migration de terminologie autorisee applique aussi les nouveaux libelles
aux copies courantes des archives. Aucune archive ne beneficie d'une dispense
lexicale. Les versions originales restent identifiables par leurs objets Git
et leurs hashes, sans reecriture de l'histoire Git. Pour WP06-F, le rapport
devient un rapport analyseur, avec le token `ANALYZER_REPORT`, sans changer son
rang d'autorite, les seuils, les resultats ou la decision de preparation.
`scripts/verify_review_terminology_migration.py` verifie exactement les deux
transformations autorisees et leurs hashes avant/apres. Cette migration ne
vaut ni qualification supplementaire ni nouvelle execution.

## Controle

Le test `tests/unit/test_review_vocabulary.py` interdit le vocabulaire
generique des anciennes revues dans les sources maintenues, les archives et
les documents generes presents dans l'inventaire Git. Aucun contrat historique
ne beneficie d'une exception lexicale. Les fichiers binaires et les objets
Git originaux ne sont pas reecrits par ce controle.
