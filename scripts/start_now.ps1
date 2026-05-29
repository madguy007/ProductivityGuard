$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Launcher = Join-Path $ProjectRoot "launch_productivityguard.py"
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

Start-Process `
    -FilePath $Python `
    -ArgumentList "`"$Launcher`"" `
    -WorkingDirectory $ProjectRoot `
    -WindowStyle Hidden

Write-Host "Started ProductivityGuard."
Write-Host "Dashboard: http://127.0.0.1:5000"
