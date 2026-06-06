# Document Extractor (`document-extractor`)

## Purpose

Extracts plain text content from uploaded documents (PDF, DOCX, DOC, TXT, MD, HTML, XLS/XLSX, etc.) so downstream LLM / Code nodes can consume the text.

Typical placements:

- **Top-level** after a Start node with a `file` or `file-list` variable.
- **Inside an Iteration** when iterating over `array[file]`. In that case each iteration sees a single `file`, and the extractor must be configured with `is_array_file: false` and `variable_selector` pointing at the iteration's `item`.

## Core Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `variable_selector` | `ValueSelector` (string[]) | Yes | Path to the file (or array of files) variable. |
| `is_array_file` | `boolean` | Yes | `true` when the input is `array[file]`; `false` for a single `file`. |

## Schema

```yaml
data:
  type: document-extractor
  title: "Document Extractor"
  desc: ""
  is_array_file: false               # true for array[file], false for single file
  variable_selector:                  # NOTE: singular "variable_selector", not a list of {value_selector: ...}
    - "start_node_id"
    - "uploaded_doc"
```

## Output Variables

| Variable | Type | Condition |
|----------|------|-----------|
| `text` | `string` | When `is_array_file: false`. Concatenated text content of the single file. |
| `text` | `array[string]` | When `is_array_file: true`. One string per file. |

Reference downstream as `{{#<doc_extractor_id>.text#}}`.

## Common Patterns

### Single file → text → LLM

```yaml
- id: "doc_extractor_1"
  type: custom
  position: { x: 380, y: 282 }
  data:
    type: document-extractor
    title: "Extract Document"
    desc: ""
    is_array_file: false
    variable_selector:
      - "start_node_1"
      - "uploaded_doc"
```

### Inside an iteration over `array[file]`

Place the document-extractor as the first node inside the iteration sub-graph. Its `variable_selector` should point at the iteration's per-element `item` variable:

```yaml
# Iteration container
- id: "iter_1"
  type: custom
  position: { x: 380, y: 200 }
  width: 900
  height: 280
  zIndex: 1
  data:
    type: iteration
    title: "Per-file processing"
    desc: ""
    iterator_selector:
      - "start_node_1"
      - "files"
    iterator_input_type: "array[file]"
    output_selector:
      - "code_in_iter_1"
      - "result"
    output_type: "array[object]"
    is_parallel: true
    parallel_nums: 3
    error_handle_mode: "continue-on-error"
    flatten_output: true
    start_node_id: "iter_1start"
    width: 900
    height: 280

# Document extractor sees a single file per iteration
- id: "doc_extractor_in_iter"
  type: custom
  parentId: "iter_1"
  position: { x: 128, y: 68 }
  width: 244
  height: 54
  zIndex: 1002
  data:
    type: document-extractor
    title: "Extract"
    desc: ""
    isInIteration: true
    iteration_id: "iter_1"
    is_array_file: false
    variable_selector:
      - "iter_1"            # iteration node id
      - "item"              # per-element variable
```

## Validation Notes

- `variable_selector` is **singular** and is a flat array of strings (`[node_id, key]`). Do not wrap it as `{value_selector: [...]}` — that is the shape used by the `variables` array on Code / LLM / Template Transform nodes.
- `is_array_file` must match the referenced variable's type. Mismatches cause runtime extraction failures.
- The source file's type must be in `features.file_upload.allowed_file_types`; otherwise the file is rejected at upload time, before the workflow runs.
