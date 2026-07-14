import { fetchWithRetry } from '../utils/fetch.mjs';
import { getExtensionForMime } from '../utils/mime.mjs';

// ImgLink 自有 REST API：X-API-Key 请求头鉴权，原始文件走 multipart 字段 file
export const imglink = {
  name: 'imglink',
  displayName: 'ImgLink',
  requiresConfig: true,
  maxFileSize: 50 * 1024 * 1024, // 50MB
  supportedTypes: ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp', 'image/svg+xml', 'image/x-icon'],
  directHosts: ['imglink.cc'], // mirror 幂等：远程 URL 已是该 host 则视为已托管，跳过再转存

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
