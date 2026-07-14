import path from 'path';

/**
 * Detect MIME type using magic bytes or extension fallback.
 * 
 * @param {Buffer} buffer - File content buffer
 * @param {string} filePath - Path to the file
 * @returns {string}
 */
export function detectMimeType(buffer, filePath) {
  // Magic bytes check
  if (buffer[0] === 0x89 && buffer[1] === 0x50 && buffer[2] === 0x4e && buffer[3] === 0x47) return 'image/png';
  if (buffer[0] === 0xff && buffer[1] === 0xd8 && buffer[2] === 0xff) return 'image/jpeg';
  if (buffer[0] === 0x47 && buffer[1] === 0x49 && buffer[2] === 0x46) return 'image/gif';
  if (buffer[0] === 0x52 && buffer[1] === 0x49 && buffer[2] === 0x46 && buffer[3] === 0x46) return 'image/webp';
  if (buffer[0] === 0x42 && buffer[1] === 0x4d) return 'image/bmp';
  if (buffer[0] === 0x00 && buffer[1] === 0x00 && buffer[2] === 0x01 && buffer[3] === 0x00) return 'image/x-icon';

  // SVG 是文本型 XML，无固定二进制头，从首部内容中嗅探 <svg 标签
  if (buffer.slice(0, 1024).toString('utf8').includes('<svg')) return 'image/svg+xml';

  // File extension fallback
  const ext = path.extname(filePath).toLowerCase();
  const extToMime = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.webp': 'image/webp',
    '.bmp': 'image/bmp',
    '.ico': 'image/x-icon',
    '.svg': 'image/svg+xml'
  };
  return extToMime[ext] || '';
}

/**
 * Gets extension for a specific MIME type.
 * 
 * @param {string} mimeType - MIME type
 * @returns {string}
 */
export function getExtensionForMime(mimeType) {
  const mimeToExt = {
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/gif': '.gif',
    'image/webp': '.webp',
    'image/bmp': '.bmp',
    'image/x-icon': '.ico',
    'image/svg+xml': '.svg'
  };
  return mimeToExt[mimeType] || '';
}
