# Career Knowledge Copilot

Career Knowledge Copilot 是面向大学生求职场景的资料知识库助手。当前项目先完成稳定的文档上传、持久化和 PDF 文本提取基础，后续再接入检索增强问答。

## 当前功能

- `GET /health`：健康检查。
- `POST /chat`：返回模拟聊天回答。
- `POST /documents`：上传不超过 20 MB 的 PDF，保存文件和数据库元数据。
- `GET /documents`：从 PostgreSQL 查询文档列表。
- `DELETE /documents/{id}`：删除文档记录和本地 PDF 文件。
- PDF 后台处理：上传后状态为 `processing`，解析成功变为 `ready`，解析失败变为 `failed`，失败原因保存到 `error_message`。
- `document_pages` 表：持久化每页提取出的文本，服务重启后仍可读取。

当前尚未接入 OCR、Embedding、RAG、LangChain、真实大模型或 Vue 前端。

## 技术栈

- Python、FastAPI
- PostgreSQL、pgvector
- SQLAlchemy、Alembic
- Docker Compose
- pypdf

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
| `alembic/versions/` | 数据库迁移历史 |
| `tests/` | 自动化测试 |
