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
from jarvis_assistant.brave_music import BraveMusicController  # noqa: E402
from jarvis_assistant.config_manager import ConfigManager  # noqa: E402
from jarvis_assistant.paths import build_app_paths  # noqa: E402
from jarvis_assistant.window_manager import WindowManager  # noqa: E402
from jarvis_assistant.workflow_engine import WorkflowEngine  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test the Jarvis assistant action registry.")
    parser.add_argument("--list", action="store_true", help="List the registered safe assistant actions.")
    parser.add_argument("--dry-run-open-app", default="", help="Dry-run an open_app action for the given target.")
    parser.add_argument("--dry-run-theme", default="", help="Dry-run a switch_theme action for the given theme.")
    parser.add_argument("--status", action="store_true", help="Run the assistant_status action.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger("JarvisAssistant.TestActions")

    config = ConfigManager(build_app_paths()).load_or_create()
    window_manager = WindowManager(logger)
    brave_music = BraveMusicController(window_manager, logger)
    action_executor = ActionExecutor(window_manager, brave_music, logger)
    workflow_engine = WorkflowEngine(action_executor, logger)
    ai_manager = LocalAIManager(logger)
    ai_status = ai_manager.probe(config.ai)

    current_surface_theme = config.ui.theme
    current_atom_theme = config.ui.atom_theme

    def theme_provider() -> tuple[str, str]:
        return current_surface_theme, current_atom_theme

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
        theme_provider=theme_provider,
        obs_clip_handler=obs_clip_stub,
    )

    if args.list:
        print("Registered actions:")
        for action in registry.list_actions():
            required = ", ".join(action.required_parameters) if action.required_parameters else "none"
            print(
                f"- {action.action_id}: {action.name} "
                f"(permission={action.permission_level}, required={required})"
            )

    if args.dry_run_open_app:
        outcome = registry.execute(
            "open_app",
            config,
            {"app": args.dry_run_open_app},
            dry_run=True,
        )
        print("")
        print("open_app dry run:")
        print(outcome.response_text)
        print(outcome.detail_text)

    if args.dry_run_theme:
        outcome = registry.execute(
            "switch_theme",
            config,
            {"theme": args.dry_run_theme},
            dry_run=True,
        )
        print("")
        print("switch_theme dry run:")
        print(outcome.response_text)
        print(outcome.detail_text)
        print(f"Payload: {outcome.payload}")

    if args.status:
        outcome = registry.execute("assistant_status", config, {}, dry_run=True)
        print("")
        print("assistant_status:")
        print(outcome.response_text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
