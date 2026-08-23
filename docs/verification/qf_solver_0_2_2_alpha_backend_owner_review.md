---
doc_id: DOC-OWNER-BACKEND-022-001
revision: 0.3
status: owner_accepted_with_recommendations
review_mode: owner_review
applicable_version: 0.2.2a0
promotion_target: bounded_backend_gate
scope: backend-scaling-vnv
date: 2026-08-23
owner_review: signed_by_owner
decision: accepted_with_recommendations
reviewer: "Owner"
approver: "Owner"
---

# Owner review - backend numerique et scaling 0.2.2a0

## Objet de la decision

Cette revue porte sur la fermeture du gate technique backend de la tranche
`0.2.2a0`. Elle ne demande pas de promouvoir les elements, les methodes ou le
package en `stable`. Elle vise a confirmer que la campagne backend est
suffisamment documentee pour rester utilisable dans un perimetre de
developpement borne, avec ses limites explicitement conservees.

La decision Owner doit rester separee de la decision de release, du tag Git et
de la publication PyPI.

## Identite et versioning

La base de code analysee et les manifestes de la campagne backend portent
`QF_solver 0.2.2a0`. L'image Docker `qf-solver-large:0.2.0` est le tag de
l'environnement d'execution epingle par digest ; ce tag n'est pas le numero de
version du package et ne doit pas etre lu comme une release `0.2.0` du solver.

| Identite | Valeur | Role |
| --- | --- | --- |
| Package | `QF_solver 0.2.2a0` | base de code et version applicable |
| Image d'execution | `qf-solver-large:0.2.0` | environnement Docker historique |
| Digest image | `sha256:f2a7931d0543ee142ce67847bb91bf59350a947d5d4874bfe7be43b6848a49c8` | identite immuable de l'environnement |
| Digest image de base | `sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8` | tracabilite de l'image |
| Revision des campagnes dynamiques | `f5061fe5260e42582dc5f3202ccf3f626cd00ded` | revision propre enregistree dans les manifestes |

Le dossier historique `results_large/qualification_matrix_free_1m` est exclu
de la preuve backend `0.2.2a0` : il correspond a un ancien calcul PETSc/GAMG
de `1 029 000` DDL en `0.2.1a0`, et non a une preuve matrix-free.

## Perimetre accepte pour la revue

Le perimetre est defini par des tailles, des chemins numeriques, une
configuration d'execution et des exclusions. Il ne signifie pas que tous les
modeles de cette taille sont qualifies.

| Chemin | Couverture executee | Configuration | Exclusion principale |
| --- | --- | --- | --- |
| Statique contigu | `2 044 416` et `4 102 893` DDL | PETSc CG/GAMG/BAIJ, 2 et 4 rangs | pas de generalisation HPC |
| Statique graphe | `2 044 416` DDL | PT-Scotch, 2 et 4 rangs | ne remplace pas le chemin contigu par defaut |
| Matrix-free | `107 811` DDL | CG par operateur, bloc-Jacobi nodal | tentative 1M incomplete |
| Coherence backend | `1 029` DDL | SciPy, matrix-free et PETSc | pas de conclusion grande echelle |
| Modal | `1 029` et `107 811` DDL, 3 modes | SLEPc shift-invert | modal 2M bloque par ressource |
| Newmark | `2 044 416` DDL, 10 pas, `dt=1e-4 s` | PETSc/GAMG, masse TET4 coherente | seuil borne `1e-5`; calibration production requise |

La campagne a ete executee sur une seule configuration hote x86_64 sous
WSL2, avec une seule image Docker. Le profil d'execution associe est desormais
archive dans `qualification/benchmarks/qf_solver_0_2_2_backend_campaign/runtime_profile.json`
et documente dans le fichier Markdown voisin : CPU visible AMD Ryzen 5 5500,
12 coeurs logiques et 46,97 GiB de memoire visible. Ces valeurs decrivent les
ressources exposees au conteneur au moment du probe ; aucune generalisation de
performance a une autre machine n'est permise.

## Environnement de test et tracabilite

