---
name: image-upload
description: scan a document's local image references and upload to ImgBB / Freeimage / UploadMe / ImgLink, replacing links in-place. Use when the user says "上传图片", "replace local image links", "全量转存", "mirror images", "scan and upload images", "图床化".
---

# 图床化 Skill

扫描文档（Markdown / HTML）中的本地图片引用，上传至图床，将本地路径替换为远程 URL。

## 执行步骤

### Step 1 — 确定模式

根据用户意图选择模式：
- **document 模式**：用户指定一篇文档 → 扫描其中的本地图片引用（`![](./...)` / `<img src="...">`）
- **single 模式**：用户指定单张图片文件 → 直接上传，返回 URL
- **mirror 模式**：用户要求"全量转存"/"把文档里所有图片（含网络图片）搬到我的图床" → 扫描本地 + 文档内已有的远程 URL 图片，一并转存

_完成标准：模式已确定，目标文件路径 / 图片路径已明确。_

### Step 2 — 加载配置

运行 `node scripts/upload.mjs --help` 确认脚本可用，然后查找 `.env` 文件（搜索顺序：当前目录 → Skill 目录 → `~/.claude/` → `~/`）。

读取 `IMAGE_UPLOAD_PROVIDER`（默认 `imglink`）和对应的 API Key 环境变量。

**如果 API Key 缺失**（出现 `Missing *_API_KEY` 错误）：
1. 展示对应图床的 API Key 获取链接（见 [`references/providers.md`](references/providers.md)）
2. 询问用户粘贴 Key
3. 将 Key 写入 `.env` 文件（优先写到项目目录；如不存在则写到 `~/.claude/.env`）
4. 静默重试上传

_完成标准：API Key 已就绪，provider 已确认；或用户明确放弃。_

### Step 3 — 上传

根据模式调用脚本：

```bash
# document 模式（仅打印映射表）
node scripts/upload.mjs /path/to/document.md

# document 模式（原地替换链接）
node scripts/upload.mjs /path/to/document.md --replace

# mirror 模式（含网络图片，原地替换）
node scripts/upload.mjs /path/to/document.md --mirror --replace

# single 模式
node scripts/upload.mjs /path/to/image.png
```

**SVG / 大文件**：若图片为 SVG 或超过当前 provider 单文件上限，自动切换到支持的 provider（详见 [`references/providers.md`](references/providers.md)）。不支持时跳过该图并保留原链接。

**mirror 幂等**：若远程图片的 host 已是目标图床域名，跳过再次转存。

_完成标准：所有扫描到的图片都有上传结果（成功 URL 或明确的跳过理由），无遗漏。_

### Step 4 — 输出结果

- **document 模式（无 `--replace`）**：输出映射表 `本地路径 → 远程直链 → Markdown 引用`
- **document 模式（有 `--replace`）**：确认文档已写回，报告替换数量
- **single 模式**：返回 URL、`![name](url)`、`<img src="url">`、`[IMG]url[/IMG]`

_完成标准：结果已展示给用户；替换模式下文档已实际写回磁盘。_
