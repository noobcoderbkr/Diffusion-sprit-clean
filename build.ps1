param(
    [string]$PythonPath = (Join-Path $PSScriptRoot '.venv\Scripts\python.exe')
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $PythonPath)) {
    throw 'Create .venv and install requirements-build.txt first. See README.md.'
}

Push-Location $PSScriptRoot
try {
    & $PythonPath -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed; build cancelled.' }
    & $PythonPath -m PyInstaller --noconfirm --clean --noupx --onefile --windowed --name RegionCompositor --collect-all tkinterdnd2 --distpath dist --workpath build --specpath build region_compositor.py
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }
    Get-FileHash -LiteralPath (Join-Path $PSScriptRoot 'dist\RegionCompositor.exe') -Algorithm SHA256
}
finally {
    Pop-Location
}
