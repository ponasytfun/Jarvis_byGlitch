from __future__ import annotations

import json
import os
import platform
import shutil
import sys
from datetime import datetime
from typing import Any

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication

from jarvis_assistant.actions import ActionExecutor
from jarvis_assistant.ai_manager import LocalAIManager
from jarvis_assistant.assistant_actions import AssistantActionOutcome, AssistantActionRegistry
from jarvis_assistant.assistant_engine import AssistantEngine, AssistantTurnResult
from jarvis_assistant.audio_listener import AudioListener
from jarvis_assistant.brave_music import BraveMusicController
from jarvis_assistant.config_manager import ConfigManager
from jarvis_assistant.logger_setup import LogEmitter, setup_logging
from jarvis_assistant.models import (
    AIBackendStatus,
    AudioCalibration,
    AudioLevel,
    AudioProbeResult,
    JarvisConfig,
    SpeechCaptureResult,
    WorkflowResult,
)
from jarvis_assistant.paths import build_app_paths, open_in_explorer
from jarvis_assistant.process_utils import path_exists
from jarvis_assistant.resource_utils import ensure_qml_exists, qml_main_url
from jarvis_assistant.theme_manager import (
    choose_font_family,
    normalize_atom_theme,
    normalize_theme,
)
from jarvis_assistant.trigger_engine import TriggerEngine
from jarvis_assistant.ui_bridge import UiBridge
from jarvis_assistant.voice_agent import LocalVoiceAgent
from jarvis_assistant.window_manager import WindowManager
from jarvis_assistant.workflow_engine import WorkflowEngine
from jarvis_assistant.workers import WorkerManager


