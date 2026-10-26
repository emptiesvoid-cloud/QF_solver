[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string] $RequestRoot,
    [Parameter(Mandatory)] [string] $EvidenceRoot,
    [Parameter(Mandatory)] [string] $ArchiveRoot,
    [Parameter(Mandatory)] [string] $OwnerDecisionRoot,
    [Parameter(Mandatory)] [string] $PythonExecutable,
    [Parameter(Mandatory)] [string] $PythonExecutableSha256,
    [Parameter(Mandatory)] [string] $VerifierScriptSha256,
    [Parameter(Mandatory)] [string] $ContractsScriptSha256,
    [Parameter(Mandatory)] [string] $OwnerTrustScriptSha256,
    [Parameter(Mandatory)] [string] $CanonicalizationScriptSha256,
    [Parameter(Mandatory)] [string] $WorkerScriptSha256,
    [Parameter(Mandatory)] [string] $ManifestPath,
    [Parameter(Mandatory)] [string] $ManifestSha256,
    [Parameter(Mandatory)] [string] $RunnerSid,
    [switch] $Watch
)

$ErrorActionPreference = 'Stop'

Add-Type -TypeDefinition @'
using System;
using System.Text;
using Microsoft.Win32.SafeHandles;
using System.Runtime.InteropServices;

public static class WP12DirectoryLock {
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern SafeFileHandle CreateFileW(string name, uint access, uint share, IntPtr security, uint creation, uint flags, IntPtr template);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern uint GetFinalPathNameByHandleW(SafeFileHandle handle, StringBuilder path, uint length, uint flags);
    [StructLayout(LayoutKind.Sequential)]
    public struct FileInformation {
        public uint Attributes;
        public System.Runtime.InteropServices.ComTypes.FILETIME CreationTime;
        public System.Runtime.InteropServices.ComTypes.FILETIME LastAccessTime;
        public System.Runtime.InteropServices.ComTypes.FILETIME LastWriteTime;
        public uint VolumeSerialNumber;
        public uint FileSizeHigh;
        public uint FileSizeLow;
        public uint NumberOfLinks;
        public uint FileIndexHigh;
        public uint FileIndexLow;
    }
    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern bool GetFileInformationByHandle(SafeFileHandle handle, out FileInformation info);
}
'@

function Resolve-OrdinaryDirectory([string] $Value, [string] $Label) {
    if ($Value -notmatch '^[A-Za-z]:\\') { throw "$Label must be an absolute drive path" }
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
    return $resolved.TrimEnd('\')
}

function Get-Sha256([string] $Path) {
    $algorithm = [Security.Cryptography.SHA256]::Create()
    $stream = [IO.File]::OpenRead($Path)
    try { return [BitConverter]::ToString($algorithm.ComputeHash($stream)).Replace('-', '').ToLowerInvariant() }
    finally { $stream.Dispose(); $algorithm.Dispose() }
}

function Get-Sha256Bytes([byte[]] $Bytes) {
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($algorithm.ComputeHash($Bytes)).Replace('-', '').ToLowerInvariant() }
    finally { $algorithm.Dispose() }
}

function Quote-ProcessArgument([string] $Value) {
    if ($Value.Contains('"')) { throw 'A process argument contains a forbidden quote character.' }
    return '"' + $Value + '"'
}

