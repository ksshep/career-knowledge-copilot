from abc import ABC, abstractmethod
import os

import httpx


class ChatProviderError(Exception):
    """Raised when a chat provider cannot generate an answer."""


class ChatProviderConfigError(ChatProviderError):
    """Raised when the environment cannot configure a chat provider."""


class ChatProvider(ABC):
    """Small interface shared by fake and future real chat providers."""

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate an answer from a system instruction and user prompt."""


class FakeChatProvider(ChatProvider):
    """Deterministic, network-free provider for local development and tests."""

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        if not isinstance(system_prompt, str) or not system_prompt.strip():
            raise ChatProviderError("system_prompt cannot be empty")
        if not isinstance(user_prompt, str) or not user_prompt.strip():
            raise ChatProviderError("user_prompt cannot be empty")
        return "根据提供的资料，这是一个模拟回答。"


class OpenAICompatibleChatProvider(ChatProvider):
    """Chat provider for services exposing the common chat completions API."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: float,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not api_key.strip():
            raise ChatProviderConfigError("LLM_API_KEY is required")
        if not base_url.strip():
            raise ChatProviderConfigError("LLM_BASE_URL is required")
        if not model.strip():
            raise ChatProviderConfigError("LLM_MODEL is required")
        if timeout_seconds <= 0:
            raise ChatProviderConfigError("LLM_TIMEOUT_SECONDS must be greater than 0")

        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    @classmethod
    def from_env(cls) -> "OpenAICompatibleChatProvider":
        values = {name: os.getenv(name) for name in _LLM_ENV_NAMES}
        missing = [name for name, value in values.items() if not value or not value.strip()]
        if missing:
            raise ChatProviderConfigError(
                f"Missing LLM configuration: {', '.join(missing)}"
            )

        try:
            timeout_seconds = float(values["LLM_TIMEOUT_SECONDS"])
        except (TypeError, ValueError) as exc:
            raise ChatProviderConfigError(
                "LLM_TIMEOUT_SECONDS must be a number"
            ) from exc

        return cls(
            api_key=values["LLM_API_KEY"],
            base_url=values["LLM_BASE_URL"],
            model=values["LLM_MODEL"],
            timeout_seconds=timeout_seconds,
        )

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        if not isinstance(system_prompt, str) or not system_prompt.strip():
            raise ChatProviderError("system_prompt cannot be empty")
        if not isinstance(user_prompt, str) or not user_prompt.strip():
            raise ChatProviderError("user_prompt cannot be empty")

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(
                timeout=self._timeout_seconds,
                transport=self._transport,
            ) as client:
                response = client.post(
                    f"{self._base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise ChatProviderError("Chat provider request timed out") from exc
        except httpx.HTTPStatusError as exc:
            raise ChatProviderError("Chat provider returned an HTTP error") from exc
        except httpx.RequestError as exc:
            raise ChatProviderError("Chat provider request failed") from exc

        try:
            body = response.json()
            content = body["choices"][0]["message"]["content"]
        except (ValueError, TypeError, KeyError, IndexError) as exc:
            raise ChatProviderError("Chat provider returned an invalid response") from exc

        if not isinstance(content, str) or not content.strip():
            raise ChatProviderError("Chat provider returned an empty answer")
        return content


_LLM_ENV_NAMES = (
    "LLM_API_KEY",
    "LLM_BASE_URL",
    "LLM_MODEL",
    "LLM_TIMEOUT_SECONDS",
)


def create_chat_provider_from_env() -> ChatProvider:
    """Use Fake locally, or configure the generic HTTP provider when requested."""
    if not any(os.getenv(name) for name in _LLM_ENV_NAMES):
        return FakeChatProvider()
    return OpenAICompatibleChatProvider.from_env()
