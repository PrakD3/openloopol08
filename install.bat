@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo Vigilens Clean Install Script
echo ==========================================

:: Check for FFmpeg
echo [0/2] Checking for FFmpeg...
set "FFMPEG_FOUND=0"

:: 1. Check if it's already in the system PATH
where ffmpeg >nul 2>nul
if !ERRORLEVEL! EQU 0 (
    echo   - FFmpeg found in system PATH.
    set "FFMPEG_FOUND=1"
)

:: 2. Check if it's in our project tools folder
if !FFMPEG_FOUND! EQU 0 (
    if exist "tools\ffmpeg.exe" (
        echo   - FFmpeg found in project tools folder.
        set "FFMPEG_LOCAL_PATH=%CD%\tools"
        set "PATH=!PATH!;!FFMPEG_LOCAL_PATH!"
        set "FFMPEG_FOUND=1"
        
        :: Try to add to permanent User PATH (Fail-safe)
        echo   - Attempting to add tools folder to permanent User PATH...
        powershell -Command "$oldPath = [Environment]::GetEnvironmentVariable('Path', 'User'); $newPath = '%CD%\tools'; if ($oldPath -notlike '*'+$newPath+'*') { [Environment]::SetEnvironmentVariable('Path', $oldPath + ';' + $newPath, 'User') }"
    )
)

:: 3. If still not found, then download
if !FFMPEG_FOUND! EQU 0 (
    echo   - FFmpeg not found. Attempting to install...
    
    :: Try winget first
    where winget >nul 2>nul
    if !ERRORLEVEL! EQU 0 (
        echo   - Attempting winget install...
        winget install ffmpeg --silent --accept-source-agreements --accept-package-agreements
        where ffmpeg >nul 2>nul
        if !ERRORLEVEL! EQU 0 (
            echo   - FFmpeg installed successfully via winget!
            set "FFMPEG_FOUND=1"
            goto :ffmpeg_done
        )
    )

    :: Fallback: PowerShell Download
    echo   - winget not available or failed. Downloading FFmpeg via PowerShell...
    if not exist "tools" mkdir tools
    powershell -Command "& { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $url = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip'; $dest = 'tools\ffmpeg.zip'; Invoke-WebRequest -Uri $url -OutFile $dest; Expand-Archive -Path $dest -DestinationPath 'tools\ffmpeg-temp' -Force; Move-Item -Path 'tools\ffmpeg-temp\ffmpeg-*-essentials_build\bin\*' -Destination 'tools\' -Force; Remove-Item -Path 'tools\ffmpeg.zip', 'tools\ffmpeg-temp' -Recurse -Force }"
    
    if exist "tools\ffmpeg.exe" (
        echo   - FFmpeg downloaded to project tools folder.
        set "FFMPEG_LOCAL_PATH=%CD%\tools"
        set "PATH=!PATH!;!FFMPEG_LOCAL_PATH!"
        
        :: Add to permanent User PATH
        echo   - Adding tools folder to permanent User PATH...
        powershell -Command "$oldPath = [Environment]::GetEnvironmentVariable('Path', 'User'); $newPath = '%CD%\tools'; if ($oldPath -notlike '*'+$newPath+'*') { [Environment]::SetEnvironmentVariable('Path', $oldPath + ';' + $newPath, 'User') }"
        
        set "FFMPEG_FOUND=1"
    ) else (
        echo   [!] ERROR: Failed to download FFmpeg. Please install it manually from https://ffmpeg.org/
        pause
        exit /b 1
    )
)

:ffmpeg_done
echo.
:: Frontend Cleanup and Install
echo [1/2] Resetting Frontend...
cd frontend

:: Detect Package Manager
set PKG_MANAGER=npm
if exist pnpm-lock.yaml (
    set PKG_MANAGER=pnpm
    echo   - Detected pnpm-lock.yaml, using pnpm...
) else if exist package-lock.json (
    set PKG_MANAGER=npm
    echo   - Detected package-lock.json, using npm...
) else (
    where pnpm >nul 2>nul
    if !ERRORLEVEL! EQU 0 (
        set PKG_MANAGER=pnpm
        echo   - No lockfile found, but pnpm detected. Using pnpm...
    ) else (
        echo   - No lockfile found, using npm...
    )
)

if exist node_modules (
    echo   - Deleting node_modules...
    rmdir /s /q node_modules
)
if exist .next (
    echo   - Deleting .next build cache...
    rmdir /s /q .next
)

echo   - Installing frontend dependencies with !PKG_MANAGER!...
call !PKG_MANAGER! install
if !ERRORLEVEL! NEQ 0 (
    echo ERROR: Frontend installation failed.
    pause
    exit /b !ERRORLEVEL!
)
cd ..

echo.
:: Backend Cleanup and Install
echo [2/2] Resetting Backend...
cd backend
if exist .venv (
    echo   - Deleting existing .venv...
    rmdir /s /q .venv
)
echo   - Creating new virtual environment...
python -m venv .venv
if !ERRORLEVEL! NEQ 0 (
    echo ERROR: Failed to create virtual environment. Make sure Python is installed.
    pause
    exit /b !ERRORLEVEL!
)

echo   - Upgrading core build tools...
call .venv\Scripts\activate && python -m pip install --upgrade pip
call .venv\Scripts\activate && pip install wheel setuptools setuptools-rust
if !ERRORLEVEL! NEQ 0 (
    echo ERROR: Failed to upgrade build tools.
    pause
    exit /b !ERRORLEVEL!
)

:: Installing Whisper from GitHub
echo   - Installing OpenAI Whisper from GitHub...
call .venv\Scripts\activate && pip install git+https://github.com/openai/whisper.git
if !ERRORLEVEL! NEQ 0 (
    echo ERROR: Failed to install Whisper from GitHub. Trying fallback to PyPI...
    call .venv\Scripts\activate && pip install openai-whisper --no-build-isolation
)

echo   - Installing remaining backend dependencies...
call .venv\Scripts\activate && pip install -r requirements.txt
call .venv\Scripts\activate && pip install pydantic-settings
if !ERRORLEVEL! NEQ 0 (
    echo ERROR: Backend dependencies installation failed.
    pause
    exit /b !ERRORLEVEL!
)
cd ..

echo.
echo ==========================================
echo SUCCESS: All dependencies installed cleanly!
echo You can now use run.bat to start the project.
echo ==========================================
pause
