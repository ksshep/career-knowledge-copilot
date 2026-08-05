# Career Knowledge Copilot

Career Knowledge Copilot 是面向大学生求职场景的资料知识库助手。当前项目先完成稳定的文档上传、持久化和 PDF 文本提取基础，后续再接入检索增强问答。

## 当前功能

- `GET /health`：健康检查。
- `POST /chat`：返回模拟聊天回答。
- `POST /documents`：上传不超过 20 MB 的 PDF，保存文件和数据库元数据。
- `GET /documents`：从 PostgreSQL 查询文档列表。
- `DELETE /documents/{id}`：删除文档记录和本地 PDF 文件。
- `POST /search`：通过 Embedding Provider 和 pgvector 检索最相似的 ready 文档 Chunk。
- `POST /ask`：检索相关 Chunk、构建受限上下文，并使用 Fake Chat Provider 返回模拟回答和引用。
- Chat Provider：默认使用 Fake Provider；配置通用 LLM 环境变量后可调用 OpenAI-compatible Chat API。
- Embedding Provider：默认使用 Fake Provider；设置 `EMBEDDING_PROVIDER=compatible` 后，文档处理和相似度检索会使用通用兼容 API。
- `rag_context`：将检索结果整理为带文件名、页码和片段编号的有限上下文。
- PDF 后台处理：上传后状态为 `processing`，解析成功变为 `ready`，解析失败变为 `failed`，失败原因保存到 `error_message`。
- `document_pages` 表：持久化每页提取出的文本，服务重启后仍可读取。
- `document_chunks` 表：持久化按页切分后的文本片段，为后续 Embedding 和向量检索准备数据。
- `document_chunks.embedding`：使用 pgvector 保存 Embedding 向量，当前维度为 `1536`，由 `EMBEDDING_DIMENSION` 统一定义。

当前默认使用 Fake Embedding（1536 维）；尚未接入 OCR、真实聊天模型、LangChain 或 Vue 前端。

真实模型配置使用 `.env` 中的 `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL` 和 `LLM_TIMEOUT_SECONDS`。项目不会把这些值写入代码；未配置时继续使用 Fake Provider。

Embedding 配置使用 `.env` 中的 `EMBEDDING_PROVIDER`、`EMBEDDING_API_KEY`、`EMBEDDING_BASE_URL`、`EMBEDDING_MODEL` 和 `EMBEDDING_TIMEOUT_SECONDS`。默认 provider 是 `fake`，不会访问网络；`compatible` 模式使用配置的真实模型。

迁移后可用以下命令为历史 Chunk 生成缺失向量（不会删除 PDF、页面或 Chunk）：

```bash
python -m backend.app.reembed_documents --batch-size 32
```

## 技术栈

- Python、FastAPI
- PostgreSQL、pgvector
- SQLAlchemy、Alembic
- Docker Compose
- pypdf
- pgvector

## 本地启动

在 Git Bash 中进入项目目录：

```bash
cd /e/gz021/code/career-knowledge-copilot
source .venv/Scripts/activate
docker compose up -d db
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8001
```

Swagger 地址：<http://127.0.0.1:8001/docs>

执行数据库迁移：

```bash
alembic upgrade head
```

当前迁移版本为 `0005_change_embedding_dimension`，会将 `document_chunks.embedding` 调整为 `vector(1536)`。升级前会清除旧的 8 维 Fake 向量；降级同样会清除向量后改回 8 维，因此降级会丢失向量数据，但不会删除 Chunk 文本。

检索请求示例：

```json
{
  "query": "Python 项目经验",
  "top_k": 5
}
```

检索结果只包含 `ready` 文档中有 embedding 的 Chunk，并按相似度从高到低返回。

## 运行测试

```bash
python -m pytest -q
git diff --check
```

测试使用独立的 `career_copilot_test` 数据库，不会清理开发数据库中的手动数据。

## 目录说明

| 路径 | 作用 |
| --- | --- |
| `backend/app/main.py` | FastAPI 应用和 HTTP 接口 |
| `backend/app/database.py` | SQLAlchemy Engine、Session 和依赖 |
| `backend/app/models.py` | `Document`、`DocumentPage` 数据模型 |
| `backend/app/pdf_parser.py` | 按页提取 PDF 文本 |
| `backend/app/document_processor.py` | 后台解析并更新文档状态、页面文本 |
| `backend/app/text_splitter.py` | 将页面文本切成带重叠的小段 |
| `backend/app/vector_search.py` | 使用 pgvector 检索相似的文档 Chunk |
| `backend/app/rag_context.py` | 构建发送给模型的受限上下文和引用 |
| `backend/app/chat_provider.py` | 定义聊天模型接口并提供本地 Fake Provider |
| `backend/app/embedding.py` | 定义 Embedding 接口、Fake Provider 和通用 HTTP Provider |
| `backend/app/provider_factory.py` | 根据环境变量创建 Embedding Provider |
| `alembic/versions/` | 数据库迁移历史 |
| `tests/` | 自动化测试 |
