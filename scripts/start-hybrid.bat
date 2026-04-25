@echo off
setlocal enabledelayedexpansion

:: ============================================================
:: Vigilens - Hybrid Mode
::
:: Reads INFERENCE_MODE from .env in the project root:
::   INFERENCE_MODE=online  -> Groq cloud mode (no Docker needed)
::   INFERENCE_MODE=offline -> Local Docker mode (Ollama + DeepSafe)
::
:: Run this from the project root:
::   scripts\start-hybrid.bat
:: ============================================================

:: Add local bin to PATH for FFmpeg / yt-dlp
set "PATH=%PATH%;%CD%\bin\ffmpeg-master-latest-win64-gpl\bin"

echo.
echo ============================================================
echo  Vigilens - Hybrid Mode
echo ============================================================
echo.

:: ── Read .env to get INFERENCE_MODE and key settings ──────────────────────
set "INFERENCE_MODE=offline"
set "WHISPER_USE_GROQ=false"
set "GROQ_API_KEY="

if not exist ".env" (
    echo [WARN] No .env file found in project root.
    echo        Copy backend\.env.example to .env and fill in your values.
    echo        Defaulting to INFERENCE_MODE=offline.
    echo.
) else (
    :: Use PowerShell to read .env — handles UTF-8 BOM, quoted values, and
    :: inline comments correctly. Outputs lines as KEY=VALUE for cmd to consume.
    for /f "usebackq tokens=*" %%A in (`powershell -NoProfile -Command "Get-Content '.env' | Where-Object { $_ -notmatch '^\s*#' -and $_ -match '=' } | ForEach-Object { $_.Trim() }"`) do (
        set "%%A"
    )
)

echo [INFO] Detected INFERENCE_MODE=!INFERENCE_MODE!
echo.

:: ── Route to the correct startup mode ─────────────────────────────────────
if /i "!INFERENCE_MODE!"=="online" goto :groq_mode
if /i "!INFERENCE_MODE!"=="offline" goto :offline_mode

echo [WARN] Unrecognised INFERENCE_MODE=!INFERENCE_MODE! in .env
echo        Supported values: online, offline. Defaulting to offline.
set "INFERENCE_MODE=offline"
goto :offline_mode


:: ══════════════════════════════════════════════════════════════════════════
:: OFFLINE MODE — Ollama + DeepSafe via Docker
:: ══════════════════════════════════════════════════════════════════════════
:offline_mode
echo [MODE] OFFLINE — Starting Docker infrastructure (Ollama + DeepSafe)
echo.

:: Check Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not installed or not in PATH.
    echo         Install Docker Desktop: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

:: Check Docker daemon is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker daemon is not running.
    echo         Please start Docker Desktop and try again.
    pause
    exit /b 1
)

:: 1/4 — Start Docker infrastructure
echo [1/4] Starting Docker containers (Ollama + DeepSafe)...
docker compose up -d ollama deepsafe
if %errorlevel% neq 0 (
    echo [ERROR] Failed to start Docker infrastructure.
    echo         Run "docker compose logs" to see what went wrong.
    pause
    exit /b 1
)
echo       Containers started.
echo.

:: 2/4 — Pull Ollama model if needed
echo [2/4] Ensuring Ollama model (gemma4:e4b) is ready...
echo       This may take several minutes on first run (model download).
docker exec openloop-ol08-ollama-1 ollama pull gemma4:e4b
echo.

goto :start_app


:: ══════════════════════════════════════════════════════════════════════════
:: ONLINE / GROQ MODE — no Docker needed
:: ══════════════════════════════════════════════════════════════════════════
:groq_mode
echo [MODE] ONLINE (Groq) — Docker NOT required. Skipping Ollama + DeepSafe.
echo.

:: Validate GROQ_API_KEY is present
if "!GROQ_API_KEY!"=="" (
    echo [ERROR] INFERENCE_MODE=online but GROQ_API_KEY is not set in .env
    echo         Add your key:  GROQ_API_KEY=gsk_...
    echo         Get a free key at https://console.groq.com
    pause
    exit /b 1
)

echo [OK]   GROQ_API_KEY is set (starts with: !GROQ_API_KEY:~0,7!...)

:: Warn if Groq Whisper is not enabled
if /i "!WHISPER_USE_GROQ!"=="true" (
    echo [OK]   WHISPER_USE_GROQ=true — transcription uses Groq Whisper API
) else (
    echo [WARN] WHISPER_USE_GROQ is not true in .env
    echo        Transcription will fall back to the local Whisper model ^(slow on first run^)
    echo        Add  WHISPER_USE_GROQ=true  to .env to use Groq Whisper instead.
)
echo.

echo [1/4] Skipping Docker — Groq cloud handles LLM + Whisper.
echo [2/4] Skipping Ollama model pull — not needed in Groq mode.
echo.


:: ══════════════════════════════════════════════════════════════════════════
:: COMMON — Start Backend + Frontend locally
:: ══════════════════════════════════════════════════════════════════════════
:start_app

:: 3/4 — Backend
echo [3/4] Starting Backend (local venv)...
if not exist "backend\.venv" (
    echo [ERROR] Backend virtual environment not found at backend\.venv
    echo         Please run install.bat first to set up the project.
    pause
    exit /b 1
)

start "Vigilens Backend [!INFERENCE_MODE!]" cmd /k "cd backend && echo [BACKEND] Activating virtual environment... && call .venv\Scripts\activate && set PYTHONUNBUFFERED=1 && echo [BACKEND] Starting uvicorn on port 8888 ^(INFERENCE_MODE=!INFERENCE_MODE!^)... && python -m uvicorn api.main:app --host 127.0.0.1 --port 8888 --log-level debug"

echo       Backend window opened. Waiting 6 seconds to initialize...
timeout /t 6 >nul
echo.

:: 4/4 — Frontend
echo [4/4] Starting Frontend (Next.js)...
start "Vigilens Frontend" cmd /k "cd frontend && echo [FRONTEND] Starting Next.js dev server... && npm run dev"

echo       Frontend window opened. Waiting 5 seconds to boot...
timeout /t 5 >nul
echo.


:: ══════════════════════════════════════════════════════════════════════════
:: DONE
:: ══════════════════════════════════════════════════════════════════════════
echo ============================================================
echo  Vigilens is booting up!
echo ============================================================
echo.
echo  Mode     : !INFERENCE_MODE!
echo  Frontend : http://localhost:3000
echo  Backend  : http://127.0.0.1:8888
if /i "!INFERENCE_MODE!"=="offline" (
    echo  Ollama   : http://localhost:11434
    echo  DeepSafe : http://localhost:8001
    echo.
    echo  To stop Docker containers: docker compose down
) else (
    echo  LLM      : Groq cloud ^(llama-3.3-70b-versatile^)
    echo  Whisper  : Groq cloud ^(whisper-large-v3-turbo^)
    echo.
    echo  No Docker containers to stop.
)
echo.
echo  Check the two new terminal windows for live logs.
echo ============================================================
echo.

:: Open browser after a short delay
timeout /t 5 >nul
start http://localhost:3000

pause
