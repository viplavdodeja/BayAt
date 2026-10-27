@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" goto systempython
".venv\Scripts\python.exe" -m app.main
goto finished
:systempython
where py >nul 2>nul
if errorlevel 1 goto usepython
py -3 -m app.main
goto finished
:usepython
python -m app.main
:finished
if errorlevel 1 pause
