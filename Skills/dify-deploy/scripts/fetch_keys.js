#!/usr/bin/env node
/**
 * 一键获取 dify-deploy 所需的三个 key：DIFY_BASE_URL、ADMIN_API_KEY、WORKSPACE_ID
 *
 * 自动通过正在运行的 Docker 容器定位 Dify 部署目录，无需手动输入路径。
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// ─── 颜色输出 ────────────────────────────────────────────────────────
const GREEN = '\x1b[32m';
const YELLOW = '\x1b[33m';
const RED = '\x1b[31m';
const CYAN = '\x1b[36m';
const NC = '\x1b[0m';

const info = (msg) => console.log(`${GREEN}[✓]${NC} ${msg}`);
const warn = (msg) => console.log(`${YELLOW}[!]${NC} ${msg}`);
const error = (msg) => console.log(`${RED}[✗]${NC} ${msg}`);
const hint = (msg) => console.log(`${CYAN}[i]${NC} ${msg}`);

// ─── 工具函数 ──────────────────────────────────────────────────────────
function run(cmd, timeout = 10000) {
  try {
    const stdout = execSync(cmd, {
      encoding: 'utf-8',
      timeout,
      stdio: ['pipe', 'pipe', 'pipe'],
    });
    return { code: 0, stdout, stderr: '' };
  } catch (err) {
    return {
      code: err.status || -1,
      stdout: err.stdout || '',
      stderr: err.stderr || err.message,
    };
  }
}

function checkDocker() {
  const { code } = run('docker info');
  if (code !== 0) {
    error('Docker 未运行或未安装');
    hint('请先启动 Docker Desktop，然后重新运行此脚本');
    return false;
  }
  return true;
}

// ─── 自动定位 Dify 部署目录 ─────────────────────────────────────────
function findDifyContainers() {
  const { code, stdout } = run('docker ps --format "{{.Names}}"');
  if (code !== 0) return [];

  const names = stdout
    .split('\n')
    .map((n) => n.trim())
    .filter(Boolean);

  return names.filter(
    (n) => n.toLowerCase().includes('dify') || n.startsWith('docker-')
  );
}

function findEnvFromContainer(containerName) {
  const { code, stdout } = run(`docker inspect ${containerName}`);
  if (code !== 0) return null;

  try {
    const infoList = JSON.parse(stdout);
    const mounts = infoList[0]?.Mounts || [];
    const candidates = [];

    for (const mount of mounts) {
      const src = mount.Source;
      if (!src) continue;

      // 将反斜杠统一为正斜杠
      const normalized = src.replace(/\\/g, '/');
      let current = normalized;

      // 向上查找6级父目录
      for (let i = 0; i <= 6; i++) {
        const envPath = path.posix.join(current, '.env');
        if (fs.existsSync(envPath)) {
          candidates.push(current);
          break;
        }
        const parent = path.posix.dirname(current);
        if (parent === current) break;
        current = parent;
      }
    }

    if (candidates.length === 0) return null;

    // 过滤掉系统目录
    const filtered = candidates.filter((c) => {
      const lower = c.toLowerCase();
      if (
        lower.includes('/windows') ||
        lower.includes('/program files') ||
        lower.includes('/users/')
      ) {
        return false;
      }
      return c.split('/').length >= 2;
    });

    // 选择路径最短的（通常是docker compose的根目录）
    const best = filtered.length > 0 ? filtered : candidates;
    return best.reduce((a, b) => (a.length <= b.length ? a : b));
  } catch {
    return null;
  }
}

function detectDifyDir() {
  const containers = findDifyContainers();
  if (containers.length === 0) return null;

  hint(`检测到 ${containers.length} 个 Dify 相关容器: ${containers.slice(0, 5).join(', ')}`);

  const foundDirs = [];
  for (const name of containers) {
    const dir = findEnvFromContainer(name);
    if (dir) foundDirs.push({ name, dir });
  }

  if (foundDirs.length === 0) return null;

  // 去重并选择最佳目录
  const uniqueDirs = [...new Set(foundDirs.map((f) => f.dir))];
  const bestDir = uniqueDirs.reduce((a, b) => (a.length <= b.length ? a : b));

  const source = foundDirs.find((f) => f.dir === bestDir);
  if (source) {
    info(`从容器 ${source.name} 定位到部署目录: ${bestDir}`);
  }

  return bestDir;
}

// ─── 读取 .env 文件 ─────────────────────────────────────────────────
function parseEnvValue(envPath, key) {
  const content = fs.readFileSync(envPath, 'utf-8');
  for (const line of content.split('\n')) {
    const trimmed = line.trim();
    if (trimmed.startsWith('#') || !trimmed.includes('=')) continue;
    const eqIdx = trimmed.indexOf('=');
    const k = trimmed.slice(0, eqIdx).trim();
    const v = trimmed.slice(eqIdx + 1).trim().replace(/^["']|["']$/g, '');
    if (k === key) return v;
  }
  return null;
}

// ─── 获取三个 key ─────────────────────────────────────────────────
function getDifyBaseUrl(envPath) {
  if (envPath) {
    const val = parseEnvValue(envPath, 'CONSOLE_API_URL');
    if (val) {
      info(`DIFY_BASE_URL 从 .env 获取: ${val}`);
      return val;
    }
  }
  warn('DIFY_BASE_URL 未在 .env 中找到 CONSOLE_API_URL，使用默认值: http://localhost');
  return 'http://localhost';
}

function getAdminApiKey(envPath) {
  if (!envPath) {
    error('未找到 .env 文件，无法获取 ADMIN_API_KEY');
    return { key: '', failed: true };
  }

  const enabled = (parseEnvValue(envPath, 'ADMIN_API_KEY_ENABLE') || '').toLowerCase();
  const key = parseEnvValue(envPath, 'ADMIN_API_KEY');

  if (enabled !== 'true') {
    error('ADMIN_API_KEY_ENABLE 未设为 true，admin key 不会生效');
    return { key: '', failed: true };
  }
  if (!key) {
    error('ADMIN_API_KEY 未在 .env 中设置');
    return { key: '', failed: true };
  }

  info('ADMIN_API_KEY 从 .env 获取成功（已隐藏）');
  return { key, failed: false };
}

function getWorkspaceId() {
  const containers = ['docker-db-1', 'docker-db_postgres-1', 'db'];

  for (const container of containers) {
    const { code, stdout } = run(
      `docker exec ${container} psql -U postgres -d dify -t -A -c "SELECT id FROM tenants LIMIT 1;"`
    );
    if (code === 0 && stdout.trim()) {
      const wsId = stdout.trim();
      info(`WORKSPACE_ID 从数据库获取: ${wsId}`);
      return { id: wsId, failed: false };
    }
  }

  error('未能从数据库获取 WORKSPACE_ID');
  hint('请确认 Docker 数据库容器正在运行: docker ps | grep db');
  return { id: '', failed: true };
}

// ─── 主流程 ──────────────────────────────────────────────────────────
function main() {
  console.log();
  console.log('═══════════════════════════════════════════');
  console.log('  Dify Deploy Key 一键获取工具');
  console.log('═══════════════════════════════════════════');
  console.log();

  // 步骤 0：检查 Docker
  if (!checkDocker()) process.exit(1);

  // 步骤 1：创建配置文件
  const configDir = '.dify_key';
  const configFile = path.join(configDir, 'config.json');
  fs.mkdirSync(configDir, { recursive: true });
  fs.writeFileSync(
    configFile,
    JSON.stringify({ DIFY_BASE_URL: '', ADMIN_API_KEY: '', WORKSPACE_ID: '' }, null, 2),
    'utf-8'
  );
  info(`已创建配置文件 ${configFile}（初始空白值）`);

  // 步骤 2：将 .dify_key/ 加入 .gitignore
  const gitignore = '.gitignore';
  const marker = '.dify_key/';
  if (fs.existsSync(gitignore)) {
    const content = fs.readFileSync(gitignore, 'utf-8');
    if (!content.includes(marker)) {
      fs.appendFileSync(gitignore, `\n${marker}\n`, 'utf-8');
      info('已将 .dify_key/ 追加到 .gitignore');
    } else {
      info('.gitignore 中已包含 .dify_key/');
    }
  } else {
    fs.writeFileSync(gitignore, `${marker}\n`, 'utf-8');
    info('已创建 .gitignore 并添加 .dify_key/');
  }

  // 步骤 3：定位 Dify 部署目录
  console.log();
  let envPath = null;

  // 优先使用命令行参数
  const cliDir = process.argv[2];
  if (cliDir) {
    const resolved = path.resolve(cliDir);
    hint(`使用命令行指定的部署目录: ${resolved}`);
    const candidate = path.join(resolved, '.env');
    if (fs.existsSync(candidate)) {
      envPath = candidate;
      info(`找到 .env 文件: ${envPath}`);
    } else {
      error(`该目录下未找到 .env 文件: ${candidate}`);
      process.exit(1);
    }
  } else {
    hint('正在通过 Docker 容器自动定位 Dify 部署目录...');
    const difyDir = detectDifyDir();

    if (difyDir) {
      const candidate = path.posix.join(difyDir, '.env');
      if (fs.existsSync(candidate)) {
        envPath = candidate;
        info(`找到 .env 文件: ${envPath}`);
      } else {
        // 检查 docker 子目录
        const candidate2 = path.posix.join(difyDir, 'docker', '.env');
        if (fs.existsSync(candidate2)) {
          envPath = candidate2;
          info(`找到 .env 文件: ${envPath}`);
        }
      }
    }

    if (!envPath) {
      warn('未能自动定位 Dify 部署目录');
      console.log();
      hint('请通过命令行参数指定部署目录，例如：');
      console.log(`  node ${__filename} C:\\dify\\docker`);
      console.log();
      process.exit(1);
    }
  }

  // 步骤 4：获取三个 key
  console.log();
  hint('开始获取配置信息...');
  console.log();

  const difyBaseUrl = getDifyBaseUrl(envPath);
  const { key: adminApiKey, failed: adminFailed } = getAdminApiKey(envPath);
  const { id: workspaceId, failed: wsFailed } = getWorkspaceId();

  // 步骤 5：ADMIN_API_KEY 失败时的引导
  if (adminFailed) {
    console.log();
    warn('请在 .env 文件中添加以下两行配置：');
    console.log();
    console.log(`  文件路径: ${envPath || '<未找到的 .env 文件路径>'}`);
    console.log();
    console.log('  ADMIN_API_KEY_ENABLE=true');
    console.log('  ADMIN_API_KEY=sk-admin-替换为你的密钥');
    console.log();
    warn('保存后，在终端执行以下命令重启 API 进程：');
    console.log();
    console.log('  docker compose up -d --force-recreate api');
    console.log();
  }

  // 步骤 6：写入最终配置
  fs.writeFileSync(
    configFile,
    JSON.stringify(
      {
        DIFY_BASE_URL: difyBaseUrl,
        ADMIN_API_KEY: adminApiKey,
        WORKSPACE_ID: workspaceId,
      },
      null,
      2
    ),
    'utf-8'
  );
  info(`配置已写入 ${configFile}`);

  // 步骤 7：结果汇总
  console.log();
  console.log('=========================================');
  console.log('  配置获取结果');
  console.log('=========================================');
  console.log(`  DIFY_BASE_URL : ${difyBaseUrl}`);
  console.log(`  ADMIN_API_KEY : ${adminApiKey ? '******（已获取）' : '（未获取）'}`);
  console.log(`  WORKSPACE_ID  : ${workspaceId || '（未获取）'}`);
  console.log('=========================================');

  if (adminFailed || wsFailed) {
    console.log();
    error('部分 key 获取失败，请阅读以下文档完成手动配置：');
    console.log();
    console.log(`  ${path.join(__dirname, '..', 'README.md')}`);
    console.log();
    process.exit(1);
  }

  console.log();
  info('全部 key 获取成功！');
}

main();
