from pathlib import Path
from uuid import UUID, uuid4

from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .database import get_db
from .chat_provider import (
    ChatProvider,
    ChatProviderError,
    create_chat_provider_from_env,
)
from .document_processor import process_document
from .models import Document
from .rag_context import RAGContextError, build_rag_context
from .vector_search import VectorSearchError, search_similar_chunks


MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024
PROJECT_ROOT = Path(__file__).resolve().parents[2]
UPLOADS_DIR = PROJECT_ROOT / "uploads"
DOCUMENTS: dict[str, dict[str, str | int]] = {}
chat_provider: ChatProvider = create_chat_provider_from_env()


class ChatRequest(BaseModel):
    message: str


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


class AskRequest(BaseModel):
    query: str
    top_k: int = 5


def get_chat_provider() -> ChatProvider:
    """Resolve the provider through configuration without coupling the route to a vendor."""
    return chat_provider


app = FastAPI(
    title="Career Knowledge Copilot",
    description="求职资料知识库助手的后端 API",
    version="0.1.0",
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Return a lightweight readiness response for local checks and deployment probes."""
    return {"status": "ok"}


@app.post("/chat", tags=["chat"])
def chat(request: ChatRequest) -> dict[str, str]:
    return {"reply": f"你问的是：{request.message}"}


@app.post("/search", tags=["search"])
def search_documents(
    request: SearchRequest,
    db: Session = Depends(get_db),
) -> dict[str, list[dict[str, str | int | float]]]:
    try:
        items = search_similar_chunks(db, request.query, request.top_k)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except VectorSearchError:
        raise HTTPException(status_code=500, detail="Vector search failed.")
    return {"items": items}


@app.post("/ask", tags=["ask"])
def ask_documents(
    request: AskRequest,
    db: Session = Depends(get_db),
    provider: ChatProvider = Depends(get_chat_provider),
) -> dict[str, object]:
    try:
        search_results = search_similar_chunks(db, request.query, request.top_k)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except (VectorSearchError, SQLAlchemyError):
        raise HTTPException(status_code=500, detail="Search failed.")

    if not search_results:
        return {
            "answer": "没有找到足够依据",
            "citations": [],
            "has_evidence": False,
        }

    try:
        rag_context = build_rag_context(search_results)
    except RAGContextError:
        raise HTTPException(status_code=500, detail="Failed to build answer context.")

    try:
        answer = provider.generate(
            system_prompt=(
                "你只能依据用户提供的资料回答问题。"
                "资料不足时必须明确说明无法确定，不得编造引用。"
            ),
            user_prompt=rag_context["context"],
        )
    except ChatProviderError as exc:
        raise HTTPException(status_code=500, detail="Chat provider failed.") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Chat provider failed.") from exc

    return {
        "answer": answer,
        "citations": rag_context["citations"],
        "has_evidence": True,
    }


@app.post("/documents", status_code=201, tags=["documents"])
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict[str, str | int]:
    filename = Path(file.filename or "").name
    if file.content_type != "application/pdf" or Path(filename).suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    content = await file.read()
    file_size = len(content)
    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File size must not exceed 20 MB.")

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    document_id = uuid4()
    storage_path = UPLOADS_DIR / f"{document_id}_{filename}"
    storage_path.write_bytes(content)

    document = Document(
        id=document_id,
        filename=filename,
        storage_path=str(storage_path),
        file_size_bytes=file_size,
        status="processing",
    )

    try:
        db.add(document)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        storage_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to save document metadata.",
        )

    background_tasks.add_task(process_document, document.id)
    metadata = {
        "id": str(document.id),
        "filename": filename,
        "size_bytes": file_size,
        "status": "processing",
    }
    DOCUMENTS[str(document.id)] = metadata
    return metadata


@app.get("/documents", tags=["documents"])
def list_documents(
    db: Session = Depends(get_db),
) -> dict[str, list[dict[str, str | int]]]:
    documents = db.scalars(
        select(Document).order_by(Document.created_at.desc())
    ).all()
    return {
        "items": [
            {
                "id": str(document.id),
                "filename": document.filename,
                "size_bytes": document.file_size_bytes,
                "status": document.status,
            }
            for document in documents
        ]
    }


@app.delete("/documents/{document_id}", status_code=204, tags=["documents"])
def delete_document(
    document_id: UUID,
    db: Session = Depends(get_db),
) -> None:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    storage_path = Path(document.storage_path)
    try:
        db.delete(document)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete document.")

    storage_path.unlink(missing_ok=True)
    DOCUMENTS.pop(str(document_id), None)
