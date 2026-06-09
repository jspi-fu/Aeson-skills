# DSL Version Delta Log

This document records the changes in each version of Dify Workflow DSL relative to the previous version. Refer to this document when generating DSL to determine the available nodes and fields.

## Usage

1. Read `dsl_version` from `config.yml`
2. During generation, only use nodes and fields supported by that version and earlier
3. If `reference_dsl` exists, prioritize its structure (this version delta document serves as a supplement only)

---

## Version 0.6.0 (Dify v1.10.0+)

**New Nodes:**
- `human-input` — Pauses the workflow to wait for human input
- `trigger-schedule` — Scheduled trigger
- `trigger-webhook` — Webhook trigger
- `trigger-plugin` — Plugin trigger

**New Fields:**
- `iteration` node: `is_parallel` (whether to execute in parallel), `parallel_nums` (parallel count)
- `LLM` node: `reasoning_format` (reasoning format), `structured_output` (structured output configuration)
- `features.file_upload` extended sub-fields: `allowed_file_types`, `allowed_file_extensions`, `allowed_file_upload_methods`, `number_limits`, `fileUploadConfig`

---

## Version 0.5.0 (Dify v1.6.0~v1.9.x)

**New Nodes:**
- `knowledge-index` — Knowledge base index node
- `datasource` — Data source node
- `datasource-empty` — Empty data source node

---

## Version 0.4.0 (Dify v1.3.0~v1.5.x)

**New Nodes:**
- `loop` — Loop node (with exit condition)
- `loop-start` — Loop start node (auto-generated)
- `loop-end` — Loop end node (auto-generated)

**New Fields:**
- Multiple nodes (common): `error_strategy` (error handling strategy), `default_value` (default value)

---

## Version 0.3.0 (Dify v1.1.0~v1.2.x)

**New Nodes:**
- `agent` — Agent node (with tool calling capability)

**Format Change:**
- `provider` format changed to three-segment: `langgenius/<provider>/<provider>` (e.g., `langgenius/openai/openai`)

---

## Version 0.2.0 (Dify v1.0.0)

**New Nodes:**
- `iteration` — Iteration node
- `iteration-start` — Iteration start node (auto-generated)

**New Top-Level Fields:**
- `dependencies` — Plugin dependency list

**New Node Fields:**
- LLM, HTTP, Code, Tool nodes: `retry_config` (retry configuration)

---

## Version 0.1.1~0.1.5 (Dify v0.13.x~v0.14.x)

**Structural Change:**
- `dependencies` extracted from `graph` (not a top-level field)

**New Fields:**
- `conversation_variables` — Conversation variables
- `environment_variables` — Environment variables

---

## Version 0.1.0 (Initial Version)

**Base Nodes:**
- `start`, `end`, `answer`, `llm`, `code`, `if-else`, `http-request`
- `template-transform`, `knowledge-retrieval`, `tool`
- `parameter-extractor`, `question-classifier`
- `variable-aggregator`, `document-extractor`

**Format Characteristics:**
- No `dependencies` field
- `provider` format: `<provider>` (not three-segment)
