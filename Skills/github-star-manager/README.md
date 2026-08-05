# gh-star-manager

> 你的 GitHub Stars 已经过千了，找东西像在垃圾堆里翻。这个 Skill 让你的 Agent 一句话整理完——写回前先备份，只清理垃圾不碰宝贝。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.6%2B-blue.svg)](https://www.python.org/)
[![Agent Skills](https://img.shields.io/badge/Agent-Skills-purple.svg)](https://agentskills.io/)

---

## 🆚 它和 npm 上的 github-star-manager 有什么不同？

| 维度 | npm github-star-manager | **gh-star-manager（本 Skill）** |
|:---|:---|:---|
| **安装** | 需装 Node/Bun + npx | **无需安装**，装进 Agent 即用 |
| **LLM 配置** | 需配 OpenRouter/Gemini API Key | **无需配置**，复用宿主 Agent 智能 |
| **运行环境** | 绑死 Node.js 运行时 | **跨 runtime**：Claude Code / OpenCode / OpenClaw / Hermes 等 Agent Skills 兼容 |
| **备份** | 自动备份 | **强制备份** + 一键恢复 + Lists 原样回填 |
| **整理模式** | 单一硬编码模式 | **三级整理模式**：`conservative`(保守) / `moderate`(中等,默认) / `aggressive`(激进) |
| **清理与改表** | 仅支持基础 unstar | **全自动化 GraphQL 改表**：支持打标归类、新建 List、合并 List 及删除空 List |

**一句话**：你不用装 Node，不用配 LLM Key，你的 Agent 自带智能，它只负责把判断安全地写回 GitHub。

---

## 🛠️ 快速开始

### 1. 准备凭证
需要一个 GitHub 账号的 **Classic** 个人访问令牌（PAT），需包含以下 scope 权限：
- `public_repo` (读写公开仓库 star)
- `read:user` (读取用户信息)
- `user` (Lists 相关的创建、修改、删除与管理权限)

👉 [前往 GitHub 获取 Token (Classic)](https://github.com/settings/tokens) → 点击 `Generate new token (classic)`。

### 2. 配置环境变量与整理模式
本 Skill 严格从本 Skill 目录下的 `.env` 文件独占加载配置（避免多重来源冲突与环境干扰）。

在 `.env` 中配置凭证与整理模式：

```bash
# GitHub 访问 Token
GITHUB_TOKEN=ghp_xxxxxxxxxxxx

# 整理模式选择: conservative (保守) | moderate (中等, 默认) | aggressive (激进)
STARS_ORGANIZE_MODE=moderate

# 可选精细控制参数（默认已注释，取消注释后可手动覆盖各模式的默认策略与阈值）:
# STARS_STALE_YEARS=2
# STARS_LOW_STARS_THRESHOLD=100
# STARS_UNSTAR_LIMIT=50
# STARS_UNSTAR_SAFE_THRESHOLD=5000
# STARS_AI_SAMPLE_SIZE=60
# STARS_AI_BATCH_SIZE=30
```

#### ⚙️ 三种整理模式说明

| 模式 | List 新建/合并/删除策略 | Unstar 清理策略 |
| :--- | :--- | :--- |
| **conservative (保守)** | 严格禁止新建、合并或删除 List；所有 Repo 仅打标归入已有 List | 严格禁止 Unstar 任何项目 |
| **moderate (中等, 默认)** | 适当鼓励新建 List（当某主题 Repo 数量 ≥ 2 时建议新建）；鼓励合并重叠 List；自动建议删除空 List | 仅清理已归档且 Star 数较低 (<100) 或长期停更的仓库 |
| **aggressive (激进)** | 积极重构全量 List 体系，合并相似/冗余 List、删除无用空 List、按特定领域建立精细化新 List | 积极清理低价值/过时/Fork/低星 (<200) 仓库 |

### 3. 验证凭证
通过运行脚本验证 Token 和 scopes 状态：
```bash
python scripts/star_ops.py user
python scripts/star_ops.py check-scopes
```
返回 `can_create_lists: true` 即表示已就绪。

---

## 💬 触发方式

向支持 Agent Skills 的智能体说：

- **全量整理**：`"帮我整理一下我的 GitHub stars，现在太乱了"`
- **指定模式整理**：`"按激进模式帮我整理 GitHub stars 并清理空 List"`
- **一键导入评估**：`"一键导入这几个仓库，帮我评估要不要收藏：openai/whisper, ..."`
- **批量收藏与归类**：`"帮我把这几个仓库加入收藏并自动归类：pytorch/pytorch, vllm-project/vllm"`
- **清理废弃库**：`"帮我清理一下 stars 里已经长期未更新或废弃的项目"`
- **备份恢复**：`"把 stars 恢复到上个星期整理前的备份状态"`
- **状态检查**：`"检查一下我的 GitHub Token 权限是否正常"`

---

## 📖 使用示例

### 示例 1：全量整理 Stars（网页确认与一键写回）

- **场景**：`"帮我整理一下我的 GitHub stars，太多了想找东西很不方便"`
- **产出**：读取 `.env` 配置的模式 → 同步 stars 与画像 → 生成包含归类、新建 List 或删除 List 的方案 → 自动打开网页确认页 → 用户在页面微调 → 点击「确认执行写回」完成同步
- **要点**：服务端执行前强制备份；网页可自由二次调整；调整偏好自动沉淀进用户画像

### 示例 2：一键导入并评估（AI 三段式结构化总结与 Issues 风险）

- **场景**：`"一键导入这几个仓库并帮我评估要不要收藏：openai/whisper, ggml-org/llama.cpp"`
- **产出**：抓取每个 repo 的 README 与近期 Open Issues → 由 AI 提炼三段式评估卡片（🎯产品定位、🚀核心特色、⚠️Issues 风险与宣传符合度）→ 在内置全量 Lucide SVG 图标的网页上直观呈现代确认 → 确认后导入并归类
- **要点**：判断基于 README 实际功能与 Issues 反馈；替代了原有的 raw README 截断；有严重质量问题的 repo 建议不导入（reject）

### 示例 3：仅清理无用 Stars

- **场景**：`"帮我清理一下 stars 里已经废弃的项目"`
- **产出**：分析并列出建议 unstar 的 repos（废弃/损坏/搞笑/过时 fork），网页确认后执行
- **要点**：让用户选择清理条件（archived/stale/deprecated 等）；仅处理用户确认的 repo

### 示例 4：从备份恢复

- **场景**：`"上次整理出了问题，帮我恢复之前的 stars"`
- **产出**：列出可用备份，用户选择后对比差异，恢复缺失的 stars 与 List 归属
- **要点**：展示备份内容和差异，让用户确认后再执行恢复

---

## 🛡️ 安全边界

1. **凭证隔离**：绝对不会在日志、临时文件或 CLI 命令参数中暴露 `GITHUB_TOKEN`，仅从本 Skill 目录下的 `.env` 文件严格加载。
2. **零本地持久化与中间产物自动擦除**：
   - Stars 数据不进行本地长期保存。分类会话产生的所有临时 JSON 方案与中间文件在用户确认写回后均会自动擦除清理。
3. **读写隔离与二次确认**：
   - 所有的 `batch-set-lists`（批量分类写回）、`delete-list`（删除 List）与 `batch-unstar`（批量取消收藏）在执行前**必须向用户明文展示修改方案**并获得用户的明确授权。
   - 任何写操作触发时，均会强行生成一份 `~/.github-stars-backup/backup_*.json` 备份。
4. **大额 Unstar 限制与高星保护**：
   - 默认禁止单次处理超过 50 个 unstar 项目。
   - 对 Star 数量高于 5k 的项目进行黑名单过滤，避免误删高价值库。

---

## 📂 目录结构

```
github-star-manager/
├── SKILL.md                    # Agent 工作流编排指南
├── README.md                   # 本文件
├── LICENSE                     # MIT 许可证
├── test-prompts.json           # 触发意图与边界条件测试集
├── scripts/
│   ├── utils.py                # Token 独占加载、模式解析、限流退避
│   ├── fetch_stars.py          # 并发分页拉取 Stars(--sync 同步状态与画像)
│   ├── star_ops.py             # star/unstar/备份恢复
│   ├── github_lists.py         # Lists 管理(create/update/delete/batch-set-lists)
│   ├── generate_review_plan.py # 根据三级整理模式生成 review_plan.json
│   ├── repo_insight.py         # 导入前抓取 README 摘要与 issues
│   ├── build_review.py         # 确认页静态模式
│   ├── review_server.py        # 确认页服务模式(一键执行写回)
│   └── state.py                # 用户画像与 stars 持续状态
├── assets/
│   └── review_template.html    # 确认页交互模板(占位符注入)
├── references/
│   └── analysis-guide.md       # AI 分类策略规范与 plan JSON 契约
└── tests/
    └── test_ratelimit.py       # 限流回归测试
```

---

## 🧪 运行回归测试

回归测试已与真实的 GitHub API 隔离，基于 Mock 库直接运行，不耗费 Token：
```bash
python tests/test_ratelimit.py
```

---

## ⚖️ 许可证

本项目基于 [MIT](LICENSE) 许可证开源。
