from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel


MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024
PROJECT_ROOT = Path(__file__).resolve().parents[2]
UPLOADS_DIR = PROJECT_ROOT / "uploads"


class ChatRequest(BaseModel):
    message: str


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


@app.post("/documents", status_code=201, tags=["documents"])
async def upload_document(file: UploadFile = File(...)) -> dict[str, str | int]:
    filename = Path(file.filename or "").name
    if file.content_type != "application/pdf" or Path(filename).suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    content = await file.read()
    file_size = len(content)
    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File size must not exceed 20 MB.")

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    document_id = str(uuid4())
    storage_path = UPLOADS_DIR / f"{document_id}_{filename}"
    storage_path.write_bytes(content)

    return {
        "id": document_id,
        "filename": filename,
        "size_bytes": file_size,
        "status": "uploaded",
    }
