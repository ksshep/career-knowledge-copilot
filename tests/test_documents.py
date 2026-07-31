from fastapi.testclient import TestClient
import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select
from uuid import UUID

from backend.app import main
from backend.app.database import SessionLocal, get_db
from backend.app.models import Document


client = TestClient(main.app)


@pytest.fixture(autouse=True)
def clear_documents():
    main.DOCUMENTS.clear()
    with SessionLocal() as db:
        db.query(Document).delete()
        db.commit()
    yield
    main.DOCUMENTS.clear()
    with SessionLocal() as db:
        db.query(Document).delete()
        db.commit()


def test_upload_pdf_saves_file(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOADS_DIR", tmp_path)
    file_content = b"%PDF-1.4\nSample PDF content"

    response = client.post(
        "/documents",
        files={"file": ("resume.pdf", file_content, "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "resume.pdf"
    assert body["size_bytes"] == len(file_content)
    assert body["status"] == "processing"
    assert (tmp_path / f"{body['id']}_resume.pdf").read_bytes() == file_content


def test_upload_rejects_non_pdf_file():
    response = client.post(
        "/documents",
        files={"file": ("notes.txt", b"not a PDF", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Only PDF files are allowed."}


def test_upload_rejects_file_larger_than_20_mb():
    oversized_content = b"%PDF-1.4\n" + b"0" * (20 * 1024 * 1024)

    response = client.post(
        "/documents",
        files={"file": ("large.pdf", oversized_content, "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "File size must not exceed 20 MB."}


def test_list_documents_is_empty_without_uploads():
    response = client.get("/documents")

    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_uploaded_pdf_appears_in_document_list(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOADS_DIR", tmp_path)
    upload_response = client.post(
        "/documents",
        files={"file": ("resume.pdf", b"%PDF-1.4", "application/pdf")},
    )

    document_id = upload_response.json()["id"]
    response = client.get("/documents")

    assert response.status_code == 200
    assert response.json()["items"][0]["id"] == document_id


def test_document_list_contains_metadata(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOADS_DIR", tmp_path)
    file_content = b"%PDF-1.4\nMetadata test"
    client.post(
        "/documents",
        files={"file": ("portfolio.pdf", file_content, "application/pdf")},
    )

    item = client.get("/documents").json()["items"][0]

    assert item["filename"] == "portfolio.pdf"
    assert item["size_bytes"] == len(file_content)
    assert item["status"] == "processing"


def test_upload_writes_document_to_database(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOADS_DIR", tmp_path)
    file_content = b"%PDF-1.4\nDatabase test"

    response = client.post(
        "/documents",
        files={"file": ("database.pdf", file_content, "application/pdf")},
    )

    document_id = UUID(response.json()["id"])
    with SessionLocal() as db:
        document = db.scalar(select(Document).where(Document.id == document_id))

    assert document is not None
    assert document.filename == "database.pdf"
    assert document.storage_path.endswith(f"{document_id}_database.pdf")
    assert document.file_size_bytes == len(file_content)
    assert document.status == "processing"


def test_upload_cleans_file_when_database_commit_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOADS_DIR", tmp_path)

    class FailingSession:
        def add(self, document):
            pass

        def commit(self):
            raise SQLAlchemyError("simulated database failure")

        def rollback(self):
            self.rolled_back = True

        def close(self):
            pass

    def failing_db():
        yield FailingSession()

    main.app.dependency_overrides[get_db] = failing_db
    try:
        response = client.post(
            "/documents",
            files={"file": ("failed.pdf", b"%PDF-1.4", "application/pdf")},
        )
    finally:
        main.app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 500
    assert response.json() == {"detail": "Failed to save document metadata."}
    assert list(tmp_path.iterdir()) == []
    assert main.DOCUMENTS == {}
