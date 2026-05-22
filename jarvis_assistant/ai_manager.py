from __future__ import annotations

import json
from typing import Callable
from urllib import error, request

from jarvis_assistant.models import AIBackendStatus, AIConfig


class LocalAIManager:
    """Detects and talks to local OpenAI-compatible or Ollama-style providers."""

    def __init__(self, logger) -> None:
        self.logger = logger.getChild("local_ai")
        self._last_status = AIBackendStatus(
            connected=False,
            provider="none",
            provider_display_name="No Provider",
            base_url="",
            model_name="",
            available_models=[],
            status_text="No local AI provider has been checked yet.",
            error_text="",
        )

    @property
    def last_status(self) -> AIBackendStatus:
        return self._last_status

    def probe(self, config: AIConfig) -> AIBackendStatus:
        requested_provider = (config.provider or "auto").strip().lower()
        if requested_provider in {"lm_studio", "lmstudio", "openai_compatible"}:
            status = self._probe_lm_studio(
                config,
                self._candidate_lm_studio_urls(config),
            )
            self._last_status = status
            return status

        if requested_provider == "ollama":
            status = self._probe_ollama(
                config,
                self._normalize_ollama_base_url(config.base_url or config.ollama_base_url),
            )
            self._last_status = status
            return status

        if config.base_url.strip():
            guessed = self._probe_explicit_base_url(config)
            if guessed.connected:
                self._last_status = guessed
                return guessed

        last_failure = AIBackendStatus(
            connected=False,
            provider="none",
            provider_display_name="No Provider",
            base_url="",
            model_name="",
            available_models=[],
            status_text="No local AI provider was reachable.",
            error_text="No local AI provider was reachable.",
        )

        lm_status = self._probe_lm_studio(config, self._candidate_lm_studio_urls(config))
        if lm_status.connected:
            self._last_status = lm_status
            return lm_status
        last_failure = lm_status

        if config.allow_ollama_fallback:
            ollama_status = self._probe_ollama(
                config,
                self._normalize_ollama_base_url(config.ollama_base_url),
            )
            if ollama_status.connected:
                self._last_status = ollama_status
                return ollama_status
            last_failure = ollama_status

        self._last_status = last_failure
        return last_failure

    def chat(self, config: AIConfig, prompt_text: str) -> str:
        status = self.probe(config)
        if not status.connected:
            raise RuntimeError(status.error_text or status.status_text)

        try:
            if status.provider == "lm_studio":
                response = self._chat_lm_studio(config, status, prompt_text)
            elif status.provider == "ollama":
                response = self._chat_ollama(config, status, prompt_text)
            else:
                raise RuntimeError("No supported local AI provider is active.")
        except Exception as exc:
            self._last_status = self._status_with_runtime_error(status, str(exc))
            raise

        self._last_status = self._status_with_runtime_error(status, "")
        return response

    def stream_chat(
        self,
        config: AIConfig,
        prompt_text: str,
        on_chunk: Callable[[str], None] | None = None,
    ) -> str:
        status = self.probe(config)
        if not status.connected:
            raise RuntimeError(status.error_text or status.status_text)

        try:
            if status.provider == "lm_studio":
                response = self._stream_lm_studio(config, status, prompt_text, on_chunk)
            elif status.provider == "ollama":
                response = self._stream_ollama(config, status, prompt_text, on_chunk)
            else:
                raise RuntimeError("No supported local AI provider is active.")
        except Exception as exc:
            self._last_status = self._status_with_runtime_error(status, str(exc))
            raise

        self._last_status = self._status_with_runtime_error(status, "")
        return response

    def _probe_explicit_base_url(self, config: AIConfig) -> AIBackendStatus:
        explicit = config.base_url.strip()
        if not explicit:
            return self._last_status

        if "11434" in explicit or "/api/tags" in explicit:
            return self._probe_ollama(config, self._normalize_ollama_base_url(explicit))

        lm_status = self._probe_lm_studio(
            config,
            [self._normalize_lm_studio_base_url(explicit)],
        )
        if lm_status.connected:
            return lm_status

        if config.allow_ollama_fallback:
            return self._probe_ollama(config, self._normalize_ollama_base_url(explicit))
        return lm_status

    def _probe_lm_studio(self, config: AIConfig, candidate_urls: list[str]) -> AIBackendStatus:
        errors: list[str] = []
        for candidate in candidate_urls:
            try:
                payload = self._json_request(f"{candidate}/models", timeout=4)
            except RuntimeError as exc:
                errors.append(f"{candidate}: {exc}")
                continue

            models = [
                str(item.get("id", "")).strip()
                for item in payload.get("data", [])
                if str(item.get("id", "")).strip()
            ]
            if not models:
                message = (
                    "LM Studio is reachable, but no model is loaded. "
                    "Open LM Studio and load a local model."
                )
                return AIBackendStatus(
                    connected=False,
                    provider="lm_studio",
                    provider_display_name="LM Studio",
                    base_url=candidate,
                    model_name="",
                    available_models=[],
                    status_text=message,
                    error_text=message,
                )

            selected_model = self._choose_model(config.model_name, models)
            return AIBackendStatus(
                connected=True,
                provider="lm_studio",
                provider_display_name="LM Studio",
                base_url=candidate,
                model_name=selected_model,
                available_models=models,
                status_text=f"Connected to LM Studio with {selected_model}.",
                error_text="",
            )

        message = (
            "LM Studio is not reachable on the configured local server URLs."
            if errors
            else "LM Studio is not configured."
        )
        detail = " | ".join(errors[-2:]) if errors else message
        return AIBackendStatus(
            connected=False,
            provider="lm_studio",
            provider_display_name="LM Studio",
            base_url=candidate_urls[0] if candidate_urls else "",
            model_name="",
            available_models=[],
            status_text=message,
            error_text=detail,
        )

    def _probe_ollama(self, config: AIConfig, base_url: str) -> AIBackendStatus:
        try:
            payload = self._json_request(f"{base_url}/api/tags", timeout=4)
        except RuntimeError as exc:
            message = "Ollama is not reachable on the configured local server URL."
            return AIBackendStatus(
                connected=False,
                provider="ollama",
                provider_display_name="Ollama",
                base_url=base_url,
                model_name="",
                available_models=[],
                status_text=message,
                error_text=str(exc),
            )

        models = [
            str(item.get("name", "")).strip()
            for item in payload.get("models", [])
            if str(item.get("name", "")).strip()
        ]
        if not models:
            message = "Ollama is reachable, but no local models are installed."
            return AIBackendStatus(
                connected=False,
                provider="ollama",
                provider_display_name="Ollama",
                base_url=base_url,
                model_name="",
                available_models=[],
                status_text=message,
                error_text=message,
            )

        selected_model = self._choose_model(config.model_name, models)
        return AIBackendStatus(
            connected=True,
            provider="ollama",
            provider_display_name="Ollama",
            base_url=base_url,
            model_name=selected_model,
            available_models=models,
            status_text=f"Connected to Ollama with {selected_model}.",
            error_text="",
        )

    def _chat_lm_studio(
        self,
        config: AIConfig,
        status: AIBackendStatus,
        prompt_text: str,
    ) -> str:
        payload = {
            "model": status.model_name,
            "messages": [
                {"role": "system", "content": config.system_prompt},
                {"role": "user", "content": prompt_text},
            ],
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "stream": False,
        }
        raw = self._json_request(
            f"{status.base_url}/chat/completions",
            method="POST",
            payload=payload,
            timeout=max(10, config.request_timeout_seconds),
        )
        choices = raw.get("choices") or []
        if not choices:
            raise RuntimeError("LM Studio returned no choices.")
        message = choices[0].get("message") or {}
        content = str(message.get("content", "")).strip()
        if not content:
            raise RuntimeError("LM Studio returned an empty response.")
        self.logger.info("LM Studio response received with model '%s'.", status.model_name)
        return content

    def _chat_ollama(
        self,
        config: AIConfig,
        status: AIBackendStatus,
        prompt_text: str,
    ) -> str:
        payload = {
            "model": status.model_name,
            "messages": [
                {"role": "system", "content": config.system_prompt},
                {"role": "user", "content": prompt_text},
            ],
            "stream": False,
            "options": {
                "temperature": config.temperature,
                "num_predict": config.max_tokens,
            },
        }
        raw = self._json_request(
            f"{status.base_url}/api/chat",
            method="POST",
            payload=payload,
            timeout=max(10, config.request_timeout_seconds),
        )
        message = raw.get("message") or {}
        content = str(message.get("content", "")).strip()
        if not content:
            raise RuntimeError("Ollama returned an empty response.")
        self.logger.info("Ollama response received with model '%s'.", status.model_name)
        return content

    def _stream_lm_studio(
        self,
        config: AIConfig,
        status: AIBackendStatus,
        prompt_text: str,
        on_chunk,
    ) -> str:
        payload = {
            "model": status.model_name,
            "messages": [
                {"role": "system", "content": config.system_prompt},
                {"role": "user", "content": prompt_text},
            ],
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "stream": True,
        }
        chunks: list[str] = []
        for line in self._stream_request_lines(
            f"{status.base_url}/chat/completions",
            payload,
            timeout=max(10, config.request_timeout_seconds),
        ):
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            event = json.loads(data)
            choices = event.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}
            chunk = str(delta.get("content", ""))
            if not chunk:
                continue
            chunks.append(chunk)
            if on_chunk is not None:
                on_chunk(chunk)
        content = "".join(chunks).strip()
        if not content:
            raise RuntimeError("LM Studio returned an empty streamed response.")
        self.logger.info("LM Studio streaming response received with model '%s'.", status.model_name)
        return content

    def _stream_ollama(
        self,
        config: AIConfig,
        status: AIBackendStatus,
        prompt_text: str,
        on_chunk,
    ) -> str:
        payload = {
            "model": status.model_name,
            "messages": [
                {"role": "system", "content": config.system_prompt},
                {"role": "user", "content": prompt_text},
            ],
            "stream": True,
            "options": {
                "temperature": config.temperature,
                "num_predict": config.max_tokens,
            },
        }
        chunks: list[str] = []
        for line in self._stream_request_lines(
            f"{status.base_url}/api/chat",
            payload,
            timeout=max(10, config.request_timeout_seconds),
        ):
            if not line:
                continue
            event = json.loads(line)
            message = event.get("message") or {}
            chunk = str(message.get("content", ""))
            if chunk:
                chunks.append(chunk)
                if on_chunk is not None:
                    on_chunk(chunk)
            if event.get("done"):
                break
        content = "".join(chunks).strip()
        if not content:
            raise RuntimeError("Ollama returned an empty streamed response.")
        self.logger.info("Ollama streaming response received with model '%s'.", status.model_name)
        return content

    def _candidate_lm_studio_urls(self, config: AIConfig) -> list[str]:
        candidates: list[str] = []
        for value in [
            config.base_url,
            config.lm_studio_base_url,
            config.lm_studio_alt_base_url,
        ]:
            normalized = self._normalize_lm_studio_base_url(value)
            for variant in self._lm_studio_url_variants(normalized):
                if variant and variant not in candidates:
                    candidates.append(variant)
        return candidates

    def _lm_studio_url_variants(self, base_url: str) -> list[str]:
        normalized = (base_url or "").strip().rstrip("/")
        if not normalized:
            normalized = "http://127.0.0.1:1234/v1"
        variants = [normalized]
        if "127.0.0.1" in normalized:
            variants.append(normalized.replace("127.0.0.1", "localhost"))
        elif "localhost" in normalized:
            variants.append(normalized.replace("localhost", "127.0.0.1"))
        return variants

    def _normalize_lm_studio_base_url(self, base_url: str) -> str:
        normalized = (base_url or "").strip().rstrip("/")
        if not normalized:
            return "http://127.0.0.1:1234/v1"
        if normalized.endswith("/chat/completions") or normalized.endswith("/models"):
            normalized = normalized.rsplit("/", 1)[0]
        if normalized.endswith("/api/v1"):
            return normalized
        if normalized.endswith("/v1"):
            return normalized
        if normalized.endswith("/api"):
            return f"{normalized}/v1"
        return f"{normalized}/v1"

    def _choose_model(self, preferred_model: str, models: list[str]) -> str:
        preferred = preferred_model.strip()
        if preferred:
            preferred_lower = preferred.casefold()
            for model_name in models:
                if model_name.casefold() == preferred_lower:
                    return model_name

            # Be forgiving about provider-specific naming differences such as
            # registry prefixes, suffixes, tags, or capitalization.
            for model_name in models:
                lowered_name = model_name.casefold()
                if preferred_lower in lowered_name or lowered_name in preferred_lower:
                    return model_name

        ranked_preferences = [
            ":latest",
            "llama3.1",
            "llama3",
            "llama",
            "qwen",
            "mistral",
            "deepseek",
        ]
        lowered = [(model_name, model_name.casefold()) for model_name in models]

        for needle in ranked_preferences:
            for model_name, lowered_name in lowered:
                if needle in lowered_name and "coder" not in lowered_name:
                    return model_name

        for needle in ranked_preferences:
            for model_name, lowered_name in lowered:
                if needle in lowered_name:
                    return model_name

        return models[0]

    def _normalize_ollama_base_url(self, base_url: str) -> str:
        normalized = (base_url or "http://127.0.0.1:11434").strip().rstrip("/")
        if normalized.endswith("/api/chat") or normalized.endswith("/api/tags"):
            normalized = normalized.rsplit("/", 2)[0]
        return normalized

    def _json_request(
        self,
        url: str,
        method: str = "GET",
        payload: dict | None = None,
        timeout: int = 8,
    ) -> dict:
        last_error: RuntimeError | None = None
        for attempt in range(1, 3):
            body = None
            headers = {"Accept": "application/json"}
            if payload is not None:
                body = json.dumps(payload).encode("utf-8")
                headers["Content-Type"] = "application/json"

            req = request.Request(url, data=body, headers=headers, method=method)
            try:
                with request.urlopen(req, timeout=timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            except error.HTTPError as exc:
                try:
                    raw_error = exc.read().decode("utf-8", errors="replace")
                except Exception:
                    raw_error = str(exc)
                raise RuntimeError(
                    f"HTTP {exc.code} from {url}: {raw_error}"
                ) from exc
            except error.URLError as exc:
                last_error = RuntimeError(f"Unable to reach {url}: {exc.reason}")
            except TimeoutError:
                last_error = RuntimeError(f"Timed out while contacting {url}.")
            except json.JSONDecodeError:
                last_error = RuntimeError(f"{url} returned invalid JSON.")

            if attempt == 1 and last_error is not None:
                self.logger.debug("Retrying %s after transient provider error: %s", url, last_error)

        assert last_error is not None
        raise last_error

    def _stream_request_lines(
        self,
        url: str,
        payload: dict,
        timeout: int,
    ):
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        req = request.Request(url, data=body, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=timeout) as response:
                for raw_line in response:
                    yield raw_line.decode("utf-8", errors="replace").strip()
        except error.HTTPError as exc:
            try:
                raw_error = exc.read().decode("utf-8", errors="replace")
            except Exception:
                raw_error = str(exc)
            raise RuntimeError(
                f"HTTP {exc.code} from {url}: {raw_error}"
            ) from exc
        except error.URLError as exc:
            raise RuntimeError(f"Unable to reach {url}: {exc.reason}") from exc
        except TimeoutError as exc:
            raise RuntimeError(f"Timed out while contacting {url}.") from exc

    def _status_with_runtime_error(
        self,
        status: AIBackendStatus,
        error_text: str,
    ) -> AIBackendStatus:
        if not error_text:
            return AIBackendStatus(
                connected=status.connected,
                provider=status.provider,
                provider_display_name=status.provider_display_name,
                base_url=status.base_url,
                model_name=status.model_name,
                available_models=list(status.available_models),
                status_text=status.status_text,
                error_text="",
            )
        return AIBackendStatus(
            connected=False,
            provider=status.provider,
            provider_display_name=status.provider_display_name,
            base_url=status.base_url,
            model_name=status.model_name,
            available_models=list(status.available_models),
            status_text=f"{status.provider_display_name} error: {error_text}",
            error_text=error_text,
        )
