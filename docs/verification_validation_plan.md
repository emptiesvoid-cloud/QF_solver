---
doc_id: DOC-VV-006
revision: 1.1
status: draft
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Plan de verification et validation

## Verification logicielle

- tests unitaires et de proprietes;
- tests d'integration API, CLI et formats;
- tests negatifs et injection de fautes;
- couverture de lignes et de branches;
- analyse statique, typage progressif et architecture;
- reproductibilite Windows/Linux et versions Python supportees.

## Verification mecanique

- patch tests et modes rigides;
- symetrie, positivite, residus et identites energetiques;
- solutions analytiques et manufacturees;
- convergence en maillage et en pas de temps;
- sensibilite aux distorsions, tolerances et conditionnement;
- comparaison noyau de reference / noyau haute performance.

## Validation

Une fonction ne devient pas qualifiable uniquement parce que son code est
teste. Son domaine d'emploi doit aussi etre correle a des donnees physiques ou
a une reference independante adaptee, avec incertitudes documentees.

## Procedure interne Code_Aster Docker

Code_Aster est l'oracle externe reproductible privilegie lorsque la
formulation permet une comparaison explicite. Toute campagne utilise l'image
Docker epinglee declaree dans
`qualification/external_oracle_policy.json`; un tag mutable, une installation
hote non versionnee ou une valeur recopiee manuellement ne constituent pas une
preuve.

1. Verifier le moteur avant calcul avec `docker version` et controler que la
   version serveur est disponible. Un moteur absent, arrete ou une image non
   accessible est une indisponibilite d'infrastructure : aucun resultat ne
   peut etre publie comme correlation externe.
2. Generer les decks `.mail` et `.comm` depuis le code versionne.
3. Executer l'image epinglee et conserver les logs `stdout` et `stderr`.
4. Normaliser les observables dans `summary.json`, puis generer le rapport
   Markdown, les figures et le manifeste SHA-256.
5. Declarer toute difference de formulation ou de maillage dans le rapport;
   elle interdit de presenter la correlation comme une equivalence complete.
6. Pour le contact, declarer separement l'application normale et tangentielle,
   l'etat compare (`open`, `stick` ou `slip`) et les penalites. Une branche
   `stick` est recevable seulement si la compliance tangentielle equivalente
   est etablie; elle ne valide pas une regularisation differente par simple
   comparaison de deplacement.
7. Laisser l'execution Docker hors CI standard. Elle est lancee avec
   `QF_SOLVER_RUN_EXTERNAL=1` ou par son script V&V dedie afin que la CI ne
   telecharge jamais silencieusement un oracle de plusieurs gigaoctets.

La commande de campagne est, lorsque Docker Desktop est demarre :

```powershell
$env:QF_SOLVER_RUN_EXTERNAL = "1"
python -m pytest tests/verification/test_code_aster_friction_contact_vnv.py -q
python -m pytest tests/verification/test_code_aster_contact_tet4_vnv.py -q
```

Les scripts `scripts/run_code_aster_friction_contact_vnv.py --output <dossier>`
et `scripts/run_code_aster_contact_tet4_vnv.py --output <dossier>` publient les
preuves internes et le digest public controle. Un echec de connexion Docker
doit etre consigne comme `InfrastructureError` et ne doit pas etre transforme
en echec mecanique ou en preuve negative.

La campagne `VNV-CONTACT-CODEASTER-LIAISON-UNIL-001` applique cette procedure
a la loi normale unilaterale du contact V1.
`VNV-CONTACT-CODEASTER-TET4-MASTER-004` y ajoute le transfert sur une face
maitre TET4 : son etat ferme est impose par `LIAISON_DDL`, tandis que
`LIAISON_UNIL` conserve la preuve distincte de l'active-set. Les deux preuves
doivent rester separees dans tout rapport de validation.

## Owner review et independence

Chaque etude declare l'auteur, le validateur, la decision, la date et la nature
de la revue. Lorsque Quentin Farinazzo tient les deux roles, le mode impose est
`self_review` et la preuve indique explicitement `not_independent`. Cette
auto-revue formalise la decision engineering interne et reste recevable tant
qu'aucune independence n'est revendiquee.

Une revue independante par une personne differente demeure necessaire avant
toute revendication de qualification externe ou lorsqu'un niveau d'assurance
l'impose. Les resultats et decisions sont conserves dans le dossier de preuve
de release. Le contrat d'etude, les sorties normalisees et le rapport Markdown
sont decrits dans [Etudes V&V comparees](verification/etudes_vnv.md).
