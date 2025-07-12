@echo off
setlocal enabledelayedexpansion

:: Dat tieu de cho cua so lenh
title Yuuka OCR - Startup Check

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