from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from jarvis_assistant.actions import ActionExecutor
from jarvis_assistant.models import AIBackendStatus, JarvisConfig
from jarvis_assistant.theme_manager import atom_theme_display_name, normalize_atom_theme, normalize_theme
from jarvis_assistant.workflow_engine import WorkflowEngine


@dataclass
class RegisteredAction:
    action_id: str
    name: str
    description: str
    required_parameters: list[str]
    permission_level: str
    handler: Callable[[JarvisConfig, dict[str, Any], bool], "AssistantActionOutcome"]
    success_response: str
    failure_response: str


@dataclass(frozen=True)
class AssistantActionOutcome:
    action_id: str
    success: bool
    response_text: str
    detail_text: str = ""
    payload: dict[str, Any] = field(default_factory=dict)


class AssistantActionRegistry:
    """Safe desktop actions that Jarvis can perform without arbitrary code execution."""

    def __init__(
        self,
        action_executor: ActionExecutor,
        workflow_engine: WorkflowEngine,
        logger,
        *,
        ai_status_provider: Callable[[], AIBackendStatus],
        voice_status_provider: Callable[[], str],
        mic_status_provider: Callable[[], str],
        tts_status_provider: Callable[[], str],
        theme_provider: Callable[[], tuple[str, str]],
        obs_clip_handler: Callable[[JarvisConfig, bool], AssistantActionOutcome],
    ) -> None:
        self.action_executor = action_executor
        self.workflow_engine = workflow_engine
        self.logger = logger.getChild("assistant_actions")
        self._ai_status_provider = ai_status_provider
        self._voice_status_provider = voice_status_provider
        self._mic_status_provider = mic_status_provider
        self._tts_status_provider = tts_status_provider
        self._theme_provider = theme_provider
        self._obs_clip_handler = obs_clip_handler

        self._actions: dict[str, RegisteredAction] = {
            "open_app": RegisteredAction(
                action_id="open_app",
                name="Open App",
                description="Open or focus a supported desktop application such as Discord, VS Code, Brave, or OBS.",
                required_parameters=["app"],
                permission_level="safe",
                handler=self._handle_open_app,
                success_response="Opened the requested app.",
                failure_response="I couldn't open that application.",
            ),
            "play_music": RegisteredAction(
                action_id="play_music",
                name="Play Music",
                description="Run the configured The Clash YouTube Music automation and attempt playback safely in Brave.",
                required_parameters=[],
                permission_level="safe",
                handler=self._handle_play_music,
                success_response="Opened the music automation.",
                failure_response="I couldn't start the music automation.",
            ),
            "focus_mode": RegisteredAction(
                action_id="focus_mode",
                name="Focus Mode",
                description="Open or focus VS Code and Discord, then arrange them side by side.",
                required_parameters=[],
                permission_level="safe",
                handler=self._handle_focus_mode,
                success_response="Focus mode is ready.",
                failure_response="I couldn't finish focus mode cleanly.",
            ),
            "obs_clip": RegisteredAction(
                action_id="obs_clip",
                name="OBS Clip",
                description="Ask OBS to save a replay buffer clip when OBS replay integration is configured.",
                required_parameters=[],
                permission_level="safe",
                handler=self._handle_obs_clip,
                success_response="Saved the OBS clip.",
                failure_response="I couldn't save an OBS clip.",
            ),
            "switch_theme": RegisteredAction(
                action_id="switch_theme",
                name="Switch Theme",
                description="Switch the Jarvis visual theme to Nuclear Waste, Blood Red, Cold Blue, Dark, or Light.",
                required_parameters=["theme"],
                permission_level="safe",
                handler=self._handle_switch_theme,
                success_response="Theme switched.",
                failure_response="I couldn't switch the theme.",
            ),
            "assistant_status": RegisteredAction(
                action_id="assistant_status",
                name="Assistant Status",
                description="Report the current AI provider, model, voice status, microphone state, TTS state, and selected theme.",
                required_parameters=[],
                permission_level="safe",
                handler=self._handle_assistant_status,
                success_response="Reported Jarvis status.",
                failure_response="I couldn't collect the assistant status.",
            ),
            "stop_listening": RegisteredAction(
                action_id="stop_listening",
                name="Stop Listening",
                description="Stop the live listening mode safely.",
                required_parameters=[],
                permission_level="safe",
                handler=self._handle_stop_listening,
                success_response="Stopped listening.",
                failure_response="I couldn't stop listening.",
            ),
        }

    def list_actions(self) -> list[RegisteredAction]:
        return [self._actions[key] for key in sorted(self._actions.keys())]

    def describe_for_router(self) -> str:
        lines = []
        for action in self.list_actions():
            required = ", ".join(action.required_parameters) if action.required_parameters else "none"
            lines.append(
                f"- {action.action_id}: {action.description} "
                f"(required params: {required}; permission: {action.permission_level})"
            )
        return "\n".join(lines)

    def execute(
        self,
        action_id: str,
        config: JarvisConfig,
        args: dict[str, Any] | None = None,
        *,
        dry_run: bool | None = None,
    ) -> AssistantActionOutcome:
        action = self._actions.get(action_id)
        if action is None:
            raise KeyError(f"Unknown assistant action: {action_id}")

        payload = dict(args or {})
        missing = [
            parameter
            for parameter in action.required_parameters
            if parameter not in payload or str(payload.get(parameter, "")).strip() == ""
        ]
        if missing:
            raise ValueError(
                f"Action '{action_id}' requires parameter(s): {', '.join(missing)}."
            )

        effective_dry_run = config.runtime.dry_run if dry_run is None else dry_run
        self.logger.info("Assistant action start: %s %s", action_id, payload)
        outcome = action.handler(config, payload, effective_dry_run)
        self.logger.info("Assistant action finish: %s success=%s", action_id, outcome.success)
        return outcome

    def _handle_open_app(
        self,
        config: JarvisConfig,
        args: dict[str, Any],
        dry_run: bool,
    ) -> AssistantActionOutcome:
        raw_app = str(args.get("app", "")).strip()
        target_name, display_name = self._resolve_app_target(raw_app)
        target_timeout = self._target_timeout_ms(config, target_name)
        self.action_executor.execute(
            "focus_or_launch_app",
            {"target": target_name, "wait_timeout_seconds": max(6, target_timeout // 1000)},
            config,
            dry_run,
            timeout_ms=target_timeout,
        )
        response = (
            f"Dry run: I would open or focus {display_name}."
            if dry_run
            else f"{display_name} is ready."
        )
        detail = f"Target '{display_name}' routed to {target_name}."
        return AssistantActionOutcome("open_app", True, response, detail, {"app": target_name})

    def _handle_play_music(
        self,
        config: JarvisConfig,
        args: dict[str, Any],
        dry_run: bool,
    ) -> AssistantActionOutcome:
        requested_song = str(args.get("song", "")).strip().casefold()
        if requested_song and "should i stay or should i go" not in requested_song and "the clash" not in requested_song:
            raise RuntimeError(
                "I currently only have the configured The Clash automation for "
                "'Should I Stay or Should I Go'."
            )

        result = self.action_executor.execute(
            "open_music_in_brave",
            {},
            config,
            dry_run,
        )
        if dry_run:
            response = "Dry run: I would open the configured The Clash track in Brave."
        elif result.playback_likely_started:
            response = "The Clash track is opening and playback likely started."
        else:
            response = "The music page opened, but playback could not be confirmed."

        return AssistantActionOutcome(
            "play_music",
            bool(result.playback_likely_started or dry_run),
            response,
            result.details,
            {"url": result.url_opened},
        )

    def _handle_focus_mode(
        self,
        config: JarvisConfig,
        args: dict[str, Any],
        dry_run: bool,
    ) -> AssistantActionOutcome:
        self.action_executor.execute(
            "focus_or_launch_app",
            {"target": "vscode", "wait_timeout_seconds": max(6, config.matching.vscode.launch_timeout_ms // 1000)},
            config,
            dry_run,
            timeout_ms=config.matching.vscode.launch_timeout_ms,
        )
        self.action_executor.execute(
            "focus_or_launch_app",
            {"target": "discord", "wait_timeout_seconds": max(6, config.matching.discord.launch_timeout_ms // 1000)},
            config,
            dry_run,
            timeout_ms=config.matching.discord.launch_timeout_ms,
        )
        self.action_executor.execute(
            "arrange_two_windows_side_by_side",
            {"left_target": "vscode", "right_target": "discord"},
            config,
            dry_run,
        )
        response = (
            "Dry run: I would open VS Code, open Discord, and arrange them side by side."
            if dry_run
            else "Focus mode is ready with VS Code and Discord side by side."
        )
        return AssistantActionOutcome(
            "focus_mode",
            True,
            response,
            "Focused VS Code and Discord, then arranged the workspace.",
        )

    def _handle_obs_clip(
        self,
        config: JarvisConfig,
        args: dict[str, Any],
        dry_run: bool,
    ) -> AssistantActionOutcome:
        return self._obs_clip_handler(config, dry_run)

    def _handle_switch_theme(
        self,
        config: JarvisConfig,
        args: dict[str, Any],
        dry_run: bool,
    ) -> AssistantActionOutcome:
        requested_theme = str(args.get("theme", "")).strip()
        if not requested_theme:
            raise ValueError("No theme name was provided.")

        lowered = requested_theme.casefold()
        if lowered in {"dark", "light"}:
            response = (
                f"Dry run: I would switch the surface theme to {lowered.title()}."
                if dry_run
                else f"Surface theme switched to {lowered.title()}."
            )
            return AssistantActionOutcome(
                "switch_theme",
                True,
                response,
                f"Prepared surface theme '{lowered}'.",
                {"surface_theme": normalize_theme(lowered)},
            )

        normalized_theme = lowered.replace(" ", "_").replace("-", "_")
        if normalized_theme not in {"nuclear_waste", "blood_red", "cold_blue"}:
            raise ValueError(
                "Unsupported theme. Try Nuclear Waste, Blood Red, Cold Blue, Dark, or Light."
            )
        atom_theme = normalize_atom_theme(normalized_theme)
        display_name = atom_theme_display_name(atom_theme)
        response = (
            f"Dry run: I would switch the atom theme to {display_name}."
            if dry_run
            else f"Atom theme switched to {display_name}."
        )
        return AssistantActionOutcome(
            "switch_theme",
            True,
            response,
            f"Prepared atom theme '{display_name}'.",
            {"atom_theme": atom_theme},
        )

    def _handle_assistant_status(
        self,
        config: JarvisConfig,
        args: dict[str, Any],
        dry_run: bool,
    ) -> AssistantActionOutcome:
        ai_status = self._ai_status_provider()
        surface_theme, atom_theme = self._theme_provider()
        theme_display = atom_theme_display_name(atom_theme)
        response = (
            f"Jarvis is using {ai_status.provider_display_name or 'no provider'}"
            f"{f' with {ai_status.model_name}' if ai_status.model_name else ''}. "
            f"Voice is {'enabled' if config.voice.enabled else 'disabled'}. "
            f"TTS status: {self._tts_status_provider()} "
            f"Microphone status: {self._mic_status_provider()} "
            f"Current themes: {surface_theme.title()} surface and {theme_display} atom."
        )
        return AssistantActionOutcome(
            "assistant_status",
            True,
            response,
            self._voice_status_provider(),
        )

    def _handle_stop_listening(
        self,
        config: JarvisConfig,
        args: dict[str, Any],
        dry_run: bool,
    ) -> AssistantActionOutcome:
        if dry_run:
            return AssistantActionOutcome(
                "stop_listening",
                True,
                "Dry run: I would stop listening.",
                "Listening shutdown was skipped in dry-run mode.",
            )
        return AssistantActionOutcome(
            "stop_listening",
            True,
            "Stopping the listening field.",
            "Prepared a listening shutdown request.",
            {"request_stop_listening": True},
        )

    def _resolve_app_target(self, raw_app: str) -> tuple[str, str]:
        normalized = raw_app.casefold().strip()
        aliases = {
            "discord": ("discord", "Discord"),
            "vs code": ("vscode", "VS Code"),
            "vscode": ("vscode", "VS Code"),
            "visual studio code": ("vscode", "VS Code"),
            "code": ("vscode", "VS Code"),
            "browser": ("brave", "Brave"),
            "brave": ("brave", "Brave"),
            "youtube music": ("brave", "Brave"),
            "obs": ("obs", "OBS"),
            "obs studio": ("obs", "OBS"),
        }
        if normalized in aliases:
            return aliases[normalized]
        raise ValueError(
            "Unsupported app target. Try Discord, VS Code, Brave, browser, or OBS."
        )

    def _target_timeout_ms(self, config: JarvisConfig, target_name: str) -> int:
        if target_name == "brave":
            return config.matching.brave.launch_timeout_ms
        if target_name == "vscode":
            return config.matching.vscode.launch_timeout_ms
        if target_name == "discord":
            return config.matching.discord.launch_timeout_ms
        if target_name == "obs":
            return config.matching.obs.launch_timeout_ms
        return 15_000
