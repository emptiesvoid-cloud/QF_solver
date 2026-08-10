[CmdletBinding()]
param(
    [ValidateSet("readiness", "campaign", "test-mpi")]
    [string]$Action = "readiness",
    [string]$Image = "qf-solver-large:0.2.0",
    [int[]]$Targets = @(100000, 1000000, 3000000),
    [int]$Ranks = 1,
    [switch]$Execute
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$mount = "${projectRoot}:/workspace"
$prefix = @("run", "--rm", "-v", $mount, "-w", "/workspace", $Image)

if ($Action -eq "test-mpi") {
    $command = @(
        "mpiexec", "-n", [string]$Ranks, "python3", "-c",
        "from mpi4py import MPI; from petsc4py import PETSc; print('rank', MPI.COMM_WORLD.rank, 'size', MPI.COMM_WORLD.size, 'PETSc', PETSc.Sys.getVersion())"
    )
} elseif ($Action -eq "campaign") {
    $command = @(
        "python3", "qf_solver.py", "large-campaign",
        "--output", "/workspace/results_large/P4-CAMPAIGN-PETSC-001",
        "--targets"
    ) + @($Targets | ForEach-Object { [string]$_ }) + @(
        "--solver-backend", "petsc", "--preconditioner", "gamg"
    )
    if ($Execute) {
        $command += "--execute"
    }
} else {
    $command = @(
        "python3", "qf_solver.py", "large-readiness",
        "--output", "/workspace/results_large/readiness_container",
        "--target-dofs", [string]$Targets[0], "--solver-backend", "petsc"
    )
}

& docker @prefix @command
if ($LASTEXITCODE -ne 0) {
    throw "Container command failed with exit code $LASTEXITCODE."
}
