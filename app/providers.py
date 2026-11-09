"""Language-model backends. Each one takes a system + user prompt and returns raw text (JSON)."""
from __future__ import annotations

import httpx

from .config import Settings


class ProviderError(RuntimeError):
    """Raised when the model can't be reached or returns an error. The message is shown to the user."""


class LLMProvider:
    name = "base"

    def __init__(self, model: str, timeout: float = 120.0):
        self.model = model
        self.timeout = timeout

    @property
    def label(self) -> str:
        return f"{self.name} · {self.model}"

    async def generate(self, system: str, user: str) -> str:  # pragma: no cover - interface
        raise NotImplementedError

    async def _post(self, url: str, payload: dict, headers: dict | None = None,
                    connect_hint: str = "") -> dict:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload, headers=headers)
        except httpx.ConnectError as exc:
            raise ProviderError(connect_hint or f"Could not connect to {url}.") from exc
        except httpx.TimeoutException as exc:
            raise ProviderError(
                "The model took too long to answer. Try a shorter text or a faster model."
            ) from exc
        if resp.status_code >= 400:
            raise ProviderError(self._error_message(resp))
        return resp.json()

    def _error_message(self, resp: httpx.Response) -> str:
        return f"{self.name} returned an error ({resp.status_code}): {resp.text[:300]}"


class OllamaProvider(LLMProvider):
    """Runs a model on your own machine with Ollama - free and private."""

    name = "ollama"

    def __init__(self, model: str, url: str, timeout: float = 120.0):
        super().__init__(model, timeout)
        self.url = url

    async def generate(self, system: str, user: str) -> str:
        data = await self._post(
            f"{self.url}/api/chat",
            {
                "model": self.model,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.2},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            connect_hint=(
                f"Ollama is not running at {self.url}. Start it with `ollama serve` and run "
                f"`ollama pull {self.model}`, or set LLM_PROVIDER=offline in .env."
            ),
        )
        return data.get("message", {}).get("content", "")

    def _error_message(self, resp: httpx.Response) -> str:
        if resp.status_code == 404:
            return f"Ollama doesn't have the model '{self.model}'. Run `ollama pull {self.model}`."
        return super()._error_message(resp)


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, model: str, api_key: str, timeout: float = 120.0):
        super().__init__(model, timeout)
        self.api_key = api_key

    async def generate(self, system: str, user: str) -> str:
        if not self.api_key:
            raise ProviderError("ANTHROPIC_API_KEY is not set. Add it to your .env file.")
        data = await self._post(
            "https://api.anthropic.com/v1/messages",
            {
                "model": self.model,
                "max_tokens": 2000,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
            headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
        )
        return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, model: str, api_key: str, timeout: float = 120.0):
        super().__init__(model, timeout)
        self.api_key = api_key

    async def generate(self, system: str, user: str) -> str:
        if not self.api_key:
            raise ProviderError("OPENAI_API_KEY is not set. Add it to your .env file.")
        data = await self._post(
            "https://api.openai.com/v1/chat/completions",
            {
                "model": self.model,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
        return data["choices"][0]["message"]["content"]


class OfflineProvider(LLMProvider):
    """No AI model: fixes common mistakes with simple rules (see offline.py). Good for trying the app."""

    name = "offline"

    def __init__(self) -> None:
        super().__init__(model="basic rules")

    async def generate(self, system: str, user: str) -> str:  # not used - Refiner calls offline.py
        raise ProviderError("Offline mode does not call a model.")


def build_provider(settings: Settings) -> LLMProvider:
    p = settings.provider
    if p == "ollama":
        return OllamaProvider(settings.ollama_model, settings.ollama_url, settings.request_timeout)
    if p == "anthropic":
        return AnthropicProvider(settings.anthropic_model, settings.anthropic_api_key, settings.request_timeout)
    if p == "openai":
        return OpenAIProvider(settings.openai_model, settings.openai_api_key, settings.request_timeout)
    if p == "offline":
        return OfflineProvider()
    raise ValueError(f"Unknown LLM_PROVIDER '{p}'. Use ollama, anthropic, openai or offline.")
