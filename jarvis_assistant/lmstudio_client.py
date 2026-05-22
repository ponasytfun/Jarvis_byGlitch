from __future__ import annotations

from jarvis_assistant.ai_manager import LocalAIManager
from jarvis_assistant.models import AIConfig


class LMStudioClient:
    """Backward-compatible LM Studio helper built on top of the provider manager."""

    def __init__(self, logger) -> None:
        self._ai_manager = LocalAIManager(logger)
        self.logger = logger.getChild("lm_studio")

    def chat(self, ai_config: AIConfig, prompt_text: str) -> str:
        lm_config = AIConfig.from_dict(ai_config.to_dict())
        lm_config.provider = "lm_studio"
        return self._ai_manager.chat(lm_config, prompt_text)

    def discover_model(self, base_url: str) -> str:
        probe_config = AIConfig.from_dict(
            {
                "provider": "lm_studio",
                "base_url": base_url,
                "lm_studio_base_url": base_url,
            }
        )
        status = self._ai_manager.probe(probe_config)
        return status.model_name if status.connected else ""
