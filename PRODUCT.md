# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Vue 3 + TypeScript + Vite（由本阶段需求确认）

## Users

正在找实习、需要整理岗位 JD、面试资料和项目资料的大学生。

## Product Purpose

Career Knowledge Copilot 是求职资料知识库助手。用户上传 PDF 后，可以持续查看处理状态、管理资料，并在后续基于资料进行检索增强问答。

## Positioning

以文件、页码和片段引用为核心证据链，把求职资料管理和后续知识库问答连接起来。

## Operating Context

用户会反复上传、扫描、等待处理和删除求职 PDF。第一阶段文档管理页优先支持高频操作、状态识别和页面刷新后的真实数据恢复。

## Capabilities and Constraints

- 后端提供 `POST /documents`、`GET /documents`、`DELETE /documents/{id}`。
- 上传仅允许 PDF，后端返回 `processing`、`ready` 或 `failed` 状态。
- 前端必须使用真实后端 API，API 地址来自 `VITE_API_BASE_URL`。
- 本阶段只做文档管理页，不做问答页、登录、用户系统、OCR、RAG 逻辑或数据库变更。
- 不把 API Key 放入前端。

## Brand Commitments

- 产品名称：Career Knowledge Copilot。
- UI 采用 Operate 模式，优先信息扫描、重复操作效率和清晰反馈（由本阶段需求确认）。

## Evidence on Hand

- 真实后端接口与返回格式在 `backend/app/main.py`。
- 后端自动化测试在 `tests/`。
- 第一阶段不使用真实简历或隐私文件作为前端验收素材。

## Product Principles

- 真实数据优先：页面状态来自后端，不伪造列表。
- 一眼可扫：文件名、大小、状态和操作保持稳定对齐。
- 操作可恢复：上传、加载、空列表、错误和删除确认都给出明确反馈。
- 安全默认：前端只处理业务 API，不接触模型密钥。

## Accessibility & Inclusion

- 移动端和桌面端均可用。
- 长文件名不能溢出布局。
- 删除、上传等图标按钮提供可读文字或 tooltip。
