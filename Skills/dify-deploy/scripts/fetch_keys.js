#!/usr/bin/env node
/**
 * 一键获取 dify-deploy 所需的三个 key：DIFY_BASE_URL、ADMIN_API_KEY、WORKSPACE_ID
 * 自动通过运行中的 Docker 容器定位 Dify 部署目录，无需手动输入路径。
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const GREEN = '\x1b[32m', YELLOW = '\x1b[33m', RED = '\x1b[31m', CYAN = '\x1b[36m', NC = '\x1b[0m';
const info = (msg) => console.log(`${GREEN}[✓]${NC} ${msg}`);
const warn = (msg) => console.log(`${YELLOW}[!]${NC} ${msg}`);
const error = (msg) => console.log(`${RED}[✗]${NC} ${msg}`);
const hint = (msg) => console.log(`${CYAN}[i]${NC} ${msg}`);

function run(cmd, timeout = 10000) {
  try {
    const stdout = execSync(cmd, { encoding: 'utf-8', timeout, stdio: ['pipe', 'pipe', 'pipe'] });
    return { code: 0, stdout, stderr: '' };
  } catch (err) {
    return { code: err.status || -1, stdout: err.stdout || '', stderr: err.stderr || err.message };
  }
}

function checkDocker() {
  if (run('docker info').code !== 0) {
    error('Docker 未运行或未安装，请先启动 Docker Desktop 后重试');
    return false;
  }
  return true;
}

function findEnvFromContainer(containerName) {
  const { code, stdout } = run(`docker inspect ${containerName}`);
  if (code !== 0) return null;
  try {
    const mounts = JSON.parse(stdout)[0]?.Mounts || [];
    const candidates = [];
    for (const mount of mounts) {
      if (!mount.Source) continue;
      let current = mount.Source.replace(/\\/g, '/');
      for (let i = 0; i <= 6; i++) {
        const envPath = path.posix.join(current, '.env');
        if (fs.existsSync(envPath)) { candidates.push(current); break; }
        const parent = path.posix.dirname(current);
        if (parent === current) break;
        current = parent;
      }
    }
    const filtered = candidates.filter(c => {
      const lower = c.toLowerCase();
      return !lower.includes('/windows') && !lower.includes('/program files') && !lower.includes('/users/');
    });
    const best = filtered.length > 0 ? filtered : candidates;
    return best.length > 0 ? best.reduce((a, b) => (a.length <= b.length ? a : b)) : null;
  } catch { return null; }
}

function detectDifyDir() {
  const { code, stdout } = run('docker ps --format "{{.Names}}"');
  if (code !== 0) return null;
  const containers = stdout.split('\n').map(n => n.trim()).filter(n => n.toLowerCase().includes('dify') || n.startsWith('docker-'));
  if (containers.length === 0) return null;
  hint(`检测到 Dify 相关容器: ${containers.slice(0, 4).join(', ')}`);

  for (const name of containers) {
    const dir = findEnvFromContainer(name);
    if (dir) {
      info(`从容器 ${name} 定位到部署目录: ${dir}`);
      return dir;
    }
  }
  return null;
}

function parseEnvValue(envPath, key) {
  if (!envPath || !fs.existsSync(envPath)) return null;
  const content = fs.readFileSync(envPath, 'utf-8');
  for (const line of content.split('\n')) {
    const trimmed = line.trim();
    if (trimmed.startsWith('#') || !trimmed.includes('=')) continue;
    const [k, ...v] = trimmed.split('=');
    if (k.trim() === key) return v.join('=').trim().replace(/^["']|["']$/g, '');
  }
  return null;
}

function getDifyBaseUrl(envPath) {
  const val = parseEnvValue(envPath, 'CONSOLE_API_URL');
  if (val) {
    info(`DIFY_BASE_URL 从 .env 获取: ${val}`);
    return val;
  }
  warn('未找到 CONSOLE_API_URL，使用默认值: http://localhost');
  return 'http://localhost';
}

function getAdminApiKey(envPath) {
  if (!envPath) return { key: '', failed: true };
  const enabled = (parseEnvValue(envPath, 'ADMIN_API_KEY_ENABLE') || '').toLowerCase();
  const key = parseEnvValue(envPath, 'ADMIN_API_KEY');
  if (enabled !== 'true' || !key) {
    error('ADMIN_API_KEY_ENABLE 未设为 true 或 ADMIN_API_KEY 未设置');
    return { key: '', failed: true };
  }
  info('ADMIN_API_KEY 从 .env 获取成功');
  return { key, failed: false };
}

function getWorkspaceId() {
  const dbContainers = ['docker-db-1', 'docker-db_postgres-1', 'db'];
  for (const container of dbContainers) {
    const { code, stdout } = run(`docker exec ${container} psql -U postgres -d dify -t -A -c "SELECT id FROM tenants LIMIT 1;"`);
    if (code === 0 && stdout.trim()) {
      const wsId = stdout.trim();
      info(`WORKSPACE_ID 从数据库获取: ${wsId}`);
      return { id: wsId, failed: false };
    }
  }
  error('未能从数据库获取 WORKSPACE_ID');
  return { id: '', failed: true };
}

function updateGitignore(marker) {
  const gitignore = '.gitignore';
  if (fs.existsSync(gitignore)) {
    const content = fs.readFileSync(gitignore, 'utf-8');
    if (!content.includes(marker)) fs.appendFileSync(gitignore, `\n${marker}\n`, 'utf-8');
  } else {
    fs.writeFileSync(gitignore, `${marker}\n`, 'utf-8');
  }
}

function main() {
  console.log('\n═══ Dify Deploy Key 一键获取工具 ═══\n');
  if (!checkDocker()) process.exit(1);

  const configDir = '.dify_key';
  const configFile = path.join(configDir, 'config.json');
  fs.mkdirSync(configDir, { recursive: true });
  updateGitignore('.dify_key/');

  let envPath = null;
  const cliDir = process.argv[2];
  if (cliDir) {
    const resolved = path.resolve(cliDir);
    const candidate = path.join(resolved, '.env');
    if (fs.existsSync(candidate)) envPath = candidate;
    else { error(`指定的目录下未找到 .env 文件: ${candidate}`); process.exit(1); }
  } else {
    const difyDir = detectDifyDir();
    if (difyDir) {
      const c1 = path.posix.join(difyDir, '.env');
      const c2 = path.posix.join(difyDir, 'docker', '.env');
      if (fs.existsSync(c1)) envPath = c1;
      else if (fs.existsSync(c2)) envPath = c2;
    }
  }

  if (!envPath) {
    warn('未能自动定位 Dify .env 文件，可传入参数手动指定: node fetch_keys.js <dify_docker_dir>');
  } else {
    info(`使用 .env 文件: ${envPath}`);
  }

  const difyBaseUrl = getDifyBaseUrl(envPath);
  const { key: adminApiKey, failed: adminFailed } = getAdminApiKey(envPath);
  const { id: workspaceId, failed: wsFailed } = getWorkspaceId();

  fs.writeFileSync(configFile, JSON.stringify({ DIFY_BASE_URL: difyBaseUrl, ADMIN_API_KEY: adminApiKey, WORKSPACE_ID: workspaceId }, null, 2), 'utf-8');
  info(`配置已更新至 ${configFile}`);

  console.log('\n════════ 配置获取结果 ════════');
  console.log(`  DIFY_BASE_URL : ${difyBaseUrl}`);
  console.log(`  ADMIN_API_KEY : ${adminApiKey ? '******（已获取）' : '（未获取）'}`);
  console.log(`  WORKSPACE_ID  : ${workspaceId || '（未获取）'}`);
  console.log('═══════════════════════════════\n');

  if (adminFailed || wsFailed) {
    error('部分 Key 获取失败，请阅读 README.md 完成手动配置');
    process.exit(1);
  }
  info('全部 Key 获取成功！');
}

main();
