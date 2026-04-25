@echo off
setlocal

echo ==========================================
echo Starting Vigilens Development Environment
echo ==========================================

:: Add local tools to PATH for this session
set "PATH=%PATH%;%CD%\tools"

:: Start Backend
echo Starting Backend (FastAPI)...
start "Backend" cmd /k "cd backend && python -m uvicorn api.main:app --reload --port 8000"

:: Start Frontend
echo Starting Frontend (Next.js)...
start "Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo Both processes have been started in separate windows.
echo ==========================================
pause
