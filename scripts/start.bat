@echo off
setlocal enabledelayedexpansion

rem ============================================================
rem Vigilens - Startup Script (Cloud Mode)
rem
rem This script starts the Vigilens backend and frontend.
rem Docker is NOT required as it uses cloud APIs (Groq/Gemini).
rem
rem Run this from the project root:
rem   scripts\start.bat
rem ============================================================

rem Add local bin to PATH for FFmpeg / yt-dlp
set "PATH=%PATH%;%CD%\bin\ffmpeg-master-latest-win64-gpl\bin"

echo.
echo ============================================================
echo  Vigilens - Startup (Cloud Mode)
echo ============================================================
echo.

rem --- Read .env to get key settings ---
if not exist ".env" (
    echo [ERROR] No .env file found in project root.
    echo         Please copy backend\.env.example to .env and fill in your keys.
    pause
    exit /b 1
)

rem Use PowerShell to read .env
for /f "usebackq tokens=*" %%A in (`powershell -NoProfile -Command "Get-Content '.env' | Where-Object { $_ -notmatch '^\s*#' -and $_ -match '=' } | ForEach-Object { $_.Trim() }"`) do (
    set "%%A"
)

rem Validate GROQ_API_KEY is present
if "!GROQ_API_KEY!"=="" (
    echo [ERROR] GROQ_API_KEY is not set in .env
    echo         Get a free key at https://console.groq.com
    pause
    exit /b 1
)

echo [OK]   GROQ_API_KEY is set.

if "!GOOGLE_API_KEY!"=="" (
    echo [WARN] GOOGLE_API_KEY is missing. Geolocation will use Groq fallback.
) else (
    echo [OK]   GOOGLE_API_KEY is set.
)
echo.

rem ============================================================
rem Start Backend + Frontend locally
rem ============================================================

rem 1/2 - Backend
echo [1/2] Starting Backend (local venv)...
if not exist "backend\.venv" (
    echo [ERROR] Backend virtual environment not found at backend\.venv
    echo         Please run install.bat first.
    pause
    exit /b 1
)

start "Vigilens Backend" cmd /k "cd backend && call .venv\Scripts\activate && set PYTHONUNBUFFERED=1 && python -m uvicorn api.main:app --host 127.0.0.1 --port 8888"

echo       Backend window opened. Waiting 5 seconds...
timeout /t 5 >nul
echo.

rem 2/2 - Frontend
echo [2/2] Starting Frontend (Next.js)...
start "Vigilens Frontend" cmd /k "cd frontend && npm run dev"

echo       Frontend window opened. Waiting 5 seconds...
timeout /t 5 >nul
echo.

rem ============================================================
rem DONE
rem ============================================================
echo ============================================================
echo  Vigilens is booting up!
echo ============================================================
echo  Frontend : http://localhost:3000
echo  Backend  : http://127.0.0.1:8888
echo ============================================================
echo.
echo  Check the two new terminal windows for live logs.
echo.

rem Open browser
start http://localhost:3000

pause
