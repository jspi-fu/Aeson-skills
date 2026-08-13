---
name: dify-deploy
description: 通过 ADMIN_API_KEY 自动化调用 Dify Console API（Node.js 驱动模式）。用于脚本化创建应用、导出 DSL 到文件、从大文件 YAML 导入或覆盖 DSL。
disable-model-invocation: true
---

# Dify Console Admin API (Node.js 驱动模式)

通过 `ADMIN_API_KEY` 自动化调用 Dify Console API。全流程采用 **Node.js 模版** 执行，避免大文件 DSL YAML 在命令行传输时出现命令行超长溢出或双引号转义失败。

## 适用场景

- 自动化创建工作流或高级编排应用。
- 将应用或工作流 DSL 导出并保存为本地 `.yml` 文件。
- 从本地 YAML 文件或远程 URL 导入 DSL 到 Dify（支持超大文件）。
- 覆盖导入现有工作流应用并进行异步状态确认。

---

## Phase 1: 配置加载与准备

参数保存在 `.dify_key/config.json`：

```json
{
  "DIFY_BASE_URL": "http://127.0.0.1:5001",
  "ADMIN_API_KEY": "sk-admin-xxx",
  "WORKSPACE_ID": "d4e26a01-162f-4366-9a25-1c2c1bdd15dz"
}
```

### 加载或自动获取配置

在当前工作区检查配置：
- 若 `.dify_key/config.json` 存在：直接读取配置。
- 若配置文件不存在：运行一键获取脚本：
  ```bash
  node ./scripts/fetch_keys.js
  ```
  *(注：请指向实际 Skill 部署路径下的 `scripts/fetch_keys.js`)*

---

## Phase 2: Node.js 操作引擎

所有 HTTP 请求均需包含标准鉴权头：
- `Authorization: Bearer ${ADMIN_API_KEY}`
- `X-WORKSPACE-ID: ${WORKSPACE_ID}`

---

### 分支 A：创建应用 (Create App)

使用 Node.js 发送创建请求：

```javascript
const fs = require('fs');
const config = JSON.parse(fs.readFileSync('.dify_key/config.json', 'utf-8'));

async function createApp(appName, description = '') {
  const res = await fetch(`${config.DIFY_BASE_URL}/console/api/apps`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${config.ADMIN_API_KEY}`,
      'X-WORKSPACE-ID': config.WORKSPACE_ID,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ name: appName, mode: 'workflow', description })
  });
  const data = await res.json();
  if (res.status === 201) {
    console.log(`应用创建成功! App ID: ${data.id}`);
    return data;
  } else {
    throw new Error(`创建失败 [${res.status}]: ${JSON.stringify(data)}`);
  }
}
```

**Completion Criterion**: 收到 HTTP Status `201 CREATED`，返回包含新创建应用的 `id`。

---

### 分支 B：导出 DSL 到本地文件 (Export DSL)

安全将云端 DSL 导出为本地 `.yml` 文件：

```javascript
const fs = require('fs');
const config = JSON.parse(fs.readFileSync('.dify_key/config.json', 'utf-8'));

async function exportDSL(appId, outputPath, includeSecret = false) {
  const url = `${config.DIFY_BASE_URL}/console/api/apps/${appId}/export?include_secret=${includeSecret}`;
  const res = await fetch(url, {
    headers: {
      'Authorization': `Bearer ${config.ADMIN_API_KEY}`,
      'X-WORKSPACE-ID': config.WORKSPACE_ID
    }
  });
  const json = await res.json();
  if (res.ok && json.data) {
    fs.writeFileSync(outputPath, json.data, 'utf-8');
    console.log(`DSL 成功导出至: ${outputPath}`);
  } else {
    throw new Error(`导出失败 [${res.status}]: ${JSON.stringify(json)}`);
  }
}
```

**Completion Criterion**: 收到 HTTP `200 OK`，本地 `outputPath` 成功写入非空 YAML 内容。

---

### 分支 C：从本地文件导入 DSL (Import DSL from Local YAML)

通过 Node.js 文件流直接读取大文件 YAML，解决 CLI 命令超长问题：

```javascript
const fs = require('fs');
const config = JSON.parse(fs.readFileSync('.dify_key/config.json', 'utf-8'));

async function importDSL(yamlFilePath, targetAppId = null) {
  const yamlContent = fs.readFileSync(yamlFilePath, 'utf-8');
  const payload = {
    mode: 'yaml-content',
    yaml_content: yamlContent
  };
  if (targetAppId) payload.app_id = targetAppId; // 覆盖导入模式

  const res = await fetch(`${config.DIFY_BASE_URL}/console/api/apps/imports`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${config.ADMIN_API_KEY}`,
      'X-WORKSPACE-ID': config.WORKSPACE_ID,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });

  const result = await res.json();
  return handleImportResponse(res.status, result, config);
}
```

---

## Phase 3: 异步状态确认与终态收敛 (Status Convergence)

当导入的大文件 DSL 处理较慢时，Dify 会返回 HTTP `202 ACCEPTED` 且状态为 `pending`。**必须自动进行 Confirm 确认直至收敛**。

```javascript
async function handleImportResponse(statusCode, responseJson, config) {
  if (statusCode === 200 || statusCode === 201) {
    console.log(`DSL 导入完成! App ID: ${responseJson.app_id || responseJson.id}`);
    return responseJson;
  }

  if (statusCode === 202 && responseJson.status === 'pending') {
    const importId = responseJson.id || responseJson.import_id;
    console.log(`导入任务排队中 (Import ID: ${importId})，开始自动 Confirm 确认...`);

    const confirmRes = await fetch(`${config.DIFY_BASE_URL}/console/api/apps/imports/${importId}/confirm`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${config.ADMIN_API_KEY}`,
        'X-WORKSPACE-ID': config.WORKSPACE_ID,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({})
    });
    const confirmData = await confirmRes.json();
    console.log(`Confirm 状态结果:`, confirmData);
    return confirmData;
  }

  throw new Error(`导入异常 [${statusCode}]: ${JSON.stringify(responseJson)}`);
}
```

**Completion Criterion**: 响应状态最终收敛为 `200/201`，且返回导入后的 `app_id`。

---

## 异常排查 (Troubleshooting)

- `401 Invalid token`:
  1. 检查 `.dify_key/config.json` 中的 `ADMIN_API_KEY` 是否正确。
  2. 确认服务端 `.env` 中已配置 `ADMIN_API_KEY_ENABLE=true`。
  3. 服务端修改 `.env` 后**必须重新启动 API 容器**（如 `docker compose up -d --force-recreate api`）。
- `Connection refused`:
  - 检查 `DIFY_BASE_URL` 地址是否连通，本地 Docker 部署通常为 `http://127.0.0.1:5001` 或 `http://localhost`。
