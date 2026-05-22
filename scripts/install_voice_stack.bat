@echo off
setlocal

set "ROOT=%~dp0.."
cd /d "%ROOT%"

set "PYTHON_CMD="
py -3.12 -c "import sys" >nul 2>nul && set "PYTHON_CMD=py -3.12"
if not defined PYTHON_CMD (
    py -3.11 -c "import sys" >nul 2>nul && set "PYTHON_CMD=py -3.11"
)
if not defined PYTHON_CMD (
    if exist ".venv\Scripts\python.exe" (
        set "PYTHON_CMD=.venv\Scripts\python.exe"
    )
)
if not defined PYTHON_CMD (
    set "PYTHON_CMD=py -3"
)

echo Using %PYTHON_CMD%
call %PYTHON_CMD% -c "import sys; print('Voice setup Python:', sys.version)"
if errorlevel 1 goto :fail

for /f %%V in ('%PYTHON_CMD% -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do set "PYVER=%%V"
if not "%PYVER%"=="3.11" if not "%PYVER%"=="3.12" (
    echo.
    echo Python %PYVER% detected.
    echo The preferred local speech packages are most reliable on Python 3.11 or 3.12.
    echo This script will still download Kokoro assets, but faster-whisper or openWakeWord may fail to install here.
)

echo.
echo Installing base and optional local voice dependencies...
call %PYTHON_CMD% -m pip install -r requirements.txt -r requirements-voice.txt
if errorlevel 1 (
    echo.
    echo Optional voice dependency install failed on this interpreter.
    echo Jarvis can still use local text chat, local AI providers, and Windows Speech API fallback TTS.
    echo For full local STT, use Python 3.11 or 3.12 and run this script again.
)

echo.
echo Downloading Kokoro voice model assets...
call %PYTHON_CMD% scripts\download_voice_assets.py --kokoro
if errorlevel 1 goto :fail

echo.
echo Voice stack setup finished.
echo Next manual steps:
echo 1. Install LM Studio and start its local server on http://127.0.0.1:1234
echo 2. Load a local chat model in LM Studio
echo 3. If you want true openWakeWord detection, place a Jarvis wake-word model file and set voice.wake_word_model_path
echo 4. Enable the voice layer in JarvisAssistant settings
goto :eof

:fail
echo.
echo Voice stack setup failed.
exit /b 1
