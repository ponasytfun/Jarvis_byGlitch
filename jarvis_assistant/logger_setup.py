from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from jarvis_assistant.models import LoggingConfig


class LogEmitter(QObject):
    messageEmitted = Signal(str)


class QtSignalLogHandler(logging.Handler):
    def __init__(self, emitter: LogEmitter) -> None:
        super().__init__()
        self.emitter = emitter

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.emitter.messageEmitted.emit(self.format(record))
        except Exception:
            self.handleError(record)


def setup_logging(logs_dir: Path, settings: LoggingConfig, emitter: LogEmitter) -> logging.Logger:
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / "JarvisAssistant.log"

    level = getattr(logging, settings.level.upper(), logging.INFO)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level)

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=settings.max_bytes,
        backupCount=settings.backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    signal_handler = QtSignalLogHandler(emitter)
    signal_handler.setLevel(level)
    signal_handler.setFormatter(formatter)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(signal_handler)

    logger = logging.getLogger("JarvisAssistant")
    logger.setLevel(level)
    logger.info("Logging to %s", log_path)
    return logger
