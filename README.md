<p align="center">
  <img src="assets/claude-agent-skills.jpg" alt="Skills 架构图">
</p>

<p align="center">
  <img style="height: 50px;" src="https://readme-typing-svg.demolab.com?font=Noto+Sans+SC&weight=400&duration=3500&pause=2000&color=E78BE7&center=true&vCenter=true&random=false&width=200&lines=Customized+Skills+!" alt="Hello-vibe-typing-svg" />
</p>

<p align="center">
  <strong>作者精心开发与验证的 Agent Skills 集合，解决定制化需求</strong><br>
  <em>为 AI Agent 提供标准化、可复用的能力包</em>
</p>

---

## 什么是 Skills？

**Skills** 是可供重复使用的能力包。无论是"发送邮件"还是"文件上传"，这些成熟功能都可以封装成 Skill，让 Agent 和 MCP 像使用工具一样直接调用。

它通过固定的规则和标准化的能力，保证输出结果的稳定和一致。

### 使用场景示例

假设你要搭建一个网站，需要用户系统：

- 直接使用现成的「用户鉴权 Skill」接入登录验证
- 使用「手机验证码注册 Skill」搞定注册流程

这就是 Skills 带来的便利——**复用成熟方案，避免重复造轮子**。

---

## 项目包含的 Skills

| Skill | 说明 |
|-------|------|
| [**stop-chinese-slop**](Skills/stop-chinese-slop/SKILL.md) | 去除中文文本中的 AI 腔、翻译腔、套话、黑话和公式化表达，让表达更自然、直接、精炼、具体 |
| [**dify-deploy**](Skills/dify-deploy/SKILL.md) | 通过 ADMIN_API_KEY 自动化调用 Dify Console API，创建工作流应用、导出/导入 DSL |
| [**dify-workflow**](Skills/dify-workflow/SKILL.md) | 根据需求设计并生成 Dify 工作流 DSL，支持创建或更新 workflow/advanced-chat 应用并部署到 Dify 平台，与 dify-deploy skill 搭配使用 |
| [**ideological-self-report**](Skills/ideological-self-report/SKILL.md) | 帮助用户撰写符合规范的思想汇报文档，尤其适用于引导大学生定制思想汇报，提供预置模板并支持沉淀个人文档库 |
| [**mkdocs-shadcn**](Skills/mkdocs-shadcn/SKILL.md) | mkdocs-shadcn 主题 Markdown 排版与项目编排，包括 YAML 配置、扩展语法（admonition、details、tab、数学公式等）、文本对齐规范等 |


---

## 如何安装

```bash
npx skills add https://github.com/jspi-fu/customized-skills
```

---

<p align="center">
  <sub>如果本项目对你有帮助，欢迎 ⭐ Star 支持！</sub>
</p>
