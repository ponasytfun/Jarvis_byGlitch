from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


APP_DIR_NAME = "JarvisAssistant"


@dataclass(frozen=True)
class AppPaths:
    project_root: Path
    defaults_config_path: Path
    appdata_dir: Path
    config_path: Path
    logs_dir: Path
    chat_history_path: Path
    audio_debug_dir: Path
    icon_path: Path
    qml_dir: Path
    qml_main_path: Path


def get_resource_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def build_app_paths() -> AppPaths:
    appdata_root = Path(os.getenv("APPDATA", str(Path.home() / "AppData" / "Roaming")))
    appdata_dir = appdata_root / APP_DIR_NAME
    project_root = get_resource_root()
    qml_dir = project_root / "assets" / "qml"
    return AppPaths(
        project_root=project_root,
        defaults_config_path=project_root / "defaults" / "config.yaml",
        appdata_dir=appdata_dir,
        config_path=appdata_dir / "config.yaml",
        logs_dir=appdata_dir / "logs",
        chat_history_path=appdata_dir / "chat_history.json",
        audio_debug_dir=appdata_dir / "audio_debug",
        icon_path=project_root / "assets" / "app_icon.ico",
        qml_dir=qml_dir,
        qml_main_path=qml_dir / "Main.qml",
    )


def ensure_user_directories(paths: AppPaths) -> None:
    paths.appdata_dir.mkdir(parents=True, exist_ok=True)
    paths.logs_dir.mkdir(parents=True, exist_ok=True)
    paths.audio_debug_dir.mkdir(parents=True, exist_ok=True)


def expand_windows_path(value: str) -> str:
    return os.path.expandvars(os.path.expanduser(value or "")).strip()


def open_in_explorer(path: Path) -> None:
    os.startfile(str(path))
