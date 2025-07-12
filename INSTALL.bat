@echo off
setlocal enabledelayedexpansion

:: Dat tieu de cho cua so lenh
title Yuuka OCR - Startup Check

:: --- Step 0: Auto-update via Git ---
echo Yuuka: Checking for updates from https://github.com/HoangShiro/YuukaOCRApp.git
git --version >nul 2>nul
if %errorlevel% neq 0 (
    echo   [INFO] Git not found. Skipping auto-update.
    echo   To enable auto-updates, please install Git from https://git-scm.com/
) else (
    if not exist ".git" (
        echo   [INFO] This is not a Git repository. Skipping auto-update.
        echo   To enable auto-updates, please clone the project using:
        echo   git clone https://github.com/HoangShiro/YuukaOCRApp.git
    ) else (
        :: Ensure user files are ignored to prevent pull conflicts
        set "GITIGNORE_FILE=.gitignore"
        set "IGNORE_LINE1=user/user_config.json"
        set "IGNORE_LINE2=user/ui.png"
        set "IGNORE_LINE3=user/.env"

        findstr /C:"!IGNORE_LINE1!" "!GITIGNORE_FILE!" >nul 2>nul || (echo !IGNORE_LINE1!>>"!GITIGNORE_FILE!")
        findstr /C:"!IGNORE_LINE2!" "!GITIGNORE_FILE!" >nul 2>nul || (echo !IGNORE_LINE2!>>"!GITIGNORE_FILE!")
        findstr /C:"!IGNORE_LINE3!" "!GITIGNORE_FILE!" >nul 2>nul || (echo !IGNORE_LINE3!>>"!GITIGNORE_FILE!")

        :: Fetch latest changes from remote
        echo   Fetching updates from server...
        git fetch origin >nul 2>nul
        if !errorlevel! neq 0 (
            echo   [WARNING] Could not fetch updates. Please check your connection.
        ) else (
            for /f "delims=" %%i in ('git rev-parse HEAD') do set "LOCAL_HASH=%%i"
            for /f "delims=" %%i in ('git rev-parse origin/main') do set "REMOTE_HASH=%%i"

            if "!LOCAL_HASH!" neq "!REMOTE_HASH!" (
                echo   New version available! Forcing update to match the repository...
                echo   (Local changes to app code will be overwritten. User files are safe.)
                git reset --hard origin/main >nul 2>nul
                if !errorlevel! neq 0 (
                    echo     [ERROR] Update failed. Please check your Git setup or report an issue.
                ) else (
                    echo     Update successful! Relaunching the installer to check new dependencies...
                    start "" "%~f0"
                    exit /b
                )
            ) else (
                echo   Application is up to date.
            )
        )
    )
)
echo.

echo Yuuka: Preparing to launch...
echo.

:: --- Step 1: Check for Python ---
echo Yuuka: Checking for Python...
python --version >nul 2>nul
if %errorlevel% neq 0 (
    echo   [ERROR] Python not found!
    echo   Please install Python 3 and add it to the system PATH.
    pause
    exit /b
)
echo   Python is ready!
echo.

:: --- Step 2: Define required libraries ---
set "requirements=PySide6 numpy python-dotenv pyperclip Pillow google-generativeai pywin32 psutil opencv-python pynput"

:: --- Step 3: Check and install libraries ---
echo Yuuka: Checking for required libraries...
echo.

for %%r in (%requirements%) do (
    echo   Checking library: %%r
    pip show %%r >nul 2>nul
    if !errorlevel! neq 0 (
        echo Not found. Installing %%r...
        pip install %%r
        if !errorlevel! neq 0 (
            echo     [ERROR] Failed to install %%r. Please check your internet connection or try a manual installation.
            pause
            exit /b
        ) else (
            echo Successfully installed %%r!
        )
    ) else (
        echo Already installed.
    )
    echo.
)

:: --- Step 4: Launch the application ---
echo Yuuka: All set! Launching the application now...
echo (This window will close automatically)

:: Start main.py with pythonw.exe to hide the console window completely
start "Yuuka OCR" /B pythonw main.py

:: End of script
endlocal
exit /b