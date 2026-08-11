---
name: linc-media
description: |
  用灯虹（LinC）生成单张图片或单条视频。
  触发场景："画一张…"、"生成一段 5 秒的海浪视频"、"用这张图做成视频"、"给我出个角色设定图"、
  "首尾帧做个转场"、"多镜头视频"、"帮我把这段提示词润色一下"。
  也用于：在做整片之前先试模型、试参数、试风格。
  NOT for: 多集短剧、剧本/分镜/成片全流程 → linc-drama。整理素材、合规预审核 → linc-assets。
  不覆盖语音合成（TTS）、LLM 对话、音视频合成——这些暂无对外文档。
  Chain signal: 用户在这里试出满意的模型和参数后要做整片 → linc-drama。参考素材要先过审 → linc-assets。
---

# 灯虹图片 / 视频生成

你是**视觉制作**，不是表单。用户要的是一张图或一条片子。

先读 [common/](../../common/) 下的共享规则：[auth.md](../../common/auth.md) · [models.md](../../common/models.md) · [billing.md](../../common/billing.md) · [async-tasks.md](../../common/async-tasks.md) · [errors.md](../../common/errors.md) · [upload.md](../../common/upload.md)

JSON 请求与扣费提交使用 [`common/scripts/linc_api.py`](../../common/scripts/linc_api.py)。它负责安全编码、错误检查，并在返回控制权前把任务和正确轮询路径原子写入 `LINC-*.json`。下文 curl 只用于说明端点和字段，不作为首选执行方式。

## 交流规则

- **不报 `task_id`，不贴原始 JSON。**
- **轮询静默。** 图片通常几十秒，视频几分钟。只在完成、失败、超 5 分钟时开口。
- **不叙述内部动作。** 说"我来生成"，不说"我调用 /api/ai/video/task"。
- 跟用户说什么语言就用什么语言。

## 开工检查（BLOCKING）

1. **凭证** —— `LINC_API_KEY` / `LINC_HOST`。跑 `GET /api/auth/me` 验，`Unauthorized` 就停。
2. **模型** —— `GET /api/ai/model-list?model_type=image` 或 `?model_type=video`。**禁止硬编码模型 ID / 分辨率 / 画幅 / 时长。** 该接口无需鉴权，可以最先调。

## 三件必须让用户知道的事

第一次提交前一次性说清：花的是**团队账户**的积分；**没有中止接口，提交了就停不下来也退不回来**；这次大概花多少。

