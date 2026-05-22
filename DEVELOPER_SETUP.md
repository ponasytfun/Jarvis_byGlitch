# Developer Setup

This project is meant to be handed to another developer without local machine baggage.

## Recommended Environment

- Windows 10 or 11
- Python 3.12 preferred
- Python 3.11 also acceptable
- LM Studio or Ollama if AI chat is needed

## First-Time Setup

Run:

```bat
setup.bat
```

Or:

```powershell
.\setup.ps1
```

That will:
- create `.venv`
- install base dependencies
- install optional voice dependencies when the Python version is compatible
- probe local AI providers
- run the startup smoke test

## Run The App

```bat
run_dev.bat
```

Or:

```bat
.venv\Scripts\python.exe main.py
```

## Optional Voice Setup

```bat
scripts\install_voice_stack.bat
```

## Useful Smoke Tests

```bat
.venv\Scripts\python.exe scripts\test_app_startup.py
.venv\Scripts\python.exe scripts\test_ai_connection.py --probe-only
.venv\Scripts\python.exe scripts\test_microphone.py
.venv\Scripts\python.exe scripts\test_stt.py
.venv\Scripts\python.exe scripts\test_tts.py
.venv\Scripts\python.exe scripts\collect_diagnostics.py
```

## Local Runtime Data

Jarvis stores user/runtime data outside the repo in:

- `%APPDATA%\JarvisAssistant\config.yaml`
- `%APPDATA%\JarvisAssistant\logs\`
- `%APPDATA%\JarvisAssistant\chat_history.json`
- `%APPDATA%\JarvisAssistant\audio_debug\`

## Before Re-Sharing The Project

To clean local build artifacts and caches out of the repo folder:

```powershell
.\scripts\prepare_developer_copy.ps1
```
