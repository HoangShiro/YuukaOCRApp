@echo off
setlocal enabledelayedexpansion

:: Start main.py with pythonw.exe to hide the console window completely
start "Yuuka OCR" /B pythonw main.py

:: End of script
endlocal
exit /b