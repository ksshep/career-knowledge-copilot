from fastapi import FastAPI
from pydantic import BaseModel


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
