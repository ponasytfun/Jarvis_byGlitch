from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from jarvis_assistant.ai_manager import LocalAIManager  # noqa: E402
from jarvis_assistant.actions import ActionExecutor  # noqa: E402
from jarvis_assistant.assistant_actions import AssistantActionOutcome, AssistantActionRegistry  # noqa: E402
from jarvis_assistant.assistant_engine import AssistantEngine  # noqa: E402
from jarvis_assistant.brave_music import BraveMusicController  # noqa: E402
from jarvis_assistant.config_manager import ConfigManager  # noqa: E402
from jarvis_assistant.paths import build_app_paths  # noqa: E402
from jarvis_assistant.voice_agent import LocalVoiceAgent  # noqa: E402
from jarvis_assistant.window_manager import WindowManager  # noqa: E402
from jarvis_assistant.workflow_engine import WorkflowEngine  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test the local Jarvis voice stack.")
    parser.add_argument("--test-tts", action="store_true", help="Speak the configured test phrase.")
    parser.add_argument("--test-mic", action="store_true", help="Record a short microphone sample.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger("JarvisAssistant.TestVoice")

    config = ConfigManager(build_app_paths()).load_or_create()
    ai_manager = LocalAIManager(logger)
    ai_status = ai_manager.probe(config.ai)
    window_manager = WindowManager(logger)
    brave_music = BraveMusicController(window_manager, logger)
    action_executor = ActionExecutor(window_manager, brave_music, logger)
    workflow_engine = WorkflowEngine(action_executor, logger)

    def obs_clip_stub(_config, dry_run: bool) -> AssistantActionOutcome:
        if dry_run:
            return AssistantActionOutcome(
                "obs_clip",
                True,
                "Dry run: I would ask OBS to save a replay clip.",
                "OBS clip execution was skipped in dry-run mode.",
            )
        raise RuntimeError("OBS replay clipping is not configured in this smoke test.")

    registry = AssistantActionRegistry(
        action_executor,
        workflow_engine,
        logger,
        ai_status_provider=lambda: ai_status,
        voice_status_provider=lambda: "Voice layer ready.",
        mic_status_provider=lambda: "Microphone ready.",
        tts_status_provider=lambda: "TTS ready.",
        theme_provider=lambda: (config.ui.theme, config.ui.atom_theme),
        obs_clip_handler=obs_clip_stub,
    )
    assistant_engine = AssistantEngine(ai_manager, registry, logger)
    agent = LocalVoiceAgent(ai_manager, assistant_engine, logger)

    print("Voice summary:")
    print(f"  {agent.describe_voice_status(config)}")
    print(f"  STT: {agent.describe_stt_status(config.voice)}")
    print(f"  TTS: {agent.describe_tts_status(config.voice)}")

    if args.test_mic:
        result = agent.test_microphone(config)
        print("")
        print("Microphone probe:")
        print(f"  Device: {result.device_label}")
        print(f"  Peak: {result.peak:.3f}")
        print(f"  RMS: {result.rms:.3f}")

    if args.test_tts:
        backend = agent.test_tts(config)
        print("")
        print(f"TTS spoke through: {backend}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
