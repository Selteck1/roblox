@echo off
setlocal
cd /d "%~dp0"
python -m pip install --upgrade pyinstaller
if errorlevel 1 goto :fail
python -m PyInstaller --noconfirm --clean --onefile --windowed --name LuauDesk app.py
if errorlevel 1 goto :fail
echo.
echo Build complete: dist\LuauDesk.exe
pause
exit /b 0
:fail
echo.
echo Build failed. Check the error messages above.
pause
exit /b 1
