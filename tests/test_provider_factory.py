import pytest

from backend.app.embedding import (
    EmbeddingConfigError,
    FakeEmbeddingProvider,
    OpenAICompatibleEmbeddingProvider,
)
from backend.app.provider_factory import get_embedding_provider


def test_missing_provider_defaults_to_fake(monkeypatch):
    monkeypatch.delenv("EMBEDDING_PROVIDER", raising=False)

    assert isinstance(get_embedding_provider(), FakeEmbeddingProvider)


def test_fake_provider_value_returns_fake(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "fake")

    assert isinstance(get_embedding_provider(), FakeEmbeddingProvider)


def test_compatible_provider_value_returns_compatible_provider(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "compatible")
    monkeypatch.setenv("EMBEDDING_API_KEY", "key")
    monkeypatch.setenv("EMBEDDING_BASE_URL", "https://provider.example.com/v1")
    monkeypatch.setenv("EMBEDDING_MODEL", "model")
    monkeypatch.setenv("EMBEDDING_TIMEOUT_SECONDS", "30")

    assert isinstance(
        get_embedding_provider(), OpenAICompatibleEmbeddingProvider
    )


def test_unsupported_provider_value_raises_clear_error(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "unknown")

    with pytest.raises(EmbeddingConfigError, match="either 'fake' or 'compatible'"):
        get_embedding_provider()


def test_compatible_provider_missing_api_configuration_raises_clear_error(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "compatible")
    for name in (
        "EMBEDDING_API_KEY",
        "EMBEDDING_BASE_URL",
        "EMBEDDING_MODEL",
        "EMBEDDING_TIMEOUT_SECONDS",
    ):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(EmbeddingConfigError, match="Missing embedding configuration"):
        get_embedding_provider()
