from abc import ABC, abstractmethod


class ChatProviderError(Exception):
    """Raised when a chat provider cannot generate an answer."""


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
