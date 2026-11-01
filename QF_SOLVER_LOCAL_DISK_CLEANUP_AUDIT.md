# Audit local du stockage QF Solver — 2026-11-01

## Résumé et décision

Cet audit est un inventaire **en lecture seule** des copies QF Solver, worktrees, répertoires de cache et environnements repérés sur C:, D: et E:. Il prépare une éventuelle opération ultérieure; il n'autorise aucun nettoyage.

- **Aucune suppression, purge, commande git worktree prune, git gc, git clean ou reset, test ou exécution FEM n'a été effectuée.** Les seules écritures sont ce rapport et les quatre CSV compagnons dans le checkout de consolidation autorisé.
- Espace effectivement libéré pendant cet audit : **0 Gio**.
- Potentiel logique des seuls caches standards et du cache pip identifié : **environ 3,203 Gio**, à confirmer par une nouvelle analyse et une autorisation distincte. La quantité de clusters réellement libérable n'a pas été mesurée.
- Aucune cible n'est classée SAFE_AFTER_BACKUP. Les sorties scientifiques, copies Git ambiguës, worktrees modifiés et répertoires tmp restent à préserver ou à examiner.

Les tailles ci-dessous sont des **longueurs logiques de fichiers**, pas une mesure de l'allocation réelle NTFS. Compression, fichiers creux, liens physiques et métadonnées peuvent modifier l'espace récupéré. Les inventaires ont ignoré les points de réanalyse et n'en ont traversé aucun; aucun scanner n'a signalé d'erreur dans les racines agrégées décrites ici. Ce n'est pas un inventaire global de tout le disque.

Méthode : scanners .NET en lecture seule pour les tailles, nombres de fichiers/dossiers et dates de dernière écriture; statuts Git et HEAD des worktrees; comparaison des branches locales avec les refs distantes courantes. L'état Git du checkout de consolidation a été relevé avant la création de ce rapport et des CSV, comme indiqué dans sa ligne de l'inventaire.

## Capacité des volumes

| Volume | Capacité | Libre au relevé |
|---|---:|---:|
| C: | 890 666 606 592 octets (829,4 Gio) | 19 835 764 736 octets (18,47 Gio) |
| D: | 108 827 504 640 octets (101,3 Gio) | 89 865 822 208 octets (83,72 Gio) |
| E: | 999 477 784 576 octets (930,8 Gio) | 840 807 104 512 octets (783,2 Gio) |

## Principaux emplacements mesurés

Les 30 entrées sont triées par taille logique décroissante et servent à prioriser une revue. **Elles se chevauchent** : par exemple, un total de worktrees est inclus dans le total de son répertoire parent, et tmp, qualification, results et .git sont inclus dans le checkout SAFRAN. Ne pas additionner ces lignes.

