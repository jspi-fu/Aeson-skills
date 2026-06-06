---
name: mkdocs-shadcn
description: mkdocs-shadcn 主题 Markdown 排版与项目编排。当用户需要编写或修改 mkdocs-shadcn 主题的文档、配置 mkdocs.yml、或询问排版语法时，使用此技能。触发词：mkdocs、shadcn、排版、配置、Markdown、文档、admonition、details、tab、提示框、折叠、标签页、格式化、模板。
---

# mkdocs-shadcn 主题排版技能

## 目录
---

1. [工作流程](#工作流程)
2. [页面模板](#页面模板)
3. [资源文件速查](#资源文件速查)
4. [决策流程](#决策流程)
5. [反例清单](#反例清单)

## 工作流程（每次运行技能时必须运行该工作流程中的所有步骤）

**🔴 CHECKPOINT · 🛑 STOP：开始前确认项目目录和 mkdocs.yml 路径正确。**

---
### 1. 检查项目配置

**输入**：项目目录路径
**输出**：配置检查报告，列出问题和建议修复

运行配置检查脚本：

```bash
python <mkdocs-shadcn-path>/scripts/check_config.py <项目目录> [--apply]
```

脚本会自动检查并补充：

- `theme.name` 是否为 `shadcn`
- `plugins` 是否包含必要插件（search）
- `markdown_extensions` 是否包含推荐的扩展（admonition, codehilite, fenced_code, footnotes, pymdownx.blocks.details, pymdownx.blocks.tab, pymdownx.progressbar, pymdownx.tabbed, attr_list）
- `nav` 导航配置
- `site_name` 站点名称

如需自动应用修复，添加 `--apply` 参数。

**示例**：
```bash
# 仅检查
python skills/mkdocs-shadcn/scripts/check_config.py ./my-project

# 检查并自动修复
python skills/mkdocs-shadcn/scripts/check_config.py ./my-project --apply
```

**失败处理**：
- 如果脚本不存在 → 检查 `<mkdocs-shadcn-path>/scripts/` 目录是否完整，重新下载或克隆仓库
- 如果 Python 未安装 → 提示用户安装 Python 3.8+，或使用系统包管理器安装
- 如果 YAML 解析失败 → 检查 mkdocs.yml 语法是否正确，使用在线 YAML 验证器
- 如果 `--apply` 后配置未生效 → 手动检查 mkdocs.yml 文件权限，确保可写

---

### 2. 智能排版内容

根据内容特征选择合适语法，进行排版：

| 内容特征 | 选择语法 | 示例 |
|----------|----------|------|
| 内容较长，非必需阅读 | `/// details` | `/// details \| 📖 点击查看详细配置` |
| 问答形式的 FAQ | `/// details \| ❓ 问题` | `/// details \| ❓ 什么是 XXX？` |
| 多平台/互斥选项 | `/// tab` | `/// tab \| Windows` / `/// tab \| macOS` |
| 技巧、建议 | `!!! tip` | `!!! tip "最佳实践"` |
| 警告、风险 | `!!! warning/danger` | `!!! warning "安全提示"` |
| 补充说明 | `!!! note/info` | `!!! note "说明"` |

详细语法和示例参考 [syntax-guide.md](references/syntax-guide.md) 和 [examples.md](references/examples.md)。

**失败处理**：
- 如果语法不生效 → 检查 `markdown_extensions` 是否包含对应扩展，参考配置文档
- 如果 Tab/Details 渲染异常 → 检查 `|` 两侧是否有空格，结尾是否有 `///`
- 如果不确定使用哪种语法 → 参考决策流程章节或查看 examples.md

---

### 3. 格式化文档

**输入**：Markdown 文件或目录路径
**输出**：格式化后的文件，符合 mkdocs-shadcn 规范

排版内容完成后，必须运行格式化脚本：

```bash
python <mkdocs-shadcn-path>/scripts/format.py <文件或目录路径>
```

脚本自动处理：

- 标题分割线（H2 下方 `---`，H3 上方 `---`，H2 后第一个 H3 除外）
- 图片居中（统一转为 `<p align="center">
  <img ...>
</p>`）

- 资源路径（`assets/` 路径转为 `/assets` 绝对路径）
- 列表间距（统一空行规范）

**失败处理**：
- 如果脚本报错 → 检查文件编码是否为 UTF-8
- 如果格式化后内容异常 → 使用 `git diff` 查看具体改动，手动回滚
- 如果目录下有非 Markdown 文件 → 脚本会自动跳过，无需处理

## 页面模板
---

**🔴 CHECKPOINT · 🛑 STOP：新建页面前确认使用正确的模板。**

新建页面时，使用终端命令复制 [assets/page-template.md](assets/page-template.md) 作为起点。

项目初始化时，参考 [assets/mkdocs-template.yml](assets/mkdocs-template.yml) 创建配置文件。

## 资源文件速查
---

| 路径 | 用途 | 使用场景 | 依赖 |
|------|------|----------|------|
| `scripts/check_config.py` | 检查并补充 mkdocs.yml 配置 | 项目初始化、配置检查 | Python 3.8+, PyYAML |
| `scripts/format.py` | 格式化 Markdown 文件 | 排版完成后、提交前 | Python 3.8+ |
| `assets/page-template.md` | 页面模板 | 新建页面时复制使用 | 无 |
| `assets/mkdocs-template.yml` | mkdocs.yml 配置模板 | 项目初始化时参考 | 无 |
| `references/syntax-guide.md` | 完整语法手册 | 查询语法细节 | 无 |
| `references/examples.md` | 排版示例 | 参考排版实践 | 无 |
| `references/configuration.md` | 项目配置参考 | 配置 mkdocs.yml | 无 |

## 决策流程
---

**🔴 CHECKPOINT · 🛑 STOP：排版前确认内容类型，选择正确的语法。不确定时参考 examples.md。**

```
内容是否需要折叠？
├── 是 → /// details
│   └── FAQ 形式？→ 标题用 ❓ 开头
│
内容是否有多个互斥选项？
├── 是 → /// tab
│   └── 按平台/方式/工具分类
│
内容是否需要突出强调？
├── 是 → !!! tip/note/warning/danger
│
└── 默认 → 直接展示
```

**🔴 CHECKPOINT · 🛑 STOP：排版完成后必须运行格式化脚本，不要跳过。**

## 反例清单（不要做什么）
---

### 排版反例

| # | 反模式 | 为什么不要做 | 替代做法 |
|---|--------|-------------|----------|
| 1 | **滥用 `/// details` 折叠重要内容** | 关键信息被隐藏，用户可能错过 | 核心概念、关键步骤直接展示，仅折叠可选阅读内容 |
| 2 | **使用 `!!! warning` 强调所有内容** | 警告框失去警示效果，用户产生视觉疲劳 | 区分 tip/note/warning/danger，按严重程度选择 |
| 3 | **Tab 标签页内放有依赖关系的内容** | 用户可能跳过前置步骤直接看后续内容 | 有依赖关系的内容使用顺序列表，不要 Tab |
| 4 | **H2/H3 标题后不加 `---` 分割线** | 章节之间视觉分隔不清晰 | 严格遵循格式化脚本的标题分割线规则 |
| 5 | **图片使用相对路径 `./assets/...`** | 不同页面层级下路径可能失效 | 使用 `/assets/...` 绝对路径 |
| 6 | **列表项之间留空行** | 列表间距不一致，影响阅读流畅性 | 同一组列表的列表项之间不留空行 |

### 配置反例

| # | 反模式 | 为什么不要做 | 替代做法 |
|---|--------|-------------|----------|
| 1 | **缺少 `pymdownx.blocks.details` 扩展** | `/// details` 语法无法渲染 | 确保 `markdown_extensions` 包含所有必需扩展 |
| 2 | **`theme.name` 设置为非 `shadcn`** | 主题样式不生效 | 必须设置为 `shadcn` |
| 3 | **不运行格式化脚本直接提交** | 标题分割线、图片居中等格式不统一 | 每次排版后必须运行 `format.py` |

### 内容反例

| # | 反模式 | 为什么不要做 | 替代做法 |
|---|--------|-------------|----------|
| 1 | **在 Tab 中放完全相同的重复内容** | 浪费空间，没有实际价值 | 每个 Tab 展示有差异的内容（如不同平台的命令） |
| 2 | **Details 标题写"点击查看详情"** | 标题无信息量，用户不知道内容是什么 | 使用具体描述：`❓ 什么是 XXX？` 或 `📖 XXX 配置说明` |
| 3 | **Warning 框内写长篇大论** | 警告框应该简短有力 | 长内容放在正文中，Warning 只保留关键警示 |
| 4 | **在代码块中放配置文件路径** | 路径容易出错，且不易维护 | 使用相对路径或变量，避免硬编码 |
| 5 | **使用过时的语法或插件** | 可能导致兼容性问题 | 参考最新的官方文档，使用推荐的语法 |
| 6 | **在 Details 中放核心概念** | 用户可能错过关键信息 | 核心概念直接展示，仅折叠可选阅读内容 |