Les manifestes d'execution Docker enregistrent Python `3.12.3`, NumPy
`2.4.6`, SciPy `1.17.1`, `petsc4py 3.25.1`, OpenBLAS `0.3.31.188.0` et
`OPENBLAS_NUM_THREADS=1`. Le profil d'execution R1 ajoute la version
`slepc4py 3.25.1`, le modele CPU, le nombre de coeurs et la memoire visible ;
il ferme la condition de tracabilite avant signature sans modifier les
manifestes historiques.

La regression locale a ete executee avec Python `3.13.1`, pytest `8.4.1` et
SciPy `1.15.2`. Les `107 deselected` proviennent volontairement de la commande
`-m "not benchmark and not large and not evidence"` : ils correspondent aux
campagnes longues, benchmarks et corpus d'evidence exclus de la regression
rapide, et non a des echecs silencieux.

Les controles publics sont executes par les scripts versionnes
`scripts/audit_public_documents.py` et `scripts/audit_public_release.py`.
Ils ont inspecte `1754` fichiers et produit `0 finding`. Ces scripts n'ont pas
de numero de version independant ; leur revision est celle du depot.

## Criteres de lecture

Les criteres doivent etre distingues des seuils de decision metier :

| Famille | Critere technique documente | Resultat |
| --- | --- | --- |
| Statique contigu | DDL reels >= `2 000 000`, residu relatif <= `1e-8`, efficacite forte >= `0,60` a 2 et 4 rangs | `0,651` a 2M, `0,615` a 4M : PASS |
| Statique graphe | convergence PASS et efficacite forte >= `0,60` | `0,621` : PASS borne |
| Comparaison backend | ecart de deplacement <= `1e-7` sur le cas de comparaison | `<1,5e-13` : PASS |
| Matrix-free | convergence solveur et residu relatif observe, sans seuil de scaling 1M declare | `1,104e-12` a 107811 DDL : PASS borne |
| Modal SLEPc | tolerance numerique configuree `1e-8` et residu modal physique <= `1e-8` | `2,789e-12` a 107811 DDL : PASS borne |
| Newmark | tolerance KSP `1e-8`, convergence des pas et residu physique relatif <= `1e-5` | `1,968e-6` : PASS borne, R2 fermee |

Le residu Newmark `1,968e-6` n'est donc pas compare abusivement a la
tolerance KSP `1e-8` : ces deux grandeurs ne sont pas normalisees de la meme
maniere. Pour ce gate borne, le seuil d'acceptation du residu physique est
fixe a `1e-5`; la valeur observee est 5,08 fois inferieure au seuil. R2 est
fermee pour cette campagne, mais une calibration par domaine reste requise
avant toute production.

## Resultats obtenus

| Campagne | Mesure observee | Critere de lecture | Statut |
| --- | --- | --- | --- |
| PETSc contigu | efficacites fortes `0,651` et `0,615`, residus converges | seuils statiques ci-dessus | PASS borne |
| PETSc graphe/PT-Scotch | efficacite forte `0,621`, manifestes PASS | seuil graphe `0,60` | PASS borne |
| Matrix-free | residu relatif `1,104e-12` a `107811` DDL | convergence observee | PASS borne |
| Comparaison backend | ecarts `1,087e-13` et `1,417e-13` vs SciPy | tolerance `1e-7` | PASS |
| Modal SLEPc | residu modal maximal `2,789e-12` a `107811` DDL | tolerance `1e-8` | PASS borne |
| Newmark PETSc/GAMG | 10 pas, 222 iterations, residu physique relatif max `1,968e-6` | seuil borne `1e-5` | PASS borne, R2 fermee |
| Manifestes | sept manifestes verifies | aucune erreur de hash ou de chemin | PASS |

## Resultats echoues ou incomplets

| Test | Tentative | Cause et observable | Verdict |
| --- | --- | --- | --- |
| Modal SLEPc 2M | Oui, 3 modes, 2 rangs | signal `9` pendant shift-invert, environ `33,5 GiB` observes, aucune divergence numerique conclue | `BLOCKED_RESOURCE_LIMIT`, pas PASS |
| Matrix-free 1M | Oui, timeout `900 s` | `31` points de telemetry a `30 s`, RSS proche de `293,95 MiB`, aucun resume ni residu final | `BLOCKED_TIMEOUT`, non numerique |

