from __future__ import annotations

import json
import os
import platform
import shutil
import sys
from importlib import metadata
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from jarvis_assistant.ai_manager import LocalAIManager  # noqa: E402
from jarvis_assistant.actions import ActionExecutor  # noqa: E402
from jarvis_assistant.assistant_actions import AssistantActionOutcome, AssistantActionRegistry  # noqa: E402
from jarvis_assistant.assistant_engine import AssistantEngine  # noqa: E402
from jarvis_assistant.audio_listener import AudioListener  # noqa: E402
from jarvis_assistant.brave_music import BraveMusicController  # noqa: E402
from jarvis_assistant.config_manager import ConfigManager  # noqa: E402
from jarvis_assistant.paths import build_app_paths  # noqa: E402
from jarvis_assistant.voice_agent import LocalVoiceAgent  # noqa: E402
from jarvis_assistant.window_manager import WindowManager  # noqa: E402
from jarvis_assistant.workflow_engine import WorkflowEngine  # noqa: E402


def _safe_version(name: str) -> str:
    try:
        return metadata.version(name)
    except Exception:
        return "not installed"


def main() -> int:
    paths = build_app_paths()
    config = ConfigManager(paths).load_or_create()

    logger = __import__("logging").getLogger("JarvisAssistant.Diagnostics")
    logger.setLevel("INFO")

    ai_manager = LocalAIManager(logger)
    ai_status = ai_manager.probe(config.ai)
    window_manager = WindowManager(logger)
    brave_music = BraveMusicController(window_manager, logger)
    action_executor = ActionExecutor(window_manager, brave_music, logger)
    workflow_engine = WorkflowEngine(action_executor, logger)

    def obs_clip_stub(_config, dry_run: bool) -> AssistantActionOutcome:
        if dry_run:
            return AssistantActionOutcome("obs_clip", True, "Dry run.", "Dry run.")
        raise RuntimeError("OBS replay clipping is not configured in this diagnostics script.")

    registry = AssistantActionRegistry(
        action_executor,
        workflow_engine,
        logger,
        ai_status_provider=lambda: ai_status,
        voice_status_provider=lambda: "Voice layer ready.",
        mic_status_provider=lambda: "Microphone idle.",
        tts_status_provider=lambda: "TTS status not checked yet.",
        theme_provider=lambda: (config.ui.theme, config.ui.atom_theme),
        obs_clip_handler=obs_clip_stub,
    )
    engine = AssistantEngine(ai_manager, registry, logger)
    voice_agent = LocalVoiceAgent(ai_manager, engine, logger)

    input_devices = AudioListener.list_input_devices()
    output_devices = AudioListener.list_output_devices()

    payload = {
        "os": platform.platform(),
        "python": sys.version.splitlines()[0],
        "project_root": str(paths.project_root),
        "appdata_dir": str(paths.appdata_dir),
        "config_path": str(paths.config_path),
        "logs_dir": str(paths.logs_dir),
        "ai": {
            "provider": ai_status.provider_display_name,
            "base_url": ai_status.base_url,
            "connected": ai_status.connected,
            "selected_model": ai_status.model_name,
            "available_models": ai_status.available_models,
            "status_text": ai_status.status_text,
            "error_text": ai_status.error_text,
            "stream_enabled": config.ai.stream_enabled,
        },
        "voice": {
            "enabled": config.voice.enabled,
            "selected_input_device": config.audio.device_index,
            "selected_output_device": config.voice.output_device_name or "(default)",
            "stt_status": voice_agent.describe_stt_status(config.voice),
            "tts_status": voice_agent.describe_tts_status(config.voice),
            "listen_timeout_seconds": config.voice.listen_timeout_seconds,
            "silence_timeout_seconds": config.voice.silence_timeout_seconds,
            "min_record_seconds": config.voice.min_record_seconds,
            "max_record_seconds": config.voice.max_record_seconds,
        },
        "ui": {
            "theme": config.ui.theme,
            "atom_theme": config.ui.atom_theme,
            "chat_history_enabled": config.ui.chat_history_enabled,
            "show_debug_panel": config.ui.show_debug_panel,
        },
        "debug": {
            "log_level": config.debug.log_level,
            "save_audio_debug_files": config.debug.save_audio_debug_files,
            "save_transcripts": config.debug.save_transcripts,
        },
        "hardware": {
            "gpu_cuda_detected": bool(shutil.which("nvidia-smi") or os.getenv("CUDA_PATH")),
        },
        "devices": {
            "inputs": input_devices,
            "outputs": output_devices,
        },
        "dependency_versions": {
            "PySide6": _safe_version("PySide6"),
            "sounddevice": _safe_version("sounddevice"),
            "numpy": _safe_version("numpy"),
            "faster-whisper": _safe_version("faster-whisper"),
            "kokoro-onnx": _safe_version("kokoro-onnx"),
            "pywin32": _safe_version("pywin32"),
            "requests": _safe_version("requests"),
        },
    }

    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
