from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .embedding import EmbeddingError, FakeEmbeddingProvider
from .models import Document, DocumentChunk


DEFAULT_TOP_K = 5
MAX_TOP_K = 20


class VectorSearchError(Exception):
    """Raised when vector search cannot complete."""


def search_similar_chunks(
    db: Session,
    query: str,
    top_k: int = DEFAULT_TOP_K,
) -> list[dict[str, str | int | float]]:
    """Return the closest ready document chunks for a query."""
    _validate_search_inputs(query, top_k)

    try:
        query_embedding = FakeEmbeddingProvider().embed_texts([query])[0]
        distance = DocumentChunk.embedding.cosine_distance(query_embedding)
        statement = (
            select(
                DocumentChunk.document_id,
                Document.filename,
                DocumentChunk.page_number,
                DocumentChunk.chunk_index,
                DocumentChunk.content,
                distance.label("distance"),
            )
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(
                Document.status == "ready",
                DocumentChunk.embedding.is_not(None),
            )
            .order_by(distance)
            .limit(top_k)
        )
        rows = db.execute(statement).all()
    except (EmbeddingError, SQLAlchemyError) as exc:
        raise VectorSearchError("Vector search failed.") from exc

    return [
        {
            "document_id": str(row.document_id),
            "filename": row.filename,
            "page_number": row.page_number,
            "chunk_index": row.chunk_index,
            "content": row.content,
            "similarity_score": 1.0 - float(row.distance),
        }
        for row in rows
    ]


def _validate_search_inputs(query: str, top_k: int) -> None:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query cannot be empty")
    if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k <= 0:
        raise ValueError("top_k must be greater than 0")
    if top_k > MAX_TOP_K:
        raise ValueError(f"top_k cannot be greater than {MAX_TOP_K}")
