@echo off
setlocal enabledelayedexpansion

:: Chuyen den thu muc goc cua script
cd /d "%~dp0"

echo Yuuka: Kiem tra Python...
python --version >nul 2>nul
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
    goto :InstallLibs
)

py --version >nul 2>nul
if %errorlevel% equ 0 (
    set PYTHON_CMD=py
    goto :InstallLibs
)

echo [LOI] Khong tim thay 'python' hoac 'py'.
echo Senpai hay cai dat Python 3 (va nho tick vao "Add Python to PATH" nhe).
pause
exit /b

:InstallLibs
echo   Da tim thay: %PYTHON_CMD%
echo.
echo Yuuka: Dang cai dat cac thu vien can thiet tu requirements.txt...
if not exist "requirements.txt" (
    echo [LOI] Khong tim thay file requirements.txt!
    pause
    exit /b
)

%PYTHON_CMD% -m pip install -r requirements.txt
if !errorlevel! neq 0 (
    echo [LOI] Cai dat thu vien that bai.
    echo Senpai hay kiem tra ket noi mang hoac thu chay file nay voi quyen Administrator nhe.
    pause
    exit /b
)

echo.
echo ===================================================================
echo   Cai dat thanh cong!
echo   Bay gio senpai hay chay file YuukaOCR.bat de khoi dong Yuuka nhe!
echo ===================================================================
echo.

:: Chuyen den thu muc goc cua script
cd /d "%~dp0"

:: Khoi chay app qua launcher de bat loi ma khong can console.
:: Su dung `start /B` de chay trong nen va `pythonw.exe` de khong hien cua so console.
start "Yuuka OCR" /B pythonw.exe launcher.pyw
if %errorlevel% equ 0 goto :EOF

start "Yuuka OCR" /B pyw.exe launcher.pyw
if %errorlevel% equ 0 goto :EOF

:: Neu ca hai deu that bai, hien thi thong bao loi
echo [LOI] Khong tim thay 'pythonw.exe' hoac 'pyw.exe'.
echo Senpai hay chay file INSTALL.bat truoc nhe.
pause
exit /b

:EOF