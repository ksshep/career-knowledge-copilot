from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .database import SessionLocal
from .embedding import EMBEDDING_DIMENSION, EmbeddingError, FakeEmbeddingProvider
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
            page_records = []
            chunk_records = []
            for page in pages:
                page_number = int(page["page_number"])
                page_text = str(page["text"])
                page_records.append((page_number, page_text))
                for content in split_text_into_chunks(page_text):
                    chunk_records.append((page_number, content))

            embeddings = FakeEmbeddingProvider().embed_texts(
                [content for _, content in chunk_records]
            )
            if len(embeddings) != len(chunk_records):
                raise EmbeddingError(
                    "embedding output count must match chunk count"
                )
            if any(len(vector) != EMBEDDING_DIMENSION for vector in embeddings):
                raise EmbeddingError(
                    f"embedding dimension must be {EMBEDDING_DIMENSION}"
                )
        except EmbeddingError as exc:
            db.rollback()
            _mark_failed(db, document, str(exc))
            return
        except PdfParserError as exc:
            db.rollback()
            _mark_failed(db, document, str(exc))
            return
        except Exception:
            db.rollback()
            _mark_failed(db, document, "Unable to process document.")
            return

        _delete_existing_pages(db, document.id)
        _delete_existing_chunks(db, document.id)
        for page_number, page_text in page_records:
            db.add(
                DocumentPage(
                    document_id=document.id,
                    page_number=page_number,
                    text=page_text,
                )
            )
        for chunk_index, ((page_number, content), embedding) in enumerate(
            zip(chunk_records, embeddings)
        ):
            db.add(
                DocumentChunk(
                    document_id=document.id,
                    page_number=page_number,
                    chunk_index=chunk_index,
                    content=content,
                    embedding=embedding,
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


def _delete_existing_chunks(db: Session, document_id: UUID) -> None:
    db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))


def _mark_failed(db: Session, document: Document, error_message: str) -> None:
    _delete_existing_pages(db, document.id)
    _delete_existing_chunks(db, document.id)
    document.status = "failed"
    document.error_message = error_message
    _commit_status(db)


def _commit_status(db: Session) -> None:
    """Commit a status update and roll back if the database rejects it."""
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
