@echo off
chcp 65001 >nul 2>&1
cls
echo ========================================
echo Starting MultiClaw (멀티클로)
echo ========================================
echo.

cd /d "%~dp0"

echo [1/2] Starting backend server...
start "MultiClaw Backend" cmd /k "cd /d %~dp0\backend && python main.py"

timeout /t 3 /nobreak >nul

echo [2/2] Starting frontend server...
start "MultiClaw Frontend" cmd /k "cd /d %~dp0\frontend && npm run dev"

echo.
echo ========================================
echo Service started successfully!
echo ========================================
echo.
echo Frontend: http://localhost:5173
echo Backend: http://localhost:8000
echo.
echo Close terminal windows to stop services.
pause
