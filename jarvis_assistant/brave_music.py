from __future__ import annotations

import time
from urllib.parse import quote_plus

import win32api
import win32con

from jarvis_assistant.models import JarvisConfig, PlaybackAttemptResult
from jarvis_assistant.process_utils import build_brave_url_command, launch_subprocess, path_exists
from jarvis_assistant.window_manager import WindowManager


SAFE_SHORTCUT_KEYS: dict[str, int] = {
    "space": win32con.VK_SPACE,
    "enter": win32con.VK_RETURN,
    "k": ord("K"),
}


class BraveMusicController:
    """Best-effort music opening and playback prompting without browser automation."""

    def __init__(self, window_manager: WindowManager, logger) -> None:
        self.window_manager = window_manager
        self.logger = logger.getChild("brave_music")

    def open_and_attempt_playback(
        self,
        config: JarvisConfig,
        dry_run: bool = False,
    ) -> PlaybackAttemptResult:
        music = config.music
        direct_url = music.music_url.strip()
        used_direct_url = bool(direct_url)
        normalized_query = music.music_query.strip().casefold()
        url_to_open = (
            direct_url
            if used_direct_url
            else f"https://music.youtube.com/search?q={quote_plus(music.music_query.strip())}"
        )

        if used_direct_url:
            self.logger.info("Opened direct YouTube Music URL.")
        else:
            self.logger.warning(
                "No direct music URL configured; opened search URL as best-effort fallback."
            )

        if dry_run:
            details = (
                "DRY RUN: would launch Brave with direct music URL."
                if used_direct_url
                else "DRY RUN: would launch Brave with YouTube Music search URL."
            )
            self.logger.info(details)
            return PlaybackAttemptResult(
                url_opened=url_to_open,
                used_direct_url=used_direct_url,
                playback_attempted=used_direct_url,
                playback_likely_started=False,
                playback_confirmed=False,
                details=details,
            )

        if not path_exists(config.paths.brave_path):
            raise FileNotFoundError(f"Brave executable not found: {config.paths.brave_path}")

        launch_subprocess(build_brave_url_command(config, url_to_open), config.paths.brave_path)
        time.sleep(max(0, music.post_open_delay_ms) / 1000.0)

        playback_attempted = False
        playback_likely_started = False
        playback_confirmed = False
        details: list[str] = []

        brave_window = self.window_manager.wait_for_window(
            config.matching.brave,
            timeout_ms=music.playback_start_timeout_ms,
        )
        if brave_window is None:
            details.append("Brave window did not appear before playback timeout.")
            self.logger.warning(details[-1])
            return PlaybackAttemptResult(
                url_opened=url_to_open,
                used_direct_url=used_direct_url,
                playback_attempted=False,
                playback_likely_started=False,
                playback_confirmed=False,
                details=" ".join(details),
            )

        if used_direct_url and self._direct_page_looks_active(brave_window.title, normalized_query):
            details.append(
                "Direct music page appears active; skipped play/pause fallback to avoid interrupting playback."
            )
            self.logger.info(details[-1])
            if music.verify_playback_best_effort:
                playback_likely_started = True
                details.append("Playback likely started.")
                self.logger.info(details[-1])
            else:
                details.append("Playback verification disabled.")
            return PlaybackAttemptResult(
                url_opened=url_to_open,
                used_direct_url=used_direct_url,
                playback_attempted=False,
                playback_likely_started=playback_likely_started,
                playback_confirmed=False,
                details=" ".join(details),
            )

        if music.use_media_key_fallback or music.use_play_shortcut_fallback:
            focused, reason = self.window_manager.focus_window(
                brave_window,
                retry_count=config.matching.brave.focus_retry_count,
                retry_delay_ms=config.matching.brave.focus_retry_delay_ms,
            )
            if not focused:
                details.append(f"Could not focus Brave for playback fallback: {reason}.")
                self.logger.warning(details[-1])
            else:
                if music.use_media_key_fallback:
                    self._tap_virtual_key(win32con.VK_MEDIA_PLAY_PAUSE)
                    playback_attempted = True
                    details.append("Attempted playback fallback via media key.")
                    self.logger.info(details[-1])
                    time.sleep(0.35)
                if music.use_play_shortcut_fallback:
                    shortcut_key = SAFE_SHORTCUT_KEYS.get(music.play_shortcut_key.casefold())
                    if shortcut_key is None:
                        details.append(
                            f"Configured play shortcut '{music.play_shortcut_key}' is not allowed."
                        )
                        self.logger.warning(details[-1])
                    else:
                        self._tap_virtual_key(shortcut_key)
                        playback_attempted = True
                        details.append(
                            f"Attempted playback fallback via safe shortcut '{music.play_shortcut_key}'."
                        )
                        self.logger.info(details[-1])
                        time.sleep(0.25)

        if not playback_attempted and used_direct_url:
            details.append("Direct URL opened, but no explicit playback fallback was attempted.")
        elif not playback_attempted and not used_direct_url:
            details.append("Only the search page was opened; playback was not attempted.")

        if music.verify_playback_best_effort:
            verification = self._best_effort_verify(
                config,
                used_direct_url,
                playback_attempted,
                normalized_query,
            )
            playback_likely_started = verification
            if verification:
                self.logger.info("Playback likely started.")
                details.append("Playback likely started.")
            else:
                self.logger.warning("Playback could not be confirmed.")
                details.append("Playback could not be confirmed.")
        else:
            details.append("Playback verification disabled.")

        return PlaybackAttemptResult(
            url_opened=url_to_open,
            used_direct_url=used_direct_url,
            playback_attempted=playback_attempted,
            playback_likely_started=playback_likely_started,
            playback_confirmed=playback_confirmed,
            details=" ".join(details),
        )

    def _direct_page_looks_active(self, title: str, normalized_query: str) -> bool:
        lowered = (title or "").casefold()
        if not lowered:
            return False
        if "search" in lowered:
            return False
        if normalized_query and normalized_query[:18] in lowered:
            return True
        return "youtube music" in lowered

    def _best_effort_verify(
        self,
        config: JarvisConfig,
        used_direct_url: bool,
        playback_attempted: bool,
        normalized_query: str,
    ) -> bool:
        if not playback_attempted:
            return False
        brave_window = self.window_manager.find_window(config.matching.brave)
        if brave_window is None:
            return False
        title = brave_window.title.casefold()
        if not title:
            return used_direct_url
        if normalized_query and normalized_query[:18] in title:
            return True
        if used_direct_url and "search" not in title and "youtube music" in title:
            return True
        return False

    def _tap_virtual_key(self, virtual_key: int) -> None:
        win32api.keybd_event(virtual_key, 0, 0, 0)
        win32api.keybd_event(virtual_key, 0, win32con.KEYEVENTF_KEYUP, 0)
