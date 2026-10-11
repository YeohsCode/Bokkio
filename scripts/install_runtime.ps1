param([string]$Python = 'cpython-3.12.13-windows-x86_64-none')
$ErrorActionPreference = 'Stop'
if ([Environment]::OSVersion.Platform -ne 'Win32NT') { throw 'Windows is required' }
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { throw 'Install uv from its official distribution, then rerun.' }
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location $projectRoot
$env:PYTHONUTF8 = '1'
uv sync --frozen --extra mcp --extra browser --python $Python
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
uv run python -m playwright install chromium
if ($LASTEXITCODE -ne 0) { throw 'Browser installation failed' }
uv run bokkio-runtime --help
if ($LASTEXITCODE -ne 0) { throw 'Runtime startup failed' }
Write-Host 'Review examples/runtime-policy.json and use docs/RUNTIME-GUIDE.md.'
Write-Host 'An unlocked interactive desktop is required. UAC/secure desktops are not bypassed.'
