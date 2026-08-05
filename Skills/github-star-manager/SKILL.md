---
name: github-star-manager
description: 整理、分类、清理、备份恢复 GitHub Stars，或批量评估导入新项目。支持 organize/import/backup 模式。
---

# GitHub Stars Manager

## 前置准备与配置

- **凭证需求**: GitHub Classic PAT，需 `public_repo` + `read:user` + `user` scope。
- **环境要求**: Python >= 3.6，`pip install requests` (>= 2.28)。
- **配置隔离**: 仅从本 Skill 目录下的 `.env` 文件严格加载配置（`GITHUB_TOKEN=ghp_xxx`）。
- **写操作闸门**: 任何写回/改动操作执行前，必须依次完成：`Checkpoint(自动备份)` -> `展示方案` -> `明确授权确认`。
- **安全边界**: 
  - **高星保护**: star 数 ≥ 5000 的 repo 默认排除在 unstar 之外；单次 unstar 上限 50 项。
  - **凭证隔离**: `GITHUB_TOKEN` 仅留存环境变量与 `.env`，严禁随 JSON、日志或 CLI 参数暴露。

## 配置自愈 (Self-Healing)

若脚本报 `Missing GITHUB_TOKEN` 或 `401 Unauthorized`:
1. 输出 https://github.com/settings/tokens 向用户询问 Token；
2. 写入本 Skill 目录下的 `.env`（`GITHUB_TOKEN=ghp_xxx`）；
3. 自动重跑先前失败的命令，无需用户重复指示。

## 操作流程 (Steps)

### 步骤 1: 凭证验证与状态同步

```bash
python scripts/star_ops.py user; python scripts/star_ops.py check-scopes
python scripts/fetch_stars.py --sync -o stars.json
python scripts/github_lists.py list -o lists.json
```

> **完成准则**: `can_create_lists` 为 true；`fetch_stars.py` 与 `github_lists.py` 返回 `status: success`（退出码 0）。

### 步骤 2: 生成方案 (`review_plan.json`)

先读取用户画像 `python scripts/state.py dump-profile`。依据用户意图选择对应分支：

- **全量整理分支 (`mode: organize`)**:
  - 运行 `python scripts/generate_review_plan.py --plan-mode organize -o review_plan.json`；
  - 详细分类策略、意图驱动标签锁定 (`FROZEN`)、解散泛化标签与预设模式（`STARS_ORGANIZE_MODE`）严格遵循 [references/analysis-guide.md](references/analysis-guide.md)；
  - 产出包含建议 List 归属与 unstar 建议的 `review_plan.json`。

- **批量导入分支 (`mode: import`)**:
  - 将待评估 repo 写入 `new_repos.json` 格式 `["owner/repo", ...]`；
  - 抓取摘要: `python scripts/repo_insight.py --input-file new_repos.json -o insights.json`；
  - 运行 `python scripts/generate_review_plan.py --plan-mode import --insights-file insights.json -o review_plan.json` 产出包含建议 List 归属的 `review_plan.json`。


> **完成准则**: 成功生成符合契约规范的 `review_plan.json`。

### 步骤 3: 网页确认与写回 (两种模式)

- **服务模式 (推荐)**:
  ```bash
  python scripts/review_server.py --plan-file review_plan.json
  ```
  启动本地 Web 交互服务并自动打开浏览器。用户在页面确认写回后，服务端**强制先备份再执行**，并在 3 秒内自动安全关闭服务。Agent 接收服务输出结果。

- **静态降级模式 (兜底)**:
  ```bash
  python scripts/build_review.py --plan-file review_plan.json --output review.html --open
  ```
  用户导出修改后的方案 JSON 后，由 Agent 依据写操作闸门授权，依次调用 `github_lists.py` 与 `star_ops.py` 批处理 CLI 执行写回（参见 [references/analysis-guide.md](references/analysis-guide.md)）。

> **完成准则**: 接收到 Web 服务的写回成功回调，或用户提交导出 JSON 并明确授权 CLI 执行。

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
