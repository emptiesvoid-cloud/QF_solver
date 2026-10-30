[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory)] [string] $ScienceCheckout,
    [Parameter(Mandatory)] [string] $RunnerCheckout,
    [Parameter(Mandatory)] [string] $PythonEnvironment,
    [Parameter(Mandatory)] [string] $PythonBase,
    [Parameter(Mandatory)] [string] $EvidenceRoot,
    [Parameter(Mandatory)] [string] $TemporaryRoot,
    [Parameter(Mandatory)] [string] $ArchiveRequestRoot,
    [Parameter(Mandatory)] [string] $ArchiveRoot,
    [Parameter(Mandatory)] [string] $OwnerDecisionRoot,
    [Parameter(Mandatory)] [string] $ExpectedScienceCommit,
    [Parameter(Mandatory)] [string] $ExpectedScienceTree,
    [Parameter(Mandatory)] [string] $ExpectedRunnerCommit,
    [Parameter(Mandatory)] [string] $ExpectedRunnerTree,
    [string] $RunnerAccount = 'QF_WP12_RUNNER',
    [switch] $Apply,
    [switch] $CreateAccount
)

$ErrorActionPreference = 'Stop'

function Assert-SafeDirectory([string] $Path, [string] $Label) {
    if ($Path -notmatch '^[A-Za-z]:[\\/]') { throw "$Label must be an absolute path" }
    $full = [IO.Path]::GetFullPath($Path)
    $driveRoot = [IO.Path]::GetPathRoot($full)
    if ($full.TrimEnd('\') -eq $driveRoot.TrimEnd('\')) { throw "$Label cannot be a volume root" }
    $current = $driveRoot
    $relative = $full.Substring($driveRoot.Length)
    foreach ($part in $relative.Split([IO.Path]::DirectorySeparatorChar, [StringSplitOptions]::RemoveEmptyEntries)) {
        $current = Join-Path $current $part
        if (-not (Test-Path -LiteralPath $current)) { throw "$Label has an absent path component: $current" }
        if ((Get-Item -LiteralPath $current -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw "$Label contains a symlink or junction component: $current"
        }
    }
    if (-not (Test-Path -LiteralPath $full -PathType Container)) { throw "$Label is not a directory: $full" }
    return $full
}

function Assert-SafeFutureDirectory([string] $Path, [string] $Label) {
    if ($Path -notmatch '^[A-Za-z]:[\\/]') { throw "$Label must be an absolute path" }
    $full = [IO.Path]::GetFullPath($Path)
    $driveRoot = [IO.Path]::GetPathRoot($full)
    if ($full.TrimEnd('\') -eq $driveRoot.TrimEnd('\')) { throw "$Label cannot be a volume root" }
    if (Test-Path -LiteralPath $full) { throw "$Label already exists: $full" }
    $parent = Split-Path -Parent $full
    if (-not (Test-Path -LiteralPath $parent -PathType Container)) { throw "$Label parent must already exist: $parent" }
    $null = Assert-SafeDirectory $parent "$Label parent"
    return $full
}

function Test-PathOverlap([string] $Left, [string] $Right) {
    $leftFull = $Left.TrimEnd('\')
    $rightFull = $Right.TrimEnd('\')
    return $leftFull.Equals($rightFull, [StringComparison]::OrdinalIgnoreCase) -or
        $leftFull.StartsWith($rightFull + '\', [StringComparison]::OrdinalIgnoreCase) -or
        $rightFull.StartsWith($leftFull + '\', [StringComparison]::OrdinalIgnoreCase)
}

function Invoke-Icacls([string[]] $Arguments) {
    & icacls.exe @Arguments
    if ($LASTEXITCODE -ne 0) { throw "icacls failed: $($Arguments -join ' ')" }
}

function Assert-GitIdentity([string] $Root, [string] $Commit, [string] $Tree) {
    $actualCommit = (git -C $Root rev-parse HEAD).Trim()
    $actualTree = (git -C $Root rev-parse 'HEAD^{tree}').Trim()
    if ($LASTEXITCODE -ne 0 -or $actualCommit -ne $Commit -or $actualTree -ne $Tree) {
        throw "Git identity mismatch at $Root (commit=$actualCommit tree=$actualTree)"
    }
    $changes = @(git -C $Root status --porcelain=v1 --untracked-files=all)
    if ($LASTEXITCODE -ne 0 -or $changes.Count -ne 0) { throw "Checkout is not clean: $Root" }
}

function Set-ProtectedTreeAcl([string] $Root, [string] $RunnerSid, [bool] $RunnerCanWrite) {
    $ownerIdentity = [System.Security.Principal.SecurityIdentifier]::new($identity.User.Value)
    $adminIdentity = [System.Security.Principal.SecurityIdentifier]::new($adminGroup)
    $systemIdentity = [System.Security.Principal.SecurityIdentifier]::new($systemSid)
    $runnerIdentity = [System.Security.Principal.SecurityIdentifier]::new($RunnerSid)
    $full = [System.Security.AccessControl.FileSystemRights]::FullControl
    $runnerRights = if ($RunnerCanWrite) {
        [System.Security.AccessControl.FileSystemRights]::Modify
    }
    else {
        [System.Security.AccessControl.FileSystemRights]::ReadAndExecute
    }
    $paths = @((Get-Item -LiteralPath $Root -Force)) + @(Get-ChildItem -LiteralPath $Root -Force -Recurse)
    $reparse = @($paths | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint })
    if ($reparse.Count -gt 0) { throw "Refusing to apply runner ACL through a symlink or junction: $($reparse[0].FullName)" }
    foreach ($item in $paths) {
        $acl = Get-Acl -LiteralPath $item.FullName
        $acl.SetAccessRuleProtection($true, $false)
        foreach ($existingRule in @($acl.Access)) { $acl.RemoveAccessRuleAll($existingRule) }
        $inheritance = if ($item.PSIsContainer) {
            [System.Security.AccessControl.InheritanceFlags]::ContainerInherit -bor [System.Security.AccessControl.InheritanceFlags]::ObjectInherit
        }
        else {
            [System.Security.AccessControl.InheritanceFlags]::None
        }
        $ownerRule = [System.Security.AccessControl.FileSystemAccessRule]::new($ownerIdentity, $full, $inheritance, [System.Security.AccessControl.PropagationFlags]::None, [System.Security.AccessControl.AccessControlType]::Allow)
        $adminRule = [System.Security.AccessControl.FileSystemAccessRule]::new($adminIdentity, $full, $inheritance, [System.Security.AccessControl.PropagationFlags]::None, [System.Security.AccessControl.AccessControlType]::Allow)
        $systemRule = [System.Security.AccessControl.FileSystemAccessRule]::new($systemIdentity, $full, $inheritance, [System.Security.AccessControl.PropagationFlags]::None, [System.Security.AccessControl.AccessControlType]::Allow)
        $runnerRule = [System.Security.AccessControl.FileSystemAccessRule]::new($runnerIdentity, $runnerRights, $inheritance, [System.Security.AccessControl.PropagationFlags]::None, [System.Security.AccessControl.AccessControlType]::Allow)
        $acl.AddAccessRule($ownerRule)
        $acl.AddAccessRule($adminRule)
        $acl.AddAccessRule($systemRule)
        $acl.AddAccessRule($runnerRule)
        Set-Acl -LiteralPath $item.FullName -AclObject $acl
    }
}

if (-not $Apply) {
    throw 'This script changes ACLs only with -Apply. Run the read-only host audit first.'
}
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [System.Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this script from an elevated PowerShell session.'
}
$windowsVersion = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion'
if ($windowsVersion.EditionID -notlike '*Enterprise*' -or [int]$windowsVersion.CurrentBuild -ne 19045 -or [int]$windowsVersion.UBR -lt 7807) {
    throw "Windows 10 Enterprise 22H2 must be at least build 19045.7807 (2026-10 ESU baseline) before provisioning (observed $($windowsVersion.EditionID) $($windowsVersion.CurrentBuild).$($windowsVersion.UBR))."
}

$science = Assert-SafeDirectory $ScienceCheckout 'ScienceCheckout'
$runner = Assert-SafeDirectory $RunnerCheckout 'RunnerCheckout'
$pythonEnv = Assert-SafeDirectory $PythonEnvironment 'PythonEnvironment'
$pythonBase = Assert-SafeDirectory $PythonBase 'PythonBase'
$evidence = Assert-SafeFutureDirectory $EvidenceRoot 'EvidenceRoot'
$temporary = Assert-SafeFutureDirectory $TemporaryRoot 'TemporaryRoot'
$archiveRequests = Assert-SafeFutureDirectory $ArchiveRequestRoot 'ArchiveRequestRoot'
$archive = Assert-SafeFutureDirectory $ArchiveRoot 'ArchiveRoot'
$ownerDecisions = Assert-SafeFutureDirectory $OwnerDecisionRoot 'OwnerDecisionRoot'
$newRoots = @($evidence, $temporary, $archiveRequests, $archive, $ownerDecisions)
for ($left = 0; $left -lt $newRoots.Count; $left++) {
    for ($right = $left + 1; $right -lt $newRoots.Count; $right++) {
        if (Test-PathOverlap $newRoots[$left] $newRoots[$right]) {
            throw 'Evidence, temporary, request, archive and Owner-decision roots cannot overlap or contain one another.'
        }
    }
}
$protectedRoots = @($science, $runner, $pythonEnv, $pythonBase)
for ($left = 0; $left -lt $protectedRoots.Count; $left++) {
    for ($right = $left + 1; $right -lt $protectedRoots.Count; $right++) {
        if (Test-PathOverlap $protectedRoots[$left] $protectedRoots[$right]) {
            throw 'Scientific checkout, runner checkout and Python environment must be disjoint.'
        }
    }
}
foreach ($newRoot in $newRoots) {
    foreach ($protectedRoot in @($science, $runner, $pythonEnv, $pythonBase)) {
        if (Test-PathOverlap $newRoot $protectedRoot) {
            throw "WP12 output roots must remain outside every read-only checkout and venv: $newRoot"
        }
    }
}
if (@($newRoots | ForEach-Object { [IO.Path]::GetPathRoot($_) } | Select-Object -Unique).Count -ne 1) {
    throw 'Evidence, temporary, request and archive roots must be on one approved local NTFS volume.'
}
if ((Get-Volume -DriveLetter $evidence.Substring(0, 1) -ErrorAction Stop).FileSystem -ne 'NTFS') {
    throw 'WP12 local isolation requires NTFS for the output volume.'
}
Assert-GitIdentity $science $ExpectedScienceCommit $ExpectedScienceTree
Assert-GitIdentity $runner $ExpectedRunnerCommit $ExpectedRunnerTree

if ($WhatIfPreference) {
    [pscustomobject]@{
        state = 'PLAN_ONLY_NO_CHANGES'
        runnerAccount = $RunnerAccount
        readOnlyRoots = @($science, $runner, $pythonEnv, $pythonBase)
        writableRoots = @($evidence, $temporary, $archiveRequests)
        ownerDecisionRoot = $ownerDecisions
        readOnlyArchiveRoot = $archive
        expectedScienceCommit = $ExpectedScienceCommit
        expectedScienceTree = $ExpectedScienceTree
        expectedRunnerCommit = $ExpectedRunnerCommit
        expectedRunnerTree = $ExpectedRunnerTree
        minimumWindowsBuild = '19045.7807'
        historicalArchivesWritten = $false
        trustStoreOrRegistryChanged = $false
    } | ConvertTo-Json -Depth 4
    return
}

$runnerAccountCreated = $false
$runnerAddedToUsers = $false
$account = Get-LocalUser -Name $RunnerAccount -ErrorAction SilentlyContinue
if (-not $account) {
    if (-not $CreateAccount) { throw "Account $RunnerAccount is absent; rerun with -CreateAccount after Owner review." }
    if (-not $PSCmdlet.ShouldProcess($RunnerAccount, 'Create standard local runner account')) {
        Write-Output "PLAN_ONLY: would create standard account $RunnerAccount; no changes made."
        return
    }
    $password = Read-Host "Choose a password for $RunnerAccount" -AsSecureString
    $account = New-LocalUser -Name $RunnerAccount -Password $password -Description 'Unprivileged QF Solver WP12 runner'
    $runnerAccountCreated = $true
}
$runnerSid = $account.SID.Value
$adminGroup = 'S-1-5-32-544'
$systemSid = 'S-1-5-18'
$usersGroup = Get-LocalGroup -SID 'S-1-5-32-545'
$ownerSid = $identity.User.Value
$adminGroupObject = Get-LocalGroup -SID $adminGroup
$adminSids = @(Get-LocalGroupMember -Group $adminGroupObject.Name | ForEach-Object { $_.SID.Value })
if ($adminSids -contains $runnerSid) { throw "Runner account $RunnerAccount must not be an administrator." }
if (-not $account.Enabled) { throw "Runner account $RunnerAccount exists but is disabled; resolve that explicitly before provisioning." }
$usersSids = @(Get-LocalGroupMember -Group $usersGroup.Name | ForEach-Object { $_.SID.Value })
if ($runnerSid -notin $usersSids -and $PSCmdlet.ShouldProcess($RunnerAccount, 'Add account to standard Users group')) {
    Add-LocalGroupMember -Group $usersGroup.Name -Member $RunnerAccount
    $runnerAddedToUsers = $true
}
$backupRoot = Join-Path $env:ProgramData ('QFSolverWP12\acl-backup-' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssffffZ') + '-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
& icacls.exe $backupRoot /inheritance:r /grant:r "*$adminGroup`:(OI)(CI)(F)" "*$systemSid`:(OI)(CI)(F)"
if ($LASTEXITCODE -ne 0) { throw 'Could not protect the ACL rollback directory.' }
$backupMap = @()
$index = 0
foreach ($candidate in @($science, $runner, $pythonEnv, $pythonBase)) {
    $index++
    $backupFile = Join-Path $backupRoot ("tree-{0}.acl" -f $index)
    & icacls.exe $candidate /save $backupFile /T /C
    if ($LASTEXITCODE -ne 0) { throw "Could not back up ACLs before changing $candidate" }
    $backupMap += [pscustomobject]@{ mode = 'ICACLS_TREE'; root = $candidate; file = $backupFile }
}
$ancestorCandidates = @($science, $runner, $pythonEnv, $pythonBase, $evidence, $temporary, $archiveRequests, $archive, $ownerDecisions) | ForEach-Object {
    $current = Split-Path -Parent $_
    while ($current -and $current -ne [IO.Path]::GetPathRoot($current)) {
        $current
        $next = Split-Path -Parent $current
        if ($next -eq $current) { break }
        $current = $next
    }
}
$coveredRoots = @($science, $runner, $pythonEnv, $pythonBase)
$ancestorPaths = @($ancestorCandidates | Sort-Object -Unique | Where-Object {
    $candidate = $_
    -not ($coveredRoots | Where-Object { $candidate.Equals($_, [StringComparison]::OrdinalIgnoreCase) })
})
foreach ($ancestor in $ancestorPaths) {
    $index++
    $backupFile = Join-Path $backupRoot ("ancestor-{0}.json" -f $index)
    $acl = Get-Acl -LiteralPath $ancestor
    $descriptor = $acl.GetSecurityDescriptorSddlForm([System.Security.AccessControl.AccessControlSections]::All)
    [pscustomobject]@{ sddl = $descriptor } | ConvertTo-Json -Compress | Set-Content -LiteralPath $backupFile -Encoding utf8
    $backupMap += [pscustomobject]@{ mode = 'ACL_SDDL'; root = $ancestor; file = $backupFile }
}
[pscustomobject]@{
    schema = 'qf-wp12-local-isolation-restore-map-v1'
    runnerAccount = $RunnerAccount
    runnerAccountCreated = $runnerAccountCreated
    runnerAddedToUsers = $runnerAddedToUsers
    createdOutputRoots = @($evidence, $temporary, $archiveRequests, $archive, $ownerDecisions)
    entries = $backupMap
} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $backupRoot 'restore-map.json') -Encoding utf8
foreach ($readOnlyRoot in @($science, $runner, $pythonEnv, $pythonBase)) {
    if ($PSCmdlet.ShouldProcess($readOnlyRoot, 'Apply protected read-only runner ACL')) {
        Set-ProtectedTreeAcl $readOnlyRoot $runnerSid $false
    }
}

$environmentContainer = Split-Path -Parent $pythonEnv
if ($PSCmdlet.ShouldProcess($environmentContainer, 'Grant runner traversal on the environment container only')) {
    Invoke-Icacls @($environmentContainer, '/grant:r', "*$runnerSid`:(X)")
}

$traversalTargets = @($science, $runner, $pythonEnv, $pythonBase, $evidence, $temporary, $archiveRequests, $archive, $ownerDecisions)
foreach ($target in $traversalTargets) {
    $parent = Split-Path -Parent $target
    while ($parent -and $parent -ne [IO.Path]::GetPathRoot($parent)) {
        if ($PSCmdlet.ShouldProcess($parent, 'Grant runner traverse-only on path ancestor')) {
            Invoke-Icacls @($parent, '/grant:r', "*$runnerSid`:(X)")
        }
        $next = Split-Path -Parent $parent
        if ($next -eq $parent) { break }
        $parent = $next
    }
}

$runnerWritableRoots = @($evidence, $temporary, $archiveRequests)
foreach ($writeRoot in $runnerWritableRoots) {
    if ($PSCmdlet.ShouldProcess($writeRoot, 'Create dedicated WP12 writable directory')) {
        New-Item -ItemType Directory -Path $writeRoot | Out-Null
    }
    $resolvedWriteRoot = Assert-SafeDirectory $writeRoot 'Writable root'
    if ($PSCmdlet.ShouldProcess($resolvedWriteRoot, 'Apply dedicated runner write ACL')) {
        Set-ProtectedTreeAcl $resolvedWriteRoot $runnerSid $true
    }
}

if ($PSCmdlet.ShouldProcess($archive, 'Create Owner/admin-controlled WP12 evidence archive')) {
    New-Item -ItemType Directory -Path $archive | Out-Null
}
if (-not (Test-Path -LiteralPath $archive)) { throw "Archive root was not created: $archive" }
$resolvedArchive = Assert-SafeDirectory $archive 'Archive root'
if ($PSCmdlet.ShouldProcess($resolvedArchive, 'Protect sealed archive from runner writes')) {
    Set-ProtectedTreeAcl $resolvedArchive $runnerSid $false
}

if ($PSCmdlet.ShouldProcess($ownerDecisions, 'Create Owner/admin-controlled signed-decision inbox')) {
    New-Item -ItemType Directory -Path $ownerDecisions | Out-Null
}
if (-not (Test-Path -LiteralPath $ownerDecisions)) { throw "Owner decision root was not created: $ownerDecisions" }
$resolvedOwnerDecisions = Assert-SafeDirectory $ownerDecisions 'Owner decision root'
if ($PSCmdlet.ShouldProcess($resolvedOwnerDecisions, 'Protect signed Owner decisions from runner writes')) {
    Set-ProtectedTreeAcl $resolvedOwnerDecisions $runnerSid $false
}

$effective = [pscustomobject]@{
    state = 'ACL_CONFIGURED_REQUIRES_INDEPENDENT_PROBE_AND_REVIEW'
    runnerAccountSid = $runnerSid
    readOnlyRoots = @($science, $runner, $pythonEnv, $pythonBase, $ownerDecisions)
    writableRoots = $runnerWritableRoots
    readOnlyArchiveRoot = $archive
    ownerDecisionRoot = $ownerDecisions
    historicalArchivesWritten = $false
    trustStoreConfigured = $false
    externalEvidenceAnchorConfigured = $false
}
$effective | ConvertTo-Json -Depth 4
