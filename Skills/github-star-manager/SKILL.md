---
name: github-star-manager
description: 整理、分类、清理、备份与恢复 GitHub Stars，或批量评估导入新项目。当用户要求整理/分类/清理/备份 GitHub 收藏、管理 star 列表(List)、批量评估仓库，或提到「GitHub Stars 整理 / 清理收藏 / star 太多」时使用。支持 organize/import/backup 模式；凭证通过环境变量或 WorkBuddy 的 GitHub 连接器注入，无需在 Skill 目录内放置 .env。
---

# GitHub Stars Manager

## 前置准备与配置

- **凭证需求**: GitHub Classic PAT，需 `public_repo` + `read:user` + `user` scope。
- **环境要求**: Python >= 3.6，`pip install requests` (>= 2.28)。
- **配置来源 (级联解析)**: 不再强制依赖 Skill 目录内的 `.env`，而是按以下优先级依次读取（每个 key 取最高优先级来源；**已存在的真实环境变量永不覆盖**）：
  1. 进程环境已有的变量（WorkBuddy/连接器注入的 `GITHUB_TOKEN`、shell 环境变量）；
  2. `GH_STAR_MANAGER_ENV` 指向的显式 `.env` 路径（可指向 WorkBuddy 托管的密钥文件）；
  3. 用户级 `~/.gh-star-manager/.env`（随用户在各工作区/项目间通用）；
  4. Skill 根目录 `.env`（仅作向后兼容遗留）。
- **凭证推荐**: `GITHUB_TOKEN` 优先放在 shell 环境变量或 `~/.gh-star-manager/.env`，避免在 Skill 目录内写 `.env`（防止被打包/更新覆盖或误提交泄露）。
- **工作目录隔离**: 所有会话中间产物（`stars.json`、`review_plan.json`、`review.html` 等）与状态文件统一落在专用工作目录 `~/.gh-star-manager/`（可用 `GH_STAR_MANAGER_WORKDIR` 覆盖为任意 WorkBuddy 托管路径），**绝不污染当前项目目录**。执行脚本时请把 `-o` 输出路径指向该目录。
- **交互模式 (`GH_STAR_MANAGER_REVIEW_MODE`)**: 
  - `chat`（WorkBuddy 推荐）: 不启动浏览器，由 Agent 在对话中呈现方案摘要、征求明确授权后直接调用 CLI 写回，最贴合 Agent 循环；
  - `static`: `build_review.py` 生成 `review.html`，由 Agent 通过 `present_files` 内联预览，用户在对话中确认；
  - `server`（仅独立桌面场景）: 旧版本地 Web 服务自启自毁，Agent 环境不建议使用。
- **写操作闸门**: 任何写回/改动操作执行前，必须依次完成：`Checkpoint(自动备份)` -> `展示方案` -> `明确授权确认`。
- **安全边界**: 
  - **高星保护**: star 数 ≥ 5000 的 repo 默认排除在 unstar 之外；单次 unstar 上限 50 项。
  - **凭证隔离**: `GITHUB_TOKEN` 仅留存环境变量与 `.env`，严禁随 JSON、日志或 CLI 参数暴露。

## 配置自愈 (Self-Healing)

若脚本报 `Missing GITHUB_TOKEN` 或 `401 Unauthorized`:
1. 输出 https://github.com/settings/tokens 向用户询问 Token；
2. 写入用户级 `~/.gh-star-manager/.env`（`GITHUB_TOKEN=ghp_xxx`，目录不存在时自动创建）；
3. 自动重跑先前失败的命令，无需用户重复指示。

## 在 WorkBuddy 中自由使用

该 Skill 已与 WorkBuddy 的运行环境解耦，无需把密钥写进 Skill 目录即可随处调用：

- **方式零（最推荐，零配置）**: 在 WorkBuddy 连接器页连上 **GitHub** 连接器。连接后 `GITHUB_TOKEN` 由 WorkBuddy 托管并自动注入脚本环境，脚本因「真实环境变量优先」规则直接生效——这是最契合生态、密钥不落地的用法。
- **方式一（零文件）**: 在 shell 启动脚本或 WorkBuddy 的环境变量配置里设置 `GITHUB_TOKEN`，脚本会优先读取真实环境变量，永不覆盖。
- **方式二（随用户通用）**: 创建 `~/.gh-star-manager/.env`，所有工作区/项目共用同一份配置。
- **方式三（指向托管密钥）**: 设置环境变量 `GH_STAR_MANAGER_ENV=/path/to/secret.env`，把配置指向 WorkBuddy 或密钥管理器生成的文件。
- **遗留兼容**: 仍可在 Skill 根目录放置 `.env`，但仅作为最低优先级兜底，且易被打包/更新覆盖，不建议。

## 操作流程 (Steps)

### 步骤 1: 凭证验证与状态同步

