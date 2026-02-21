@echo off
chcp 65001 >nul 2>&1
cls
echo ========================================
echo Fixing AI Images
echo ========================================
echo.

cd /d "%~dp0"

echo Copying AI images to frontend/public/ai_image...

if not exist "frontend\public\ai_image" mkdir "frontend\public\ai_image"

copy /Y "ai_image\ChatGPT_Image.png" "frontend\public\ai_image\ChatGPT_Image.png" >nul
copy /Y "ai_image\Claude_Image.png" "frontend\public\ai_image\Claude_Image.png" >nul
copy /Y "ai_image\Gemini_Image.png" "frontend\public\ai_image\Gemini_Image.png" >nul

echo.
echo ========================================
echo Images copied successfully!
echo ========================================
echo.
echo Files copied:
dir /B "frontend\public\ai_image\*.png"
echo.
echo Please restart the frontend server:
echo 1. Close the frontend terminal
echo 2. Run: run-frontend.bat
echo.
echo Or restart everything:
echo - Close all terminals
echo - Run: run-all.bat
echo.
pause
