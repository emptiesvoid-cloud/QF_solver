---
doc_id: DOC-VV-003
revision: 0.1
status: draft controle
applicable_version: 0.2.5a0
reviewer: ""
approver: ""
---

# Tracabilite et dossier de preuve

Le registre `qualification/requirements.json` relie chaque exigence a la
conception, au code, aux tests, aux references et aux artefacts. Une exigence
orpheline rend le scope non pret.

Pour la release candidate `0.2.5a0`, les preuves numeriques qualifiees restent
liees au `QUALIFIED_SOURCE_SHA` indique dans le pack de release. Les commits
documentaires ulterieurs sont distingues des sources numeriques qualifiees et
ne constituent pas une nouvelle execution de calcul.

## Dossier standard

Un dossier `evidence` contient l'entree, les resultats, l'audit, le rapport de
maillage, les parametres solveur, le resume de qualification, les exports et
un manifeste SHA-256.

Le manifeste v2 ajoute revision source, etat du depot, versions verrouillees,
plateforme, BLAS, commande et couverture d'exigences. Le lecteur conserve la
compatibilite avec le format v1.

## Preuve documentaire

Le build du site applique le meme principe. Chaque figure et tableau possede
une entree dans `docs/generated/docs_manifest.json` avec:

- modele et SHA-256;
- analyse, methode et profil;
- version du solveur et revision Git;
- fichier resultat source;
- verdict et reference utilisee;
- empreinte du fichier publie.

Une modification manuelle d'une figure ou d'un tableau doit donc etre
detectee au prochain controle.

La [revue documentaire et tracabilite des formules](formules.md) publie en
plus la couverture formule par formule et distingue le verdict automatique
des signatures `owner_review` encore attendues.
