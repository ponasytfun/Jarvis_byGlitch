from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from jarvis_assistant.ai_manager import LocalAIManager  # noqa: E402
from jarvis_assistant.config_manager import ConfigManager  # noqa: E402
from jarvis_assistant.paths import build_app_paths  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe JarvisAssistant local AI providers.")
    parser.add_argument("--probe-only", action="store_true", help="Only probe providers and list models.")
    parser.add_argument("--chat", default="", help="Send a smoke-test prompt to the connected local model.")
    parser.add_argument("--stream-chat", default="", help="Send a streaming smoke-test prompt to the connected local model.")
    parser.add_argument("--require-connected", action="store_true", help="Return a non-zero exit code if no provider is connected.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger("JarvisAssistant.TestAI")

    paths = build_app_paths()
    config = ConfigManager(paths).load_or_create()
    manager = LocalAIManager(logger)
    status = manager.probe(config.ai)

    print(f"Connected: {status.connected}")
    print(f"Provider: {status.provider_display_name}")
    print(f"Base URL: {status.base_url or '(none)'}")
    print(f"Selected model: {status.model_name or '(none)'}")
    print(f"Status: {status.status_text}")
    if status.available_models:
        print("Available models:")
        for model_name in status.available_models:
            print(f"  - {model_name}")
    if status.error_text:
        print(f"Error detail: {status.error_text}")

    if args.chat:
        if not status.connected:
            print("No connected provider is available for a chat smoke test.")
            return 1
        print("")
        print(f"Sending prompt: {args.chat}")
        response = manager.chat(config.ai, args.chat)
        print("Response:")
        print(response)

    if args.stream_chat:
        if not status.connected:
            print("No connected provider is available for a streaming chat smoke test.")
            return 1
        print("")
        print(f"Streaming prompt: {args.stream_chat}")
        chunks: list[str] = []
        response = manager.stream_chat(config.ai, args.stream_chat, on_chunk=chunks.append)
        print(f"Received {len(chunks)} streamed chunk(s).")
        print("Response:")
        print(response)

    if args.probe_only and status.connected:
        return 0
    if args.require_connected and not status.connected:
        return 1
    return 0 if status.connected or not args.require_connected else 1


if __name__ == "__main__":
    raise SystemExit(main())
