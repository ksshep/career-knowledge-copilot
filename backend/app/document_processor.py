from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import Document, DocumentPage
from .pdf_parser import PdfParserError, extract_pdf_pages


def process_document(document_id: UUID | str) -> None:
    """Extract a document's PDF text and persist its processing status."""
    db = SessionLocal()
    try:
        document = db.get(Document, document_id)
        if document is None:
            return

        try:
            pages = extract_pdf_pages(document.storage_path)
        except PdfParserError as exc:
            _delete_existing_pages(db, document.id)
            document.status = "failed"
            document.error_message = str(exc)
            _commit_status(db)
            return
        except Exception:
            _delete_existing_pages(db, document.id)
            document.status = "failed"
            document.error_message = "Unable to process PDF text."
            _commit_status(db)
            return

        _delete_existing_pages(db, document.id)
        for page in pages:
            db.add(
                DocumentPage(
                    document_id=document.id,
                    page_number=int(page["page_number"]),
                    text=str(page["text"]),
                )
            )
        document.status = "ready"
        document.error_message = None
        _commit_status(db)
    except SQLAlchemyError:
        db.rollback()
    finally:
        db.close()


def _delete_existing_pages(db: Session, document_id: UUID) -> None:
    db.execute(delete(DocumentPage).where(DocumentPage.document_id == document_id))


def _commit_status(db: Session) -> None:
    """Commit a status update and roll back if the database rejects it."""
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
