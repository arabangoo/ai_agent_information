@echo off
echo ========================================
echo Docker Deployment
echo ========================================
echo.

cd /d C:\git_clone\gemini-react-langgraph-fullstack

echo [1/3] Building Docker image...
echo (This may take 5-10 minutes)
echo.
docker build -t gemini-fullstack-langgraph .
if %errorlevel% neq 0 (
    echo Docker build failed!
    pause
    exit /b 1
)
echo Docker image built successfully

echo.
echo [2/3] Starting Docker Compose...
docker-compose up -d
if %errorlevel% neq 0 (
    echo Docker Compose failed!
    pause
    exit /b 1
)
echo Docker containers started successfully

echo.
echo [3/3] Checking service status...
timeout /t 3 /nobreak >nul
docker-compose ps

echo.
echo ========================================
echo Docker deployment complete!
echo ========================================
echo.
echo Access: http://localhost:8123/app
echo.
echo View logs: docker-compose logs -f langgraph-api
echo Stop: docker-compose down
echo.
pause
