from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, Property, Signal, Slot

from jarvis_assistant.models import AIBackendStatus
from jarvis_assistant.theme_manager import get_theme_palette


class UiBridge(QObject):
    themeNameChanged = Signal()
    atomThemeNameChanged = Signal()
    themePaletteChanged = Signal()
    serifFontFamilyChanged = Signal()
    uiFontFamilyChanged = Signal()
    statusTextChanged = Signal()
    listeningChanged = Signal()
    workflowRunningChanged = Signal()
    assistantStateChanged = Signal()
    voiceStatusTextChanged = Signal()
    micStatusTextChanged = Signal()
    ttsStatusTextChanged = Signal()
    lastHeardTextChanged = Signal()
    lastResponseTextChanged = Signal()
    signalLevelChanged = Signal()
    signalMetricsChanged = Signal()
    currentViewChanged = Signal()
    workflowStepTitleChanged = Signal()
    workflowStepDetailChanged = Signal()
    configDataChanged = Signal()
    audioDevicesChanged = Signal()
    audioOutputDevicesChanged = Signal()
    workflowNamesChanged = Signal()
    aiConnectedChanged = Signal()
    aiProviderNameChanged = Signal()
    aiBaseUrlChanged = Signal()
    aiModelNameChanged = Signal()
    aiStatusTextChanged = Signal()
    aiErrorTextChanged = Signal()
    aiGeneratingChanged = Signal()
    aiAvailableModelsChanged = Signal()
    chatMessagesChanged = Signal()
    diagnosticsTextChanged = Signal()

    logAppended = Signal(str)
    notificationRequested = Signal(str, str)

    def __init__(self, serif_font_family: str, ui_font_family: str) -> None:
        super().__init__()
        self._controller = None
        self._theme_name = "dark"
        self._atom_theme_name = "cold_blue"
        self._theme_palette = get_theme_palette(self._theme_name, self._atom_theme_name)
        self._serif_font_family = serif_font_family
        self._ui_font_family = ui_font_family
        self._status_text = "Idle"
        self._listening = False
        self._workflow_running = False
        self._assistant_state = "idle"
        self._voice_status_text = "Voice layer standing by."
        self._mic_status_text = "Microphone idle."
        self._tts_status_text = "No local TTS backend checked yet."
        self._last_heard_text = ""
        self._last_response_text = ""
        self._signal_level = 0.0
        self._signal_metrics = "Mic ready"
        self._current_view = "home"
        self._workflow_step_title = "Awaiting command"
        self._workflow_step_detail = "Listening for your next instruction."
        self._config_data: dict[str, Any] = {}
        self._audio_devices: list[dict[str, Any]] = []
        self._audio_output_devices: list[dict[str, Any]] = []
        self._workflow_names: list[str] = []
        self._ai_connected = False
        self._ai_provider_name = "No Provider"
        self._ai_base_url = ""
        self._ai_model_name = ""
        self._ai_status_text = "No local AI provider has been checked yet."
        self._ai_error_text = ""
        self._ai_generating = False
        self._ai_available_models: list[str] = []
        self._chat_messages: list[dict[str, Any]] = []
        self._diagnostics_text = ""

    def attach_controller(self, controller) -> None:
        self._controller = controller

    @Property(str, notify=themeNameChanged)
    def themeName(self) -> str:
        return self._theme_name

    @Property(str, notify=atomThemeNameChanged)
    def atomThemeName(self) -> str:
        return self._atom_theme_name

    @Property("QVariantMap", notify=themePaletteChanged)
    def themePalette(self) -> dict[str, str]:
        return self._theme_palette

    @Property(str, notify=serifFontFamilyChanged)
    def serifFontFamily(self) -> str:
        return self._serif_font_family

    @Property(str, notify=uiFontFamilyChanged)
    def uiFontFamily(self) -> str:
        return self._ui_font_family

    @Property(str, notify=statusTextChanged)
    def statusText(self) -> str:
        return self._status_text

    @Property(bool, notify=listeningChanged)
    def listening(self) -> bool:
        return self._listening

    @Property(bool, notify=workflowRunningChanged)
    def workflowRunning(self) -> bool:
        return self._workflow_running

    @Property(str, notify=assistantStateChanged)
    def assistantState(self) -> str:
        return self._assistant_state

    @Property(str, notify=voiceStatusTextChanged)
    def voiceStatusText(self) -> str:
        return self._voice_status_text

    @Property(str, notify=micStatusTextChanged)
    def micStatusText(self) -> str:
        return self._mic_status_text

    @Property(str, notify=ttsStatusTextChanged)
    def ttsStatusText(self) -> str:
        return self._tts_status_text

    @Property(str, notify=lastHeardTextChanged)
    def lastHeardText(self) -> str:
        return self._last_heard_text

    @Property(str, notify=lastResponseTextChanged)
    def lastResponseText(self) -> str:
        return self._last_response_text

    @Property(float, notify=signalLevelChanged)
    def signalLevel(self) -> float:
        return self._signal_level

    @Property(str, notify=signalMetricsChanged)
    def signalMetrics(self) -> str:
        return self._signal_metrics

    @Property(str, notify=currentViewChanged)
    def currentView(self) -> str:
        return self._current_view

    @Property(str, notify=workflowStepTitleChanged)
    def workflowStepTitle(self) -> str:
        return self._workflow_step_title

    @Property(str, notify=workflowStepDetailChanged)
    def workflowStepDetail(self) -> str:
        return self._workflow_step_detail

    @Property("QVariantMap", notify=configDataChanged)
    def configData(self) -> dict[str, Any]:
        return self._config_data

    @Property("QVariantList", notify=audioDevicesChanged)
    def audioDevices(self) -> list[dict[str, Any]]:
        return self._audio_devices

    @Property("QVariantList", notify=audioOutputDevicesChanged)
    def audioOutputDevices(self) -> list[dict[str, Any]]:
        return self._audio_output_devices

    @Property("QVariantList", notify=workflowNamesChanged)
    def workflowNames(self) -> list[str]:
        return self._workflow_names

    @Property(bool, notify=aiConnectedChanged)
    def aiConnected(self) -> bool:
        return self._ai_connected

    @Property(str, notify=aiProviderNameChanged)
    def aiProviderName(self) -> str:
        return self._ai_provider_name

    @Property(str, notify=aiBaseUrlChanged)
    def aiBaseUrl(self) -> str:
        return self._ai_base_url

    @Property(str, notify=aiModelNameChanged)
    def aiModelName(self) -> str:
        return self._ai_model_name

    @Property(str, notify=aiStatusTextChanged)
    def aiStatusText(self) -> str:
        return self._ai_status_text

    @Property(str, notify=aiErrorTextChanged)
    def aiErrorText(self) -> str:
        return self._ai_error_text

    @Property(bool, notify=aiGeneratingChanged)
    def aiGenerating(self) -> bool:
        return self._ai_generating

    @Property("QVariantList", notify=aiAvailableModelsChanged)
    def aiAvailableModels(self) -> list[str]:
        return self._ai_available_models

    @Property("QVariantList", notify=chatMessagesChanged)
    def chatMessages(self) -> list[dict[str, Any]]:
        return self._chat_messages

    @Property(str, notify=diagnosticsTextChanged)
    def diagnosticsText(self) -> str:
        return self._diagnostics_text

    def update_theme(self, theme_name: str, atom_theme_name: str) -> None:
        self._theme_name = theme_name
        self._atom_theme_name = atom_theme_name
        self._theme_palette = get_theme_palette(theme_name, atom_theme_name)
        self.themeNameChanged.emit()
        self.atomThemeNameChanged.emit()
        self.themePaletteChanged.emit()

    def update_status(self, text: str, listening: bool, workflow_running: bool) -> None:
        self._status_text = text
        self._listening = listening
        self._workflow_running = workflow_running
        self.statusTextChanged.emit()
        self.listeningChanged.emit()
        self.workflowRunningChanged.emit()

    def update_signal(self, normalized: float, peak: float, rms: float) -> None:
        self._signal_level = normalized
        self._signal_metrics = f"Peak {peak:.3f} | RMS {rms:.3f}"
        self.signalLevelChanged.emit()
        self.signalMetricsChanged.emit()

    def update_assistant_state(
        self,
        assistant_state: str,
        voice_status_text: str | None = None,
        last_heard_text: str | None = None,
        last_response_text: str | None = None,
    ) -> None:
        if assistant_state != self._assistant_state:
            self._assistant_state = assistant_state
            self.assistantStateChanged.emit()
        if voice_status_text is not None and voice_status_text != self._voice_status_text:
            self._voice_status_text = voice_status_text
            self.voiceStatusTextChanged.emit()
        if last_heard_text is not None and last_heard_text != self._last_heard_text:
            self._last_heard_text = last_heard_text
            self.lastHeardTextChanged.emit()
        if last_response_text is not None and last_response_text != self._last_response_text:
            self._last_response_text = last_response_text
            self.lastResponseTextChanged.emit()

    def update_runtime_status(
        self,
        voice_status_text: str | None = None,
        mic_status_text: str | None = None,
        tts_status_text: str | None = None,
    ) -> None:
        if voice_status_text is not None and voice_status_text != self._voice_status_text:
            self._voice_status_text = voice_status_text
            self.voiceStatusTextChanged.emit()
        if mic_status_text is not None and mic_status_text != self._mic_status_text:
            self._mic_status_text = mic_status_text
            self.micStatusTextChanged.emit()
        if tts_status_text is not None and tts_status_text != self._tts_status_text:
            self._tts_status_text = tts_status_text
            self.ttsStatusTextChanged.emit()

    def update_view(self, view_name: str) -> None:
        if view_name == self._current_view:
            return
        self._current_view = view_name
        self.currentViewChanged.emit()

    def update_workflow_step(self, title: str, detail: str) -> None:
        self._workflow_step_title = title
        self._workflow_step_detail = detail
        self.workflowStepTitleChanged.emit()
        self.workflowStepDetailChanged.emit()

    def update_config(self, config_data: dict[str, Any], workflow_names: list[str]) -> None:
        self._config_data = config_data
        self._workflow_names = workflow_names
        self.configDataChanged.emit()
        self.workflowNamesChanged.emit()

    def update_audio_devices(self, devices: list[dict[str, Any]]) -> None:
        self._audio_devices = devices
        self.audioDevicesChanged.emit()

    def update_audio_output_devices(self, devices: list[dict[str, Any]]) -> None:
        self._audio_output_devices = devices
        self.audioOutputDevicesChanged.emit()

    def update_ai_status(self, status: AIBackendStatus) -> None:
        self._ai_connected = status.connected
        self._ai_provider_name = status.provider_display_name
        self._ai_base_url = status.base_url
        self._ai_model_name = status.model_name
        self._ai_status_text = status.status_text
        self._ai_error_text = status.error_text
        self._ai_available_models = list(status.available_models)
        self.aiConnectedChanged.emit()
        self.aiProviderNameChanged.emit()
        self.aiBaseUrlChanged.emit()
        self.aiModelNameChanged.emit()
        self.aiStatusTextChanged.emit()
        self.aiErrorTextChanged.emit()
        self.aiAvailableModelsChanged.emit()

    def update_ai_generating(self, generating: bool) -> None:
        if generating == self._ai_generating:
            return
        self._ai_generating = generating
        self.aiGeneratingChanged.emit()

    def update_chat_messages(self, messages: list[dict[str, Any]]) -> None:
        self._chat_messages = list(messages)
        self.chatMessagesChanged.emit()

    def update_diagnostics(self, diagnostics_text: str) -> None:
        if diagnostics_text == self._diagnostics_text:
            return
        self._diagnostics_text = diagnostics_text
        self.diagnosticsTextChanged.emit()

    @Slot(str)
    def handleLogMessage(self, message: str) -> None:
        self.logAppended.emit(message)

    @Slot("QVariantMap")
    def startListening(self, config_map: dict[str, Any]) -> None:
        if self._controller is not None:
            self._controller.start_listening(config_map)

    @Slot()
    def stopListening(self) -> None:
        if self._controller is not None:
            self._controller.stop_listening()

    @Slot("QVariantMap")
    def toggleListening(self, config_map: dict[str, Any]) -> None:
        if self._listening:
            self.stopListening()
        else:
            self.startListening(config_map)

    @Slot("QVariantMap")
    def testWorkflow(self, config_map: dict[str, Any]) -> None:
        if self._controller is not None:
            self._controller.test_workflow(config_map)

    @Slot("QVariantMap")
    def saveConfig(self, config_map: dict[str, Any]) -> None:
        if self._controller is not None:
            self._controller.save_config(config_map)

    @Slot()
    def reloadConfig(self) -> None:
        if self._controller is not None:
            self._controller.reload_config()

    @Slot()
    def openConfigFolder(self) -> None:
        if self._controller is not None:
            self._controller.open_config_folder()

    @Slot()
    def openLogsFolder(self) -> None:
        if self._controller is not None:
            self._controller.open_logs_folder()

    @Slot(str)
    def showView(self, view_name: str) -> None:
        if self._controller is not None:
            self._controller.show_view(view_name)

    @Slot(str)
    def setTheme(self, theme_name: str) -> None:
        if self._controller is not None:
            self._controller.set_surface_theme(theme_name)

    @Slot(str)
    def setAtomTheme(self, theme_name: str) -> None:
        if self._controller is not None:
            self._controller.set_atom_theme(theme_name)

    @Slot("QVariantMap")
    def refreshModels(self, config_map: dict[str, Any]) -> None:
        if self._controller is not None:
            self._controller.refresh_local_models(config_map)

    @Slot("QVariantMap")
    def testMicrophone(self, config_map: dict[str, Any]) -> None:
        if self._controller is not None:
            self._controller.test_microphone(config_map)

    @Slot("QVariantMap")
    def testTts(self, config_map: dict[str, Any]) -> None:
        if self._controller is not None:
            self._controller.test_tts(config_map)

    @Slot("QVariantMap")
    def testAi(self, config_map: dict[str, Any]) -> None:
        if self._controller is not None:
            self._controller.test_ai(config_map)

    @Slot("QVariantMap")
    def testStt(self, config_map: dict[str, Any]) -> None:
        if self._controller is not None:
            self._controller.test_stt(config_map)

    @Slot("QVariantMap")
    def startVoiceCapture(self, config_map: dict[str, Any]) -> None:
        if self._controller is not None:
            self._controller.start_voice_capture(config_map)

    @Slot("QVariantMap")
    def calibrateMicrophone(self, config_map: dict[str, Any]) -> None:
        if self._controller is not None:
            self._controller.calibrate_microphone(config_map)

    @Slot(str, "QVariantMap")
    def submitPrompt(self, prompt_text: str, config_map: dict[str, Any]) -> None:
        if self._controller is not None:
            self._controller.submit_prompt(prompt_text, config_map)

    @Slot()
    def clearChat(self) -> None:
        if self._controller is not None:
            self._controller.clear_chat()

    @Slot()
    def exportChat(self) -> None:
        if self._controller is not None:
            self._controller.export_chat()

    @Slot()
    def copyDiagnostics(self) -> None:
        if self._controller is not None:
            self._controller.copy_diagnostics()

    @Slot()
    def refreshAudioDevices(self) -> None:
        if self._controller is not None:
            self._controller.refresh_audio_devices()

    def notify(self, title: str, message: str) -> None:
        self.notificationRequested.emit(title, message)

    @Slot(str, str)
    def setWorkflowStep(self, title: str, detail: str) -> None:
        self.update_workflow_step(title, detail)
