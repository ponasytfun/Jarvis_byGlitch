from __future__ import annotations

import importlib
import sys


def main() -> int:
    try:
        module = importlib.import_module("faster_whisper")
    except Exception as exc:
        print("faster-whisper is not available.")
        print(str(exc))
        print("Use a Python 3.11 or 3.12 environment and run scripts\\install_voice_stack.bat for the preferred local STT path.")
        return 1

    print("faster-whisper import succeeded.")
    print(f"Module: {module.__name__}")
    print(f"Python: {sys.version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
