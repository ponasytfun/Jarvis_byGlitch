from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl

from jarvis_assistant.paths import AppPaths


def qml_main_url(paths: AppPaths) -> QUrl:
    return QUrl.fromLocalFile(str(paths.qml_main_path.resolve()))


def ensure_qml_exists(paths: AppPaths) -> Path:
    if not paths.qml_main_path.exists():
        raise FileNotFoundError(f"Main QML file not found: {paths.qml_main_path}")
    return paths.qml_main_path
