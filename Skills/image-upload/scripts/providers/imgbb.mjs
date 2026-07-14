import { fetchWithRetry } from '../utils/fetch.mjs';

export const imgbb = {
  name: 'imgbb',
  displayName: 'ImgBB',
  requiresConfig: true,
  maxFileSize: 32 * 1024 * 1024, // 32MB
  supportedTypes: ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp'],
  directHosts: ['i.ibb.co', 'ibb.co'], // mirror 幂等：远程 URL 已是该 host 则视为已托管，跳过再转存
  
  upload: async (buffer, filename) => {
    const apiKey = process.env.IMGBB_API_KEY;
    if (!apiKey) {
      throw new Error('Missing IMGBB_API_KEY in configuration. Get one free at https://api.imgbb.com/');
    }
    const base64Data = buffer.toString('base64');
    const formData = new FormData();
    formData.append('key', apiKey);
    formData.append('image', base64Data);
    if (filename) {
      formData.append('name', filename);
    }

    const response = await fetchWithRetry('https://api.imgbb.com/1/upload', {
      method: 'POST',
      body: formData,
    });

    const json = await response.json();
    if (!json.success || !json.data) {
      throw new Error(json.error?.message || 'Upload failed');
    }
    return {
      id: json.data.id,
      url: json.data.url,
      viewerUrl: json.data.url_viewer,
      deleteUrl: json.data.delete_url,
    };
  }
};
