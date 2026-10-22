@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    set "PY=py -3"
) else (
    set "PY=python"
)
%PY% -m pip install --upgrade pyinstaller
if errorlevel 1 goto failed
%PY% -m PyInstaller --noconfirm --clean --onefile --windowed --name LuauDesk app.py
if errorlevel 1 goto failed
echo.
echo Build complete: dist\LuauDesk.exe
echo Build this EXE on Windows for a Windows application.
pause
exit /b 0
:failed
echo.
echo Build failed. Check the error above and confirm Python and pip are installed.
pause
exit /b 1
