$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Launcher = Join-Path $ProjectRoot "launch_productivityguard.py"
$VenvPythonw = Join-Path $ProjectRoot "venv\Scripts\pythonw.exe"
$VenvPython = Join-Path $ProjectRoot "venv\Scripts\python.exe"

if (Test-Path $VenvPythonw) {
    $Python = $VenvPythonw
} elseif (Test-Path $VenvPython) {
    $Python = $VenvPython
} else {
    $Python = "python"
}

Start-Process `
    -FilePath $Python `
    -ArgumentList "`"$Launcher`"" `
    -WorkingDirectory $ProjectRoot `
    -WindowStyle Hidden

Write-Host "Started ProductivityGuard."
Write-Host "Dashboard: http://127.0.0.1:5000"
