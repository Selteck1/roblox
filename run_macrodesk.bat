@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 -m pip install -r requirements.txt
    if errorlevel 1 goto failed
    py -3 macrodesk.py
    exit /b %errorlevel%
)
where python >nul 2>nul
if %errorlevel%==0 (
    python -m pip install -r requirements.txt
    if errorlevel 1 goto failed
    python macrodesk.py
    exit /b %errorlevel%
)
echo Python 3 was not found. Install it from https://www.python.org/downloads/windows/
echo During setup, enable "Add Python to PATH".
pause
exit /b 1
:failed
echo.
echo Setup or launch failed. Check the error above.
pause
exit /b 1
