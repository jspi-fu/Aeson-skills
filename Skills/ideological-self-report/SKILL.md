---
name: ideological-self-report
description: 生成思想汇报（含入党积极分子、预备党员季度政治汇报）。在用户请求撰写或修改思想汇报、季度政治汇报材料时触发。
---

# 思想汇报生成技能

依据用户个性化风格配置与政治规范，生成标准化思想汇报文档。

## 辅助文件
- [requirements.md](file:///d:/源自C盘/桌面/Aeson-skills/Skills/ideological-self-report/references/requirements.md) — 格式、字数与政治规范（Single Source of Truth）
- [config_manager.py](file:///d:/源自C盘/桌面/Aeson-skills/Skills/ideological-self-report/scripts/config_manager.py) — 配置状态与风格管理脚本

---

## 执行步骤

### 步骤 1：状态检查与风格初始化

执行配置状态检查：
```bash
python <skill-path>/scripts/config_manager.py status
```

根据返回结果中的 `last_updated` 字段判定分支：

- **分支 A：未初始化（`last_updated` 为空）**
  1. 询问用户：`1. 提供历史思想汇报文件路径（分析风格）` 或 `2. 交互式填写基本信息`。
  2. **选项 1 流程**：
     - 获取用户提供的模板路径，执行扫描：`python <skill-path>/scripts/config_manager.py check`
     - 读取路径下的历史文件，提取字数分配、历史缺点记录、开篇句式、用户基本信息（姓名、身份、职务及时间线）。
     - 调用脚本保存分析结果：
       ```bash
       python <skill-path>/scripts/config_manager.py save-analysis --analysis-data '{"user_info":{...},"word_count":{...},"opening_patterns":[...],"historical_weaknesses":[...]}'
       ```
  3. **选项 2 流程**：
     - 收集姓名、身份及职务时间线。
     - 执行配置保存：`python <skill-path>/scripts/config_manager.py setup --name "姓名" --identity "身份" --positions "开始日期:职务名称"`

- **分支 B：已有配置（`last_updated` 非空）**
  1. 显示上次更新时间，询问用户是否更换配置。
  2. **选择更换**：执行重置 `python <skill-path>/scripts/config_manager.py reset`，随后进入分支 A。
  3. **选择不更换（自动更新）**：执行 `python <skill-path>/scripts/config_manager.py check` 检查增量文件，如有新文件则自动解析并追加至 `config.json` 的 `writing_style`。

**完成标准**：`config.json` 状态确认完成（`last_updated` 有效且 `writing_style` 字段完整）。

### 步骤 2：素材收集（热点与实效）

1. **时政热点 (步骤 2a)**
   - 优先读取用户提供的学习资料（如 MD 格式原文）。
   - 用户若请求推荐，则联网检索“2026年第一季度时政热点”，推荐至少 5 个选题供选择。
   - 确认选题后，阅读材料并提炼 3 项核心政治理论学习要点。
2. **个人事项 (步骤 2b)**
   - 询问本季度学习、工作、生活具体事项（及最新职务变更）。
   - 若用户选择跳过，则标记由 AI 结合身份配置合理推演生成。

**完成标准**：在完成步骤 2a（确定政治学习选题及核心要点）后，方可推进步骤 2b 及后续流程。

### 步骤 3：文本生成（政治对齐与差异去重）

读取 `config.json` 与 [requirements.md](file:///d:/源自C盘/桌面/Aeson-skills/Skills/ideological-self-report/references/requirements.md)，按照配置生成正文：
- **开篇句式**：执行 [句式去重]，创作新句式，禁止使用 `opening_patterns` 中已有的历史表述。
- **缺点与不足**：执行 [缺点去重]，从 `historical_weaknesses` 排除已用主题，选入全新缺点维度（150-200字，禁止模糊表述）。
- **政治对齐**：党章引用须与 [cpc-constitution.md](file:///d:/源自C盘/桌面/Aeson-skills/Skills/ideological-self-report/references/cpc-constitution.md) 原文严格一致；提及理论指导时须完整包含“习近平新时代中国特色社会主义思想”且排序正确。
- **严格限额**：各章节字数严格匹配 `word_count` 分配要求。

**完成标准**：草稿结构完整，覆盖思想政治、学习、工作、生活、缺点不足各模块。

### 步骤 4：质量检查（Quality Gate）

对照 [requirements.md](file:///d:/源自C盘/桌面/Aeson-skills/Skills/ideological-self-report/references/requirements.md) 逐项审核生成的思想汇报：
- 审查页面格式（标题居中、称谓顶格、落款居右等）。
- 检查禁用词与表述规范（确保使用“自从被确定为…”，排除“党性修养”等禁用词汇）。

**完成标准**：审查清单无未通过项，确认无事实编造或逻辑违规。

### 步骤 5：保存与交付

将思想汇报保存为 Markdown 文件：
- **命名规范**：`[用户姓名]思想汇报[YYYY-MM-DD].md`（例：`张三思想汇报2026-03-20.md`）。
- **落款一致性**：正文结尾落款日期须与文件名中的日期完全一致。
