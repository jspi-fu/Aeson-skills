## 整理模式与配置策略 (`STARS_ORGANIZE_MODE`)

环境配置文件 `.env` 中通过 `STARS_ORGANIZE_MODE` 设定整理模式，默认为 `moderate`。可选的精细参数（如 `STARS_LOW_STARS_THRESHOLD`、`STARS_STALE_YEARS` 等）在 `.env` 中**默认注释**，以便系统按当前模式的预设策略自动运行；用户仅在需要覆盖默认模式逻辑时方可手动取消注释。

### 三种整理模式对照表

| 模式 | List 新建/合并/删除策略 | Unstar 清理策略 | 默认预设阈值 |
| :--- | :--- | :--- | :--- |
| **conservative (保守)** | 严格禁止新建、合并或删除 List；所有 Repo 仅打标归入已有 List | 严格禁止 Unstar 任何项目 | 禁用清理与改表 |
| **moderate (中等, 默认)** | 适当鼓励新建 List（当某独立主题 Repo 数量 ≥ 2 时建议新建）；鼓励合并重叠 List；自动建议删除空 List | 仅清理已归档且 Star 数较低 (<100) 或长期停更的仓库 | 低星阈值: 100, 安全保护线: 5000 |
| **aggressive (激进)** | 积极重构全量 List 体系，合并相似/冗余 List、删除无用空 List、按特定领域建立精细化新 List | 积极清理低价值/过时/Fork/低星 (<200) 仓库 | 低星阈值: 200, 安全保护线: 5000 |

## 标签管理与保护规则

### 1. 禁用宽泛“兜底型”标签
- **原则**：严禁使用“大模型相关”、“小工具”等无明确技术或业务边界的泛化兜底 List。
- **解散处理**：若用户账户中已存在此类泛化 List，AI 方案应直接将其标记为**解散**（进入 `delete_list_ids` / `dissolved_lists`）。
- **重分配**：原归属于该泛化 List 的 Repo 视为未归类，按照优先其他具体领域 List 或新建精细 List 的策略重新分配。

### 2. “意图驱动”标签保护与锁定
- **定义**：非客观领域划分、依赖用户个人主观场景的标签（如“毕设”、“项目参考”、“待学习”）。
- **询问机制**：在生成分类方案前，Agent 必须主动询问用户具体意图方向（例如：“注意到您有[毕设]分类，请问您的毕设具体研究方向是什么？”）。
- **约束规则**：
  - **未回答/跳过**：触发硬性锁定 (`FROZEN`)，AI 自动方案**禁止新增**任何项目入该 List，且**严禁移出/删除**现有项目。
  - **已回答方向**：记录入画像，AI 方案允许将符合该具体方向的新项目归入该 List，但**依然严禁移出/删除原项目**。
  - *注：上述约束仅作用于 AI 方案自动生成；网页确认 UI 上用户的**手动勾选与调整无任何限制**。*

