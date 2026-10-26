[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory)] [string] $PublicTrustStoreSource,
    [Parameter(Mandatory)] [string] $ExpectedSha256,
    [string] $RunnerAccount = 'QF_WP12_RUNNER',
    [switch] $Apply
)

$ErrorActionPreference = 'Stop'

function Get-Sha256([string] $Path) {
    $algorithm = [Security.Cryptography.SHA256]::Create()
    $stream = [IO.File]::OpenRead($Path)
    try { return [BitConverter]::ToString($algorithm.ComputeHash($stream)).Replace('-', '').ToLowerInvariant() }
    finally { $stream.Dispose(); $algorithm.Dispose() }
}

if (-not $Apply) { throw 'This script writes a public trust store and HKLM pins only with -Apply.' }
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [System.Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this script from an elevated PowerShell session.'
}
if ($PublicTrustStoreSource -notmatch '^[A-Za-z]:[\\/]') { throw 'PublicTrustStoreSource must be absolute.' }
if ($ExpectedSha256 -cnotmatch '^[a-f0-9]{64}$') { throw 'ExpectedSha256 must be a lowercase SHA-256 digest.' }
$source = (Resolve-Path -LiteralPath $PublicTrustStoreSource).Path
$sourceItem = Get-Item -LiteralPath $source -Force
if ($sourceItem.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Public trust store source cannot be a symlink or junction.' }
$sourceHash = Get-Sha256 $source
if ($sourceHash -cne $ExpectedSha256) { throw 'Public trust store bytes do not match ExpectedSha256.' }
$trustDocument = Get-Content -LiteralPath $source -Raw -Encoding utf8 | ConvertFrom-Json
if ($trustDocument.schema -ne 'qf-wp12-owner-trust-store-v1' -or @($trustDocument.keys).Count -lt 1) {
    throw 'Public trust store schema or keys array is invalid.'
}
foreach ($entry in $trustDocument.keys) {
    $rawKey = [Convert]::FromBase64String([string]$entry.public_key_base64)
    if ($rawKey.Length -ne 32 -or -not $entry.key_id -or -not $entry.principal -or $entry.revoked -isnot [bool]) {
        throw 'Every trust-store entry must have a key ID, principal, 32-byte Ed25519 public key, and revoked Boolean.'
    }
}
$runner = Get-LocalUser -Name $RunnerAccount -ErrorAction Stop
if (-not $runner.Enabled) { throw 'Runner account is disabled.' }
$runnerSid = $runner.SID.Value
$adminSid = 'S-1-5-32-544'
$systemSid = 'S-1-5-18'
$trustContainer = Join-Path $env:ProgramData 'QFSolverWP12'
$trustDirectory = Join-Path $trustContainer 'trust'
$trustPath = Join-Path $trustDirectory 'owner-trust-store.json'
if (Test-Path -LiteralPath $trustPath) { throw "Refusing to replace existing pinned trust store: $trustPath" }
if (-not (Test-Path -LiteralPath $trustContainer)) {
    if ($PSCmdlet.ShouldProcess($trustContainer, 'Create machine-protected WP12 configuration directory')) {
        New-Item -ItemType Directory -Path $trustContainer | Out-Null
    }
}
if (-not (Test-Path -LiteralPath $trustContainer)) { throw 'WP12 configuration directory was not created.' }
if ($PSCmdlet.ShouldProcess($trustContainer, 'Grant runner traverse-only on WP12 configuration directory')) {
    & icacls.exe $trustContainer /inheritance:r /grant:r "*$adminSid`:(OI)(CI)(F)" "*$systemSid`:(OI)(CI)(F)" "*$runnerSid`:(X)"
    if ($LASTEXITCODE -ne 0) { throw 'Could not protect the WP12 configuration directory.' }
}
if (-not (Test-Path -LiteralPath $trustDirectory)) {
    if ($PSCmdlet.ShouldProcess($trustDirectory, 'Create machine-protected Owner trust-store directory')) {
        New-Item -ItemType Directory -Path $trustDirectory -Force | Out-Null
    }
}
if (-not (Test-Path -LiteralPath $trustDirectory)) { throw 'Trust-store directory was not created.' }
if ($PSCmdlet.ShouldProcess($trustDirectory, 'Set public trust-store directory ACL')) {
    & icacls.exe $trustDirectory /inheritance:r /grant:r "*$adminSid`:(OI)(CI)(F)" "*$systemSid`:(OI)(CI)(F)" "*$runnerSid`:(OI)(CI)(RX)"
    if ($LASTEXITCODE -ne 0) { throw 'Could not set trust-store directory ACL.' }
}
$registryPath = 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Environment'
$registryKey = 'HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment'
$existingPath = Get-ItemPropertyValue -Path $registryPath -Name 'QF_WP12_TRUST_STORE' -ErrorAction SilentlyContinue
$existingPin = Get-ItemPropertyValue -Path $registryPath -Name 'QF_WP12_TRUST_STORE_SHA256' -ErrorAction SilentlyContinue
if ($existingPath -or $existingPin) { throw 'A machine trust-store pin already exists; refuse to replace it automatically.' }
if ($PSCmdlet.ShouldProcess($trustPath, 'Install immutable public trust-store bytes')) {
    Copy-Item -LiteralPath $source -Destination $trustPath
}
if ((Get-Sha256 $trustPath) -cne $ExpectedSha256) {
    throw 'Copied public trust-store SHA-256 does not match the expected value.'
}
if ($PSCmdlet.ShouldProcess($registryKey, 'Pin the Owner trust store in HKLM')) {
    New-ItemProperty -Path $registryPath -Name 'QF_WP12_TRUST_STORE' -Value $trustPath -PropertyType String | Out-Null
    New-ItemProperty -Path $registryPath -Name 'QF_WP12_TRUST_STORE_SHA256' -Value $ExpectedSha256 -PropertyType String | Out-Null
}
[pscustomobject]@{
    state = 'TRUST_STORE_PINNED_REQUIRES_RUNNER_ACCOUNT_VERIFICATION'
    publicTrustStorePath = $trustPath
    sha256 = $ExpectedSha256
    keyIds = @($trustDocument.keys | ForEach-Object { $_.key_id })
    privateKeyReadOrCreated = $false
    signedDecisionCreated = $false
} | ConvertTo-Json -Depth 4
