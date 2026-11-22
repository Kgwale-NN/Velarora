param([string]$Python = '', [string]$Config = '')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
if (-not $Python) { $Python = Join-Path $projectRoot 'data\agent-build\venv\Scripts\python.exe' }
if (-not (Test-Path -LiteralPath $Python)) { throw 'Create the agent build environment described in workstation/README.md first.' }
& $Python -m PyInstaller --noconfirm --clean --onedir --windowed --name Velarora-Agent --paths $projectRoot --distpath 'data\portable' --workpath 'data\agent-build\work' --specpath 'data\agent-build' 'workstation\portable.py'
if ($LASTEXITCODE -ne 0) { throw 'Portable build failed.' }
$package = Join-Path $projectRoot 'data\portable\Velarora-Agent'
Copy-Item -LiteralPath 'workstation\README.md' -Destination (Join-Path $package 'README.md')
if ($Config) { Copy-Item -LiteralPath $Config -Destination (Join-Path $package 'agent.json') }
Write-Output "Portable folder: $package"
Write-Output 'Copy the whole folder. Keep agent.json private; never commit it.'
