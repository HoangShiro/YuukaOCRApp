@echo off
setlocal enabledelayedexpansion

:: --- Step 0: Auto-update via Git ---
echo Yuuka: Checking for updates...
:: Kiem tra xem git co duoc cai dat khong
git --version >nul 2>nul
if %errorlevel% neq 0 (
    echo   [INFO] Git not found. Skipping auto-update.
) else (
    :: Kiem tra xem day co phai la repo git khong
    if not exist ".git" (
        echo   [INFO] This is not a Git repository. Skipping auto-update.
    ) else (
        echo   Fetching updates from server...
        git fetch origin >nul 2>nul
        if !errorlevel! neq 0 (
            echo   [WARNING] Could not fetch updates. Please check your connection.
        ) else (
            set "LOCAL_HASH="
            set "REMOTE_HASH="
            for /f "delims=" %%i in ('git rev-parse HEAD') do set "LOCAL_HASH=%%i"
            for /f "delims=" %%i in ('git rev-parse origin/main') do set "REMOTE_HASH=%%i"

            if "!LOCAL_HASH!" neq "!REMOTE_HASH!" (
                echo   New version available! Forcing update to match the repository...
                :: Lenh nay se cap nhat cac file duoc theo doi va bo qua cac file khong duoc theo doi
                git reset --hard origin/main >nul
                if !errorlevel! neq 0 (
                    echo     [ERROR] Update failed. Please check Git setup or report an issue.
                    pause
                    exit /b
                ) else (
                    echo     Update successful! Relaunching installer to check for new dependencies...
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

:: --- Step 1: Check for Python ---
echo Yuuka: Checking for Python installation...
set "PYTHON_CMD=python"
%PYTHON_CMD% --version >nul 2>nul
if !errorlevel! neq 0 (
    set "PYTHON_CMD=py"
    %PYTHON_CMD% --version >nul 2>nul
    if !errorlevel! neq 0 (
        echo   [ERROR] Neither 'python' nor 'py' command found. Please install Python 3.
        pause
        exit /b
    )
)
echo   Python command found: !PYTHON_CMD!
echo.

:: --- Step 2: Install Dependencies ---
echo Yuuka: Installing required libraries from requirements.txt...
if not exist "requirements.txt" (
    echo   [ERROR] requirements.txt not found! The application cannot be installed.
    pause
    exit /b
)
!PYTHON_CMD! -m pip install -r requirements.txt
if !errorlevel! neq 0 (
    echo   [ERROR] Failed to install libraries. Please check internet or run as Administrator.
    pause
    exit /b
)
echo   All libraries are installed successfully!
echo.

:: --- Step 3: Launch Application ---
echo Yuuka: All set! Launching the application...
echo (This window will close automatically)

set "PYTHONW_CMD=!PYTHON_CMD!w.exe"
start "Yuuka OCR" /B !PYTHONW_CMD! main.py

endlocal
exit /b