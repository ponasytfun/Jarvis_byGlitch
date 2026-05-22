from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable

from jarvis_assistant.ai_manager import LocalAIManager
from jarvis_assistant.assistant_actions import AssistantActionOutcome, AssistantActionRegistry
from jarvis_assistant.models import AIConfig, JarvisConfig


@dataclass(frozen=True)
class AssistantIntent:
    type: str
    tool: str = ""
    args: dict[str, Any] = field(default_factory=dict)
    message: str = ""


@dataclass(frozen=True)
class AssistantTurnResult:
    mode: str
    response_text: str
    success: bool = True
    action_id: str = ""
    detail_text: str = ""
    payload: dict[str, Any] = field(default_factory=dict)


class AssistantEngine:
    """Hybrid intent router that keeps normal chat and safe local tools separate."""

    def __init__(
        self,
        ai_manager: LocalAIManager,
        action_registry: AssistantActionRegistry,
        logger,
    ) -> None:
        self.ai_manager = ai_manager
        self.action_registry = action_registry
        self.logger = logger.getChild("assistant_engine")

    def handle_prompt(
        self,
        config: JarvisConfig,
        prompt_text: str,
        *,
        on_status: Callable[[str, str], None] | None = None,
    ) -> AssistantTurnResult:
        prompt = prompt_text.strip()
        if not prompt:
            raise ValueError("Prompt text is empty.")

        intent = self._rule_based_intent(prompt)
        if intent is None and config.ai.tool_routing_enabled:
            intent = self._llm_router_intent(config, prompt)

        if intent is None or intent.type == "normal_chat":
            if config.ai.stream_enabled:
                response = self.ai_manager.stream_chat(config.ai, prompt)
            else:
                response = self.ai_manager.chat(config.ai, prompt)
            return AssistantTurnResult(
                mode="normal_chat",
                response_text=response,
                success=True,
                detail_text="Answered through the local AI brain.",
            )

        if intent.type == "clarify":
            return AssistantTurnResult(
                mode="clarify",
                response_text=intent.message or "I need a bit more detail before I do that.",
                success=False,
                detail_text=intent.message or "Clarification requested.",
            )

        if intent.type != "tool_call" or not intent.tool:
            response = self.ai_manager.chat(config.ai, prompt)
            return AssistantTurnResult(
                mode="normal_chat",
                response_text=response,
                success=True,
                detail_text="Fell back to normal local AI chat.",
            )

        action_name = intent.tool
        status_message = self._tool_status_message(action_name, intent.args)
        if on_status is not None:
            on_status("executing_action", status_message)

        try:
            outcome = self.action_registry.execute(action_name, config, intent.args)
        except Exception as exc:
            failure_text = self._tool_failure_message(action_name, intent.args, str(exc))
            self.logger.warning("Assistant action '%s' failed: %s", action_name, exc)
            return AssistantTurnResult(
                mode="tool_call",
                response_text=failure_text,
                success=False,
                action_id=action_name,
                detail_text=str(exc),
            )

        if not outcome.success:
            return AssistantTurnResult(
                mode="tool_call",
                response_text=outcome.response_text,
                success=False,
                action_id=outcome.action_id,
                detail_text=outcome.detail_text,
                payload=dict(outcome.payload),
            )

        return AssistantTurnResult(
            mode="tool_call",
            response_text=outcome.response_text,
            success=True,
            action_id=outcome.action_id,
            detail_text=outcome.detail_text,
            payload=dict(outcome.payload),
        )

    def _rule_based_intent(self, prompt: str) -> AssistantIntent | None:
        lowered = prompt.casefold().strip()

        theme_map = {
            "nuclear waste": "nuclear_waste",
            "blood red": "blood_red",
            "cold blue": "cold_blue",
            "dark theme": "dark",
            "light theme": "light",
        }
        for needle, theme_name in theme_map.items():
            if needle in lowered and any(
                phrase in lowered
                for phrase in ("switch", "change", "set", "use")
            ):
                return AssistantIntent("tool_call", "switch_theme", {"theme": theme_name})

        if any(phrase in lowered for phrase in ("jarvis status", "assistant status", "what model are you using", "which model are you using", "what provider are you using", "what ai are you using")):
            return AssistantIntent("tool_call", "assistant_status", {})

        if any(phrase in lowered for phrase in ("stop listening", "deactivate listening", "stop hearing me")):
            return AssistantIntent("tool_call", "stop_listening", {})

        if "focus mode" in lowered or (
            ("discord" in lowered and ("vs code" in lowered or "vscode" in lowered))
            and any(phrase in lowered for phrase in ("side by side", "split", "focus"))
        ):
            return AssistantIntent("tool_call", "focus_mode", {})

        if "clip that" in lowered or "save clip" in lowered or "obs clip" in lowered or "save replay" in lowered:
            return AssistantIntent("tool_call", "obs_clip", {})

        if "should i stay or should i go" in lowered or (
            "the clash" in lowered and any(phrase in lowered for phrase in ("play", "open", "start"))
        ):
            return AssistantIntent("tool_call", "play_music", {"song": "should i stay or should i go"})

        open_app = self._match_open_app(lowered)
        if open_app is not None:
            return AssistantIntent("tool_call", "open_app", {"app": open_app})

        return None

    def _match_open_app(self, lowered_prompt: str) -> str | None:
        app_aliases = {
            "discord": ("discord",),
            "vscode": ("vs code", "vscode", "visual studio code", "code editor"),
            "browser": ("browser", "brave"),
            "obs": ("obs", "obs studio"),
        }
        trigger_words = ("open", "launch", "focus", "bring up", "show")
        if not any(word in lowered_prompt for word in trigger_words):
            return None

        for app_name, aliases in app_aliases.items():
            if any(alias in lowered_prompt for alias in aliases):
                return app_name
        return None

    def _llm_router_intent(self, config: JarvisConfig, prompt_text: str) -> AssistantIntent | None:
        routing_config = self._routing_config(config.ai)
        routing_prompt = (
            "You are Jarvis's local intent router. Decide whether the user wants normal chat "
            "or a safe built-in tool. Return JSON only.\n\n"
            "Allowed JSON shapes:\n"
            '{"type":"normal_chat"}\n'
            '{"type":"clarify","message":"short question"}\n'
            '{"type":"tool_call","tool":"open_app","args":{"app":"discord"}}\n\n'
            "Allowed tools:\n"
            f"{self.action_registry.describe_for_router()}\n\n"
            "Rules:\n"
            "- Use open_app only for Discord, VS Code, browser/Brave, or OBS.\n"
            "- Use play_music only for the configured The Clash automation.\n"
            "- Use switch_theme for Nuclear Waste, Blood Red, Cold Blue, Dark, or Light.\n"
            "- Use assistant_status for provider/model/status questions.\n"
            "- Use stop_listening for direct listening stop requests.\n"
            "- If it is a normal question, return normal_chat.\n"
            "- If the request is missing a required detail, return clarify.\n"
            "- Do not invent tools.\n"
        )
        try:
            raw_response = self.ai_manager.chat(routing_config, prompt_text)
        except Exception as exc:
            self.logger.info("Intent router fell back to normal chat because planning failed: %s", exc)
            return None

        parsed = self._parse_router_json(raw_response)
        if parsed is None:
            self.logger.info("Intent router returned non-JSON output; using normal chat fallback.")
            return None

        intent_type = str(parsed.get("type", "normal_chat")).strip().lower()
        if intent_type == "tool_call":
            tool_name = str(parsed.get("tool", "")).strip()
            args = parsed.get("args", {})
            if not tool_name:
                return None
            if not isinstance(args, dict):
                args = {}
            return AssistantIntent("tool_call", tool_name, dict(args))
        if intent_type == "clarify":
            return AssistantIntent("clarify", message=str(parsed.get("message", "")).strip())
        return AssistantIntent("normal_chat")

    def _routing_config(self, ai_config: AIConfig) -> AIConfig:
        payload = ai_config.to_dict()
        payload["temperature"] = 0.05
        payload["max_tokens"] = 180
        payload["system_prompt"] = (
            "You are a JSON-only router for Jarvis. You never answer conversationally. "
            "You only return one compact JSON object."
        )
        return AIConfig.from_dict(payload)

    def _parse_router_json(self, raw_response: str) -> dict[str, Any] | None:
        cleaned = raw_response.strip()
        if not cleaned:
            return None

        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL | re.IGNORECASE)
        if fence_match:
            cleaned = fence_match.group(1).strip()
        elif not cleaned.startswith("{"):
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1 and end > start:
                cleaned = cleaned[start : end + 1]

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    def _tool_status_message(self, action_name: str, args: dict[str, Any]) -> str:
        if action_name == "open_app":
            return f"Opening {str(args.get('app', 'application')).title()}."
        if action_name == "play_music":
            return "Opening The Clash automation."
        if action_name == "focus_mode":
            return "Preparing focus mode."
        if action_name == "obs_clip":
            return "Saving an OBS clip."
        if action_name == "switch_theme":
            return f"Switching the theme to {args.get('theme', 'the requested palette')}."
        if action_name == "assistant_status":
            return "Collecting the current assistant status."
        if action_name == "stop_listening":
            return "Stopping the listening field."
        return f"Executing {action_name}."

    def _tool_failure_message(self, action_name: str, args: dict[str, Any], error_text: str) -> str:
        if action_name == "open_app":
            return f"I couldn't open {args.get('app', 'that app')} because {error_text}"
        if action_name == "play_music":
            return f"I couldn't complete the music automation because {error_text}"
        if action_name == "focus_mode":
            return f"I couldn't finish focus mode because {error_text}"
        if action_name == "obs_clip":
            return f"I couldn't save an OBS clip because {error_text}"
        if action_name == "switch_theme":
            return f"I couldn't switch the theme because {error_text}"
        if action_name == "assistant_status":
            return f"I couldn't collect my status because {error_text}"
        if action_name == "stop_listening":
            return f"I couldn't stop listening because {error_text}"
        return f"I couldn't complete that action because {error_text}"
