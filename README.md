<div align="center">

<p align="center">
  <img style="height: 50px;" src="https://readme-typing-svg.demolab.com?font=Noto+Sans+SC&weight=400&duration=3500&pause=2000&color=E78BE7&center=true&vCenter=true&random=false&width=200&lines=Aeson+Skills+!" alt="Hello-vibe-typing-svg" />
</p>

#### 烨笙开发的 Agent Skills 集合，解决定制化需求

[![License](https://img.shields.io/badge/License-MIT-3B82F6?style=for-the-badge)](./LICENSE)
[![Skills](https://img.shields.io/badge/Skills-6-10B981?style=for-the-badge)](#-skills)
[![AgentSkills](https://img.shields.io/badge/AgentSkills-Standard-8B5CF6?style=for-the-badge)](https://agentskills.io)

</div>

为 AI Agent 提供标准化、可复用的能力包。每个 Skill 都是 Agent 能直接加载的结构化指令集，遵循 [Agent Skills](https://agentskills.io) 开放标准。通过固定的规则和标准化的能力，保证输出结果的稳定和一致。

---

## 📋 目录

| 名字 | 一句话 | 链接 |
|---|---|---|
| 🚫 [**stop-chinese-slop（去 AI 腔）**](#-stop-chinese-slop去-ai-腔) | 去除中文文本中的 AI 腔、翻译腔、套话、黑话和公式化表达 | [SKILL.md](./Skills/stop-chinese-slop/SKILL.md) |
| 🚀 [**dify-deploy（Dify 部署）**](#-dify-deploydify-部署) | 通过 ADMIN_API_KEY 自动化调用 Dify Console API，创建工作流应用、导入导出 DSL | [公众号文章](https://mp.weixin.qq.com/s/Fm1vmyrbKOjeCNQBDD24Bw) |
| 🔧 [**dify-workflow（Dify 工作流）**](#-dify-workflowdify-工作流) | 根据需求设计并生成 Dify 工作流 DSL，与 dify-deploy 搭配使用 | [公众号文章](https://mp.weixin.qq.com/s/Fm1vmyrbKOjeCNQBDD24Bw) |
| 📝 [**ideological-self-report（思想汇报）**](#-ideological-self-report思想汇报) | 帮助撰写符合规范的思想汇报文档，提供预置模板并支持沉淀个人文档库 | [SKILL.md](./Skills/ideological-self-report/SKILL.md) |
| 📖 [**mkdocs-shadcn（文档排版）**](#-mkdocs-shadcn文档排版) | MkDocs Shadcn 主题 Markdown 排版与项目编排，含 YAML 配置、扩展语法等 | [排版示例](https://hello-vibe.netlify.app/) |
| � [**image-upload（文档图床化）**](#-image-upload文档图床化) | 扫描文档中的本地/网络图片并批量上传至图床（ImgBB / Freeimage / UploadMe / ImgLink），自动替换为直链，支持全量转存与内容指纹去重 | [公众号文章](https://mp.weixin.qq.com/s/bWuH9pXnH3L2ablM_2GbuA) |

---

## 📦 安装方式

**方式一：npx 一键安装**

```bash
npx skills add https://github.com/jspi-fu/Aeson-skills
```

**方式二：对话式安装**

在支持 Skill 的 Agent 里，直接说：

```
帮我安装这个 skill：https://github.com/jspi-fu/Aeson-skills
```

Agent 会自己 clone 到对应目录，不用你操心路径。

---

## ✨ Skills

<table>
<tr><td>

### 🚫 stop-chinese-slop（去 AI 腔）

> *"让文字重新说人话。"*

中文互联网上的 AI 生成内容越来越多——「赋能」「抓手」「闭环」「在当今 XX 快速发展的时代」，一看就知道是机器写的。

这个 Skill 专门干一件事：把你丢进来的中文文本，**去掉 AI 腔、翻译腔、套话、黑话和公式化表达**，让文字变得自然、直接、精炼、具体。

**适合**

- 改 AI 生成的营销文案、公众号文章、产品介绍
- 清理翻译过来的技术文档里的翻译腔
- 让正式文件去掉官话套话

→ [SKILL.md](./Skills/stop-chinese-slop/SKILL.md)

</td></tr>
</table>

<table>
<tr><td>

### 🚀 dify-deploy（Dify 部署）

> *"不用打开网页，命令行搞定 Dify 应用部署。"*

通过 Dify 的 ADMIN_API_KEY，自动化调用 Console API。一行命令创建工作流应用、导出 DSL 配置、导入已有 DSL 并部署——全程不需要手动操作 Dify 后台。

**它能做什么**

- 创建 workflow / advanced-chat 类型的应用
- 导出应用的 DSL 配置文件
- 导入 DSL 并自动创建或更新应用
- 与 `dify-workflow` Skill 搭配，从设计到部署一条龙

→ [SKILL.md](./Skills/dify-deploy/SKILL.md)

</td></tr>
</table>

<table>
<tr><td>

### 🔧 dify-workflow（Dify 工作流）

> *"描述需求，直接拿到能跑的工作流。"*

根据你的需求描述，自动设计并生成 Dify 工作流 DSL。支持创建或更新 workflow 和 advanced-chat 类型的应用，生成的 DSL 可以直接交给 `dify-deploy` 部署到 Dify 平台。

**适合**

- 快速搭建 Dify 工作流原型
- 批量生成标准化的工作流模板
- 不熟悉 Dify 可视化编辑器但想快速出活

→ [SKILL.md](./Skills/dify-workflow/SKILL.md)

</td></tr>
</table>

<table>
<tr><td>

### 📝 ideological-self-report（思想汇报）

> *"帮你把想说的话，写成该有的格式。"*

专门为大学生设计的思想汇报写作助手。提供符合规范的预置模板，引导你一步步完成内容填充，写完还能沉淀成个人文档库，下次写的时候有参考。

**它会做什么**

- 提供标准格式的思想汇报模板
- 引导式填充，不用对着空白页发呆
- 支持沉淀个人文档库，越写越顺

→ [SKILL.md](./Skills/ideological-self-report/SKILL.md)

</td></tr>
</table>

<table>
<tr><td>

### 📖 mkdocs-shadcn（文档排版）

> *"Markdown 写文档，也能好看。"*

[MkDocs Shadcn 主题](https://asiffer.github.io/mkdocs-shadcn/)的完整排版指南。从 YAML 配置到扩展语法（admonition、details、tab、数学公式），从文本对齐到项目编排，一个 Skill 搞定所有文档排版需求。

**涵盖**

- YAML frontmatter 配置规范
- 扩展语法：admonition、details、tab、数学公式
- 文本对齐与排版规范
- 项目目录编排建议

→ [SKILL.md](./Skills/mkdocs-shadcn/SKILL.md)

</td></tr>
</table>

<table>
<tr><td>

### � image-upload（文档图床化）

> *"说一句话，文档里的图片全部上云。"*

扫描 Markdown / HTML 文档里的本地图片，一键上传到 [ImgBB](https://imgbb.com/)、[Freeimage](https://freeimage.host/)、[UploadMe](https://uploadme.me/) 或 [ImgLink](https://imglink.cc/)，自动把本地路径替换成可访问的直链——不用打开 PicGo，不用一张张手动上传。零外部依赖，Node.js 18+ 开箱即用。

**它能做什么**

- 扫描文档提取本地图片并批量上传，`--replace` 原地替换为图床直链
- 全量转存（`--mirror`）：本地图片 + 文档内已有的网络图片一并搬到目标图床
- 内容指纹去重：SHA-256 缓存 + HEAD 存活校验，相同图片跨次运行不重复上传
- 四家图床任选，仅 ImgLink 支持 SVG；缺 API Key 时引导填写 `.env` 并自动重试

→ [SKILL.md](./Skills/image-upload-skill/SKILL.md)

</td></tr>
</table>

---

<div align="center">

[MIT License](./LICENSE) · 自由使用 / 修改 / 再分发

如果本项目对你有帮助，欢迎 ⭐ Star 支持！

</div>
