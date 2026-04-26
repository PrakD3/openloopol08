@echo off
:: ============================================================
:: Vigilens — Online Mode Setup Script (Windows)
:: Usage: scripts\start-online.bat
:: ============================================================

title Vigilens — Online Mode
color 0B

echo.
echo   VIGILENS — Online Mode Setup
echo   ==============================
echo   Cloud APIs, No Docker Needed
echo.

:: ── Check prerequisites ──────────────────────────────────────────────────────

echo [1/5] Checking prerequisites...

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python 3.11+ is required.
    echo Download from: https://python.org
    pause & exit /b 1
)
for /f "tokens=2" %%v in ('python --version') do echo   OK Python %%v

node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Node.js 18+ is required.
    echo Download from: https://nodejs.org
    pause & exit /b 1
)
for /f %%v in ('node --version') do echo   OK Node.js %%v

ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: FFmpeg is required for video processing.
    echo Download from: https://ffmpeg.org/download.html
    echo Then add ffmpeg\bin to your PATH.
    pause & exit /b 1
)
echo   OK FFmpeg found

:: ── Backend .env ─────────────────────────────────────────────────────────────

echo.
echo [2/5] Setting up backend environment...

if not exist "backend\.env" (
    copy "backend\.env.example" "backend\.env" >nul
    echo   Created backend\.env from template
    echo.
    echo   !!! IMPORTANT: Open backend\.env and fill in GROQ_API_KEY
    echo   Get a free key at: https://console.groq.com
    echo.
    start notepad "backend\.env"
    echo   Notepad is open. Save the file, then press any key to continue...
    pause >nul
) else (
    echo   backend\.env already exists
)

if not exist "frontend\.env.local" (
    copy "frontend\.env.example" "frontend\.env.local" >nul
    :: Set app mode to real
    powershell -Command "(Get-Content 'frontend\.env.local') -replace 'NEXT_PUBLIC_APP_MODE=.*','NEXT_PUBLIC_APP_MODE=real' | Set-Content 'frontend\.env.local'"
    echo   Created frontend\.env.local
) else (
    echo   frontend\.env.local already exists
)

:: ── Python dependencies ──────────────────────────────────────────────────────

echo.
echo [3/5] Installing Python dependencies (online mode - no local Whisper)...

cd backend

if not exist ".venv" (
    python -m venv .venv
    echo   Created .venv
)

call .venv\Scripts\activate.bat
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements-online.txt
if %errorlevel% neq 0 (
    echo ERROR: pip install failed. Check your internet connection and Python version.
    pause & exit /b 1
)
echo   Python packages installed
cd ..

:: ── Frontend dependencies ────────────────────────────────────────────────────

echo.
echo [4/5] Installing frontend dependencies...
cd frontend
call npm install --silent
if %errorlevel% neq 0 (
    echo ERROR: npm install failed.
    pause & exit /b 1
)
echo   npm packages installed
cd ..

:: ── Launch ───────────────────────────────────────────────────────────────────

echo.
echo [5/5] Starting Vigilens...
echo.
echo   Backend  -^> http://localhost:8000
echo   Frontend -^> http://localhost:3000
echo   API Docs -^> http://localhost:8000/docs
echo.
echo   Two terminal windows will open. Close them to stop the servers.
echo.

:: Open backend in new window
start "Vigilens Backend" cmd /k "cd backend && .venv\Scripts\activate.bat && uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload"

:: Small delay so backend starts first
timeout /t 2 /nobreak >nul

:: Open frontend in new window
start "Vigilens Frontend" cmd /k "cd frontend && npm run dev"

echo   Servers started! Opening browser...
timeout /t 3 /nobreak >nul
start http://localhost:3000