| # | Emplacement | Gio | Classe de traitement |
|---:|---|---:|---|
| 1 | C:\Users\fari\.codex\worktrees (total) | 88,597 | NEEDS_REVIEW — racine mixte de worktrees et copies |
| 2 | C:\Users\fari\Documents\projet\SAFRAN\solveur | 65,549 | NEEDS_REVIEW — dépôt distant distinct; préserver ses données |
| 3 | Worktrees enregistrés sous C:\Users\fari\.codex\worktrees (87) | 56,854 | KEEP_ACTIVE / NEEDS_REVIEW |
| 4 | E:\QFSolverAgents (total) | 52,623 | KEEP_ACTIVE / KEEP_SCIENTIFIC_EVIDENCE / NEEDS_REVIEW |
| 5 | Worktrees enregistrés sous E:\QFSolverAgents (76) | 49,936 | KEEP_ACTIVE / NEEDS_REVIEW |
| 6 | C:\Users\fari\Documents\projet\SAFRAN\solveur\tmp | 37,044 | NEEDS_REVIEW — contenu non classifié |
| 7 | 56 dossiers auxiliaires sous C:\Users\fari\.codex\worktrees | 31,743 | NEEDS_REVIEW — dépôts et instantanés |
| 8 | E:\qf_wp16_staging_20260929 | 20,502 | NEEDS_REVIEW — staging |
| 9 | E:\QFSolverWP12B | 13,399 | NEEDS_REVIEW — copies de travail |
| 10 | C:\Users\fari\Documents\projet\SAFRAN\.codex-worktrees | 11,903 | NEEDS_REVIEW — worktrees, certains modifiés |
| 11 | SAFRAN\solveur\qualification | 11,336 | KEEP_SCIENTIFIC_EVIDENCE |
| 12 | E:\QFSolverAgents\worktrees | 10,492 | KEEP_ACTIVE / NEEDS_REVIEW |
| 13 | SAFRAN\solveur\results | 8,373 | KEEP_SCIENTIFIC_EVIDENCE |
| 14 | E:\QFSolverAgents\controllers | 7,206 | KEEP_ACTIVE — contrôleurs épinglés |
| 15 | C:\Users\fari\Documents\projet\venv | 5,837 | NEEDS_REVIEW — usage sans lien confirmé |
| 16 | C:\qf212 | 5,032 | NEEDS_REVIEW — dépôts imbriqués |
| 17 | SAFRAN\solveur\.git | 4,973 | KEEP — métadonnées du dépôt |
| 18 | C:\Users\fari\Documents\qf_solver | 3,078 | NEEDS_REVIEW — checkout modifié, en retard sur remote |
| 19 | E:\QFSolverAgents\test-worktrees | 1,968 | NEEDS_REVIEW |
| 20 | SAFRAN\qf_solver_corrective_025_lot2_head | 1,536 | NEEDS_REVIEW — copie Git à vérifier |
| 21 | SAFRAN\qf_solver_corrective_025_final | 1,442 | NEEDS_REVIEW — copie Git à vérifier |
| 22 | SAFRAN\qf-solver-v0.2.12-clean | 1,269 | NEEDS_REVIEW — clone propre et environnement Python |
| 23 | SAFRAN\qf_solver_corrective_025_lot6_c601 | 1,261 | NEEDS_REVIEW — copie Git à vérifier |
| 24 | SAFRAN\qf_solver_corrective_025_replay | 1,260 | NEEDS_REVIEW — copie Git à vérifier |
| 25 | SAFRAN\qf_solver_corrective_025_g02_clean | 1,256 | NEEDS_REVIEW — copie Git à vérifier |
| 26 | SAFRAN\qf_solver_corrective_025 | 1,213 | NEEDS_REVIEW — copie Git à vérifier |
| 27 | SAFRAN\solveur\results_large | 1,096 | KEEP_SCIENTIFIC_EVIDENCE |
| 28 | SAFRAN\solveur\docs | 1,025 | KEEP — documentation |
| 29 | E:\QFSolverAgents\publish | 0,657 | KEEP / NEEDS_REVIEW — artefacts de publication |
| 30 | SAFRAN\solveur\.ci-repro-venv | 0,653 | NEEDS_REVIEW — environnement reproductible |

Les chemins SAFRAN abrégés sont sous C:\Users\fari\Documents\projet\SAFRAN. Les copies correctives présentent plusieurs pointeurs .git invalides; candidate_025_final et candidate_025_rc sont modifiées. Les clones WP05/WP06/WP07/WP08/WP15, chacun entre 0,343 et 0,540 Gio, pointent vers des branches locales absentes des références GitHub actuelles; ils ne sont pas des candidats de suppression automatique.

## Worktrees, branches et copies auxiliaires

### Worktrees enregistrés

Le relevé contient 164 worktrees enregistrés : 87 sous C:\Users\fari\.codex\worktrees, 76 sous E:\QFSolverAgents et le checkout C:\Users\fari\Documents\qf_solver. Tous les chemins existaient pendant le scan. Leur taille logique totale est 117 970 022 581 octets, soit **109,87 Gio** : 56,854 Gio, 49,936 Gio et 3,078 Gio respectivement.

État Git au relevé :

- 153 propres et 11 modifiés; 42 sont détachés (41 propres, un modifié).
- 15 entrées non suivies et 1 760 entrées ignorées dans les statuts des worktrees.
- Parmi les 122 worktrees attachés à une branche, 92 noms de branche sont absents des refs distantes actuellement publiées, 28 HEAD correspondent à la branche distante, et 2 HEAD en diffèrent.
- Les branches absentes du remote ne prouvent pas que leurs commits ou fichiers soient inutiles.
- Les deux HEAD divergents sont en retard, sans commit en avance : C:\Users\fari\Documents\qf_solver est 228 commits derrière (branche locale emptiesvoids-cloud/0.2.12); E:\QFSolverAgents\test-worktrees\vv3d-science-source-candidate est 3 commits derrière. Le premier checkout a également quatre entrées de statut, dont deux non suivies.

