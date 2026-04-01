# Restart dashboard.py
$ErrorActionPreference = 'SilentlyContinue'
$projectDir = "D:\PythonApp\mt5-gold-trader"

if (Test-Path "$projectDir\dashboard.pid") {
    $pid = Get-Content "$projectDir\dashboard.pid"
    Stop-Process -Id $pid -Force
    Remove-Item "$projectDir\dashboard.pid"
    Write-Host "Killed dashboard.py (PID: $pid)"
}

Start-Sleep -Seconds 2
Start-Process python -ArgumentList dashboard.py -WindowStyle Normal -WorkingDirectory $projectDir
Write-Host "Started dashboard.py"
