param([string]$Python = 'python', [string]$Flutter = 'flutter')
$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path $PSScriptRoot -Parent
Push-Location $RepoRoot
try {
    if (!(Test-Path .venv-flutter/Scripts/python.exe)) {
        & $Python -m venv .venv-flutter
        if ($LASTEXITCODE) { throw 'Python environment creation failed' }
    }
    $BuildPython = Join-Path $RepoRoot '.venv-flutter/Scripts/python.exe'
    $env:REGION_COMPOSITOR_PYTHON = $BuildPython
    & $BuildPython -m pip install -r requirements-flutter.txt 'pyinstaller==6.21.0'
    if ($LASTEXITCODE) { throw 'Python dependencies failed' }
    & $BuildPython scripts/build_app_icon.py
    if ($LASTEXITCODE) { throw 'Windows icon generation failed' }
    & $BuildPython -m unittest discover -s tests -v
    if ($LASTEXITCODE) { throw 'Python tests failed' }
    Push-Location flutter_app
    try {
        & $Flutter pub get
        if ($LASTEXITCODE) { throw 'Flutter dependencies failed. Windows requires Developer Mode or permission to create symlinks.' }
    } finally { Pop-Location }
    & $BuildPython scripts/collect_licenses.py
    if ($LASTEXITCODE) { throw 'License collection failed' }
    Push-Location flutter_app
    try {
        & $Flutter analyze --no-pub
        if ($LASTEXITCODE) { throw 'Flutter analysis failed' }
        & $Flutter test --no-pub
        if ($LASTEXITCODE) { throw 'Flutter tests failed' }
        & $Flutter build windows --release --no-pub
        if ($LASTEXITCODE) { throw 'Flutter build failed' }
    } finally { Pop-Location }
    & $BuildPython -m PyInstaller --noconfirm --clean --onedir --console --name region_worker `
        --paths $RepoRoot --exclude-module tkinter --exclude-module tkinterdnd2 `
        --distpath build/flutter-worker --workpath build/flutter-worker-work `
        --specpath build backend/entrypoint.py
    if ($LASTEXITCODE) { throw 'Python worker build failed' }
    $BundlePath = Join-Path $RepoRoot 'flutter_app/build/windows/x64/runner/Release'
    New-Item -ItemType Directory -Force (Join-Path $BundlePath 'engine') | Out-Null
    Copy-Item -Path build/flutter-worker/region_worker/* -Destination (Join-Path $BundlePath 'engine') -Recurse -Force
    Copy-Item -LiteralPath LICENSE, docs/THIRD_PARTY_NOTICES.md, flutter_app/assets/THIRD_PARTY_LICENSES.txt -Destination $BundlePath -Force
    & $BuildPython scripts/smoke_packaged_worker.py
    if ($LASTEXITCODE) { throw 'Packaged worker smoke test failed' }
    Write-Host "Ready: $BundlePath (distribute the entire folder, not only the executable)"
} finally { Pop-Location }
