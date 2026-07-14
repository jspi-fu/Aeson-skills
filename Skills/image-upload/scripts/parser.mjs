import fs from 'fs';
import path from 'path';

/**
 * Scans a Markdown or HTML document for local image references.
 *
 * @param {string} docPath - Absolute path to the document file
 * @param {object} [options]
 * @param {boolean} [options.includeRemote=false] - 是否同时收集远程 URL 图片（mirror 全量转存模式）
 * @returns {object} { content, images: [{ raw, relativePath, absolutePath, exists, isRemote }] }
 */
export function scanDocument(docPath, options = {}) {
  const { includeRemote = false } = options;
  const absoluteDocPath = path.resolve(docPath);
  if (!fs.existsSync(absoluteDocPath)) {
    throw new Error(`Document not found: ${absoluteDocPath}`);
  }

  const content = fs.readFileSync(absoluteDocPath, 'utf8');
  const docDir = path.dirname(absoluteDocPath);

  // Regex for Markdown images: ![alt](path)
  // alt 限定为不含 ']'，避免把 [![alt](url)](link) 这类带链接的徽章结构整体吞掉
  const mdRegex = /!\[([^\]]*)\]\(((?!https?:\/\/|data:image|\/\/).*?)\)/g;
  // Regex for HTML images: <img src="path" ...> or <img ... src="path">
  const htmlRegex = /<img\s+[^>]*src=["']((?!https?:\/\/|data:image|\/\/)[^"']+)["'][^>]*>/g;

  const imagesMap = new Map();

  let match;
  
  // Find Markdown matches
  mdRegex.lastIndex = 0;
  while ((match = mdRegex.exec(content)) !== null) {
    const raw = match[0];
    const relativePath = match[2];
    // Strip query parameters or hashes
    const cleanPath = decodeURIComponent(relativePath.split('?')[0].split('#')[0]);
    const absolutePath = path.resolve(docDir, cleanPath);
    const exists = fs.existsSync(absolutePath);

    imagesMap.set(relativePath, {
      raw,
      relativePath,
      absolutePath,
      exists,
      isRemote: false
    });
  }

  // Find HTML matches
  htmlRegex.lastIndex = 0;
  while ((match = htmlRegex.exec(content)) !== null) {
    const raw = match[0];
    const relativePath = match[1];
    // Strip query parameters or hashes
    const cleanPath = decodeURIComponent(relativePath.split('?')[0].split('#')[0]);
    const absolutePath = path.resolve(docDir, cleanPath);
    const exists = fs.existsSync(absolutePath);

    imagesMap.set(relativePath, {
      raw,
      relativePath,
      absolutePath,
      exists,
      isRemote: false
    });
  }

  // mirror 全量模式：额外收集文档内的远程 URL 图片，按 URL 去重
  if (includeRemote) {
    const mdRemoteRegex = /!\[([^\]]*)\]\((https?:\/\/[^\s)]+)\)/g;
    const htmlRemoteRegex = /<img\s+[^>]*src=["'](https?:\/\/[^"']+)["'][^>]*>/g;

    for (const remoteRegex of [mdRemoteRegex, htmlRemoteRegex]) {
      remoteRegex.lastIndex = 0;
      while ((match = remoteRegex.exec(content)) !== null) {
        const url = match[match.length - 1];
        if (imagesMap.has(url)) continue;
        imagesMap.set(url, {
          raw: match[0],
          relativePath: url,
          absolutePath: null,
          exists: true,
          isRemote: true
        });
      }
    }
  }

  return {
    content,
    images: Array.from(imagesMap.values())
  };
}

/**
 * Replaces local image references with remote URLs in the document content.
 * Writes changes back to disk.
 * 
 * @param {string} docPath - Absolute path to the document file
 * @param {string} originalContent - Original document content
 * @param {Array<{relativePath: string, remoteUrl: string}>} mappings - Mappings of local paths to remote URLs
 * @returns {string} The updated document content
 */
export function replaceImageLinks(docPath, originalContent, mappings) {
  let updatedContent = originalContent;

  for (const { relativePath, remoteUrl } of mappings) {
    // Escape path for split/join to do global safe replacement
    // Replacing (path) in Markdown syntax
    updatedContent = updatedContent.split(`(${relativePath})`).join(`(${remoteUrl})`);
    // Replacing src="path" in HTML
    updatedContent = updatedContent.split(`src="${relativePath}"`).join(`src="${remoteUrl}"`);
    updatedContent = updatedContent.split(`src='${relativePath}'`).join(`src='${remoteUrl}'`);
  }

  fs.writeFileSync(path.resolve(docPath), updatedContent, 'utf8');
  return updatedContent;
}