平台**没有查余额的接口**，预估 + 确认是唯一防线。见 [models.md 的成本预估](../../common/models.md#成本预估重要)。

---

## 图片

提交前创建或选择对应状态文件，然后用 `submit`：`operation_type=media_task`、`id-field=data.id`、`poll-path=/api/ai/tasks/{operation_id}`。请求体先写入权限受控的临时 JSON 文件，避免提示词破坏 shell 引号。

```bash
curl -s -X POST "$LINC_HOST/api/ai/image/task" \
  -H "Authorization: Bearer $LINC_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "<来自 model-list>",
    "prompt": "电影感海边公路，清晨薄雾，一辆红色复古跑车",
    "aspect_ratio": "16:9",
    "resolution": "2K"
  }'
```

| 参数 | 必填 | 说明 |
|---|---|---|
| `model` | 是 | 来自 model-list |
| `prompt` | 是 | 去空白后不可为空。Kling 系列 ≤2500 字符 |
| `aspect_ratio` | 是 | **必须来自该模型的 `aspect_ratio` 数组** |
| `resolution` | 条件 | 模型 `resolution` 数组**非空时必填**且取值来自它；**数组为空时必须省略** |
| `image_list[].url` | 否 | 参考图。HTTP(S) URL 或 `data:image/png;base64,…`。数量 ≤ `max_reference_images` |
| `group_id` | 否 | 结果存哪个素材库文件夹。不传或 `root` = 根目录 |
| `asset_name` | 否 | 素材名 |

**模式由参考图决定**：不传 `image_list` = `text_to_image`；传了 = `image_to_image`。模型支不支持看 `gen_modes`。

**多图引用**：`prompt` 里用 `<image1>` / `<image2>` 指代 `image_list` 里对应位置的图（下标从 1 开始）。数组保留顺序、不去重。

> "保留 `<image1>` 的人物外观，采用 `<image2>` 的服装设计，出全身设定图"

**请求体 ≤ 16 MiB**（含 Base64）。超了直接 HTTP 413——大图先走 `POST /api/upload` 换成 URL，见 [upload.md](../../common/upload.md)。

返回 `data.id`。

**一个请求出一张。** 要 4 张就发 4 个请求，扣 4 次费。批量前把总数总价念给用户。

---

## 视频

和图片一样使用 `submit`，任务类型为 `media_task`，响应 ID 为 `data.id`。

```bash
curl -s -X POST "$LINC_HOST/api/ai/video/task" \
  -H "Authorization: Bearer $LINC_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "<来自 model-list>",
    "prompt": "海边日落，浪花拍打礁石",
    "resolution": "1080p",
    "aspect": "9:16",
    "duration": 8
  }'
```

| 参数 | 必填 | 说明 |
|---|---|---|
| `model` | 是 | 来自 model-list |
| `resolution` | 是 | 通常 `720p`/`1080p`/`4k`；模型 `aspect_ratio` 为空数组时用绝对尺寸如 `720x1280`；MiniMax-H3 用 `2k`/`768p`（大小写不敏感） |
| `duration` | 是 | 秒。必须在模型 `duration` 的 `{min,max}` 内 |
| `aspect` | 条件 | **字段名是 `aspect` 不是 `aspect_ratio`**。模型 `aspect_ratio` 非空时通常必填并取自该集合；**为空数组时必须省略** |
| `prompt` | 条件 | 一般必填。只有 kling-v3-omni 在传了 `shots` 时可省略 |
| `video_mode` | 否 | `text_to_video`/`image_to_video`/`start_end_to_video`/`multi_ref_to_video`；不传按参考素材自动推断 |
| `generate_audio` | 否 | Kling 系列不传 = 不生成 |
| `watermark` | 否 | 默认 false，**仅 seedance** |
| `auto_create_assets` | 否 | 默认 false，**仅 seedance**，其余模型传 `true` 报错。开启后参考素材临时创建审核用完清理，不进素材库也不占审核配额 |
| `group_id` | 否 | 结果归档分组 |

### 参考素材

- `image_list[].url` 必填非空；`image_list[].role` ∈ `first_frame` / `end_frame` / `reference_image`
- `video_list[].url`：**仅 MP4/MOV，≤200 MB，≥3 秒，宽高 720–2160 px**。`refer_type` ∈ `base`（待编辑，默认）/ `feature`（特征参考）；`keep_original_sound` ∈ `yes`（默认）/ `no`。后两个**仅 kling-v3-omni**
- `audio_list` 是**裸 URL 字符串数组**，不是 `[{url:…}]`

参考视频为 `base`（待编辑）时**不能同时定义首尾帧**。

### 多镜头（`shots`）

**仅 kling-v3 / kling-v3-omni。** 传了即启用多镜头，最多 6 个。

```json
"shots": [
  {"index": 1, "prompt": "主角推门而入，逆光剪影", "duration": 5},
  {"index": 2, "prompt": "特写：主角抬头，眼神坚定", "duration": 5}
]
```

`index` ≥1 且不重复；每镜 `prompt` ≤512 字符；**各镜 `duration` 之和必须等于顶层 `duration`**。

### MiniMax-H3

model ID 是 `minimax/minimax-h3`。分辨率 `2K`/`768P`，时长 5-15 秒。**所有模式都必须传 `prompt`。**

| 模式 | 素材 | `aspect` |
|---|---|---|
| `text_to_video` | 无 | 必填，`21:9`/`16:9`/`4:3`/`1:1`/`3:4`/`9:16` |
| `image_to_video` | 1 张图 | 可省，画幅跟随图片 |
| `start_end_to_video` | 1 张 `first_frame` + 1 张 `end_frame` | 可省，跟随首帧 |
| `multi_ref_to_video` | 图/视频/音频 | 必填，支持 `adaptive` + 六种固定比例 |

上限：图 ≤9、视频 ≤3、音频 ≤3，合计 ≤12。**多模态模式至少要有一张图或一段视频，不能只给音频。**

多模态 `prompt` 里按提交顺序用 `Image 1` / `Video 1` / `Audio 1` 引用素材。

返回 `data.id`。

---

## Pre-Submit Gate（BLOCKING）

- [ ] `model` 来自 model-list 实时返回
- [ ] `resolution` 在该模型 `resolution` 数组里（数组为空则已省略该字段）
- [ ] 图片的 `aspect_ratio` / 视频的 `aspect` 取值合法（空数组则已省略）
- [ ] 视频 `duration` 在模型 `{min,max}` 内
- [ ] 参考素材数量 ≤ `max_reference_images` / `max_reference_videos` / `max_reference_audios`
- [ ] 目标模式在该模型 `gen_modes` 里
- [ ] 该模型 `review_asset_enabled=true` 时，参考素材已走审核素材库（→ [linc-assets](../linc-assets/SKILL.md)）
- [ ] 已把预估消耗念给用户，用户确认了
- [ ] 已告诉用户提交后无法中止

## 轮询与交付

优先读取状态文件中该操作的 `poll_path`，再通过共享脚本查询。单图/单视频的路径应当是 `/api/ai/tasks/{task_id}`。

```bash
curl -s "$LINC_HOST/api/ai/tasks/$TASK_ID" -H "Authorization: Bearer $LINC_API_KEY"
```

`data.status` ∈ `pending`/`processing`/`completed`/`failed`，结果在 `data.url`。前 2 分钟每 10 秒查一次，之后每 30 秒。**静默**。

失败看 `data.error_code`，见 [errors.md](../../common/errors.md)。

交付：给用户 `data.url`，说清这次花了多少。

## 提示词润色

同步，不扣费（文档未标 `InsufficientBalance`）：

```bash
curl -s -X POST "$LINC_HOST/api/prompts/generate" \
  -H "Authorization: Bearer $LINC_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"type":"role","input":"角色：林栖。银发狐妖少女，改良汉服，手持发光画笔。风格：2D 动画，干净线条。"}'
```

`type` ∈ `role` / `prop` / `scene`。`input` 由你自己拼上下文（主体信息 + 风格要求）。返回 `data.prompt`。

用户提示词很简略时，可以先润色再生成——但**要把润色后的提示词给用户看过再提交**，别偷偷替换。

## 不覆盖

有路由但无对外文档，**不要调用**：`/api/ai/audio/tts`、`/api/ai/audio/voices`、`/api/ai/llm/chat[/stream]`、`/api/ai/composition/compose`、全部 legacy `/api/ai/image/*/generate`。

用户要这些能力 → 如实说目前没有公开接口，建议去控制台操作。

## 遇到问题

见 [references/troubleshooting.md](references/troubleshooting.md)。
