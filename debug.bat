@echo off
setlocal

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