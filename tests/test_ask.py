from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from backend.app import main
from backend.app.database import SessionLocal
from backend.app.embedding import FakeEmbeddingProvider
from backend.app.models import Document, DocumentChunk
from backend.app.vector_search import VectorSearchError


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


def _add_ready_document(content="FastAPI and PostgreSQL", page_number=2, chunk_index=1):
    document = Document(
        id=uuid4(),
        filename="project.pdf",
        storage_path=f"/tmp/{uuid4()}.pdf",
        file_size_bytes=1,
        status="ready",
    )
    db = SessionLocal()
    db.add(document)
    db.flush()
    db.add(
        DocumentChunk(
            document_id=document.id,
            page_number=page_number,
            chunk_index=chunk_index,
            content=content,
            embedding=FakeEmbeddingProvider().embed_texts([content])[0],
        )
    )
    db.commit()
    db.close()
    return document


def test_ask_returns_answer_and_citations_for_relevant_document():
    document = _add_ready_document()

    response = client.post("/ask", json={"query": "FastAPI and PostgreSQL"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "根据提供的资料，这是一个模拟回答。"
    assert body["citations"] == [
        {"filename": "project.pdf", "page_number": 2, "chunk_index": 1}
    ]
    assert body["has_evidence"] is True


def test_ask_returns_no_evidence_without_results(monkeypatch):
    provider = main.chat_provider
    called = False

    def fail_if_called(system_prompt, user_prompt):
        nonlocal called
        called = True
        raise AssertionError("provider should not be called")

    monkeypatch.setattr(main, "chat_provider", type("Provider", (), {"generate": fail_if_called})())
    response = client.post("/ask", json={"query": "unknown"})
    monkeypatch.setattr(main, "chat_provider", provider)

    assert response.status_code == 200
    assert response.json() == {
        "answer": "没有找到足够依据",
        "citations": [],
        "has_evidence": False,
    }
    assert called is False


def test_ask_rejects_empty_query():
    response = client.post("/ask", json={"query": "   "})

    assert response.status_code == 400
    assert response.json() == {"detail": "query cannot be empty"}


@pytest.mark.parametrize("error", [VectorSearchError("database unavailable"), SQLAlchemyError("database unavailable")])
def test_ask_returns_clear_database_error(monkeypatch, error):
    def fail_search(db, query, top_k):
        raise error

    monkeypatch.setattr(main, "search_similar_chunks", fail_search)
    response = client.post("/ask", json={"query": "query"})

    assert response.status_code == 500
    assert response.json() == {"detail": "Search failed."}


def test_ask_returns_clear_chat_provider_error(monkeypatch):
    class FailingProvider:
        def generate(self, system_prompt, user_prompt):
            raise RuntimeError("secret provider details")

    _add_ready_document()
    monkeypatch.setattr(main, "chat_provider", FailingProvider())
    response = client.post("/ask", json={"query": "FastAPI"})

    assert response.status_code == 500
    assert response.json() == {"detail": "Chat provider failed."}
