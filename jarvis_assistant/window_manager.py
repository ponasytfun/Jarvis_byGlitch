from __future__ import annotations

import ctypes
import re
import time
from collections.abc import Iterable

import psutil
import pywintypes
import win32api
import win32con
import win32gui
import win32process

from jarvis_assistant.models import WindowCandidate, WindowMatchConfig


user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


class WindowManager:
    """Visible top-level window discovery and reliable Win32 window control."""

    def __init__(self, logger) -> None:
        self.logger = logger.getChild("window_manager")

    def enumerate_windows(self) -> list[WindowCandidate]:
        windows: list[WindowCandidate] = []

        def callback(hwnd: int, _) -> bool:
            if not win32gui.IsWindow(hwnd):
                return True
            if not win32gui.IsWindowVisible(hwnd):
                return True
            if win32gui.GetParent(hwnd):
                return True

            title = (win32gui.GetWindowText(hwnd) or "").strip()
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                process_name = psutil.Process(pid).name()
            except Exception:
                pid = 0
                process_name = ""

            if not title and not process_name:
                return True

            rect = tuple(int(value) for value in win32gui.GetWindowRect(hwnd))
            windows.append(
                WindowCandidate(
                    hwnd=hwnd,
                    title=title,
                    pid=pid,
                    process_name=process_name,
                    is_minimized=bool(win32gui.IsIconic(hwnd)),
                    rectangle=rect,
                )
            )
            return True

        win32gui.EnumWindows(callback, None)
        return windows

    def find_window(self, match: WindowMatchConfig) -> WindowCandidate | None:
        matches = self.find_windows(match)
        return matches[0] if matches else None

    def find_windows(self, match: WindowMatchConfig) -> list[WindowCandidate]:
        process_names = [item.casefold() for item in match.allowed_process_names if item]
        title_fragments = [item.casefold() for item in match.allowed_title_fragments if item]
        regex = re.compile(match.title_regex, re.IGNORECASE) if match.title_regex else None
        windows = self.enumerate_windows()

        process_matches = [
            window
            for window in windows
            if window.process_name.casefold() in process_names
        ]
        if process_matches:
            return self._rank_windows(process_matches, title_fragments, regex)

        title_matches = [
            window
            for window in windows
            if title_fragments
            and any(fragment in window.title.casefold() for fragment in title_fragments)
        ]
        if title_matches:
            return self._rank_windows(title_matches, title_fragments, regex)

        if regex is not None:
            return [window for window in windows if regex.search(window.title)]
        return []

    def wait_for_window(
        self,
        match: WindowMatchConfig,
        timeout_ms: int,
        poll_interval_ms: int = 250,
    ) -> WindowCandidate | None:
        deadline = time.monotonic() + (timeout_ms / 1000.0)
        while time.monotonic() < deadline:
            found = self.find_window(match)
            if found is not None:
                return found
            time.sleep(poll_interval_ms / 1000.0)
        return None

    def restore_window(self, window: WindowCandidate) -> bool:
        try:
            if win32gui.IsIconic(window.hwnd):
                win32gui.ShowWindow(window.hwnd, win32con.SW_RESTORE)
            else:
                win32gui.ShowWindow(window.hwnd, win32con.SW_SHOW)
            return True
        except Exception:
            self.logger.exception("Unable to restore window '%s'.", window.title)
            return False

    def minimize_window(self, window: WindowCandidate) -> bool:
        try:
            win32gui.ShowWindow(window.hwnd, win32con.SW_MINIMIZE)
            return True
        except Exception:
            self.logger.exception("Unable to minimize window '%s'.", window.title)
            return False

    def focus_window(
        self,
        window: WindowCandidate,
        retry_count: int = 3,
        retry_delay_ms: int = 350,
    ) -> tuple[bool, str]:
        last_reason = "focus denied"
        for attempt in range(1, max(1, retry_count) + 1):
            if window.is_minimized or win32gui.IsIconic(window.hwnd):
                if not self.restore_window(window):
                    last_reason = "minimized window could not be restored"
                    time.sleep(retry_delay_ms / 1000.0)
                    continue
                last_reason = "minimized window restored"

            if self._apply_focus_sequence(window.hwnd):
                return True, "focused"

            last_reason = "focus denied"
            time.sleep(retry_delay_ms / 1000.0)
        return False, last_reason

    def move_and_resize(
        self,
        window: WindowCandidate,
        left: int,
        top: int,
        width: int,
        height: int,
    ) -> bool:
        try:
            if win32gui.IsIconic(window.hwnd) or bool(user32.IsZoomed(window.hwnd)):
                win32gui.ShowWindow(window.hwnd, win32con.SW_RESTORE)
                time.sleep(0.08)
            win32gui.SetWindowPos(
                window.hwnd,
                win32con.HWND_TOP,
                left,
                top,
                width,
                height,
                win32con.SWP_SHOWWINDOW,
            )
            time.sleep(0.05)
            rect = win32gui.GetWindowRect(window.hwnd)
            return abs(rect[0] - left) < 32 and abs(rect[1] - top) < 32
        except Exception:
            self.logger.exception("Unable to move window '%s'.", window.title)
            return False

    def arrange_side_by_side(
        self,
        left_window: WindowCandidate,
        right_window: WindowCandidate,
    ) -> bool:
        work_left, work_top, work_right, work_bottom = self.get_primary_work_area()
        width = work_right - work_left
        height = work_bottom - work_top
        left_width = width // 2
        right_width = width - left_width

        left_ok = self.move_and_resize(
            left_window,
            work_left,
            work_top,
            left_width,
            height,
        )
        right_ok = self.move_and_resize(
            right_window,
            work_left + left_width,
            work_top,
            right_width,
            height,
        )
        if not (left_ok and right_ok):
            return False

        time.sleep(0.1)
        left_rect = win32gui.GetWindowRect(left_window.hwnd)
        right_rect = win32gui.GetWindowRect(right_window.hwnd)
        left_valid = abs(left_rect[0] - work_left) < 24 and abs(left_rect[2] - (work_left + left_width)) < 32
        right_valid = abs(right_rect[0] - (work_left + left_width)) < 32 and abs(right_rect[2] - work_right) < 32
        if not (left_valid and right_valid):
            self.logger.warning(
                "Window arrangement verification was imperfect. left=%s right=%s",
                left_rect,
                right_rect,
            )
            return False
        return True

    def get_primary_work_area(self) -> tuple[int, int, int, int]:
        monitor = win32api.MonitorFromPoint((0, 0), win32con.MONITOR_DEFAULTTOPRIMARY)
        info = win32api.GetMonitorInfo(monitor)
        left, top, right, bottom = info["Work"]
        return int(left), int(top), int(right), int(bottom)

    def has_process(self, process_names: Iterable[str]) -> bool:
        normalized = {item.casefold() for item in process_names if item}
        if not normalized:
            return False
        for process in psutil.process_iter(attrs=["name"]):
            name = (process.info.get("name") or "").casefold()
            if name in normalized:
                return True
        return False

    def _choose_best_window(
        self,
        windows: list[WindowCandidate],
        title_fragments: list[str],
        regex: re.Pattern[str] | None,
    ) -> WindowCandidate:
        return self._rank_windows(windows, title_fragments, regex)[0]

    def _rank_windows(
        self,
        windows: list[WindowCandidate],
        title_fragments: list[str],
        regex: re.Pattern[str] | None,
    ) -> list[WindowCandidate]:
        def score(window: WindowCandidate) -> tuple[int, int, int, int]:
            lowered_title = window.title.casefold()
            fragment_score = sum(1 for fragment in title_fragments if fragment in lowered_title)
            regex_score = 1 if regex and regex.search(window.title) else 0
            minimized_score = 0 if window.is_minimized else 1
            title_length = len(window.title)
            return fragment_score, regex_score, minimized_score, title_length

        return sorted(windows, key=score, reverse=True)

    def _apply_focus_sequence(self, hwnd: int) -> bool:
        try:
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            else:
                win32gui.ShowWindow(hwnd, win32con.SW_SHOW)

            foreground = user32.GetForegroundWindow()
            current_thread = kernel32.GetCurrentThreadId()
            target_thread = user32.GetWindowThreadProcessId(hwnd, 0)
            foreground_thread = user32.GetWindowThreadProcessId(foreground, 0) if foreground else 0

            if foreground_thread and foreground_thread != current_thread:
                user32.AttachThreadInput(foreground_thread, current_thread, True)
            if target_thread and target_thread != current_thread:
                user32.AttachThreadInput(target_thread, current_thread, True)

            win32gui.BringWindowToTop(hwnd)
            flags = win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, flags)
            win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0, flags)

            try:
                user32.SetForegroundWindow(hwnd)
            except pywintypes.error:
                pass
            try:
                user32.SetFocus(hwnd)
            except Exception:
                pass
            try:
                user32.SetActiveWindow(hwnd)
            except Exception:
                pass
            time.sleep(0.05)
            return user32.GetForegroundWindow() == hwnd
        except Exception:
            self.logger.exception("Focus sequence failed for hwnd=%s.", hwnd)
            return False
        finally:
            try:
                foreground = user32.GetForegroundWindow()
                current_thread = kernel32.GetCurrentThreadId()
                target_thread = user32.GetWindowThreadProcessId(hwnd, 0)
                foreground_thread = (
                    user32.GetWindowThreadProcessId(foreground, 0) if foreground else 0
                )
                if target_thread and target_thread != current_thread:
                    user32.AttachThreadInput(target_thread, current_thread, False)
                if foreground_thread and foreground_thread != current_thread:
                    user32.AttachThreadInput(foreground_thread, current_thread, False)
            except Exception:
                pass
