# Kill main.py
$ErrorActionPreference = 'SilentlyContinue'
$projectDir = "D:\PythonApp\mt5-gold-trader"

if (Test-Path "$projectDir\main.pid") {
    $pid = Get-Content "$projectDir\main.pid"
    Stop-Process -Id $pid -Force
    Remove-Item "$projectDir\main.pid"
    Write-Host "Killed main.py (PID: $pid)"
} else {
    Write-Host "main.pid not found"
}
