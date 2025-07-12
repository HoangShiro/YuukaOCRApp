@echo off
setlocal enabledelayedexpansion

:: --- Auto-update via Git (Logic giu nguyen, rat tot) ---
echo Yuuka: Checking for updates...
git --version >nul 2>nul
if %errorlevel% neq 0 (
    echo   [INFO] Git not found. Skipping auto-update.
) else (
    if exist ".git" (
        git fetch origin >nul 2>nul
        if !errorlevel! equ 0 (
            git rev-parse HEAD > "%TEMP%\local_hash.tmp"
            git rev-parse origin/main > "%TEMP%\remote_hash.tmp"
            fc "%TEMP%\local_hash.tmp" "%TEMP%\remote_hash.tmp" >nul 2>nul
            if !errorlevel! neq 0 (
                echo   New version available! Forcing update...
                echo   WARNING: Any local code changes will be overwritten.
                git reset --hard origin/main
                if !errorlevel! neq 0 (
                    echo   [ERROR] Update failed. The application will run with the current version.
                ) else (
                    echo   Update successful! You may need to run INSTALL.bat again if there are new dependencies.
                )
            ) else (
                echo   Application is up to date.
            )
        )
    )
)
echo.

:: --- Launch the application from virtual environment ---
set "VENV_PYTHONW=yuuka_venv\Scripts\pythonw.exe"
if not exist "!VENV_PYTHONW!" (
    echo [ERROR] Virtual environment not found.
    echo Please run INSTALL.bat first to set up the application.
    pause
    exit /b
)

echo Launching Yuuka OCR...
start "Yuuka OCR" /B "!VENV_PYTHONW!" main.py

endlocal
exit /b