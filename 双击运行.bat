@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist "dist\个人账本\个人账本.exe" (
    start "" "dist\个人账本\个人账本.exe"
    exit /b 0
)
if exist ".venv312\Scripts\python.exe" (
    ".venv312\Scripts\python.exe" main.py
) else (
    python main.py
)
if errorlevel 1 (
    echo.
    echo Run failed. Please make sure Python and dependencies are installed:
    echo     pip install -r requirements.txt
    pause
)