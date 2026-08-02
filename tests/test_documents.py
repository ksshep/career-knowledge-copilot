from fastapi.testclient import TestClient
import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select
from uuid import UUID, uuid4

from backend.app import document_processor, main
from backend.app.database import SessionLocal, get_db
from backend.app.document_processor import process_document
from backend.app.models import Document, DocumentChunk, DocumentPage


client = TestClient(main.app)


@pytest.fixture(autouse=True)
def clear_documents(monkeypatch):
    # Endpoint tests focus on upload/transaction behavior; processor tests call
    # process_document directly so they can assert each final status reliably.
    monkeypatch.setattr(main, "process_document", lambda document_id: None)
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


def _write_pdf(path, page_texts):
    """Write a tiny text PDF without adding a test-only PDF dependency."""
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b""]
    page_numbers = []
    content_numbers = []
    next_number = 3
    for _ in page_texts:
        page_numbers.append(next_number)
        content_numbers.append(next_number + 1)
        next_number += 2

    font_number = next_number
    objects[1] = (
        f"<< /Type /Pages /Kids [{ ' '.join(f'{n} 0 R' for n in page_numbers)}] "
        f"/Count {len(page_texts)} >>"
    ).encode()
    for text, page_number, content_number in zip(
        page_texts, page_numbers, content_numbers
    ):
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] "
            f"/Resources << /Font << /F1 {font_number} 0 R >> >> "
            f"/Contents {content_number} 0 R >>".encode()
        )
        stream = f"BT /F1 18 Tf 30 250 Td ({text}) Tj ET".encode()
        objects.append(
            f"<< /Length {len(stream)} >>\nstream\n".encode()
            + stream
            + b"\nendstream"
        )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    data = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(data))
        data.extend(f"{number} 0 obj\n".encode())
        data.extend(obj)
        data.extend(b"\nendobj\n")
    xref_offset = len(data)
    data.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    data.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        data.extend(f"{offset:010d} 00000 n \n".encode())
    data.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode()
    )
    path.write_bytes(data)


def _create_document(db, path, filename="processor.pdf"):
    document = Document(
        id=uuid4(),
        filename=filename,
        storage_path=str(path),
        file_size_bytes=path.stat().st_size,
        status="processing",
    )
    db.add(document)
    db.commit()
    return document


def test_upload_registers_background_processor(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOADS_DIR", tmp_path)
    calls = []
    monkeypatch.setattr(main, "process_document", lambda document_id: calls.append(document_id))

    response = client.post(
        "/documents",
        files={"file": ("queued.pdf", b"%PDF-1.4", "application/pdf")},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "processing"
    assert calls == [UUID(response.json()["id"])]


def test_process_document_marks_text_pdf_ready(tmp_path):
    pdf_path = tmp_path / "ready.pdf"
    _write_pdf(pdf_path, ["Resume text"])
    with SessionLocal() as db:
        document = _create_document(db, pdf_path)
        document_id = document.id

    process_document(document_id)

    with SessionLocal() as db:
        saved = db.get(Document, document_id)
        assert saved.status == "ready"
        assert saved.error_message is None
    assert pdf_path.exists()


def test_process_document_saves_pages_and_chunks(tmp_path):
    pdf_path = tmp_path / "chunks.pdf"
    first_text = "First page text " * 45
    second_text = "Second page text " * 45
    _write_pdf(pdf_path, [first_text, second_text])
    with SessionLocal() as db:
        document = _create_document(db, pdf_path)
        document_id = document.id

    process_document(document_id)

    with SessionLocal() as db:
        saved = db.get(Document, document_id)
        pages = db.scalars(
            select(DocumentPage)
            .where(DocumentPage.document_id == document_id)
            .order_by(DocumentPage.page_number)
        ).all()
        chunks = db.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        ).all()

        assert saved.status == "ready"
        assert [page.page_number for page in pages] == [1, 2]
        assert pages[0].text.strip() == " ".join(first_text.split())
        assert pages[1].text.strip() == " ".join(second_text.split())
        assert len(chunks) > 2
        assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
        assert {chunk.page_number for chunk in chunks} == {1, 2}
        assert all(chunk.content.strip() for chunk in chunks)
        assert all(len(chunk.content) <= 500 for chunk in chunks)
        assert any(
            chunk.page_number == 1 and "First page text" in chunk.content
            for chunk in chunks
        )
        assert any(
            chunk.page_number == 2 and "Second page text" in chunk.content
            for chunk in chunks
        )


def test_reprocessing_replaces_old_chunks_without_duplicates(tmp_path):
    pdf_path = tmp_path / "repeat.pdf"
    _write_pdf(pdf_path, ["Repeatable text " * 45, "Second page " * 45])
    with SessionLocal() as db:
        document = _create_document(db, pdf_path)
        document_id = document.id

    process_document(document_id)
    with SessionLocal() as db:
        first_ids = [
            chunk.id
            for chunk in db.scalars(
                select(DocumentChunk)
                .where(DocumentChunk.document_id == document_id)
                .order_by(DocumentChunk.chunk_index)
            )
        ]

    process_document(document_id)
    with SessionLocal() as db:
        chunks = db.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        ).all()

    assert len(chunks) == len(first_ids)
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
    assert {chunk.id for chunk in chunks}.isdisjoint(first_ids)