> 脚本位于本 Skill 目录下（通常为 `~/.workbuddy/skills/github-star-manager/scripts/`），执行时请使用 Skill 的**绝对路径**；所有 `-o` 输出请指向工作目录 `~/.gh-star-manager/`。

```bash
python <skill_dir>/scripts/star_ops.py user; python <skill_dir>/scripts/star_ops.py check-scopes
python <skill_dir>/scripts/fetch_stars.py --sync -o ~/.gh-star-manager/stars.json
python <skill_dir>/scripts/github_lists.py list -o ~/.gh-star-manager/lists.json
```

> **完成准则**: `can_create_lists` 为 true；`fetch_stars.py` 与 `github_lists.py` 返回 `status: success`（退出码 0）。

### 步骤 2: 生成方案 (`review_plan.json`)

先读取用户画像 `python <skill_dir>/scripts/state.py dump-profile`。依据用户意图选择对应分支：

- **全量整理分支 (`mode: organize`)**:
  - 运行 `python <skill_dir>/scripts/generate_review_plan.py --plan-mode organize -o ~/.gh-star-manager/review_plan.json`；
  - 详细分类策略、意图驱动标签锁定 (`FROZEN`)、解散泛化标签与预设模式（`STARS_ORGANIZE_MODE`）严格遵循 [references/analysis-guide.md](references/analysis-guide.md)；
  - 产出包含建议 List 归属与 unstar 建议的 `review_plan.json`。

- **批量导入分支 (`mode: import`)**:
  - 将待评估 repo 写入 `~/.gh-star-manager/new_repos.json` 格式 `["owner/repo", ...]`；
  - 抓取摘要: `python <skill_dir>/scripts/repo_insight.py --input-file ~/.gh-star-manager/new_repos.json -o ~/.gh-star-manager/insights.json`；
  - 运行 `python <skill_dir>/scripts/generate_review_plan.py --plan-mode import --insights-file ~/.gh-star-manager/insights.json -o ~/.gh-star-manager/review_plan.json` 产出包含建议 List 归属的 `review_plan.json`。


> **完成准则**: 成功生成符合契约规范的 `review_plan.json`。

### 步骤 3: 方案确认与写回 (WorkBuddy 原生流程)

在 WorkBuddy 的 Agent 循环里，**不启动本地浏览器服务**，而是用对话驱动，三种模式按 `GH_STAR_MANAGER_REVIEW_MODE` 选择：

- **(推荐) chat 模式**: 直接读取 `~/.gh-star-manager/review_plan.json`，在对话中以清晰列表呈现建议（新建/合并 List、unstar 清单、标星归类），明确列出将要执行的写操作；得到用户**显式授权**后，严格遵循写操作闸门（先备份再执行），依次调用 `github_lists.py` 与 `star_ops.py` 批处理 CLI 完成写回（写回细节见 [references/analysis-guide.md](references/analysis-guide.md)）。

- **static 模式 (可视化预览)**: 生成可交互 HTML 供用户在对话内预览与核对：
  ```bash
  python <skill_dir>/scripts/build_review.py --plan-file ~/.gh-star-manager/review_plan.json --output ~/.gh-star-manager/review.html
  ```
  随后用 `present_files` 将 `review.html` 内联预览给用户；用户在对话中确认或调整，Agent 再按授权执行 CLI 写回。

- **server 模式 (仅独立桌面)**: `python <skill_dir>/scripts/review_server.py --plan-file ~/.gh-star-manager/review_plan.json` 启动本地 Web 服务并自动开浏览器、确认后强制先备份再执行并 3 秒自毁。**Agent 环境不要使用此模式**。

> **完成准则**: 用户在对话中明确授权后，CLI 写回成功（备份已完成、退出码 0）；或 static 模式下用户确认且 Agent 已执行授权写回。

### 步骤 4: 偏好蒸馏 (Preference Distillation)

交互结束后，对比用户最终方案与原始建议，将差异总结为偏好规则追加至画像：
```bash
python scripts/state.py add-preference "规则描述"
```

### 步骤 5: 备份与恢复 (可选)

查看与加载备份、恢复 stars/List 归属的具体 CLI 指令见 [references/analysis-guide.md#备份与恢复流程](references/analysis-guide.md#备份与恢复流程)。

## 异常降级与资源索引

- **GraphQL API 变更**: 降级为输出 Markdown/Awesome-list 结构化报告。
- **服务启动失败**: 降级至静态模式 (`build_review.py`) 导出 JSON 执行。
- **资源索引**: [scripts/fetch_stars.py](scripts/fetch_stars.py) | [scripts/github_lists.py](scripts/github_lists.py) | [scripts/star_ops.py](scripts/star_ops.py) | [scripts/review_server.py](scripts/review_server.py) | [scripts/state.py](scripts/state.py)
