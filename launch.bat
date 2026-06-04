@echo off
color 0a
title ADB Expert Tool Launcher
echo ==========================================
echo    ADB EXPERT TOOL v2.0
echo    Professional Android Control Center
echo ==========================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python 3.8+
    pause
    exit /b 1
)

echo [+] Python found
echo [+] Checking dependencies...

cd /d "%~dp0"

:: Run the tool
echo [+] Starting ADB Expert Tool...
python adb_gui.py

if errorlevel 1 (
    echo.
    echo [ERROR] Application exited with error
    pause
)
