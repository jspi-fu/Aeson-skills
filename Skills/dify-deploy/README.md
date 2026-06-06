# 如何获取 dify-deploy skill 所需要的三个key值

## 1. `DIFY_BASE_URL` — Dify API 地址

这是你部署的 Dify 服务的 API 地址：

- **自部署（本地开发）**：通常是 `http://localhost`
- **自部署（线上）**：例如 `https://dify.example.com`
- **Dify Cloud**：`https://api.dify.ai/v1`

取决于你的 Dify 实例部署在哪里，如果本地部署的版本有自定义过访问 URL，将进入工作区后的网址去除尾部的`/apps`输入即可。

---

## 2. `ADMIN_API_KEY` — 管理员 API 密钥

这是在 Dify 服务端的 `.env` 配置文件中手动设置的。获取步骤：

1. 找到 Dify 部署目录下的 `.env` 文件（通常在 `dify/docker/.env` 或 `dify/api/.env`）
2. 确认以下两项已配置：
   ```env
   ADMIN_API_KEY_ENABLE=true
   ADMIN_API_KEY=your-admin-key
   ```
	![.env修改演示](https://bsyimg.luoca.net/imgtc/20260606/9702c9448ad0c7a5b7eb358a04eac3d6.webp)
3. 如果没有设置，请在`.env`中手动添加两项配置，并自定义密钥字符串（如 `sk-admin-xxxxx`），然后**重启 API 进程**使其生效：
	```bash
	cd /d "你的dify docker部署源码路径，如~\dify\dify\docker"
	docker compose up -d --force-recreate api
	```
> 注意：
> - 是重启 API 进程，不是在 Docker 可视化面板中按 restart ，请打开你的命令行输入指令。
> - 如果请求返回 `401 Invalid token`，说明 key 未启用、值不对，或修改后未重启服务，请再次检查变量设置是否正确、文件是否保存、API进程是否正确重启。

---

## 3. `WORKSPACE_ID` — 工作区 ID

这是 Dify 数据库中 `tenants` 表的 `id` 字段。获取方式：

### 方法一（推荐）：浏览器开发者工具
1. 登录 Dify 网页端，按 `F12` 打开开发者工具 → Network（网络） 标签
2. 筛选器中选择`Fetch/XHR`
3. 按`F5`刷新界面，找到名称为 `workspaces` 的接口
4. 在右侧预览中点击`响应`
5. 响应中 `id` 字段即为 `WORKSPACE_ID`：
   ```json
   {
     "workspaces": [
       {
         "id": "d4e26a01-162f-4366-9a25-1c2c1bdd15dz",
         "name": "admin's Workspace",
         "current": true
         ……
       }
     ]
   }
   ```
![获取 WORKSPACE_ID 演示](https://bsyimg.luoca.net/imgtc/20260606/ea2bd5a314829bf9492744389eb15477.webp)


### 方法二：直接查数据库
如果你有数据库访问权限，查询 `tenants` 表即可。

1. 进到 dify 的 docker 目录，执行数据库连接：
	```bash
	docker exec -it docker-db-1 psql -U postgres -d dify
	```
2. 查空间 ID：
	```bash
	SELECT id,name FROM tenants;
	```
	查询出来第一列 UUID = WORKSPACE_ID。输入`\`q退出数据库。

