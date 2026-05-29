$ErrorActionPreference = "Stop"

$TaskName = "ProductivityGuard"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Launcher = Join-Path $ProjectRoot "launch_productivityguard.py"
$StartupShortcut = Join-Path ([Environment]::GetFolderPath("Startup")) "$TaskName.lnk"
$VenvPython = Join-Path $ProjectRoot "venv\Scripts\python.exe"

function Test-PythonForApp {
    param([string]$PythonPath)

    if (-not $PythonPath) {
        return $false
    }

    try {
        & $PythonPath -c "import flask" *> $null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

$Python = $null
if ((Test-Path $VenvPython) -and (Test-PythonForApp $VenvPython)) {
    $Python = $VenvPython
} else {
    $PythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($PythonCommand -and (Test-PythonForApp $PythonCommand.Source)) {
        $Python = $PythonCommand.Source
    }
}

if (-not $Python) {
    throw "No working Python with Flask was found. Run: pip install -r requirements.txt"
}

if (-not (Test-Path $Launcher)) {
    throw "Launcher not found: $Launcher"
}

try {
    $Action = New-ScheduledTaskAction `
        -Execute $Python `
        -Argument "`"$Launcher`"" `
        -WorkingDirectory $ProjectRoot
    $Trigger = New-ScheduledTaskTrigger -AtLogOn
    $Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
    $Settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -MultipleInstances IgnoreNew `
        -StartWhenAvailable

    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $Action `
        -Trigger $Trigger `
        -Principal $Principal `
        -Settings $Settings `
        -Description "Starts ProductivityGuard automatically when you log in." `
        -Force | Out-Null

    Start-ScheduledTask -TaskName $TaskName
    Write-Host "Installed scheduled task: $TaskName."
} catch {
    Write-Host "Scheduled task install failed, using Startup shortcut instead."
    $Shell = New-Object -ComObject WScript.Shell
    $Shortcut = $Shell.CreateShortcut($StartupShortcut)
    $Shortcut.TargetPath = $Python
    $Shortcut.Arguments = "`"$Launcher`""
    $Shortcut.WorkingDirectory = $ProjectRoot
    $Shortcut.Description = "Starts ProductivityGuard automatically when you log in."
    $Shortcut.Save()

    Start-Process `
        -FilePath $Python `
        -ArgumentList "`"$Launcher`"" `
        -WorkingDirectory $ProjectRoot `
        -WindowStyle Hidden

    Write-Host "Installed Startup shortcut: $StartupShortcut"
}

Write-Host "Installed and started $TaskName."
Write-Host "Dashboard: http://127.0.0.1:5000"
