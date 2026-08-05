from __future__ import annotations

import argparse

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from .database import SessionLocal
from .embedding import EMBEDDING_DIMENSION, EmbeddingError, EmbeddingProvider
from .models import DocumentChunk
from .provider_factory import get_embedding_provider


def reembed_documents(
    batch_size: int = 32,
    *,
    provider: EmbeddingProvider | None = None,
) -> dict[str, int]:
    """Generate vectors for chunks without embeddings, one committed batch at a time."""
    if not isinstance(batch_size, int) or isinstance(batch_size, bool) or batch_size <= 0:
        raise ValueError("batch_size must be greater than 0")

    embedding_provider = provider or get_embedding_provider()
    generated = 0
    failed = 0

    with SessionLocal() as db:
        total = db.scalar(select(func.count()).select_from(DocumentChunk)) or 0
        while True:
            chunks = db.scalars(
                select(DocumentChunk)
                .where(DocumentChunk.embedding.is_(None))
                .order_by(DocumentChunk.created_at, DocumentChunk.id)
                .limit(batch_size)
            ).all()
            if not chunks:
                break

            try:
                vectors = embedding_provider.embed_texts(
                    [chunk.content for chunk in chunks]
                )
                if len(vectors) != len(chunks):
                    raise EmbeddingError(
                        "embedding output count must match chunk count"
                    )
                if any(len(vector) != EMBEDDING_DIMENSION for vector in vectors):
                    raise EmbeddingError(
                        f"embedding dimension must be {EMBEDDING_DIMENSION}"
                    )
                for chunk, vector in zip(chunks, vectors):
                    chunk.embedding = vector
                db.commit()
                generated += len(chunks)
            except EmbeddingError:
                db.rollback()
                failed += len(chunks)
                raise
            except SQLAlchemyError as exc:
                db.rollback()
                failed += len(chunks)
                raise RuntimeError("Failed to save regenerated embeddings.") from exc

    return {"total": total, "generated": generated, "failed": failed}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Regenerate missing DocumentChunk embeddings."
    )
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()
    result = reembed_documents(args.batch_size)
    print(f"total={result['total']}")
    print(f"generated={result['generated']}")
    print(f"failed={result['failed']}")
    print(f"dimension={EMBEDDING_DIMENSION}")


if __name__ == "__main__":
    main()
