@echo off
setlocal

:: Chuyen den thu muc goc cua script de dam bao cac duong dan tuong doi (vd: config/, user/) luon dung
cd /d "%~dp0"

echo Yuuka: Dang khoi dong...
echo (Cac log chi tiet se hien thi trong tab Console cua ung dung)
echo.

:: Tim trinh thong dich Python va khoi dong app
:: YUUKA: Su dung python.exe/py.exe thay vi pythonw.exe/pyw.exe de hien thi loi startup (neu co).
:: Cua so console nay se duoc dung de hien thi log, sau do log se duoc chuyen vao UI.
python main.py
if %errorlevel% equ 0 goto :EOF

py main.py
if %errorlevel% equ 0 goto :EOF

:: Neu ca hai lenh tren deu that bai
echo [LOI] Khong tim thay 'python' hoac 'py'.
echo Senpai da cai dat Python va them vao PATH chua?
echo Vui long chay file INSTALL.bat truoc.
pause
exit /b

:EOF