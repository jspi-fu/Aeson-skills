---
name: dify-workflow
description: 根据用户需求设计并生成 Dify 应用 DSL，支持创建或更新 workflow/advanced-chat 应用并部署到 Dify 平台。当用户要求从需求构建 Dify 工作流、生成 DSL、从 DSL 创建应用、更新现有应用 DSL、或通过 Admin API 自动化创建/更新 Dify 应用时使用。
---

# Dify Workflow DSL 生成器

## 概述

本技能生成可直接导入 Dify 实例的工作流 DSL 文件。根据用户对目标工作流的自然语言描述，生成包含所有节点、边、布局位置和配置的完整 YAML（默认）或 JSON 文件。

触发条件：
- 创建、生成或构建 Dify 工作流
- 将流程描述转换为 Dify DSL
- 搭建 chatflow 或 workflow 应用
- 通过 Admin API 将生成的 DSL 部署到 Dify 实例
- 更新现有 Dify 应用的 DSL

输出格式默认为 YAML（`.dify.yml`），也可按需输出 JSON（`.dify.json`）。

涉及 Console Admin API 的请求时，必须先读取并遵守 `skills/dify-deploy/SKILL.md`。

## 智能交互逻辑

生成前先评估用户描述是否充分：

**直接执行**的条件：
- 描述包含明确的输入/输出预期
- 包含处理逻辑（工作流应该做什么）
- 有足够细节来选择合适的节点

**最多追问 3 轮**以澄清需求：
1. "工作流将接收什么输入，应该产生什么输出？"
2. "需要哪些处理步骤？（如 LLM 调用、知识检索、API 调用、条件逻辑）"
3. "有特定的模型、工具或知识库要使用吗？"

需求明确后即可开始生成。

## 节点路由表

| 节点 | 类型标识 | 用途 | 关键参数 | Schema 路径 |
|------|----------|------|----------|-------------|
| Start | `start` | 入口节点；定义输入变量 | `variables` | `references/nodes/start.md` |
| End | `end` | Workflow 模式的终端节点；声明输出 | `outputs` | `references/nodes/end.md` |
| Answer | `answer` | Chatflow 模式的流式输出节点 | `answer`, `variables` | `references/nodes/answer.md` |
| LLM | `llm` | 调用大语言模型 | `model`, `prompt_template`, `context`, `vision` | `references/nodes/llm.md` |
| Knowledge Retrieval | `knowledge-retrieval` | 从知识库检索相关文档片段 | `query_variable_selector`, `dataset_ids`, `retrieval_mode` | `references/nodes/knowledge-retrieval.md` |
| Code | `code` | 执行 Python3/JavaScript/JSON 代码 | `code_language`, `code`, `variables`, `outputs` | `references/nodes/code.md` |
| HTTP Request | `http-request` | 发起 HTTP API 调用 | `method`, `url`, `headers`, `body`, `authorization` | `references/nodes/http-request.md` |
| If/Else | `if-else` | 条件分支（IF/ELIF/ELSE） | `cases` | `references/nodes/if-else.md` |
| Variable Aggregator | `variable-aggregator` | 合并多分支变量 | `output_type`, `variables` | `references/nodes/variable-aggregator.md` |
| Iteration | `iteration` | 遍历数组，对每个元素执行子图 | `iterator_selector`, `iterator_input_type`, `output_selector`, `start_node_id` | `references/nodes/iteration.md` |
| Document Extractor | `document-extractor` | 从上传文件提取文本（PDF/DOCX 等） | `variable_selector`, `is_array_file` | `references/nodes/document-extractor.md` |
| Template Transform | `template-transform` | 使用变量渲染 Jinja2 模板 | `template`, `variables` | `references/nodes/template-transform.md` |
| Question Classifier | `question-classifier` | 通过 LLM 将输入分类到预定义类别 | `query_variable_selector`, `model`, `classes` | `references/nodes/question-classifier.md` |
| Parameter Extractor | `parameter-extractor` | 通过 LLM 从文本提取结构化参数 | `query`, `model`, `parameters`, `reasoning_mode` | `references/nodes/parameter-extractor.md` |
| Tool | `tool` | 调用外部工具（内置、API、MCP） | `provider_id`, `provider_type`, `tool_name`, `tool_parameters` | `references/nodes/tool.md` |

