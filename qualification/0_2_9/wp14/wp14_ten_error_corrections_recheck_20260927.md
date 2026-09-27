# WP14 — État réel des dix anciens points en échec

**Bilan du recontrôle : 5 PASS, 5 FAIL. WP14 reste HOLD, 0/1.**
Le total machine observé reste 95/100. Aucun point, seuil, résultat brut ni
décision Owner n'a été modifié. Aucun commit, merge, push, tag ou publication.

Branche : `codex/wp14-remediation-clean` ; HEAD :
`0c7ecfaee74c1f0bb362afb1f0ac8bc45686c0ba`. Les tests portent sur la copie
de travail corrigée et non committée. Ce n'est pas une exécution de release
sur une source nouvellement gelée.

## Liste des dix points

| ID | Contrôle | État actuel | Correction ou blocage |
| --- | --- | --- | --- |
| R01 | Objectif de 700 lignes | PASS | Politique Owner appliquée : objectif indicatif, dépassements visibles ; pas de plafond arbitraire. |
| R02 | Audit documentaire du dépôt entier | FAIL | Les preuves internes du dépôt ne forment pas une distribution publique propre. |
| R03 | Snapshot documentaire historique et classification courante | FAIL | Le PASS 0.2.7 demeure intact ; il ne prouve pas le PASS du dépôt courant. |
| R04 | Hygiène des sources du dépôt entier | FAIL | Des chemins de poste et marqueurs internes subsistent dans les preuves ; scanners inchangés. |
| R05 | Hygiène de `git archive HEAD` | FAIL | Cette archive contient toujours les preuves internes ; ce n'est pas le paquet sélectionné. |
| R06 | Vocabulaire analyseur | PASS | Contrôle lexical strict, copies d'archives comprises, migration vérifiable. |
| R07 | Convergence TET4 en déplacement | PASS du contrôle corrigé | Qualification C2R6 vérifiée séparément ; ancien échec préservé. |
| R08 | Convergence TET4 en énergie | PASS du contrôle corrigé | Même séparation des générations ; seuil inchangé. |
| R09 | Convergence TET4 en contrainte | PASS du contrôle corrigé | Même séparation des générations ; seuil inchangé. |
| R10 | Quatre NPZ HEX8 historiques | FAIL / preuve indisponible | Lecteur d'archive sécurisé ajouté ; les octets originaux restent introuvables. |

R01 et R06 étaient déjà corrigés au début de ce lot. R07–R09 sont les trois
correctifs supplémentaires. Les cinq autres points ne sont ni désélectionnés,
ni marqués `xfail`, ni convertis artificiellement en PASS.

## R07–R09 : correction du contrôle, pas des nombres

L'ancien test exigeait que la campagne grossière WP04-C soit qualifiée,
alors que son échec avait été conservé et que WP04-F retenait C2R6.

| Observable | WP04-C historique | Seuil gelé | C2R6 accepté |
| --- | ---: | ---: | ---: |
| Déplacement | 16,406181 % — FAIL | 2 % | 1,692701 % — PASS |
| Énergie | 16,379509 % — FAIL | 2 % | 1,689047 % — PASS |
| Contrainte | 24,310580 % — FAIL | 10 % | 2,164607 % — PASS |

Le nouveau helper `tests/helpers/wp04_lineage.py` contrôle :

- l'identité des blobs Git et SHA-256 du contrat historique, du résumé FAIL
  et de la clôture WP04-F ; la copie courante ne peut modifier leurs nombres ;
- les trois entrées C2R6 récupérées, par le manifeste d'archive existant :
  audit gelé, campagne et résultat M3 ; le M3 séparé doit égaler le M3 de la campagne ;
- les hiérarchies distinctes `8/16/24` et `48/64`, leurs définitions de delta
  propres, les observables, la route MINRES/Jacobi, les 12 états acceptés,
  l'équilibre et l'enveloppe ;
- l'ancien G04-10 réellement FAIL et le placeholder original C2R6
  `UNRESOLVED`, tous deux préservés.

Les trois tests conservent leurs identifiants, mais contrôlent maintenant
explicitement l'échec historique **et** la paire acceptée. Les tests négatifs
refusent les seuils modifiés, mauvaises routes/hiérarchies, données absentes,
états/digests incohérents, valeurs non finies et métriques falsifiées.

Un test supplémentaire conserve la recomputation live de l'ancienne campagne
et exige ses trois échecs numériques. Il n'a pas été exécuté dans ce lot :
aucun grand solve n'a été relancé. Une comparaison AST confirme que les
fonctions de maillage, de campagne, de calcul et d'écriture demeurent identiques.

Le SHA-256 `66e64047…aa0708` du résumé Git LF et le digest historique
`a9647723…c0368d` diffèrent uniquement par LF/CRLF : la conversion exacte
reproduit ce dernier. Aucun hash historique n'a été remplacé.

