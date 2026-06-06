---
name: dify-deploy
description: 通过 ADMIN_API_KEY 自动化调用 Dify Console API，创建工作流应用、导出 DSL、导入 DSL。适用于不想走浏览器登录 cookie、需要脚本化测试或自动化工作流导入导出的场景。
disable-model-invocation: true
---

# Dify Console Admin API

## 适用场景

当用户想通过 `ADMIN_API_KEY` 自动化调用 Dify Console API 时使用，包括：

- 创建工作流应用。
- 导出应用或工作流 DSL。
- 从 YAML 内容或 URL 导入 DSL。
- 验证 admin key 鉴权是否生效。

## 参数管理

### 配置文件位置

配置保存在项目根目录下：`.dify_key/config.json`

### 首次使用：收集并保存参数

如果配置文件不存在，先收集这些必需参数：

- `DIFY_BASE_URL`：Dify API 地址，例如 `https://dify.example.com` 或 `http://127.0.0.1:5001`
- `ADMIN_API_KEY`：服务端配置的 admin key
- `WORKSPACE_ID`：目标 workspace 的 `tenants.id`

然后保存到配置文件：

```bash
mkdir -p .dify_key
# 确保 .dify_key/ 已加入 .gitignore
if ! grep -q "^\.dify_key/" .gitignore 2>/dev/null; then
  echo ".dify_key/" >> .gitignore
fi
cat > .dify_key/config.json << 'EOF'
{
  "DIFY_BASE_URL": "用户提供的值",
  "ADMIN_API_KEY": "用户提供的值",
  "WORKSPACE_ID": "用户提供的值"
}
EOF
```

### 后续使用：加载已保存参数

每次执行前先检查并加载配置：

```bash
if [ -f .dify_key/config.json ]; then
  export DIFY_BASE_URL=$(python3 -c "import json; print(json.load(open('.dify_key/config.json'))['DIFY_BASE_URL'])")
  export ADMIN_API_KEY=$(python3 -c "import json; print(json.load(open('.dify_key/config.json'))['ADMIN_API_KEY'])")
  export WORKSPACE_ID=$(python3 -c "import json; print(json.load(open('.dify_key/config.json'))['WORKSPACE_ID'])")
  echo "已加载配置：DIFY_BASE_URL=${DIFY_BASE_URL}"
else
  echo "配置文件不存在，请先提供必需参数。"
fi
```

### 更新配置

用户要求更新参数时，读取现有配置、合并更新、重新保存：

```bash
# 读取现有配置
EXISTING=$(cat .dify_key/config.json)
# 更新后保存（示例：更新 WORKSPACE_ID）
python3 -c "
import json
config = json.loads('''$EXISTING''')
config['WORKSPACE_ID'] = 'new-workspace-id'
with open('.dify_key/config.json', 'w') as f:
    json.dump(config, f, indent=2)
"
```

### 安全要求

- 配置文件权限必须为 `600`（仅用户可读写）
- 不要把 `ADMIN_API_KEY` 写入仓库文件、PR 描述、日志或长期保存的脚本
- 展示命令时，优先使用变量而非明文值
- 创建配置文件时脚本会自动将 `.dify_key/` 加入 `.gitignore`

### 操作类型

加载配置后，确认操作类型和附加参数：

- 创建应用：`APP_NAME`，可选 `APP_DESCRIPTION`
- 导出 DSL：`APP_ID`，可选 `INCLUDE_SECRET`、`WORKFLOW_ID`
- 导入 DSL：`YAML_CONTENT` 或 `YAML_URL`
- 覆盖导入：额外需要 `APP_ID`，且只能覆盖 workflow 或 advanced-chat 应用
- 确认导入：`IMPORT_ID`

## 前置条件

运行中的 API 进程必须启用：

```env
ADMIN_API_KEY_ENABLE=true
ADMIN_API_KEY=<admin-key>
```

修改后必须重启 API 进程。如果请求返回 `401 Invalid token`，通常表示运行中的进程没有加载 admin key，或者 key 不正确。

## 推荐变量模板

让用户先在 shell 中设置变量，再执行后续命令：

```bash
export DIFY_BASE_URL="https://dify.example.com"
export ADMIN_API_KEY="your-admin-key"
export WORKSPACE_ID="your-workspace-id"
```

如果用户明确是在本地开发环境测试，`DIFY_BASE_URL` 常见值是：

```bash
export DIFY_BASE_URL="http://127.0.0.1:5001"
```

## 请求头规则

所有通过 admin key 鉴权的 Console API 请求都要带：

```text
Authorization: Bearer ${ADMIN_API_KEY}
X-WORKSPACE-ID: ${WORKSPACE_ID}
```

admin key 生效时不需要 `X-CSRF-Token`，也不需要登录 cookie。API 会在指定 workspace 中找到一个 owner 账号，并以该账号身份执行。

## 可选：查询 workspace id

