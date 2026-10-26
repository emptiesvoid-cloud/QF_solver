[CmdletBinding()]
param(
    [string[]] $CheckoutRoots = @(),
    [string[]] $QualificationRoots = @(),
    [string[]] $PythonExecutables = @()
)

$ErrorActionPreference = 'Stop'
$os = Get-CimInstance Win32_OperatingSystem
$computer = Get-CimInstance Win32_ComputerSystem
$processor = Get-CimInstance Win32_Processor | Select-Object -First 1
$bios = Get-CimInstance Win32_BIOS
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [System.Security.Principal.WindowsPrincipal]::new($identity)
$windowsRegistry = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion'
$volumes = Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | ForEach-Object {
    [pscustomobject]@{
        DeviceID = $_.DeviceID
        FileSystem = $_.FileSystem
        SizeBytes = $_.Size
        FreeBytes = $_.FreeSpace
        VolumeName = $_.VolumeName
    }
}
$pythonCommands = Get-Command python, py -ErrorAction SilentlyContinue | ForEach-Object {
    [pscustomobject]@{ Name = $_.Name; Source = $_.Source }
}
$pythonInstallations = @()
$pyLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($pyLauncher) { $pythonInstallations += [pscustomobject]@{ Launcher = $pyLauncher.Source; Installed = @(& $pyLauncher.Source -0p 2>&1) } }
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCommand) {
    $PythonExecutables += @($pythonCommand.Source)
}
$pythonProbe = @'
import hashlib, importlib.metadata, json, pathlib, platform, site, sys
names = ("qf-solver", "numpy", "scipy", "pytest", "cryptography", "jsonschema", "psutil", "pip")
packages = {}
for name in names:
    try:
        distribution = importlib.metadata.distribution(name)
    except importlib.metadata.PackageNotFoundError:
        packages[name] = None
    else:
        packages[name] = {"version": distribution.version, "metadata_path": str(getattr(distribution, "_path", ""))}
exe = pathlib.Path(sys.executable).resolve()
print(json.dumps({"executable": str(exe), "executable_sha256": hashlib.sha256(exe.read_bytes()).hexdigest(), "version": platform.python_version(), "implementation": platform.python_implementation(), "prefix": str(pathlib.Path(sys.prefix).resolve()), "base_prefix": str(pathlib.Path(sys.base_prefix).resolve()), "virtual_environment": sys.prefix != sys.base_prefix, "site_packages": site.getsitepackages(), "packages": packages}, sort_keys=True))
'@
$pythonProbeResults = foreach ($pythonPath in @($PythonExecutables | Select-Object -Unique)) {
    if ($pythonPath -notmatch '^[A-Za-z]:[\\/]' -or -not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
        [pscustomobject]@{ executable = $pythonPath; state = 'ABSENT_OR_NOT_ABSOLUTE' }
        continue
    }
    $pythonResolved = (Resolve-Path -LiteralPath $pythonPath).Path
    $pythonItem = Get-Item -LiteralPath $pythonResolved -Force
    if ($pythonItem.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        [pscustomobject]@{ executable = $pythonResolved; state = 'REPARSE_POINT_REFUSED' }
        continue
    }
    $probeOutput = @(& $pythonResolved -I -c $pythonProbe 2>&1)
    $probeCode = $LASTEXITCODE
    [pscustomobject]@{ executable = $pythonResolved; exitCode = $probeCode; probe = @($probeOutput) }
}
$features = @()
if (Get-Command Get-WindowsOptionalFeature -ErrorAction SilentlyContinue) {
    try {
        $features = @(Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All -ErrorAction Stop |
            Select-Object FeatureName, State)
    }
    catch {
        $features = @([pscustomobject]@{ FeatureName = 'Microsoft-Hyper-V-All'; State = 'NOT_QUERYABLE'; Detail = $_.Exception.Message })
    }
}
$checkouts = foreach ($root in $CheckoutRoots) {
    $resolved = [IO.Path]::GetFullPath($root)
    if (-not (Test-Path -LiteralPath $resolved -PathType Container)) {
        [pscustomobject]@{ Path = $resolved; State = 'ABSENT' }
        continue
    }
    $git = git -C $resolved status --porcelain=v1 --branch 2>&1
    [pscustomobject]@{ Path = $resolved; GitStatus = @($git); Icacls = @(icacls $resolved 2>&1) }
}
$qualification = foreach ($root in $QualificationRoots) {
    $resolved = [IO.Path]::GetFullPath($root)
    if (Test-Path -LiteralPath $resolved) {
        [pscustomobject]@{ Path = $resolved; Icacls = @(icacls $resolved 2>&1) }
    }
    else {
        [pscustomobject]@{ Path = $resolved; State = 'ABSENT' }
    }
}
$report = [ordered]@{
    collectedUtc = [DateTime]::UtcNow.ToString('o')
    windows = [ordered]@{
        Caption = $os.Caption
        Version = $os.Version
        BuildNumber = $os.BuildNumber
        Ubr = $windowsRegistry.UBR
        DisplayVersion = $windowsRegistry.DisplayVersion
        EditionId = $windowsRegistry.EditionID
        ProductName = $windowsRegistry.ProductName
        Architecture = $os.OSArchitecture
        TotalVisibleMemoryBytes = $computer.TotalPhysicalMemory
        Manufacturer = $computer.Manufacturer
        Model = $computer.Model
        HypervisorPresent = $computer.HypervisorPresent
        Processor = $processor.Name
        LogicalProcessors = $processor.NumberOfLogicalProcessors
        VirtualizationFirmwareEnabled = $processor.VirtualizationFirmwareEnabled
        VMMonitorModeExtensions = $processor.VMMonitorModeExtensions
        SecondLevelAddressTranslationExtensions = $processor.SecondLevelAddressTranslationExtensions
        BiosVersion = @($bios.SMBIOSBIOSVersion)
        HyperVFeature = $features
    }
    account = [ordered]@{
        Sid = $identity.User.Value
        IsAdministrator = $principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)
        Groups = @($identity.Groups | ForEach-Object { $_.Value })
    }
    pythonCommands = @($pythonCommands)
    pythonInstallations = @($pythonInstallations + $pythonProbeResults)
    volumes = @($volumes)
    checkouts = @($checkouts)
    qualificationRoots = @($qualification)
    dockerInstalled = [bool](Get-Command docker -ErrorAction SilentlyContinue)
}
$report | ConvertTo-Json -Depth 8
