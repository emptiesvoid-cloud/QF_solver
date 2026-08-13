[CmdletBinding()]
param(
    [string]$Image = "qf-solver-large:0.2.0"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot

docker build `
    --file (Join-Path $projectRoot "tools/containers/large/Dockerfile") `
    --tag $Image `
    $projectRoot

if ($LASTEXITCODE -ne 0) {
    throw "Docker build failed with exit code $LASTEXITCODE."
}

docker run --rm $Image python3 -c `
    "import h5py, mpi4py, petsc4py; from petsc4py import PETSc; print('h5py', h5py.__version__); print('mpi4py', mpi4py.__version__); print('petsc4py', petsc4py.__version__); print('PETSc', PETSc.Sys.getVersion())"

if ($LASTEXITCODE -ne 0) {
    throw "Container runtime verification failed with exit code $LASTEXITCODE."
}
