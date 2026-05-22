@echo off
setlocal

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py
) else (
    py -3.12 -c "import sys" >nul 2>nul && py -3.12 main.py || py -3 main.py
)

endlocal
