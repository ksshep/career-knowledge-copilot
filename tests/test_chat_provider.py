import json

import httpx
import pytest

from backend.app.chat_provider import (
    ChatProviderConfigError,
    ChatProviderError,
    FakeChatProvider,
    OpenAICompatibleChatProvider,
)


def _provider(handler):
    return OpenAICompatibleChatProvider(
        api_key="test-secret",
        base_url="https://provider.example.com/v1/",
        model="test-model",
        timeout_seconds=3,
        transport=httpx.MockTransport(handler),
    )


def test_compatible_provider_extracts_assistant_content_and_sends_request():
    captured = {}

    def handler(request):
        captured["url"] = str(request.url)
        captured["headers"] = request.headers
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "model answer"}}]},
        )

    answer = _provider(handler).generate("system rules", "user context")

    assert answer == "model answer"
    assert captured["url"] == "https://provider.example.com/v1/chat/completions"
    assert captured["headers"]["authorization"] == "Bearer test-secret"
    assert captured["body"] == {
        "model": "test-model",
        "messages": [
            {"role": "system", "content": "system rules"},
            {"role": "user", "content": "user context"},
        ],
        "temperature": 0.2,
    }


@pytest.mark.parametrize("status_code", [401, 500])
def test_http_errors_become_chat_provider_error(status_code):
    def handler(request):
        return httpx.Response(status_code, json={"error": "internal details"})

    with pytest.raises(ChatProviderError, match="HTTP error"):
        _provider(handler).generate("system", "user")


def test_timeout_becomes_chat_provider_error():
    def handler(request):
        raise httpx.ReadTimeout("timed out")

    with pytest.raises(ChatProviderError, match="timed out"):
        _provider(handler).generate("system", "user")


def test_network_error_becomes_chat_provider_error():
    def handler(request):
        raise httpx.ConnectError("connection failed")

    with pytest.raises(ChatProviderError, match="request failed"):
        _provider(handler).generate("system", "user")


@pytest.mark.parametrize(
    "body",
    [{}, {"choices": []}, {"choices": [{"message": {}}]}, {"choices": [{"message": {"content": ""}}]}],
)
def test_invalid_response_structure_becomes_chat_provider_error(body):
    def handler(request):
        return httpx.Response(200, json=body)

    with pytest.raises(ChatProviderError, match="invalid response|empty answer"):
        _provider(handler).generate("system", "user")


def test_missing_environment_values_raise_configuration_error(monkeypatch):
    for name in ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL", "LLM_TIMEOUT_SECONDS"):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(ChatProviderConfigError, match="Missing LLM configuration"):
        OpenAICompatibleChatProvider.from_env()


def test_invalid_timeout_environment_value_raises_configuration_error(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "key")
    monkeypatch.setenv("LLM_BASE_URL", "https://provider.example.com/v1")
    monkeypatch.setenv("LLM_MODEL", "model")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "not-a-number")

    with pytest.raises(ChatProviderConfigError, match="must be a number"):
        OpenAICompatibleChatProvider.from_env()


def test_fake_provider_remains_deterministic():
    provider = FakeChatProvider()
    assert provider.generate("system", "user") == "根据提供的资料，这是一个模拟回答。"
    with pytest.raises(ChatProviderError):
        provider.generate("", "user")
