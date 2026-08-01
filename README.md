# Career Knowledge Copilot

Career Knowledge Copilot 是一个面向大学生的求职资料知识库助手。项目最终将支持上传岗位 JD、面试资料和项目材料 PDF，并根据资料回答问题、给出文件名和页码引用。

## 当前阶段

项目目前处于 FastAPI 后端学习与骨架搭建阶段，已经实现了四个可运行接口：

- `GET /health`：返回服务健康状态，用于确认后端已正常启动。
- `POST /chat`：接收 JSON 中的 `message`，返回包含该消息的模拟回复。
- `POST /documents`：接收一个不超过 20 MB 的 PDF，保存到项目根目录的 `uploads/`，并将元数据写入 PostgreSQL，初始状态为 `processing`。
- `GET /documents`：从 PostgreSQL 查询并返回已上传的文档元数据列表。
- `DELETE /documents/{id}`：删除数据库记录和本地 PDF 文件。

当前尚未接入大模型、PDF 解析、向量检索或 Vue 前端；数据库持久化和 Docker Compose 基础设施已经完成，后续 MVP 将继续接入这些能力。

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

返回 PostgreSQL 中的文档元数据。服务重启后列表仍可从数据库恢复。

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

### 删除文档

```text
DELETE /documents/{id}
```

成功时返回 `204 No Content`。文档不存在时返回 `404`。数据库删除失败时会回滚，保留原 PDF；文件已经不存在时不会导致删除接口失败。

## 运行测试

另开一个 Git Bash 窗口，执行：

```bash
source .venv/Scripts/activate
python -m pytest -q
```

当前有 17 条自动化测试：健康检查、聊天、PDF 上传和列表，以及文档删除的成功、失败和边界场景。测试会自动使用独立的 `career_copilot_test` 数据库，不会清理开发数据库中的手动数据。

## 文档导航

| 文件 | 作用 |
| --- | --- |
| [docs/PRD.md](docs/PRD.md) | 产品目标、MVP 范围和非目标。 |
| [docs/user-flow.md](docs/user-flow.md) | 用户上传、提问、查看引用等目标流程。 |
| [docs/technical-design.md](docs/technical-design.md) | 后续完整 MVP 的架构、数据流和数据库设计。 |
| [docs/test-cases.md](docs/test-cases.md) | 完整 MVP 的验收用例清单。 |
