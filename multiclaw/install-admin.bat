@echo off
:: Check for admin rights
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting Administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

chcp 65001 >nul 2>&1
cls
echo ========================================
echo Installing MultiClaw (Admin)
echo ========================================
echo.

cd /d "%~dp0"

echo [1/2] Installing backend dependencies...
cd backend
pip install -e .
if %errorlevel% neq 0 (
    echo ERROR: Backend installation failed
    pause
    exit /b 1
)
echo Backend installation completed!
echo.

cd ..

echo [2/2] Installing frontend dependencies...
cd frontend
call npm install
if %errorlevel% neq 0 (
    echo ERROR: Frontend installation failed
    pause
    exit /b 1
)
echo Frontend installation completed!
echo.

cd ..

echo ========================================
echo Installation completed successfully!
echo ========================================
echo.
echo Next steps:
echo 1. Run setup-env.bat (configure API keys)
echo 2. Run run-all.bat (start service)
echo.
pause
