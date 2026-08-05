from uuid import uuid4

import pytest
from sqlalchemy import select

from backend.app import reembed_documents
from backend.app.database import SessionLocal
from backend.app.embedding import (
    EMBEDDING_DIMENSION,
    EmbeddingError,
    FakeEmbeddingProvider,
)
from backend.app.models import Document, DocumentChunk


@pytest.fixture(autouse=True)
def clear_documents():
    with SessionLocal() as db:
        db.query(Document).delete()
        db.commit()
    yield
    with SessionLocal() as db:
        db.query(Document).delete()
        db.commit()


def _add_chunks(contents):
    with SessionLocal() as db:
        document = Document(
            id=uuid4(),
            filename="reembed.pdf",
            storage_path=f"/tmp/{uuid4()}.pdf",
            file_size_bytes=1,
            status="ready",
        )
        db.add(document)
        db.flush()
        for index, content in enumerate(contents):
            db.add(
                DocumentChunk(
                    document_id=document.id,
                    page_number=1,
                    chunk_index=index,
                    content=content,
                )
            )
        db.commit()
        return document.id


def test_reembed_fills_missing_vectors_in_batches_and_is_repeatable():
    document_id = _add_chunks(["one", "two", "three"])
    provider = FakeEmbeddingProvider()

    first = reembed_documents.reembed_documents(2, provider=provider)
    second = reembed_documents.reembed_documents(2, provider=provider)

    assert first == {"total": 3, "generated": 3, "failed": 0}
    assert second == {"total": 3, "generated": 0, "failed": 0}
    with SessionLocal() as db:
        chunks = db.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        ).all()
        assert all(len(chunk.embedding) == EMBEDDING_DIMENSION for chunk in chunks)


def test_reembed_rolls_back_when_embedding_fails():
    document_id = _add_chunks(["one", "two"])

    class FailingProvider:
        def embed_texts(self, texts):
            raise EmbeddingError("provider failed")

    with pytest.raises(EmbeddingError, match="provider failed"):
        reembed_documents.reembed_documents(provider=FailingProvider())

    with SessionLocal() as db:
        chunks = db.scalars(
            select(DocumentChunk).where(DocumentChunk.document_id == document_id)
        ).all()
        assert all(chunk.embedding is None for chunk in chunks)


def test_reembed_rejects_wrong_dimension():
    _add_chunks(["one"])

    class WrongDimensionProvider:
        def embed_texts(self, texts):
            return [[0.1] * (EMBEDDING_DIMENSION - 1) for _ in texts]

    with pytest.raises(EmbeddingError, match="dimension"):
        reembed_documents.reembed_documents(provider=WrongDimensionProvider())
