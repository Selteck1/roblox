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
%PY% -m py_compile scriptdeck.py
if errorlevel 1 goto failed
%PY% -m PyInstaller --noconfirm --clean --onefile --windowed --name ScriptDeck scriptdeck.py
if errorlevel 1 goto failed
echo.
echo Build complete: dist\ScriptDeck.exe
pause
exit /b 0
:failed
echo.
echo Build failed. Check Python and pip, then retry.
pause
exit /b 1
