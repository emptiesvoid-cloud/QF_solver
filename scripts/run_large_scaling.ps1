[CmdletBinding()]
param(
    [ValidateSet("weak", "preconditioners", "profile", "tuning")]
    [string]$Action = "weak",
    [string]$Image = "qf-solver-large:0.2.0",
    [string]$Output = "results_large/P4-REPRODUCED",
    [switch]$Execute,
    [string]$ModelRoot = "results_large/P4-PETSC-PROFILE-TOPOLOGIES-001/profile",
    [ValidateSet("contiguous", "graph")]
    [string]$PartitionStrategy = "contiguous"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$outputRoot = Join-Path $projectRoot $Output
$mount = "${projectRoot}:/workspace"

if (-not $Execute) {
    Write-Output "PLAN ONLY: $Action"
    Write-Output "Image: $Image"
    Write-Output "Output: $outputRoot"
    Write-Output "Add -Execute to generate models and run PETSc/MPI."
    exit 0
}

function Invoke-QfDocker([int]$Ranks, [string[]]$Arguments, [string]$PetscOptions = "") {
    $dockerArguments = @("run", "--rm")
    if ($PetscOptions) {
        $dockerArguments += @("-e", "PETSC_OPTIONS=$PetscOptions")
    }
    $dockerArguments += @("-v", $mount, "-w", "/workspace", $Image)
    $dockerArguments += @("mpiexec", "-n", $Ranks, "python3", "qf_solver.py")
    $dockerArguments += $Arguments
    & docker @dockerArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Docker PETSc command failed with exit code $LASTEXITCODE."
    }
}

