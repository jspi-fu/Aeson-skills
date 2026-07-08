# BeeImg 上传图片 API 参考文档

## 概览

蜜蜂图床(BeeImg)提供免费图片上传服务，支持图片存储与外链分享。本文档描述其上传API的完整接口规范与平台限制。

## 平台限制

| 限制项 | 值 |
|--------|-----|
| 最大文件大小 | 10.00 MB |
| 并发上传数量 | 10 张 |
| 每分钟上传限制 | 20 张 |
| 每小时上传限制 | 100 张 |

## 接口信息

- **接口地址**: `https://www.beeimg.cn/api/v2/upload`
- **请求方式**: POST
- **请求类型**: multipart/form-data
- **接口功能**: 上传图片文件，支持自定义存储、相册、过期时间、标签、公开状态等配置
- **详细API文档**: https://beeimg.apifox.cn/450605912e0

## 请求头(Headers)

| 参数 | 类型 | 说明 |
|------|------|------|
| Accept | string | `application/json` |

## 请求参数

| 参数名 | 类型 | 是否必填 | 说明 | 示例 |
|--------|------|----------|------|------|
| file | file | 是 | 二进制图片文件 | banner.png |
| storage_id | integer | 是 | 存储ID | 1 |
| album_id | integer | 否 | 相册ID(登录用户可用) | - |
| expired_at | string | 否 | 过期时间，格式: `yyyy-MM-dd HH:mm:ss` | - |
| tags[] | array[string] | 否 | 图片标签(登录用户可用) | ["街头摄影","城市建筑"] |
| is_public | boolean | 否 | 是否公开，默认false(登录用户可用) | false |
| is_remove_exif | boolean | 否 | 是否移除图片EXIF信息 | - |
| intro | string | 否 | 图片描述 | - |

## 调用示例

### 使用 batch_upload.py 批量上传

```bash
python scripts/batch_upload.py --dir ./images --recursive
```

### 使用 api_call.py 单文件上传

```bash
python scripts/api_call.py --method POST \
  --url "https://www.beeimg.cn/api/v2/upload" \
  --headers '{"Accept":"application/json"}' \
  --form-data '{"storage_id":"1","intro":"my photo"}' \
  --files '{"file":"./photo.png"}'
```

### 使用模板上传

```bash
# 先保存模板
python scripts/api_template.py save --name "beeimg-upload" \
  --method POST --url "https://www.beeimg.cn/api/v2/upload" \
  --headers '{"Accept":"application/json"}' \
  --form-data '{"storage_id":"1"}' \
  --description "蜜蜂图床图片上传"

# 复用模板上传
python scripts/api_template.py run --name "beeimg-upload" \
  --files '{"file":"./new-photo.jpg"}'
```

## 成功响应(200)

| 参数名 | 类型 | 说明 |
|--------|------|------|
| status | string | 响应状态 |
| message | string | 响应信息 |
| data | object | 图片数据 |
| data.id | integer | 图片ID |
| data.name | string | 图片名称(不含扩展名) |
| data.filename | string | 文件全名 |
| data.pathname | string | 物理存储路径 |
| data.mimetype | string | 文件MIME类型 |
| data.extension | string | 文件扩展名 |
| data.intro | string | 图片描述 |
| data.is_public | boolean | 是否公开 |
| data.md5 | string | 文件MD5值 |
| data.sha1 | string | 文件SHA1值 |
| data.ip_address | string | 上传IP |
| data.public_url | string | 图片公开访问地址 |
| data.width | integer | 图片宽度 |
| data.height | integer | 图片高度 |
| time | integer | 响应时间戳 |

### 响应示例

```json
{
  "status": "success",
  "message": "success",
  "data": {
    "id": 23,
    "name": "example",
    "filename": "example.gif",
    "pathname": "20240627/6a39702c8347047c6749854a40831de0.gif",
    "mimetype": "image/gif",
    "extension": "gif",
    "intro": "",
    "is_public": false,
    "md5": "6a39702c8347047c6749854a40831de0",
    "sha1": "570bdc9ae184db710ee74824a15725d5ed3db589",
    "width": 282,
    "height": 282,
    "ip_address": "127.0.0.1",
    "public_url": "https://www.beeimg.cn/20240627/6a39702c8347047c6749854a40831de0.gif"
  },
  "time": 1719468654
}
```

## 错误响应

| 状态码 | 说明 |
|--------|------|
| 422 | 参数错误(缺少必填参数或格式不正确) |
| 429 | 超出频率限制(每分钟20张/每小时100张) |

## 注意事项

1. 图片文件为**必传参数**，需以二进制形式上传
2. 单文件大小不超过 **10 MB**
3. `album_id`、`tags[]`、`is_public` 仅登录用户可使用
4. 过期时间需严格遵循 `yyyy-MM-dd HH:mm:ss` 格式
5. `storage_id` 必填，默认值为 `1`
6. 并发上传最多 **10** 张，每分钟最多 **20** 张，每小时最多 **100** 张
7. 触发频率限制会返回 429 状态码
