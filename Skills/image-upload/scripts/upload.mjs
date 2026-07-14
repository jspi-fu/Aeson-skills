#!/usr/bin/env node

import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import { fileURLToPath } from 'url';
import { loadEnv } from './config.mjs';
import { getProvider, listProviders } from './providers/index.mjs';
import { scanDocument, replaceImageLinks } from './parser.mjs';
import { detectMimeType } from './utils/mime.mjs';
import { downloadBuffer, checkUrlAlive } from './utils/fetch.mjs';
import { getCachedUrl, setCachedUrl, removeCached } from './utils/cache.mjs';

// Load environment variables from .env files
loadEnv();

// Parse command line arguments
function parseArgs(args) {
  const result = {
    args: []
  };
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === '--help' || arg === '-h') {
      result.help = true;
    } else if (arg === '--list' || arg === '-l') {
      result.list = true;
    } else if (arg === '--replace' || arg === '-r') {
      result.replace = true;
    } else if (arg === '--mirror' || arg === '-m') {
      result.mirror = true;
    } else if (arg === '--provider' || arg === '-p') {
      result.provider = args[++i];
    } else if (arg === '--name' || arg === '-n') {
      result.name = args[++i];
    } else if (!arg.startsWith('-')) {
      result.args.push(arg);
    }
  }
  return result;
}

function printHelp() {
  console.log(`
Image Upload Skill - Upload images and cloudify documents

Usage:
  image-upload <file-path> [options]

Options:
  -p, --provider <name>  Provider to use (default: imglink, options: imgbb, freeimage, uploadme, imglink)
  -n, --name <filename>  Custom name for the uploaded file (single image upload only)
  -r, --replace          Scan document and replace local links in-place with remote URLs
  -m, --mirror           全量转存：本地图片 + 文档内远程 URL 图片一并上传到目标图床（去重），配合 --replace 写回
  -l, --list             List available providers
  -h, --help             Show this help message

Examples:
  # Upload a single image
  node scripts/upload.mjs ./photo.jpg --provider imgbb
  
  # Scan document, upload all local images, and print mappings
  node scripts/upload.mjs ./README.md
  
  # Scan document, upload all local images, and replace links in README.md in-place
  node scripts/upload.mjs ./README.md --replace

  # 全量转存：把本地图片和文档内的网络图片都搬到自己的图床并写回
  node scripts/upload.mjs ./README.md --mirror --replace
`);
}

function printProviders() {
  console.log('\nAvailable Image Hosting Providers:\n');
  console.log('| Provider    | Max Size | Config Required | Notes                    |');
  console.log('|-------------|----------|-----------------|--------------------------|');
  for (const p of listProviders()) {
    const size = `${Math.round(p.maxFileSize / 1024 / 1024)}MB`;
    const config = p.requiresConfig ? 'Yes' : 'No';
    const notes = p.name === 'imglink' ? 'Default provider' : '';
    console.log(
      `| ${p.displayName.padEnd(11)} | ${size.padEnd(8)} | ${config.padEnd(15)} | ${notes.padEnd(24)} |`
    );
  }
  console.log('\nTo use a provider, set IMAGE_UPLOAD_PROVIDER in .env or use --provider.\n');
}

function assertUploadable(provider, buffer, mimeType) {
  if (!mimeType || !provider.supportedTypes.includes(mimeType)) {
    throw new Error(`Unsupported MIME type: ${mimeType || 'unknown'} for ${provider.displayName}`);
  }

  if (buffer.length > provider.maxFileSize) {
    const sizeMB = (buffer.length / 1024 / 1024).toFixed(2);
    const limitMB = provider.maxFileSize / 1024 / 1024;
    throw new Error(`File size (${sizeMB}MB) exceeds limit of ${limitMB}MB for ${provider.displayName}`);
  }
}

// mirror 幂等：远程 URL 的 host 已是目标图床自己的直链域名，则无需再次转存
function isAlreadyOnProvider(provider, url) {
  const hosts = provider.directHosts || [];
  if (hosts.length === 0) return false;
  try {
    const host = new URL(url).hostname.toLowerCase();
    return hosts.some((h) => host === h || host.endsWith(`.${h}`));
  } catch {
    return false;
  }
}

