# AI 能力接入设计文档 v0.2（设置中心化版）

## 1. 设计结论（先定原则）

- 模型厂商、API 密钥、API 地址、模型列表、默认模型，全部集中在“设置”里管理。
- AI 对话页只负责会话与问答，不承载配置编辑逻辑。
- 配置读取统一经过 `core/settings.py`，业务内容写入 `data.db`。
- 参考 CherryStudio 信息架构：左侧服务商列表，中间服务商配置，底部模型管理操作。

## 2. 目标与范围

- 首批支持：DeepSeek、豆包、Qwen、自定义（Ollama / OpenAI-compatible）。
- 完成“可运行骨架 + 设置中心化管理 + 对话联动全局搜索”。
- 暂不做：函数调用编排、多模态上传、RAG。

## 3. 信息架构（Settings）

### 3.1 设置页结构（新增 AI 分组）

- 一级分组：`AI 设置`
- 二级页签：
  - `模型服务`（核心）
  - `默认模型`
  - `常规参数`

### 3.2 模型服务页（参考图）

- 左栏：服务商列表
  - 展示 `DeepSeek`、`豆包`、`Qwen`、`Ollama`、`自定义`
  - 每项带启用状态（ON/OFF）
  - 支持新增自定义服务商
- 中栏：服务商详情编辑区
  - `API 密钥`（支持显示/隐藏）
  - `API 地址`
  - `连接测试`按钮
  - `启用`开关
- 下栏：模型管理区
  - 展示当前服务商模型列表
  - 支持 `新增`、`编辑`、`删除`、`启用/禁用`
  - 支持设置默认模型

### 3.3 默认模型页

- 全局默认服务商
- 全局默认模型
- 每服务商“最后使用模型”

### 3.4 常规参数页

- `stream_enabled`
- `temperature`
- `max_tokens`
- `request_timeout_sec`
- `retry_count`

## 4. 配置存储设计（QSettings）

- 配置统一由 `core/settings.py` 提供 `AISettingsManager` 管理。
- 关键键位：
  - `ai/default_provider`
  - `ai/default_model`
  - `ai/stream_enabled`
  - `ai/temperature`
  - `ai/max_tokens`
  - `ai/request_timeout_sec`
  - `ai/retry_count`
  - `ai/providers/<provider>/api_key`
  - `ai/providers/<provider>/base_url`
  - `ai/providers/<provider>/enabled`
  - `ai/providers/<provider>/extra_headers_json`
  - `ai/models/catalog_json`
  - `ai/models/last_selected_by_provider_json`
- 安全策略：
  - v0.2 先沿用 `QSettings`。
  - v0.3 升级为系统凭据存储（Windows Credential Manager）并保留兼容迁移。

## 5. 对话页职责（瘦身）

- AI 对话插件保留：
  - 会话列表
  - 消息流
  - 输入框
  - 发送/停止
- AI 对话插件移除：
  - API Key 编辑
  - API URL 编辑
  - 模型新增编辑
- 模型选择行为：
  - 仅允许“选择已配置模型”
  - 不允许在对话页直接新增模型配置

## 6. 全局搜索联动

- 输入 `@搜索 关键词` 触发搜索桥接。
- 由 `AISearchBridge` 调用 `GlobalSearchManager.search()`。
- 将 TopN 结果摘要注入上下文，避免长文本污染。
- 点击搜索结果继续复用 `SearchResult.action`。

## 7. 数据库存储（data.db）

- 结论：会话与消息继续存放在 `data.db`，不保存 API 密钥。
- 表：
  - `ai_conversations`
  - `ai_messages`
- 密钥归属：
  - 只在 `QSettings`，不入 `data.db`。

## 8. 分层架构（代码视角）

- `core/ai/types.py`：统一领域对象
- `core/ai/provider_base.py`：适配器抽象与注册表
- `core/ai/settings_bridge.py`：读取 `AISettingsManager`
- `core/ai/chat_service.py`：统一发送入口
- `core/ai/search_bridge.py`：搜索摘要注入
- `storage/repositories/ai_repository.py`：会话消息仓储
- `plugins/ai_assistant`：简洁对话 UI
- `ui/settings_interface.py`：新增 AI 设置分组与页面

## 9. 交互流程（关键链路）

1. 用户进入设置页，配置服务商、密钥、地址、模型。
2. 点击连接测试，验证通过后保存。
3. 用户进入 AI 对话页，仅选择已配置模型发起聊天。
4. 输入 `@搜索 xxx` 时触发全局搜索注入上下文。
5. 会话和消息写入 `data.db`。

## 10. 当前实现与后续

- 当前：已具备 AI 基础骨架和数据表结构。
- 下一步优先级：
  - 先补 `ui/settings_interface.py` 的 AI 设置页（按本设计）
  - 再接入 DeepSeek / 豆包 / Qwen / Ollama 实际请求
  - 最后优化对话页视觉与流式体验
