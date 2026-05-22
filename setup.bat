@echo off
setlocal

set "ROOT=%~dp0"
cd /d "%ROOT%"

set "PYTHON_CMD="
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_CMD=.venv\Scripts\python.exe"
) else (
    py -3.12 -c "import sys" >nul 2>nul && set "PYTHON_CMD=py -3.12"
    if not defined PYTHON_CMD py -3.11 -c "import sys" >nul 2>nul && set "PYTHON_CMD=py -3.11"
    if not defined PYTHON_CMD set "PYTHON_CMD=py -3"
)

echo Using %PYTHON_CMD%
call %PYTHON_CMD% -c "import sys; print('Python:', sys.version)"
if errorlevel 1 goto :fail

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo Creating virtual environment...
    call %PYTHON_CMD% -m venv .venv
    if errorlevel 1 goto :fail
    set "PYTHON_CMD=.venv\Scripts\python.exe"
)

echo.
echo Installing core JarvisAssistant dependencies...
call %PYTHON_CMD% -m pip install --upgrade pip
if errorlevel 1 goto :fail
call %PYTHON_CMD% -m pip install -r requirements.txt -r requirements-dev.txt
if errorlevel 1 goto :fail

echo.
echo Checking optional voice runtime compatibility...
for /f %%V in ('%PYTHON_CMD% -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do set "PYVER=%%V"
if "%PYVER%"=="3.11" goto :install_voice
if "%PYVER%"=="3.12" goto :install_voice

echo Python %PYVER% detected.
echo Optional faster-whisper and openWakeWord packages are most reliable on Python 3.11 or 3.12.
echo Skipping full optional voice package install on this interpreter.
echo Jarvis will still use local text chat, Ollama or LM Studio, and Windows Speech API fallback for TTS.
goto :probe

:install_voice
echo Installing optional local voice dependencies...
call %PYTHON_CMD% -m pip install -r requirements-voice.txt
if errorlevel 1 (
    echo Voice dependency install failed. Jarvis will continue with partial voice support.
) else (
    call %PYTHON_CMD% scripts\download_voice_assets.py --kokoro
)

:probe
echo.
echo Probing local AI providers...
call %PYTHON_CMD% scripts\test_ai_connection.py --probe-only

echo.
echo Running startup smoke test...
call %PYTHON_CMD% scripts\test_app_startup.py
if errorlevel 1 goto :fail

echo.
echo Setup complete.
echo If LM Studio is running, load a model and enable its local server.
echo If Ollama is running, Jarvis can use it automatically as a fallback.
echo For full speech recognition, use a Python 3.11 or 3.12 environment and rerun scripts\install_voice_stack.bat.
goto :eof

:fail
echo.
echo Setup failed.
exit /b 1
