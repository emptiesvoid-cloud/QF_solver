# WP12-B — Actions Owner requises

**PREPARATION_ONLY** · **NUMERICAL_EXECUTION_NOT_PERFORMED** · **WP12_STATUS=OPEN**

Le code d'isolation n'a pas été lancé avec élévation et aucun paramètre système n'a été changé. Deux actions locales sont nécessaires avant qu'un compte dédié puisse être évalué. Le lancement scientifique reste bloqué séparément par l'absence d'attestation de processus enfant et de décision Ed25519 authentifiée.

## OWNER_ACTION_REQUIRED — mettre à jour Windows

**Problème observé :** hôte Windows 10 Enterprise 22H2 en build `19045.6456`; le script refuse tout provisionnement avant `19045.7807`.

**Action :** le niveau correspondant au garde-fou du script est le build `19045.7807`, publié le 13 octobre 2026 sous **KB5126657** pour Windows 10 ESU. Microsoft indique que le package concerne Windows 10 ESU; la seule édition Enterprise ne démontre pas l'éligibilité ESU. Dans Windows, ouvrir **Paramètres → Mise à jour et sécurité → Windows Update → Rechercher des mises à jour**, installer KB5126657 uniquement si Windows Update la propose pour cet appareil, puis redémarrer. Voir [l'article Microsoft KB5126657](https://support.microsoft.com/en-us/servicing/os/windows-10/2026/10/kb5126657-windows-10-21h2-22h2-security-update) et [l'historique Microsoft des versions Windows](https://learn.microsoft.com/en-us/windows/release-health/release-information). Ne pas désactiver les contrôles de mise à jour ni installer un paquet d'une source non approuvée. Si elle n'est pas proposée, arrêter et faire vérifier l'inscription ESU de l'appareil par l'administrateur compétent.

**Vérification après redémarrage :** dans PowerShell, exécuter :

```powershell
$os = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion'
[pscustomobject]@{ Edition = $os.EditionID; Build = $os.CurrentBuild; UBR = $os.UBR; DisplayVersion = $os.DisplayVersion }
```

Le prérequis du script est `EditionID` contenant `Enterprise`, `CurrentBuild=19045`, et `UBR >= 7807`. Si Windows Update ne propose pas ce niveau de build, arrêter et faire vérifier le canal de maintenance ESU de cette édition; ne pas contourner le garde-fou.

## OWNER_ACTION_REQUIRED — prévisualiser le provisionnement local

Après la mise à jour, ouvrir **PowerShell en tant qu'administrateur** et lancer le bloc ci-dessous avec `-WhatIf`. Il vérifie les identités, les chemins, NTFS et le minimum Windows sans créer le compte, appliquer les ACL ou créer les racines de sortie.

```powershell
$runnerRoot = 'E:\QFSolverWP12B\runner'
$isolationScript = Join-Path $runnerRoot 'scripts\wp12_runner\windows\Set-WP12LocalIsolation.ps1'
$isolation = @{
    ScienceCheckout = 'E:\QFSolverWP12B\science'
    RunnerCheckout = 'E:\QFSolverWP12B\runner'
    PythonEnvironment = 'E:\QFSolverWP12B\venv-3.13.17'
    PythonBase = 'E:\QFSolverWP12B\python-3.13.17'
    EvidenceRoot = 'E:\QFSolverWP12B\evidence'
    TemporaryRoot = 'E:\QFSolverWP12B\temporary'
    ArchiveRequestRoot = 'E:\QFSolverWP12B\archive-requests'
    ArchiveRoot = 'E:\QFSolverWP12B\sealed-archive'
    OwnerDecisionRoot = 'E:\QFSolverWP12B\owner-decisions'
    ExpectedScienceCommit = '00428adf38e9397340ac136f6f503a268eb671da'
    ExpectedScienceTree = 'df4ec667bf746b042c900fad1f86bf542e1a437b'
    ExpectedRunnerCommit = '782820fe31fa8b69223bd368e39949fca325ba3e'
    ExpectedRunnerTree = '100d7b3ca869cad267666337947f204c9c8bf31e'
    RunnerAccount = 'QF_WP12_RUNNER'
}
& $isolationScript @isolation -CreateAccount -Apply -WhatIf
```

Le résultat attendu est `PLAN_ONLY_NO_CHANGES` et doit citer les deux identités exactes ci-dessus. Si un chemin ou une identité diffère, ne pas poursuivre.

## OWNER_ACTION_REQUIRED — appliquer l'isolation locale

**Effets :** cette opération administrative crée `QF_WP12_RUNNER` comme compte local standard et demande son mot de passe de manière sécurisée; donne au compte l'accès lecture/exécution aux deux checkouts et aux arbres Python; lui permet d'écrire uniquement dans `evidence`, `temporary` et `archive-requests`; garde `sealed-archive` et `owner-decisions` en lecture seule. Le script crée un backup d'ACL sous `%ProgramData%\QFSolverWP12\acl-backup-*` et donne au compte runner les droits de traversée nécessaires sur les ancêtres. Il ne protège pas contre un administrateur local malveillant et ne crée pas de sandbox du système de fichiers.

**Commande :** reprendre le même bloc PowerShell de prévisualisation, après validation Owner, et remplacer sa dernière ligne par :

```powershell
& $isolationScript @isolation -CreateAccount -Apply
```

Ne pas exécuter cette commande avant le résultat `PLAN_ONLY_NO_CHANGES`, le contrôle des identités et l'approbation explicite de l'Owner. Aucun provisionnement n'a été exécuté par l'agent.

**Vérification synthétique des ACL :** après le provisionnement et depuis une session administrateur, exécuter le probe qui ne crée que des fichiers factices sous `%ProgramData%` :

```powershell
& (Join-Path $runnerRoot 'scripts\wp12_runner\windows\Test-WP12AclProbe.ps1') -RunnerAccount 'QF_WP12_RUNNER' -Apply
```

Il doit refuser l'écriture du compte runner dans trois fichiers synthétiques protégés, autoriser les écritures dans les répertoires factices evidence/temp/request et retourner `PASS_SYNTHETIC_ACL_PROBE`. Il ne touche pas aux preuves historiques. Conserver le `probeRoot` du résultat pour le nettoyage local après revue; il n'est pas une preuve de confinement des processus scientifiques.

**Annulation :** utiliser le `backupRoot` effectivement retourné par le script de provisionnement :

```powershell
$runnerRoot = 'E:\QFSolverWP12B\runner'
& (Join-Path $runnerRoot 'scripts\wp12_runner\windows\Restore-WP12LocalIsolation.ps1') -BackupRoot '<backupRoot retourné>' -Apply
```

Le rollback restaure les ACL sauvegardées, conserve les racines de sortie déjà créées et désactive le compte s'il a été créé par le script. Il ne supprime pas les sorties.

## Trust Owner et décision Ed25519

Aucune clé réelle n'est demandée ni créée. Le générateur de trust store public et le signataire Owner existent; ils demandent localement un chemin de clé privé hors dépôt et une phrase secrète sans écho, sans afficher ni copier la clé privée. La racine HKLM n'est pas configurée. **Ne pas provisionner le trust store à ce stade** : le lancement reste bloqué par le code d'attestation du processus enfant, même si une signature devient disponible.

Après correction/revue indépendante de l'orchestration et nouvelle décision Owner, la procédure locale prévue est : générer un trust store public dans `%LOCALAPPDATA%\QFSolverWP12\owner-trust-source.json` avec `scripts/build_wp12_owner_trust_store.py`, calculer son SHA-256, puis faire approuver et exécuter `Set-WP12OwnerTrustStore.ps1` dans PowerShell administrateur. Ensuite l'Owner prépare et signe une décision distincte liant le SHA du manifeste v3, le nodeid, l'unité, l'environnement, le budget, la destination et l'unique tentative. La clé privée reste uniquement sous contrôle Owner.

Ces opérations HKLM/ACL ne sont pas encore requises pour le pilote, puisque l'exécuteur scientifique demeure désactivé. Une simple confirmation conversationnelle, un JSON `APPROVED` ou le silence ne remplacent pas la décision signée et la confirmation explicite du lancement.
