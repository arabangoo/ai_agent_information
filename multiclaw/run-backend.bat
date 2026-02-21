@echo off
chcp 65001 >nul 2>&1
cls
echo ========================================
echo Starting MultiClaw Backend
echo ========================================
echo.

cd /d "%~dp0\backend"

echo Checking Python version...
python --version
echo.

echo Starting backend server...
python main.py

pause
