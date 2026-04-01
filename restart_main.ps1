# Restart main.py
$ErrorActionPreference = 'SilentlyContinue'
$projectDir = "D:\PythonApp\mt5-gold-trader"

if (Test-Path "$projectDir\main.pid") {
    $pid = Get-Content "$projectDir\main.pid"
    Stop-Process -Id $pid -Force
    Remove-Item "$projectDir\main.pid"
    Write-Host "Killed main.py (PID: $pid)"
}

Start-Sleep -Seconds 2
Start-Process python -ArgumentList main.py -WindowStyle Normal -WorkingDirectory $projectDir
Write-Host "Started main.py"
