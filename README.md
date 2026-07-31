# Career Knowledge Copilot

Career Knowledge Copilot 是一个面向大学生的求职资料知识库助手。项目最终将支持上传岗位 JD、面试资料和项目材料 PDF，并根据资料回答问题、给出文件名和页码引用。

## 当前阶段

项目目前处于 FastAPI 后端学习与骨架搭建阶段，已经实现了四个可运行接口：

- `GET /health`：返回服务健康状态，用于确认后端已正常启动。
- `POST /chat`：接收 JSON 中的 `message`，返回包含该消息的模拟回复。
- `POST /documents`：接收一个不超过 20 MB 的 PDF，保存到项目根目录的 `uploads/`，并将元数据写入 PostgreSQL，初始状态为 `processing`。
- `GET /documents`：返回当前进程内存中已经上传的文档元数据列表。

当前尚未接入大模型、PDF 解析、数据库、向量检索、Vue 前端或 Docker Compose。这些是后续 MVP 的实现目标，而不是已完成的功能。

## 本地启动

在 Git Bash 中进入项目目录后执行：

```bash
source .venv/Scripts/activate
python -m uvicorn backend.app.main:app --reload
```

启动成功后打开 Swagger 接口文档：

```text
http://127.0.0.1:8000/docs
```

## 当前接口

### 健康检查

```text
GET /health
```

返回：

```json
{
  "status": "ok"
}
```

### 模拟聊天

```text
POST /chat
```

请求：

```json
{
  "message": "什么是 Python？"
}
```

返回：

```json
{
  "reply": "你问的是：什么是 Python？"
}
```

`message` 是必填字段。缺失时 FastAPI 自动返回 `422`，说明请求 JSON 不符合接口要求。

### 基础 PDF 上传

```text
POST /documents
```

以 `multipart/form-data` 提交名为 `file` 的 PDF 文件。接口只接受 MIME 类型为 `application/pdf` 且文件名以 `.pdf` 结尾的文件，单文件最大 20 MB。

成功时返回 `201`：

```json
{
  "id": "文件 UUID",
  "filename": "resume.pdf",
  "size_bytes": 1024,
  "status": "uploaded"
}
```

### 文档列表

```text
GET /documents
```

返回当前进程内存中的文档元数据。服务重启后该列表会清空，正式版本需要替换为数据库。

```json
{
  "items": [
    {
      "id": "文件 UUID",
      "filename": "resume.pdf",
      "size_bytes": 1024,
      "status": "uploaded"
    }
  ]
}
```

## 运行测试

另开一个 Git Bash 窗口，执行：

```bash
source .venv/Scripts/activate
python -m pytest -q
```

当前有 11 条自动化测试：健康检查、三条聊天接口测试、PDF 上传校验、文档列表测试，以及数据库写入成功和数据库失败后的文件清理测试。

## 文档导航

| 文件 | 作用 |
| --- | --- |
| [docs/PRD.md](docs/PRD.md) | 产品目标、MVP 范围和非目标。 |
| [docs/user-flow.md](docs/user-flow.md) | 用户上传、提问、查看引用等目标流程。 |
| [docs/technical-design.md](docs/technical-design.md) | 后续完整 MVP 的架构、数据流和数据库设计。 |
| [docs/test-cases.md](docs/test-cases.md) | 完整 MVP 的验收用例清单。 |
