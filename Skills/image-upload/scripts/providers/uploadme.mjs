import { fetchWithRetry } from '../utils/fetch.mjs';

// UploadMe 基于 Chevereto，API 形态与 Freeimage 一致：
// POST /api/1/upload （不带尾斜杠），key + action=upload + source(base64) + format=json
export const uploadme = {
  name: 'uploadme',
  displayName: 'UploadMe',
  requiresConfig: true,
  maxFileSize: 200 * 1024 * 1024, // 200MB
  supportedTypes: ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp'],
  directHosts: ['cdn.uploaded.photo', 'uploadme.me'], // mirror 幂等：直链实际由 cdn.uploaded.photo 提供

  upload: async (buffer, filename) => {
    const apiKey = process.env.UPLOADME_API_KEY;
    if (!apiKey) {
      throw new Error('Missing UPLOADME_API_KEY in configuration. Get one free at https://uploadme.me/settings');
    }
    const base64Data = buffer.toString('base64');
    const formData = new FormData();
    formData.append('key', apiKey);
    formData.append('action', 'upload');
    formData.append('source', base64Data);
    formData.append('format', 'json');

    const response = await fetchWithRetry('https://uploadme.me/api/1/upload', {
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
