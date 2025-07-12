@echo off
setlocal

:: --- Launching Application ---
echo Yuuka: Launching application...
echo   (Update checks are now handled within the app)
echo.

:: --- Find Python command and Launch ---
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
start "Yuuka OCR" /B pythonw.exe main.py
goto :EOF


:LaunchWithPy
start "Yuuka OCR" /B pyw.exe main.py
goto :EOF