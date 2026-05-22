from __future__ import annotations

import importlib
import sys


def _try_import(module_name: str) -> tuple[bool, str]:
    try:
        importlib.import_module(module_name)
        return True, f"{module_name} available"
    except Exception as exc:
        return False, f"{module_name} unavailable: {exc}"


def main() -> int:
    results = [
        _try_import("kokoro_onnx"),
        _try_import("win32com.client"),
    ]

    print(f"Python: {sys.version}")
    for available, message in results:
        prefix = "[ok]" if available else "[warn]"
        print(f"{prefix} {message}")

    if any(available for available, _message in results):
        print("At least one local TTS path is available.")
        return 0

    print("No local TTS backend import succeeded.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
