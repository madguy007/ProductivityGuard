$ErrorActionPreference = "Stop"

$TaskName = "ProductivityGuard"
$StartupShortcut = Join-Path ([Environment]::GetFolderPath("Startup")) "$TaskName.lnk"

$Task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($Task) {
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Removed $TaskName startup task."
} else {
    Write-Host "$TaskName startup task was not installed."
}

if (Test-Path $StartupShortcut) {
    Remove-Item -Path $StartupShortcut -Force
    Write-Host "Removed Startup shortcut: $StartupShortcut"
}
