@echo off
setlocal enabledelayedexpansion

:: --- Step 0: Auto-update via Git ---
echo Yuuka: Checking for updates...
git --version >nul 2>nul
if %errorlevel% equ 0 (
    if exist ".git" (
        git fetch origin >nul 2>nul
        if !errorlevel! equ 0 (
            set "LOCAL_HASH="
            set "REMOTE_HASH="
            for /f "delims=" %%i in ('git rev-parse HEAD') do set "LOCAL_HASH=%%i"
            for /f "delims=" %%i in ('git rev-parse origin/main') do set "REMOTE_HASH=%%i"

            if "!LOCAL_HASH!" neq "!REMOTE_HASH!" (
                echo   New version available! Forcing update...
                echo   (User files in 'user' folder will be preserved.)
                git reset --hard origin/main
                if !errorlevel! equ 0 (
                    echo   Update successful! If the app fails to start, please run INSTALL.bat again.
                ) else (
                    echo   [ERROR] Update failed. Running with the current version.
                )
            ) else (
                echo   Application is up to date.
            )
        )
    )
)
echo.

:: --- Step 1: Check for Virtual Environment and Launch ---
set "VENV_PYTHONW=yuuka_venv\Scripts\pythonw.exe"
if not exist "!VENV_PYTHONW!" (
    echo [ERROR] Application is not installed correctly.
    echo Please run INSTALL.bat first to set up all necessary components.
    pause
    exit /b
)

echo Launching Yuuka OCR...
start "Yuuka OCR" /B "!VENV_PYTHONW!" main.py

endlocal
exit /b