from fastapi.testclient import TestClient

from backend.app import main


client = TestClient(main.app)


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
    assert body["status"] == "uploaded"
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
