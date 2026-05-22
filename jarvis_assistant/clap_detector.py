from __future__ import annotations

import math
from collections import deque
from typing import Deque

from jarvis_assistant.models import AudioCalibration, ClapEvent, TriggerConfig


class ClapDetector:
    """Practical clap detector tuned for indoor rooms and transient sounds."""

    def __init__(self, trigger_config: TriggerConfig, logger) -> None:
        self.config = trigger_config
        self.logger = logger.getChild("clap_detector")
        self._recent_claps: Deque[float] = deque()
        self._noise_floor = 0.0
        self._effective_threshold = trigger_config.amplitude_threshold
        self._above_threshold = False
        self._last_peak_timestamp = 0.0

    @property
    def noise_floor(self) -> float:
        return self._noise_floor

    @property
    def effective_threshold(self) -> float:
        return self._effective_threshold

    def apply_calibration(self, noise_floor: float) -> AudioCalibration:
        self._noise_floor = max(0.0, noise_floor)
        if self.config.noise_floor_auto_calibrate:
            self._effective_threshold = min(
                0.38,
                max(self.config.amplitude_threshold, (self._noise_floor * 2.2) + 0.02),
            )
        else:
            self._effective_threshold = self.config.amplitude_threshold

        self.logger.info(
            "Calibration applied. noise_floor=%.4f effective_threshold=%.4f",
            self._noise_floor,
            self._effective_threshold,
        )
        return AudioCalibration(
            noise_floor=self._noise_floor,
            effective_threshold=self._effective_threshold,
        )

    def process_block(self, timestamp: float, rms: float, peak: float) -> ClapEvent | None:
        self._expire_stale_claps(timestamp)

        reset_threshold = max(self._effective_threshold * 0.55, self._noise_floor * 1.4)
        if peak < reset_threshold:
            self._above_threshold = False

        if peak < self._effective_threshold or self._above_threshold:
            return None

        duplicate_suppression = max(0.08, (self.config.min_clap_gap_ms / 1000.0) * 0.35)
        if (timestamp - self._last_peak_timestamp) < duplicate_suppression:
            return None

        transient_ratio = peak / max(rms, 0.0001)
        transient_strength = peak - (rms * 1.35)
        minimum_transient_strength = max(self._effective_threshold * 0.35, 0.015)
        if transient_ratio < 1.8 or transient_strength < minimum_transient_strength:
            return None

        self._above_threshold = True
        self._last_peak_timestamp = timestamp

        min_gap_seconds = self.config.min_clap_gap_ms / 1000.0
        max_gap_seconds = self.config.max_clap_gap_ms / 1000.0

        if self._recent_claps and (timestamp - self._recent_claps[-1]) > max_gap_seconds:
            self._recent_claps.clear()

        self._recent_claps.append(timestamp)
        self.logger.debug(
            "Clap candidate accepted. peak=%.4f rms=%.4f ratio=%.2f recent=%s",
            peak,
            rms,
            transient_ratio,
            len(self._recent_claps),
        )

        if len(self._recent_claps) < self.config.clap_count:
            return None

        sequence = list(self._recent_claps)[-self.config.clap_count :]
        gaps = [current - previous for previous, current in zip(sequence, sequence[1:])]
        span = sequence[-1] - sequence[0]
        gaps_ok = all(min_gap_seconds <= gap <= max_gap_seconds for gap in gaps)
        within_window = span <= self.config.window_seconds

        if not gaps_ok or not within_window:
            return None

        self._recent_claps.clear()
        self.logger.info(
            "Detected %s claps in %.2f seconds.",
            self.config.clap_count,
            span,
        )
        return ClapEvent(
            timestamp=timestamp,
            peak=peak,
            rms=rms,
            effective_threshold=self._effective_threshold,
            clap_timestamps=sequence,
        )

    def _expire_stale_claps(self, timestamp: float) -> None:
        while self._recent_claps and (
            timestamp - self._recent_claps[0] > self.config.window_seconds
        ):
            self._recent_claps.popleft()

    @staticmethod
    def calculate_rms(samples) -> float:
        return float(math.sqrt(max(float((samples * samples).mean()), 0.0)))
