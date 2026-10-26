[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory)] [string] $RequestRoot,
    [Parameter(Mandatory)] [string] $EvidenceRoot,
    [Parameter(Mandatory)] [string] $ArchiveRoot,
    [Parameter(Mandatory)] [string] $OwnerDecisionRoot,
    [Parameter(Mandatory)] [string] $PythonExecutable,
    [Parameter(Mandatory)] [string] $ManifestPath,
    [string] $RunnerAccount = 'QF_WP12_RUNNER',
    [switch] $Apply
)

$ErrorActionPreference = 'Stop'
$taskPath = '\QFSolverWP12\'
$taskName = 'ArchiveWorker'
$workerScript = Join-Path $PSScriptRoot 'Invoke-WP12EvidenceArchiveWorker.ps1'

function Resolve-OrdinaryDirectory([string] $Value, [string] $Label) {
    if ($Value -notmatch '^[A-Za-z]:[\\/]') { throw "$Label must be absolute" }
    $resolved = [IO.Path]::GetFullPath($Value)
    if (-not (Test-Path -LiteralPath $resolved -PathType Container)) { throw "$Label is absent: $resolved" }
    $current = [IO.Path]::GetPathRoot($resolved)
    $relative = $resolved.Substring($current.Length)
    foreach ($part in $relative.Split([IO.Path]::DirectorySeparatorChar, [StringSplitOptions]::RemoveEmptyEntries)) {
        $current = Join-Path $current $part
        if ((Get-Item -LiteralPath $current -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw "$Label has a reparse-point component: $current"
        }
    }
    return $resolved
}

function Test-PathOverlap([string] $Left, [string] $Right) {
    $leftFull = $Left.TrimEnd('\')
    $rightFull = $Right.TrimEnd('\')
    return $leftFull.Equals($rightFull, [StringComparison]::OrdinalIgnoreCase) -or
        $leftFull.StartsWith($rightFull + '\', [StringComparison]::OrdinalIgnoreCase) -or
        $rightFull.StartsWith($leftFull + '\', [StringComparison]::OrdinalIgnoreCase)
}

function Get-Sha256([string] $Path) {
    $algorithm = [Security.Cryptography.SHA256]::Create()
    $stream = [IO.File]::OpenRead($Path)
    try { return [BitConverter]::ToString($algorithm.ComputeHash($stream)).Replace('-', '').ToLowerInvariant() }
    finally { $stream.Dispose(); $algorithm.Dispose() }
}

if (-not $Apply) { throw 'No Task Scheduler changes occur without -Apply.' }
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [System.Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this command from an elevated PowerShell session after Owner approval.'
}
if (-not (Test-Path -LiteralPath $workerScript -PathType Leaf)) { throw "Archive worker script is absent: $workerScript" }
$request = Resolve-OrdinaryDirectory $RequestRoot 'RequestRoot'
$evidence = Resolve-OrdinaryDirectory $EvidenceRoot 'EvidenceRoot'
$archive = Resolve-OrdinaryDirectory $ArchiveRoot 'ArchiveRoot'
$ownerDecisions = Resolve-OrdinaryDirectory $OwnerDecisionRoot 'OwnerDecisionRoot'
$runnerRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
$python = [IO.Path]::GetFullPath($PythonExecutable)
if ($python -notmatch '^[A-Za-z]:\\' -or -not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'PythonExecutable must be an existing absolute local path.'
}
if ((Get-Item -LiteralPath $python -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
    throw 'PythonExecutable cannot be a reparse point.'
}
$verifierScript = Join-Path $runnerRoot 'scripts\wp12_runner\owner_decision_verifier.py'
$manifestPath = [IO.Path]::GetFullPath($ManifestPath)
if (-not (Test-Path -LiteralPath $verifierScript -PathType Leaf) -or -not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
    throw 'The pinned owner-decision verifier or protected execution manifest is absent.'
}

$verifierPath = [IO.Path]::GetFullPath($verifierScript)
if ((Get-Item -LiteralPath $manifestPath -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
    throw 'The protected execution manifest cannot be a reparse point.'
}
if (-not $manifestPath.StartsWith($ownerDecisions.TrimEnd([char]92) + [char]92 + 'WP12-1-PILOT-001' + [char]92, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'ManifestPath must be inside the protected Owner decision root and campaign directory.'
}
$manifestDirectory = Resolve-OrdinaryDirectory (Split-Path -Parent $manifestPath) 'ManifestDirectory'
if (-not $manifestDirectory.Equals((Split-Path -Parent $manifestPath), [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Manifest parent path is not canonical.'
}
$manifestPath = [IO.Path]::GetFullPath($manifestPath)
$pythonSha256 = Get-Sha256 $python
$verifierSha256 = Get-Sha256 $verifierPath
$contractsSha256 = Get-Sha256 (Join-Path $runnerRoot 'scripts\wp12_runner\contracts.py')
$ownerTrustSha256 = Get-Sha256 (Join-Path $runnerRoot 'scripts\wp12_runner\owner_trust.py')
$canonicalizationSha256 = Get-Sha256 (Join-Path $runnerRoot 'scripts\wp12_owner_canonicalization.py')
$workerSha256 = Get-Sha256 $workerScript
$manifestSha256 = Get-Sha256 $manifestPath
$manifestObject = Get-Content -LiteralPath $manifestPath -Raw -Encoding utf8 | ConvertFrom-Json
$archivePin = $manifestObject.execution_context.archive
if (-not $archivePin -or $archivePin.execution_attestation -ne 'NONE') {
    throw 'No child-process attestation is implemented; only execution_attestation=NONE may be installed, and it cannot authorize scientific EXECUTE.'
}
if ([IO.Path]::GetFullPath([string]$archivePin.manifest_path) -ne $manifestPath) {
    throw 'Manifest path differs from the protected path declared inside the manifest.'
}
if ($manifestObject.campaign_id -ne 'WP12-1-PILOT-001' -or $manifestObject.status -ne 'FROZEN_NOT_AUTHORIZED') {
    throw 'Only the frozen, non-authorized WP12-1 pilot manifest may be installed.'
}
if ($archivePin.status -ne 'CONFIGURED') {
    throw 'The manifest does not record a configured independent evidence archive.'
}
foreach ($pair in @(
    @{ field = 'python_executable_sha256'; actual = $pythonSha256 },
    @{ field = 'decision_verifier_script_sha256'; actual = $verifierSha256 },
    @{ field = 'contracts_script_sha256'; actual = $contractsSha256 },
    @{ field = 'owner_trust_script_sha256'; actual = $ownerTrustSha256 },
    @{ field = 'canonicalization_script_sha256'; actual = $canonicalizationSha256 },
    @{ field = 'worker_script_sha256'; actual = $workerSha256 }
)) {
    if ($archivePin.($pair.field) -ne $pair.actual) { throw "Manifest archive pin differs for $($pair.field)." }
}
$runner = Get-LocalUser -Name $RunnerAccount -ErrorAction Stop
if (-not $runner.Enabled) { throw 'The dedicated runner account must be enabled.' }
$adminSids = @(Get-LocalGroupMember -Group (Get-LocalGroup -SID 'S-1-5-32-544').Name | ForEach-Object { $_.SID.Value })
if ($adminSids -contains $runner.SID.Value) { throw 'The dedicated runner account must not be an administrator.' }
foreach ($path in @($request, $evidence, $archive, $ownerDecisions)) {
    if (Test-PathOverlap $path $runnerRoot) { throw 'Archive roots must remain outside the runner checkout.' }
}
$roots = @($request, $evidence, $archive, $ownerDecisions)
for ($left = 0; $left -lt $roots.Count; $left++) {
    for ($right = $left + 1; $right -lt $roots.Count; $right++) {
        if (Test-PathOverlap $roots[$left] $roots[$right]) { throw 'Request, evidence and archive roots cannot overlap or contain one another.' }
    }
}
if (@($roots | ForEach-Object { [IO.Path]::GetPathRoot($_) } | Select-Object -Unique).Count -ne 1) {
    throw 'Request, evidence and archive roots must share one local NTFS volume.'
}
$volume = Get-Volume -DriveLetter $archive.Substring(0, 1) -ErrorAction Stop
if ($volume.FileSystem -ne 'NTFS' -or $volume.DriveType -ne 'Fixed') { throw 'The sealed archive must be on a local fixed NTFS volume.' }
if (Get-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction SilentlyContinue) {
    throw "Refusing to overwrite existing scheduled task $taskPath$taskName. Inspect it explicitly first."
}
$powershell = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$runnerSid = $runner.SID.Value
$arguments = @(
    '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'RemoteSigned', '-File', ('"' + $workerScript + '"'),
    '-RequestRoot', ('"' + $request + '"'), '-EvidenceRoot', ('"' + $evidence + '"'),
    '-ArchiveRoot', ('"' + $archive + '"'), '-OwnerDecisionRoot', ('"' + $ownerDecisions + '"'),
    '-PythonExecutable', ('"' + $python + '"'), '-PythonExecutableSha256', $pythonSha256,
    '-VerifierScriptSha256', $verifierSha256,
    '-ContractsScriptSha256', $contractsSha256, '-OwnerTrustScriptSha256', $ownerTrustSha256,
    '-CanonicalizationScriptSha256', $canonicalizationSha256, '-WorkerScriptSha256', $workerSha256,
    '-ManifestPath', ('"' + $manifestPath + '"'), '-ManifestSha256', $manifestSha256,
    '-RunnerSid', $runnerSid, '-Watch'
) -join ' '
$action = New-ScheduledTaskAction -Execute $powershell -Argument $arguments
$trigger = New-ScheduledTaskTrigger -AtStartup
$taskPrincipal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
if ($PSCmdlet.ShouldProcess("$taskPath$taskName", 'Register and start the WP12 sealed evidence archive worker as SYSTEM')) {
    Register-ScheduledTask -TaskPath $taskPath -TaskName $taskName -Action $action -Trigger $trigger -Principal $taskPrincipal -Settings $settings -Description 'Copies verified WP12 evidence requests to the administrator-controlled archive.' | Out-Null
    Start-ScheduledTask -TaskPath $taskPath -TaskName $taskName
}
$task = Get-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction Stop
[pscustomobject]@{
    taskPath = "$taskPath$taskName"
    state = $task.State.ToString()
    principal = $task.Principal.UserId
    workerScript = $workerScript
    workerScriptSha256 = Get-Sha256 $workerScript
    requestRoot = $request
    evidenceRoot = $evidence
    archiveRoot = $archive
    ownerDecisionRoot = $ownerDecisions
    pythonExecutable = $python
    pythonExecutableSha256 = $pythonSha256
    verifierScript = $verifierPath
    verifierScriptSha256 = $verifierSha256
    contractsScriptSha256 = $contractsSha256
    ownerTrustScriptSha256 = $ownerTrustSha256
    canonicalizationScriptSha256 = $canonicalizationSha256
    manifestSha256 = $manifestSha256
    executionAttestation = $archivePin.execution_attestation
    manifestPath = $manifestPath
    changesApplied = $true
    historicalArchivesModified = $false
} | ConvertTo-Json -Depth 4