## 版本检测（每次生成前必须执行）

1. 读取 `references/config.yml`，获取 `dsl_version` 和 `reference_dsl`
2. 如果 `reference_dsl` 非空，读取 `references/user-reference/<文件名>` 作为 schema 参考
3. 读取 `references/version-deltas.md`，找到目标版本的变更记录
4. 生成时遵循：
   - 输出 YAML 的 `version` 字段使用 config 中的 `dsl_version` 值
   - 仅使用目标版本及之前版本支持的节点类型
   - 仅使用目标版本及之前版本支持的字段
   - 若有 reference_dsl，优先以其结构为准（版本差异文档仅作补充）

## 任务完成步骤

### 基本原则

- 先给出 DSL 设计方案并征求用户确认，用户同意后再修改文件或调用接口
- 不要把 `ADMIN_API_KEY` 写入PR 描述或最终回复
- 默认 `include_secret=false`，除非用户明确要求导出密钥
- 覆盖更新前先导出旧 DSL 作为备份，避免丢失已有配置
- Admin API 卡住或失败时，先报告错误和排查建议；只有用户明确授权，才允许直接写数据库

### 执行路径

根据用户需求选择执行路径。涉及 Console Admin API 的请求时，先读取并遵守 `skills/dify-deploy/SKILL.md`。

**只生成 DSL**：

1. **解析需求** -- 确定应用模式（`workflow` 或 `advanced-chat`）、所需节点和数据流。
   - 批处理任务使用 `workflow` 模式（Start/End 节点）。
   - 对话聊天机器人使用 `advanced-chat` 模式（Start/Answer 节点）。

2. **选择节点** -- 从上方路由表中选取节点，加载对应的 schema 文件获取完整字段规范。

3. **检查模板匹配** -- 如果需求与已知模式高度匹配，从模板开始（见下方模板匹配）。按需调整字段。

4. **从 Schema 组装** -- 若无模板匹配，逐个构建节点：
   - 生成唯一 ID（13 位时间戳字符串，如 `"1711536487001"`）。
   - 按节点 schema 填写必填字段。
   - 使用 `{{#nodeId.variableName#}}` 语法引用变量。
   - Chatflow 模式下使用 `{{#sys.query#}}` 引用系统查询变量。

5. **生成边** -- 按 `references/edge-and-layout.md` 的规则连接节点：
   - 边 ID 格式：`{sourceId}-{sourceHandle}-{targetId}-{targetHandle}`
   - 标准 `sourceHandle`：大多数节点使用 `"source"`
   - If/Else 分支：`"true"`（第一个条件）、case_id（elif）、`"false"`（else）
   - Question Classifier 分支：topic `id` 作为 sourceHandle
   - `targetHandle` 始终为 `"target"`
   - 所有边使用 `type: "custom"`，`zIndex: 0`（迭代内部为 `1002`）

6. **计算布局位置** -- 将节点放置在从左到右的网格上：
   - 起始节点位于 `{x: 80, y: 282}`
   - 水平间距：每步 300px（`NODE_WIDTH 240 + X_OFFSET 60`）
   - 并行分支垂直间距：200px
   - 节点宽度：244px，高度：因节点而异（通常 54-150px）

7. **输出文件** -- 渲染为 YAML（默认）或 JSON，验证结构完整性。按输出规则命名和存放文件。

**创建应用**：

1-7. 同"只生成 DSL"步骤。

8. **创建应用** -- 调用 Admin API 创建 workflow 应用，获取 `APP_ID`。

9. **导入 DSL** -- 使用返回的 `APP_ID` 覆盖导入 DSL。

10. **确认导入** -- 如果导入返回 `202 pending`，调用 confirm 接口。

11. **导出验证** -- 重新导出该应用 DSL，验证远端内容。

**更新应用**：

1. **备份** -- 使用 `APP_ID` 导出当前 DSL，保存为备份文件。

2-8. 同"只生成 DSL"步骤。

9. **覆盖导入** -- 使用 `apps/imports` 传入 `app_id` 覆盖导入。

