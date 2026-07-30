# Career Knowledge Copilot

Career Knowledge Copilot 是一个面向大学生的求职资料知识库助手。项目最终将支持上传岗位 JD、面试资料和项目材料 PDF，并根据资料回答问题、给出文件名和页码引用。

## 当前阶段

项目目前处于 FastAPI 后端学习与骨架搭建阶段，已经实现了两个可运行接口：

- `GET /health`：返回服务健康状态，用于确认后端已正常启动。
- `POST /chat`：接收 JSON 中的 `message`，返回包含该消息的模拟回复。

当前尚未接入大模型、PDF 上传、数据库、向量检索、Vue 前端或 Docker Compose。这些是后续 MVP 的实现目标，而不是已完成的功能。

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

## 运行测试

另开一个 Git Bash 窗口，执行：

```bash
source .venv/Scripts/activate
python -m pytest -q
```

当前有 3 条自动化测试：健康检查、正常聊天请求、缺少 `message` 的请求校验。

## 文档导航

| 文件 | 作用 |
| --- | --- |
| [docs/PRD.md](docs/PRD.md) | 产品目标、MVP 范围和非目标。 |
| [docs/user-flow.md](docs/user-flow.md) | 用户上传、提问、查看引用等目标流程。 |
| [docs/technical-design.md](docs/technical-design.md) | 后续完整 MVP 的架构、数据流和数据库设计。 |
| [docs/test-cases.md](docs/test-cases.md) | 完整 MVP 的验收用例清单。 |
