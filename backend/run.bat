@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    python -m pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

set PORT=8080
echo Starting SkillProof API at http://127.0.0.1:%PORT%
echo (If port 8000 fails on your PC, we use 8080 by default.)
.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port %PORT%
pause