class JarvisAssistantController(QObject):
    workflowStepReported = Signal(str, str)

    def __init__(self, qml_engine: QQmlApplicationEngine) -> None:
        super().__init__()
        self.paths = build_app_paths()
        ensure_qml_exists(self.paths)

        self.config_manager = ConfigManager(self.paths)
        self.current_config = self.config_manager.load_or_create()

        self.log_emitter = LogEmitter()
        self.logger = setup_logging(self.paths.logs_dir, self.current_config.logging, self.log_emitter)

        serif_font = choose_font_family(
            ["Roboto Serif", "Georgia", "Cambria"],
            "Georgia",
        )
        ui_font = choose_font_family(
            ["Inter", "Segoe UI", "Arial"],
            "Segoe UI",
        )
        self.bridge = UiBridge(serif_font, ui_font)
        self.bridge.attach_controller(self)
        self.log_emitter.messageEmitted.connect(self.bridge.handleLogMessage)
        self.workflowStepReported.connect(self.bridge.setWorkflowStep)

        self.worker_manager = WorkerManager()
        self.window_manager = WindowManager(self.logger)
        self.audio_listener = AudioListener(self.logger)
        self.brave_music = BraveMusicController(self.window_manager, self.logger)
        self.ai_manager = LocalAIManager(self.logger)
        self.action_executor = ActionExecutor(
            window_manager=self.window_manager,
            brave_music=self.brave_music,
            logger=self.logger,
            notifier=self.bridge.notify,
        )
        self.workflow_engine = WorkflowEngine(self.action_executor, self.logger)
        self.action_registry = AssistantActionRegistry(
            self.action_executor,
            self.workflow_engine,
            self.logger,
            ai_status_provider=self._get_ai_status,
            voice_status_provider=lambda: self._voice_status_text,
            mic_status_provider=lambda: self._mic_status_text,
            tts_status_provider=lambda: self._tts_status_text,
            theme_provider=self._current_themes,
            obs_clip_handler=self._handle_obs_clip_action,
        )
        self.assistant_engine = AssistantEngine(
            self.ai_manager,
            self.action_registry,
            self.logger,
        )
        self.voice_agent = LocalVoiceAgent(self.ai_manager, self.assistant_engine, self.logger)
        self.trigger_engine = TriggerEngine(
            self.audio_listener,
            self.workflow_engine,
            self.worker_manager,
            self.logger,
        )
        self.voice_agent.stateChanged.connect(self._handle_voice_state_change)
        self.voice_agent.transcriptCaptured.connect(self._handle_voice_transcript)
        self.voice_agent.responsePrepared.connect(self._handle_voice_response)
        self.voice_agent.warningRaised.connect(self._handle_voice_warning)
        self.voice_agent.deactivateRequested.connect(self._handle_voice_deactivate_requested)

        self._voice_presence_state = "idle"
        self._voice_base_status_text = "Voice layer disabled."
        self._voice_status_text = self._voice_base_status_text
        self._mic_status_text = "Microphone idle."
        self._tts_status_text = "No local TTS backend checked yet."
        self._ai_generating = False
        self._last_heard_text = ""
        self._last_response_text = ""
        self._chat_messages: list[dict[str, Any]] = []
        self._diagnostics_text = ""
        self._ai_status = AIBackendStatus(
            connected=False,
            provider="none",
            provider_display_name="Scanning",
            base_url="",
            model_name="",
            available_models=[],
            status_text="Scanning local AI providers...",
            error_text="",
        )

        self.audio_devices = self._list_audio_devices()
        self.audio_output_devices = self._list_output_devices()
        self._load_chat_history()
        self._push_config_to_ui(self.current_config)
        self.bridge.update_ai_status(self._ai_status)
        self.bridge.update_ai_generating(False)
        self.bridge.update_status("Idle", False, False)
        self.bridge.update_assistant_state("idle", self._voice_status_for_config(self.current_config))
        self.bridge.update_workflow_step(
            "Awaiting Command",
            "The command core is idle and ready for the next workflow.",
        )
        self._append_system_message("Jarvis command core online.", persist=False)
        self.bridge.update_view("home")

        qml_engine.rootContext().setContextProperty("bridge", self.bridge)
        qml_engine.load(qml_main_url(self.paths))
        if not qml_engine.rootObjects():
            raise RuntimeError("Main QML window failed to load.")

        self.refresh_local_models()
        QApplication.instance().aboutToQuit.connect(self.shutdown)

    def start_listening(self, config_map: dict[str, Any]) -> None:
        config = self._config_from_map(config_map)
        self.current_config = config
        self.bridge.update_theme(config.ui.theme, config.ui.atom_theme)
        self.bridge.update_view("listening")
        self.bridge.update_workflow_step(
            "Listening Field Active",
            f"Armed for workflow '{config.runtime.default_workflow}'.",
        )
        if config.voice.enabled and config.voice.auto_start_with_listening:
            self.voice_agent.start(config)
        else:
            self._refresh_runtime_indicators(config)
            self._sync_assistant_state()
        self.trigger_engine.start_listening(
            config=config,
            on_level=self._handle_audio_level,
            on_state_change=self._handle_state_change,
            on_workflow_complete=self._handle_workflow_complete,
            on_workflow_step=self._report_workflow_step,
            on_audio_block=self.voice_agent.push_audio_block if config.voice.enabled else None,
        )

    def stop_listening(self) -> None:
        self.voice_agent.stop()
        self.trigger_engine.stop_listening()
        self.bridge.update_view("home")
        self.bridge.update_workflow_step(
            "Awaiting Command",
            "Listening has stopped. The command core is back at rest.",
        )
        self._refresh_runtime_indicators(self.current_config)
        self._sync_assistant_state()

    def test_workflow(self, config_map: dict[str, Any]) -> None:
        config = self._config_from_map(config_map)
        self.current_config = config
        self.bridge.update_theme(config.ui.theme, config.ui.atom_theme)
        self.bridge.update_view("executing")
        self.bridge.update_workflow_step(
            "Workflow Test",
            f"Manually running '{config.runtime.default_workflow}'.",
        )
        self.trigger_engine.run_manual_workflow(
            config=config,
            on_state_change=self._handle_state_change,
            on_workflow_complete=self._handle_workflow_complete,
            on_workflow_step=self._report_workflow_step,
        )

    def save_config(self, config_map: dict[str, Any]) -> None:
        config = self._config_from_map(config_map)
        self.current_config = config
        self.current_config.logging.level = self.current_config.debug.log_level
        self.current_config.voice.log_transcripts = self.current_config.debug.save_transcripts
        self.config_manager.save(self.current_config)
        self.logger.info("Config saved to %s", self.paths.config_path)
        self._push_config_to_ui(self.current_config)
        self._save_chat_history()
        self.refresh_local_models()
        self.bridge.notify("JarvisAssistant", "Configuration saved.")

    def reload_config(self) -> None:
        self.current_config = self.config_manager.load_or_create()
        self.audio_devices = self._list_audio_devices()
        self.audio_output_devices = self._list_output_devices()
        self.logger.info("Config reloaded from %s", self.paths.config_path)
        self._load_chat_history()
        self._push_config_to_ui(self.current_config)
        self.refresh_local_models()

    def set_surface_theme(self, theme_name: str) -> None:
        self._apply_surface_theme(theme_name, persist=False)

    def set_atom_theme(self, theme_name: str) -> None:
        self._apply_atom_theme(theme_name, persist=False)

    def calibrate_microphone(self, config_map: dict[str, Any]) -> None:
        if self.trigger_engine.listening:
            self.bridge.notify("JarvisAssistant", "Stop listening before manual calibration.")
            return
        config = self._config_from_map(config_map)
        self.current_config = config
        self._handle_state_change("Calibrating", False, False)
        self.worker_manager.submit(
            "microphone_calibration",
            self.audio_listener.calibrate,
            config.audio,
            config.trigger,
            on_success=self._handle_calibration_success,
            on_error=self._handle_calibration_error,
        )

    def open_config_folder(self) -> None:
        open_in_explorer(self.paths.appdata_dir)

    def open_logs_folder(self) -> None:
        open_in_explorer(self.paths.logs_dir)

    def refresh_local_models(self, config_map: dict[str, Any] | None = None) -> None:
        if config_map is not None:
            self.current_config = self._config_from_map(config_map)
        self.bridge.update_workflow_step(
            "AI Provider Scan",
            "Checking LM Studio first, then local fallbacks.",
        )
        self.worker_manager.submit(
            "ai_provider_scan",
            self.ai_manager.probe,
            self.current_config.ai,
            on_success=self._handle_ai_status_success,
            on_error=self._handle_ai_status_error,
        )

    def test_microphone(self, config_map: dict[str, Any]) -> None:
        config = self._config_from_map(config_map)
        self.current_config = config
        self.bridge.update_workflow_step(
            "Microphone Test",
            "Sampling the selected microphone for signal strength.",
        )
        self.worker_manager.submit(
            "microphone_test",
            self.voice_agent.test_microphone,
            config,
            on_success=self._handle_microphone_test_success,
            on_error=self._handle_microphone_test_error,
        )

    def test_tts(self, config_map: dict[str, Any]) -> None:
        config = self._config_from_map(config_map)
        self.current_config = config
        self.bridge.update_workflow_step(
            "TTS Test",
            "Sending a local spoken phrase through the configured TTS stack.",
        )
        self.worker_manager.submit(
            "tts_test",
            self.voice_agent.test_tts,
            config,
            on_success=self._handle_tts_test_success,
            on_error=self._handle_tts_test_error,
        )

    def test_stt(self, config_map: dict[str, Any]) -> None:
        config = self._config_from_map(config_map)
        self.current_config = config
        self.bridge.update_workflow_step(
            "STT Test",
            "Recording and transcribing a short speech sample.",
        )
        self.worker_manager.submit(
            "stt_test",
            self.voice_agent.test_stt,
            config,
            on_success=self._handle_stt_test_success,
            on_error=self._handle_stt_test_error,
        )

    def test_ai(self, config_map: dict[str, Any]) -> None:
        config = self._config_from_map(config_map)
        self.current_config = config
        self._set_ai_generating(True)
        self.bridge.update_workflow_step(
            "AI Test",
            "Sending a local smoke-test prompt to the active AI provider.",
        )
        self.worker_manager.submit(
            "ai_test",
            self._run_ai_smoke_test,
            config,
            on_success=self._handle_ai_test_success,
            on_error=self._handle_ai_test_error,
        )

    def refresh_audio_devices(self) -> None:
        self.audio_devices = self._list_audio_devices()
        self.audio_output_devices = self._list_output_devices()
        self.bridge.update_audio_devices(self.audio_devices)
        self.bridge.update_audio_output_devices(self.audio_output_devices)
        self._refresh_runtime_indicators(self.current_config)
        self._update_diagnostics()
        self._sync_assistant_state()
        self.bridge.notify("JarvisAssistant", "Audio device lists refreshed.")

    def clear_chat(self) -> None:
        self._chat_messages = []
        self.bridge.update_chat_messages(self._chat_messages)
        if self.paths.chat_history_path.exists():
            try:
                self.paths.chat_history_path.unlink()
            except Exception:
                pass
        self._update_diagnostics()
        self.bridge.notify("JarvisAssistant", "Chat history cleared for this session.")

    def export_chat(self) -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_path = self.paths.appdata_dir / f"chat_export_{timestamp}.txt"
        lines: list[str] = []
        for item in self._chat_messages:
            role = str(item.get("role", "system")).upper()
            stamp = str(item.get("timestamp", ""))
            text = str(item.get("text", "")).strip()
            if not text:
                continue
            lines.append(f"[{stamp}] {role}: {text}")
        payload = "\n\n".join(lines) if lines else "No chat messages were available to export."
        try:
            export_path.write_text(payload, encoding="utf-8")
        except Exception as exc:
            self.logger.error("Unable to export chat transcript: %s", exc)
            self.bridge.notify("Chat Export Failed", str(exc))
            return
        self.logger.info("Exported chat transcript to %s", export_path)
        self.bridge.notify("Chat Exported", f"Saved chat transcript to:\n{export_path}")

    def copy_diagnostics(self) -> None:
        diagnostics = self._build_diagnostics_text()
        QApplication.clipboard().setText(diagnostics)
        self.bridge.notify("Diagnostics", "Runtime diagnostics copied to the clipboard.")

    def start_voice_capture(self, config_map: dict[str, Any]) -> None:
        if self.trigger_engine.listening:
            self.bridge.notify(
                "JarvisAssistant",
                "Stop clap listening first, or use the armed voice layer while listening is active.",
            )
            return
        config = self._config_from_map(config_map)
        self.current_config = config
        if not config.voice.enabled:
            self.bridge.notify(
                "JarvisAssistant",
                "Enable the voice layer in Settings before using click-to-talk.",
            )
            return
        if not config.voice.click_to_talk_enabled:
            self.bridge.notify(
                "JarvisAssistant",
                "Click-to-talk is disabled in Settings.",
            )
            return
        self.bridge.update_view("listening")
        self.bridge.update_workflow_step(
            "Click-to-Talk",
            "Listening for a one-shot spoken command.",
        )
        self.worker_manager.submit(
            "voice_capture",
            self.voice_agent.capture_once_and_respond,
            config,
            on_success=self._handle_voice_capture_complete,
            on_error=self._handle_voice_capture_error,
        )

    def show_view(self, view_name: str) -> None:
        requested = (view_name or "home").strip().lower()
        if requested not in {"home", "listening", "executing", "settings", "logs"}:
            requested = "home"
        self.bridge.update_view(requested)

    def submit_prompt(self, prompt_text: str, config_map: dict[str, Any]) -> None:
        prompt = (prompt_text or "").strip()
        if not prompt:
            self.bridge.notify("JarvisAssistant", "Type a prompt before sending it to Jarvis.")
            return
        config = self._config_from_map(config_map)
        self.current_config = config
        self.bridge.update_theme(config.ui.theme, config.ui.atom_theme)
        self.bridge.update_view("executing")
        self._set_ai_generating(True)
        self.bridge.update_workflow_step(
            "Text Command",
            "Sending your prompt to the local model stack.",
        )
        self.worker_manager.submit(
            "text_prompt",
            self.voice_agent.submit_text_prompt,
            config,
            prompt,
            on_success=self._handle_text_prompt_complete,
            on_error=self._handle_text_prompt_error,
        )

    def shutdown(self) -> None:
        try:
            self.voice_agent.stop()
        except Exception:
            pass
        try:
            self.trigger_engine.stop_listening()
        except Exception:
            pass
        self.worker_manager.shutdown()

    def _handle_audio_level(self, level: AudioLevel) -> None:
        self.bridge.update_signal(level.normalized, level.peak, level.rms)

    def _handle_state_change(self, text: str, listening: bool, workflow_running: bool) -> None:
        self.bridge.update_status(text, listening, workflow_running)
        self._refresh_runtime_indicators(self.current_config)
        self._sync_assistant_state()
        if workflow_running:
            self.bridge.update_view("executing")
        elif listening:
            self.bridge.update_view("listening")
        elif self.bridge.currentView in {"listening", "executing"}:
            self.bridge.update_view("home")

    def _handle_workflow_complete(self, result: WorkflowResult) -> None:
        if result.success:
            self.bridge.notify("Workflow Complete", result.message)
        else:
            self.bridge.notify("Workflow Issue", result.message)
        self._sync_assistant_state()
        if self.trigger_engine.listening:
            self.bridge.update_view("listening")
            self.bridge.update_workflow_step(
                "Listening Field Active",
                f"Workflow finished. '{self.current_config.runtime.default_workflow}' remains armed.",
            )
        else:
            self.bridge.update_view("home")
            self.bridge.update_workflow_step(
                "Awaiting Command",
                "The workflow finished and the system returned to idle.",
            )

    def _handle_calibration_success(self, calibration: AudioCalibration) -> None:
        self.logger.info(
            "Manual calibration complete. noise_floor=%.4f threshold=%.4f",
            calibration.noise_floor,
            calibration.effective_threshold,
        )
        self.bridge.notify(
            "Calibration Complete",
            (
                f"Noise floor: {calibration.noise_floor:.4f}\n"
                f"Effective threshold: {calibration.effective_threshold:.4f}"
            ),
        )
        self.bridge.update_status("Idle", self.trigger_engine.listening, self.trigger_engine.workflow_running)
        self.bridge.update_workflow_step(
            "Calibration Complete",
            "Microphone calibration finished successfully.",
        )
        self._refresh_runtime_indicators(self.current_config)
        self._sync_assistant_state()

    def _handle_calibration_error(self, message: str) -> None:
        self.logger.error("Manual calibration failed: %s", message)
        self.bridge.notify("Calibration Failed", message)
        self.bridge.update_status("Idle", self.trigger_engine.listening, self.trigger_engine.workflow_running)
        self.bridge.update_workflow_step(
            "Calibration Failed",
            message,
        )
        self._refresh_runtime_indicators(self.current_config)
        self._sync_assistant_state()

    def _handle_ai_status_success(self, status: AIBackendStatus) -> None:
        self._ai_status = status
        self.logger.info("AI provider probe result: %s", status.status_text)
        self.bridge.update_ai_status(status)
        self._update_diagnostics()
        self._refresh_runtime_indicators(self.current_config)
        self._sync_assistant_state()
        if status.connected:
            self.bridge.update_workflow_step(
                "AI Ready",
                f"{status.provider_display_name} is ready with {status.model_name}.",
            )
        else:
            self.bridge.update_workflow_step(
                "AI Unavailable",
                status.status_text,
            )
            if status.error_text:
                self._append_system_message(f"AI unavailable: {status.error_text}")

    def _handle_ai_status_error(self, message: str) -> None:
        self.logger.error("AI provider probe failed: %s", message)
        self._ai_status = AIBackendStatus(
            connected=False,
            provider="none",
            provider_display_name="No Provider",
            base_url="",
            model_name="",
            available_models=[],
            status_text="Unable to scan local AI providers.",
            error_text=message,
        )
        self.bridge.update_ai_status(self._ai_status)
        self._update_diagnostics()
        self._refresh_runtime_indicators(self.current_config)
        self._sync_assistant_state()
        self.bridge.update_workflow_step("AI Probe Failed", message)
        self._append_system_message(f"AI probe failed: {message}")

    def _run_ai_smoke_test(self, config: JarvisConfig) -> str:
        prompt = "Reply with: Jarvis AI connection working."
        return self.ai_manager.chat(config.ai, prompt)

    def _handle_ai_test_success(self, response_text: str) -> None:
        self._set_ai_generating(False)
        self._ai_status = self.ai_manager.last_status
        self.bridge.update_ai_status(self._ai_status)
        self._update_diagnostics()
        self._last_response_text = response_text
        self._append_assistant_message(response_text)
        self._append_system_message("AI connection test passed.")
        self.bridge.update_workflow_step(
            "AI Test Passed",
            "The local AI provider returned a healthy response.",
        )
        self.bridge.notify("AI Test", response_text)
        self._sync_assistant_state()

    def _handle_ai_test_error(self, message: str) -> None:
        self._set_ai_generating(False)
        self._ai_status = self.ai_manager.last_status
        self.bridge.update_ai_status(self._ai_status)
        self._update_diagnostics()
        self.logger.error("AI test failed: %s", message)
        self.bridge.update_workflow_step(
            "AI Test Failed",
            message,
        )
        self.bridge.notify("AI Test Failed", message)
        self._voice_presence_state = "error"
        self._voice_status_text = message
        self._append_system_message(f"AI test failed: {message}")
        self._sync_assistant_state()

    def _handle_microphone_test_success(self, result: AudioProbeResult) -> None:
        if result.detected_audio:
            self._mic_status_text = (
                f"Microphone captured usable audio on {result.device_label} "
                f"(peak {result.peak:.3f}, RMS {result.rms:.3f})."
            )
        else:
            self._mic_status_text = (
                f"Microphone capture was extremely quiet on {result.device_label}. "
                "Choose a different device or raise the input level."
            )
        self.logger.info(self._mic_status_text)
        self._update_diagnostics()
        self.bridge.update_runtime_status(
            voice_status_text=self._voice_status_text,
            mic_status_text=self._mic_status_text,
            tts_status_text=self._tts_status_text,
        )
        self.bridge.notify(
            "Microphone Test" if result.detected_audio else "Microphone Test Warning",
            (
                f"Device: {result.device_label}\n"
                f"Peak: {result.peak:.3f}\n"
                f"RMS: {result.rms:.3f}\n"
                f"Average: {result.average_abs:.3f}\n"
                f"Detected audio: {'yes' if result.detected_audio else 'no'}\n"
                f"Rate: {result.sample_rate} Hz\n"
                f"Duration: {result.seconds:.1f}s"
                + (f"\nDebug WAV: {result.debug_wav_path}" if result.debug_wav_path else "")
            ),
        )
        if result.detected_audio:
            self._append_system_message(
                f"Microphone test passed on {result.device_label} with peak {result.peak:.3f} and RMS {result.rms:.3f}."
            )
        else:
            self._append_system_message(
                f"Microphone test warning: {result.device_label} captured almost no signal. Peak {result.peak:.3f}, RMS {result.rms:.3f}."
            )

    def _handle_microphone_test_error(self, message: str) -> None:
        self._mic_status_text = f"Microphone error: {message}"
        self.logger.error(self._mic_status_text)
        self._update_diagnostics()
        self.bridge.update_runtime_status(
            voice_status_text=self._voice_status_text,
            mic_status_text=self._mic_status_text,
            tts_status_text=self._tts_status_text,
        )
        self.bridge.notify("Microphone Test Failed", message)
        self._append_system_message(f"Microphone test failed: {message}")

    def _handle_tts_test_success(self, backend_name: str) -> None:
        self._tts_status_text = f"TTS ready through {backend_name}."
        self.logger.info(self._tts_status_text)
        self._update_diagnostics()
        self.bridge.update_runtime_status(
            voice_status_text=self._voice_status_text,
            mic_status_text=self._mic_status_text,
            tts_status_text=self._tts_status_text,
        )
        self.bridge.notify("TTS Test", f"Spoken test completed through {backend_name}.")
        self._append_system_message(f"TTS test succeeded through {backend_name}.")

    def _handle_tts_test_error(self, message: str) -> None:
        self._tts_status_text = f"TTS unavailable: {message}"
        self.logger.error(self._tts_status_text)
        self._update_diagnostics()
        self.bridge.update_runtime_status(
            voice_status_text=self._voice_status_text,
            mic_status_text=self._mic_status_text,
            tts_status_text=self._tts_status_text,
        )
        self.bridge.notify("TTS Test Failed", message)
        self._append_system_message(f"TTS test failed: {message}")

    def _handle_stt_test_success(self, result: SpeechCaptureResult) -> None:
        self._mic_status_text = f"Microphone ready on {result.device_label}."
        self._voice_status_text = "Speech-to-text test finished."
        self._update_diagnostics()
        self.bridge.update_runtime_status(
            voice_status_text=self._voice_status_text,
            mic_status_text=self._mic_status_text,
            tts_status_text=self._tts_status_text,
        )
        self.bridge.update_workflow_step(
            "STT Test Passed",
            f"Transcribed {result.seconds:.1f} seconds of speech.",
        )
        self.bridge.notify(
            "STT Test",
            result.transcript + (f"\n\nDebug WAV: {result.debug_wav_path}" if result.debug_wav_path else ""),
        )
        self._append_system_message(f"STT test transcript: {result.transcript}")
        self._sync_assistant_state()

    def _handle_stt_test_error(self, message: str) -> None:
        self.logger.error("STT test failed: %s", message)
        self._voice_presence_state = "error"
        self._voice_status_text = message
        self._mic_status_text = f"Microphone error: {message}"
        self._update_diagnostics()
        self.bridge.update_runtime_status(
            voice_status_text=self._voice_status_text,
            mic_status_text=self._mic_status_text,
            tts_status_text=self._tts_status_text,
        )
        self.bridge.notify("STT Test Failed", message)
        self._append_system_message(f"STT test failed: {message}")
        self._sync_assistant_state()

    def _handle_voice_capture_complete(self, turn_result: AssistantTurnResult) -> None:
        self._set_ai_generating(False)
        self._ai_status = self.ai_manager.last_status
        self.bridge.update_ai_status(self._ai_status)
        self._update_diagnostics()
        if not turn_result.success:
            self.bridge.notify("JarvisAssistant", turn_result.response_text)
            self._append_system_message(turn_result.response_text)
        if self._apply_turn_side_effects(turn_result):
            return
        self._voice_status_text = self._voice_base_status_text
        self.bridge.update_view("home")
        self._sync_assistant_state()

    def _handle_voice_capture_error(self, message: str) -> None:
        self.logger.error("Click-to-talk failed: %s", message)
        self._set_ai_generating(False)
        self._ai_status = self.ai_manager.last_status
        self.bridge.update_ai_status(self._ai_status)
        self._update_diagnostics()
        self._voice_presence_state = "error"
        self._voice_status_text = message
        self.bridge.notify("Voice Command Failed", message)
        self._append_system_message(f"Voice command failed: {message}")
        self.bridge.update_view("home")
        self._sync_assistant_state()

    def _push_config_to_ui(self, config: JarvisConfig) -> None:
        self.bridge.update_theme(config.ui.theme, config.ui.atom_theme)
        self.bridge.update_config(config.to_dict(), list(config.workflows.keys()))
        self.bridge.update_audio_devices(self.audio_devices)
        self.bridge.update_audio_output_devices(self.audio_output_devices)
        self.bridge.update_chat_messages(self._chat_messages)
        self._refresh_runtime_indicators(config)
        self._sync_assistant_state()

    def _list_audio_devices(self) -> list[dict[str, Any]]:
        try:
            raw_devices = AudioListener.list_input_devices()
        except Exception as exc:
            self.logger.warning("Unable to enumerate audio devices: %s", exc)
            return [{"index": -1, "name": "Default system input", "label": "Default system input"}]

        devices: list[dict[str, Any]] = []
        for device in raw_devices:
            if int(device.get("index", -1)) == -1:
                label = "Default system input"
            else:
                label = (
                    f"[{device['index']}] {device['name']} "
                    f"({device['max_input_channels']} in, {device['default_samplerate']} Hz)"
                )
            devices.append({**device, "label": label})
        return devices

    def _list_output_devices(self) -> list[dict[str, Any]]:
        try:
            raw_devices = AudioListener.list_output_devices()
        except Exception as exc:
            self.logger.warning("Unable to enumerate output devices: %s", exc)
            return [{"index": -1, "name": "Default system output", "label": "Default system output"}]

        devices: list[dict[str, Any]] = []
        for device in raw_devices:
            if int(device.get("index", -1)) == -1:
                label = "Default system output"
            else:
                label = (
                    f"[{device['index']}] {device['name']} "
                    f"({device['max_output_channels']} out, {device['default_samplerate']} Hz)"
                )
            devices.append({**device, "label": label})
        return devices

    def _config_from_map(self, config_map: dict[str, Any]) -> JarvisConfig:
        if not config_map:
            return self.current_config.clone()
        config = JarvisConfig.from_dict(config_map)
        config.ui.theme = normalize_theme(config.ui.theme)
        config.ui.atom_theme = normalize_atom_theme(config.ui.atom_theme)
        return config

    def _report_workflow_step(self, title: str, detail: str) -> None:
        self.workflowStepReported.emit(title, detail)

    def _handle_voice_state_change(self, state_name: str, detail: str) -> None:
        self._voice_presence_state = state_name
        self._voice_status_text = detail
        if state_name in {"thinking", "executing_action"}:
            self._set_ai_generating(True)
        elif state_name in {"idle", "listening", "speaking", "error", "recording", "transcribing"}:
            self._set_ai_generating(False)

        if state_name == "recording":
            self._mic_status_text = f"Microphone recording on {self._selected_input_device_label(self.current_config)}."
        elif state_name == "transcribing":
            self._mic_status_text = f"Transcribing audio from {self._selected_input_device_label(self.current_config)}."
        elif state_name == "listening":
            self._mic_status_text = f"Microphone listening on {self._selected_input_device_label(self.current_config)}."
        elif state_name == "error":
            self._mic_status_text = f"Microphone error on {self._selected_input_device_label(self.current_config)}."
        elif state_name == "idle" and not self.trigger_engine.listening:
            self._mic_status_text = f"Microphone idle on {self._selected_input_device_label(self.current_config)}."

        if not self.trigger_engine.workflow_running:
            if state_name == "thinking":
                self.bridge.update_workflow_step("Thinking", detail)
                self.bridge.update_view("executing")
            elif state_name == "executing_action":
                self.bridge.update_workflow_step("Executing Action", detail)
                self.bridge.update_view("executing")
            elif state_name == "recording":
                self.bridge.update_workflow_step("Recording", detail)
                self.bridge.update_view("listening")
            elif state_name == "transcribing":
                self.bridge.update_workflow_step("Transcribing", detail)
                self.bridge.update_view("executing")
            elif state_name == "speaking":
                self.bridge.update_workflow_step("Speaking", detail)
            elif state_name == "listening" and self.trigger_engine.listening:
                self.bridge.update_workflow_step("Voice Layer Armed", detail)
                self.bridge.update_view("listening")
            elif state_name == "error":
                self.bridge.update_workflow_step("Action Warning", detail)
            elif state_name == "idle":
                self._voice_status_text = self._voice_base_status_text
        self._sync_assistant_state()

    def _handle_voice_transcript(self, transcript: str, source: str) -> None:
        self._last_heard_text = transcript
        self._append_user_message(transcript, source)
        self.bridge.update_assistant_state(
            self._derive_assistant_state(),
            self._voice_status_text,
            self._last_heard_text,
            self._last_response_text,
        )

    def _handle_voice_response(self, response: str) -> None:
        self._last_response_text = response
        self._append_assistant_message(response)
        self.bridge.update_assistant_state(
            self._derive_assistant_state(),
            self._voice_status_text,
            self._last_heard_text,
            self._last_response_text,
        )

    def _handle_voice_warning(self, message: str) -> None:
        self.logger.warning("Voice layer warning: %s", message)
        self._voice_presence_state = "error"
        self._voice_status_text = message
        self.bridge.notify("Voice Layer", message)
        self._append_system_message(f"Voice warning: {message}")
        self._sync_assistant_state()

    def _handle_voice_deactivate_requested(self) -> None:
        self.logger.info("Voice layer requested deactivation.")
        self.stop_listening()

    def _handle_text_prompt_complete(self, turn_result: AssistantTurnResult) -> None:
        self._set_ai_generating(False)
        self._ai_status = self.ai_manager.last_status
        self.bridge.update_ai_status(self._ai_status)
        self._update_diagnostics()
        if not turn_result.success:
            self.bridge.notify("JarvisAssistant", turn_result.response_text)
            self._append_system_message(turn_result.response_text)
        if self._apply_turn_side_effects(turn_result):
            return
        if self.trigger_engine.listening:
            self.bridge.update_view("listening")
        else:
            self.bridge.update_view("home")
        self._voice_status_text = self._voice_base_status_text
        self._sync_assistant_state()

    def _handle_text_prompt_error(self, message: str) -> None:
        self.logger.error("Text prompt failed: %s", message)
        self._set_ai_generating(False)
        self._ai_status = self.ai_manager.last_status
        self.bridge.update_ai_status(self._ai_status)
        self._update_diagnostics()
        self._voice_presence_state = "error"
        self.bridge.notify("JarvisAssistant", message)
        self._append_system_message(f"Text prompt failed: {message}")
        if self.trigger_engine.listening:
            self.bridge.update_view("listening")
        else:
            self.bridge.update_view("home")
        self._voice_status_text = message
        self._sync_assistant_state()

    def _derive_assistant_state(self) -> str:
        if self.trigger_engine.workflow_running:
            return "executing"
        if self._voice_presence_state in {"thinking", "speaking", "error", "executing_action"}:
            return self._voice_presence_state
        if self._voice_presence_state == "transcribing":
            return "thinking"
        if self._voice_presence_state == "recording":
            return "listening"
        if self.trigger_engine.listening:
            return "listening"
        return "idle"

    def _sync_assistant_state(self) -> None:
        self.bridge.update_assistant_state(
            self._derive_assistant_state(),
            self._voice_status_text,
            self._last_heard_text,
            self._last_response_text,
        )
        self.bridge.update_runtime_status(
            voice_status_text=self._voice_status_text,
            mic_status_text=self._mic_status_text,
            tts_status_text=self._tts_status_text,
        )
        self._update_diagnostics()

    def _set_ai_generating(self, generating: bool) -> None:
        self._ai_generating = generating
        self.bridge.update_ai_generating(generating)

    def _append_user_message(self, text: str, source: str) -> None:
        self._append_chat_message("user", text, source=source or "text")

    def _append_assistant_message(self, text: str) -> None:
        self._append_chat_message("assistant", text, source="assistant")

    def _append_system_message(self, text: str, *, persist: bool = True) -> None:
        self._append_chat_message("system", text, source="system", persist=persist)

    def _append_chat_message(
        self,
        role: str,
        text: str,
        *,
        source: str,
        persist: bool = True,
    ) -> None:
        cleaned = (text or "").strip()
        if not cleaned:
            return
        entry = {
            "role": role,
            "text": cleaned,
            "source": source,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }
        if self._chat_messages and self._chat_messages[-1] == entry:
            return
        self._chat_messages.append(entry)
        self._chat_messages = self._chat_messages[-120:]
        self.bridge.update_chat_messages(self._chat_messages)
        if persist:
            self._save_chat_history()

    def _load_chat_history(self) -> None:
        self._chat_messages = []
        if not self.current_config.ui.chat_history_enabled:
            self.bridge.update_chat_messages(self._chat_messages)
            return
        try:
            if self.paths.chat_history_path.exists():
                with self.paths.chat_history_path.open("r", encoding="utf-8") as handle:
                    payload = json.load(handle)
                if isinstance(payload, list):
                    self._chat_messages = [
                        item
                        for item in payload[-120:]
                        if isinstance(item, dict) and str(item.get("text", "")).strip()
                    ]
        except Exception as exc:
            self.logger.warning("Unable to load chat history: %s", exc)
            self._chat_messages = []
        self.bridge.update_chat_messages(self._chat_messages)

    def _save_chat_history(self) -> None:
        if not self.current_config.ui.chat_history_enabled:
            return
        try:
            with self.paths.chat_history_path.open("w", encoding="utf-8") as handle:
                json.dump(self._chat_messages[-120:], handle, ensure_ascii=False, indent=2)
        except Exception as exc:
            self.logger.warning("Unable to save chat history: %s", exc)

    def _build_diagnostics_text(self) -> str:
        microphone_names = [str(device.get("label", device.get("name", ""))) for device in self.audio_devices]
        output_names = [
            str(device.get("label", device.get("name", "")))
            for device in self.audio_output_devices
        ]
        gpu_available = "yes" if (shutil.which("nvidia-smi") or bool(os.getenv("CUDA_PATH"))) else "no"
        return "\n".join(
            [
                f"OS: {platform.platform()}",
                f"Python: {sys.version.splitlines()[0]}",
                f"Project version: {self.current_config.app.version}",
                f"AI provider: {self._ai_status.provider_display_name}",
                f"AI base URL: {self._ai_status.base_url or '(none)'}",
                f"AI connected: {self._ai_status.connected}",
                f"Selected model: {self._ai_status.model_name or '(none)'}",
                f"AI last error: {self._ai_status.error_text or '(none)'}",
                f"AI generating: {self._ai_generating}",
                f"AI streaming enabled: {self.current_config.ai.stream_enabled}",
                f"Voice status: {self._voice_status_text}",
                f"Voice enabled: {self.current_config.voice.enabled}",
                f"Microphone status: {self._mic_status_text}",
                f"Selected microphone: {self._selected_input_device_label(self.current_config)}",
                f"Microphones found: {len(self.audio_devices)}",
                "Microphone list: " + ("; ".join(microphone_names) if microphone_names else "(none)"),
                f"Selected output device: {self.current_config.voice.output_device_name or '(default)'}",
                f"Output devices found: {len(self.audio_output_devices)}",
                "Output device list: " + ("; ".join(output_names) if output_names else "(none)"),
                f"STT status: {self.voice_agent.describe_stt_status(self.current_config.voice)}",
                f"TTS status: {self._tts_status_text}",
                f"GPU/CUDA detected: {gpu_available}",
                f"Theme: {self.current_config.ui.theme} / {self.current_config.ui.atom_theme}",
                f"Chat history enabled: {self.current_config.ui.chat_history_enabled}",
                f"Debug log level: {self.current_config.debug.log_level}",
                f"Save audio debug files: {self.current_config.debug.save_audio_debug_files}",
                f"Save transcripts: {self.current_config.debug.save_transcripts}",
            ]
        )

    def _update_diagnostics(self) -> None:
        self._diagnostics_text = self._build_diagnostics_text()
        self.bridge.update_diagnostics(self._diagnostics_text)

    def _voice_status_for_config(self, config: JarvisConfig) -> str:
        return self.voice_agent.describe_voice_status(config)

    def _refresh_runtime_indicators(self, config: JarvisConfig) -> None:
        config.voice.log_transcripts = config.debug.save_transcripts
        self._voice_base_status_text = self._voice_status_for_config(config)
        if self._voice_presence_state in {"idle", "listening"} and not self.trigger_engine.workflow_running:
            self._voice_status_text = self._voice_base_status_text

        if self.trigger_engine.listening:
            self._mic_status_text = f"Microphone listening on {self._selected_input_device_label(config)}."
        else:
            self._mic_status_text = f"Microphone idle on {self._selected_input_device_label(config)}."
        self._tts_status_text = self.voice_agent.describe_tts_status(config.voice)

    def _selected_input_device_label(self, config: JarvisConfig) -> str:
        target_index = config.audio.device_index
        for device in self.audio_devices:
            if device.get("index") == target_index:
                return str(device.get("label", device.get("name", "Default system input")))
        return "Default system input"

    def _get_ai_status(self) -> AIBackendStatus:
        return self._ai_status

    def _current_themes(self) -> tuple[str, str]:
        return self.current_config.ui.theme, self.current_config.ui.atom_theme

    def _apply_surface_theme(self, theme_name: str, persist: bool) -> str:
        theme = normalize_theme(theme_name)
        self.current_config.ui.theme = theme
        self.bridge.update_theme(theme, self.current_config.ui.atom_theme)
        self.bridge.update_config(
            self.current_config.to_dict(),
            list(self.current_config.workflows.keys()),
        )
        if persist:
            self.config_manager.save(self.current_config)
            self.logger.info("Surface theme persisted as %s.", theme)
        return theme

    def _apply_atom_theme(self, theme_name: str, persist: bool) -> str:
        atom_theme = normalize_atom_theme(theme_name)
        self.current_config.ui.atom_theme = atom_theme
        self.bridge.update_theme(self.current_config.ui.theme, atom_theme)
        self.bridge.update_config(
            self.current_config.to_dict(),
            list(self.current_config.workflows.keys()),
        )
        if persist:
            self.config_manager.save(self.current_config)
            self.logger.info("Atom theme persisted as %s.", atom_theme)
        return atom_theme

    def _apply_turn_side_effects(self, turn_result: AssistantTurnResult) -> bool:
        payload = dict(turn_result.payload or {})
        if payload.get("surface_theme"):
            self._apply_surface_theme(str(payload["surface_theme"]), persist=True)
        if payload.get("atom_theme"):
            self._apply_atom_theme(str(payload["atom_theme"]), persist=True)

        if payload.get("request_stop_listening"):
            self.stop_listening()
            return True
        return False

    def _stop_listening_action(self) -> str:
        if not self.trigger_engine.listening and not self.voice_agent.running:
            return "Jarvis was already idle."
        self.stop_listening()
        return "Listening has stopped."

    def _handle_obs_clip_action(
        self,
        config: JarvisConfig,
        dry_run: bool,
    ) -> AssistantActionOutcome:
        if dry_run:
            return AssistantActionOutcome(
                "obs_clip",
                True,
                "Dry run: I would ask OBS to save a replay clip.",
                "OBS clip execution was skipped in dry-run mode.",
            )

        if not path_exists(config.paths.obs_path):
            raise RuntimeError(
                "OBS Studio is not installed or the configured OBS path is invalid."
            )

        self.action_executor.execute(
            "focus_or_launch_app",
            {"target": "obs", "wait_timeout_seconds": max(6, config.matching.obs.launch_timeout_ms // 1000)},
            config,
            dry_run=False,
            timeout_ms=config.matching.obs.launch_timeout_ms,
        )

        try:
            import obsws_python  # noqa: F401
        except Exception as exc:
            raise RuntimeError(
                "OBS is available, but replay clipping needs obs-websocket support. "
                "Install or enable OBS WebSocket and Replay Buffer before using this action."
            ) from exc

        raise RuntimeError(
            "OBS opened successfully, but replay clipping is not configured yet. "
            "Enable the OBS WebSocket server and Replay Buffer, then I can finish this action safely."
        )


def run_app() -> None:
    QQuickStyle.setStyle("Basic")
    app = QApplication(sys.argv)
    app.setApplicationName("JarvisAssistant")
    app.setOrganizationName("JarvisAssistant")
    QGuiApplication.setDesktopSettingsAware(True)

    qml_engine = QQmlApplicationEngine()
    controller = JarvisAssistantController(qml_engine)
    _ = controller
    sys.exit(app.exec())
