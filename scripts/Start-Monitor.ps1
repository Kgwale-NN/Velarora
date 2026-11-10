$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$ErrorActionPreference = 'Stop'
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { throw 'Python environment missing. Follow docs/LOCAL-SETUP.md to create it.' }
function Test-LocalPort([int]$Port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try { $client.Connect('127.0.0.1', $Port); return $true }
    catch { return $false }
    finally { $client.Dispose() }
}
if (Test-LocalPort 8080) {
    Write-Host 'Port 8080 is already in use. If the monitor is running, open http://127.0.0.1:8080 .'
    exit 0
}
$env:YOLO_CONFIG_DIR = Join-Path $projectRoot 'data\ultralytics'
$env:MPLCONFIGDIR = Join-Path $projectRoot 'data\matplotlib'
New-Item -ItemType Directory -Force -Path $env:YOLO_CONFIG_DIR,$env:MPLCONFIGDIR | Out-Null
$apiProcess = $null
$cli = 'C:\Program Files\Veyon\veyon-cli.exe'
try {
    if (-not (Test-LocalPort 11080)) {
        if (Test-Path $cli) {
            $apiProcess = Start-Process -FilePath $cli -ArgumentList 'webapi','runserver' -WindowStyle Hidden -PassThru -RedirectStandardOutput 'data\webapi.stdout.log' -RedirectStandardError 'data\webapi.stderr.log'
        } else { Write-Warning 'Veyon is not installed. The dashboard can open but cannot capture screens.' }
    }
    Write-Host 'Open http://127.0.0.1:8080 . Press Ctrl+C here to stop the app.'
    & $python run.py
} finally {
    if ($apiProcess -and -not $apiProcess.HasExited) { Stop-Process -Id $apiProcess.Id -ErrorAction SilentlyContinue }
}
