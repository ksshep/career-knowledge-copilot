import os

from .embedding import (
    EmbeddingConfigError,
    EmbeddingProvider,
    FakeEmbeddingProvider,
    OpenAICompatibleEmbeddingProvider,
)


def get_embedding_provider() -> EmbeddingProvider:
    """Build the configured embedding provider for the current process."""
    provider_name = (os.getenv("EMBEDDING_PROVIDER") or "fake").strip().lower()
    if provider_name == "fake":
        return FakeEmbeddingProvider()
    if provider_name == "compatible":
        return OpenAICompatibleEmbeddingProvider.from_env()
    raise EmbeddingConfigError(
        "EMBEDDING_PROVIDER must be either 'fake' or 'compatible'"
    )