function Test-OwnerDecisionAuthorization([object] $Request) {
    foreach ($identifier in @($Request.campaign_id, $Request.decision_id, $Request.unit_id)) {
        if ($identifier -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$') { throw 'Owner decision request identity is malformed.' }
    }
    $campaignDirectory = Join-Path $script:OwnerDecisionRoot ([string]$Request.campaign_id)
    if (-not (Test-Path -LiteralPath $campaignDirectory -PathType Container)) { throw 'Protected Owner decision campaign directory is absent.' }
    $decisionPath = Join-Path $campaignDirectory ([string]$Request.decision_id + '.json')
    if (-not (Test-Path -LiteralPath $decisionPath -PathType Leaf)) { throw 'Protected Owner decision file is absent.' }
    foreach ($candidate in @($script:OwnerDecisionRoot, $campaignDirectory, $decisionPath)) {
        if ((Get-Item -LiteralPath $candidate -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw 'Owner decision path contains a reparse point.'
        }
    }
    $resolvedDecision = [IO.Path]::GetFullPath($decisionPath)
    if (-not $resolvedDecision.StartsWith($script:OwnerDecisionRoot.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Owner decision path escapes its protected root.'
    }
    if ((Get-Sha256 $resolvedDecision) -ne $Request.owner_decision_sha256) { throw 'Protected Owner decision digest differs from the reservation request.' }
    $manifestPath = $script:ManifestPath
    if ($request.manifest_sha256 -ne $script:ManifestSha256 -or
        (Get-Sha256 $manifestPath) -ne $script:ManifestSha256) {
        throw 'Protected execution manifest digest differs from the installed pin or Owner request.'
    }
    $verifier = Join-Path $script:RunnerRoot 'scripts\wp12_runner\owner_decision_verifier.py'
    if ((Get-Sha256 $verifier) -ne $script:VerifierScriptSha256) { throw 'Owner decision verifier script hash differs from the installed task pin.' }
    if ((Get-Sha256 $script:PythonExecutable) -ne $script:PythonExecutableSha256) { throw 'Pinned Python executable hash differs from the installed task pin.' }

    # Keep the decision file open without write/delete sharing during the
    # signature and binding check. The protected OwnerDecisionRoot ACL is the
    # primary write boundary; this handle also closes the ordinary race window.
    $decisionLock = [IO.File]::Open($resolvedDecision, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
    try {
        $arguments = @(
            '-I', '-B', (Quote-ProcessArgument $verifier),
            '--runner-root', (Quote-ProcessArgument $script:RunnerRoot),
            '--decision-path', (Quote-ProcessArgument $resolvedDecision),
            '--manifest-path', (Quote-ProcessArgument $manifestPath),
            '--campaign-id', ([string]$Request.campaign_id),
            '--decision-id', ([string]$Request.decision_id),
            '--unit-id', ([string]$Request.unit_id),
            '--run-id', ([string]$Request.run_id),
            '--manifest-sha256', ([string]$Request.manifest_sha256),
            '--nodeid', ([string]$Request.nodeid),
            '--attempt-number', ([string]$Request.attempt),
            '--destination', ([string]$Request.destination),
            '--scientific-commit', ([string]$Request.identities.scientific_commit),
            '--scientific-tree', ([string]$Request.identities.scientific_tree),
            '--runner-commit', ([string]$Request.identities.runner_commit),
            '--runner-tree', ([string]$Request.identities.runner_tree)
        )
        $start = [Diagnostics.ProcessStartInfo]::new()
        $start.FileName = $script:PythonExecutable
        $start.Arguments = $arguments -join ' '
        $start.WorkingDirectory = $script:RunnerRoot
        $start.UseShellExecute = $false
        $start.CreateNoWindow = $true
        $start.RedirectStandardOutput = $true
        $start.RedirectStandardError = $true
        $process = [Diagnostics.Process]::new()
        $process.StartInfo = $start
        try {
            if (-not $process.Start()) { throw 'Owner decision verifier process did not start.' }
            if (-not $process.WaitForExit(30000)) {
                try { $process.Kill() } catch {}
                throw 'Owner decision verifier timed out.'
            }
            $stdout = $process.StandardOutput.ReadToEnd()
            $stderr = $process.StandardError.ReadToEnd()
            if ($process.ExitCode -ne 0) { throw ('Owner decision signature or binding verification failed: ' + $stderr.Trim()) }
            $report = $stdout | ConvertFrom-Json
            foreach ($field in @('decision_sha256', 'manifest_sha256', 'campaign_id', 'unit_id', 'run_id', 'nodeid', 'destination')) {
                $expected = if ($field -eq 'decision_sha256') { $Request.owner_decision_sha256 } else { $Request.$field }
                if ($report.$field -ne $expected) { throw "Owner verifier report differs for $field." }
            }
            if ($report.scientific_identity.commit -ne $Request.identities.scientific_commit -or
                $report.scientific_identity.git_tree -ne $Request.identities.scientific_tree -or
                $report.runner_identity.commit -ne $Request.identities.runner_commit -or
                $report.runner_identity.git_tree -ne $Request.identities.runner_tree) {
                throw 'Owner verifier report Git identities differ from the reservation request.'
            }
            if ($report.authenticated -ne $true) { throw 'Owner verifier did not authenticate the decision.' }
            return $report
        }
        finally { $process.Dispose() }
    }
    finally { $decisionLock.Dispose() }
}

function Open-LockedOrdinaryDirectory([string] $Path, [string] $ExpectedPath) {
    # Keep this handle open through sealing and copy. Sharing read only prevents
    # new write/delete opens on the directory; failure is fail-closed.
    $handle = [WP12DirectoryLock]::CreateFileW($Path, 0x00000001 -bor 0x00000080, 0x00000001, [IntPtr]::Zero, 3, 0x02200000, [IntPtr]::Zero)
    if ($handle.IsInvalid) { $code = [Runtime.InteropServices.Marshal]::GetLastWin32Error(); $handle.Dispose(); throw "Could not lock the evidence directory (Win32 $code)." }
    $buffer = [Text.StringBuilder]::new(32768)
    $length = [WP12DirectoryLock]::GetFinalPathNameByHandleW($handle, $buffer, [uint32]$buffer.Capacity, 0)
    if ($length -eq 0 -or $length -ge $buffer.Capacity) { $handle.Dispose(); throw 'Could not resolve the locked evidence directory handle.' }
    $final = $buffer.ToString() -replace '^\\\\\?\\', ''
    $expected = [IO.Path]::GetFullPath($ExpectedPath).TrimEnd('\')
    if (-not $final.TrimEnd('\').Equals($expected, [StringComparison]::OrdinalIgnoreCase)) { $handle.Dispose(); throw 'Locked evidence directory identity differs from the configured destination.' }
    $information = [WP12DirectoryLock+FileInformation]::new()
    if (-not [WP12DirectoryLock]::GetFileInformationByHandle($handle, [ref]$information) -or ($information.Attributes -band 0x400)) {
        $handle.Dispose(); throw 'Locked evidence directory is a reparse point or its attributes are unavailable.'
    }
    return $handle
}

function Read-LockedRequest([string] $Path) {
    $handle = [WP12DirectoryLock]::CreateFileW($Path, 0x00000001 -bor 0x00000080, 0x00000001, [IntPtr]::Zero, 3, 0x00200000, [IntPtr]::Zero)
    if ($handle.IsInvalid) { $code = [Runtime.InteropServices.Marshal]::GetLastWin32Error(); $handle.Dispose(); throw "Could not safely open request (Win32 $code)." }
    try {
        $information = [WP12DirectoryLock+FileInformation]::new()
        if (-not [WP12DirectoryLock]::GetFileInformationByHandle($handle, [ref]$information) -or
            ($information.Attributes -band 0x400) -or [long]$information.FileSizeHigh * 4294967296 + $information.FileSizeLow -gt 1048576) {
            throw 'Request is a reparse point, too large, or its attributes are unavailable.'
        }
        $buffer = [Text.StringBuilder]::new(32768)
        $length = [WP12DirectoryLock]::GetFinalPathNameByHandleW($handle, $buffer, [uint32]$buffer.Capacity, 0)
        if ($length -eq 0 -or $length -ge $buffer.Capacity) { throw 'Could not resolve the request file handle.' }
        $final = ($buffer.ToString() -replace '^\\\\\?\\', '').TrimEnd('\')
        if (-not $final.StartsWith($script:RequestRoot.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) {
            throw 'Request file handle resolves outside the configured request root.'
        }
        $stream = [IO.FileStream]::new($handle, [IO.FileAccess]::Read)
        try {
            $memory = [IO.MemoryStream]::new()
            try { $stream.CopyTo($memory); return ,$memory.ToArray() }
            finally { $memory.Dispose() }
        }
        finally { $stream.Dispose() }
    }
    finally { if (-not $handle.IsClosed) { $handle.Dispose() } }
}

function Write-SystemJsonCreateNew([string] $Path, [object] $Payload) {
    $bytes = [Text.Encoding]::UTF8.GetBytes(($Payload | ConvertTo-Json -Depth 8 -Compress) + [Environment]::NewLine)
    $temporary = Join-Path (Split-Path -Parent $Path) ('.' + [IO.Path]::GetFileName($Path) + '.' + [guid]::NewGuid().ToString('N') + '.tmp')
    $stream = [IO.File]::Open($temporary, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    try {
        $stream.Write($bytes, 0, $bytes.Length)
        $stream.Flush($true)
        $stream.Dispose()
        [IO.File]::Move($temporary, $Path)
    }
    finally {
        if ($stream) { $stream.Dispose() }
        if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Force }
    }
}

function Process-Reservation([string] $RequestPath) {
    $bytes = Read-LockedRequest $RequestPath
    $requestHash = Get-Sha256Bytes $bytes
    $request = [Text.Encoding]::UTF8.GetString($bytes) | ConvertFrom-Json
    if ($request.schema -ne 'qf-wp12-attempt-reservation-request-v1' -or $request.request_id -notmatch '^[A-Za-z0-9-]{36}$') { throw 'Attempt reservation request schema or ID is invalid.' }
    foreach ($identifier in @($request.campaign_id, $request.decision_id, $request.unit_id, $request.run_id)) {
        if ($identifier -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$') { throw 'Unsafe attempt reservation identifier.' }
    }
    foreach ($digest in @($request.reservation_key, $request.manifest_sha256, $request.owner_decision_sha256)) {
        if ($digest -notmatch '^[a-f0-9]{64}$') { throw 'Attempt reservation digest is malformed.' }
    }
    if ($request.campaign_id -ne 'WP12-1-PILOT-001' -or $request.unit_id -ne 'WP12-1-PILOT-001-UNIT-01' -or
        $request.attempt -ne 1 -or $request.maximum_attempts -ne 1 -or
        $request.nodeid -notmatch '^tests/unit/test_modal_symmetric_projection\.py::test_structured_symmetric_projection_matches_dense_bilinear_form$') {
        throw 'Only the frozen single-attempt WP12 pilot reservation is supported.'
    }
    if ($request.destination -ne 'qualification/0_2_12/wp12_evidence/WP12-1-PILOT-001/attempt-001' -or
        $request.run_id -ne 'attempt-001' -or $request.destination.Split('/')[-1] -ne $request.run_id) {
        throw 'Attempt reservation destination is not the frozen pilot directory.'
    }
    $canonical = [string]$request.campaign_id + "`n" + [string]$request.manifest_sha256 + "`n" + [string]$request.nodeid
    $calculatedKey = Get-Sha256Bytes ([Text.Encoding]::UTF8.GetBytes($canonical))
    if ($calculatedKey -ne $request.reservation_key) { throw 'Attempt reservation key does not match its canonical identity.' }
    $identities = $request.identities
    foreach ($identity in @($identities.scientific_commit, $identities.scientific_tree, $identities.runner_commit, $identities.runner_tree)) {
        if ($identity -notmatch '^[a-f0-9]{40}$') { throw 'Attempt reservation Git identity is incomplete.' }
    }
    $ownerVerification = Test-OwnerDecisionAuthorization $request
    if ($ownerVerification.authenticated -ne $true) { throw 'Owner decision was not authenticated.' }
    $ledgerRoot = Join-Path $script:ArchiveRoot '_wp12_ledger'
    $reservationDirectory = Join-Path $ledgerRoot 'reservations'
    $ackDirectory = Join-Path $ledgerRoot 'reservation-acks'
    foreach ($directory in @($ledgerRoot, $reservationDirectory, $ackDirectory)) {
        if (-not (Test-Path -LiteralPath $directory)) { New-Item -ItemType Directory -Path $directory | Out-Null }
        if ((Get-Item -LiteralPath $directory -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Protected attempt ledger path is a reparse point.' }
    }
    $reservationPath = Join-Path $reservationDirectory ($request.reservation_key + '.reserved.json')
    $ackPath = Join-Path $ackDirectory ($request.request_id + '.json')
    $status = 'RESERVED'
    $reservationRecord = [ordered]@{
        schema = 'qf-wp12-protected-attempt-reservation-v1'
        reservation_key = $request.reservation_key
        campaign_id = $request.campaign_id
        decision_id = $request.decision_id
        unit_id = $request.unit_id
        run_id = $request.run_id
        nodeid = $request.nodeid
        destination = $request.destination
        manifest_sha256 = $request.manifest_sha256
        owner_decision_sha256 = $request.owner_decision_sha256
        identities = $request.identities
        attempt = 1
        maximum_attempts = 1
        request_id = $request.request_id
        request_sha256 = $requestHash
        reserved_utc = [DateTime]::UtcNow.ToString('o')
        owner_authentication = 'ED25519_DECISION_VERIFIED_BY_PROTECTED_WORKER'
        result_assurance = 'NO_PROCESS_ATTESTATION'
        trust_note = 'SYSTEM verified the exact signed Owner decision against the HKLM-pinned trust store before reservation; this does not attest execution.'
    }
    try { Write-SystemJsonCreateNew $reservationPath $reservationRecord }
    catch [IO.IOException] {
        if (Test-Path -LiteralPath $reservationPath -PathType Leaf) { $status = 'REJECTED_ALREADY_RESERVED' }
        else { throw }
    }
    $ack = [ordered]@{
        schema = 'qf-wp12-attempt-reservation-ack-v1'
        request_id = $request.request_id
        request_sha256 = $requestHash
        reservation_key = $request.reservation_key
        decision_id = $request.decision_id
        unit_id = $request.unit_id
        destination = $request.destination
        owner_decision_sha256 = $request.owner_decision_sha256
        status = $status
        acknowledged_utc = [DateTime]::UtcNow.ToString('o')
    }
    Write-SystemJsonCreateNew $ackPath $ack
    return [pscustomobject]@{ state = $status; request = $RequestPath; reservation = $reservationPath; acknowledgement = $ackPath }
}

function Assert-NoReparseTree([string] $Root) {
    $pending = [Collections.Generic.Stack[string]]::new()
    $pending.Push($Root)
    while ($pending.Count -gt 0) {
        $directory = $pending.Pop()
        foreach ($item in Get-ChildItem -LiteralPath $directory -Force) {
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
                throw "Reparse point is not allowed in the evidence tree: $($item.FullName)"
            }
            if ($item.PSIsContainer) { $pending.Push($item.FullName) }
        }
    }
}

function Process-Request([string] $RequestPath) {
    $requestBytes = Read-LockedRequest $RequestPath
    $requestHash = Get-Sha256Bytes $requestBytes
    $request = [Text.Encoding]::UTF8.GetString($requestBytes) | ConvertFrom-Json
    if ($request.schema -ne 'qf-wp12-administrator-archive-request-v1') { throw 'Unsupported archive request schema.' }
    foreach ($identifier in @($request.campaign_id, $request.decision_id, $request.unit_id, $request.run_id)) {
        if ($identifier -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$') { throw 'Unsafe campaign or run identifier.' }
    }
    if ($request.campaign_id -ne 'WP12-1-PILOT-001') { throw 'Archive worker accepts only WP12-1-PILOT-001.' }
    if ($request.manifest_sha256 -notmatch '^[a-f0-9]{64}$' -or $request.owner_decision_sha256 -notmatch '^[a-f0-9]{64}$' -or
        $request.reservation_key -notmatch '^[a-f0-9]{64}$' -or $request.receipt_sha256 -notmatch '^[a-f0-9]{64}$') {
        throw 'Archive request has an invalid digest.'
    }
    if ($request.nodeid -notmatch '^tests/unit/test_modal_symmetric_projection\.py::test_structured_symmetric_projection_matches_dense_bilinear_form$') {
        throw 'Archive request nodeid is not the frozen WP12 pilot.'
    }
    if ($request.unit_id -ne 'WP12-1-PILOT-001-UNIT-01' -or
        $request.destination -ne 'qualification/0_2_12/wp12_evidence/WP12-1-PILOT-001/attempt-001' -or
        $request.run_id -ne 'attempt-001' -or $request.destination.Split('/')[-1] -ne $request.run_id) {
        throw 'Archive request unit or destination is not the frozen WP12 pilot.'
    }
    $ownerVerification = Test-OwnerDecisionAuthorization $request
    if ($ownerVerification.authenticated -ne $true) { throw 'Owner decision was not authenticated for this archive request.' }
    $reservationPath = Join-Path (Join-Path (Join-Path $script:ArchiveRoot '_wp12_ledger') 'reservations') ($request.reservation_key + '.reserved.json')
    if (-not (Test-Path -LiteralPath $reservationPath -PathType Leaf)) { throw 'Protected attempt reservation is absent.' }
    $reservation = Get-Content -LiteralPath $reservationPath -Raw | ConvertFrom-Json
    foreach ($field in @('reservation_key', 'campaign_id', 'decision_id', 'unit_id', 'run_id', 'nodeid', 'destination', 'manifest_sha256', 'owner_decision_sha256')) {
        if ($reservation.$field -ne $request.$field) { throw "Archive request differs from protected reservation field $field." }
    }
    if ($request.runner_status_claim -notin @('PASS', 'FAIL', 'INCONCLUSIVE', 'TIMEOUT', 'RESOURCE_LIMIT', 'INTERRUPTED', 'INFRA_ERROR') -or
        $request.claim_assurance -ne 'UNATTESTED_RUNNER_OUTPUT') {
        throw 'Archive request has an invalid or unattested runner-status claim.'
    }
    $campaignArchive = Join-Path $script:ArchiveRoot $request.campaign_id
    $ackPath = Join-Path $campaignArchive ($request.run_id + '.archive-ack.json')
    if (Test-Path -LiteralPath $ackPath) {
        $existingAck = Get-Content -LiteralPath $ackPath -Raw | ConvertFrom-Json
        if ($existingAck.request_sha256 -eq $requestHash -and
            $existingAck.campaign_id -eq $request.campaign_id -and
            $existingAck.decision_id -eq $request.decision_id -and
            $existingAck.unit_id -eq $request.unit_id -and
            $existingAck.run_id -eq $request.run_id -and
            $existingAck.destination -eq $request.destination -and
            $existingAck.manifest_sha256 -eq $request.manifest_sha256 -and
            $existingAck.receipt_sha256 -eq $request.receipt_sha256 -and
            $existingAck.reservation_key -eq $request.reservation_key -and
            $existingAck.nodeid -eq $request.nodeid -and
            $existingAck.owner_decision_sha256 -eq $request.owner_decision_sha256 -and
            $existingAck.runner_status_claim_unattested -eq $request.runner_status_claim -and
            $existingAck.status -eq 'ARCHIVED_BYTES_ONLY' -and
            $existingAck.archive_assurance -eq 'BYTE_INTEGRITY_ONLY_PROCESS_EXECUTION_NOT_ATTESTED' -and
            $existingAck.process_execution_attested -eq $false -and
            $existingAck.scientific_status_attested -eq $false) {
            return [pscustomobject]@{ state = 'ALREADY_ARCHIVED'; request = $RequestPath; acknowledgement = $ackPath; request_sha256 = $requestHash }
        }
        throw 'An existing archive acknowledgement conflicts with the submitted request.'
    }
    $source = [IO.Path]::GetFullPath([string]$request.source_run_directory).TrimEnd('\')
    $expectedSource = [IO.Path]::GetFullPath((Join-Path (Join-Path $script:EvidenceRoot $request.campaign_id) $request.run_id)).TrimEnd('\')
    if (-not $source.Equals($expectedSource, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Archive request source does not match the preconfigured evidence namespace.'
    }
    $sourceHandle = Open-LockedOrdinaryDirectory $source $expectedSource
    try {
    Assert-NoReparseTree $source
    & icacls.exe $source /inheritance:r /grant:r "*S-1-5-32-544`:(OI)(CI)(F)" "*S-1-5-18`:(OI)(CI)(F)" "*$script:RunnerSid`:(OI)(CI)(RX)" /T /C
    if ($LASTEXITCODE -ne 0) { throw 'Could not seal the source evidence tree before reading it.' }
    Assert-NoReparseTree $source
    $receiptPath = Join-Path $source 'receipt.json'
    $sidecarPath = Join-Path $source 'receipt.sha256'
    if ((Get-Sha256 $receiptPath) -ne $request.receipt_sha256) { throw 'Submitted receipt digest mismatch.' }
    if ((Get-Content -LiteralPath $sidecarPath -Raw).Trim() -ne "$($request.receipt_sha256)  receipt.json") {
        throw 'Submitted receipt sidecar mismatch.'
    }
    $receipt = Get-Content -LiteralPath $receiptPath -Raw | ConvertFrom-Json
    if ($receipt.schema -ne 'qf-solver-wp12-runner-receipt-v1' -or $receipt.artifacts -isnot [array]) {
        throw 'Submitted receipt structure is invalid.'
    }
    foreach ($field in @('campaign_id', 'decision_id', 'unit_id', 'run_id', 'nodeid', 'destination', 'reservation_key', 'manifest_sha256', 'owner_decision_sha256')) {
        if ($receipt.metadata.$field -ne $request.$field) { throw "Receipt metadata differs from archive request field $field." }
    }
    if ($receipt.metadata.scientific_status -ne 'INCONCLUSIVE' -or
        $receipt.metadata.runner_process_classification -ne $request.runner_status_claim) {
        throw 'Receipt status must remain inconclusive and its runner claim must match the submitted claim.'
    }
    $resultPath = Join-Path $source 'campaign_result.json'
    if (-not (Test-Path -LiteralPath $resultPath -PathType Leaf)) { throw 'Campaign result report is absent.' }
    $campaignResult = Get-Content -LiteralPath $resultPath -Raw | ConvertFrom-Json
    foreach ($field in @('campaign_id', 'decision_id', 'unit_id', 'run_id', 'nodeid', 'destination', 'manifest_sha256', 'owner_decision_sha256')) {
        if ($campaignResult.$field -ne $request.$field) { throw "Campaign report differs from archive request field $field." }
    }
    if ($campaignResult.scientific_status -ne 'INCONCLUSIVE' -or
        $campaignResult.runner_process_classification -ne $request.runner_status_claim) {
        throw 'Campaign report status must remain inconclusive and its runner claim must match the submitted claim.'
    }
    $listed = @('receipt.json', 'receipt.sha256')
    $listedSet = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    [void]$listedSet.Add('receipt.json')
    [void]$listedSet.Add('receipt.sha256')
    foreach ($artifact in $receipt.artifacts) {
        $relative = [string]$artifact.path
        if ([IO.Path]::IsPathRooted($relative) -or $relative -match '(^|[\\/])\.\.(?:[\\/]|$)' -or $relative -match ':') {
            throw 'Receipt contains an unsafe artifact path.'
        }
        $relative = $relative.Replace('/', '\')
        if (-not $listedSet.Add($relative)) { throw 'Receipt contains a duplicate or reserved artifact path.' }
        $sourceFile = [IO.Path]::GetFullPath((Join-Path $source $relative))
        if (-not $sourceFile.StartsWith($source + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Artifact path escaped source.' }
        if (-not (Test-Path -LiteralPath $sourceFile -PathType Leaf) -or (Get-Item -LiteralPath $sourceFile -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw "Receipt artifact is absent or a reparse point: $relative"
        }
        if ((Get-Sha256 $sourceFile) -ne $artifact.sha256) { throw "Source artifact hash mismatch: $relative" }
        $listed += $relative
    }
    $actual = @(Get-ChildItem -LiteralPath $source -Force -Recurse -File | ForEach-Object { $_.FullName.Substring($source.Length + 1) | ForEach-Object { $_.Replace('/', '\') } } | Sort-Object -Unique)
    if (Compare-Object ($listed | Sort-Object -Unique) $actual) { throw 'Source tree contains files outside the receipt inventory.' }

    $campaignArchive = Join-Path $script:ArchiveRoot $request.campaign_id
    if (-not (Test-Path -LiteralPath $campaignArchive)) { New-Item -ItemType Directory -Path $campaignArchive | Out-Null }
    if ((Get-Item -LiteralPath $campaignArchive -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Archive campaign path is a reparse point.' }
    $destination = Join-Path $campaignArchive $request.run_id
    if (Test-Path -LiteralPath $destination) { throw "Refusing to overwrite archived evidence: $destination" }
    New-Item -ItemType Directory -Path $destination | Out-Null
    foreach ($relative in $listed) {
        $sourceFile = Join-Path $source $relative
        $destinationFile = Join-Path $destination $relative
        $destinationParent = Split-Path -Parent $destinationFile
        if (-not (Test-Path -LiteralPath $destinationParent)) { New-Item -ItemType Directory -Path $destinationParent -Force | Out-Null }
        Copy-Item -LiteralPath $sourceFile -Destination $destinationFile
        $expected = if ($relative -eq 'receipt.json') { $request.receipt_sha256 } elseif ($relative -eq 'receipt.sha256') {
            "$($request.receipt_sha256)  receipt.json"
        } else {
            ($receipt.artifacts | Where-Object { $_.path.Replace('/', '\') -eq $relative } | Select-Object -First 1).sha256
        }
        if ($relative -eq 'receipt.sha256') {
            if ((Get-Content -LiteralPath $destinationFile -Raw).Trim() -ne $expected) { throw 'Copied receipt sidecar mismatch.' }
        }
        elseif ($expected -and (Get-Sha256 $destinationFile) -ne $expected) { throw "Copied artifact hash mismatch: $relative" }
    }
    $ack = [ordered]@{
        schema = 'qf-wp12-administrator-archive-ack-v1'
        status = 'ARCHIVED_BYTES_ONLY'
        campaign_id = $request.campaign_id
        decision_id = $request.decision_id
        unit_id = $request.unit_id
        run_id = $request.run_id
        destination = $request.destination
        manifest_sha256 = $request.manifest_sha256
        request_sha256 = $requestHash
        receipt_sha256 = $request.receipt_sha256
        reservation_key = $request.reservation_key
        nodeid = $request.nodeid
        owner_decision_sha256 = $request.owner_decision_sha256
        runner_status_claim_unattested = $request.runner_status_claim
        archived_receipt_sha256 = Get-Sha256 (Join-Path $destination 'receipt.json')
        archive_relative_path = "$($request.campaign_id)/$($request.run_id)"
        archive_assurance = 'BYTE_INTEGRITY_ONLY_PROCESS_EXECUTION_NOT_ATTESTED'
        process_execution_attested = $false
        scientific_status_attested = $false
        archived_utc = [DateTime]::UtcNow.ToString('o')
    }
    & icacls.exe $destination /inheritance:r /grant:r "*S-1-5-32-544`:(OI)(CI)(F)" "*S-1-5-18`:(OI)(CI)(F)" "*$script:RunnerSid`:(OI)(CI)(RX)" /T /C
    if ($LASTEXITCODE -ne 0) { throw 'Could not seal the archived run ACL.' }
    $ackPath = Join-Path $campaignArchive ($request.run_id + '.archive-ack.json')
    $ackBytes = [Text.Encoding]::UTF8.GetBytes(($ack | ConvertTo-Json -Depth 4) + [Environment]::NewLine)
    $ackTemporary = Join-Path $campaignArchive ('.' + $request.run_id + '.' + [guid]::NewGuid().ToString('N') + '.ack.tmp')
    $ackStream = [IO.File]::Open($ackTemporary, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    try { $ackStream.Write($ackBytes, 0, $ackBytes.Length); $ackStream.Flush($true) }
    finally { $ackStream.Dispose() }
    if (Test-Path -LiteralPath $ackPath) { throw 'Archive acknowledgement appeared concurrently; refusing replacement.' }
    $terminalDirectory = Join-Path (Join-Path $script:ArchiveRoot '_wp12_ledger') 'terminals'
    if (-not (Test-Path -LiteralPath $terminalDirectory)) { New-Item -ItemType Directory -Path $terminalDirectory | Out-Null }
    $terminalPath = Join-Path $terminalDirectory ($request.reservation_key + '.terminal.json')
    Write-SystemJsonCreateNew $terminalPath ([ordered]@{
        schema = 'qf-wp12-protected-attempt-terminal-v1'
        reservation_key = $request.reservation_key
        campaign_id = $request.campaign_id
        run_id = $request.run_id
        nodeid = $request.nodeid
        manifest_sha256 = $request.manifest_sha256
        owner_decision_sha256 = $request.owner_decision_sha256
        scientific_assessment = 'NOT_ATTESTED'
        runner_status_claim_unattested = $request.runner_status_claim
        owner_authentication = 'ED25519_DECISION_VERIFIED_BY_PROTECTED_WORKER'
        archive_assurance = 'BYTE_INTEGRITY_ONLY_PROCESS_EXECUTION_NOT_ATTESTED'
        process_execution_attested = $false
        scientific_status_attested = $false
        request_sha256 = $requestHash
        receipt_sha256 = $request.receipt_sha256
        finished_utc = [DateTime]::UtcNow.ToString('o')
    })
    if (Test-Path -LiteralPath $ackPath) { throw 'Archive acknowledgement appeared concurrently; refusing replacement.' }
    [IO.File]::Move($ackTemporary, $ackPath)
    return [pscustomobject]@{ state = 'ARCHIVED_BYTES_ONLY'; request = $RequestPath; destination = $destination; acknowledgement = $ackPath; request_sha256 = $requestHash }
    }
    finally { $sourceHandle.Dispose() }
}

$script:RequestRoot = Resolve-OrdinaryDirectory $RequestRoot 'RequestRoot'
$script:EvidenceRoot = Resolve-OrdinaryDirectory $EvidenceRoot 'EvidenceRoot'
$script:ArchiveRoot = Resolve-OrdinaryDirectory $ArchiveRoot 'ArchiveRoot'
$script:OwnerDecisionRoot = Resolve-OrdinaryDirectory $OwnerDecisionRoot 'OwnerDecisionRoot'
$script:RunnerRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
$script:PythonExecutable = [IO.Path]::GetFullPath($PythonExecutable)
$script:ManifestPath = [IO.Path]::GetFullPath($ManifestPath)
$script:ManifestSha256 = $ManifestSha256
if ($script:PythonExecutable -notmatch '^[A-Za-z]:\\' -or -not (Test-Path -LiteralPath $script:PythonExecutable -PathType Leaf) -or
    (Get-Item -LiteralPath $script:PythonExecutable -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
    throw 'Pinned Python executable is absent, non-absolute, or a reparse point.'
}
foreach ($digest in @($PythonExecutableSha256, $VerifierScriptSha256, $ContractsScriptSha256, $OwnerTrustScriptSha256, $CanonicalizationScriptSha256, $WorkerScriptSha256, $ManifestSha256)) {
    if ($digest -notmatch '^[a-f0-9]{64}$') { throw 'Installed worker pin contains a malformed SHA-256.' }
}
if ((Get-Sha256 $script:PythonExecutable) -ne $PythonExecutableSha256) { throw 'Pinned Python executable hash differs from the installed task.' }
if ((Get-Sha256 $PSCommandPath) -ne $WorkerScriptSha256) { throw 'Archive worker script hash differs from the installed task.' }
$verifier = Join-Path $script:RunnerRoot 'scripts\wp12_runner\owner_decision_verifier.py'
if (-not (Test-Path -LiteralPath $verifier -PathType Leaf) -or (Get-Sha256 $verifier) -ne $VerifierScriptSha256) {
    throw 'Owner decision verifier is absent or its hash differs from the installed task.'
}
foreach ($modulePin in @(
    @{ path = 'scripts\wp12_runner\contracts.py'; digest = $ContractsScriptSha256 },
    @{ path = 'scripts\wp12_runner\owner_trust.py'; digest = $OwnerTrustScriptSha256 },
    @{ path = 'scripts\wp12_owner_canonicalization.py'; digest = $CanonicalizationScriptSha256 }
)) {
    $modulePath = Join-Path $script:RunnerRoot $modulePin.path
    if (-not (Test-Path -LiteralPath $modulePath -PathType Leaf) -or (Get-Sha256 $modulePath) -ne $modulePin.digest) {
        throw "Owner verifier dependency differs from its installed task pin: $($modulePin.path)"
    }
}
if ($script:ManifestPath -notmatch '^[A-Za-z]:\\' -or
    -not (Test-Path -LiteralPath $script:ManifestPath -PathType Leaf) -or
    (Get-Item -LiteralPath $script:ManifestPath -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
    throw 'Protected ManifestPath must be an existing absolute ordinary file.'
}
if (-not $script:ManifestPath.StartsWith($script:OwnerDecisionRoot.TrimEnd([char]92) + [char]92 + 'WP12-1-PILOT-001' + [char]92, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Protected ManifestPath must be inside the Owner decision campaign directory.'
}
$manifestParent = Resolve-OrdinaryDirectory (Split-Path -Parent $script:ManifestPath) 'ManifestDirectory'
if (-not $manifestParent.Equals((Split-Path -Parent $script:ManifestPath), [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Protected manifest parent path is not canonical.'
}
if ((Get-Sha256 $script:ManifestPath) -ne $script:ManifestSha256) {
    throw 'Protected manifest differs from the installed task digest.'
}
$manifestObject = Get-Content -LiteralPath $script:ManifestPath -Raw -Encoding utf8 | ConvertFrom-Json
if ($manifestObject.campaign_id -ne 'WP12-1-PILOT-001' -or
    [IO.Path]::GetFullPath([string]$manifestObject.execution_context.archive.manifest_path) -ne $script:ManifestPath -or
    $manifestObject.execution_context.archive.execution_attestation -ne 'NONE') {
    throw 'Protected manifest path, campaign or disabled-attestation declaration is inconsistent.'
}
if ($RunnerSid -notmatch '^S-1-[0-9-]+$') { throw 'RunnerSid must be a Windows SID.' }
foreach ($left in @($script:RequestRoot, $script:EvidenceRoot, $script:ArchiveRoot, $script:OwnerDecisionRoot)) {
    foreach ($right in @($script:RequestRoot, $script:EvidenceRoot, $script:ArchiveRoot, $script:OwnerDecisionRoot)) {
        if ($left -ne $right -and
            ($left.StartsWith($right.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase) -or
                $right.StartsWith($left.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase))) {
            throw 'Request, evidence, archive and Owner-decision roots cannot overlap or contain one another.'
        }
    }
}

do {
    foreach ($reservationFile in Get-ChildItem -LiteralPath $script:RequestRoot -Filter '*.reserve.json' -File) {
        try {
            $requestId = $reservationFile.BaseName -replace '\.reserve$', ''
            if ($requestId -notmatch '^[A-Za-z0-9-]{36}$') { throw 'Reservation request filename has an invalid ID.' }
            $reservationAck = Join-Path (Join-Path (Join-Path $script:ArchiveRoot '_wp12_ledger') 'reservation-acks') ($requestId + '.json')
            if (-not (Test-Path -LiteralPath $reservationAck)) { $null = Process-Reservation $reservationFile.FullName }
        }
        catch {
            Write-Error -ErrorAction Continue ("WP12 attempt reservation refused: " + $_.Exception.Message)
        }
    }
    foreach ($requestFile in Get-ChildItem -LiteralPath $script:RequestRoot -Filter '*.request.json' -File) {
        try {
            $null = Process-Request $requestFile.FullName
        }
        catch {
            Write-Error -ErrorAction Continue ("WP12 archive request refused: " + $_.Exception.Message)
        }
    }
    if ($Watch) { Start-Sleep -Seconds 1 }
} while ($Watch)
