param(
    [Parameter(Mandatory=$true)][string]$Iscc,
    [Parameter(Mandatory=$true)][string]$CrtDirectory,
    [string]$OutputDirectory
)
$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path $PSScriptRoot -Parent
$BundleDirectory = Join-Path $RepoRoot 'flutter_app/build/windows/x64/runner/Release'
if (!$OutputDirectory) { $OutputDirectory = Join-Path $RepoRoot 'build/installer' }
$Iscc = (Resolve-Path -LiteralPath $Iscc).Path
$CrtDirectory = (Resolve-Path -LiteralPath $CrtDirectory).Path
$CompilerLicense = Join-Path (Split-Path $Iscc -Parent) 'license.txt'
foreach ($RequiredFile in @(
    (Join-Path $BundleDirectory 'region_compositor.exe'),
    (Join-Path $BundleDirectory 'engine/region_worker.exe'),
    (Join-Path $BundleDirectory 'THIRD_PARTY_LICENSES.txt'),
    (Join-Path $CrtDirectory 'msvcp140.dll'),
    $CompilerLicense
)) {
    if (!(Test-Path -LiteralPath $RequiredFile -PathType Leaf)) { throw "Required file missing: $RequiredFile" }
}
New-Item -ItemType Directory -Force $OutputDirectory | Out-Null
$OutputDirectory = (Resolve-Path -LiteralPath $OutputDirectory).Path
& $Iscc "/DBundleDir=$BundleDirectory" "/DCrtDir=$CrtDirectory" `
    "/DCompilerLicense=$CompilerLicense" "/DOutputDir=$OutputDirectory" `
    (Join-Path $RepoRoot 'packaging/windows-installer.iss')
if ($LASTEXITCODE) { throw 'Installer compilation failed' }
$SetupFile = Join-Path $OutputDirectory 'RegionCompositor-Setup-v0.2.1-x64.exe'
$Digest = (Get-FileHash -LiteralPath $SetupFile -Algorithm SHA256).Hash.ToLowerInvariant()
"$Digest  $([IO.Path]::GetFileName($SetupFile))" | Set-Content -Encoding ascii (Join-Path $OutputDirectory 'SHA256SUMS-Setup.txt')
Write-Host "Installer ready: $SetupFile"
