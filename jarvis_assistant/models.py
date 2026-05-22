from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _coerce_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


@dataclass
class AppInfo:
    name: str = "JarvisAssistant"
    version: str = "1.0.0"
    subtitle: str = "Local desktop command core"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppInfo":
        return cls(
            name=str(data.get("name", "JarvisAssistant")),
            version=str(data.get("version", "1.0.0")),
            subtitle=str(data.get("subtitle", "Local desktop command core")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "subtitle": self.subtitle,
        }


@dataclass
class UIConfig:
    theme: str = "dark"
    atom_theme: str = "cold_blue"
    animations_enabled: bool = True
    compact_logs: bool = False
    chat_history_enabled: bool = True
    show_debug_panel: bool = True
    window_width: int = 1480
    window_height: int = 940

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UIConfig":
        raw_theme = str(data.get("theme", "dark")).lower()
        theme = raw_theme if raw_theme in {"dark", "light"} else "dark"
        raw_atom_theme = str(data.get("atom_theme", "cold_blue")).lower()
        atom_theme = (
            raw_atom_theme
            if raw_atom_theme in {"nuclear_waste", "blood_red", "cold_blue"}
            else "cold_blue"
        )
        return cls(
            theme=theme,
            atom_theme=atom_theme,
            animations_enabled=bool(data.get("animations_enabled", True)),
            compact_logs=bool(data.get("compact_logs", False)),
            chat_history_enabled=bool(data.get("chat_history_enabled", True)),
            show_debug_panel=bool(data.get("show_debug_panel", True)),
            window_width=int(data.get("window_width", 1480)),
            window_height=int(data.get("window_height", 940)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "theme": self.theme,
            "atom_theme": self.atom_theme,
            "animations_enabled": self.animations_enabled,
            "compact_logs": self.compact_logs,
            "chat_history_enabled": self.chat_history_enabled,
            "show_debug_panel": self.show_debug_panel,
            "window_width": self.window_width,
            "window_height": self.window_height,
        }


@dataclass
class AudioConfig:
    device_index: int | None = None
    sample_rate: int = 16_000
    block_duration_ms: int = 20
    calibration_seconds: float = 2.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AudioConfig":
        raw_device = data.get("device_index")
        device_index: int | None
        if raw_device in ("", None):
            device_index = None
        else:
            device_index = int(raw_device)

        return cls(
            device_index=device_index,
            sample_rate=int(data.get("sample_rate", 16_000)),
            block_duration_ms=int(data.get("block_duration_ms", 20)),
            calibration_seconds=float(data.get("calibration_seconds", 2.0)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "device_index": self.device_index,
            "sample_rate": self.sample_rate,
            "block_duration_ms": self.block_duration_ms,
            "calibration_seconds": self.calibration_seconds,
        }


@dataclass
class TriggerConfig:
    clap_count: int = 3
    window_seconds: float = 2.5
    min_clap_gap_ms: int = 120
    max_clap_gap_ms: int = 900
    amplitude_threshold: float = 0.12
    cooldown_seconds: float = 10.0
    noise_floor_auto_calibrate: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TriggerConfig":
        return cls(
            clap_count=int(data.get("clap_count", 3)),
            window_seconds=float(data.get("window_seconds", 2.5)),
            min_clap_gap_ms=int(data.get("min_clap_gap_ms", 120)),
            max_clap_gap_ms=int(data.get("max_clap_gap_ms", 900)),
            amplitude_threshold=float(data.get("amplitude_threshold", 0.12)),
            cooldown_seconds=float(data.get("cooldown_seconds", 10.0)),
            noise_floor_auto_calibrate=bool(data.get("noise_floor_auto_calibrate", True)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "clap_count": self.clap_count,
            "window_seconds": self.window_seconds,
            "min_clap_gap_ms": self.min_clap_gap_ms,
            "max_clap_gap_ms": self.max_clap_gap_ms,
            "amplitude_threshold": self.amplitude_threshold,
            "cooldown_seconds": self.cooldown_seconds,
            "noise_floor_auto_calibrate": self.noise_floor_auto_calibrate,
        }


@dataclass
class PathsConfig:
    brave_path: str = "%ProgramFiles%\\BraveSoftware\\Brave-Browser\\Application\\brave.exe"
    brave_args: list[str] = field(default_factory=list)
    vscode_path: str = "%LocalAppData%\\Programs\\Microsoft VS Code\\Code.exe"
    vscode_args: list[str] = field(default_factory=list)
    discord_path: str = "%LocalAppData%\\Discord\\Update.exe"
    discord_launch_args: list[str] = field(
        default_factory=lambda: ["--processStart", "Discord.exe"]
    )
    obs_path: str = "%ProgramFiles%\\obs-studio\\bin\\64bit\\obs64.exe"
    obs_args: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PathsConfig":
        return cls(
            brave_path=str(
                data.get(
                    "brave_path",
                    "%ProgramFiles%\\BraveSoftware\\Brave-Browser\\Application\\brave.exe",
                )
            ),
            brave_args=_coerce_str_list(data.get("brave_args", [])),
            vscode_path=str(
                data.get(
                    "vscode_path",
                    "%LocalAppData%\\Programs\\Microsoft VS Code\\Code.exe",
                )
            ),
            vscode_args=_coerce_str_list(data.get("vscode_args", [])),
            discord_path=str(
                data.get("discord_path", "%LocalAppData%\\Discord\\Update.exe")
            ),
            discord_launch_args=_coerce_str_list(
                data.get("discord_launch_args", ["--processStart", "Discord.exe"])
            ),
            obs_path=str(
                data.get("obs_path", "%ProgramFiles%\\obs-studio\\bin\\64bit\\obs64.exe")
            ),
            obs_args=_coerce_str_list(data.get("obs_args", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "brave_path": self.brave_path,
            "brave_args": self.brave_args,
            "vscode_path": self.vscode_path,
            "vscode_args": self.vscode_args,
            "discord_path": self.discord_path,
            "discord_launch_args": self.discord_launch_args,
            "obs_path": self.obs_path,
            "obs_args": self.obs_args,
        }


@dataclass
class WindowMatchConfig:
    allowed_title_fragments: list[str] = field(default_factory=list)
    allowed_process_names: list[str] = field(default_factory=list)
    title_regex: str = ""
    focus_retry_count: int = 3
    focus_retry_delay_ms: int = 350
    launch_timeout_ms: int = 18_000
    continue_on_error: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WindowMatchConfig":
        return cls(
            allowed_title_fragments=_coerce_str_list(data.get("allowed_title_fragments", [])),
            allowed_process_names=_coerce_str_list(data.get("allowed_process_names", [])),
            title_regex=str(data.get("title_regex", "")),
            focus_retry_count=int(data.get("focus_retry_count", 3)),
            focus_retry_delay_ms=int(data.get("focus_retry_delay_ms", 350)),
            launch_timeout_ms=int(data.get("launch_timeout_ms", 18_000)),
            continue_on_error=bool(data.get("continue_on_error", True)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed_title_fragments": self.allowed_title_fragments,
            "allowed_process_names": self.allowed_process_names,
            "title_regex": self.title_regex,
            "focus_retry_count": self.focus_retry_count,
            "focus_retry_delay_ms": self.focus_retry_delay_ms,
            "launch_timeout_ms": self.launch_timeout_ms,
            "continue_on_error": self.continue_on_error,
        }


@dataclass
class MatchingConfig:
    brave: WindowMatchConfig = field(default_factory=WindowMatchConfig)
    vscode: WindowMatchConfig = field(default_factory=WindowMatchConfig)
    discord: WindowMatchConfig = field(default_factory=WindowMatchConfig)
    obs: WindowMatchConfig = field(default_factory=WindowMatchConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MatchingConfig":
        return cls(
            brave=WindowMatchConfig.from_dict(data.get("brave", {})),
            vscode=WindowMatchConfig.from_dict(data.get("vscode", {})),
            discord=WindowMatchConfig.from_dict(data.get("discord", {})),
            obs=WindowMatchConfig.from_dict(data.get("obs", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "brave": self.brave.to_dict(),
            "vscode": self.vscode.to_dict(),
            "discord": self.discord.to_dict(),
            "obs": self.obs.to_dict(),
        }


@dataclass
class MusicConfig:
    music_query: str = "Should I Stay or Should I Go"
    music_url: str = "https://music.youtube.com/watch?v=BN1WwnEDWAM"
    playback_start_timeout_ms: int = 5000
    post_open_delay_ms: int = 2800
    use_media_key_fallback: bool = True
    use_play_shortcut_fallback: bool = False
    play_shortcut_key: str = "k"
    verify_playback_best_effort: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MusicConfig":
        music_query = data.get("music_query", data.get("query", "Should I Stay or Should I Go"))
        music_url = data.get("music_url", data.get("url", "https://music.youtube.com/watch?v=BN1WwnEDWAM"))
        open_delay = data.get("post_open_delay_ms", data.get("open_delay_ms", 2800))
        return cls(
            music_query=str(music_query),
            music_url=str(music_url),
            playback_start_timeout_ms=int(data.get("playback_start_timeout_ms", 5000)),
            post_open_delay_ms=int(open_delay),
            use_media_key_fallback=bool(data.get("use_media_key_fallback", True)),
            use_play_shortcut_fallback=bool(data.get("use_play_shortcut_fallback", False)),
            play_shortcut_key=str(data.get("play_shortcut_key", "k")),
            verify_playback_best_effort=bool(
                data.get("verify_playback_best_effort", True)
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "music_query": self.music_query,
            "music_url": self.music_url,
            "playback_start_timeout_ms": self.playback_start_timeout_ms,
            "post_open_delay_ms": self.post_open_delay_ms,
            "use_media_key_fallback": self.use_media_key_fallback,
            "use_play_shortcut_fallback": self.use_play_shortcut_fallback,
            "play_shortcut_key": self.play_shortcut_key,
            "verify_playback_best_effort": self.verify_playback_best_effort,
        }


@dataclass
class LoggingConfig:
    level: str = "INFO"
    max_bytes: int = 1_048_576
    backup_count: int = 5

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LoggingConfig":
        return cls(
            level=str(data.get("level", "INFO")),
            max_bytes=int(data.get("max_bytes", 1_048_576)),
            backup_count=int(data.get("backup_count", 5)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "max_bytes": self.max_bytes,
            "backup_count": self.backup_count,
        }


@dataclass
class AIConfig:
    provider: str = "auto"
    base_url: str = ""
    model_name: str = ""
    tool_routing_enabled: bool = True
    stream_enabled: bool = False
    temperature: float = 0.35
    max_tokens: int = 220
    system_prompt: str = (
        "You are Jarvis, a helpful local desktop assistant. You are concise, practical, "
        "and capable of helping with coding, automation, system tasks, and general "
        "questions. You run locally and should explain clearly when a requested action "
        "requires user permission or a missing dependency."
    )
    request_timeout_seconds: int = 45
    lm_studio_base_url: str = "http://127.0.0.1:1234/v1"
    lm_studio_alt_base_url: str = "http://127.0.0.1:1234/api/v1"
    ollama_base_url: str = "http://127.0.0.1:11434"
    allow_ollama_fallback: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AIConfig":
        return cls(
            provider=str(data.get("provider", "auto")),
            base_url=str(data.get("base_url", "")),
            model_name=str(data.get("model_name", "")),
            tool_routing_enabled=bool(data.get("tool_routing_enabled", True)),
            stream_enabled=bool(data.get("stream_enabled", False)),
            temperature=float(data.get("temperature", 0.35)),
            max_tokens=int(data.get("max_tokens", 220)),
            system_prompt=str(
                data.get(
                    "system_prompt",
                    "You are Jarvis, a helpful local desktop assistant. You are concise, practical, "
                    "and capable of helping with coding, automation, system tasks, and general "
                    "questions. You run locally and should explain clearly when a requested action "
                    "requires user permission or a missing dependency.",
                )
            ),
            request_timeout_seconds=int(data.get("request_timeout_seconds", 45)),
            lm_studio_base_url=str(data.get("lm_studio_base_url", "http://127.0.0.1:1234/v1")),
            lm_studio_alt_base_url=str(
                data.get("lm_studio_alt_base_url", "http://127.0.0.1:1234/api/v1")
            ),
            ollama_base_url=str(data.get("ollama_base_url", "http://127.0.0.1:11434")),
            allow_ollama_fallback=bool(data.get("allow_ollama_fallback", True)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "base_url": self.base_url,
            "model_name": self.model_name,
            "tool_routing_enabled": self.tool_routing_enabled,
            "stream_enabled": self.stream_enabled,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "system_prompt": self.system_prompt,
            "request_timeout_seconds": self.request_timeout_seconds,
            "lm_studio_base_url": self.lm_studio_base_url,
            "lm_studio_alt_base_url": self.lm_studio_alt_base_url,
            "ollama_base_url": self.ollama_base_url,
            "allow_ollama_fallback": self.allow_ollama_fallback,
        }


@dataclass
class RuntimeConfig:
    default_workflow: str = "triple_clap_focus_mode"
    dry_run: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RuntimeConfig":
        return cls(
            default_workflow=str(data.get("default_workflow", "triple_clap_focus_mode")),
            dry_run=bool(data.get("dry_run", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "default_workflow": self.default_workflow,
            "dry_run": self.dry_run,
        }


@dataclass
class VoiceConfig:
    enabled: bool = False
    click_to_talk_enabled: bool = True
    auto_start_with_listening: bool = False
    wake_word_enabled: bool = False
    wake_word_model_path: str = ""
    wake_phrases: list[str] = field(
        default_factory=lambda: ["hey jarvis", "jarvis activate"]
    )
    deactivate_phrases: list[str] = field(
        default_factory=lambda: ["jarvis deactivate", "jarvis deactivate now"]
    )
    wake_threshold: float = 0.52
    wakeword_vad_threshold: float = 0.45
    vad_enabled: bool = True
    vad_sensitivity: float = 0.55
    vad_mode: str = "energy"
    vad_aggressiveness: int = 2
    speech_threshold: float = 0.018
    listen_timeout_seconds: float = 15.0
    silence_timeout_seconds: float = 1.2
    silence_timeout_ms: int = 1200
    min_record_seconds: float = 0.5
    max_record_seconds: float = 20.0
    max_utterance_seconds: float = 20.0
    stt_backend: str = "faster_whisper"
    stt_model: str = "base"
    stt_fallback_model: str = "tiny"
    stt_device: str = "auto"
    stt_compute_type: str = "auto"
    tts_backend: str = "auto"
    tts_voice: str = "bf_emma"
    tts_rate: float = 1.0
    tts_volume: float = 0.9
    tts_model_path: str = (
        "%APPDATA%\\JarvisAssistant\\models\\kokoro\\kokoro-v1.0.int8.onnx"
    )
    tts_voices_path: str = "%APPDATA%\\JarvisAssistant\\models\\kokoro\\voices-v1.0.bin"
    piper_exe_path: str = ""
    piper_model_path: str = ""
    output_device_index: int | None = None
    output_device_name: str = ""
    barge_in_enabled: bool = False
    log_transcripts: bool = True
    speak_responses: bool = True
    acknowledgement_phrase: str = "Yes?"
    test_phrase: str = "Voice systems nominal."

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VoiceConfig":
        raw_output_device = data.get("output_device_index")
        output_device_index: int | None
        if raw_output_device in ("", None):
            output_device_index = None
        else:
            output_device_index = int(raw_output_device)

        silence_timeout_seconds = float(
            data.get(
                "silence_timeout_seconds",
                float(data.get("silence_timeout_ms", 1200)) / 1000.0,
            )
        )
        max_record_seconds = float(
            data.get(
                "max_record_seconds",
                data.get("max_utterance_seconds", 20.0),
            )
        )

        return cls(
            enabled=bool(data.get("enabled", data.get("voice_enabled", False))),
            click_to_talk_enabled=bool(data.get("click_to_talk_enabled", True)),
            auto_start_with_listening=bool(data.get("auto_start_with_listening", False)),
            wake_word_enabled=bool(data.get("wake_word_enabled", False)),
            wake_word_model_path=str(data.get("wake_word_model_path", "")),
            wake_phrases=_coerce_str_list(
                data.get("wake_phrases", ["hey jarvis", "jarvis activate"])
            ),
            deactivate_phrases=_coerce_str_list(
                data.get(
                    "deactivate_phrases",
                    ["jarvis deactivate", "jarvis deactivate now"],
                )
            ),
            wake_threshold=float(data.get("wake_threshold", 0.52)),
            wakeword_vad_threshold=float(data.get("wakeword_vad_threshold", 0.45)),
            vad_enabled=bool(data.get("vad_enabled", True)),
            vad_sensitivity=float(data.get("vad_sensitivity", 0.55)),
            vad_mode=str(data.get("vad_mode", "energy")),
            vad_aggressiveness=int(data.get("vad_aggressiveness", 2)),
            speech_threshold=float(data.get("speech_threshold", 0.018)),
            listen_timeout_seconds=float(data.get("listen_timeout_seconds", 15.0)),
            silence_timeout_seconds=silence_timeout_seconds,
            silence_timeout_ms=int(round(silence_timeout_seconds * 1000.0)),
            min_record_seconds=float(data.get("min_record_seconds", 0.5)),
            max_record_seconds=max_record_seconds,
            max_utterance_seconds=max_record_seconds,
            stt_backend=str(data.get("stt_backend", "faster_whisper")),
            stt_model=str(data.get("stt_model", "base")),
            stt_fallback_model=str(data.get("stt_fallback_model", "tiny")),
            stt_device=str(data.get("stt_device", "auto")),
            stt_compute_type=str(data.get("stt_compute_type", "auto")),
            tts_backend=str(data.get("tts_backend", "auto")),
            tts_voice=str(data.get("tts_voice", data.get("voice_name", "bf_emma"))),
            tts_rate=float(data.get("tts_rate", data.get("rate", 1.0))),
            tts_volume=float(data.get("tts_volume", data.get("volume", 0.9))),
            tts_model_path=str(
                data.get(
                    "tts_model_path",
                    "%APPDATA%\\JarvisAssistant\\models\\kokoro\\kokoro-v1.0.int8.onnx",
                )
            ),
            tts_voices_path=str(
                data.get(
                    "tts_voices_path",
                    "%APPDATA%\\JarvisAssistant\\models\\kokoro\\voices-v1.0.bin",
                )
            ),
            piper_exe_path=str(data.get("piper_exe_path", "")),
            piper_model_path=str(data.get("piper_model_path", "")),
            output_device_index=output_device_index,
            output_device_name=str(data.get("output_device_name", "")),
            barge_in_enabled=bool(data.get("barge_in_enabled", False)),
            log_transcripts=bool(data.get("log_transcripts", True)),
            speak_responses=bool(data.get("speak_responses", True)),
            acknowledgement_phrase=str(data.get("acknowledgement_phrase", "Yes?")),
            test_phrase=str(data.get("test_phrase", "Voice systems nominal.")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "click_to_talk_enabled": self.click_to_talk_enabled,
            "auto_start_with_listening": self.auto_start_with_listening,
            "wake_word_enabled": self.wake_word_enabled,
            "wake_word_model_path": self.wake_word_model_path,
            "wake_phrases": self.wake_phrases,
            "deactivate_phrases": self.deactivate_phrases,
            "wake_threshold": self.wake_threshold,
            "wakeword_vad_threshold": self.wakeword_vad_threshold,
            "vad_enabled": self.vad_enabled,
            "vad_sensitivity": self.vad_sensitivity,
            "vad_mode": self.vad_mode,
            "vad_aggressiveness": self.vad_aggressiveness,
            "speech_threshold": self.speech_threshold,
            "listen_timeout_seconds": self.listen_timeout_seconds,
            "silence_timeout_seconds": self.silence_timeout_seconds,
            "silence_timeout_ms": self.silence_timeout_ms,
            "min_record_seconds": self.min_record_seconds,
            "max_record_seconds": self.max_record_seconds,
            "max_utterance_seconds": self.max_utterance_seconds,
            "stt_backend": self.stt_backend,
            "stt_model": self.stt_model,
            "stt_fallback_model": self.stt_fallback_model,
            "stt_device": self.stt_device,
            "stt_compute_type": self.stt_compute_type,
            "tts_backend": self.tts_backend,
            "tts_voice": self.tts_voice,
            "tts_rate": self.tts_rate,
            "tts_volume": self.tts_volume,
            "tts_model_path": self.tts_model_path,
            "tts_voices_path": self.tts_voices_path,
            "piper_exe_path": self.piper_exe_path,
            "piper_model_path": self.piper_model_path,
            "output_device_index": self.output_device_index,
            "output_device_name": self.output_device_name,
            "barge_in_enabled": self.barge_in_enabled,
            "log_transcripts": self.log_transcripts,
            "speak_responses": self.speak_responses,
            "acknowledgement_phrase": self.acknowledgement_phrase,
            "test_phrase": self.test_phrase,
        }


@dataclass
class DebugConfig:
    log_level: str = "INFO"
    save_audio_debug_files: bool = False
    save_transcripts: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any], logging_level: str = "INFO") -> "DebugConfig":
        return cls(
            log_level=str(data.get("log_level", logging_level or "INFO")),
            save_audio_debug_files=bool(data.get("save_audio_debug_files", False)),
            save_transcripts=bool(data.get("save_transcripts", True)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "log_level": self.log_level,
            "save_audio_debug_files": self.save_audio_debug_files,
            "save_transcripts": self.save_transcripts,
        }


@dataclass
class WorkflowStep:
    action: str
    params: dict[str, Any] = field(default_factory=dict)
    timeout_ms: int | None = None
    retries: int = 1
    delay_after_ms: int = 0
    continue_on_error: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkflowStep":
        params = data.get("params", data.get("parameters", {}))
        timeout = data.get("timeout_ms", data.get("timeout_seconds"))
        timeout_ms = None if timeout is None else int(timeout)
        if timeout_ms is not None and "timeout_seconds" in data:
            timeout_ms = int(float(timeout) * 1000)

        return cls(
            action=str(data["action"]),
            params=dict(params or {}),
            timeout_ms=timeout_ms,
            retries=int(data.get("retries", 1)),
            delay_after_ms=int(data.get("delay_after_ms", 0)),
            continue_on_error=bool(data.get("continue_on_error", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "action": self.action,
            "params": self.params,
            "retries": self.retries,
            "delay_after_ms": self.delay_after_ms,
            "continue_on_error": self.continue_on_error,
        }
        if self.timeout_ms is not None:
            payload["timeout_ms"] = self.timeout_ms
        return payload


@dataclass
class WorkflowDefinition:
    description: str = ""
    steps: list[WorkflowStep] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkflowDefinition":
        return cls(
            description=str(data.get("description", "")),
            steps=[WorkflowStep.from_dict(item) for item in data.get("steps", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "steps": [step.to_dict() for step in self.steps],
        }


@dataclass
class JarvisConfig:
    app: AppInfo = field(default_factory=AppInfo)
    ui: UIConfig = field(default_factory=UIConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    trigger: TriggerConfig = field(default_factory=TriggerConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    matching: MatchingConfig = field(default_factory=MatchingConfig)
    music: MusicConfig = field(default_factory=MusicConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    voice: VoiceConfig = field(default_factory=VoiceConfig)
    debug: DebugConfig = field(default_factory=DebugConfig)
    workflows: dict[str, WorkflowDefinition] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JarvisConfig":
        return cls(
            app=AppInfo.from_dict(data.get("app", {})),
            ui=UIConfig.from_dict(data.get("ui", {})),
            audio=AudioConfig.from_dict(data.get("audio", {})),
            trigger=TriggerConfig.from_dict(data.get("trigger", {})),
            paths=PathsConfig.from_dict(data.get("paths", {})),
            matching=MatchingConfig.from_dict(data.get("matching", {})),
            music=MusicConfig.from_dict(data.get("music", {})),
            ai=AIConfig.from_dict(data.get("ai", {})),
            runtime=RuntimeConfig.from_dict(data.get("runtime", {})),
            logging=LoggingConfig.from_dict(data.get("logging", {})),
            voice=VoiceConfig.from_dict(data.get("voice", {})),
            debug=DebugConfig.from_dict(
                data.get("debug", {}),
                logging_level=str(data.get("logging", {}).get("level", "INFO")),
            ),
            workflows={
                str(name): WorkflowDefinition.from_dict(item)
                for name, item in data.get("workflows", {}).items()
            },
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "app": self.app.to_dict(),
            "ui": self.ui.to_dict(),
            "audio": self.audio.to_dict(),
            "trigger": self.trigger.to_dict(),
            "paths": self.paths.to_dict(),
            "matching": self.matching.to_dict(),
            "music": self.music.to_dict(),
            "ai": self.ai.to_dict(),
            "runtime": self.runtime.to_dict(),
            "logging": self.logging.to_dict(),
            "voice": self.voice.to_dict(),
            "debug": self.debug.to_dict(),
            "workflows": {
                name: workflow.to_dict() for name, workflow in self.workflows.items()
            },
        }

    def clone(self) -> "JarvisConfig":
        return JarvisConfig.from_dict(self.to_dict())


@dataclass(frozen=True)
class AudioCalibration:
    noise_floor: float
    effective_threshold: float


@dataclass(frozen=True)
class AudioLevel:
    normalized: float
    peak: float
    rms: float


@dataclass(frozen=True)
class ClapEvent:
    timestamp: float
    peak: float
    rms: float
    effective_threshold: float
    clap_timestamps: list[float]


@dataclass(frozen=True)
class WindowCandidate:
    hwnd: int
    title: str
    pid: int
    process_name: str
    is_minimized: bool
    rectangle: tuple[int, int, int, int]


@dataclass(frozen=True)
class PlaybackAttemptResult:
    url_opened: str
    used_direct_url: bool
    playback_attempted: bool
    playback_likely_started: bool
    playback_confirmed: bool
    details: str


@dataclass(frozen=True)
class WorkflowResult:
    success: bool
    message: str


@dataclass(frozen=True)
class AIBackendStatus:
    connected: bool
    provider: str
    provider_display_name: str
    base_url: str
    model_name: str
    available_models: list[str]
    status_text: str
    error_text: str = ""


@dataclass(frozen=True)
class AudioProbeResult:
    peak: float
    rms: float
    seconds: float
    device_label: str
    sample_rate: int = 0
    average_abs: float = 0.0
    detected_audio: bool = False
    debug_wav_path: str = ""


@dataclass(frozen=True)
class SpeechCaptureResult:
    transcript: str
    peak: float
    rms: float
    seconds: float
    device_label: str
    sample_rate: int
    debug_wav_path: str = ""
