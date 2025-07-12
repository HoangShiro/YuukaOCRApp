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
                git reset --hard origin/main
                if !errorlevel! equ 0 (
                    echo   Update successful! Run INSTALL.bat if you encounter issues.
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

:: --- Step 1: Find Python command and Launch ---
python --version >nul 2>nul
if %errorlevel% equ 0 goto :LaunchWithPython

py --version >nul 2>nul
if %errorlevel% equ 0 goto :LaunchWithPy

:: If we reach here, both failed
echo [ERROR] Neither 'python' nor 'py' command found.
echo Please run INSTALL.bat first.
pause
exit /b


:LaunchWithPython
echo Launching Yuuka OCR using 'python'...
start "Yuuka OCR" /B pythonw.exe main.py
goto :EOF


:LaunchWithPy
echo Launching Yuuka OCR using 'py'...
start "Yuuka OCR" /B pyw.exe main.py
goto :EOF