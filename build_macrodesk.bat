@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    set "PY=py -3"
) else (
    set "PY=python"
)
%PY% -m pip install --upgrade -r requirements.txt
if errorlevel 1 goto failed
%PY% -m py_compile macrodesk.py
if errorlevel 1 goto failed
%PY% -m PyInstaller --noconfirm --clean --onefile --windowed --name MacroDesk --collect-all keyboard --collect-all pyautogui --collect-all pyperclip macrodesk.py
if errorlevel 1 goto failed
echo.
echo Build complete: dist\MacroDesk.exe
pause
exit /b 0
:failed
echo.
echo Build failed. Check the error above and confirm Python and pip are installed.
pause
exit /b 1
