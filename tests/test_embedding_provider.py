import json

import httpx
import pytest

from backend.app.embedding import (
    EMBEDDING_DIMENSION,
    EmbeddingConfigError,
    EmbeddingError,
    EmbeddingOutputError,
    OpenAICompatibleEmbeddingProvider,
)


def _provider(handler):
    return OpenAICompatibleEmbeddingProvider(
        api_key="embedding-secret",
        base_url="https://provider.example.com/v1/",
        model="embedding-model",
        timeout_seconds=3,
        transport=httpx.MockTransport(handler),
    )


def test_provider_sends_batch_and_returns_vectors_in_index_order():
    captured = {}

    def handler(request):
        captured["url"] = str(request.url)
        captured["headers"] = request.headers
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": 1, "embedding": [0.3] * EMBEDDING_DIMENSION},
                    {"index": 0, "embedding": [0.1] * EMBEDDING_DIMENSION},
                ]
            },
        )

    vectors = _provider(handler).embed_texts(["first", "second"])

    assert vectors == [
        [0.1] * EMBEDDING_DIMENSION,
        [0.3] * EMBEDDING_DIMENSION,
    ]
    assert captured["url"] == "https://provider.example.com/v1/embeddings"
    assert captured["headers"]["authorization"] == "Bearer embedding-secret"
    assert captured["body"] == {
        "model": "embedding-model",
        "input": ["first", "second"],
    }


def test_empty_batch_does_not_make_a_request():
    def fail_if_called(request):
        raise AssertionError("empty input should not call the provider")

    assert _provider(fail_if_called).embed_texts([]) == []


def test_inconsistent_vector_dimensions_raise_error():
    def handler(request):
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": 0, "embedding": [0.1] * EMBEDDING_DIMENSION},
                    {"index": 1, "embedding": [0.2] * (EMBEDDING_DIMENSION - 1)},
                ]
            },
        )

    with pytest.raises(EmbeddingOutputError, match="consistent dimension"):
        _provider(handler).embed_texts(["first", "second"])


@pytest.mark.parametrize(
    "body",
    [{}, {"data": []}, {"data": [{"index": 0}]}, {"data": [{"index": 0, "embedding": ["x"]}]}],
)
def test_invalid_response_structure_raises_error(body):
    def handler(request):
        return httpx.Response(200, json=body)

    with pytest.raises(EmbeddingError):
        _provider(handler).embed_texts(["text"])


@pytest.mark.parametrize("status_code", [401, 500])
def test_http_errors_raise_embedding_error(status_code):
    def handler(request):
        return httpx.Response(status_code, json={"error": "internal details"})

    with pytest.raises(EmbeddingError, match="HTTP error"):
        _provider(handler).embed_texts(["text"])


def test_timeout_raises_embedding_error():
    def handler(request):
        raise httpx.ReadTimeout("timed out")

    with pytest.raises(EmbeddingError, match="timed out"):
        _provider(handler).embed_texts(["text"])


def test_missing_environment_values_raise_configuration_error(monkeypatch):
    for name in (
        "EMBEDDING_API_KEY",
        "EMBEDDING_BASE_URL",
        "EMBEDDING_MODEL",
        "EMBEDDING_TIMEOUT_SECONDS",
    ):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(EmbeddingConfigError, match="Missing embedding configuration"):
        OpenAICompatibleEmbeddingProvider.from_env()


def test_invalid_timeout_environment_value_raises_configuration_error(monkeypatch):
    monkeypatch.setenv("EMBEDDING_API_KEY", "key")
    monkeypatch.setenv("EMBEDDING_BASE_URL", "https://provider.example.com/v1")
    monkeypatch.setenv("EMBEDDING_MODEL", "model")
    monkeypatch.setenv("EMBEDDING_TIMEOUT_SECONDS", "invalid")

    with pytest.raises(EmbeddingConfigError, match="must be a number"):
        OpenAICompatibleEmbeddingProvider.from_env()
