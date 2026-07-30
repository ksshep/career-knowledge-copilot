、# Career Knowledge Copilot

Career Knowledge Copilot 是一个面向大学生的求职资料知识库助手。它帮助用户上传岗位 JD、面试资料和项目材料 PDF，并根据这些资料回答问题。每个有依据的回答都会列出文件名和页码，方便用户核对原文。

## 当前阶段

项目已完成最小 FastAPI 后端骨架，当前包含 `GET /health` 和对应的自动化测试。PDF、数据库、RAG、Vue 和 Docker 功能将按 MVP 任务逐步实现。整体技术栈为 Python、FastAPI、PostgreSQL、pgvector、Vue 3 和 Docker Compose。

## 当前可运行功能

启动后端：

```bash
source .venv/Scripts/activate
python -m uvicorn backend.app.main:app --reload
```

打开接口文档：

```text
http://127.0.0.1:8000/docs
```

健康检查接口：

```text
GET http://127.0.0.1:8000/health
```

运行测试：

```bash
python -m pytest -q
```

## MVP 能做什么

- 上传一个文字型 PDF（单文件不超过 20 MB）。
- 在文档列表中查看处理状态，并删除文档。
- 对已成功处理的资料提问。
- 在回答中查看文件名和页码引用。
- 在同一浏览器中保存并恢复一条基础对话记录。

## 明确不做什么

MVP 不包含登录、OCR、Agent、支付、复杂权限、多人协作或非 PDF 文件支持。扫描件 PDF 因未做 OCR 而不能保证可用。

## 文档导航

| 文件 | 作用 |
| --- | --- |
| [docs/PRD.md](docs/PRD.md) | 定义目标用户、用户问题、MVP 范围、非目标和验收标准，回答“为什么做、做什么”。 |
| [docs/user-flow.md](docs/user-flow.md) | 描述上传、删除、提问、引用核对和异常时的完整操作路径，回答“用户如何使用”。 |
| [docs/technical-design.md](docs/technical-design.md) | 说明 Vue、FastAPI、PostgreSQL、pgvector、大模型与 Docker Compose 如何协作，包含 API、数据流和最小表结构，回答“如何实现”。 |
| [docs/test-cases.md](docs/test-cases.md) | 提供 22 条可重复执行的验收用例，回答“如何确认功能正确”。 |

## 建议阅读顺序

零基础开发者建议依次阅读 PRD、用户流程、技术设计和测试用例。先理解用户要完成的事情，再理解系统如何处理数据，最后以测试用例检查实现是否符合预期。

## 未来实现的本地启动目标

实现完成后，项目应支持以下流程：

```bash
docker compose up --build
```

该命令的预期作用是同时启动 Vue 前端、FastAPI 后端和带 pgvector 的 PostgreSQL 数据库。真实模型 API 密钥应配置在不提交 Git 的 `.env` 文件中。
