from __future__ import annotations

import queue
import time
from collections.abc import Callable
from typing import Any

import numpy as np
import sounddevice as sd

from jarvis_assistant.clap_detector import ClapDetector
from jarvis_assistant.models import AudioCalibration, AudioConfig, AudioLevel, TriggerConfig


class AudioListener:
    def __init__(self, logger) -> None:
        self.logger = logger.getChild("audio")
        self._thread = None
        self._stop_requested = False

    @staticmethod
    def list_input_devices() -> list[dict[str, Any]]:
        devices: list[dict[str, Any]] = [
            {
                "index": -1,
                "name": "Default system input",
                "max_input_channels": 0,
                "default_samplerate": 0,
            }
        ]
        for index, device in enumerate(sd.query_devices()):
            if int(device.get("max_input_channels", 0)) <= 0:
                continue
            devices.append(
                {
                    "index": int(index),
                    "name": str(device.get("name", f"Input {index}")),
                    "max_input_channels": int(device.get("max_input_channels", 0)),
                    "default_samplerate": int(float(device.get("default_samplerate", 0))),
                }
            )
        return devices

    @staticmethod
    def list_output_devices() -> list[dict[str, Any]]:
        devices: list[dict[str, Any]] = [
            {
                "index": -1,
                "name": "Default system output",
                "max_output_channels": 0,
                "default_samplerate": 0,
            }
        ]
        for index, device in enumerate(sd.query_devices()):
            if int(device.get("max_output_channels", 0)) <= 0:
                continue
            devices.append(
                {
                    "index": int(index),
                    "name": str(device.get("name", f"Output {index}")),
                    "max_output_channels": int(device.get("max_output_channels", 0)),
                    "default_samplerate": int(float(device.get("default_samplerate", 0))),
                }
            )
        return devices

    @property
    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def calibrate(self, audio_config: AudioConfig, trigger_config: TriggerConfig) -> AudioCalibration:
        detector = ClapDetector(trigger_config, self.logger)
        return self._calibrate_detector(detector, audio_config)

    def start(
        self,
        audio_config: AudioConfig,
        trigger_config: TriggerConfig,
        on_clap: Callable[[Any], None],
        on_level: Callable[[AudioLevel], None],
        on_audio_block: Callable[[float, np.ndarray, float, float], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        if self.is_running:
            self.logger.warning("Audio listener is already running.")
            return

        import threading

        self._stop_requested = False
        self._thread = threading.Thread(
            target=self._run_stream_loop,
            args=(audio_config, trigger_config, on_clap, on_level, on_audio_block, on_error),
            name="JarvisAudioListener",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_requested = True
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None

    def _run_stream_loop(
        self,
        audio_config: AudioConfig,
        trigger_config: TriggerConfig,
        on_clap: Callable[[Any], None],
        on_level: Callable[[AudioLevel], None],
        on_audio_block: Callable[[float, np.ndarray, float, float], None] | None,
        on_error: Callable[[str], None] | None,
    ) -> None:
        detector = ClapDetector(trigger_config, self.logger)
        try:
            self._calibrate_detector(detector, audio_config)
            metrics_queue: queue.Queue[tuple[float, float, float]] = queue.Queue(maxsize=128)

            def audio_callback(indata, frames, time_info, status) -> None:
                if status:
                    self.logger.warning("Audio stream status: %s", status)

                samples = np.asarray(indata[:, 0], dtype=np.float32)
                peak = float(np.max(np.abs(samples)))
                rms = ClapDetector.calculate_rms(samples)
                timestamp = time.monotonic()
                if on_audio_block is not None:
                    try:
                        on_audio_block(timestamp, samples.copy(), peak, rms)
                    except Exception as exc:
                        self.logger.debug("Audio block subscriber rejected frame: %s", exc)
                try:
                    metrics_queue.put_nowait((timestamp, rms, peak))
                except queue.Full:
                    pass

            block_size = max(1, int(audio_config.sample_rate * audio_config.block_duration_ms / 1000))
            self.logger.info(
                "Opening microphone stream. device_index=%s sample_rate=%s block_duration_ms=%s",
                audio_config.device_index,
                audio_config.sample_rate,
                audio_config.block_duration_ms,
            )

            with sd.InputStream(
                samplerate=audio_config.sample_rate,
                device=None if audio_config.device_index in (-1, None) else audio_config.device_index,
                channels=1,
                dtype="float32",
                blocksize=block_size,
                callback=audio_callback,
            ):
                self.logger.info("Microphone listening started.")
                while not self._stop_requested:
                    try:
                        timestamp, rms, peak = metrics_queue.get(timeout=0.2)
                    except queue.Empty:
                        continue

                    on_level(self._build_level(peak, detector.effective_threshold, rms))
                    event = detector.process_block(timestamp, rms, peak)
                    if event is not None:
                        on_clap(event)
        except Exception as exc:
            message = f"Microphone error: {exc}"
            self.logger.exception(message)
            if on_error is not None:
                on_error(message)
        finally:
            self.logger.info("Microphone listening stopped.")

    def _calibrate_detector(
        self,
        detector: ClapDetector,
        audio_config: AudioConfig,
    ) -> AudioCalibration:
        self.logger.info(
            "Calibrating microphone for %.1f seconds using device %s.",
            audio_config.calibration_seconds,
            audio_config.device_index,
        )
        frame_count = max(1, int(audio_config.sample_rate * audio_config.calibration_seconds))
        recording = sd.rec(
            frame_count,
            samplerate=audio_config.sample_rate,
            device=None if audio_config.device_index in (-1, None) else audio_config.device_index,
            channels=1,
            dtype="float32",
        )
        sd.wait()

        samples = np.abs(np.asarray(recording[:, 0], dtype=np.float32))
        block_size = max(1, int(audio_config.sample_rate * 0.02))
        peaks = []
        for offset in range(0, samples.size, block_size):
            block = samples[offset : offset + block_size]
            if block.size:
                peaks.append(float(np.max(block)))
        if not peaks:
            peaks = [0.0]

        noise_floor = float(np.percentile(np.asarray(peaks, dtype=np.float32), 70))
        calibration = detector.apply_calibration(noise_floor)
        self.logger.info(
            "Calibration finished. noise_floor=%.4f effective_threshold=%.4f",
            calibration.noise_floor,
            calibration.effective_threshold,
        )
        return calibration

    @staticmethod
    def _build_level(peak: float, threshold: float, rms: float) -> AudioLevel:
        divisor = max(threshold * 1.8, 0.2)
        normalized = min(1.0, max(0.0, peak / divisor))
        return AudioLevel(normalized=normalized, peak=peak, rms=rms)
