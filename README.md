# JarvisAssistant

JarvisAssistant is a local Windows desktop assistant built with Python, PySide6, and QML. It combines a Jarvis-style animated UI, local AI provider support, optional local voice chat, and desktop automation such as triple-clap focus mode and the YouTube Music / VS Code / Discord workflow.

This copy is prepared to be shareable:
- machine-specific build output has been removed
- local logs and caches are excluded
- the project no longer includes local virtual environments
- user runtime data stays in `%APPDATA%\JarvisAssistant\`

## What This Project Includes

- Animated Jarvis UI with a Uranium-235 command core
- Surface themes: `dark`, `light`
- Atom themes: `Nuclear Waste`, `Blood Red`, `Cold Blue`
- Local AI provider support
  - LM Studio preferred
  - Ollama fallback
- Text chat inside the desktop app
- Optional local voice loop
  - microphone input
  - local STT with `faster-whisper`
  - local TTS with `Kokoro`, `Piper`, or Windows Speech API fallback
- Triple-clap workflow automation
- The Clash automation:
  - opens Brave
  - opens YouTube Music for `Should I Stay or Should I Go`
  - minimizes Brave
  - focuses or launches VS Code and Discord
  - arranges windows side by side

## What Is Not Included In The Repo

The following are intentionally not kept in the project folder:

- `.venv/`
- build output in `build/` and `dist/`
- local logs
- `__pycache__/`
- generated screenshots
- `%APPDATA%\JarvisAssistant\config.yaml`
- `%APPDATA%\JarvisAssistant\logs\`
- downloaded voice model assets in `%APPDATA%\JarvisAssistant\models\`

These are local runtime artifacts and should stay out of the shared project copy.

## Project Layout

```text
JarvisAssistant/
  assets/
    app_icon.ico
    qml/
      Main.qml
      components/
  defaults/
    config.yaml
  jarvis_assistant/
    app.py
    ai_manager.py
    assistant_actions.py
    assistant_engine.py
    audio_listener.py
    brave_music.py
    clap_detector.py
    config_manager.py
    logger_setup.py
    models.py
    paths.py
    theme_manager.py
    trigger_engine.py
    ui_bridge.py
    voice_agent.py
    window_manager.py
    workflow_engine.py
    workers.py
  scripts/
    collect_diagnostics.py
    download_voice_assets.py
    install_voice_stack.bat
    prepare_developer_copy.ps1
    test_ai_connection.py
    test_app_startup.py
    test_microphone.py
    test_stt.py
    test_tts.py
    test_voice_stack.py
  main.py
  setup.bat
  setup.ps1
  run_dev.bat
  build_exe.bat
  JarvisAssistant.spec
```

## Requirements

- Windows 10 or 11
- Python 3.12 recommended
  - Python 3.11 also works
  - Python 3.14 is not recommended for the full voice stack
- A local AI provider if you want AI chat
  - LM Studio preferred
  - Ollama supported

## Quick Start

### 1. Install Python

Install Python 3.12 if possible.

### 2. Run Setup

Use either:

```bat
setup.bat
```

or:

```powershell
.\setup.ps1
```

The setup script will:
- create `.venv`
- install core dependencies
- install optional voice dependencies when the Python version is compatible
- probe local AI providers
- run the startup smoke test

### 3. Launch The App

```bat
run_dev.bat
```

or:

```bat
.venv\Scripts\python.exe main.py
```

## Local AI Setup

Jarvis defaults to local-only AI.

### Option A: LM Studio

Preferred endpoints:

- `http://127.0.0.1:1234/v1`
- `http://127.0.0.1:1234/api/v1`

Steps:

1. Open LM Studio
2. Load a local chat model
3. Start the local server
4. Leave it running

### Option B: Ollama

Default endpoint:

- `http://127.0.0.1:11434`

If LM Studio is not reachable and Ollama is running, Jarvis can use Ollama automatically.

## Voice Setup

Voice is optional, but the code supports a local stack.

Recommended stack:

- STT: `faster-whisper`
- TTS: `Kokoro`
- TTS fallback: `Piper`
- Final Windows fallback: Speech API

Install the optional voice stack with:

```bat
scripts\install_voice_stack.bat
```

That helper will:
- install `requirements-voice.txt`
- download Kokoro voice assets into `%APPDATA%\JarvisAssistant\models\kokoro\`

### Wake Word

Wake word support is optional and not required for normal use.

If you want openWakeWord:
- provide a compatible wake-word model file
- set `voice.wake_word_model_path` in config

### Basic Voice Flow

The app supports:
- text chat
- click-to-talk
- microphone test
- STT test
- TTS test

If voice is not working, start here:

```bat
.venv\Scripts\python.exe scripts\test_microphone.py
.venv\Scripts\python.exe scripts\test_stt.py
.venv\Scripts\python.exe scripts\test_tts.py
```

## Config And Runtime Data

The app writes user-editable runtime data to:

- Config: `%APPDATA%\JarvisAssistant\config.yaml`
- Logs: `%APPDATA%\JarvisAssistant\logs\`
- Chat history: `%APPDATA%\JarvisAssistant\chat_history.json`
- Audio debug files: `%APPDATA%\JarvisAssistant\audio_debug\`

Default config template:

- [defaults/config.yaml](./defaults/config.yaml)

If the live config is missing, Jarvis creates one automatically.
If the live config is invalid, Jarvis backs it up and recreates a safe config.

## Important Features Preserved

This project intentionally keeps the existing assistant features:

- Jarvis-themed desktop UI
- local AI support
- voice support
- triple-clap automation
- The Clash workflow
- Discord / VS Code focus and arrangement
- theme system
- settings/config workflow

## Development Notes

### Run Smoke Tests

Startup:

```bat
.venv\Scripts\python.exe scripts\test_app_startup.py
```

AI connection:

```bat
.venv\Scripts\python.exe scripts\test_ai_connection.py --probe-only
```

AI prompt:

```bat
.venv\Scripts\python.exe scripts\test_ai_connection.py --chat "Reply with: Jarvis AI connection working."
```

Microphone:

```bat
.venv\Scripts\python.exe scripts\test_microphone.py
```

STT:

```bat
.venv\Scripts\python.exe scripts\test_stt.py
```

TTS:

```bat
.venv\Scripts\python.exe scripts\test_tts.py
```

Diagnostics dump:

```bat
.venv\Scripts\python.exe scripts\collect_diagnostics.py
```

## Build The EXE

```bat
build_exe.bat
```

Output:

```text
dist\JarvisAssistant\JarvisAssistant.exe
```

## Developer Handoff Notes

If you give this project to someone else, send:

- the source code
- `README.md`
- `defaults/config.yaml`
- the scripts and requirements files

Do not send:

- your local `.venv`
- `dist/`
- `build/`
- `logs/`
- `%APPDATA%\JarvisAssistant\`

Those can contain machine-specific paths, local diagnostics, or generated assets.

You can re-clean the folder before handing it to another developer:

```powershell
.\scripts\prepare_developer_copy.ps1
```

Short setup guide:

- [DEVELOPER_SETUP.md](./DEVELOPER_SETUP.md)

## Main Entry Point

Main entry point:

- [main.py](./main.py)

Primary runtime controller:

- [jarvis_assistant/app.py](./jarvis_assistant/app.py)

Primary UI:

- [assets/qml/Main.qml](./assets/qml/Main.qml)
