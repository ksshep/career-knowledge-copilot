from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from .database import SessionLocal
from .models import Document
from .pdf_parser import PdfParserError, extract_pdf_pages


def process_document(document_id: UUID | str) -> None:
    """Extract a document's PDF text and persist its processing status."""
    db = SessionLocal()
    try:
        document = db.get(Document, document_id)
        if document is None:
            return

        try:
            extract_pdf_pages(document.storage_path)
        except PdfParserError as exc:
            document.status = "failed"
            document.error_message = str(exc)
            _commit_status(db)
            return
        except Exception:
            document.status = "failed"
            document.error_message = "Unable to process PDF text."
            _commit_status(db)
            return

        document.status = "ready"
        document.error_message = None
        _commit_status(db)
    except SQLAlchemyError:
        db.rollback()
    finally:
        db.close()


def _commit_status(db) -> None:
    """Commit a status update and roll back if the database rejects it."""
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
