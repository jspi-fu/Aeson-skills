---
name: beeimg-uploader
description: 批量图片上传工具，扫描本地目录中的所有图片文件并上传至蜜蜂图床，返回每张图片的公开访问地址，支持并发上传、速率控制、文件大小校验、递归扫描子目录与错误隔离；当用户需要批量上传图片到图床、获取图片外链地址、将本地图片目录同步到在线图床时使用
dependency:
  python:
    - requests>=2.28.0
---

# BeeImg Uploader - 批量图片上传蜜蜂图床

## 任务目标
- 本 Skill 用于: 快速批量上传本地目录下的所有图片到[蜜蜂图床](https://www.beeimg.cn/)，返回每张图片的公开访问地址
- 能力包含: 目录图片扫描、并发批量上传、速率控制(每分钟20张/每小时100张)、文件大小校验(10MB上限)、公开URL提取、失败隔离
- 触发条件: 用户需要批量上传图片、获取图片外链、将本地图片同步到图床

## 前置准备
- 依赖说明: Python 3.7+，requests 库
- 蜜蜂图床API无需认证，storage_id 默认值为 1
- 平台限制: 单文件最大10MB，并发上限10张，每分钟20张，每小时100张

## 操作步骤

### 1. 批量上传图片（核心流程）

使用 `batch_upload.py` 扫描目录并批量上传所有图片:

```bash
python scripts/batch_upload.py --dir ./images
```

**参数说明:**
| 参数 | 必填 | 说明 |
|------|------|------|
| --dir | 是 | 图片所在目录路径 |
| --storage-id | 否 | 蜜蜂图床存储ID，默认 1 |
| --recursive | 否 | 递归扫描子目录中的图片 |
| --concurrency | 否 | 并发上传数，上限10，默认 5 |
| --timeout | 否 | 单文件上传超时秒数，默认 30 |
| --extensions | 否 | 自定义扩展名过滤，逗号分隔（默认: jpg,jpeg,png,gif,bmp,webp,svg,tiff,tif） |
| --max-file-size | 否 | 最大文件大小(字节)，默认 10485760(10MB) |

**输出格式:** 脚本以JSON输出到stdout:
```json
{
  "status": "success",
  "total": 10,
  "success_count": 8,
  "fail_count": 1,
  "skipped_count": 1,
  "elapsed_time": 15.3,
  "rate_limit": {
    "uploads_this_minute": 8,
    "uploads_this_hour": 8,
    "limits": {"per_minute": 20, "per_hour": 100, "max_file_size_mb": 10, "max_concurrency": 10}
  },
  "results": [
    {
      "filename": "photo1.jpg",
      "public_url": "https://www.beeimg.cn/20240627/xxx.jpg",
      "width": 1920,
      "height": 1080,
      "md5": "abc123..."
    }
  ],
  "errors": [
    {"filename": "broken.png", "error": "HTTP 422: Invalid file"},
    {"filename": "huge.jpg", "error": "File size 15.20 MB exceeds limit of 10 MB"}
  ]
}
```

### 2. 提取公开访问地址

从脚本输出的 `results` 数组中提取每张图片的 `public_url` 字段，即为图片的公开访问外链。

向用户展示结果时，按以下格式整理:
- 文件名 -> 公开URL
- 汇总: 成功数/总数，耗时，速率限制使用情况

### 3. 速率控制与错误处理

脚本内建速率控制，自动遵守蜜蜂图床平台限制:
- **每分钟20张**: 超过时自动等待至下一分钟窗口
- **每小时100张**: 达到上限后停止上传，输出中附带 warning 提示
- **文件大小校验**: 超过10MB的文件在扫描阶段直接跳过，不消耗上传配额
- **单张失败隔离**: 某张图片上传失败不影响其他图片继续上传
- **429响应处理**: 收到频率限制响应时自动停止后续上传

常见错误:
| 错误 | 说明 | 建议 |
|------|------|------|
| HTTP 422 | 文件格式不支持或参数错误 | 检查文件是否为有效图片 |
| HTTP 429 | 请求频率超限 | 脚本已自动处理，降低 --concurrency |
| File size exceeds | 文件超过10MB | 压缩图片或调整 --max-file-size |
| Connection error | 网络问题 | 检查网络连通性 |

### 4. 辅助能力

#### 单文件上传

当只需上传单张图片时:
```bash
python scripts/api_call.py --method POST --url "https://www.beeimg.cn/api/v2/upload" \
  --headers '{"Accept":"application/json"}' \
  --form-data '{"storage_id":"1"}' \
  --files '{"file":"./photo.png"}'
```

#### API配置模板管理

保存和复用常用API配置:
```bash
python scripts/api_template.py save --name "beeimg-upload" \
  --method POST --url "https://www.beeimg.cn/api/v2/upload" \
  --headers '{"Accept":"application/json"}' \
  --form-data '{"storage_id":"1"}' \
  --description "蜜蜂图床图片上传"

python scripts/api_template.py list
python scripts/api_template.py run --name "beeimg-upload" --files '{"file":"./photo.jpg"}'
```

## 使用示例

### 示例1: 批量上传目录下所有图片
- 场景/输入: 用户本地 `./photos` 目录下有数十张图片，需要全部上传获取外链
- 执行: `python scripts/batch_upload.py --dir ./photos`
- 预期产出: 返回每张图片的 public_url、尺寸、MD5，以及速率限制使用情况
- 关键要点: 默认并发5张，自动遵守每分钟20张/每小时100张限制；超过10MB的文件自动跳过

### 示例2: 递归上传含子目录的图片库
- 场景/输入: 用户有一个按年份分类的图片库，子目录中也有图片
- 执行: `python scripts/batch_upload.py --dir ./photo-library --recursive --concurrency 3`
- 预期产出: 递归扫描所有子目录中的图片并上传
- 关键要点: `--recursive` 启用递归扫描；降低并发数可减少对网络的压力

### 示例3: 仅上传特定格式的图片
- 场景/输入: 用户目录中混有多种文件，只需上传 PNG 和 JPG
- 执行: `python scripts/batch_upload.py --dir ./mixed-files --extensions png,jpg,jpeg`
- 预期产出: 仅上传匹配扩展名的文件，其余忽略
- 关键要点: `--extensions` 支持自定义过滤，逗号分隔

## 资源索引
- 脚本: 见 [scripts/batch_upload.py](scripts/batch_upload.py)（核心批量上传脚本，扫描目录图片并发上传至蜜蜂图床，内建速率控制与文件大小校验，返回公开URL）
- 脚本: 见 [scripts/api_call.py](scripts/api_call.py)（通用API请求工具，用于单文件上传或自定义API调用）
- 脚本: 见 [scripts/api_template.py](scripts/api_template.py)（API配置模板管理，支持save/load/list/delete/run）
- 参考: 见 [references/beeimg-api.md](references/beeimg-api.md)（蜜蜂图床API完整接口规范与平台限制，何时读取: 需要了解API参数细节或排查上传问题时）

## 注意事项
- 蜜蜂图床平台限制: 单文件最大10MB，并发上限10张，每分钟20张，每小时100张
- 脚本已内建速率控制，默认并发5张，自动遵守平台限制
- 超过10MB的文件在扫描阶段跳过，不消耗上传配额
- 达到每小时100张上限后自动停止，输出中附带 warning
- 支持的图片格式: jpg/jpeg/png/gif/bmp/webp/svg/tiff/tif
- 上传无需认证，storage_id 默认为 1
- 仅在有实际需要时读取参考文档，保持上下文简洁