// 带内容指纹缓存的统一上传：相同内容（含不同文件名/跨次运行）命中缓存且直链存活则复用，
// 从而避免重复上传占用图床空间，也绕过 Chevereto 对重复内容的 101 拒绝。
async function uploadBuffer(provider, buffer, filename, mimeType) {
  assertUploadable(provider, buffer, mimeType);

  const cacheKey = `${provider.name}:${crypto.createHash('sha256').update(buffer).digest('hex')}`;
  const cachedUrl = getCachedUrl(cacheKey);
  if (cachedUrl) {
    if (await checkUrlAlive(cachedUrl)) {
      return { url: cachedUrl, fromCache: true };
    }
    // 缓存中的直链已失效（例如被图床删除），清掉后按新图重新上传
    removeCached(cacheKey);
  }

  const result = await provider.upload(buffer, filename, mimeType);
  if (result && result.url) {
    setCachedUrl(cacheKey, result.url);
  }
  return result;
}

async function uploadSingleImage(provider, absolutePath, customName) {
  const buffer = fs.readFileSync(absolutePath);
  const mimeType = detectMimeType(buffer, absolutePath);
  const filename = customName || path.basename(absolutePath, path.extname(absolutePath));
  return await uploadBuffer(provider, buffer, filename, mimeType);
}

// mirror 模式：下载远程图片再上传到目标图床
async function uploadRemoteImage(provider, url) {
  const buffer = await downloadBuffer(url);
  let pathname = url;
  try {
    pathname = new URL(url).pathname;
  } catch {
    // URL 解析失败则退回原始字符串，仅用于扩展名/命名推断
  }
  const mimeType = detectMimeType(buffer, pathname);
  const base = path.basename(pathname, path.extname(pathname));
  const filename = base || 'image';
  return await uploadBuffer(provider, buffer, filename, mimeType);
}

async function handleDocumentUpload(provider, absolutePath, replaceLinks, includeRemote) {
  console.log(`Scanning document: ${absolutePath}`);
  const { content, images } = scanDocument(absolutePath, { includeRemote });

  if (images.length === 0) {
    console.log('No images found in document.');
    return;
  }

  const remoteCount = images.filter((i) => i.isRemote).length;
  const scanScope = includeRemote
    ? `${images.length} image references (${images.length - remoteCount} local + ${remoteCount} remote)`
    : `${images.length} local image references`;
  console.log(`Found ${scanScope}. Starting uploads...\n`);

  // 本地按绝对路径去重、远程按 URL 去重，统一收敛到一张映射表
  const uploadsMap = new Map();
  const missingFiles = [];
  const skippedRemote = [];

  for (const img of images) {
    if (img.isRemote) {
      // mirror 幂等：已托管在目标图床的远程图片直接跳过，避免反复搬运自己的图
      if (isAlreadyOnProvider(provider, img.relativePath)) {
        skippedRemote.push(img.relativePath);
        continue;
      }
      uploadsMap.set(img.relativePath, {
        relativePath: img.relativePath,
        isRemote: true,
        url: null
      });
      continue;
    }
    if (!img.exists) {
      missingFiles.push(img.relativePath);
      continue;
    }
    uploadsMap.set(img.absolutePath, {
      relativePath: img.relativePath,
      absolutePath: img.absolutePath,
      isRemote: false,
      url: null
    });
  }

  if (skippedRemote.length > 0) {
    console.log(`Skipped ${skippedRemote.length} remote image(s) already hosted on ${provider.displayName}.\n`);
  }

  if (missingFiles.length > 0) {
    console.warn(`Warning: The following referenced local files do not exist:\n${missingFiles.map(f => `  - ${f}`).join('\n')}\n`);
  }

  // Upload each unique existing image
  const mappings = [];
  for (const imgData of uploadsMap.values()) {
    try {
      let result;
      if (imgData.isRemote) {
        console.log(`  Mirroring remote ${imgData.relativePath}...`);
        result = await uploadRemoteImage(provider, imgData.relativePath);
      } else {
        console.log(`  Uploading ${path.basename(imgData.absolutePath)}...`);
        result = await uploadSingleImage(provider, imgData.absolutePath);
      }
      if (result.fromCache) {
        console.log(`    ↳ 命中内容指纹缓存，复用已有直链（未重复上传）`);
      }
      imgData.url = result.url;
      mappings.push({
        relativePath: imgData.relativePath,
        remoteUrl: result.url
      });
    } catch (err) {
      const label = imgData.isRemote ? imgData.relativePath : path.basename(imgData.absolutePath);
      console.error(`  Failed to upload ${label}: ${err.message}`);
    }
  }

  if (mappings.length === 0) {
    console.log('\nNo images were successfully uploaded.');
    return;
  }

  console.log('\nUpload mapping results:\n');
  console.log('| Source | Remote Direct URL | Markdown Reference |');
  console.log('|--------|-------------------|--------------------|');
  for (const map of mappings) {
    const filename = path.basename(map.relativePath.split('?')[0], path.extname(map.relativePath.split('?')[0]));
    console.log(`| ${map.relativePath.padEnd(10)} | ${map.remoteUrl.padEnd(17)} | ![${filename}](${map.remoteUrl}) |`);
  }

  if (replaceLinks) {
    console.log('\nReplacing links in-place...');
    replaceImageLinks(absolutePath, content, mappings);
    console.log(`Successfully updated document links in: ${absolutePath}`);
  }
}