Worktrees modifiés à préserver (le nombre après le chemin est le nombre d'entrées de statut; les fichiers non suivis sont indiqués séparément) :

| Chemin | État constaté |
|---|---|
| C:\Users\fari\Documents\qf_solver | 4 entrées, 2 non suivies; 228 en retard, 0 en avance |
| C:\Users\fari\.codex\worktrees\qf-solver-branch-cleanup-2026-10-27\qf_solver | 2 entrées, 2 non suivies |
| C:\Users\fari\.codex\worktrees\verify-wp12-elements-loads\qf_solver | 7 entrées, 7 non suivies |
| C:\Users\fari\.codex\worktrees\wp12-rotor-config\qf_solver | 1 entrée, 1 non suivie |
| C:\Users\fari\.codex\worktrees\wp12a-phase4-canonical\qf_solver | 1 entrée |
| C:\Users\fari\.codex\worktrees\wp12a-collect-only\qf_solver | détaché, 3 entrées |
| C:\Users\fari\.codex\worktrees\wp12b-hex8sri-correction\qf_solver | 2 entrées, 2 non suivies |
| E:\QFSolverAgents\hex8-sri-cross-contract-fix | 1 entrée |
| E:\QFSolverAgents\worktrees\vv3d-r2-import-fix | 3 entrées |
| E:\QFSolverAgents\wp12-policy-final | 1 entrée |
| E:\QFSolverAgents\wp12b-hex20-controller-draft | 2 entrées, 1 non suivie |

### Auxiliaires C: et E:

Sous C:\Users\fari\.codex\worktrees, 143 dossiers de premier niveau ont été recensés : 87 sont les worktrees enregistrés ci-dessus et 56 sont des dossiers auxiliaires. Les 56 occupent **31,743 Gio** (319 496 fichiers, 29 195 dossiers, zéro erreur de scan) et comprennent 51 racines Git (46 propres, 5 modifiées) et 5 dossiers sans marqueur Git. Les cinq racines Git modifiées sont :

- d01-combined-rehearsal-20261024 — 4 entrées.
- wp-d01-final-reconcile-scratch-20261024 — 7 entrées, 2 non suivies.
- wp-d01-safe-ff-rehearsal-20261024 — 7 entrées, 2 non suivies.
- wp-e01-restart-current — 4 entrées, 4 non suivies.
- wp-e01l-prep-ae429 — 50 entrées, 50 non suivies.

Les cinq dossiers sans marqueur Git direct sont d01-r4-symmetry-root-cause, r5-canonical-m2-static-2047, r5-canonical-m2-static-r3, vv3d-r2-controller-designation et wp12b-hex8sri-controller-b668292. Ces répertoires contiennent principalement du code, des documents, des contrôleurs ou des artefacts scientifiques; aucun n'est un cache générique confirmé.

La racine E:\QFSolverAgents se réconcilie exactement à **56 503 547 949 octets** :

| Composant non chevauchant | Octets | Gio |
|---|---:|---:|
| 76 worktrees enregistrés | 53 618 547 258 | 49,936 |
| Clone scientifique actif worktrees\vv3d-family-remainder-science-final | 703 121 618 | 0,655 |
| 22 autres dossiers auxiliaires de premier niveau | 2 177 121 575 | 2,028 |
| Résidus sous worktrees hors clones recensés | 114 928 | 0,000107 |
| Résidus sous test-worktrees | 10 727 | 0,000010 |
| Fichiers directement sous la racine | 4 631 843 | 0,004314 |
| **Total** | **56 503 547 949** | **52,623** |

Le clone scientifique actif est propre, sur research/wp12-vv3d-family-remainder-20261030, HEAD ac0f1855a88cc66e48e629eadc4f0e681d1d719d; la politique du dépôt le désigne comme actif. Le répertoire controllers, qui contient les contrôleurs épinglés, n'a aucun résidu hors worktrees enregistrés. Les dossiers publish, evidence, dépendances WP13, builds, diagnostics et journaux sont conservés ou soumis à revue; leur taille complète est dans le CSV auxiliaire.

Après la publication autorisée de la branche de consolidation, origin exposait 36 branches. Les PR #114, #115 et #116 étaient ouvertes au relevé et doivent rester intactes. Les modifications de #115 et #116 se trouvent déjà dans la branche de consolidation. La PR #118 cible codex/wp13-release-engineering-20261031.

## Autres racines et distinction des dépôts

C:\Users\fari\Documents\projet\SAFRAN\solveur occupe **65,549 Gio** (415 559 fichiers, 39 857 dossiers), avec un remote distinct : https://github.com/emptiesvoid-cloud/Solveur.git. Il s'agit d'un checkout scientifique distinct du dépôt QF_solver; sa racine Git est modifiée et compte environ 14 949 entrées non suivies. La branche est main, HEAD afb6c8ebb9aea3fc6ca24c3ad4f5a3f0375f5fd0. Préserver ce checkout et examiner son contenu avant toute action.

- tmp : 37,044 Gio, 373 528 fichiers; dernière écriture observée le 25 octobre 2026. Son nom ne suffit pas à établir que son contenu soit jetable.
- qualification : 11,336 Gio; results : 8,373 Gio; results_large : 1,096 Gio; test-results : 0,449 Gio. **KEEP_SCIENTIFIC_EVIDENCE.**
- .git : 4,973 Gio. Ne pas nettoyer manuellement.
- .ci-repro-venv : 0,653 Gio. Environnement de reproduction; revue avant toute action.
- .mypy_cache : 0,053 Gio environ; inclus dans les caches standards.

Autres racines notables : E:\qf_wp16_staging_20260929 (20,502 Gio), E:\QFSolverWP12B (13,399 Gio; 18 racines Git, dont xD modifiée), C:\Users\fari\Documents\projet\SAFRAN\.codex-worktrees (11,903 Gio; certaines copies modifiées), C:\qf212 (5,032 Gio; dépôts imbriqués), C:\Users\fari\Documents\qf_solver (3,078 Gio; décrit plus haut), qf-solver-v0.2.12-clean (1,269 Gio, clone propre au HEAD de version 0.2.12) et qf_solver_evidence_archive (0,169 Gio, KEEP_SCIENTIFIC_EVIDENCE).

La somme des racines QF et apparentées mesurées, en évitant d'additionner les sous-dossiers aux parents, est d'environ **272,127 Gio**, dont **65,549 Gio** pour le dépôt distinct SAFRAN\solveur. Cela exclut le venv générique de 5,837 Gio et plusieurs runtimes et caches globaux; ce n'est ni la taille de tout C:/E:, ni une mesure de l'allocation physique.

## Caches, environnements et potentiel de récupération

Le scan des répertoires régénérables a couvert 33 racines choisies; ce n'est pas une recherche globale dans tous les profils Windows.

| Type | Dossiers | Taille logique | Classe |
|---|---:|---:|---|
| __pycache__ | 15 989 | 2,139 Gio | SAFE_TO_DELETE lors d'une phase ultérieure autorisée |
| .mypy_cache | 28 | 0,888 Gio | SAFE_TO_DELETE lors d'une phase ultérieure autorisée |
| .pytest_cache | 184 | 0,005 Gio | SAFE_TO_DELETE lors d'une phase ultérieure autorisée |
| .ruff_cache | 177 | 0,001 Gio | SAFE_TO_DELETE lors d'une phase ultérieure autorisée |
| **Caches standards** | **16 378** | **3,033 Gio** | **potentiel logique** |
| Cache pip C:\Users\fari\AppData\Local\pip\Cache | 351 fichiers | 0,169 Gio | SAFE_TO_DELETE lors d'une phase ultérieure autorisée |
| **Total potentiel identifié** |  | **3,203 Gio** | **aucune suppression effectuée** |
| Répertoires build / dist | 64 | 0,099 Gio | NEEDS_REVIEW — ne pas traiter comme cache sûr |
| Environnements venv / .venv repérés dans les racines | 9 | 0,664 Gio | NEEDS_REVIEW — préserver jusqu'à confirmation d'usage |

Répartition logique des caches standards : C: 2,502 Gio, E: 0,532 Gio. En ajoutant le cache pip, le potentiel est C: 2,671 Gio et E: 0,532 Gio. Le cache pip a été confirmé par C:\Python313\python.exe -m pip cache dir; sa dernière écriture relevée est le 31 octobre. Ne pas additionner ces chiffres aux totaux de racines, qui les comprennent déjà.

Autres environnements relevés : C:\Python313 0,144 Gio (KEEP_ACTIVE), C:\Users\fari\venv 0,629 Gio (usage incertain), C:\Users\fari\Documents\projet\venv_qf_solver_agent_b_wp05 0,572 Gio, E:\QFSolverWP12B\venv 0,362 Gio, le .venv du clone propre 0,279 Gio, le venv de l'archive de preuves 0,022 Gio (KEEP_SCIENTIFIC_EVIDENCE), .ci-repro-venv 0,653 Gio, et E:\QFSolverWP12B\python-3.13.17 0,043 Gio. Ces valeurs sont déjà incluses dans les racines parentes.

### Commandes possibles lors d'une phase autorisée distincte

Les commandes suivantes sont consignées pour une éventuelle exécution ultérieure uniquement. Il faudra refaire l'inventaire, confirmer que les chemins et statuts n'ont pas changé, et obtenir une autorisation explicite de nettoyage. Elles n'ont **pas** été exécutées dans cet audit.

Après validation du CSV fraîchement produit, les seules catégories de répertoires à cibler seraient pycache, mypy, pytest et ruff :

~~~powershell
$csv = 'C:\Users\fari\.codex\worktrees\wp13-branch-consolidation-20261101\qf_solver\QF_SOLVER_LOCAL_DISK_REGENERABLE_DIRS.csv'
$allowedKinds = @('pycache', 'mypy', 'pytest', 'ruff')
$targets = @(Import-Csv -LiteralPath $csv | Where-Object { $_.Kind -in $allowedKinds } | Sort-Object { $_.Path.Length } -Descending)
$targets.Count
($targets | Measure-Object -Property Bytes -Sum).Sum
foreach ($target in $targets) {
    if (Test-Path -LiteralPath $target.Path) {
        Remove-Item -LiteralPath $target.Path -Recurse -Force
    }
}
~~~

Pour le cache pip, après autorisation distincte :

~~~powershell
& 'C:\Python313\python.exe' -m pip cache purge
~~~

### SAFRAN\solveur\tmp : sauvegarde, vérification, revue

Ce répertoire de 37,044 Gio est **NEEDS_REVIEW**, pas un cache sûr. D: disposait de 83,72 Gio libres au relevé, soit davantage que sa taille logique, mais il faut revérifier l'espace disponible et la taille réelle avant une copie. Après classification sémantique et autorisation de sauvegarde, choisir une destination D: nouvelle et absente; copier, puis comparer le manifeste SHA-256 complet avant toute décision séparée sur la source.

~~~powershell
$src = 'C:\Users\fari\Documents\projet\SAFRAN\solveur\tmp'
$dst = 'D:\QF_SOLVER_LOCAL_DISK_BACKUPS\SAFRAN-solveur-tmp-20261101'
if (Test-Path -LiteralPath $dst) { throw "La destination existe déjà; choisir un nouvel emplacement." }
robocopy $src $dst /E /COPY:DAT /DCOPY:DAT /R:1 /W:1 /XJ
if ($LASTEXITCODE -ge 8) { throw "Robocopy a signalé une erreur: code $LASTEXITCODE" }

function Get-FileManifest([string]$root) {
    $prefix = [IO.Path]::GetFullPath($root).TrimEnd('\') + '\'
    Get-ChildItem -LiteralPath $root -File -Recurse -Force |
        Where-Object { ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0 } |
        ForEach-Object {
            [pscustomobject]@{
                Path   = $_.FullName.Substring($prefix.Length)
                Length = $_.Length
                SHA256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
            }
        } | Sort-Object Path
}

$sourceManifest = @(Get-FileManifest $src)
$backupManifest = @(Get-FileManifest $dst)
$differences = @(Compare-Object $sourceManifest $backupManifest -Property Path, Length, SHA256)
if ($differences.Count -ne 0) { throw "La vérification SHA-256 a échoué; conserver les deux arborescences." }
~~~

Une copie vérifiée n'autorise pas à elle seule la suppression de la source. Il faut d'abord classifier le contenu et obtenir une autorisation explicite distincte. Si ces deux conditions sont remplies ultérieurement, la commande exacte envisagée serait :

~~~powershell
Remove-Item -LiteralPath 'C:\Users\fari\Documents\projet\SAFRAN\solveur\tmp' -Recurse -Force
~~~

Cette commande n'a pas été lancée. Aucun dossier sale, worktree, dépôt, environnement Python, staging, build/dist, contrôleur, résultat ou preuve scientifique n'a de commande de suppression proposée ici.

## Inventaires compagnons

Les CSV issus de scans en lecture seule apportent le détail par chemin :

- [Inventaire des 164 worktrees](QF_SOLVER_LOCAL_DISK_WORKTREE_INVENTORY.csv)
- [56 dossiers auxiliaires sous .codex\worktrees](QF_SOLVER_LOCAL_DISK_AUXILIARY_CHECKOUTS.csv)
- [Auxiliaires E: et clone scientifique actif](QF_SOLVER_LOCAL_DISK_E_AUXILIARY_DIRECTORIES.csv)
- [Répertoires de cache, build, dist et environnements](QF_SOLVER_LOCAL_DISK_REGENERABLE_DIRS.csv)
