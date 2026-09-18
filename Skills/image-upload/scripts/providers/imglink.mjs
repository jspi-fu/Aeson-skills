import { fetchWithRetry } from '../utils/fetch.mjs';
import { getExtensionForMime } from '../utils/mime.mjs';

// ImgLink 自有 REST API（权威参考：https://imglink.cc/tools/sharex 的 "API reference" 一节）：
// POST /api/v1/upload，X-API-Key 请求头鉴权，原始文件走 multipart 字段 file
// 响应 { success, id, url, viewer, thumbnail, delete, ... }；单文件上限 50MB（已验证邮箱账号）。
// 注意：站内 /wiki 与 /blog 页面里的 /api/upload + Authorization: Bearer 写法是通用示意，与真实 API 不一致，勿参照。
export const imglink = {
  name: 'imglink',
  displayName: 'ImgLink',
  requiresConfig: true,
  maxFileSize: 50 * 1024 * 1024, // 50MB
  supportedTypes: ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp', 'image/avif', 'image/svg+xml', 'image/x-icon'],
  // mirror 幂等：直链现由 i.imglink.cc 提供，viewer/管理页仍在 imglink.cc
  directHosts: ['imglink.cc', 'i.imglink.cc'],

  upload: async (buffer, filename, mimeType) => {
    const apiKey = process.env.IMGLINK_API_KEY;
    if (!apiKey) {
      throw new Error('Missing IMGLINK_API_KEY in configuration. Create one at https://imglink.cc/dashboard');
    }
    const ext = getExtensionForMime(mimeType);
    const formData = new FormData();
    formData.append('file', new Blob([buffer], { type: mimeType }), `${filename}${ext}`);

    const response = await fetchWithRetry('https://imglink.cc/api/v1/upload', {
      method: 'POST',
      headers: { 'X-API-Key': apiKey },
      body: formData,
    });

    const json = await response.json();
    if (!json.success || !json.url) {
      throw new Error(json.error || 'Upload failed');
    }
    return {
      id: json.id,
      url: json.url,
      viewerUrl: json.viewer,
      deleteUrl: json.delete,
    };
  }
};
