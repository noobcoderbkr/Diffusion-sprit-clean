param([string]$Python = 'python', [string]$Flutter = 'flutter')
$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path $PSScriptRoot -Parent
Push-Location $RepoRoot
try {
    if (!(Test-Path .venv-flutter/Scripts/python.exe)) {
        & $Python -m venv .venv-flutter
        if ($LASTEXITCODE) { throw 'Python environment creation failed' }
    }
    $WorkerPython = Join-Path $RepoRoot '.venv-flutter/Scripts/python.exe'
    & $WorkerPython -m pip install -r requirements.txt
    if ($LASTEXITCODE) { throw 'Python dependency installation failed' }
    $env:REGION_COMPOSITOR_ROOT = $RepoRoot
    $env:REGION_COMPOSITOR_PYTHON = $WorkerPython
    Push-Location flutter_app
    try {
        & $Flutter pub get
        if ($LASTEXITCODE) { throw 'Flutter dependency installation failed' }
        & $Flutter run -d windows
        if ($LASTEXITCODE) { throw 'Flutter launch failed' }
    } finally { Pop-Location }
} finally { Pop-Location }
