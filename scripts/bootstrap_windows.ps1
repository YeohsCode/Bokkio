# Run in the disposable Windows ARM64 VM after copying the setup media.
# Media contains Bokkio-windows-setup.zip and the two official tool archives.
param(
    [Parameter(Mandatory = $true)][string]$MediaRoot,
    [string]$WorkspaceRoot = (Join-Path $env:LOCALAPPDATA 'BokkioTest')
)
$ErrorActionPreference = 'Stop'
if ([Environment]::OSVersion.Platform -ne 'Win32NT') { throw 'Windows is required' }

$uvArchive = Join-Path $MediaRoot 'bokkio-uv-arm64.zip'
$sdkArchive = Join-Path $MediaRoot 'bokkio-dotnet-arm64.zip'
$expectedUv = '93ed53b94e9cec000cacdfd18ca67bc4cb2b6a5f5ec041edd7f2a3dae365ce79'
$expectedSdk = '2a75864daac54fe8360498d0a7260e3f8d851c3d811d864d7229f00ae51eac9e534998b7c3d221fc423319b9c8147dd43fa80690c969e43b2045cc2f1f93e537'
if ((Get-FileHash $uvArchive -Algorithm SHA256).Hash -ne $expectedUv) { throw 'uv archive hash mismatch' }
if ((Get-FileHash $sdkArchive -Algorithm SHA512).Hash -ne $expectedSdk) { throw '.NET archive hash mismatch' }

$tools = Join-Path $WorkspaceRoot 'tools'
$uvDir = Join-Path $tools 'uv'
$sdkDir = Join-Path $tools 'dotnet'
New-Item -ItemType Directory -Force $tools | Out-Null
if (-not (Test-Path (Join-Path $uvDir 'uv.exe'))) { Expand-Archive $uvArchive $uvDir }
if (-not (Test-Path (Join-Path $sdkDir 'dotnet.exe'))) { Expand-Archive $sdkArchive $sdkDir }
$project = Join-Path $WorkspaceRoot 'Bokkio'
if (-not (Test-Path $project)) {
    Expand-Archive (Join-Path $MediaRoot 'Bokkio-windows-setup.zip') $WorkspaceRoot
}
$env:DOTNET_ROOT = $sdkDir
$env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
$env:PYTHONUTF8 = '1'
$env:PATH = "$uvDir;$sdkDir;$env:PATH"
Set-Location $project

# xa11y 0.15.0 ships win_amd64 wheels. Pin the emulated x64 interpreter.
# Windows PowerShell 5.1 can treat native stderr progress as an error record.
# Check exit codes explicitly so download/build progress cannot abort setup.
$ErrorActionPreference = 'Continue'
uv sync --group test --python cpython-3.12.13-windows-x86_64-none
if ($LASTEXITCODE -ne 0) { throw 'uv sync failed' }
uv run python -c "import platform, struct, xa11y; print(platform.platform(), platform.machine(), struct.calcsize('P') * 8, xa11y.__file__)"
if ($LASTEXITCODE -ne 0) { throw 'xa11y import failed' }
uv run pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Unit tests failed' }
dotnet build vendor/xa11y/test-apps/winforms/xa11y-winforms-test-app.csproj -c Release
if ($LASTEXITCODE -ne 0) { throw 'WinForms build failed' }
dotnet build fixtures/windows-scale/windows-scale.csproj -c Release
if ($LASTEXITCODE -ne 0) { throw 'Scale fixture build failed' }
$ErrorActionPreference = 'Stop'
Start-Process (Join-Path $project 'vendor/xa11y/test-apps/winforms/bin/Release/net8.0-windows/xa11y-winforms-test-app.exe')
Write-Host "Setup completed in $project. Open native matrix apps, then run scripts/verify_windows.py."
