param([ValidateSet('Start','Stop')][string]$Action = 'Start')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$demoDirectory = Join-Path $projectRoot 'data\demo'
$toolsDirectory = Join-Path $projectRoot 'data\tools'
$executable = Join-Path $toolsDirectory 'cloudflared.exe'
$recordPath = Join-Path $demoDirectory 'tunnel-process.json'
$urlPath = Join-Path $demoDirectory 'public-url.txt'
New-Item -ItemType Directory -Force -Path $demoDirectory,$toolsDirectory | Out-Null
$existing = $null
if (Test-Path -LiteralPath $recordPath) {
    $record = Get-Content -Raw -LiteralPath $recordPath | ConvertFrom-Json
    $candidate = Get-Process -Id $record.pid -ErrorAction SilentlyContinue
    if ($candidate) {
        $expectedTime = [datetime]::Parse($record.started).ToUniversalTime()
        if ($candidate.Path -ne $executable -or [math]::Abs(($candidate.StartTime.ToUniversalTime() - $expectedTime).TotalSeconds) -gt 1) {
            throw 'The saved process ID belongs to a different process. No process was stopped.'
        }
        $existing = $candidate
    }
}
if ($Action -eq 'Stop') {
    if ($existing) { Stop-Process -Id $existing.Id -ErrorAction Stop }
    foreach ($file in @($recordPath,$urlPath)) {
        if (Test-Path -LiteralPath $file) { Remove-Item -LiteralPath $file }
    }
    Write-Host 'Public demo link stopped. Local Velarora remains running.'
    exit 0
}
if ($existing) {
    Write-Host 'Your public demo link is already running:'
    Get-Content -LiteralPath $urlPath
    exit 0
}
try { $session = Invoke-RestMethod -Uri 'http://127.0.0.1:8080/api/session' -TimeoutSec 10 }
catch { throw 'Start Velarora first using scripts\Start-Monitor.ps1, then run Demo-Link.ps1.' }
if (-not $session.PSObject.Properties['csrf']) { throw 'Port 8080 did not return a Velarora session.' }
$hashPath = Join-Path $toolsDirectory 'cloudflared.sha256'
if (-not (Test-Path -LiteralPath $executable) -or -not (Test-Path -LiteralPath $hashPath)) {
    $release = Invoke-RestMethod -Uri 'https://api.github.com/repos/cloudflare/cloudflared/releases/latest' -Headers @{ 'User-Agent' = 'Velarora-demo-setup' }
    $asset = $release.assets | Where-Object { $_.name -eq 'cloudflared-windows-amd64.exe' } | Select-Object -First 1
    if (-not $asset -or -not $asset.digest -or -not $asset.digest.StartsWith('sha256:')) { throw 'No verified Windows download is available.' }
    Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $executable
    $expectedHash = $asset.digest.Substring(7)
    if ((Get-FileHash -LiteralPath $executable -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expectedHash) { throw 'Cloudflared checksum mismatch; nothing was started.' }
    Set-Content -LiteralPath $hashPath -Value $expectedHash
}
$expectedHash = (Get-Content -Raw -LiteralPath $hashPath).Trim()
if ((Get-FileHash -LiteralPath $executable -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expectedHash) { throw 'The saved tunnel tool checksum changed. Nothing was started.' }
Write-Host 'Publishing Velarora through Cloudflare. Anyone can reach its login; staff permissions still apply.'
$stdout = Join-Path $demoDirectory 'tunnel.stdout.log'
$stderr = Join-Path $demoDirectory 'tunnel.stderr.log'
$demoProcess = Start-Process -FilePath $executable -ArgumentList @('tunnel','--no-autoupdate','--url','http://127.0.0.1:8080','--protocol','http2') -WindowStyle Hidden -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
try {
    @{ pid=$demoProcess.Id; started=$demoProcess.StartTime.ToUniversalTime().ToString('o'); executable=$executable } | ConvertTo-Json | Set-Content -LiteralPath $recordPath
    $publicUrl = $null
    for ($attempt = 0; $attempt -lt 80; $attempt++) {
        if ($demoProcess.HasExited) { throw 'Tunnel exited; check data\demo\tunnel.stderr.log.' }
        if (Test-Path -LiteralPath $stderr) {
            $demoMatch = [regex]::Match((Get-Content -Raw -LiteralPath $stderr), 'https://[a-z0-9-]+\.trycloudflare\.com')
            if ($demoMatch.Success) { $publicUrl = $demoMatch.Value; break }
        }
        Start-Sleep -Milliseconds 500
    }
    if (-not $publicUrl) { throw 'No demo URL was issued within 40 seconds.' }
    Set-Content -LiteralPath $urlPath -Value $publicUrl
    Write-Host ('Demo login: ' + $publicUrl + '/admin/login')
    Write-Host 'Keep this PC, Velarora and its internet connection on. The link changes when restarted.'
    Write-Host 'Stop publishing: powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Demo-Link.ps1 -Action Stop'
} catch {
    if (-not $demoProcess.HasExited) { Stop-Process -Id $demoProcess.Id }
    if (Test-Path -LiteralPath $recordPath) { Remove-Item -LiteralPath $recordPath }
    throw
}