async function main() {
  const options = parseArgs(process.argv.slice(2));

  if (options.help) {
    printHelp();
    process.exit(0);
  }

  if (options.list) {
    printProviders();
    process.exit(0);
  }

  if (options.args.length === 0) {
    console.error('Error: No file path provided.\n');
    printHelp();
    process.exit(1);
  }

  const targetPath = options.args[0];
  const absolutePath = path.resolve(targetPath);

  if (!fs.existsSync(absolutePath)) {
    console.error(`Error: File not found: ${absolutePath}`);
    process.exit(1);
  }

  const stat = fs.statSync(absolutePath);
  if (!stat.isFile()) {
    console.error(`Error: Path is not a file: ${absolutePath}`);
    process.exit(1);
  }

  const providerName = options.provider || process.env.IMAGE_UPLOAD_PROVIDER || 'imglink';
  const provider = getProvider(providerName);

  if (!provider) {
    console.error(`Error: Unknown provider "${providerName}". Run with --list to view valid providers.`);
    process.exit(1);
  }

  try {
    const ext = path.extname(absolutePath).toLowerCase();
    const docExtensions = ['.md', '.markdown', '.html', '.htm', '.txt'];

    if (docExtensions.includes(ext)) {
      // Document mode
      await handleDocumentUpload(provider, absolutePath, options.replace, options.mirror);
    } else {
      // Single image mode
      console.log(`Uploading ${path.basename(absolutePath)} to ${provider.displayName}...`);
      const result = await uploadSingleImage(provider, absolutePath, options.name);
      console.log(`\nUpload successful!${result.fromCache ? ' (命中缓存，复用已有直链，未重复上传)' : ''}\n`);
      console.log(`URL: ${result.url}`);
      console.log(`Markdown: ![${options.name || path.basename(absolutePath, ext)}](${result.url})`);
      console.log(`HTML: <img src="${result.url}" alt="${options.name || path.basename(absolutePath, ext)}">`);
      console.log(`BBCode: [IMG]${result.url}[/IMG]`);
      if (result.viewerUrl) console.log(`Viewer: ${result.viewerUrl}`);
      if (result.deleteUrl) console.log(`Delete: ${result.deleteUrl}`);
    }
  } catch (error) {
    console.error(`\nError during upload: ${error.message}`);
    process.exit(1);
  }
}

// Check if run directly
const isMain = process.argv[1] && (
  fs.realpathSync(process.argv[1]) === fs.realpathSync(fileURLToPath(import.meta.url))
);
if (isMain) {
  main();
}

// Export for programmatic use
export { scanDocument, replaceImageLinks } from './parser.mjs';
export async function uploadImage(imagePath, options = {}) {
  const absolutePath = path.resolve(imagePath);
  const providerName = options.provider || process.env.IMAGE_UPLOAD_PROVIDER || 'imglink';
  const provider = getProvider(providerName);

  if (!provider) {
    throw new Error(`Unknown provider: ${providerName}`);
  }

  const result = await uploadSingleImage(provider, absolutePath, options.name);
  const filename = options.name || path.basename(absolutePath, path.extname(absolutePath));
  return {
    ...result,
    formatted: {
      url: result.url,
      markdown: `![${filename}](${result.url})`,
      html: `<img src="${result.url}" alt="${filename}">`,
      bbcode: `[IMG]${result.url}[/IMG]`,
    }
  };
}
