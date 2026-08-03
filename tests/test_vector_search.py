from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from backend.app import main
from backend.app.database import SessionLocal
from backend.app.embedding import FakeEmbeddingProvider
from backend.app.models import Document, DocumentChunk
from backend.app.vector_search import (
    MAX_TOP_K,
    VectorSearchError,
    search_similar_chunks,
)


client = TestClient(main.app)


@pytest.fixture(autouse=True)
def clear_documents():
    with SessionLocal() as db:
        db.query(Document).delete()
        db.commit()
    yield
    with SessionLocal() as db:
        db.query(Document).delete()
        db.commit()


def _add_document(db, status="ready", chunks=None):
    document = Document(
        id=uuid4(),
        filename=f"{status}.pdf",
        storage_path=f"/tmp/{uuid4()}.pdf",
        file_size_bytes=1,
        status=status,
    )
    db.add(document)
    db.flush()
    for page_number, chunk_index, content, embedding in chunks or []:
        db.add(
            DocumentChunk(
                document_id=document.id,
                page_number=page_number,
                chunk_index=chunk_index,
                content=content,
                embedding=embedding,
            )
        )
    db.commit()
    return document


def _embedding(text):
    return FakeEmbeddingProvider().embed_texts([text])[0]


def test_search_returns_ready_chunks_in_similarity_order():
    with SessionLocal() as db:
        ready = _add_document(
            db,
            chunks=[
                (1, 0, "python", _embedding("python")),
                (1, 1, "unrelated text", _embedding("unrelated text")),
            ],
        )
        _add_document(
            db,
            status="processing",
            chunks=[(1, 0, "python", _embedding("python"))],
        )
        ready_id = ready.id

        results = search_similar_chunks(db, "python", top_k=2)

    assert len(results) == 2
    assert results[0]["document_id"] == str(ready_id)
    assert results[0]["content"] == "python"
    assert results[0]["similarity_score"] >= results[1]["similarity_score"]


def test_search_returns_expected_result_fields_and_score():
    with SessionLocal() as db:
        document = _add_document(
            db,
            chunks=[(3, 2, "FastAPI route", _embedding("FastAPI route"))],
        )
        document_id = document.id

        result = search_similar_chunks(db, "FastAPI route")[0]

    assert result["document_id"] == str(document_id)
    assert result["page_number"] == 3
    assert result["chunk_index"] == 2
    assert result["content"] == "FastAPI route"
    assert result["similarity_score"] == pytest.approx(1.0, abs=1e-5)


def test_search_excludes_chunks_without_embedding():
    with SessionLocal() as db:
        _add_document(
            db,
            chunks=[(1, 0, "no vector", None)],
        )

        assert search_similar_chunks(db, "no vector") == []


def test_search_respects_top_k():
    with SessionLocal() as db:
        _add_document(
            db,
            chunks=[
                (1, index, f"text {index}", _embedding(f"text {index}"))
                for index in range(3)
            ],
        )

        results = search_similar_chunks(db, "text", top_k=2)

    assert len(results) == 2


def test_search_returns_empty_list_when_no_ready_match_exists():
    with SessionLocal() as db:
        assert search_similar_chunks(db, "nothing") == []


@pytest.mark.parametrize(
    ("query", "top_k"),
    [
        ("", 5),
        ("   ", 5),
        ("query", 0),
        ("query", -1),
        ("query", MAX_TOP_K + 1),
    ],
)
def test_search_rejects_invalid_inputs(query, top_k):
    with SessionLocal() as db:
        with pytest.raises(ValueError):
            search_similar_chunks(db, query, top_k)


def test_search_database_error_becomes_clear_exception():
    class FailingSession:
        def execute(self, statement):
            raise SQLAlchemyError("database unavailable")

    with pytest.raises(VectorSearchError, match="Vector search failed"):
        search_similar_chunks(FailingSession(), "query")


def test_search_endpoint_returns_items():
    with SessionLocal() as db:
        document = _add_document(
            db,
            chunks=[(1, 0, "Python", _embedding("Python"))],
        )
        document_id = document.id

    response = client.post("/search", json={"query": "Python", "top_k": 1})

    assert response.status_code == 200
    assert response.json()["items"][0]["document_id"] == str(document_id)


def test_search_endpoint_rejects_empty_query():
    response = client.post("/search", json={"query": "   "})

    assert response.status_code == 400
    assert response.json() == {"detail": "query cannot be empty"}
