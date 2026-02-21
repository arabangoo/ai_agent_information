@echo off
chcp 65001 >nul 2>&1
cls
echo ========================================
echo Installing MultiClaw (멀티클로)
echo ========================================
echo.

cd /d "%~dp0"

echo [1/2] Installing backend dependencies...
cd backend
pip install --user -e .
if %errorlevel% neq 0 (
    echo ERROR: Backend installation failed
    echo.
    echo Try running as Administrator or check Python installation
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
echo 1. Configure backend\.env with API keys
echo 2. Run run-all.bat
echo.
pause
