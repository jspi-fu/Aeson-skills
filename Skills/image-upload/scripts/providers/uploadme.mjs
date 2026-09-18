import { fetchWithRetry } from '../utils/fetch.mjs';

// UploadMe 基于 Chevereto，API 已升级到 v1.1（文档迁移至 https://uploadme.me/api-v1）：
// POST /api/1/upload （不带尾斜杠），source(base64) + format=json；
// 鉴权首选 X-API-Key 请求头，key 表单字段保留为无请求头场景的兜底。
// 单文件上限：登录用户 64MB、游客 32MB（2025-07 由 20MB/10MB 上调）；2026-09 起额外接受 AVIF。
export const uploadme = {
  name: 'uploadme',
  displayName: 'UploadMe',
  requiresConfig: true,
  maxFileSize: 64 * 1024 * 1024, // 64MB（登录用户上限；游客为 32MB）
  supportedTypes: ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp', 'image/avif'],
  directHosts: ['cdn.uploaded.photo', 'uploadme.me'], // mirror 幂等：直链实际由 cdn.uploaded.photo 提供

  upload: async (buffer, filename) => {
    const apiKey = process.env.UPLOADME_API_KEY;
    if (!apiKey) {
      throw new Error('Missing UPLOADME_API_KEY in configuration. Get one free at https://uploadme.me/settings/api');
    }
    const base64Data = buffer.toString('base64');
    const formData = new FormData();
    // API v1.1 首选 X-API-Key 请求头鉴权；key 字段保留作兜底
    formData.append('key', apiKey);
    formData.append('action', 'upload');
    formData.append('source', base64Data);
    formData.append('format', 'json');

    const response = await fetchWithRetry('https://uploadme.me/api/1/upload', {
      method: 'POST',
      headers: { 'X-API-Key': apiKey },
      body: formData,
    });

    const json = await response.json();
    if (json.status_code !== 200 || !json.image) {
      throw new Error(json.error?.message || 'Upload failed');
    }
    return {
      id: json.image.name,
      url: json.image.url,
      viewerUrl: json.image.url_viewer,
      deleteUrl: json.image.delete_url,
    };
  }
};