def test_process_document_skips_blank_page_and_preserves_page_number(tmp_path):
    pdf_path = tmp_path / "mixed.pdf"
    _write_pdf(pdf_path, ["Page one", "   "])
    with SessionLocal() as db:
        document = _create_document(db, pdf_path)
        document_id = document.id

    process_document(document_id)

    with SessionLocal() as db:
        saved = db.get(Document, document_id)
        pages = db.scalars(
            select(DocumentPage)
            .where(DocumentPage.document_id == document_id)
            .order_by(DocumentPage.page_number)
        ).all()
        assert saved.status == "ready"
        assert [(page.page_number, page.text) for page in pages] == [
            (1, "Page one")
        ]
    assert pdf_path.exists()


def test_process_document_marks_blank_pdf_failed(tmp_path):
    pdf_path = tmp_path / "failed.pdf"
    _write_pdf(pdf_path, [""])
    with SessionLocal() as db:
        document = _create_document(db, pdf_path)
        document_id = document.id

    process_document(document_id)

    with SessionLocal() as db:
        saved = db.get(Document, document_id)
        assert saved.status == "failed"
    assert saved.error_message
    assert pdf_path.exists()


def test_failed_processing_leaves_no_pages_or_chunks(tmp_path):
    pdf_path = tmp_path / "failed_with_old_data.pdf"
    _write_pdf(pdf_path, [""])
    with SessionLocal() as db:
        document = _create_document(db, pdf_path)
        db.add(
            DocumentPage(
                document_id=document.id,
                page_number=1,
                text="Old page",
            )
        )
        db.add(
            DocumentChunk(
                document_id=document.id,
                page_number=1,
                chunk_index=0,
                content="Old chunk",
            )
        )
        db.commit()
        document_id = document.id

    process_document(document_id)

    with SessionLocal() as db:
        saved = db.get(Document, document_id)
        assert saved.status == "failed"
        assert db.scalars(
            select(DocumentPage).where(DocumentPage.document_id == document_id)
        ).all() == []
        assert db.scalars(
            select(DocumentChunk).where(DocumentChunk.document_id == document_id)
        ).all() == []


def test_process_document_marks_corrupt_pdf_failed(tmp_path):
    pdf_path = tmp_path / "corrupt.pdf"
    pdf_path.write_bytes(b"not a PDF")
    with SessionLocal() as db:
        document = _create_document(db, pdf_path)
        document_id = document.id

    process_document(document_id)

    with SessionLocal() as db:
        saved = db.get(Document, document_id)
        assert saved.status == "failed"
        assert "Unable to read PDF" in saved.error_message
    assert pdf_path.exists()


def test_process_document_missing_document_is_safe():
    process_document(uuid4())


def test_process_document_rolls_back_on_database_error(monkeypatch):
    class FakeDocument:
        id = uuid4()
        storage_path = "unused.pdf"
        status = "processing"
        error_message = None

    class FailingSession:
        def __init__(self):
            self.document = FakeDocument()
            self.rollback_called = False
            self.closed = False

        def get(self, model, document_id):
            return self.document

        def execute(self, statement):
            return None

        def add(self, page):
            pass

        def commit(self):
            raise SQLAlchemyError("simulated status update failure")

        def rollback(self):
            self.rollback_called = True

        def close(self):
            self.closed = True

    session = FailingSession()
    monkeypatch.setattr(document_processor, "SessionLocal", lambda: session)
    monkeypatch.setattr(
        document_processor,
        "extract_pdf_pages",
        lambda path: [{"page_number": 1, "text": "text"}],
    )

    document_processor.process_document(uuid4())

    assert session.rollback_called is True
    assert session.closed is True


def test_delete_document_cascades_page_text(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOADS_DIR", tmp_path)
    pdf_path = tmp_path / "cascade.pdf"
    _write_pdf(pdf_path, ["Page one"])
    with SessionLocal() as db:
        document = _create_document(db, pdf_path, "cascade.pdf")
        db.add(
            DocumentPage(
                document_id=document.id,
                page_number=1,
                text="Page one",
            )
        )
        db.commit()
        document_id = document.id

    response = client.delete(f"/documents/{document_id}")

    assert response.status_code == 204
    with SessionLocal() as db:
        assert db.scalars(
            select(DocumentPage).where(DocumentPage.document_id == document_id)
        ).all() == []


def test_delete_document_cascades_chunks(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOADS_DIR", tmp_path)
    pdf_path = tmp_path / "cascade_chunks.pdf"
    _write_pdf(pdf_path, ["Page one"])
    with SessionLocal() as db:
        document = _create_document(db, pdf_path, "cascade_chunks.pdf")
        db.add(
            DocumentChunk(
                document_id=document.id,
                page_number=1,
                chunk_index=0,
                content="Page one",
            )
        )
        db.commit()
        document_id = document.id

    response = client.delete(f"/documents/{document_id}")

    assert response.status_code == 204
    with SessionLocal() as db:
        assert db.scalars(
            select(DocumentChunk).where(DocumentChunk.document_id == document_id)
        ).all() == []


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
