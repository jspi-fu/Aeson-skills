import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

// 缓存文件随 skill 走，跨文档、跨次运行复用「内容指纹 → 直链」映射，
// 从而避免相同内容重复上传（省空间、绕过 Chevereto 重复内容拒绝、保证幂等）。
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const CACHE_PATH = path.resolve(__dirname, '../../.image-upload-cache.json');

let cache = null;

function load() {
  if (cache) return cache;
  try {
    const parsed = JSON.parse(fs.readFileSync(CACHE_PATH, 'utf8'));
    // 文件损坏或结构异常都退回空缓存，绝不因缓存问题阻断上传
    cache = parsed && typeof parsed === 'object' && parsed.entries ? parsed : { version: 1, entries: {} };
  } catch {
    cache = { version: 1, entries: {} };
  }
  return cache;
}

function persist() {
  try {
    fs.writeFileSync(CACHE_PATH, JSON.stringify(cache, null, 2), 'utf8');
  } catch (err) {
    console.warn(`Warning: failed to persist upload cache: ${err.message}`);
  }
}

/** 按缓存键取直链，未命中返回 null。键约定为 `${provider}:${sha256}`。 */
export function getCachedUrl(key) {
  const entry = load().entries[key];
  return entry ? entry.url : null;
}

/** 写入/更新一条缓存并落盘。 */
export function setCachedUrl(key, url) {
  const c = load();
  c.entries[key] = { url, uploadedAt: new Date().toISOString() };
  persist();
}

/** 删除一条缓存（用于命中但远程直链已失效的场景）。 */
export function removeCached(key) {
  const c = load();
  if (c.entries[key]) {
    delete c.entries[key];
    persist();
  }
}
