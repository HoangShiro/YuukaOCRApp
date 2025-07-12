@echo off
setlocal enabledelayedexpansion

:: --- Step 0: Auto-update via Git ---
echo Yuuka: Checking for updates...
git --version >nul 2>nul
if %errorlevel% neq 0 (
    echo   [INFO] Git not found. Skipping auto-update.
) else (
    if exist ".git" (
        echo   Fetching updates from server...
        git fetch origin >nul 2>nul
        if !errorlevel! equ 0 (
            set "LOCAL_HASH="
            set "REMOTE_HASH="
            for /f "delims=" %%i in ('git rev-parse HEAD') do set "LOCAL_HASH=%%i"
            for /f "delims=" %%i in ('git rev-parse origin/main') do set "REMOTE_HASH=%%i"
            if "!LOCAL_HASH!" neq "!REMOTE_HASH!" (
                echo   New version available! Forcing update...
                git reset --hard origin/main >nul
                if !errorlevel! equ 0 (
                    echo     Update successful! Relaunching installer...
                    start "" "%~f0"
                    exit /b
                ) else (
                    echo     [ERROR] Update failed. Please check Git setup.
                    pause
                    exit /b
                )
            ) else (
                echo   Application is up to date.
            )
        )
    )
)
echo.

:: --- Step 1: Check for Python command ---
echo Yuuka: Checking for Python installation...
python --version >nul 2>nul
if %errorlevel% equ 0 goto :InstallWithPython

py --version >nul 2>nul
if %errorlevel% equ 0 goto :InstallWithPy

:: If we reach here, both failed
echo   [ERROR] Neither 'python' nor 'py' command found. Please install Python 3.
pause
exit /b


:InstallWithPython
echo   Python command found: python
echo.
echo Yuuka: Installing required libraries from requirements.txt...
if not exist "requirements.txt" (
    echo [ERROR] requirements.txt not found!
    pause
    exit /b
)
python -m pip install -r requirements.txt
if !errorlevel! neq 0 (
    echo [ERROR] Failed to install libraries. Please check internet or run as Administrator.
    pause
    exit /b
)
echo   All libraries are installed successfully!
echo.
echo Yuuka: All set! Launching the application...
start "Yuuka OCR" /B pythonw.exe main.py
goto :EOF


:InstallWithPy
echo   Python command found: py
echo.
echo Yuuka: Installing required libraries from requirements.txt...
if not exist "requirements.txt" (
    echo [ERROR] requirements.txt not found!
    pause
    exit /b
)
py -m pip install -r requirements.txt
if !errorlevel! neq 0 (
    echo [ERROR] Failed to install libraries. Please check internet or run as Administrator.
    pause
    exit /b
)
echo   All libraries are installed successfully!
echo.
echo Yuuka: All set! Launching the application...
start "Yuuka OCR" /B pyw.exe main.py
goto :EOF