@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 app.py
    if not errorlevel 1 exit /b 0
)
where python >nul 2>nul
if %errorlevel%==0 (
    python app.py
    exit /b %errorlevel%
)
echo Python 3 was not found. Install it from https://www.python.org/downloads/windows/
echo During setup, enable "Add Python to PATH".
pause
