@echo off
setlocal

echo ==========================================
echo Starting Vigilens Development Environment
echo ==========================================

:: Add local tools to PATH for this session
set "PATH=%PATH%;%CD%\tools"

:: Start Backend
echo Starting Backend (FastAPI)...
start "Gaand Chal Raha hai" cmd /k "cd backend && call .venv\Scripts\activate && python -m uvicorn api.main:app --reload --port 8000"

:: Start Frontend
echo Starting Frontend (Next.js)...
start "Samne app ho" cmd /k "cd frontend && pnpm dev"

echo.
echo Both processes have been started in separate windows.
echo ==========================================
pause