Ce contrôle recompute des observables depuis les JSON archivés. Il ne constitue
ni un nouveau solve FEM indépendant ni un audit exhaustif des anciennes télémétries.

## R02–R05 : le paquet sélectionné passe, le dépôt entier reste en échec

Un nouveau mode **de préparation uniquement**,
`preview_public_package_worktree`, lit les octets actuellement sélectionnés,
conserve leurs hashes et les distingue des blobs de la baseline.
Le planner historique lié aux blobs Git reste disponible et inchangé dans son rôle.

Résultat du preview : **551 fichiers, zéro constat strict, zéro fichier de
packaging requis manquant**. Seuls `src/solveur/api/public.py` et
`src/solveur/core/audit.py` diffèrent des blobs de préparation, pour les
corrections textuelles déjà documentées. Hash du mapping déterministe :
`87786986092e730c4418f23019f49448d6a4b3a693c850e3eae9ad0482e557c2`.

Ce PASS de préparation ne ferme pas les quatre gates du dépôt entier.
Il n'y a eu ni build wheel/sdist ni installation du nouveau paquet. La commande
de diagnostic `git archive HEAD` a, elle, été exécutée et reste en échec.

Pour fermer ce groupe sans détruire les preuves internes : figer la source
corrigée, enregistrer prospectivement le périmètre public exact, puis attester
la sélection réelle, le build, l'installation, les imports, les commandes CLI
et les scans des artefacts distribués. La décision de périmètre et la clôture
release restent des gates Owner ; le preview ne les autorise pas.

## R10 : intégrité corrigée dans le lecteur, disponibilité toujours bloquée

La recherche en lecture seule a vérifié les chemins exacts dans 54 dossiers
temporaires et 33 racines supplémentaires du workspace/worktrees enregistrés.
Ces groupes peuvent se chevaucher. Aucun des quatre fichiers n'a été trouvé ;
le manifeste d'archive existant ne les contient pas non plus.

| Fichier manquant | Taille attendue | SHA-256 historique |
| --- | ---: | --- |
| `h1_raw.npz` | 510 642 | `021fb16a46f369452f5aa0a8e913c1bd345eb3128df3cb5c5a1edce63805ab2d` |
| `h1_replay_raw.npz` | 510 642 | `021fb16a46f369452f5aa0a8e913c1bd345eb3128df3cb5c5a1edce63805ab2d` |
| `h2_raw.npz` | 1 635 806 | `cdaf20e269e379e52d9888a618bad6b5bd8d7ca98dc20adbef1a7d54a1aaf3ee` |
| `h3_raw.npz` | 3 761 002 | `a595374adbabde01a1f297a6e221c73adeaf10f915dfd7f59af4b4bf455dd14b` |

Le nouveau lecteur accepte les octets exacts du checkout **ou** d'une archive
liée par manifeste, vérifie taille/hash avant lecture NumPy, interdit les
échappements de chemin et refuse un fichier local corrompu sans le remplacer
silencieusement par une autre copie. Le test existant conserve ses contrôles
de dimensions, finitude, absence de tableaux objets et identité des octets ;
il vérifie aussi la liste complète des arrays déclarés.

Le résultat réel demeure `HISTORICAL_RAW_EVIDENCE_UNAVAILABLE`.
Il faut récupérer les originaux ou autoriser une campagne prospective distincte
avec de nouveaux hashes. Un nouveau solve ne prouverait pas l'intégrité
des fichiers historiques disparus.

## Vérifications exécutées

| Contrôle | Résultat |
| --- | --- |
| Recontrôle exact des dix points | **5 PASS, 5 FAIL**, 1 avertissement ; 223,12 s ; code 1 |
| Batterie ciblée élargie | **195 PASS**, 1 avertissement ; 24,18 s ; code 0 |
| Ruff global `src scripts tests` | PASS |
| Mypy ciblé | PASS, trois modules ; aucun claim global |
| Compileall `scripts tests src` | PASS |
| Conservation AST de la campagne historique | PASS |
| `git diff --check` | PASS |

L'avertissement décrit la dette des 48 fichiers dépassant l'objectif indicatif
de 700 lignes. Les commandes utilisent explicitement le répertoire d'archive
via `QF_SOLVER_EVIDENCE_ARCHIVE_ROOT` ; aucune preuve absente n'est ignorée.
Les argv exacts, hashes des fichiers corrigés, essais intermédiaires et limites
de capture figurent dans le JSON compagnon. Il n'existe pas de nouveau manifeste
de processus ou de logs bruts/JUnit distincts pour cette vérification de développement.

**Suite :** traiter le contrat public prospectif et la lacune d'archive, puis
figer le candidat avant les gates complets de qualité, engineering, documentation
et packaging. Ce lot ne ferme pas la totalité de WP14.
