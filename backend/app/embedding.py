from __future__ import annotations

import hashlib
import os
from abc import ABC, abstractmethod

import httpx


EMBEDDING_DIMENSION = 8


class EmbeddingError(Exception):
    """Base error for embedding input and output failures."""


class EmbeddingConfigError(EmbeddingError):
    """Raised when the environment cannot configure an embedding provider."""


class EmbeddingInputError(EmbeddingError, ValueError):
    """Raised when embedding input is invalid."""


class EmbeddingOutputError(EmbeddingError):
    """Raised when a provider returns an invalid result."""


class EmbeddingProvider(ABC):
    """Common contract and validation for text embedding providers."""

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self._validate_inputs(texts)
        vectors = self._embed_texts(texts)
        self._validate_outputs(texts, vectors)
        return vectors

    @abstractmethod
    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate vectors for already validated input text."""

    @staticmethod
    def _validate_inputs(texts: list[str]) -> None:
        if not isinstance(texts, list):
            raise EmbeddingInputError("texts must be a list")
        for index, text in enumerate(texts):
            if not isinstance(text, str):
                raise EmbeddingInputError(
                    f"texts[{index}] must be a string"
                )
            if not text.strip():
                raise EmbeddingInputError(
                    f"texts[{index}] cannot be empty or whitespace"
                )

    @staticmethod
    def _validate_outputs(
        texts: list[str], vectors: list[list[float]]
    ) -> None:
        if not isinstance(vectors, list) or len(vectors) != len(texts):
            raise EmbeddingOutputError(
                "embedding output count must match input text count"
            )
        for index, vector in enumerate(vectors):
            if not isinstance(vector, list):
                raise EmbeddingOutputError(f"embedding[{index}] must be a list")
            if len(vector) != EMBEDDING_DIMENSION:
                raise EmbeddingOutputError(
                    f"embedding[{index}] must have dimension "
                    f"{EMBEDDING_DIMENSION}"
                )
            if any(
                not isinstance(value, (int, float)) or isinstance(value, bool)
                for value in vector
            ):
                raise EmbeddingOutputError(
                    f"embedding[{index}] must contain only numbers"
                )


class FakeEmbeddingProvider(EmbeddingProvider):
    """Generate deterministic local vectors without network access."""

    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vectors.append(self._embed_one(text))
        return vectors

    @staticmethod
    def _embed_one(text: str) -> list[float]:
        vector: list[float] = []
        text_digest = hashlib.sha256(text.encode("utf-8")).digest()
        for index in range(EMBEDDING_DIMENSION):
            dimension_digest = hashlib.sha256(
                text_digest + index.to_bytes(2, byteorder="big")
            ).digest()
            integer = int.from_bytes(dimension_digest[:8], byteorder="big")
            normalized = integer / ((1 << 64) - 1)
            vector.append((normalized * 2) - 1)
        return vector


class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    """Embedding client for providers exposing the common embeddings API."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: float,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not isinstance(api_key, str) or not api_key.strip():
            raise EmbeddingConfigError("EMBEDDING_API_KEY is required")
        if not isinstance(base_url, str) or not base_url.strip():
            raise EmbeddingConfigError("EMBEDDING_BASE_URL is required")
        if not isinstance(model, str) or not model.strip():
            raise EmbeddingConfigError("EMBEDDING_MODEL is required")
        if timeout_seconds <= 0:
            raise EmbeddingConfigError(
                "EMBEDDING_TIMEOUT_SECONDS must be greater than 0"
            )

        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    @classmethod
    def from_env(cls) -> "OpenAICompatibleEmbeddingProvider":
        values = {name: os.getenv(name) for name in _EMBEDDING_ENV_NAMES}
        missing = [
            name for name, value in values.items()
            if not value or not value.strip()
        ]
        if missing:
            raise EmbeddingConfigError(
                f"Missing embedding configuration: {', '.join(missing)}"
            )

        try:
            timeout_seconds = float(values["EMBEDDING_TIMEOUT_SECONDS"])
        except (TypeError, ValueError) as exc:
            raise EmbeddingConfigError(
                "EMBEDDING_TIMEOUT_SECONDS must be a number"
            ) from exc

        return cls(
            api_key=values["EMBEDDING_API_KEY"],
            base_url=values["EMBEDDING_BASE_URL"],
            model=values["EMBEDDING_MODEL"],
            timeout_seconds=timeout_seconds,
        )

    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        payload = {"model": self._model, "input": texts}
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
                    f"{self._base_url}/embeddings",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise EmbeddingError("Embedding provider request timed out") from exc
        except httpx.HTTPStatusError as exc:
            raise EmbeddingError(
                "Embedding provider returned an HTTP error"
            ) from exc
        except httpx.RequestError as exc:
            raise EmbeddingError("Embedding provider request failed") from exc

        try:
            body = response.json()
            data = body["data"]
        except (ValueError, TypeError, KeyError) as exc:
            raise EmbeddingOutputError(
                "Embedding provider returned an invalid response"
            ) from exc

        if not isinstance(data, list) or len(data) != len(texts):
            raise EmbeddingOutputError(
                "embedding output count must match input text count"
            )

        vectors: list[list[float] | None] = [None] * len(texts)
        expected_dimension: int | None = None
        for item in data:
            if not isinstance(item, dict):
                raise EmbeddingOutputError("embedding data items must be objects")

            index = item.get("index")
            vector = item.get("embedding")
            if (
                not isinstance(index, int)
                or isinstance(index, bool)
                or index < 0
                or index >= len(texts)
            ):
                raise EmbeddingOutputError("embedding index is invalid")
            if vectors[index] is not None:
                raise EmbeddingOutputError("embedding indexes must be unique")
            if not isinstance(vector, list):
                raise EmbeddingOutputError("embedding must be a list")
            if any(
                not isinstance(value, (int, float)) or isinstance(value, bool)
                for value in vector
            ):
                raise EmbeddingOutputError("embedding must contain only numbers")
            if expected_dimension is None:
                expected_dimension = len(vector)
            elif len(vector) != expected_dimension:
                raise EmbeddingOutputError(
                    "embedding vectors must have a consistent dimension"
                )
            vectors[index] = vector

        if any(vector is None for vector in vectors):
            raise EmbeddingOutputError("embedding indexes are incomplete")
        return [vector for vector in vectors if vector is not None]


_EMBEDDING_ENV_NAMES = (
    "EMBEDDING_API_KEY",
    "EMBEDDING_BASE_URL",
    "EMBEDDING_MODEL",
    "EMBEDDING_TIMEOUT_SECONDS",
)