- [阶段一:分类建议生成](#阶段一分类建议生成)
- [阶段二:批量分类](#阶段二批量分类)
- [批量导入评估](#批量导入评估)
- [新增项目归类策略](#新增项目归类策略)
- [Unstar 清理策略](#unstar-清理策略)
- [plan JSON 契约](#plan-json-契约)

## 画像运用

分析开始前必须读取画像:

```bash
python scripts/state.py dump-profile
```

- **stats** 提供语言/话题分布与近 90 天 star 记录,用于理解用户关注面;
- **insights** 为既往归纳的研究方向/近期关注方向,分类命名与归组应与其一致;若为空或明显过时,分析结束后按 [SKILL.md 步骤 6.5] 更新;
- **preferences** 是用户历次二次调整沉淀的规则,**约束力高于本文档的一般策略**——与之冲突时以偏好为准(除非用户本次明确推翻)。

## 阶段一:分类建议生成

### 分层采样策略

stars 数量 > 100 时,按语言比例分层采样 `STARS_AI_SAMPLE_SIZE`(默认 60)个 repo 分析:

1. 统计所有 repo 的语言分布
2. 按语言占比分配采样名额,每种语言至少 1 个
3. 在每个语言组内随机采样

### 分析维度

- **用途**: 工具/库/学习资源/框架/应用
- **领域**: Web/AI-ML/DevOps/移动端/数据/安全/基础设施
- **活跃度**: 基于 pushed_at 判断最近活跃时间
- **语言**: 主要编程语言

### 分类原则

- 按用途或领域分组,而非仅按语言
- 每个分类有明确描述,说明什么类型的 repo 归入此类
- 建议 5-8 个分类
- 优先复用画像 insights 中的研究方向作为分组骨架;与现有 Lists 避免重复

### 分类建议输出格式

```json
{
  "lists": [
    {
      "name": "AI/ML Tools",
      "description": "AI and machine learning tools, frameworks, and utilities",
      "keywords": ["machine-learning", "deep-learning", "pytorch", "tensorflow"]
    }
  ]
}
```

## 阶段二:批量分类

### 分批处理

每批 `STARS_AI_BATCH_SIZE`(默认 30)个 repo 独立分析。

### 分类决策

| 决策 | 含义 | 条件 |
|------|------|------|
| categorize | 归入某个 List | repo 符合某个分类的描述 |
| keep | 保持不变 | 已在合适的 List 中,或不属于任何分类 |
| unstar | 建议取消 star | 仅用于明确废弃/损坏的 repo(保守策略) |

### 批量分类 Prompt 模板

对每批 repo,构建如下分析请求:

```
将以下 GitHub repos 分类到对应 List。

List 列表(使用编号):
1. AI/ML Tools
2. Web Development
...

操作说明:
- "categorize": 分配到新 List(使用编号 1-N)。一个 repo 可以在多个 List 中。
- "keep": 已分类良好或不属于任何 List。
- "unstar": 仅废弃/搞笑/损坏的 repo(保守!)

Repos:
- owner/repo1 | description | Python | star_count | age
- owner/repo2 | description | JavaScript | star_count | age

返回 JSON:
{
  "summary": "简要分类总结",
  "repos": [
    { "repo": "owner/name", "action": "categorize", "list": 1 },
    { "repo": "owner/name", "action": "keep" }
  ]
}
```

### 已有 List 处理

对于已在 List 中的 repo(标记为 `IN:[list_name]`):

- 已分类良好 → keep
- 适合其他 List → 额外 categorize

## 批量导入评估

输入为 `repo_insight.py` 的输出(README 摘要 + 近期 issues)。对每个 repo 产出**极简**判断:

- **match**(high/mid/low): 与画像 insights 的研究方向、preferences 规则、现有 Lists 主题的匹配度。判据示例: topics/语言命中画像高频项 → high;仅领域相关 → mid;无明显关联 → low。
- **reason**: 一句话说明为什么这样归类/匹配,如「LLM 推理框架,与你近期关注的 vLLM 同方向」。
- **issues_note**: 仅在 issues 暴露问题时填写,如「近 3 个月 40+ 个 bug report 无响应」「项目已停止维护」;健康项目省略此字段。
- **action**: 默认 `categorize`;match=low 且有明显问题时建议 `reject`;用户明确要求全部导入时全部 `categorize`/`keep`。

判断必须基于 insight 实际内容,禁止臆测 README 未提供的信息。

## 新增项目归类策略

### 核心原则: 优先现有组

1. **优先匹配现有 Lists**: 分析每个新 repo 与现有 List 名称和描述的语义匹配度
2. **尽量不开新组**: 完全不符合任何现有 List 主题时才建议新建
3. **用户手动指定优先**: 用户明确指定分组时直接采用

### 匹配流程

1. 获取现有 Lists 的名称和描述
2. 计算每个新 repo 与各 List 的语义相关度
3. 分配规则:
   - 高匹配: 直接归入
   - 中匹配: 归入但在方案中保留理由,供页面确认
   - 低匹配: 暂不归类(action=keep),汇总后由用户在页面决定
4. 未归类 repo 数量 >= 3 且主题相近 → 建议创建新 List;否则在页面由用户决定

## Unstar 清理策略

### 保守原则

| 建议 unstar | 不建议 unstar |
|-------------|--------------|
| 已废弃且有替代方案 | 已归档但仍有参考价值 |
| 搞笑/meme 项目 | 老旧但经典的稳定库 |
| 明确标记损坏/放弃 | 学习资源 |
| 过时的个人 fork | 高 star(5k+)项目 |

### 清理条件选项

用户可选清理条件,AI 分析时必须优先读取 `.env`/环境变量对应配置:

- **archived**: 被所有者标记为 archived 的 repo
- **stale**: 超过 `STARS_STALE_YEARS`(默认 2)年未更新
- **low_stars**: star 数低于 `STARS_LOW_STARS_THRESHOLD`(默认 100)
- **deprecated**: 有替代方案或标记为 deprecated
- **personal_fork**: 个人 fork 且已过时
- **joke_meme**: 搞笑/meme 项目

### 分析流程

1. 按用户选择的条件构建分析 prompt
2. 每批 `STARS_AI_BATCH_SIZE`(默认 30,纯 unstar 分析最大 `STARS_UNSTAR_LIMIT` 默认 50)个 repo
3. Star 数 ≥ `STARS_UNSTAR_SAFE_THRESHOLD`(默认 5000)强制排除,除非用户指名
4. 输出建议 unstar 的 repo 列表及原因

## plan JSON 契约

AI 分析的最终产物是 plan JSON(写入 `review_plan.json`),供确认页与服务端消费:

```json
{
  "mode": "organize",
  "generated_at": "2026-08-04 15:00",
  "lists": [{"id": "UL_xxx", "name": "AI/ML Tools", "description": "..."}],
  "new_lists": [{"id": "NEW_1", "name": "Rust Tools", "description": "..."}],
  "repos": [
    {
      "full_name": "owner/repo",
      "node_id": "R_xxx",
      "description": "...",
      "language": "Python",
      "stargazers_count": 1234,
      "archived": false,
      "action": "categorize",
      "list_ids": ["UL_xxx", "NEW_1"],
      "reason": "一句话归类理由",
      "match": "high",
      "issues_note": "仅在有问题时填写",
      "readme_excerpt": "仅 import 模式填写"
    }
  ]
}
```

字段要求:

- `mode`: `organize`(全量整理/清理)或 `import`(批量导入);
- `lists`: 现有 List 原样透传(来自 `github_lists.py list`);
- `new_lists`: 建议新建的 List,`id` 用 `NEW_N` 占位,服务端执行时替换为真实 id;
- `repos[].action`: organize 用 `categorize`/`keep`/`unstar`;import 用 `categorize`/`keep`/`reject`;
- `repos[].list_ids`: 该 repo 的**完整目标 List 集合**(全量替换语义,含要保留的已有归属);
- `reason`/`match`/`issues_note`/`readme_excerpt`: 展示用,保持极简;`reason` 每个 repo 必填。

### 备份数据格式

备份文件保存在 `~/.github-stars-backup/`,格式:

```json
{
  "timestamp": "20250117_120000",
  "stars": [{"full_name": "owner/repo", "...": "..."}],
  "lists": [
    {
      "id": "...", "name": "List Name", "description": "...",
      "is_private": false, "item_count": 12,
      "repos": [{"node_id": "R_xxx", "full_name": "owner/repo"}]
    }
  ]
}
```

`lists` 来自 `github_lists.py list --with-items`,每个 list 的 `repos` 为该 List 全部成员。

## 备份与恢复流程

备份可通过 CLI 查看与加载:

```bash
python scripts/star_ops.py list-backups
python scripts/star_ops.py load-backup --filepath ~/.github-stars-backup/backup_20250117_120000.json
```
*(注: 备份时若用 `--output-dir` 自定义目录,`list-backups` 亦需带相同的 `--output-dir`。)*

恢复操作分两步，均须先通过「写操作闸门」获得用户明确授权:

1. **恢复 stars**: 对比备份与当前 stars,将缺失 repo 写入 `restore_repos.json` 后执行 `python scripts/star_ops.py batch-star --input-file restore_repos.json`（单项失败记入 `failed` 结果并继续）。
2. **恢复 List 归类**（需备份为 `--with-items` 产物）:
   - 执行 `python scripts/github_lists.py list` 获取当前账户 Lists;
   - 缺失的 List 使用 `create` 重建并记录返回的新 `list_id`;
   - 构建 `batch-set-lists` 输入文件，回填成员——`node_id` 取自备份中该 List 的 `repos`;同一 repo 属于多个 List 时合并 `list_ids` 后统一回填。

