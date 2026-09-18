# 图床服务商参考

> 现状核实日期：2026-09-12。四家的上传端点、鉴权方式与响应结构均已按官方文档逐一复核。

## 选择规则

- 需要上传 **SVG / ICO** → 必须用 **ImgLink**（其余三家拒绝该格式，返回不支持的 MIME 类型）
- 需要上传 **AVIF** → 用 **ImgLink** 或 **UploadMe**（其余两家不收）
- 文件 **> 64 MB** → 四家都不支持，跳过该图并保留原链接
- 未指定 → 用 `IMAGE_UPLOAD_PROVIDER` 环境变量的值；未配置则默认 **ImgLink**

## 各服务商速查

| 服务商 | 环境变量 | 单文件上限 | 额外格式 | API Key 获取地址 |
|--------|----------|-----------|---------|-----------------|
| ImgLink（默认） | `IMGLINK_API_KEY` | 50 MB | SVG、ICO、AVIF | https://imglink.cc/dashboard → API Keys |
| ImgBB | `IMGBB_API_KEY` | 32 MB | — | https://api.imgbb.com/ |
| Freeimage | `FREEIMAGE_API_KEY` | 64 MB | — | https://freeimage.host/page/api |
| UploadMe | `UPLOADME_API_KEY` | 64 MB（游客 32 MB） | AVIF | https://uploadme.me/settings/api |

## 各服务商 API 现状（2026-09）

| 服务商 | 上传端点 | 鉴权 | 文件字段 | 响应取值 |
|--------|----------|------|----------|----------|
| ImgLink | `POST https://imglink.cc/api/v1/upload` | `X-API-Key` 请求头 | `file` | `json.url` / `json.viewer` / `json.delete` |
| ImgBB | `POST https://api.imgbb.com/1/upload` | `key` 表单字段 | `image`（base64） | `json.data.url` |
| Freeimage | `POST https://freeimage.host/api/1/upload` | `key` 表单字段 | `source`（base64） | `json.image.url` |
| UploadMe | `POST https://uploadme.me/api/1/upload` | `X-API-Key` 请求头（`key` 字段兜底） | `source`（base64） | `json.image.url` |

**ImgLink 注意**：站内 `/wiki`、`/blog` 页面里的 `/api/upload` + `Authorization: Bearer` 示例是通用示意，**与真实 API 不符**；权威说明在 https://imglink.cc/tools/sharex 的 "API reference" 一节。直链现由 `i.imglink.cc` 提供（viewer 页仍在 `imglink.cc`）。可选字段：`album`/`folder`、`visibility`、`private`、`nsfw`。

**UploadMe 注意**：API 已升级到 **v1.1**，文档地址由 `/page/api` 迁至 https://uploadme.me/api-v1；鉴权新增 `X-API-Key` 请求头（`key` 表单字段转为可选兜底）。上限 2025-07 由 20MB（登录）/10MB（游客）上调为 **64MB / 32MB**。2026-09-03 起额外接受 `.AVIF`、`.WEBM`、`.MOV`、`.MP4`。

## Chevereto 重复上传说明

Freeimage / UploadMe 基于 Chevereto，重复内容返回 `code:101 Duplicated upload` 并**不返回直链**。
内容指纹缓存（`.image-upload-cache.json`）会在上传前做 SHA-256 去重 + HEAD 存活校验，命中缓存则直接复用直链，跳过上传。
