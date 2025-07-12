@echo off
setlocal enabledelayedexpansion

:: --- Step 0: Auto-update via Git (Logic giu nguyen, rat tot) ---
echo Yuuka: Checking for updates from https://github.com/HoangShiro/YuukaOCRApp.git
git --version >nul 2>nul
if %errorlevel% neq 0 (
    echo   [INFO] Git not found. Skipping auto-update.
) else (
    if not exist ".git" (
        echo   [INFO] This is not a Git repository. Skipping auto-update.
    ) else (
        set "GITIGNORE_FILE=.gitignore"
        set "IGNORE_LINE1=user/"
        set "IGNORE_LINE2=yuuka_venv/"
        findstr /C:"!IGNORE_LINE1!" "!GITIGNORE_FILE!" >nul 2>nul || (echo !IGNORE_LINE1!>>"!GITIGNORE_FILE!")
        findstr /C:"!IGNORE_LINE2!" "!GITIGNORE_FILE!" >nul 2>nul || (echo !IGNORE_LINE2!>>"!GITIGNORE_FILE!")

        echo   Fetching updates from server...
        git fetch origin >nul 2>nul
        if !errorlevel! neq 0 (
            echo   [WARNING] Could not fetch updates. Please check your connection.
        ) else (
            git rev-parse HEAD > "%TEMP%\local_hash.tmp"
            git rev-parse origin/main > "%TEMP%\remote_hash.tmp"
            fc "%TEMP%\local_hash.tmp" "%TEMP%\remote_hash.tmp" >nul 2>nul
            if !errorlevel! neq 0 (
                echo   New version available! Forcing update...
                git reset --hard origin/main >nul 2>nul
                if !errorlevel! neq 0 (
                    echo     [ERROR] Update failed. Please check your Git setup.
                ) else (
                    echo     Update successful! Relaunching installer to check new dependencies...
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
    echo   [ERROR] Python not found! Please install Python 3.
    pause
    exit /b
)
echo   Python is ready!
echo.

:: --- Step 2: Create/Check Virtual Environment ---
set "VENV_DIR=yuuka_venv"
echo Yuuka: Checking for virtual environment...
if not exist "!VENV_DIR!\Scripts\python.exe" (
    echo   Virtual environment not found. Creating one...
    python -m venv !VENV_DIR!
    if !errorlevel! neq 0 (
        echo   [ERROR] Failed to create virtual environment.
        pause
        exit /b
    )
    echo   Virtual environment created successfully.
) else (
    echo   Virtual environment found.
)
echo.

:: --- Step 3: Install libraries from requirements.txt ---
echo Yuuka: Installing/Verifying required libraries...
if not exist "requirements.txt" (
    echo   [ERROR] requirements.txt not found!
    pause
    exit /b
)
"!VENV_DIR!\Scripts\python.exe" -m pip install -r requirements.txt
if !errorlevel! neq 0 (
    echo   [ERROR] Failed to install libraries. Please check your internet or run this as Admin.
    pause
    exit /b
)
echo   All libraries are ready!
echo.

:: --- Step 4: Launch the application ---
echo Yuuka: All set! Launching the application now...
echo (This window will close automatically)

start "Yuuka OCR" /B "!VENV_DIR!\Scripts\pythonw.exe" main.py

endlocal
exit /b