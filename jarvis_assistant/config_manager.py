from __future__ import annotations

import sys
import shutil
from datetime import datetime

import yaml

from jarvis_assistant.models import JarvisConfig
from jarvis_assistant.paths import AppPaths, ensure_user_directories


class ConfigManager:
    def __init__(self, paths: AppPaths) -> None:
        self.paths = paths

    def load_or_create(self) -> JarvisConfig:
        ensure_user_directories(self.paths)
        if not self.paths.config_path.exists():
            self._copy_defaults()
        return self.load()

    def load(self) -> JarvisConfig:
        defaults_raw = self._read_yaml(self.paths.defaults_config_path)
        user_raw = self._read_user_yaml()
        migrated_raw = self._migrate_legacy_config(user_raw)
        merged = self._deep_merge(defaults_raw, migrated_raw)
        try:
            config = JarvisConfig.from_dict(merged)
        except Exception as exc:
            backup_path = self._backup_invalid_config("schema", exc)
            config = JarvisConfig.from_dict(defaults_raw)
            self.save(config)
            self._emit_recovery_notice(
                "The JarvisAssistant config contained invalid values and was reset to defaults."
                + (f" Backup: {backup_path}" if backup_path else "")
            )
            return config
        if config.to_dict() != user_raw:
            self.save(config)
        return config

    def save(self, config: JarvisConfig) -> None:
        ensure_user_directories(self.paths)
        with self.paths.config_path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(
                config.to_dict(),
                handle,
                sort_keys=False,
                allow_unicode=False,
                default_flow_style=False,
            )

    def _copy_defaults(self) -> None:
        if not self.paths.defaults_config_path.exists():
            raise FileNotFoundError(
                f"Default config was not found: {self.paths.defaults_config_path}"
            )
        shutil.copyfile(self.paths.defaults_config_path, self.paths.config_path)

    def _read_yaml(self, path) -> dict:
        with path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}

    def _read_user_yaml(self) -> dict:
        try:
            payload = self._read_yaml(self.paths.config_path)
        except FileNotFoundError:
            return {}
        except yaml.YAMLError as exc:
            backup_path = self._backup_invalid_config("yaml", exc)
            self._emit_recovery_notice(
                "The JarvisAssistant config could not be parsed and was reset to defaults."
                + (f" Backup: {backup_path}" if backup_path else "")
            )
            return {}

        if not isinstance(payload, dict):
            backup_path = self._backup_invalid_config(
                "shape",
                ValueError(f"Top-level config payload must be a mapping, got {type(payload).__name__}."),
            )
            self._emit_recovery_notice(
                "The JarvisAssistant config had an invalid top-level structure and was reset to defaults."
                + (f" Backup: {backup_path}" if backup_path else "")
            )
            return {}
        return payload

    def _backup_invalid_config(self, reason: str, error: Exception) -> str:
        if not self.paths.config_path.exists():
            return ""

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = self.paths.config_path.with_suffix(f".{reason}.{timestamp}.bak")
        try:
            shutil.move(str(self.paths.config_path), str(backup_path))
        except Exception:
            try:
                shutil.copyfile(self.paths.config_path, backup_path)
            except Exception:
                return ""
        self._emit_recovery_notice(
            f"Backed up invalid config to {backup_path} after {reason} recovery: {error}"
        )
        return str(backup_path)

    def _emit_recovery_notice(self, message: str) -> None:
        print(f"JarvisAssistant config recovery: {message}", file=sys.stderr)

    def _migrate_legacy_config(self, data: dict) -> dict:
        migrated = dict(data or {})

        legacy_apps = migrated.pop("applications", None)
        if legacy_apps and "paths" not in migrated:
            paths: dict = {}
            matching = dict(migrated.get("matching", {}))
            for target_name, target_data in legacy_apps.items():
                window_match = dict(target_data.get("window_match", {}))
                match_payload = {
                    "allowed_title_fragments": window_match.get("title_fragments", []),
                    "allowed_process_names": window_match.get("process_names", []),
                    "title_regex": window_match.get("title_regex", ""),
                }

                if target_name == "brave":
                    paths["brave_path"] = target_data.get("executable", "")
                    paths["brave_args"] = target_data.get("args", [])
                    matching["brave"] = {**match_payload, **dict(matching.get("brave", {}))}
                elif target_name == "vscode":
                    paths["vscode_path"] = target_data.get("executable", "")
                    paths["vscode_args"] = target_data.get("args", [])
                    matching["vscode"] = {**match_payload, **dict(matching.get("vscode", {}))}
                elif target_name == "discord":
                    paths["discord_path"] = target_data.get("executable", "")
                    paths["discord_launch_args"] = target_data.get("args", [])
                    matching["discord"] = {
                        **match_payload,
                        **dict(matching.get("discord", {})),
                    }

            migrated["paths"] = {**dict(migrated.get("paths", {})), **paths}
            migrated["matching"] = matching

        music = dict(migrated.get("music", {}))
        if music:
            if "music_query" not in music and "query" in music:
                music["music_query"] = music.get("query", "")
            if "music_url" not in music and "url" in music:
                music["music_url"] = music.get("url", "")
            if "post_open_delay_ms" not in music and "open_delay_ms" in music:
                music["post_open_delay_ms"] = music.get("open_delay_ms", 2800)
            if (
                not str(music.get("music_url", "")).strip()
                and str(music.get("music_query", "")).strip().casefold()
                == "should i stay or should i go"
            ):
                music["music_url"] = "https://music.youtube.com/watch?v=BN1WwnEDWAM"
            migrated["music"] = music

        ai = dict(migrated.get("ai", {}))
        voice = dict(migrated.get("voice", {}))
        debug = dict(migrated.get("debug", {}))
        if voice:
            if "lm_studio_base_url" not in ai and voice.get("lm_studio_base_url"):
                ai["lm_studio_base_url"] = voice.get("lm_studio_base_url", "")
            if "model_name" not in ai and voice.get("lm_studio_model"):
                ai["model_name"] = voice.get("lm_studio_model", "")
            if "system_prompt" not in ai and voice.get("system_prompt"):
                ai["system_prompt"] = voice.get("system_prompt", "")
            if "temperature" not in ai and voice.get("temperature") is not None:
                ai["temperature"] = voice.get("temperature")
            if "max_tokens" not in ai and voice.get("response_max_tokens") is not None:
                ai["max_tokens"] = voice.get("response_max_tokens")
            if (
                str(ai.get("provider", "auto")).strip().lower() == "auto"
                and str(ai.get("base_url", "")).strip()
                == str(ai.get("lm_studio_base_url", "")).strip()
            ):
                ai["base_url"] = ""
            if ai:
                migrated["ai"] = {**dict(migrated.get("ai", {})), **ai}

            if "silence_timeout_seconds" not in voice and voice.get("silence_timeout_ms") is not None:
                try:
                    voice["silence_timeout_seconds"] = float(voice.get("silence_timeout_ms", 1200)) / 1000.0
                except Exception:
                    pass
            if "max_record_seconds" not in voice and voice.get("max_utterance_seconds") is not None:
                voice["max_record_seconds"] = voice.get("max_utterance_seconds")
            migrated["voice"] = {**dict(migrated.get("voice", {})), **voice}

        if "debug" not in migrated:
            debug["log_level"] = dict(migrated.get("logging", {})).get("level", "INFO")
            debug["save_transcripts"] = dict(migrated.get("voice", {})).get("log_transcripts", True)
            debug["save_audio_debug_files"] = False
            migrated["debug"] = debug

        ui = dict(migrated.get("ui", {}))
        if "chat_history_enabled" not in ui:
            ui["chat_history_enabled"] = True
        if "show_debug_panel" not in ui:
            ui["show_debug_panel"] = True
        migrated["ui"] = ui

        workflows = migrated.get("workflows", {})
        for workflow in workflows.values():
            for step in workflow.get("steps", []):
                params = step.get("params", step.get("parameters", {})) or {}
                if step.get("action") == "open_url_in_brave" and params.get("use_music_defaults"):
                    step["action"] = "open_music_in_brave"
                    step["params"] = {}
                    step.pop("parameters", None)
                elif "parameters" in step and "params" not in step:
                    step["params"] = step.pop("parameters")

        return migrated

    def _deep_merge(self, base: dict, override: dict) -> dict:
        merged = dict(base or {})
        for key, value in (override or {}).items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = self._deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged
