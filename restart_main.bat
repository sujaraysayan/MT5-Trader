@echo off
cd /d D:\PythonApp\mt5-gold-trader
if exist main.pid (
    for /f %%i in (main.pid) do taskkill /F /PID %%i 2>nul
    del main.pid
)
timeout /t 2 >nul
start python main.py
