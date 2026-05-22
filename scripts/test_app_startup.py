from __future__ import annotations

import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402
from PySide6.QtQuickControls2 import QQuickStyle  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from jarvis_assistant.app import JarvisAssistantController  # noqa: E402


def main() -> int:
    QQuickStyle.setStyle("Basic")
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    engine = QQmlApplicationEngine()
    controller = JarvisAssistantController(engine)
    if not engine.rootObjects():
        raise RuntimeError("QML engine did not create any root objects.")

    QTimer.singleShot(250, app.quit)
    app.exec()
    controller.shutdown()
    print("JarvisAssistant startup smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
