from __future__ import annotations

import time
from typing import Any, Callable

import win32api
import win32con

from jarvis_assistant.brave_music import SAFE_SHORTCUT_KEYS, BraveMusicController
from jarvis_assistant.models import JarvisConfig, PlaybackAttemptResult, WindowMatchConfig
from jarvis_assistant.process_utils import (
    build_target_command,
    launch_subprocess,
    path_exists,
)
from jarvis_assistant.window_manager import WindowManager


class ActionExecutor:
    def __init__(
        self,
        window_manager: WindowManager,
        brave_music: BraveMusicController,
        logger,
        notifier: Callable[[str, str], None] | None = None,
    ) -> None:
        self.window_manager = window_manager
        self.brave_music = brave_music
        self.logger = logger.getChild("actions")
        self.notifier = notifier

    def execute(
        self,
        action_name: str,
        params: dict[str, Any],
        config: JarvisConfig,
        dry_run: bool,
        timeout_ms: int | None = None,
    ) -> Any:
        handler = getattr(self, f"_action_{action_name}", None)
        if handler is None:
            raise ValueError(f"Unsupported action: {action_name}")
        self.logger.info("Action start: %s", action_name)
        result = handler(params, config, dry_run, timeout_ms)
        self.logger.info("Action finish: %s", action_name)
        return result

    def _action_open_url_in_brave(
        self,
        params: dict[str, Any],
        config: JarvisConfig,
        dry_run: bool,
        timeout_ms: int | None,
    ) -> None:
        if bool(params.get("use_music_defaults", False)):
            self._action_open_music_in_brave(params, config, dry_run, timeout_ms)
            return
        url = str(params.get("url", "")).strip()
        if not url:
            raise ValueError("open_url_in_brave requires a non-empty url parameter.")
        command = build_target_command("brave", config)
        command.append(url)
        self.logger.info("Launching Brave with URL: %s", url)
        if dry_run:
            self.logger.info("DRY RUN: would execute %s", command)
            return
        if not path_exists(config.paths.brave_path):
            raise FileNotFoundError(f"Brave path does not exist: {config.paths.brave_path}")
        launch_subprocess(command, config.paths.brave_path)

    def _action_open_music_in_brave(
        self,
        params: dict[str, Any],
        config: JarvisConfig,
        dry_run: bool,
        timeout_ms: int | None,
    ) -> PlaybackAttemptResult:
        result = self.brave_music.open_and_attempt_playback(config=config, dry_run=dry_run)
        if result.playback_likely_started:
            self.logger.info("Music playback likely started.")
            return result

        if result.used_direct_url and result.playback_attempted:
            self.logger.warning(
                "Playback was attempted on a direct music URL but could not be confirmed. Details: %s",
                result.details,
            )
            return result

        if result.used_direct_url and not result.playback_attempted:
            message = (
                "Opened the direct music URL, but no meaningful playback attempt completed. "
                f"Details: {result.details}"
            )
            self.logger.warning(message)
            raise RuntimeError(message)

        if result.playback_attempted:
            message = (
                "Opened the search fallback and attempted playback, but playback could not be "
                f"confirmed. Details: {result.details}"
            )
            self.logger.warning(message)
            raise RuntimeError(message)

        message = (
            "Only the music page or search results opened; playback was not verified. "
            f"Details: {result.details}"
        )
        self.logger.warning(message)
        raise RuntimeError(message)

    def _action_focus_or_launch_app(
        self,
        params: dict[str, Any],
        config: JarvisConfig,
        dry_run: bool,
        timeout_ms: int | None,
    ) -> None:
        target_name = str(params["target"]).strip().lower()
        match = self._get_match_config(config, target_name)
        existing_window = self.window_manager.find_window(match)
        if existing_window is not None:
            self.logger.info("Found existing %s window: %s", target_name, existing_window.title)
            if existing_window.is_minimized:
                self.logger.info("%s window is minimized.", target_name)
            if dry_run:
                self.logger.info("DRY RUN: would focus existing %s window.", target_name)
                return
            focused, reason = self._focus_with_retries(target_name, match, existing_window)
            if focused:
                return
            self.logger.warning(
                "Unable to focus existing window for %s: %s",
                target_name,
                reason,
            )

        process_found = self.window_manager.has_process(match.allowed_process_names)
        if process_found and existing_window is None:
            self.logger.warning("Process found but no usable window for %s.", target_name)
        if not process_found:
            self.logger.warning("No process found for %s.", target_name)

        if dry_run:
            self.logger.info("DRY RUN: would launch or relaunch %s.", target_name)
            return

        command = build_target_command(target_name, config)
        executable = self._get_executable_path(config, target_name)
        if not path_exists(executable):
            raise FileNotFoundError(f"{target_name} path does not exist: {executable}")

        self.logger.info("Launching or relaunching %s with command %s", target_name, command)
        launch_subprocess(command, executable)

        wait_timeout_ms = (
            int(params.get("launch_timeout_ms", 0))
            or timeout_ms
            or match.launch_timeout_ms
        )
        window = self.window_manager.wait_for_window(match, timeout_ms=wait_timeout_ms)
        if window is None:
            message = f"Timeout waiting for window for {target_name}."
            self.logger.warning(message)
            raise TimeoutError(message)

        focused, reason = self._focus_with_retries(target_name, match, window)
        if not focused:
            message = f"Unable to focus existing window for {target_name}: {reason}"
            self.logger.warning(message)
            raise RuntimeError(message)

    def _action_minimize_window(
        self,
        params: dict[str, Any],
        config: JarvisConfig,
        dry_run: bool,
        timeout_ms: int | None,
    ) -> None:
        match = self._resolve_match(params, config)
        window = self.window_manager.find_window(match)
        if window is None:
            raise RuntimeError("No matching window found to minimize.")
        if dry_run:
            self.logger.info("DRY RUN: would minimize '%s'.", window.title)
            return
        if not self.window_manager.minimize_window(window):
            raise RuntimeError(f"Failed to minimize '{window.title}'.")

    def _action_focus_window(
        self,
        params: dict[str, Any],
        config: JarvisConfig,
        dry_run: bool,
        timeout_ms: int | None,
    ) -> None:
        match = self._resolve_match(params, config)
        window = self.window_manager.find_window(match)
        if window is None:
            raise RuntimeError("No matching window found to focus.")
        if dry_run:
            self.logger.info("DRY RUN: would focus '%s'.", window.title)
            return
        focused, reason = self.window_manager.focus_window(
            window,
            retry_count=match.focus_retry_count,
            retry_delay_ms=match.focus_retry_delay_ms,
        )
        if not focused:
            raise RuntimeError(f"Unable to focus '{window.title}': {reason}")

    def _action_arrange_two_windows_side_by_side(
        self,
        params: dict[str, Any],
        config: JarvisConfig,
        dry_run: bool,
        timeout_ms: int | None,
    ) -> None:
        left_match = self._get_match_config(config, str(params["left_target"]).strip().lower())
        right_match = self._get_match_config(config, str(params["right_target"]).strip().lower())
        left_window = self.window_manager.find_window(left_match)
        right_window = self.window_manager.find_window(right_match)
        if left_window is None or right_window is None:
            missing = []
            if left_window is None:
                missing.append(str(params["left_target"]))
            if right_window is None:
                missing.append(str(params["right_target"]))
            raise RuntimeError(f"Missing windows for arrange: {', '.join(missing)}")
        if dry_run:
            self.logger.info("DRY RUN: would arrange windows side by side.")
            return
        if not self.window_manager.arrange_side_by_side(left_window, right_window):
            raise RuntimeError("Unable to arrange windows side by side.")
        self.logger.info(
            "Arranged %s and %s side by side successfully.",
            params["left_target"],
            params["right_target"],
        )

    def _action_wait(
        self,
        params: dict[str, Any],
        config: JarvisConfig,
        dry_run: bool,
        timeout_ms: int | None,
    ) -> None:
        if bool(params.get("use_music_open_delay", False)):
            milliseconds = int(config.music.post_open_delay_ms)
        else:
            milliseconds = int(params.get("milliseconds", 0))
        self.logger.info("Waiting for %s ms.", milliseconds)
        if not dry_run:
            time.sleep(milliseconds / 1000.0)

    def _action_show_notification(
        self,
        params: dict[str, Any],
        config: JarvisConfig,
        dry_run: bool,
        timeout_ms: int | None,
    ) -> None:
        title = str(params.get("title", config.app.name))
        message = str(params.get("message", ""))
        self.logger.info("Notification: %s", message)
        if dry_run:
            self.logger.info("DRY RUN: would show notification.")
            return
        if self.notifier is not None:
            self.notifier(title, message)

    def _action_send_media_play_pause(
        self,
        params: dict[str, Any],
        config: JarvisConfig,
        dry_run: bool,
        timeout_ms: int | None,
    ) -> None:
        self.logger.info("Sending media play/pause.")
        if dry_run:
            return
        self._tap_virtual_key(win32con.VK_MEDIA_PLAY_PAUSE)

    def _action_send_keypress_to_window(
        self,
        params: dict[str, Any],
        config: JarvisConfig,
        dry_run: bool,
        timeout_ms: int | None,
    ) -> None:
        key_name = str(params["key"]).casefold()
        virtual_key = SAFE_SHORTCUT_KEYS.get(key_name)
        if virtual_key is None:
            raise ValueError(f"Unsupported safe key: {key_name}")
        match = self._resolve_match(params, config)
        window = self.window_manager.find_window(match)
        if window is None:
            raise RuntimeError("No matching window found for keypress.")
        if dry_run:
            self.logger.info("DRY RUN: would send '%s' to '%s'.", key_name, window.title)
            return
        focused, reason = self.window_manager.focus_window(
            window,
            retry_count=match.focus_retry_count,
            retry_delay_ms=match.focus_retry_delay_ms,
        )
        if not focused:
            raise RuntimeError(f"Unable to focus '{window.title}' for keypress: {reason}")
        time.sleep(0.15)
        self._tap_virtual_key(virtual_key)

    def _resolve_match(
        self,
        params: dict[str, Any],
        config: JarvisConfig,
    ) -> WindowMatchConfig:
        target_name = str(params.get("target", "")).strip().lower()
        if target_name:
            return self._get_match_config(config, target_name)
        return WindowMatchConfig(
            allowed_title_fragments=[
                str(item) for item in params.get("allowed_title_fragments", [])
            ],
            allowed_process_names=[
                str(item) for item in params.get("allowed_process_names", [])
            ],
            title_regex=str(params.get("title_regex", "")),
            focus_retry_count=int(params.get("focus_retry_count", 3)),
            focus_retry_delay_ms=int(params.get("focus_retry_delay_ms", 350)),
            launch_timeout_ms=int(params.get("launch_timeout_ms", 15_000)),
            continue_on_error=bool(params.get("continue_on_error", True)),
        )

    def _get_match_config(self, config: JarvisConfig, target_name: str) -> WindowMatchConfig:
        if target_name == "brave":
            return config.matching.brave
        if target_name == "vscode":
            return config.matching.vscode
        if target_name == "discord":
            return config.matching.discord
        if target_name == "obs":
            return config.matching.obs
        raise KeyError(f"Unknown target name: {target_name}")

    def _get_executable_path(self, config: JarvisConfig, target_name: str) -> str:
        if target_name == "brave":
            return config.paths.brave_path
        if target_name == "vscode":
            return config.paths.vscode_path
        if target_name == "discord":
            return config.paths.discord_path
        if target_name == "obs":
            return config.paths.obs_path
        raise KeyError(f"Unknown target name: {target_name}")

    def _focus_with_retries(
        self,
        target_name: str,
        match: WindowMatchConfig,
        initial_window,
    ) -> tuple[bool, str]:
        candidate = initial_window
        last_reason = "focus denied"
        for _ in range(max(1, match.focus_retry_count)):
            focused, reason = self.window_manager.focus_window(
                candidate,
                retry_count=1,
                retry_delay_ms=match.focus_retry_delay_ms,
            )
            if focused:
                return True, "focused"
            last_reason = reason
            refreshed = self.window_manager.find_window(match)
            if refreshed is not None:
                candidate = refreshed
            time.sleep(match.focus_retry_delay_ms / 1000.0)
        return False, last_reason

    def _tap_virtual_key(self, virtual_key: int) -> None:
        win32api.keybd_event(virtual_key, 0, 0, 0)
        win32api.keybd_event(virtual_key, 0, win32con.KEYEVENTF_KEYUP, 0)
