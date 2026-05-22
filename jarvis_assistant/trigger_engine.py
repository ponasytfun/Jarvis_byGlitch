from __future__ import annotations

import threading
import time
from collections.abc import Callable

from jarvis_assistant.audio_listener import AudioListener
from jarvis_assistant.models import AudioLevel, JarvisConfig, WorkflowResult
from jarvis_assistant.workflow_engine import WorkflowEngine
from jarvis_assistant.workers import WorkerManager


class TriggerEngine:
    def __init__(
        self,
        audio_listener: AudioListener,
        workflow_engine: WorkflowEngine,
        worker_manager: WorkerManager,
        logger,
    ) -> None:
        self.audio_listener = audio_listener
        self.workflow_engine = workflow_engine
        self.worker_manager = worker_manager
        self.logger = logger.getChild("trigger_engine")
        self._lock = threading.Lock()
        self._config: JarvisConfig | None = None
        self._on_level: Callable[[AudioLevel], None] | None = None
        self._on_state_change: Callable[[str, bool, bool], None] | None = None
        self._workflow_complete_callback: Callable[[WorkflowResult], None] | None = None
        self._workflow_step_callback: Callable[[str, str], None] | None = None
        self._listening = False
        self._workflow_running = False
        self._cooldown_until = 0.0

    @property
    def listening(self) -> bool:
        return self._listening

    @property
    def workflow_running(self) -> bool:
        return self._workflow_running

    def start_listening(
        self,
        config: JarvisConfig,
        on_level: Callable[[AudioLevel], None],
        on_state_change: Callable[[str, bool, bool], None],
        on_workflow_complete: Callable[[WorkflowResult], None] | None = None,
        on_workflow_step: Callable[[str, str], None] | None = None,
        on_audio_block=None,
    ) -> None:
        with self._lock:
            if self._listening:
                self.logger.info("Start listening ignored because listener is already active.")
                return
            self._config = config.clone()
            self._on_level = on_level
            self._on_state_change = on_state_change
            self._workflow_complete_callback = on_workflow_complete
            self._workflow_step_callback = on_workflow_step
            self._listening = True

        self._emit_state("Listening")
        self.audio_listener.start(
            audio_config=config.audio,
            trigger_config=config.trigger,
            on_clap=self._handle_clap,
            on_level=self._handle_level,
            on_audio_block=on_audio_block,
            on_error=self._handle_audio_error,
        )

    def stop_listening(self) -> None:
        with self._lock:
            self._listening = False
        self.audio_listener.stop()
        self._emit_state("Idle")

    def run_manual_workflow(
        self,
        config: JarvisConfig,
        on_state_change: Callable[[str, bool, bool], None],
        on_workflow_complete: Callable[[WorkflowResult], None] | None = None,
        on_workflow_step: Callable[[str, str], None] | None = None,
    ) -> None:
        with self._lock:
            self._config = config.clone()
            self._on_state_change = on_state_change
            self._workflow_complete_callback = on_workflow_complete
            self._workflow_step_callback = on_workflow_step
        self._queue_workflow(source="manual")

    def _handle_clap(self, clap_event) -> None:
        config = self._config
        if config is None:
            return

        if self._workflow_running:
            self.logger.info("Clap trigger ignored because workflow is already running.")
            return
        if time.monotonic() < self._cooldown_until:
            remaining = self._cooldown_until - time.monotonic()
            self.logger.info("Clap trigger ignored during cooldown (%.1fs remaining).", remaining)
            return

        self.logger.info(
            "Accepted clap trigger. peak=%.4f threshold=%.4f",
            clap_event.peak,
            clap_event.effective_threshold,
        )
        self._queue_workflow(source="clap")

    def _handle_level(self, level: AudioLevel) -> None:
        if self._on_level is not None:
            self._on_level(level)

    def _handle_audio_error(self, message: str) -> None:
        with self._lock:
            self._listening = False
        self.logger.error(message)
        self._emit_state("Audio Error")

    def _queue_workflow(self, source: str) -> None:
        with self._lock:
            if self._workflow_running:
                return
            self._workflow_running = True

        config = self._config.clone() if self._config is not None else None
        if config is None:
            with self._lock:
                self._workflow_running = False
            return

        workflow_name = config.runtime.default_workflow
        self._emit_state(f"Executing {workflow_name}")
        self.worker_manager.submit(
            "workflow",
            self.workflow_engine.run_workflow,
            workflow_name,
            config,
            self._workflow_step_callback,
            on_success=lambda result, workflow_source=source: self._handle_workflow_result(
                workflow_source,
                result,
                config,
            ),
            on_error=lambda exc: self._handle_workflow_exception(source, config, exc),
        )

    def _handle_workflow_result(
        self,
        source: str,
        config: JarvisConfig,
        result: WorkflowResult,
    ) -> None:
        with self._lock:
            self._workflow_running = False
            if result.success and source == "clap":
                self._cooldown_until = time.monotonic() + config.trigger.cooldown_seconds

        if self._workflow_complete_callback is not None:
            self._workflow_complete_callback(result)

        if self._listening:
            self._emit_state("Listening")
        else:
            self._emit_state("Idle")

    def _handle_workflow_exception(
        self,
        source: str,
        config: JarvisConfig,
        exc: Exception,
    ) -> None:
        with self._lock:
            self._workflow_running = False
        self.logger.exception("Workflow runner crashed: %s", exc)
        if self._workflow_complete_callback is not None:
            self._workflow_complete_callback(
                WorkflowResult(success=False, message=f"Workflow crashed: {exc}")
            )
        if self._listening:
            self._emit_state("Listening")
        else:
            self._emit_state("Idle")

    def _emit_state(self, text: str) -> None:
        if self._on_state_change is not None:
            self._on_state_change(text, self._listening, self._workflow_running)
