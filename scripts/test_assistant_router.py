from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from jarvis_assistant.actions import ActionExecutor  # noqa: E402
from jarvis_assistant.ai_manager import LocalAIManager  # noqa: E402
from jarvis_assistant.assistant_actions import AssistantActionOutcome, AssistantActionRegistry  # noqa: E402
from jarvis_assistant.assistant_engine import AssistantEngine  # noqa: E402
from jarvis_assistant.brave_music import BraveMusicController  # noqa: E402
from jarvis_assistant.config_manager import ConfigManager  # noqa: E402
from jarvis_assistant.models import JarvisConfig  # noqa: E402
from jarvis_assistant.paths import build_app_paths  # noqa: E402
from jarvis_assistant.window_manager import WindowManager  # noqa: E402
from jarvis_assistant.workflow_engine import WorkflowEngine  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test the Jarvis assistant router.")
    parser.add_argument(
        "--prompt",
        action="append",
        default=[],
        help="Prompt to run through the assistant router. May be provided multiple times.",
    )
    args = parser.parse_args()

    prompts = args.prompt or [
        "Open Discord",
        "Switch to Nuclear Waste theme",
        "What model are you using?",
        "Play Should I Stay or Should I Go",
    ]

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger("JarvisAssistant.TestRouter")

    config = ConfigManager(build_app_paths()).load_or_create()
    config.runtime.dry_run = True

    ai_manager = LocalAIManager(logger)
    ai_status = ai_manager.probe(config.ai)
    window_manager = WindowManager(logger)
    brave_music = BraveMusicController(window_manager, logger)
    action_executor = ActionExecutor(window_manager, brave_music, logger)
    workflow_engine = WorkflowEngine(action_executor, logger)

    current_surface_theme = config.ui.theme
    current_atom_theme = config.ui.atom_theme

    def theme_provider() -> tuple[str, str]:
        return current_surface_theme, current_atom_theme

    def obs_clip_stub(_config: JarvisConfig, dry_run: bool) -> AssistantActionOutcome:
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
        theme_provider=theme_provider,
        obs_clip_handler=obs_clip_stub,
    )
    engine = AssistantEngine(ai_manager, registry, logger)

    for prompt in prompts:
        print("")
        print(f"Prompt: {prompt}")
        result = engine.handle_prompt(config, prompt)
        print(f"Mode: {result.mode}")
        print(f"Success: {result.success}")
        if result.action_id:
            print(f"Action: {result.action_id}")
        print(f"Response: {result.response_text}")
        if result.detail_text:
            print(f"Detail: {result.detail_text}")
        if result.payload:
            print(f"Payload: {result.payload}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
