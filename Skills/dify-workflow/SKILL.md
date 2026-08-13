---
name: dify-workflow
description: 设计、生成并部署 Dify 应用 DSL (workflow/advanced-chat)。当用户要求构建 Dify 工作流、生成/更新 DSL 文件或通过 Admin API 部署到 Dify 实例时使用。
---

# Dify Workflow DSL 生成器

## 交互原则与凭证隔离

- **需求澄清**：若用户描述不足以确定节点或输入/输出流程，优先澄清输入输出变量与核心节点，确认后开始生成。
- **凭证隔离**：严格隔离敏感凭证。最终回复与导出产物中仅包含 App ID、DSL 文件路径、节点统计与部署状态，禁止泄露 `ADMIN_API_KEY`。
- **关联 Skill 约定**：涉及 Console Admin API 操作时，先读取并遵守 [dify-deploy](file:///d:/源自C盘/桌面/Aeson-skills/Skills/dify-deploy/SKILL.md)。

## 版本锚定 (Version Anchoring)

每次生成前按顺序执行：
1. 读取 `references/config.yml`，获取 `dsl_version` 与 `reference_dsl`。
2. 若 `reference_dsl` 非空，读取 `references/user-reference/<文件名>` 作为基准 schema。
3. 读取 `references/version-deltas.md` 查找版本差异。
4. 约束：输出 YAML 的 `version` 必须匹配 `dsl_version`，且仅使用目标版本支持的节点与字段。

## 节点路由表

| 节点 | 类型标识 | 用途 | 关键参数 | Schema 路径 |
|------|----------|------|----------|-------------|
| Start | `start` | 入口节点；定义输入变量 | `variables` | `references/nodes/start.md` |
| End | `end` | Workflow 模式终端；声明输出 | `outputs` | `references/nodes/end.md` |
| Answer | `answer` | Chatflow 模式流式输出 | `answer`, `variables` | `references/nodes/answer.md` |
| LLM | `llm` | 调用大语言模型 | `model`, `prompt_template`, `context`, `vision` | `references/nodes/llm.md` |
| Knowledge Retrieval | `knowledge-retrieval` | 知识库文档检索 | `query_variable_selector`, `dataset_ids`, `retrieval_mode` | `references/nodes/knowledge-retrieval.md` |
| Code | `code` | 执行 Python3/JS/JSON | `code_language`, `code`, `variables`, `outputs` | `references/nodes/code.md` |
| HTTP Request | `http-request` | HTTP API 调用 | `method`, `url`, `headers`, `body`, `authorization` | `references/nodes/http-request.md` |
| If/Else | `if-else` | 条件分支 (IF/ELIF/ELSE) | `cases` | `references/nodes/if-else.md` |
| Variable Aggregator | `variable-aggregator` | 合并多分支变量 | `output_type`, `variables` | `references/nodes/variable-aggregator.md` |
| Iteration | `iteration` | 数组循环遍历 | `iterator_selector`, `iterator_input_type`, `output_selector` | `references/nodes/iteration.md` |
| Document Extractor | `document-extractor` | 文件文本提取 (PDF/DOCX) | `variable_selector`, `is_array_file` | `references/nodes/document-extractor.md` |
| Template Transform | `template-transform` | Jinja2 模板渲染 | `template`, `variables` | `references/nodes/template-transform.md` |
| Question Classifier | `question-classifier` | LLM 意图分类 | `query_variable_selector`, `model`, `classes` | `references/nodes/question-classifier.md` |
| Parameter Extractor | `parameter-extractor` | LLM 结构化参数提取 | `query`, `model`, `parameters`, `reasoning_mode` | `references/nodes/parameter-extractor.md` |
| Tool | `tool` | 调用外部工具 | `provider_id`, `provider_type`, `tool_name`, `tool_parameters` | `references/nodes/tool.md` |

## 任务执行路径与校验关卡

### 执行路径

1. **解析与模式确定**：批处理用 `workflow` 模式（Start -> End）；对话交互用 `advanced-chat` 模式（Start -> Answer）。
2. **节点选择与模板匹配**：优先匹配 `## 模板匹配` 中的预设模板；无匹配时依据路由表 schema 逐个组装。
3. **构图与边连接**：
   - 节点 ID 格式：13 位时间戳字符串（如 `"1711536487001"`）。
   - 坐标规划：起始点 `{x: 80, y: 282}`，X 轴增量 `+300px`，分支 Y 轴增量 `+200px`。
   - 边 ID 格式：`{sourceId}-{sourceHandle}-{targetId}-{targetHandle}`，`targetHandle` 统一为 `"target"`。分支 sourceHandle 分别为 `"true"`/`case_id`/`"false"` 或类别 ID。
4. **部署与更新**（如适用）：覆盖更新前先导出原 DSL 保存为备份文件。API 异常卡住时报告排查建议，未获明确授权禁止直连数据库。

### 校验关卡 (Validation Gate)

交付产物前必须完成以下 4 项校验：
- [ ] **语法与命名**：默认输出为当前目录的 `<kebab-case-name>.dify.yml`（按需输出 `.dify.json`）。所有字符串节点 ID 显式加引号。
- [ ] **拓扑完整性**：所有 Edge 的 `source` 和 `target` ID 在 Graph Nodes 中真实存在，边 `type` 为 `"custom"`。
- [ ] **变量引用合法性**：节点变量引用为 `{{#nodeId.variableName#}}`，系统变量为 `sys` 前缀（`workflow` 模式严禁引用 `sys.query`）。
- [ ] **Provider 正确性**：`model.provider` 遵循 `"langgenius/<provider>/<provider>"` 格式，且使用真实模型标识（如 `gpt-4o-mini`、`deepseek-chat`）。

## DSL 结构快速参考

```yaml
version: "<dsl_version from config.yml>"
kind: app
app:
  name: "工作流名称"
  mode: "advanced-chat"           # 或 "workflow"
  description: "..."
  icon: "\U0001F916"
  icon_background: "#FFEAD5"
  icon_type: emoji
  use_icon_as_answer_icon: false
dependencies: []
workflow:
  environment_variables: []
  conversation_variables: []
  features:
    file_upload:
      enabled: false
    opening_statement: ""         # 仅 chatflow
    retriever_resource:
      enabled: false
    sensitive_word_avoidance:
      enabled: false
    speech_to_text:
      enabled: false
    suggested_questions: []       # 仅 chatflow
    suggested_questions_after_answer:
      enabled: false
    text_to_speech:
      enabled: false
  graph:
    nodes: []                     # 节点对象数组
    edges: []                     # 边对象数组
    viewport:
      x: 0
      y: 0
      zoom: 0.7
```
完整字段级规范参照 `references/dsl-format.md`。

## 常见 Schema 陷阱

1. **变量形状差异**：
   - `code` / `llm` / `template-transform` / `parameter-extractor`：`[{ variable: "arg", value_selector: ["node_id", "field"], value_type: "string" }]`
   - `variable-aggregator`：裸嵌套列表 `[["node1_id", "output"], ["node2_id", "output"]]`
   - `document-extractor`：扁平列表 `variable_selector: ["upstream_id", "field"]`
2. **Memory 作用域**：`memory` 块仅存在于 `advanced-chat` 模式的 LLM 节点，`workflow` 模式及迭代内部节点必须省略。
3. **迭代节点约束**：内层节点须包含 `parentId: <iteration_id>`、`data.isInIteration: true`、`zIndex: 1002`，坐标为相对坐标（初始约 `{x: 24, y: 68}`）。`iterator_input_type` 必须与真实元素匹配（如 `"array[file]"`）。
4. **特定节点输出形状**：End 节点 `outputs` 为列表；Code 节点 `outputs` 为字典。
5. **Edge Data 字段**：包含 `sourceType`、`targetType`、`isInIteration`、`isInLoop`。迭代内边补充 `iteration_id` 与 `zIndex: 1002`。

## 模板与参考示例

与已知模式高度匹配时优先使用预设模板，按需调整字段：

| 模板 | 路径 | 匹配条件 |
|------|------|----------|
| Chatbot | `references/templates/chatbot.yml` | 简单对话：Start -> LLM -> Answer |
| RAG | `references/templates/rag.yml` | 知识库问答：Start -> Knowledge Retrieval -> LLM -> Answer |
| Agent | `references/templates/agent.yml` | 带分类/参数提取的工具 Agent |
| Translation | `references/templates/translation.yml` | 文本转换/翻译 |

### 完整示例文件指针 (Progressive Disclosure)

- **Minimal Chatbot DSL**：对应完整 DSL 见 [`examples/simple-chatbot.yml`](file:///d:/源自C盘/桌面/Aeson-skills/Skills/dify-workflow/examples/simple-chatbot.yml)
- **RAG with Rerank DSL**：对应完整 DSL 见 [`examples/rag-with-rerank.yml`](file:///d:/源自C盘/桌面/Aeson-skills/Skills/dify-workflow/examples/rag-with-rerank.yml)
