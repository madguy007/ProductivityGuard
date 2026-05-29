$ErrorActionPreference = "Stop"

$TaskName = "ProductivityGuard"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Launcher = Join-Path $ProjectRoot "launch_productivityguard.py"
$StartupShortcut = Join-Path ([Environment]::GetFolderPath("Startup")) "$TaskName.lnk"
$VenvPythonw = Join-Path $ProjectRoot "venv\Scripts\pythonw.exe"
$VenvPython = Join-Path $ProjectRoot "venv\Scripts\python.exe"

if (Test-Path $VenvPythonw) {
    $Python = $VenvPythonw
} elseif (Test-Path $VenvPython) {
    $Python = $VenvPython
} else {
    $PythonCommand = Get-Command pythonw.exe -ErrorAction SilentlyContinue
    if (-not $PythonCommand) {
        $PythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
    }
    if (-not $PythonCommand) {
        throw "Python was not found. Create/activate the project venv first, then run this script again."
    }
    $Python = $PythonCommand.Source
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
