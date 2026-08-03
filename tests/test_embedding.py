import pytest

from backend.app.embedding import (
    EMBEDDING_DIMENSION,
    EmbeddingOutputError,
    EmbeddingProvider,
    EmbeddingInputError,
    FakeEmbeddingProvider,
)


def test_single_text_generates_one_vector():
    vectors = FakeEmbeddingProvider().embed_texts(["Python"])

    assert len(vectors) == 1
    assert len(vectors[0]) == EMBEDDING_DIMENSION


def test_multiple_texts_generate_matching_number_of_vectors():
    vectors = FakeEmbeddingProvider().embed_texts(["Python", "FastAPI", "PostgreSQL"])

    assert len(vectors) == 3
    assert all(len(vector) == EMBEDDING_DIMENSION for vector in vectors)


def test_vector_dimension_is_fixed():
    provider = FakeEmbeddingProvider()

    vectors = provider.embed_texts(["one", "two"])

    assert {len(vector) for vector in vectors} == {EMBEDDING_DIMENSION}


def test_same_text_returns_same_vector():
    provider = FakeEmbeddingProvider()

    first = provider.embed_texts(["same text"])
    second = provider.embed_texts(["same text"])

    assert first == second


def test_different_texts_do_not_return_identical_vectors():
    vectors = FakeEmbeddingProvider().embed_texts(["first text", "second text"])

    assert vectors[0] != vectors[1]


def test_empty_list_returns_empty_list():
    assert FakeEmbeddingProvider().embed_texts([]) == []


def test_empty_text_raises_clear_input_error():
    with pytest.raises(EmbeddingInputError, match="empty or whitespace"):
        FakeEmbeddingProvider().embed_texts(["   "])


def test_non_string_input_raises_clear_input_error():
    with pytest.raises(EmbeddingInputError, match="must be a string"):
        FakeEmbeddingProvider().embed_texts([123])


def test_output_count_mismatch_is_detected():
    class BrokenProvider(EmbeddingProvider):
        def _embed_texts(self, texts):
            return []

    with pytest.raises(EmbeddingOutputError, match="output count"):
        BrokenProvider().embed_texts(["one text"])
