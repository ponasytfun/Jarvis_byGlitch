from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.request import urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from jarvis_assistant.paths import build_app_paths  # noqa: E402


KOKORO_ASSETS = {
    "kokoro-v1.0.int8.onnx": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx",
    "voices-v1.0.bin": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin",
}


def download_file(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        print(f"Skipping existing file: {destination}")
        return

    print(f"Downloading {url}")
    with urlopen(url, timeout=60) as response, destination.open("wb") as handle:
        while True:
            chunk = response.read(1024 * 128)
            if not chunk:
                break
            handle.write(chunk)
    print(f"Saved to {destination}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Download local voice assets for JarvisAssistant.")
    parser.add_argument(
        "--kokoro",
        action="store_true",
        help="Download Kokoro ONNX model files.",
    )
    args = parser.parse_args()

    if not args.kokoro:
        parser.print_help()
        return 0

    paths = build_app_paths()
    kokoro_dir = paths.appdata_dir / "models" / "kokoro"

    for filename, url in KOKORO_ASSETS.items():
        download_file(url, kokoro_dir / filename)

    print()
    print("Kokoro assets are ready.")
    print(f"Model folder: {kokoro_dir}")
    print("If you want a real openWakeWord Jarvis wake-word model, place it under:")
    print(paths.appdata_dir / "models" / "wakewords")
    print("Then point voice.wake_word_model_path at that file in the JarvisAssistant config.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