如果用户不知道 `WORKSPACE_ID`，最简单的方式是在 Dify 网页上按 F12 打开开发者工具，找到 `/console/api/workspaces` 接口的响应，其中 `id` 字段即为 `WORKSPACE_ID`：

```json
{
  "workspaces": [
    {
      "id": "d4e26a01-162f-4366-9a25-1c2c1bdd15dz",
      "name": "admin's Workspace",
      "current": true
    }
  ]
}
```

## 创建工作流应用

先确认：

```bash
export APP_NAME="admin-key-test-workflow"
export APP_DESCRIPTION="created by admin api key test"
```

```bash
curl -i -X POST "${DIFY_BASE_URL}/console/api/apps" \
  -H "Authorization: Bearer ${ADMIN_API_KEY}" \
  -H "X-WORKSPACE-ID: ${WORKSPACE_ID}" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"${APP_NAME}\",
    \"mode\": \"workflow\",
    \"description\": \"${APP_DESCRIPTION}\"
  }"
```

成功时应返回：

```text
HTTP/1.1 201 CREATED
```

## 导出应用或工作流 DSL

先确认：

```bash
export APP_ID="your-app-id"
export INCLUDE_SECRET="false"
```

```bash
curl -sS -X GET \
  "${DIFY_BASE_URL}/console/api/apps/${APP_ID}/export?include_secret=${INCLUDE_SECRET}" \
  -H "Authorization: Bearer ${ADMIN_API_KEY}" \
  -H "X-WORKSPACE-ID: ${WORKSPACE_ID}"
```

如果要导出指定草稿 workflow，追加 `workflow_id`：

```bash
export WORKFLOW_ID="your-workflow-id"

curl -sS -X GET \
  "${DIFY_BASE_URL}/console/api/apps/${APP_ID}/export?include_secret=${INCLUDE_SECRET}&workflow_id=${WORKFLOW_ID}" \
  -H "Authorization: Bearer ${ADMIN_API_KEY}" \
  -H "X-WORKSPACE-ID: ${WORKSPACE_ID}"
```

响应结构：

```json
{
  "data": "version: 0.6.0\nkind: app\n..."
}
```

## 导入 DSL

从 YAML 内容导入：

```bash
export YAML_CONTENT="$(cat /path/to/workflow.yml)"

curl -i -X POST "${DIFY_BASE_URL}/console/api/apps/imports" \
  -H "Authorization: Bearer ${ADMIN_API_KEY}" \
  -H "X-WORKSPACE-ID: ${WORKSPACE_ID}" \
  -H "Content-Type: application/json" \
  --data-binary @- <<JSON
{
  "mode": "yaml-content",
  "yaml_content": $(python3 -c 'import json, os; print(json.dumps(os.environ["YAML_CONTENT"]))')
}
JSON
```

从 URL 导入：

```bash
export YAML_URL="https://example.com/workflow.yml"

curl -i -X POST "${DIFY_BASE_URL}/console/api/apps/imports" \
  -H "Authorization: Bearer ${ADMIN_API_KEY}" \
  -H "X-WORKSPACE-ID: ${WORKSPACE_ID}" \
  -H "Content-Type: application/json" \
  -d "{
    \"mode\": \"yaml-url\",
    \"yaml_url\": \"${YAML_URL}\"
  }"
```

如果要覆盖已有 workflow 或 advanced-chat 应用，传入 `app_id`：

```bash
export APP_ID="existing-app-id"
export YAML_CONTENT="$(cat /path/to/workflow.yml)"

curl -i -X POST "${DIFY_BASE_URL}/console/api/apps/imports" \
  -H "Authorization: Bearer ${ADMIN_API_KEY}" \
  -H "X-WORKSPACE-ID: ${WORKSPACE_ID}" \
  -H "Content-Type: application/json" \
  --data-binary @- <<JSON
{
  "mode": "yaml-content",
  "yaml_content": $(python3 -c 'import json, os; print(json.dumps(os.environ["YAML_CONTENT"]))'),
  "app_id": "${APP_ID}"
}
JSON
```

如果导入返回 `202` 且 `status: pending`，需要确认导入：

```bash
export IMPORT_ID="your-import-id"

curl -i -X POST "${DIFY_BASE_URL}/console/api/apps/imports/${IMPORT_ID}/confirm" \
  -H "Authorization: Bearer ${ADMIN_API_KEY}" \
  -H "X-WORKSPACE-ID: ${WORKSPACE_ID}" \
  -H "Content-Type: application/json" \
  -d '{}'
```

## 排查

- `201 CREATED`：创建应用成功。
- `200 OK`：导出或导入完成，或已返回数据。
- `202 ACCEPTED`：导入进入 pending，需要调用 confirm 接口。
- `401 Invalid token`：admin key 缺失、未启用、值不正确，或配置变更后 API 进程未重启。
- Connection refused：`DIFY_BASE_URL` 不可达，或 API 服务未运行。
- `ModuleNotFoundError: werkzeug.utils`：`.venv` 里的 Werkzeug 安装损坏；重装 `Werkzeug==3.1.6` 或重建 `api/.venv`。
