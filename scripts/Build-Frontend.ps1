$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$frontendRoot = Join-Path $projectRoot 'frontend\react'
$index = Join-Path $frontendRoot 'dist\index.html'
$npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $npm) { throw 'Install Node.js 22.12+ (or Node.js 24 LTS), reopen the terminal, then run Start-Monitor.ps1 again.' }
$sources = @(Get-ChildItem -LiteralPath (Join-Path $frontendRoot 'src') -File -Recurse)
$sources += Get-Item -LiteralPath (Join-Path $frontendRoot 'package.json'),(Join-Path $frontendRoot 'package-lock.json'),(Join-Path $frontendRoot 'index.html'),(Join-Path $frontendRoot 'vite.config.ts')
$needsBuild = -not (Test-Path -LiteralPath $index)
if (-not $needsBuild) {
    $builtAt = (Get-Item -LiteralPath $index).LastWriteTimeUtc
    $needsBuild = @($sources | Where-Object { $_.LastWriteTimeUtc -gt $builtAt }).Count -gt 0
}
if ($needsBuild) {
    Push-Location -LiteralPath $frontendRoot
    try {
        $modules = Join-Path $frontendRoot 'node_modules'
        $installedLock = Join-Path $modules '.package-lock.json'
        $sourceLock = Join-Path $frontendRoot 'package-lock.json'
        if (-not (Test-Path -LiteralPath $installedLock) -or (Get-Item -LiteralPath $sourceLock).LastWriteTimeUtc -gt (Get-Item -LiteralPath $installedLock).LastWriteTimeUtc) {
            & $npm.Source ci
            if ($LASTEXITCODE -ne 0) { throw 'React dependency installation failed.' }
        }
        Write-Host 'Building the React interface...'
        & $npm.Source run build
        if ($LASTEXITCODE -ne 0) { throw 'React build failed. The server was not started.' }
    } finally { Pop-Location }
}