La tentative historique matrix-free 1M est archivee dans
`qualification/benchmarks/qf_solver_0_2_2_backend_campaign/matrix_free_1m_resource_limit/`.
La relance R3 controlee est archivee dans
`qualification/benchmarks/qf_solver_0_2_2_backend_campaign/matrix_free_1m_r2/`.
Elle ne pretend ni FAIL numerique ni PASS : le timeout est un resultat de
ressource/temps, avec telemetry reproductible.

## Architecture du chemin graphe

Le chemin PT-Scotch est relie au code dans
`src/solveur/large/partitioning.py` et appele depuis
`src/solveur/large/distributed_model.py`. Les manifestes graphe conservent la
commande `--partition-strategy graph --graph-partitioner ptscotch`, le nombre
de rangs, la strategie de partition et le nom du partitionneur. Le dossier
technique de reference est `docs/architecture.md`, complete par le plan V&V
`docs/verification/qf_solver_0_2_2_alpha_vnv_multi_million_plan.md`.

## Synthese pre-decision Go/No-Go

- **Go technique borne :** six chemins numeriques completes sont agreges,
  sept manifestes sont verifies et les criteres explicites statiques,
  graphe, comparaison et modal intermediaire passent.
- **Condition dynamique :** Newmark converge et publie `1,968e-6` de residu
  physique relatif maximal, sous le seuil borne `1e-5`; R2 est fermee pour la
  campagne, avec calibration production encore requise.
- **Hors perimetre :** modal SLEPc 2M bloque par ressource et matrix-free 1M
  bloque par timeout controle ; aucune extrapolation 107811 -> 2M n'est permise.
- **Risque principal :** generalisation a une autre machine, une autre image,
  une autre version SLEPc ou une autre topologie non demontree.
- **Decision Owner enregistree :** `accepted_with_recommendations`.
  La condition R1 de la reponse Q8 est fermee par l'addendum
  `runtime_profile.json` : `slepc4py 3.25.1`, AMD Ryzen 5 5500, 12 coeurs
  logiques et 46,97 GiB visibles sont maintenant traces. La signature Owner
  est enregistree le 2026-08-23 sur ce dossier.

La decision ne vaut ni promotion `stable`, ni release. Les conditions et
recommandations restent dans le registre de revue.

## Questions Owner reformulees

### Q1 - Fermeture du gate technique

Acceptez-vous de fermer le gate backend uniquement pour le perimetre numerique
explicitement liste, avec les seuils et exclusions ci-dessus ?

Reponse Owner : **OUI** - perimetre clair et exclusions assumees.

### Q2 - Scalabilite statique contigue

Acceptez-vous la preuve statique jusqu'a `2 044 416` et `4 102 893` DDL sur
architecture contigue, sachant que les criteres sont residu relatif `<=1e-8`,
efficacite forte `>=0,60` a 2/4 rangs, une machine et une image ?

Reponse Owner : **CONDITIONNELLEMENT** - efficacites `0,651` et `0,615`
superieures a `0,60`, avec verification du calcul a conserver.

### Q3 - Partitionnement PT-Scotch

Acceptez-vous le chemin graphe comme preuve bornee, avec efficacite `0,621`,
la commande PT-Scotch tracee dans les manifestes et le chemin contigu conserve
comme defaut ?

Reponse Owner : **OUI** - PT-Scotch est accepte et le chemin reste optionnel.

### Q4 - Matrix-free et coherence backend

Acceptez-vous la coherence SciPy/matrix-free/PETSc sur le cas `1029` DDL
(`ecarts <=1e-7`) et la preuve matrix-free a `107811` DDL (`1,104e-12`), sans
revendiquer la tentative matrix-free 1M ?

Reponse Owner : **CONDITIONNELLEMENT** - coherence validee ; la relance R3 est
executee et classee `BLOCKED_TIMEOUT`, sans PASS matrix-free 1M.

### Q5 - Modal SLEPc

Acceptez-vous le modal SLEPc jusqu'a `107811` DDL, trois modes et residu
`2,789e-12` pour une tolerance configuree `1e-8`, sans couverture modale 2M ?

Reponse Owner : **CONDITIONNELLEMENT** - modal accepte jusqu'a `107811` DDL ;
la couverture 2M reste inconnue et doit rester une limite documentaire.

### Q6 - Newmark

Acceptez-vous la preuve Newmark a `2 044 416` DDL, dix pas et 222 iterations,
avec un residu physique relatif maximal `1,968e-6`, et un seuil borne explicite
de `1e-5` pour cette observable ?

