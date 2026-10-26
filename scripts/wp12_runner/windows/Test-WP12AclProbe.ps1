[CmdletBinding()]
param(
    [string] $ProbeRoot = (Join-Path $env:ProgramData ('QFSolverWP12\acl-probes\probe-' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssffffZ') + '-' + [guid]::NewGuid().ToString('N'))),
    [string] $RunnerAccount = 'QF_WP12_RUNNER',
    [switch] $Apply
)

$ErrorActionPreference = 'Stop'
if (-not $Apply) { throw 'The ACL probe creates synthetic files only when -Apply is supplied.' }
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [System.Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run the ACL probe from an elevated PowerShell session.'
}
if ($ProbeRoot -notmatch '^[A-Za-z]:[\\/]') { throw 'ProbeRoot must be an absolute path.' }
$root = [IO.Path]::GetFullPath($ProbeRoot)
$allowedRoot = [IO.Path]::GetFullPath((Join-Path $env:ProgramData 'QFSolverWP12\acl-probes')).TrimEnd('\') + '\'
if (-not $root.StartsWith($allowedRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'ProbeRoot must be a new child of the WP12 synthetic ACL probe directory under ProgramData.'
}
if (Test-Path -LiteralPath $root) { throw "Refusing to reuse an existing synthetic probe directory: $root" }
$runner = Get-LocalUser -Name $RunnerAccount -ErrorAction Stop
if (-not $runner.Enabled) { throw 'Runner account is disabled.' }
$runnerSid = $runner.SID.Value
$adminSid = 'S-1-5-32-544'
$systemSid = 'S-1-5-18'
$ownerSid = $identity.User.Value
$protected = Join-Path $root 'protected'
$evidence = Join-Path $root 'evidence'
$temporary = Join-Path $root 'temporary'
$requests = Join-Path $root 'requests'
$archive = Join-Path $root 'archive'
New-Item -ItemType Directory -Path $protected, $evidence, $temporary, $requests, $archive -Force | Out-Null
$sourceFile = Join-Path $protected 'source-fixture.txt'
$archiveFile = Join-Path $protected 'archive-fixture.txt'
$sealedArchiveFile = Join-Path $archive 'historical-receipt.txt'
Set-Content -LiteralPath $sourceFile -Value 'synthetic protected source' -Encoding ascii
Set-Content -LiteralPath $archiveFile -Value 'synthetic protected archive' -Encoding ascii
Set-Content -LiteralPath $sealedArchiveFile -Value 'synthetic sealed archive' -Encoding ascii

foreach ($target in @($root, $protected)) {
    & icacls.exe $target /inheritance:r /grant:r "*$ownerSid`:(OI)(CI)(F)" "*$adminSid`:(OI)(CI)(F)" "*$systemSid`:(OI)(CI)(F)" "*$runnerSid`:(X)"
    if ($LASTEXITCODE -ne 0) { throw "Could not protect synthetic directory $target" }
}
foreach ($target in @($evidence, $temporary)) {
    & icacls.exe $target /inheritance:r /grant:r "*$ownerSid`:(OI)(CI)(F)" "*$adminSid`:(OI)(CI)(F)" "*$systemSid`:(OI)(CI)(F)" "*$runnerSid`:(OI)(CI)(M)"
    if ($LASTEXITCODE -ne 0) { throw "Could not prepare synthetic writable directory $target" }
}
& icacls.exe $archive /inheritance:r /grant:r "*$ownerSid`:(OI)(CI)(F)" "*$adminSid`:(OI)(CI)(F)" "*$systemSid`:(OI)(CI)(F)" "*$runnerSid`:(OI)(CI)(RX)" /T /C
if ($LASTEXITCODE -ne 0) { throw 'Could not protect synthetic sealed archive.' }
& icacls.exe $requests /inheritance:r /grant:r "*$ownerSid`:(OI)(CI)(F)" "*$adminSid`:(OI)(CI)(F)" "*$systemSid`:(OI)(CI)(F)" "*$runnerSid`:(OI)(CI)(M)" /T /C
if ($LASTEXITCODE -ne 0) { throw 'Could not prepare the synthetic archive-request queue.' }

$payload = [pscustomobject]@{
    protectedFiles = @($sourceFile, $archiveFile, $sealedArchiveFile)
    evidenceFile = Join-Path $evidence 'runner-write.txt'
    temporaryFile = Join-Path $temporary 'runner-write.txt'
    requestFile = Join-Path $requests 'request.json'
} | ConvertTo-Json -Compress
$payload64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($payload))
$childCode = @"
`$data = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('$payload64')) | ConvertFrom-Json
`$denied = 0
foreach (`$path in `$data.protectedFiles) {
    try {
        `$null = [IO.File]::ReadAllText(`$path)
        `$stream = [IO.File]::Open(`$path, [IO.FileMode]::Open, [IO.FileAccess]::Write, [IO.FileShare]::ReadWrite)
        `$stream.Dispose()
        throw "WRITE_ALLOWED:`$path"
    }
    catch [UnauthorizedAccessException] { `$denied++ }
}
Set-Content -LiteralPath `$data.evidenceFile -Value 'synthetic evidence write' -Encoding ascii
Set-Content -LiteralPath `$data.temporaryFile -Value 'synthetic temporary write' -Encoding ascii
Set-Content -LiteralPath `$data.requestFile -Value 'synthetic archive request' -Encoding ascii
if (`$denied -ne 3) { exit 41 }
if (-not (Test-Path -LiteralPath `$data.evidenceFile) -or -not (Test-Path -LiteralPath `$data.temporaryFile) -or -not (Test-Path -LiteralPath `$data.requestFile)) { exit 42 }
'ACL_PROBE_PASS'
exit 0
"@
$encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($childCode))
$credential = Get-Credential -UserName ("{0}\{1}" -f $env:COMPUTERNAME, $RunnerAccount) -Message 'Credentials are used only for the synthetic ACL probe.'
$stdout = Join-Path $temporary 'runner-stdout.txt'
$stderr = Join-Path $temporary 'runner-stderr.txt'
$arguments = "-NoProfile -NonInteractive -EncodedCommand $encoded"
$process = Start-Process -FilePath "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -Credential $credential -LoadUserProfile -WindowStyle Hidden -ArgumentList $arguments -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru -Wait
$decodedPayload = $payload | ConvertFrom-Json
$result = [pscustomobject]@{
    state = if ($process.ExitCode -eq 0) { 'PASS_SYNTHETIC_ACL_PROBE' } else { 'FAIL_SYNTHETIC_ACL_PROBE' }
    exitCode = $process.ExitCode
    probeRoot = $root
    protectedPaths = @($sourceFile, $archiveFile)
    writablePaths = @($decodedPayload.evidenceFile, $decodedPayload.temporaryFile)
    requestPath = $decodedPayload.requestFile
    sealedArchivePath = $sealedArchiveFile
    stdout = if (Test-Path -LiteralPath $stdout) { Get-Content -LiteralPath $stdout -Raw } else { '' }
    stderr = if (Test-Path -LiteralPath $stderr) { Get-Content -LiteralPath $stderr -Raw } else { '' }
    historicalArchivesTouched = $false
}
$result | ConvertTo-Json -Depth 4
if ($process.ExitCode -ne 0) { exit 1 }
