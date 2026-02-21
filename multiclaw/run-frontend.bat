@echo off
chcp 65001 >nul 2>&1
cls
echo ========================================
echo Starting MultiClaw Frontend
echo ========================================
echo.

cd /d "%~dp0\frontend"

echo Checking Node.js version...
node --version
echo.

echo Starting frontend server...
npm run dev

pause
