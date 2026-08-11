# 上传与素材引用

## 上传文件

```bash
curl -s -X POST "$AICANVAS_HOST/api/upload" \
  -H "Authorization: Bearer $AICANVAS_API_KEY" \
  -F "file=@./ref.png" \
  -F "keyPrefix=images"
```

`multipart/form-data`。`file` 必填；`keyPrefix` 可选（如 `thumbnails` / `images` / `videos`），不传落 `uploads/`。

返回 `data.url`（CDN URL）、`data.hash`、`data.name`、`data.size`。**后续所有生成接口的参考素材，都用这个 `data.url`。**

没有预签名直传，只有这一条服务端转存。不扣费。

### 支持的类型

- 图片 PNG / JPEG / WebP
- 视频 MP4 / MOV
- 音频 MP3 / WAV / M4A
- 文档 TXT / Markdown / JSON / CSV / YAML / PDF / DOC / DOCX

**明确拒绝**：HTML、XHTML、MHTML、SVG、JavaScript、SWF 等主动内容。

**按实际内容校验，不看扩展名。** 改后缀名绕不过去——用户拿一个 `.png` 后缀的 SVG 来，一样报 `Upload.UnsupportedFormat`。遇到这个错就直说文件格式不受支持，不要重试、不要建议改后缀。

限制：图片 2000 万像素；JSON 16 MiB；DOCX 解压校验 128 MiB。

## 视频裁剪转存

```bash
curl -s -X POST "$AICANVAS_HOST/api/upload/process-video" \
  -H "Authorization: Bearer $AICANVAS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"videoUrl":"https://…/v.mp4","startTime":"00:00:10","endTime":"00:00:30"}'
```

拿公网视频 URL，按需裁剪后转存，返回 `data.url`。不传 `startTime`/`endTime` 就只校验并原样返回原 URL。时间格式固定 `HH:MM:SS`。

用途：用户给了一段长视频但只想引用其中一段。

## 三个容易混的字段

这三个长得像，但语义完全不同，**不能互换**：

| 字段 | 是什么 | 用在哪 |
|---|---|---|
| `image_list[].url` / `video_list[]` / `audio_list[]` | **输入**：参考素材的 URL 字符串 | `POST /api/ai/image/task`、`POST /api/ai/video/task` |
| `referenceAssetIdList` | **输入**：参考图的 media_asset **ID 数组**（不是 URL） | 短剧资产：`POST /api/storyboards/{id}/assets`、`POST /api/storyboards/{id}/assets/{asset_id}` |
| `group_id` / `asset_group_id` | **输出**：结果存到哪个素材库文件夹 | 生成类接口、建项目接口 |

划重点：

- **`group_id` 不是参考素材。** 它只决定产物归档位置，传不传都不影响生成内容。不传或传 `root` = 素材库根目录。传了不存在的文件夹 → `ResourceNotFound`。
- **`referenceAssetIdList` 要 ID，不要 URL。** ID 从素材库接口拿（见 [aicanvas-assets](../skills/aicanvas-assets/SKILL.md)）。把 `POST /api/upload` 返回的 URL 塞进去必然失败。
- **`image_list[].url` 要 URL，不要 ID。** 反过来同理。

单条视频生成的 `image_list[]` 还有个 `role` 字段：`first_frame` / `end_frame` / `reference_image`。选哪个要和模型的 `gen_modes` 对上——`start_end_to_video` 才认首尾帧。见 [models.md](./models.md#gen_modes)。

## 审核素材库是另一回事

`model-list` 里 `review_asset_enabled=true` 的模型，参考素材必须先过审核素材库（`POST /api/review-assets`），不能直接给 URL。见 [aicanvas-assets](../skills/aicanvas-assets/SKILL.md)。
