# WP14 — Terminologie analyseur et correctifs de qualité

**Correctifs ciblés vérifiés ; WP14 reste HOLD, 0/1.** Le total machine
observé reste 95/100, sans modification du ledger.

Branche : `codex/wp14-remediation-clean`. HEAD de départ :
`0c7ecfaee74c1f0bb362afb1f0ac8bc45686c0ba`. Les contrôles portent sur la
copie de travail modifiée, non committée : aucune exécution formelle sur un
nouveau SHA n'est revendiquée. Aucun merge, push, tag ou publication.

## Terminologie, archives comprises

Les deux occurrences restantes ont été remplacées par `analyzer report`
et `ANALYZER_REPORT`. Les représentations maintenues utilisent « analyseur ».
Les décisions Owner conservent leur autorité : un rapport analyseur n'est
pas une nouvelle acceptation ni une référence indépendante.

Le contrôle lexical ne dispense plus les archives et documents générés de
l'inventaire Git. Il refuse aussi une entrée attendue absente ou un texte
UTF-8 invalide. L'inventaire effectué avant l'écriture de ce bilan comptait
5 682 entrées ; le contrôle n'a trouvé aucun libellé interdit ni erreur de
lecture. Les fichiers d'instructions privés et binaires ne sont pas migrés.

Le manifeste `wp14_analyzer_terminology_migration_20260927.json` distingue
les octets originaux et les copies migrées. Le vérificateur reconstruit la
transformation depuis les objets Git originaux, puis compare **tous les
octets**, et pas seulement le nouveau hash. Pour chacun des deux fichiers,
une seule substitution est autorisée. Toute autre modification, notamment
un changement de seuil même accompagné d'un manifeste recalculé, échoue.

| Copie courante migrée | SHA-256 original | SHA-256 migré |
| --- | --- | --- |
| `docs/verification/0_2_9/wp06f-closure-contract.md` | `45f919ba237957cad473959fd86b0dd9d1e4c8a2009856407b088802378df866` | `8e389f0987fbeb346aea4a6e32f124fd428d9c5a4e326a2411e49e3e9c7869cb` |
| `qualification/0_2_9/wp06f_closure_contract.json` | `b9379d24e255343020428ee840fdc5afe724a6bf4cee4190975ea2aad178843d` | `6bd5228ed76748173579e2d378a8319b8f91c840ced0ebcd572167e269012875` |

L'historique Git n'est pas réécrit. Les digests d'exécutions anciennes restent
liés aux originaux ; ils ne sont pas remplacés rétroactivement par les hashes
des copies actuelles. Une future utilisation formelle doit figer et lier le
nouveau digest. Le rang d'autorité du rapport, les nombres, les seuils, les
guards et les scores du contrat WP06-F restent identiques.

## Les 23 diagnostics Ruff sont corrigés

Le bootstrap de cinq runners garde les mêmes chemins et le même ordre
d'insertion dans `sys.path`, mais les affectations `ROOT`/`LOCAL_SOURCE` ont
été déplacées après les imports. Ceci corrige les 20 E402 sans ajouter de
`noqa` ni d'exclusion. Deux imports inutilisés ont été retirés.

Pour le F841 WP08, seule l'affectation inutilisée a été retirée : l'appel
`_json(contract_path)` demeure. Sa validation et ses exceptions ne sont
donc pas supprimées. La configuration Ruff existante n'a pas été assouplie.

Une comparaison AST des sept scripts corrigés confirme la conservation des
corps de fonctions et des affectations de module. La seule normalisation
permise est le remplacement de l'affectation inutilisée par le même appel.
Cinq imports en processus frais depuis un autre répertoire confirment les
mêmes racines source, sans lancer de campagne. Les deux fichiers produit
modifiés ne diffèrent qu'en docstrings et dans un message de présentation.

Les fichiers de runners changent donc de hash : une **nouvelle** campagne
doit les rebinder prospectivement. Cela ne requalifie ni ne réécrit les
preuves d'exécution historiques.

## Échec de test observé puis corrigé

Le premier lot a donné **78 passed, 1 failed**. Le test unitaire
`test_r1_12_contract_freezes_one_m4_slip_attempt` dépendait d'un contrat R1.11
archivé absent du checkout. Ce n'était pas une divergence du solveur.

Le test utilise maintenant des fixtures explicites sous son répertoire
temporaire, marquées `FIXTURE_ONLY_NOT_EXECUTION_EVIDENCE`. Aucun faux
contrat n'a été placé dans les preuves de qualification. Le runner réel
n'acquiert aucun fallback : des tests négatifs démontrent le refus d'un
parent absent, d'un hash incorrect et d'un JSON invalide. L'assertion gelée
du seuil `1e-9` reste présente et inchangée.

## Résultats réellement exécutés

| Contrôle | Résultat | Limitation |
| --- | --- | --- |
| Lot ciblé élargi, 16 modules | **140 passed, 1 warning**, 19,80 s | Pas la suite complète |
| Ruff `src scripts tests` | **PASS**, zéro diagnostic | Configuration existante inchangée |
| Mypy ciblé | PASS, quatre scripts | `--follow-imports=silent`, pas de claim global |
| Compileall `scripts tests src` | PASS | Compilation seulement |
| Migration exacte des deux archives | PASS | Transformation textuelle, pas de qualification numérique |
| Vocabulaire du checkout | PASS, zéro occurrence | Inventaire de fichiers, pas réécriture des anciens commits Git |
| Identité des cinq bootstraps | PASS | Imports frais ; aucun solve de campagne |
| Conservation AST et seuils | PASS | Seuls bootstrap, texte et code inutilisé sont corrigés |
| JSON et diff-check | PASS | Fichiers de cette remédiation |

L'avertissement concerne les dépassements de l'objectif indicatif de
700 lignes. Les 48 fichiers concernés restent visibles ; cet objectif
ne devient pas un plafond de 1 000 ou 2 000 lignes.

## Ce qui reste ouvert

La réussite ci-dessus ne clôt ni G04 standard ni G05 engineering sans leur
nouvelle exécution complète sur une source figée. Les audits du dépôt entier,
le périmètre public prospectif/build, les métadonnées documentaires et les
autres gates release restent à traiter.

Les trois échecs de convergence de l'ancien maillage WP04-C ne sont pas
modifiés ni relancés ici. Les quatre NPZ historiques WP04-D absents ne sont
pas recréés artificiellement. Ces preuves et les résultats C2R6 acceptés
restent des générations distinctes, sans seuil assoupli.

Aucune campagne M1/M2/M3 n'a été relancée. Aucun score ni verdict numérique
historique n'a été converti en PASS. Prochain lot : figer la source corrigée,
lier prospectivement la sélection publique, puis traiter les gates documentaires
et les preuves manquantes avant la décision release.
