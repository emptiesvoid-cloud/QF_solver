[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory)] [string] $BackupRoot,
    [switch] $Apply
)

$ErrorActionPreference = 'Stop'
if (-not $Apply) { throw 'No ACL changes occur without -Apply.' }
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [System.Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run rollback from an elevated PowerShell session.'
}
if ($BackupRoot -notmatch '^[A-Za-z]:[\\/]') { throw 'BackupRoot must be absolute.' }
$backup = [IO.Path]::GetFullPath($BackupRoot)
$expectedParent = [IO.Path]::GetFullPath((Join-Path $env:ProgramData 'QFSolverWP12'))
if (-not $backup.StartsWith($expectedParent.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'BackupRoot must be a child of ProgramData\QFSolverWP12.'
}
if (-not (Test-Path -LiteralPath $backup -PathType Container) -or
    (Get-Item -LiteralPath $backup -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
    throw 'BackupRoot is absent or is a reparse point.'
}
$mapPath = Join-Path $backup 'restore-map.json'
if (-not (Test-Path -LiteralPath $mapPath -PathType Leaf) -or
    (Get-Item -LiteralPath $mapPath -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
    throw 'Restore map is absent or is a reparse point.'
}
$map = Get-Content -LiteralPath $mapPath -Raw -Encoding utf8 | ConvertFrom-Json
if ($map.schema -ne 'qf-wp12-local-isolation-restore-map-v1' -or $map.entries -isnot [array]) {
    throw 'Unsupported WP12 isolation restore map.'
}
$entries = @($map.entries)
foreach ($entry in $entries) {
    $file = [IO.Path]::GetFullPath([string]$entry.file)
    if (-not $file.StartsWith($backup.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase) -or
        -not (Test-Path -LiteralPath $file -PathType Leaf)) {
        throw 'Restore entry points outside the protected backup or to a missing file.'
    }
    if (-not (Test-Path -LiteralPath ([string]$entry.root))) {
        throw "A path to restore no longer exists: $($entry.root)"
    }
    if ($entry.mode -notin @('ICACLS_TREE', 'ACL_SDDL')) { throw "Unsupported restore mode: $($entry.mode)" }
    if ($entry.mode -eq 'ACL_SDDL') {
        $document = Get-Content -LiteralPath $file -Raw -Encoding utf8 | ConvertFrom-Json
        if (-not $document.sddl -or $document.sddl -notmatch '^O:') { throw "Invalid SDDL backup: $file" }
    }
}
if (-not $PSCmdlet.ShouldProcess($backup, 'Restore ACLs captured before WP12 local isolation')) { return }

foreach ($entry in @($entries | Where-Object mode -eq 'ICACLS_TREE')) {
    & icacls.exe ([string]$entry.root) /restore ([string]$entry.file) /C
    if ($LASTEXITCODE -ne 0) { throw "icacls failed to restore $($entry.root)." }
}
foreach ($entry in @($entries | Where-Object mode -eq 'ACL_SDDL' | Sort-Object -Property { ([string]$_.root).Length } -Descending)) {
    $acl = Get-Acl -LiteralPath ([string]$entry.root)
    $document = Get-Content -LiteralPath ([string]$entry.file) -Raw -Encoding utf8 | ConvertFrom-Json
    $acl.SetSecurityDescriptorSddlForm(
        [string]$document.sddl,
        [System.Security.AccessControl.AccessControlSections]::All
    )
    Set-Acl -LiteralPath ([string]$entry.root) -AclObject $acl
}

$runner = Get-LocalUser -Name ([string]$map.runnerAccount) -ErrorAction SilentlyContinue
$runnerSid = if ($runner) { $runner.SID.Value } else { $null }
$protectedRoots = @($map.createdOutputRoots | Where-Object { Test-Path -LiteralPath ([string]$_) })
foreach ($root in $protectedRoots) {
    $path = [IO.Path]::GetFullPath([string]$root)
    if ((Get-Item -LiteralPath $path -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw "Refusing to change rollback permissions through a reparse point: $path"
    }
    if ($runnerSid) {
        & icacls.exe $path /inheritance:r /grant:r "*S-1-5-32-544`:(OI)(CI)(F)" "*S-1-5-18`:(OI)(CI)(F)" "*$runnerSid`:(OI)(CI)(RX)" /T /C
    }
    else {
        & icacls.exe $path /inheritance:r /grant:r "*S-1-5-32-544`:(OI)(CI)(F)" "*S-1-5-18`:(OI)(CI)(F)" /T /C
    }
    if ($LASTEXITCODE -ne 0) { throw "Could not seal preserved output root $path during rollback." }
}

$accountRemovedFromUsers = $false
if ($map.runnerAddedToUsers -and $runner) {
    $usersGroup = Get-LocalGroup -SID 'S-1-5-32-545'
    $members = @(Get-LocalGroupMember -Group $usersGroup.Name -ErrorAction SilentlyContinue | ForEach-Object { $_.SID.Value })
    if ($runner.SID.Value -in $members) {
        Remove-LocalGroupMember -Group $usersGroup.Name -Member ([string]$map.runnerAccount)
        $accountRemovedFromUsers = $true
    }
}
$accountDisabled = $false
if ($map.runnerAccountCreated) {
    $account = Get-LocalUser -Name ([string]$map.runnerAccount) -ErrorAction SilentlyContinue
    if ($account -and $account.Enabled) {
        Disable-LocalUser -Name ([string]$map.runnerAccount)
        $accountDisabled = $true
    }
}
$remainingRoots = @($map.createdOutputRoots | Where-Object { Test-Path -LiteralPath ([string]$_) })
[pscustomobject]@{
    state = 'ACL_RESTORED_OUTPUT_ROOTS_PRESERVED'
    backupRoot = $backup
    restoredEntries = $entries.Count
    runnerAccountDisabled = $accountDisabled
    runnerAccountRemovedFromUsersGroup = $accountRemovedFromUsers
    outputRootsPreserved = $remainingRoots
    historicalArchiveContentsModified = $false
} | ConvertTo-Json -Depth 4
