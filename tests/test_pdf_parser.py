from pathlib import Path

import pytest

from backend.app.pdf_parser import PdfParserError, extract_pdf_pages


def _write_pdf(path: Path, page_texts: list[str]) -> None:
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"",
    ]
    page_object_numbers = []
    content_object_numbers = []
    next_object_number = 3

    for text in page_texts:
        page_object_numbers.append(next_object_number)
        content_object_numbers.append(next_object_number + 1)
        next_object_number += 2

    font_object_number = next_object_number
    objects[1] = (
        f"<< /Type /Pages /Kids [{ ' '.join(f'{number} 0 R' for number in page_object_numbers)}] "
        f"/Count {len(page_texts)} >>"
    ).encode()

    for text, page_object_number, content_object_number in zip(
        page_texts, page_object_numbers, content_object_numbers
    ):
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] "
            f"/Resources << /Font << /F1 {font_object_number} 0 R >> >> "
            f"/Contents {content_object_number} 0 R >>".encode()
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
    for object_number, obj in enumerate(objects, start=1):
        offsets.append(len(data))
        data.extend(f"{object_number} 0 obj\n".encode())
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


def test_extracts_text_from_pdf_pages(tmp_path):
    pdf_path = tmp_path / "text.pdf"
    _write_pdf(pdf_path, ["First page", "Second page"])

    pages = extract_pdf_pages(pdf_path)

    assert pages == [
        {"page_number": 1, "text": "First page"},
        {"page_number": 2, "text": "Second page"},
    ]


def test_page_numbers_start_at_one(tmp_path):
    pdf_path = tmp_path / "numbered.pdf"
    _write_pdf(pdf_path, ["One", "Two", "Three"])

    pages = extract_pdf_pages(pdf_path)

    assert [page["page_number"] for page in pages] == [1, 2, 3]


def test_ignores_blank_pages_without_renumbering(tmp_path):
    pdf_path = tmp_path / "mixed.pdf"
    _write_pdf(pdf_path, ["First page", "   ", "Third page"])

    pages = extract_pdf_pages(pdf_path)

    assert pages == [
        {"page_number": 1, "text": "First page"},
        {"page_number": 3, "text": "Third page"},
    ]


def test_blank_pdf_raises_no_text_error(tmp_path):
    pdf_path = tmp_path / "blank.pdf"
    _write_pdf(pdf_path, ["", ""])

    with pytest.raises(PdfParserError, match="no extractable text"):
        extract_pdf_pages(pdf_path)


def test_corrupt_pdf_raises_read_error(tmp_path):
    pdf_path = tmp_path / "corrupt.pdf"
    pdf_path.write_bytes(b"this is not a PDF")

    with pytest.raises(PdfParserError, match="Unable to read PDF"):
        extract_pdf_pages(pdf_path)