10. **确认导入** -- 如果导入返回 `202 pending`，调用 confirm 接口。

11. **导出验证** -- 重新导出该应用 DSL，验证远端内容。

### 验证要求

部署完成后至少验证：
- 远端导出的 DSL 能成功返回
- 远端 DSL 包含预期输入变量
- 远端 DSL 包含预期节点类型和关键配置
- 远端 DSL 包含预期输出字段或输出文本

最终回复只说明结果、文件路径、应用 ID 和验证结论；不要泄露 `ADMIN_API_KEY`。

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
    nodes: []                     # 节点对象
    edges: []                     # 边对象
    viewport:
      x: 0
      y: 0
      zoom: 0.7
```

完整的字段级规范请参见 `references/dsl-format.md`。

## 输出规则

- **输出位置**：最终工作流文件（`.dify.yml` / `.dify.json`）输出到**当前工作目录**。中间/临时文件输出到 `/tmp/dify-workflow/`。
- **文件名**：`<kebab-case-name>.dify.yml`（JSON 输出为 `.dify.json`）
- **必需章节**：`version`、`kind`、`app`、`workflow`（含 `graph`、`features`）
- **节点 ID**：13 位时间戳字符串（如 `"1711536487001"`）。节点间递增几千以模拟真实 ID。
- **坐标**：起始于 `{x: 80, y: 282}`。后续每列 x 轴 `+300`。并行分支 y 轴偏移 `+200`。
- **变量引用**：使用 `{{#nodeId.variableName#}}` 语法。系统变量使用 `sys` 前缀：`{{#sys.query#}}`、`{{#sys.user_id#}}`。
- **模型 Provider 格式**：`"langgenius/<provider>/<provider>"`（如 `"langgenius/openai/openai"`）。`model.name` 必须使用真实存在的模型名（如 `deepseek-chat`、`gpt-4o-mini`）；虚构名称如 `deepseek-v4-pro` 会导致 provider 验证失败。
- **所有字符串类型的节点 ID** 必须在 YAML 中加引号，防止类型强制转换。

## 常见 Schema 陷阱（必须避免）

以下是目标 Dify 版本中最容易导致 DSL 导入失败的 schema 错误：

1. **变量形状因节点类型而异。** 节点变量列表中单个条目的形状在不同节点间**不相同**：
   - `code`、`llm`、`template-transform`、`parameter-extractor` 使用**对象**：
     ```yaml
     variables:
       - variable: my_arg
         value_selector: ["upstream_id", "field"]
         value_type: string
     ```
   - `variable-aggregator` 使用**裸嵌套列表**（无 `value_selector:` 包装，无 `variable:` 名称）：
     ```yaml
     variables:
       - - "branch1_id"
         - "output"
       - - "branch2_id"
         - "output"
     ```
   - `document-extractor` 使用单数 `variable_selector`（扁平字符串数组），不是列表：
     ```yaml
     variable_selector: ["upstream_id", "field"]
     ```
2. **`memory` 仅属于 chatflow 的 LLM 节点。** 在 `workflow` 模式应用中，`sys.query` 不存在；LLM 节点必须省略 `memory` 块。workflow 应用中迭代内部的 LLM 节点同理。
3. **迭代容器需要在两处设置尺寸。** 在 `data` 内部和外层节点级别都设置 `width` 和 `height`。iteration-start 子节点使用外层 `type: custom-iteration-start`，`data.type: iteration-start`。
4. **迭代子节点** 必须声明 `parentId: <iteration_id>`、`data.isInIteration: true`、`data.iteration_id: <iteration_id>` 和 `zIndex: 1002`。其 `position` 相对于迭代容器（如起始位置约 `{x: 24, y: 68}`）。
5. **`iterator_input_type` 必须匹配真实元素类型。** 文件：`"array[file]"`。数字：`"array[number]"`。不匹配会破坏运行时变量解析。
6. **插件依赖。** 如果引用了模型 provider（如 `langgenius/deepseek/deepseek`）或 Dify 未内置的工具 provider，需在顶层 `dependencies` 中声明，以便导入时明确标记缺失插件。当部署环境已安装这些插件时，空 `dependencies: []` 是可以的。
7. **End 节点的 `outputs` 是 `{variable, value_selector, value_type}` 条目列表**；Code 节点的 `outputs` 是以变量名为键、`{type, children}` 为值的字典。不要混淆这两种形状。
8. **Edge 的 `data` 块** 应包含 `sourceType`、`targetType`、`isInIteration`、`isInLoop`。迭代内部的边还需要 `iteration_id` 和 `zIndex: 1002`。

## 模板匹配

当用户需求与以下模式高度匹配时，使用模板。加载模板后按需定制字段（模型、提示词、变量）。

| 模板 | 路径 | 匹配条件 |
|------|------|----------|
| Chatbot | `references/templates/chatbot.yml` | 简单对话机器人：Start -> LLM -> Answer |
| RAG | `references/templates/rag.yml` | 知识库问答：Start -> Knowledge Retrieval -> LLM -> Answer |
| Agent | `references/templates/agent.yml` | 使用工具的 Agent，带问题分类或参数提取 |
| Translation | `references/templates/translation.yml` | 文本转换/翻译：Start -> LLM（带特定 system prompt）-> Answer/End |

如果需求部分匹配，使用最接近的模板作为起点，按需增删节点。

## 示例

最小 chatflow（Start -> LLM -> Answer）：

```yaml
version: "<参照 config.yml>"
kind: app
app:
  name: "Simple Chatbot"
  mode: advanced-chat
  icon: "\U0001F916"
  icon_background: "#FFEAD5"
  icon_type: emoji
  description: "A minimal chatbot using GPT-4o-mini."
  use_icon_as_answer_icon: false
dependencies: []
workflow:
  environment_variables: []
  conversation_variables: []
  features:
    file_upload:
      enabled: false
    opening_statement: "Hello! How can I help you today?"
    retriever_resource:
      enabled: false
    sensitive_word_avoidance:
      enabled: false
    speech_to_text:
      enabled: false
    suggested_questions:
      - "What can you help me with?"
    suggested_questions_after_answer:
      enabled: false
    text_to_speech:
      enabled: false
  graph:
    edges:
      - id: "1711536487001-source-1711536522001-target"
        source: "1711536487001"
        sourceHandle: source
        target: "1711536522001"
        targetHandle: target
        type: custom
        zIndex: 0
        data:
          sourceType: start
          targetType: llm
      - id: "1711536522001-source-1711536558001-target"
        source: "1711536522001"
        sourceHandle: source
        target: "1711536558001"
        targetHandle: target
        type: custom
        zIndex: 0
        data:
          sourceType: llm
          targetType: answer
    nodes:
      - id: "1711536487001"
        type: custom
        position: { x: 80, y: 282 }
        data:
          type: start
          title: Start
          desc: ""
          variables: []
      - id: "1711536522001"
        type: custom
        position: { x: 380, y: 282 }
        data:
          type: llm
          title: LLM
          desc: ""
          model:
            provider: "langgenius/openai/openai"
            name: "gpt-4o-mini"
            mode: "chat"
            completion_params:
              temperature: 0.7
          prompt_template:
            - role: "system"
              text: "You are a helpful assistant."
          variables: []
          context:
            enabled: false
            variable_selector: []
          vision:
            enabled: false
          memory:
            query_prompt_template: "{{#sys.query#}}"
            window:
              enabled: false
              size: 10
      - id: "1711536558001"
        type: custom
        position: { x: 680, y: 282 }
        data:
          type: answer
          title: Answer
          desc: ""
          answer: "{{#1711536522001.text#}}"
          variables: []
    viewport:
      x: 0
      y: 0
      zoom: 0.7
```

完整版本（含所有可选字段）请参见 `examples/simple-chatbot.yml`。RAG 工作流示例请参见 `examples/rag-with-rerank.yml`。

## 格式选择

- **YAML（默认）**：输出为 `.dify.yml`。使用标准 YAML 格式，2 空格缩进。所有节点 ID 字符串加引号。这是可读性和 Dify 导入的首选格式。
- **JSON**：用户明确要求时输出为 `.dify.json`。使用相同结构的标准 JSON 格式。适用于程序化消费或基于 API 的导入。

两种格式均被 Dify 导入功能完全支持。
