from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import Document, DocumentChunk, DocumentPage
from .pdf_parser import PdfParserError, extract_pdf_pages
from .text_splitter import split_text_into_chunks


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
            _delete_existing_chunks(db, document.id)
            document.status = "failed"
            document.error_message = str(exc)
            _commit_status(db)
            return
        except Exception:
            _delete_existing_pages(db, document.id)
            _delete_existing_chunks(db, document.id)
            document.status = "failed"
            document.error_message = "Unable to process PDF text."
            _commit_status(db)
            return

        _delete_existing_pages(db, document.id)
        _delete_existing_chunks(db, document.id)
        chunk_index = 0
        for page in pages:
            page_number = int(page["page_number"])
            page_text = str(page["text"])
            db.add(
                DocumentPage(
                    document_id=document.id,
                    page_number=page_number,
                    text=page_text,
                )
            )
            for content in split_text_into_chunks(page_text):
                db.add(
                    DocumentChunk(
                        document_id=document.id,
                        page_number=page_number,
                        chunk_index=chunk_index,
                        content=content,
                    )
                )
                chunk_index += 1
        document.status = "ready"
        document.error_message = None
        _commit_status(db)
    except SQLAlchemyError:
        db.rollback()
    finally:
        db.close()


def _delete_existing_pages(db: Session, document_id: UUID) -> None:
    db.execute(delete(DocumentPage).where(DocumentPage.document_id == document_id))


def _delete_existing_chunks(db: Session, document_id: UUID) -> None:
    db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))


def _commit_status(db: Session) -> None:
    """Commit a status update and roll back if the database rejects it."""
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
