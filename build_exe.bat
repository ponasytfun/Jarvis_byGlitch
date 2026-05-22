@echo off
setlocal

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt -r requirements-dev.txt
    if errorlevel 1 exit /b %errorlevel%
    ".venv\Scripts\python.exe" -m PyInstaller --clean --noconfirm JarvisAssistant.spec
) else (
    py -3.12 -c "import sys" >nul 2>nul && (
        py -3.12 -m pip install -r requirements.txt -r requirements-dev.txt
        if errorlevel 1 exit /b %errorlevel%
        py -3.12 -m PyInstaller --clean --noconfirm JarvisAssistant.spec
        goto :done
    )
    py -3 -m pip install -r requirements.txt -r requirements-dev.txt
    if errorlevel 1 exit /b %errorlevel%
    py -3 -m PyInstaller --clean --noconfirm JarvisAssistant.spec
)

if errorlevel 1 exit /b %errorlevel%

:done
echo.
echo Build complete.
echo Launch with dist\JarvisAssistant\JarvisAssistant.exe
endlocal
