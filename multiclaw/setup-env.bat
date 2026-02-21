@echo off
chcp 65001 >nul 2>&1
cls
echo ========================================
echo Environment Setup for MultiClaw
echo ========================================
echo.

cd /d "%~dp0"

REM Backup existing files
if exist "backend\.env" (
    echo Found existing backend\.env
    copy "backend\.env" "backend\.env.backup" >nul 2>&1
    echo Backed up to backend\.env.backup
)

if exist ".env" (
    echo Found existing .env
    copy ".env" ".env.backup" >nul 2>&1
    echo Backed up to .env.backup
)

echo.
echo Please enter your API keys:
echo.

set /p openai_key="OpenAI API Key (sk-...): "
set /p anthropic_key="Anthropic API Key (sk-ant-...): "
set /p gemini_key="Gemini API Key (AIzaSy...): "
set /p perplexity_key="Perplexity API Key (pplx-...) [optional]: "

echo.
echo Creating backend\.env...

REM Delete old file first
if exist "backend\.env" del "backend\.env"

REM Create new backend/.env
echo # MultiClaw - API Keys > backend\.env
echo OPENAI_API_KEY=%openai_key% >> backend\.env
echo ANTHROPIC_API_KEY=%anthropic_key% >> backend\.env
echo GEMINI_API_KEY=%gemini_key% >> backend\.env
echo. >> backend\.env
echo # Perplexity API (for Agent web search) >> backend\.env
echo PERPLEXITY_API_KEY=%perplexity_key% >> backend\.env
echo. >> backend\.env
echo # File Search Store (auto-generated on first run) >> backend\.env
echo FILE_SEARCH_STORE_NAME= >> backend\.env
echo. >> backend\.env
echo # Server Settings >> backend\.env
echo HOST=0.0.0.0 >> backend\.env
echo PORT=8000 >> backend\.env

echo Created backend\.env

echo.
echo Creating .env...

REM Delete old file first
if exist ".env" del ".env"

REM Create new .env
echo # MultiClaw - API Keys (Docker) > .env
echo OPENAI_API_KEY=%openai_key% >> .env
echo ANTHROPIC_API_KEY=%anthropic_key% >> .env
echo GEMINI_API_KEY=%gemini_key% >> .env
echo PERPLEXITY_API_KEY=%perplexity_key% >> .env
echo. >> .env
echo # File Search Store >> .env
echo FILE_SEARCH_STORE_NAME= >> .env
echo. >> .env
echo # Optional: LangSmith (for monitoring) >> .env
echo LANGSMITH_API_KEY= >> .env

echo Created .env

echo.
echo ========================================
echo SUCCESS! Configuration files created!
echo ========================================
echo.
echo Created files:
echo - backend\.env (for local development)
echo - .env (for Docker deployment)
echo.
echo Next steps:
echo 1. Run install-simple.bat (install dependencies)
echo 2. Run run-all.bat (start service)
echo.
pause
