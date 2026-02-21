@echo off
echo ========================================
echo Starting MultiClaw (venv)
echo ========================================
echo.

cd /d "%~dp0"

echo [1/2] Starting backend server (with venv)...
start "MultiClaw Backend" cmd /k "cd /d %~dp0\backend && .venv\Scripts\activate.bat && echo Backend: http://localhost:8000 && python main.py"

echo Waiting for backend to start...
timeout /t 5 /nobreak >nul

echo.
echo [2/2] Starting frontend server...
start "MultiClaw Frontend" cmd /k "cd /d %~dp0\frontend && echo Frontend: http://localhost:5173 && npm run dev"

echo.
echo ========================================
echo Servers started!
echo ========================================
echo.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
echo.
echo Open http://localhost:5173 in your browser!
echo.
pause
