param([string]$Python = 'python', [string]$Flutter = 'flutter')
& (Join-Path $PSScriptRoot 'scripts/build_flutter.ps1') -Python $Python -Flutter $Flutter
if ($LASTEXITCODE) { exit $LASTEXITCODE }
