# 图床服务商参考

## 选择规则

- 需要上传 **SVG** → 必须用 **ImgLink**（其余三家拒绝 SVG，返回 `Unsupported MIME type`）
- 超大文件（>64 MB）→ **UploadMe**（上限 200 MB）
- 未指定 → 用 `IMAGE_UPLOAD_PROVIDER` 环境变量的值；未配置则默认 **ImgLink**

## 各服务商速查

| 服务商 | 环境变量 | 单文件上限 | SVG | API Key 获取地址 |
|--------|----------|-----------|-----|-----------------|
| ImgLink（默认） | `IMGLINK_API_KEY` | 50 MB | ✅ | https://imglink.cc/dashboard → API Keys |
| ImgBB | `IMGBB_API_KEY` | 32 MB | ❌ | https://api.imgbb.com/ |
| Freeimage | `FREEIMAGE_API_KEY` | 64 MB | ❌ | https://freeimage.host/page/api |
| UploadMe | `UPLOADME_API_KEY` | 200 MB | ❌ | https://uploadme.me/settings |

## Chevereto 重复上传说明

Freeimage / UploadMe 基于 Chevereto，重复内容返回 `code:101 Duplicated upload` 并**不返回直链**。
内容指纹缓存（`.image-upload-cache.json`）会在上传前做 SHA-256 去重 + HEAD 存活校验，命中缓存则直接复用直链，跳过上传。
