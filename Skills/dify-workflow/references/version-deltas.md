# DSL 版本差异记录

本文档记录 Dify Workflow DSL 各版本相对于前一版本的变更。生成 DSL 时参照此文档决定可用的节点和字段。

## 使用方法

1. 读取 `config.yml` 中的 `dsl_version`
2. 生成时仅使用该版本及之前版本支持的节点和字段
3. 若有 `reference_dsl`，优先以其结构为准（版本差异文档仅作补充）

---

## 版本 0.6.0（Dify v1.10.0+）

**新增节点：**
- `human-input` — 暂停工作流等待人工输入
- `trigger-schedule` — 定时触发器
- `trigger-webhook` — Webhook 触发器
- `trigger-plugin` — 插件触发器

**新增字段：**
- `iteration` 节点：`is_parallel`（是否并行执行）、`parallel_nums`（并行数量）
- `LLM` 节点：`reasoning_format`（推理格式）、`structured_output`（结构化输出配置）
- `features.file_upload` 扩展子字段：`allowed_file_types`、`allowed_file_extensions`、`allowed_file_upload_methods`、`number_limits`、`fileUploadConfig`

---

## 版本 0.5.0（Dify v1.6.0~v1.9.x）

**新增节点：**
- `knowledge-index` — 知识库索引节点
- `datasource` — 数据源节点
- `datasource-empty` — 空数据源节点

---

## 版本 0.4.0（Dify v1.3.0~v1.5.x）

**新增节点：**
- `loop` — 循环节点（带退出条件）
- `loop-start` — 循环起始节点（自动生成）
- `loop-end` — 循环结束节点（自动生成）

**新增字段：**
- 多节点通用：`error_strategy`（错误处理策略）、`default_value`（默认值）

---

## 版本 0.3.0（Dify v1.1.0~v1.2.x）

**新增节点：**
- `agent` — Agent 节点（带工具调用能力）

**格式变更：**
- `provider` 格式变更为三段式：`langgenius/<provider>/<provider>`（如 `langgenius/openai/openai`）

---

## 版本 0.2.0（Dify v1.0.0）

**新增节点：**
- `iteration` — 迭代节点
- `iteration-start` — 迭代起始节点（自动生成）

**新增顶层字段：**
- `dependencies` — 插件依赖列表

**新增节点字段：**
- LLM、HTTP、Code、Tool 节点：`retry_config`（重试配置）

---

## 版本 0.1.1~0.1.5（Dify v0.13.x~v0.14.x）

**结构变更：**
- `dependencies` 从 `graph` 中提取（非顶层字段）

**新增字段：**
- `conversation_variables` — 会话变量
- `environment_variables` — 环境变量

---

## 版本 0.1.0（初始版本）

**基础节点：**
- `start`、`end`、`answer`、`llm`、`code`、`if-else`、`http-request`
- `template-transform`、`knowledge-retrieval`、`tool`
- `parameter-extractor`、`question-classifier`
- `variable-aggregator`、`document-extractor`

**格式特征：**
- 无 `dependencies` 字段
- `provider` 格式：`<provider>`（非三段式）
