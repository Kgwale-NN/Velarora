param(
    [Parameter(Mandatory=$true)][string]$PythonExe,
    [Parameter(Mandatory=$true)][string]$ConfigPath,
    [Parameter(Mandatory=$true)][string]$StudentWindowsUser
)
$ErrorActionPreference = 'Stop'
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this installer in PowerShell as Administrator.'
}
$studentIdentity = New-Object Security.Principal.NTAccount($StudentWindowsUser)
$studentSid = $studentIdentity.Translate([Security.Principal.SecurityIdentifier]).Value
$taskName = 'Velarora Workstation Agent - ' + $studentSid
$pythonPath = (Resolve-Path -LiteralPath $PythonExe).Path
$configFile = (Resolve-Path -LiteralPath $ConfigPath).Path
$agentSource = Join-Path $PSScriptRoot 'agent.py'
$config = Get-Content -LiteralPath $configFile -Raw | ConvertFrom-Json
if (-not $config.token -or -not $config.server_url) { throw 'Select the configuration downloaded for this PC.' }
$installPath = Join-Path $env:ProgramFiles 'VelaroraAgent'
New-Item -ItemType Directory -Path $installPath -Force | Out-Null
& $pythonPath -m venv (Join-Path $installPath '.venv')
if ($LASTEXITCODE -ne 0) { throw 'Python environment creation failed.' }
$agentPython = Join-Path $installPath '.venv\Scripts\python.exe'
& $agentPython -m pip install --disable-pip-version-check 'psutil>=5.9,<8'
if ($LASTEXITCODE -ne 0) { throw 'Agent dependency installation failed.' }
Copy-Item -LiteralPath $agentSource -Destination (Join-Path $installPath 'agent.py') -Force
Copy-Item -LiteralPath $configFile -Destination (Join-Path $installPath 'agent.json') -Force
$pythonWindowless = Join-Path $installPath '.venv\Scripts\pythonw.exe'
$arguments = '"' + (Join-Path $installPath 'agent.py') + '" --config "' + (Join-Path $installPath 'agent.json') + '"'
$action = New-ScheduledTaskAction -Execute $pythonWindowless -Argument $arguments -WorkingDirectory $installPath
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $StudentWindowsUser
$taskPrincipal = New-ScheduledTaskPrincipal -UserId $StudentWindowsUser -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $taskPrincipal -Settings $settings -Force | Out-Null
Write-Host 'Installed. The agent starts when this Windows student account signs in.'
Write-Host 'Keep the server online and make sure workstation sound is enabled.'