if ($Action -eq "profile") {
    $containerOutputRoot = $Output.Replace("\", "/")
    $cases = @(
        @{ Name = "block"; Nx = 43; Ny = 43; Nz = 43; Length = 1.0; Height = 1.0; Depth = 1.0 },
        @{ Name = "beam"; Nx = 159; Ny = 22; Nz = 22; Length = 10.0; Height = 1.0; Depth = 1.0 },
        @{ Name = "plate"; Nx = 91; Ny = 91; Nz = 9; Length = 10.0; Height = 10.0; Depth = 1.0 }
    )
    $profileLogs = @()
    $profileLabels = @()
    foreach ($case in $cases) {
        $caseRoot = Join-Path $outputRoot "profile/$($case.Name)"
        $modelPath = Join-Path $caseRoot "model.h5"
        $profilePath = Join-Path $caseRoot "petsc_log_view.txt"
        $benchmarkPath = Join-Path $caseRoot "benchmark/benchmark_large.json"
        New-Item -ItemType Directory -Force -Path $caseRoot | Out-Null
        if ((Test-Path $profilePath) -and (Test-Path $benchmarkPath)) {
            Write-Output "PROFILE RESUME: $($case.Name) already complete"
            $profileLogs += $profilePath
            $profileLabels += $case.Name
            continue
        }
        & python (Join-Path $projectRoot "qf_solver.py") generate-large-tet4-block `
            --output $modelPath --nx $case.Nx --ny $case.Ny --nz $case.Nz `
            --length $case.Length --height $case.Height --depth $case.Depth
        if ($LASTEXITCODE -ne 0) {
            throw "Large-model generation failed for $($case.Name)."
        }
        $containerCaseRoot = "/workspace/$containerOutputRoot/profile/$($case.Name)"
        $petscLog = "$containerCaseRoot/petsc_log_view.txt"
        Invoke-QfDocker 4 @(
            "benchmark-large", "--input", "$containerCaseRoot/model.h5",
            "--output", "$containerCaseRoot/benchmark", "--solver-backend", "petsc",
            "--preconditioner", "gamg", "--matrix-format", "baij",
            "--partition-strategy", $PartitionStrategy
        ) "-log_view ascii:${petscLog}:ascii_info_detail"
        $profileLogs += $profilePath
        $profileLabels += $case.Name
    }
    $reportArguments = @("petsc-profile-report", "--inputs") + $profileLogs
    $reportArguments += @("--labels") + $profileLabels
    $reportArguments += @("--output", (Join-Path $outputRoot "profile/report"))
    & python (Join-Path $projectRoot "qf_solver.py") @reportArguments
    if ($LASTEXITCODE -ne 0) {
        throw "PETSc profile report generation failed."
    }
    exit 0
}

if ($Action -eq "tuning") {
    $containerOutputRoot = $Output.Replace("\", "/")
    $containerModelRoot = $ModelRoot.Replace("\", "/")
    $topologies = @("block", "beam", "plate")
    $presets = @(
        @{ Name = "gamg-default"; Pc = "gamg"; Options = "" },
        @{ Name = "gamg-threshold-001"; Pc = "gamg"; Options = "-pc_gamg_threshold 0.01" },
        @{ Name = "gamg-threshold-005"; Pc = "gamg"; Options = "-pc_gamg_threshold 0.05" },
        @{ Name = "hypre-default"; Pc = "hypre"; Options = "" },
        @{
            Name = "hypre-hmis-exti"
            Pc = "hypre"
            Options = "-pc_hypre_boomeramg_strong_threshold 0.5 -pc_hypre_boomeramg_coarsen_type HMIS -pc_hypre_boomeramg_interp_type ext+i"
        }
    )
    $benchmarkReports = @()
    $reportTopologies = @()
    $reportPresets = @()
    foreach ($topology in $topologies) {
        $hostModel = Join-Path $projectRoot "$ModelRoot/$topology/model.h5"
        if (-not (Test-Path $hostModel)) {
            throw "Missing profile model for topology ${topology}: $hostModel"
        }
        foreach ($preset in $presets) {
            $runRoot = Join-Path $outputRoot "tuning/$topology/$($preset.Name)"
            $benchmarkPath = Join-Path $runRoot "benchmark_large.json"
            $logPath = Join-Path $runRoot "petsc_log_view.txt"
            if ((Test-Path $benchmarkPath) -and (Test-Path $logPath)) {
                Write-Output "TUNING RESUME: $topology/$($preset.Name) already complete"
            }
            else {
                New-Item -ItemType Directory -Force -Path $runRoot | Out-Null
                $containerRunRoot = "/workspace/$containerOutputRoot/tuning/$topology/$($preset.Name)"
                $petscOptions = "$($preset.Options) -log_view ascii:${containerRunRoot}/petsc_log_view.txt:ascii_info_detail".Trim()
                Invoke-QfDocker 4 @(
                    "benchmark-large", "--input", "/workspace/$containerModelRoot/$topology/model.h5",
                    "--output", $containerRunRoot, "--solver-backend", "petsc",
                    "--preconditioner", $preset.Pc, "--matrix-format", "baij",
                    "--partition-strategy", $PartitionStrategy
                ) $petscOptions
            }
            $benchmarkReports += $benchmarkPath
            $reportTopologies += $topology
            $reportPresets += $preset.Name
        }
    }
    $reportArguments = @("petsc-tuning-report", "--inputs") + $benchmarkReports
    $reportArguments += @("--topologies") + $reportTopologies
    $reportArguments += @("--presets") + $reportPresets
    $reportArguments += @("--output", (Join-Path $outputRoot "tuning/report"))
    & python (Join-Path $projectRoot "qf_solver.py") @reportArguments
    if ($LASTEXITCODE -ne 0) {
        throw "PETSc tuning report generation failed."
    }
    exit 0
}

if ($Action -eq "preconditioners") {
    $model = "/workspace/results_large/P4-PETSC-1M-001/model_rtol_1e-12.h5"
    $target = "/workspace/$Output/preconditioners"
    Invoke-QfDocker 4 @(
        "large-preconditioners", "--input", $model, "--output", $target,
        "--preconditioners", "gamg", "hypre", "--matrix-format", "baij"
    )
    exit 0
}

$cases = @(
    @{ Name = "r1"; Ranks = 1; Nx = 17; Length = 17.0 / 69.0 },
    @{ Name = "r2"; Ranks = 2; Nx = 34; Length = 34.0 / 69.0 },
    @{ Name = "r4"; Ranks = 4; Nx = 69; Length = 1.0 }
)
$reports = @()
foreach ($case in $cases) {
    $caseRoot = Join-Path $outputRoot $case.Name
    $modelPath = Join-Path $caseRoot "model.h5"
    & python (Join-Path $projectRoot "qf_solver.py") generate-large-tet4-block `
        --output $modelPath --nx $case.Nx --ny 69 --nz 69 `
        --length $case.Length --height 1 --depth 1
    if ($LASTEXITCODE -ne 0) {
        throw "Large-model generation failed."
    }
    $containerModel = "/workspace/$Output/$($case.Name)/model.h5"
    $containerOutput = "/workspace/$Output/$($case.Name)/benchmark"
    Invoke-QfDocker $case.Ranks @(
        "benchmark-large", "--input", $containerModel, "--output", $containerOutput,
        "--solver-backend", "petsc", "--preconditioner", "gamg", "--matrix-format", "baij"
    )
    $reports += Join-Path $caseRoot "benchmark/benchmark_large.json"
}

& python (Join-Path $projectRoot "qf_solver.py") large-scaling-report `
    --mode weak --weak-work-tolerance 0.05 --efficiency-warning-threshold 0.60 `
    --inputs $reports --output (Join-Path $outputRoot "report")
if ($LASTEXITCODE -ne 0) {
    throw "Weak-scaling report failed."
}
