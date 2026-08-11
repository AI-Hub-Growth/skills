# Changelog

本技能包版本跟随灯虹（LinC）对外 API 契约。接口路径、必填参数、扣费口径、`auto-produce` 阶段枚举、`model-list` 字段语义发生变化时发新版本。

格式参照 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [0.1.0] - 2026-08-10

首个版本。

### Added

- `linc-drama` —— 整部短剧制作。一键链路（`POST /api/storyboards/auto-produce`）与分步链路（建项目 → 剧本 → 资产 → 参考图 → 分镜项目 → 分镜 → 分集视频 → 导出）双路径，含分镜导出/编辑/preview/apply 往返流程。
- `linc-media` —— 单张图片（`POST /api/ai/image/task`）、单条视频（`POST /api/ai/video/task`）、提示词润色（`POST /api/prompts/generate`）。
- `linc-assets` —— 素材库目录与资产管理、审核素材库合规预审核。
- `plugins/linc/common/` 共享规则：`auth.md`、`models.md`、`billing.md`、`async-tasks.md`、`errors.md`、`upload.md`、`api-index.md`。
- 共享 HTTP/状态脚本：校验 HTTPS Host、拒绝跨域与重定向、检查 HTTP/业务错误、原子记录任务类型和轮询路径。
- Claude Code 与 Codex marketplace 清单，插件实体位于标准 `plugins/linc/` 布局。
- 安装文档：`INSTALL.md`（给人看）、`INSTALL_FOR_AGENTS.md`（给 agent 看）。
- CI 校验 `scripts/validate.py`：frontmatter、链接与锚点、manifest、恢复契约、版本一致性、明文密钥和生成文件检测；附共享脚本离线单测。

### 已知限制

- **并发上限、单次批量条数上限平台未公开**。技能包写了保守默认（批量不超过 3 并发），遇 `UpstreamError.RateLimited` 退避重试。
- 不覆盖无对外文档的能力：TTS、LLM chat、composition、legacy 图片接口。
- HTTP 提交与本地状态不能组成跨系统事务；提交结果不明确时默认禁止自动重发，并先通过读取接口对账。
- Cursor 安装尚未实装验证；首版正式支持 Claude Code 与 Codex。

[0.1.0]: https://github.com/AI-Hub-Growth/skills/releases/tag/v0.1.0
