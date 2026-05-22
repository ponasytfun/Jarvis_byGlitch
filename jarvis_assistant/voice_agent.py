from __future__ import annotations

import os
import queue
import shutil
import subprocess
import tempfile
import threading
import time
import wave
from collections import deque
from pathlib import Path

import numpy as np
import sounddevice as sd
from PySide6.QtCore import QObject, Signal

from jarvis_assistant.ai_manager import LocalAIManager
from jarvis_assistant.assistant_engine import AssistantEngine, AssistantTurnResult
from jarvis_assistant.models import (
    AudioProbeResult,
    JarvisConfig,
    SpeechCaptureResult,
    VoiceConfig,
)
from jarvis_assistant.paths import expand_windows_path

try:
    from faster_whisper import WhisperModel
except Exception:  # pragma: no cover - optional dependency
    WhisperModel = None

try:
    from kokoro_onnx import Kokoro
except Exception:  # pragma: no cover - optional dependency
    Kokoro = None

try:
    from openwakeword.model import Model as OpenWakeWordModel
except Exception:  # pragma: no cover - optional dependency
    OpenWakeWordModel = None

try:
    import win32com.client as win32_client
except Exception:  # pragma: no cover - optional dependency
    win32_client = None


class LocalVoiceAgent(QObject):
    """Optional local voice pipeline that can share the clap listener microphone stream."""

    stateChanged = Signal(str, str)
    transcriptCaptured = Signal(str, str)
    responsePrepared = Signal(str)
    warningRaised = Signal(str)
    deactivateRequested = Signal()

    def __init__(
        self,
        ai_manager: LocalAIManager,
        assistant_engine: AssistantEngine,
        logger,
    ) -> None:
        super().__init__()
        self.ai_manager = ai_manager
        self.assistant_engine = assistant_engine
        self.logger = logger.getChild("voice")
        self._queue: queue.Queue[tuple[float, np.ndarray, float, float]] = queue.Queue(maxsize=512)
        self._thread: threading.Thread | None = None
        self._running = False
        self._config: JarvisConfig | None = None
        self._whisper_model = None
        self._wake_model = None
        self._kokoro_engine = None
        self._manual_capture_lock = threading.Lock()

    @property
    def running(self) -> bool:
        return self._running

    def start(self, config: JarvisConfig) -> None:
        if self._running:
            return
        self._config = config.clone()
        self._running = True
        self._drain_audio_queue()
        self._thread = threading.Thread(
            target=self._loop,
            name="JarvisVoiceAgent",
            daemon=True,
        )
        self._thread.start()
        self.stateChanged.emit("listening", "Voice layer armed.")

    def stop(self) -> None:
        self._running = False
        self._drain_audio_queue()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None
        self.stateChanged.emit("idle", "Voice layer stopped.")

    def push_audio_block(
        self,
        timestamp: float,
        samples: np.ndarray,
        peak: float,
        rms: float,
    ) -> None:
        if not self._running:
            return
        try:
            self._queue.put_nowait((timestamp, samples, peak, rms))
        except queue.Full:
            self.logger.debug("Voice queue full; dropping audio block.")

    def submit_text_prompt(self, config: JarvisConfig, prompt_text: str) -> AssistantTurnResult:
        prompt = prompt_text.strip()
        if not prompt:
            raise ValueError("Prompt text is empty.")
        self._config = config.clone()
        self.stateChanged.emit("thinking", "Sending text prompt to the local AI brain.")
        self.transcriptCaptured.emit(prompt, "text")
        turn_result = self._respond_to_prompt(self._config, prompt, "Text prompt received.")
        self.stateChanged.emit("idle", "Text prompt finished.")
        return turn_result

    def capture_once_and_respond(self, config: JarvisConfig) -> AssistantTurnResult:
        if self.running:
            raise RuntimeError(
                "Click-to-talk is unavailable while the shared voice layer is already using the microphone. "
                "Stop listening first or speak through the armed voice layer."
            )

        with self._manual_capture_lock:
            self._config = config.clone()
            self.stateChanged.emit("listening", "Listening for a voice command.")
            utterance = self._record_single_utterance(self._config)
            self.stateChanged.emit("transcribing", "Transcribing the recorded command.")
            transcript = self._transcribe_audio(self._config, utterance).strip()
            if not transcript:
                self.stateChanged.emit("idle", "No speech recognized.")
                raise RuntimeError("No speech was recognized from the microphone input.")

            self.transcriptCaptured.emit(transcript, "voice")
            if self._config.debug.save_transcripts and self._config.voice.log_transcripts:
                self.logger.info("Manual voice transcript: %s", transcript)

            lowered = transcript.casefold()
            if self._contains_phrase(lowered, self._config.voice.deactivate_phrases):
                self.deactivateRequested.emit()
                self.stateChanged.emit("idle", "Voice deactivation phrase received.")
                return AssistantTurnResult(
                    mode="tool_call",
                    response_text="Voice listening deactivated.",
                    success=True,
                    action_id="stop_listening",
                    detail_text="Voice deactivation phrase received.",
                    payload={"request_stop_listening": True},
                )

            cleaned_prompt = transcript
            if self._config.voice.wake_word_enabled:
                matched_prefix = self._matching_prefix(lowered, self._config.voice.wake_phrases)
                if matched_prefix:
                    cleaned_prompt = transcript[len(matched_prefix) :].strip(" ,.-")

            turn_result = self._respond_to_prompt(
                self._config,
                cleaned_prompt or transcript,
                "Voice command captured.",
            )
            self.stateChanged.emit("idle", "Voice interaction complete.")
            return turn_result

    def test_microphone(self, config: JarvisConfig) -> AudioProbeResult:
        seconds = 3.0
        frame_count = max(1, int(config.audio.sample_rate * seconds))
        device = None if config.audio.device_index in (-1, None) else config.audio.device_index
        device_label = self._describe_input_device(config.audio.device_index)
        self.logger.info(
            "Recording a microphone test sample from %s for %.1f seconds at %s Hz.",
            device_label,
            seconds,
            config.audio.sample_rate,
        )
        recording = sd.rec(
            frame_count,
            samplerate=config.audio.sample_rate,
            device=device,
            channels=1,
            dtype="float32",
        )
        sd.wait()
        samples = np.asarray(recording[:, 0], dtype=np.float32)
        peak = float(np.max(np.abs(samples))) if samples.size else 0.0
        rms = self._calculate_rms(samples)
        average_abs = float(np.mean(np.abs(samples))) if samples.size else 0.0
        detected_audio = self._detect_audio_presence(config.voice, peak, rms, average_abs)
        debug_wav_path = ""
        if config.debug.save_audio_debug_files:
            self._config = config.clone()
            debug_wav_path = self._save_debug_wav(
                samples,
                config.audio.sample_rate,
                prefix="microphone_test",
            )
        return AudioProbeResult(
            peak=peak,
            rms=rms,
            seconds=seconds,
            device_label=device_label,
            sample_rate=config.audio.sample_rate,
            average_abs=average_abs,
            detected_audio=detected_audio,
            debug_wav_path=debug_wav_path,
        )

    def test_stt(self, config: JarvisConfig) -> SpeechCaptureResult:
        if self.running:
            raise RuntimeError("Stop the shared voice layer before running a manual STT test.")

        with self._manual_capture_lock:
            self._config = config.clone()
            self.stateChanged.emit("listening", "Listening for a short speech sample.")
            utterance = self._record_single_utterance(self._config)
            self.stateChanged.emit("transcribing", "Transcribing the speech sample.")
            transcript = self._transcribe_audio(self._config, utterance).strip()
            if not transcript:
                self.stateChanged.emit("idle", "No speech recognized.")
                raise RuntimeError("No speech was recognized from the microphone input.")

            self.transcriptCaptured.emit(transcript, "voice")
            seconds = float(utterance.size) / float(max(1, config.audio.sample_rate))
            peak = float(np.max(np.abs(utterance))) if utterance.size else 0.0
            rms = self._calculate_rms(utterance)
            debug_wav_path = ""
            if config.debug.save_audio_debug_files:
                debug_wav_path = self._save_debug_wav(
                    utterance,
                    config.audio.sample_rate,
                    prefix="stt_test",
                )
            self.stateChanged.emit("idle", "Speech-to-text test finished.")
            return SpeechCaptureResult(
                transcript=transcript,
                peak=peak,
                rms=rms,
                seconds=seconds,
                device_label=self._describe_input_device(config.audio.device_index),
                sample_rate=config.audio.sample_rate,
                debug_wav_path=debug_wav_path,
            )

    def test_tts(self, config: JarvisConfig) -> str:
        phrase = config.voice.test_phrase.strip() or "Voice systems nominal."
        backend = self._speak_text(phrase, config.voice)
        if not backend:
            raise RuntimeError(self.describe_tts_status(config.voice))
        return backend

    def describe_stt_status(self, voice: VoiceConfig) -> str:
        if WhisperModel is None:
            return (
                "Speech-to-text unavailable. Install faster-whisper with a Python 3.11 or 3.12 "
                "environment to enable local transcription."
            )
        return f"Speech-to-text ready through faster-whisper ({voice.stt_model})."

    def describe_tts_status(self, voice: VoiceConfig) -> str:
        backends = self._tts_backend_candidates(voice)
        if "kokoro" in backends and self._kokoro_assets_ready(voice):
            return f"TTS ready through Kokoro ({voice.tts_voice})."
        if "piper" in backends and self._piper_assets_ready(voice):
            return "TTS ready through Piper."
        if "sapi" in backends and win32_client is not None:
            return "TTS ready through Windows Speech API."
        return (
            "No local TTS backend is ready. Configure Kokoro or Piper, or keep pywin32 available "
            "for the Windows Speech API fallback."
        )

    def describe_voice_status(self, config: JarvisConfig) -> str:
        if not config.voice.enabled:
            return "Voice layer disabled."

        parts: list[str] = []
        if config.voice.click_to_talk_enabled:
            parts.append("click-to-talk ready")
        if config.voice.auto_start_with_listening:
            if config.voice.wake_word_enabled:
                parts.append("wake-phrase listening arms with the microphone")
            else:
                parts.append("shared listening arms with the microphone")
        parts.append(self.describe_stt_status(config.voice))
        parts.append(self.describe_tts_status(config.voice))
        return ". ".join(part.rstrip(".") for part in parts if part).strip() + "."

    def _loop(self) -> None:
        config = self._config
        if config is None:
            self._running = False
            return

        voice = config.voice
        block_seconds = max(0.02, config.audio.block_duration_ms / 1000.0)
        threshold = self._effective_voice_threshold(voice)
        silence_seconds = max(0.35, voice.silence_timeout_seconds)
        min_record_seconds = max(0.35, voice.min_record_seconds)
        pre_roll = deque(maxlen=max(1, int(0.6 / block_seconds)))

        recording = False
        utterance_start = 0.0
        last_voice_time = 0.0
        recorded_blocks: list[np.ndarray] = []
        armed_until = 0.0

        wake_model = self._get_wake_model(voice)
        if voice.wake_word_enabled and wake_model is None:
            self.logger.info(
                "No openWakeWord model is configured or available; falling back to wake-phrase recognition."
            )

        while self._running:
            try:
                timestamp, samples, _peak, rms = self._queue.get(timeout=0.25)
            except queue.Empty:
                continue

            pre_roll.append(samples)

            if wake_model is not None and voice.wake_word_enabled:
                try:
                    score = self._predict_wake_score(wake_model, samples)
                    if score >= voice.wake_threshold:
                        armed_until = timestamp + max(5.0, voice.max_utterance_seconds)
                        self.stateChanged.emit("listening", "Wake word detected. Listening for a command.")
                except Exception as exc:
                    self.logger.warning("Wake-word prediction failed: %s", exc)
                    self.warningRaised.emit(
                        "Wake-word prediction failed, so phrase-based wake fallback is being used."
                    )
                    wake_model = None

            wake_gating = voice.wake_word_enabled and wake_model is not None
            can_capture = (not wake_gating) or (timestamp <= armed_until)

            if not recording and can_capture and self._frame_is_speech(rms, threshold, voice):
                recording = True
                utterance_start = timestamp
                last_voice_time = timestamp
                recorded_blocks = [block.copy() for block in pre_roll]
                self.logger.info("Shared voice recording started.")
                self.stateChanged.emit("recording", "Capturing voice command.")
                continue

            if not recording:
                continue

            recorded_blocks.append(samples.copy())
            if self._frame_is_speech(rms, threshold * 0.74, voice):
                last_voice_time = timestamp

            utterance_duration = timestamp - utterance_start
            if (
                utterance_duration >= voice.max_record_seconds
                or (
                    utterance_duration >= min_record_seconds
                    and (timestamp - last_voice_time) >= silence_seconds
                )
            ):
                recording = False
                utterance = (
                    np.concatenate(recorded_blocks)
                    if recorded_blocks
                    else np.array([], dtype=np.float32)
                )
                recorded_blocks = []
                pre_roll.clear()
                self.logger.info(
                    "Shared voice recording stopped after %.2f seconds.",
                    float(utterance.size) / float(max(1, config.audio.sample_rate)),
                )
                self._handle_utterance(config, utterance, wake_model is not None)
                armed_until = 0.0

        self.logger.info("Voice processing loop stopped.")

    def _handle_utterance(
        self,
        config: JarvisConfig,
        utterance: np.ndarray,
        wake_word_backend_active: bool,
    ) -> None:
        if utterance.size < max(8000, config.audio.sample_rate // 2):
            self.logger.debug("Ignoring utterance because it is too short.")
            self.stateChanged.emit("listening", "Voice layer armed.")
            return

        self.stateChanged.emit("transcribing", "Transcribing the captured utterance.")
        transcript = self._transcribe_audio(config, utterance).strip()
        if not transcript:
            self.logger.info("No speech was recognized from the captured utterance.")
            self.stateChanged.emit("listening", "No speech recognized.")
            return

        lowered = transcript.casefold()
        self.transcriptCaptured.emit(transcript, "voice")
        if config.debug.save_transcripts and config.voice.log_transcripts:
            self.logger.info("Voice transcript: %s", transcript)

        if self._contains_phrase(lowered, config.voice.deactivate_phrases):
            self.logger.info("Voice deactivation phrase recognized.")
            self.deactivateRequested.emit()
            self.stateChanged.emit("idle", "Voice deactivation phrase received.")
            return

        cleaned_prompt = transcript
        if config.voice.wake_word_enabled and not wake_word_backend_active:
            matched_prefix = self._matching_prefix(lowered, config.voice.wake_phrases)
            if not matched_prefix:
                self.logger.debug("Ignoring utterance because it did not contain a wake phrase.")
                self.stateChanged.emit("listening", "Waiting for a wake phrase.")
                return
            cleaned_prompt = transcript[len(matched_prefix) :].strip(" ,.-")

        if not cleaned_prompt:
            cleaned_prompt = config.voice.acknowledgement_phrase.strip() or "Yes?"

        try:
            self._respond_to_prompt(config, cleaned_prompt, "Sending command to the local AI brain.")
        except Exception as exc:
            message = str(exc)
            self.logger.error("Local voice response failed: %s", message)
            self.warningRaised.emit(message)
        finally:
            self.stateChanged.emit("listening", "Voice layer armed.")

    def _respond_to_prompt(
        self,
        config: JarvisConfig,
        prompt_text: str,
        thinking_message: str,
    ) -> AssistantTurnResult:
        self.stateChanged.emit("thinking", thinking_message)
        turn_result = self.assistant_engine.handle_prompt(
            config,
            prompt_text,
            on_status=self.stateChanged.emit,
        )
        self.responsePrepared.emit(turn_result.response_text)
        if turn_result.mode == "tool_call":
            self.logger.info(
                "Assistant tool result prepared through %s. action=%s success=%s",
                self.ai_manager.last_status.provider_display_name,
                turn_result.action_id,
                turn_result.success,
            )
        else:
            self.logger.info(
                "AI response prepared through %s.",
                self.ai_manager.last_status.provider_display_name,
            )

        if not turn_result.success and turn_result.detail_text:
            self.warningRaised.emit(turn_result.detail_text)
            self.stateChanged.emit("error", turn_result.detail_text)

        if config.voice.speak_responses:
            self.stateChanged.emit("speaking", "Speaking response.")
            backend = self._speak_text(turn_result.response_text, config.voice)
            if not backend:
                self.warningRaised.emit(
                    "A spoken reply was requested, but no local TTS backend was ready."
                )
            else:
                self.logger.info("Spoken response delivered through %s.", backend)
        return turn_result

    def _record_single_utterance(self, config: JarvisConfig) -> np.ndarray:
        voice = config.voice
        block_size = max(1, int(config.audio.sample_rate * config.audio.block_duration_ms / 1000))
        block_seconds = max(0.02, config.audio.block_duration_ms / 1000.0)
        threshold = self._effective_voice_threshold(voice)
        silence_seconds = max(0.35, voice.silence_timeout_seconds)
        listen_timeout = max(2.0, voice.listen_timeout_seconds)
        min_record_seconds = max(0.35, voice.min_record_seconds)
        max_utterance_seconds = max(4.0, voice.max_record_seconds)
        pre_roll = deque(maxlen=max(1, int(0.5 / block_seconds)))
        device = None if config.audio.device_index in (-1, None) else config.audio.device_index
        device_label = self._describe_input_device(config.audio.device_index)
        consecutive_voice_frames = 0

        self.logger.info(
            "Manual voice capture ready. device=%s sample_rate=%s block_ms=%s threshold=%.4f",
            device_label,
            config.audio.sample_rate,
            config.audio.block_duration_ms,
            threshold,
        )

        with sd.InputStream(
            samplerate=config.audio.sample_rate,
            device=device,
            channels=1,
            dtype="float32",
            blocksize=block_size,
        ) as stream:
            start_deadline = time.monotonic() + listen_timeout
            recording_started = False
            utterance_start = 0.0
            last_voice_time = 0.0
            captured_blocks: list[np.ndarray] = []

            while True:
                data, overflowed = stream.read(block_size)
                if overflowed:
                    self.logger.debug("Microphone overflow detected during click-to-talk capture.")

                samples = np.asarray(data[:, 0], dtype=np.float32).copy()
                rms = self._calculate_rms(samples)
                now = time.monotonic()

                if not recording_started:
                    pre_roll.append(samples)
                    if self._frame_is_speech(rms, threshold, voice):
                        consecutive_voice_frames += 1
                    else:
                        consecutive_voice_frames = 0
                    if consecutive_voice_frames >= 2:
                        recording_started = True
                        utterance_start = now
                        last_voice_time = now
                        captured_blocks = [block.copy() for block in pre_roll]
                        self.logger.info("Manual voice recording started.")
                        self.stateChanged.emit("recording", "Recording voice command.")
                        continue
                    if now >= start_deadline:
                        raise RuntimeError(
                            "No speech was detected before the listen timeout expired. "
                            "Try speaking closer to the microphone or lower the speech threshold."
                        )
                    continue

                captured_blocks.append(samples)
                if self._frame_is_speech(rms, threshold * 0.74, voice):
                    last_voice_time = now

                if (
                    (now - utterance_start) >= max_utterance_seconds
                    or (
                        (now - utterance_start) >= min_record_seconds
                        and (now - last_voice_time) >= silence_seconds
                    )
                ):
                    break

        if not captured_blocks:
            raise RuntimeError("The microphone did not capture a usable voice command.")
        utterance = np.concatenate(captured_blocks)
        self.logger.info(
            "Manual voice recording stopped. duration=%.2fs peak=%.4f rms=%.4f",
            float(utterance.size) / float(max(1, config.audio.sample_rate)),
            float(np.max(np.abs(utterance))) if utterance.size else 0.0,
            self._calculate_rms(utterance),
        )
        return utterance

    def _transcribe_audio(self, config: JarvisConfig, samples: np.ndarray) -> str:
        whisper_model = self._get_whisper_model(config.voice)
        if whisper_model is None:
            raise RuntimeError(self.describe_stt_status(config.voice))

        duration = float(samples.size) / float(max(1, config.audio.sample_rate))
        self.logger.info("Starting transcription for %.2f seconds of audio.", duration)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
            temp_path = Path(handle.name)
        try:
            self._write_wav(temp_path, samples, config.audio.sample_rate)
            segments, _info = whisper_model.transcribe(
                str(temp_path),
                beam_size=1,
                language="en",
                vad_filter=bool(config.voice.vad_enabled),
                condition_on_previous_text=False,
            )
            transcript = " ".join(segment.text.strip() for segment in segments).strip()
            if transcript:
                self.logger.info("Transcription result: %s", transcript)
            else:
                self.logger.info("Transcription result was empty.")
            return transcript
        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except Exception:
                pass

    def _speak_text(self, text: str, voice: VoiceConfig) -> str:
        if not text.strip():
            return ""

        for backend in self._tts_backend_candidates(voice):
            try:
                if backend == "kokoro" and self._speak_with_kokoro(text, voice):
                    return "Kokoro"
                if backend == "piper" and self._speak_with_piper(text, voice):
                    return "Piper"
                if backend == "sapi" and self._speak_with_sapi(text, voice):
                    return "Windows Speech API"
            except Exception as exc:
                self.logger.warning("%s TTS failed: %s", backend, exc)
        return ""

    def _tts_backend_candidates(self, voice: VoiceConfig) -> list[str]:
        backend = (voice.tts_backend or "auto").strip().lower()
        if backend == "kokoro":
            return ["kokoro", "piper", "sapi"]
        if backend == "piper":
            return ["piper", "kokoro", "sapi"]
        if backend == "sapi":
            return ["sapi"]
        return ["kokoro", "piper", "sapi"]

    def _speak_with_kokoro(self, text: str, voice: VoiceConfig) -> bool:
        if Kokoro is None or not self._kokoro_assets_ready(voice):
            return False

        model_path = Path(expand_windows_path(voice.tts_model_path))
        voices_path = Path(expand_windows_path(voice.tts_voices_path))
        if self._kokoro_engine is None:
            self._kokoro_engine = Kokoro(str(model_path), str(voices_path))

        audio, sample_rate = self._kokoro_engine.create(
            text,
            voice=voice.tts_voice,
            speed=voice.tts_rate,
        )
        self._play_samples(np.asarray(audio, dtype=np.float32), int(sample_rate), voice)
        return True

    def _speak_with_piper(self, text: str, voice: VoiceConfig) -> bool:
        if not self._piper_assets_ready(voice):
            return False

        piper_exe = expand_windows_path(voice.piper_exe_path)
        piper_model = expand_windows_path(voice.piper_model_path)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
            wav_path = Path(handle.name)
        try:
            command = [piper_exe, "-m", piper_model, "-f", str(wav_path)]
            subprocess.run(
                command,
                input=text.encode("utf-8"),
                check=True,
                capture_output=True,
            )
            samples, sample_rate = self._read_wav(wav_path)
            self._play_samples(samples, sample_rate, voice)
            return True
        finally:
            try:
                wav_path.unlink(missing_ok=True)
            except Exception:
                pass

    def _speak_with_sapi(self, text: str, voice: VoiceConfig) -> bool:
        if win32_client is None:
            return False
        speaker = win32_client.Dispatch("SAPI.SpVoice")
        speaker.Rate = max(-10, min(10, int(round((voice.tts_rate - 1.0) * 6))))
        speaker.Volume = max(0, min(100, int(round(voice.tts_volume * 100))))
        speaker.Speak(text)
        return True

    def _play_samples(self, samples: np.ndarray, sample_rate: int, voice: VoiceConfig) -> None:
        playback = np.asarray(samples, dtype=np.float32)
        playback = np.clip(playback * max(0.0, voice.tts_volume), -1.0, 1.0)
        output_device = self._resolve_output_device(voice)
        sd.play(playback, samplerate=sample_rate, device=output_device)
        sd.wait()

    def _resolve_output_device(self, voice: VoiceConfig) -> int | None:
        if voice.output_device_index not in (None, -1):
            return int(voice.output_device_index)
        if voice.output_device_name.strip():
            target = voice.output_device_name.strip().casefold()
            for index, device in enumerate(sd.query_devices()):
                if int(device.get("max_output_channels", 0)) <= 0:
                    continue
                if target in str(device.get("name", "")).casefold():
                    return index
        return None

    def _get_whisper_model(self, voice: VoiceConfig):
        if WhisperModel is None:
            return None
        if self._whisper_model is not None:
            return self._whisper_model

        device, compute_type = self._resolve_whisper_runtime(voice)
        model_candidates = [voice.stt_model.strip(), voice.stt_fallback_model.strip()]
        for model_name in [item for item in model_candidates if item]:
            try:
                self.logger.info(
                    "Loading faster-whisper model '%s' on %s (%s).",
                    model_name,
                    device,
                    compute_type,
                )
                self._whisper_model = WhisperModel(
                    model_name,
                    device=device,
                    compute_type=compute_type,
                )
                return self._whisper_model
            except Exception as exc:
                self.logger.warning("Unable to load STT model '%s': %s", model_name, exc)
        return None

    def _get_wake_model(self, voice: VoiceConfig):
        if OpenWakeWordModel is None:
            return None
        if self._wake_model is not None:
            return self._wake_model

        model_path = expand_windows_path(voice.wake_word_model_path)
        if not model_path or not Path(model_path).exists():
            return None
        try:
            self._wake_model = OpenWakeWordModel(wakeword_models=[model_path])
            self.logger.info("Loaded openWakeWord model from %s.", model_path)
            return self._wake_model
        except Exception as exc:
            self.logger.warning("Unable to load openWakeWord model: %s", exc)
            return None

    def _predict_wake_score(self, wake_model, samples: np.ndarray) -> float:
        clipped = np.clip(samples, -1.0, 1.0)
        pcm = (clipped * 32767.0).astype(np.int16)
        prediction = wake_model.predict(pcm)
        if isinstance(prediction, dict):
            values = [float(value) for value in prediction.values()]
            return max(values) if values else 0.0
        return float(prediction or 0.0)

    def _resolve_whisper_runtime(self, voice: VoiceConfig) -> tuple[str, str]:
        requested_device = (voice.stt_device or "auto").strip().lower()
        requested_compute = (voice.stt_compute_type or "auto").strip().lower()

        has_gpu = shutil.which("nvidia-smi") is not None or bool(os.getenv("CUDA_PATH"))
        if requested_device == "auto":
            device = "cuda" if has_gpu else "cpu"
        else:
            device = requested_device

        if requested_compute == "auto":
            compute_type = "int8_float16" if device == "cuda" else "int8"
        else:
            compute_type = requested_compute
        return device, compute_type

    def _kokoro_assets_ready(self, voice: VoiceConfig) -> bool:
        if Kokoro is None:
            return False
        model_path = Path(expand_windows_path(voice.tts_model_path))
        voices_path = Path(expand_windows_path(voice.tts_voices_path))
        return model_path.exists() and voices_path.exists()

    def _piper_assets_ready(self, voice: VoiceConfig) -> bool:
        piper_exe = expand_windows_path(voice.piper_exe_path)
        piper_model = expand_windows_path(voice.piper_model_path)
        return bool(piper_exe and piper_model) and Path(piper_exe).exists() and Path(piper_model).exists()

    def _contains_phrase(self, text: str, phrases: list[str]) -> bool:
        return any(phrase.strip().casefold() in text for phrase in phrases if phrase.strip())

    def _matching_prefix(self, text: str, phrases: list[str]) -> str:
        normalized = text.strip()
        for phrase in phrases:
            candidate = phrase.strip().casefold()
            if candidate and normalized.startswith(candidate):
                return phrase.strip()
        return ""

    def _write_wav(self, path: Path, samples: np.ndarray, sample_rate: int) -> None:
        pcm = (np.clip(samples, -1.0, 1.0) * 32767.0).astype("<i2")
        with wave.open(str(path), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(sample_rate)
            handle.writeframes(pcm.tobytes())

    def _read_wav(self, path: Path) -> tuple[np.ndarray, int]:
        with wave.open(str(path), "rb") as handle:
            sample_rate = handle.getframerate()
            frame_count = handle.getnframes()
            channels = handle.getnchannels()
            raw = handle.readframes(frame_count)
        pcm = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32767.0
        if channels > 1:
            pcm = pcm.reshape(-1, channels).mean(axis=1)
        return pcm, int(sample_rate)

    def _describe_input_device(self, device_index: int | None) -> str:
        if device_index in (None, -1):
            return "Default system input"
        try:
            device = sd.query_devices(device_index)
        except Exception:
            return f"Input device {device_index}"
        return str(device.get("name", f"Input device {device_index}"))

    def _effective_voice_threshold(self, voice: VoiceConfig) -> float:
        sensitivity = min(0.95, max(0.05, float(voice.vad_sensitivity)))
        return max(0.0035, float(voice.speech_threshold) * (1.35 - sensitivity))

    def _frame_is_speech(self, rms: float, threshold: float, voice: VoiceConfig) -> bool:
        if not voice.vad_enabled:
            return rms >= max(0.0025, threshold * 0.75)
        return rms >= threshold

    def _detect_audio_presence(
        self,
        voice: VoiceConfig,
        peak: float,
        rms: float,
        average_abs: float,
    ) -> bool:
        peak_threshold = max(0.008, float(voice.speech_threshold) * 0.55)
        rms_threshold = max(0.002, float(voice.speech_threshold) * 0.16)
        average_threshold = max(0.0015, float(voice.speech_threshold) * 0.13)
        return (
            peak >= peak_threshold
            or rms >= rms_threshold
            or average_abs >= average_threshold
        )

    def _save_debug_wav(self, samples: np.ndarray, sample_rate: int, prefix: str) -> str:
        debug_dir = Path(expand_windows_path("%APPDATA%\\JarvisAssistant\\audio_debug"))
        debug_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{prefix}_{int(time.time())}.wav"
        output_path = debug_dir / filename
        self._write_wav(output_path, samples, sample_rate)
        self.logger.info("Saved debug audio to %s", output_path)
        return str(output_path)

    def _drain_audio_queue(self) -> None:
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    def _calculate_rms(self, samples: np.ndarray) -> float:
        if samples.size == 0:
            return 0.0
        return float(np.sqrt(float(np.mean(np.square(samples)))))
