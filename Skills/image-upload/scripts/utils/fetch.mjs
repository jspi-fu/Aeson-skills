/**
 * Fetch wrapper with timeout and transient error retries.
 * 
 * @param {string} url - Target URL
 * @param {RequestInit} options - Fetch options
 * @param {number} retries - Number of remaining retry attempts
 * @param {number} timeout - Request timeout in milliseconds
 * @returns {Promise<Response>}
 */
export async function fetchWithRetry(url, options = {}, retries = 2, timeout = 30000) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!response.ok) {
      if (response.status >= 500 && retries > 0) {
        await new Promise((resolve) => setTimeout(resolve, 1000));
        return fetchWithRetry(url, options, retries - 1, timeout);
      }
      // 读取响应体以暴露图床返回的具体原因（如 duplicate/flood 提示）
      let body = '';
      try {
        body = (await response.text()).trim();
      } catch {
        // 忽略读取失败，回退到仅状态码
      }
      const detail = body ? ` - ${body.slice(0, 300)}` : '';
      throw new Error(`HTTP ${response.status}: ${response.statusText}${detail}`);
    }
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') {
      if (retries > 0) {
        await new Promise((resolve) => setTimeout(resolve, 1000));
        return fetchWithRetry(url, options, retries - 1, timeout);
      }
      throw new Error(`Request timed out after ${timeout}ms`);
    }
    if (retries > 0) {
      await new Promise((resolve) => setTimeout(resolve, 1000));
      return fetchWithRetry(url, options, retries - 1, timeout);
    }
    throw error;
  }
}

/**
 * 下载远程资源为 Buffer（用于 mirror 模式把网络图片转存到目标图床）。
 *
 * @param {string} url - 远程资源地址
 * @param {number} timeout - 超时毫秒
 * @returns {Promise<Buffer>}
 */
export async function downloadBuffer(url, timeout = 30000) {
  const response = await fetchWithRetry(url, {}, 2, timeout);
  const arrayBuffer = await response.arrayBuffer();
  return Buffer.from(arrayBuffer);
}

/**
 * 轻量校验远程直链是否仍然可用（缓存命中时用，避免复用已被删除的死链）。
 * 用 HEAD 请求：2xx/3xx 视为存活；405 说明服务端不支持 HEAD 但资源大概率存在，
 * 也按存活处理，避免误判为死链而触发无谓重传（重传相同内容可能被 Chevereto 拒绝）。
 *
 * @param {string} url - 待校验的直链
 * @param {number} timeout - 超时毫秒
 * @returns {Promise<boolean>}
 */
export async function checkUrlAlive(url, timeout = 10000) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetch(url, { method: 'HEAD', signal: controller.signal });
    clearTimeout(timeoutId);
    return response.status < 400 || response.status === 405;
  } catch {
    clearTimeout(timeoutId);
    return false;
  }
}

