param(
    [int]$Port = 8000,
    [ValidateSet("engineering", "qualification")]
    [string]$Profile = "engineering"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Push-Location $Root
try {
    python .\scripts\build_docs.py --profile $Profile
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
    python -m mkdocs serve --dev-addr "127.0.0.1:$Port"
}
finally {
    Pop-Location
}
