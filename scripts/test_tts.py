from __future__ import annotations

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
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger("JarvisAssistant.TestTTS")
    config = ConfigManager(build_app_paths()).load_or_create()

    ai_manager = LocalAIManager(logger)
    ai_status = ai_manager.probe(config.ai)
    window_manager = WindowManager(logger)
    brave_music = BraveMusicController(window_manager, logger)
    action_executor = ActionExecutor(window_manager, brave_music, logger)
    workflow_engine = WorkflowEngine(action_executor, logger)

    def obs_clip_stub(_config, dry_run: bool) -> AssistantActionOutcome:
        if dry_run:
            return AssistantActionOutcome("obs_clip", True, "Dry run.", "Dry run.")
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
    engine = AssistantEngine(ai_manager, registry, logger)
    voice_agent = LocalVoiceAgent(ai_manager, engine, logger)
    backend = voice_agent.test_tts(config)
    print(f"TTS test succeeded through: {backend}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
