from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod


EMBEDDING_DIMENSION = 8


class EmbeddingError(Exception):
    """Base error for embedding input and output failures."""


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
