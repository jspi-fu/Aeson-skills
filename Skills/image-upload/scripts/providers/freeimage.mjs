import { fetchWithRetry } from '../utils/fetch.mjs';

export const freeimage = {
  name: 'freeimage',
  displayName: 'Freeimage.host',
  requiresConfig: true,
  maxFileSize: 64 * 1024 * 1024, // 64MB
  supportedTypes: ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp'],
  directHosts: ['iili.io', 'freeimage.host'], // mirror 幂等：远程 URL 已是该 host 则视为已托管，跳过再转存
  
  upload: async (buffer, filename) => {
    const apiKey = process.env.FREEIMAGE_API_KEY;
    if (!apiKey) {
      throw new Error('Missing FREEIMAGE_API_KEY in configuration. Get one free at https://freeimage.host/page/api');
    }
    const base64Data = buffer.toString('base64');
    const formData = new FormData();
    formData.append('key', apiKey);
    formData.append('action', 'upload');
    formData.append('source', base64Data);
    formData.append('format', 'json');

    // 末尾不能带斜杠：freeimage.host 会对 .../upload/ 返回 301 重定向，
    // 导致 POST 降级为 GET、表单丢失，服务端改回 HTML 页面。
    const response = await fetchWithRetry('https://freeimage.host/api/1/upload', {
      method: 'POST',
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
