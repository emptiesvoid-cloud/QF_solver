---
doc_id: DOC-GOV-REV-TERMS-001
revision: 0.1
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

Les archives de preuve sous `qualification/evidence/` sont immuables : elles
peuvent conserver un vocabulaire historique. Elles ne doivent pas etre citees
comme un contrat de terminologie courant. Tout rapport nouveau applique cette
politique et identifie clairement les artefacts d'archive qu'il reference.

## Controle

Le test `tests/unit/test_review_vocabulary.py` interdit le vocabulaire
generique des anciennes revues dans les sources publiees et maintenues. Les
archives immuables et les produits generes sont exclus de ce controle, car ils
font l'objet d'un audit de publication distinct.
