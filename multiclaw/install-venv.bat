@echo off
echo ========================================
echo Installing MultiClaw with Virtual Environment
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] Creating virtual environment...
cd backend
python -m venv .venv
if %errorlevel% neq 0 (
    echo Failed to create virtual environment!
    pause
    exit /b 1
)
echo Virtual environment created.

echo.
echo [2/3] Installing backend (with venv)...
call .venv\Scripts\activate.bat
pip install -e .
if %errorlevel% neq 0 (
    echo Backend installation failed!
    pause
    exit /b 1
)
echo Backend installation complete.
deactivate
cd ..

echo.
echo [3/3] Installing frontend...
cd frontend
call npm install
if %errorlevel% neq 0 (
    echo Frontend installation failed!
    pause
    exit /b 1
)
echo Frontend installation complete.
cd ..

echo.
echo ========================================
echo Installation complete!
echo ========================================
echo.
echo IMPORTANT: Backend uses virtual environment
echo You must activate it before running:
echo   cd backend
echo   .venv\Scripts\activate.bat
echo.
echo Or just use: run-all-venv.bat
echo.
pause