Reponse Owner : **CONDITIONNELLEMENT** - preuve technique acceptee ; le seuil
borne du residu physique est fixe a `1e-5` et la valeur `1,968e-6` le respecte.
La calibration du seuil pour la production reste requise.

### Q7 - Echecs et limites

Acceptez-vous de classer le modal 2M comme `BLOCKED_RESOURCE_LIMIT` et le
matrix-free 1M comme `BLOCKED_TIMEOUT`, plutot que de les presenter comme des
PASS ou des echecs numeriques ?

Reponse Owner : **OUI** - classification honnete : `BLOCKED_RESOURCE_LIMIT`
et `BLOCKED_TIMEOUT`, pas `FAIL` numerique.

### Q8 - Environnement et tracabilite

Acceptez-vous l'archivage avec package `0.2.2a0`, image d'execution taguee
`0.2.0` mais epinglee par digest, versions PETSc/SciPy/SLEPc capturees, profil
hardware archive, et `107` tests exclus par filtre explicite ?

Reponse Owner : **CONDITIONNELLEMENT** - environnement acceptable ; la
condition R1 est maintenant satisfaite par l'addendum de profil, et la
confirmation Owner enregistree le 2026-08-23.

### Q9 - Decision Owner

Choisir une decision pour le gate backend, sans promotion `stable` :

`accepted_with_recommendations / accepted_for_bounded_engineering_use / more_evidence_required`

Decision Owner : `accepted_with_recommendations`.

Commentaire Owner : R1 et R2 sont fermees pour le perimetre borne. R2 reste
soumise a calibration avant toute production ; R3 est executee et reste
bloquee par timeout.

Signature Owner : Owner - confirmation explicite enregistree    Date : 2026-08-23

## Recommandations Owner enregistrees

1. **R1 - FERMEE avant signature :** version `slepc4py 3.25.1` et profil
   CPU/RAM exact de la machine de campagne archives dans
   `qualification/benchmarks/qf_solver_0_2_2_backend_campaign/runtime_profile.json`.
2. **R2 - FERMEE pour le gate borne :** seuil d'acceptation du residu
   physique Newmark fixe a `1e-5`; calibration par domaine requise avant
   production.
3. **R3 - EXECUTEE, resultat bloque :** relance matrix-free 1M avec timeout
   `900 s`, telemetry memoire et metriques periodiques ; poursuivre en v0.3.0
   avec une strategie de performance dediee.
4. **R4 - v0.3.0 :** definir une strategie memoire pour le modal 2M ou
   documenter formellement la limite actuelle a `107k` DDL.

## Tracabilite

- Rapport technique : `docs/verification/qf_solver_0_2_2_alpha_backend_report.md`.
- Plan assemblage/scaling : `docs/verification/qf_solver_0_2_2_alpha_vnv_assembly_scaling_plan.md`.
- Plan multi-million : `docs/verification/qf_solver_0_2_2_alpha_vnv_multi_million_plan.md`.
- Synthese campagne : `qualification/benchmarks/qf_solver_0_2_2_backend_campaign/campaign.json`.
- Limite modale 2M : `qualification/benchmarks/qf_solver_0_2_2_backend_campaign/modal_2m_resource_limit/attempt.json`.
- Limite matrix-free 1M : `qualification/benchmarks/qf_solver_0_2_2_backend_campaign/matrix_free_1m_resource_limit/attempt.json`.
- Profil d'execution R1 : `qualification/benchmarks/qf_solver_0_2_2_backend_campaign/runtime_profile.json` et `qualification/benchmarks/qf_solver_0_2_2_backend_campaign/runtime_profile.md`.
- Seuil Newmark R2 : `qualification/benchmarks/qf_solver_0_2_2_backend_campaign/newmark_acceptance_threshold.json`.
- Relance matrix-free R3 : `qualification/benchmarks/qf_solver_0_2_2_backend_campaign/matrix_free_1m_r2/attempt.json` et `attempt.md`.
- Audit public : `qualification/publication_audit_0_2_2.json`.
- Feuille de route : `prochaines_etapes.md`.

Une reponse Owner favorable ferme uniquement le gate technique borne. Elle ne
vaut ni qualification `stable`, ni decision de release, ni autorisation de
publication.
