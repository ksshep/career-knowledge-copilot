from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError


class PdfParserError(Exception):
    """Raised when a PDF cannot be read or has no extractable text."""


def extract_pdf_pages(pdf_path: str | Path) -> list[dict[str, int | str]]:
    path = Path(pdf_path)

    try:
        reader = PdfReader(str(path))
        pages = [
            {
                "page_number": page_number,
                "text": page.extract_text() or "",
            }
            for page_number, page in enumerate(reader.pages, start=1)
        ]
    except (OSError, PdfReadError, ValueError) as exc:
        raise PdfParserError(f"Unable to read PDF: {path}") from exc

    if not pages or not any(page["text"].strip() for page in pages):
        raise PdfParserError(f"PDF contains no extractable text: {path}")

    return pages
