@echo off
setlocal enabledelayedexpansion

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
echo Yuuka: All set! Launching the application for the first time...
echo   (You can use RUN.bat for subsequent launches)
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
echo Yuuka: All set! Launching the application for the first time...
echo   (You can use RUN.bat for subsequent launches)
start "Yuuka OCR" /B pyw.exe main.py
goto :EOF