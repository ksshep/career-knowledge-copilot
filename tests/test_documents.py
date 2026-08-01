from fastapi.testclient import TestClient
import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select
from uuid import UUID, uuid4

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
        files={"file": ("pytest_resume.pdf", file_content, "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "pytest_resume.pdf"
    assert body["size_bytes"] == len(file_content)
    assert body["status"] == "processing"
    assert (tmp_path / f"{body['id']}_pytest_resume.pdf").read_bytes() == file_content


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
        files={"file": ("pytest_resume.pdf", b"%PDF-1.4", "application/pdf")},
    )

    document_id = upload_response.json()["id"]
    main.DOCUMENTS.clear()
    response = client.get("/documents")

    assert response.status_code == 200
    assert response.json()["items"][0]["id"] == document_id


def test_document_list_contains_metadata(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOADS_DIR", tmp_path)
    file_content = b"%PDF-1.4\nMetadata test"
    client.post(
        "/documents",
        files={"file": ("pytest_portfolio.pdf", file_content, "application/pdf")},
    )

    item = client.get("/documents").json()["items"][0]

    assert item["filename"] == "pytest_portfolio.pdf"
    assert item["size_bytes"] == len(file_content)
    assert item["status"] == "processing"


def test_upload_writes_document_to_database(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOADS_DIR", tmp_path)
    file_content = b"%PDF-1.4\nDatabase test"

    response = client.post(
        "/documents",
        files={"file": ("pytest_database.pdf", file_content, "application/pdf")},
    )

    document_id = UUID(response.json()["id"])
    with SessionLocal() as db:
        document = db.scalar(select(Document).where(Document.id == document_id))

    assert document is not None
    assert document.filename == "pytest_database.pdf"
    assert document.storage_path.endswith(f"{document_id}_pytest_database.pdf")
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


def test_delete_existing_document_returns_no_content(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOADS_DIR", tmp_path)
    upload_response = client.post(
        "/documents",
        files={"file": ("pytest_delete.pdf", b"%PDF-1.4", "application/pdf")},
    )

    response = client.delete(f"/documents/{upload_response.json()['id']}")

    assert response.status_code == 204
    assert response.content == b""


def test_delete_removes_database_record(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOADS_DIR", tmp_path)
    upload_response = client.post(
        "/documents",
        files={"file": ("pytest_database_delete.pdf", b"%PDF-1.4", "application/pdf")},
    )
    document_id = UUID(upload_response.json()["id"])

    response = client.delete(f"/documents/{document_id}")
    with SessionLocal() as db:
        document = db.get(Document, document_id)

    assert response.status_code == 204
    assert document is None


def test_delete_removes_local_pdf(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOADS_DIR", tmp_path)
    upload_response = client.post(
        "/documents",
        files={"file": ("pytest_file_delete.pdf", b"%PDF-1.4", "application/pdf")},
    )
    document_id = upload_response.json()["id"]
    storage_path = tmp_path / f"{document_id}_pytest_file_delete.pdf"

    response = client.delete(f"/documents/{document_id}")

    assert response.status_code == 204
    assert not storage_path.exists()


def test_delete_unknown_document_returns_not_found():
    response = client.delete(f"/documents/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Document not found."}


def test_delete_same_document_twice_returns_not_found(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOADS_DIR", tmp_path)
    upload_response = client.post(
        "/documents",
        files={"file": ("pytest_twice.pdf", b"%PDF-1.4", "application/pdf")},
    )
    document_id = upload_response.json()["id"]

    first_response = client.delete(f"/documents/{document_id}")
    second_response = client.delete(f"/documents/{document_id}")

    assert first_response.status_code == 204
    assert second_response.status_code == 404


def test_delete_succeeds_when_local_file_is_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOADS_DIR", tmp_path)
    upload_response = client.post(
        "/documents",
        files={"file": ("pytest_missing_file.pdf", b"%PDF-1.4", "application/pdf")},
    )
    document_id = upload_response.json()["id"]
    (tmp_path / f"{document_id}_pytest_missing_file.pdf").unlink()

    response = client.delete(f"/documents/{document_id}")

    assert response.status_code == 204
