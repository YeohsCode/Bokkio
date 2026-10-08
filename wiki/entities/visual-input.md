---
title: "有界视觉输入：代码与验收边界"
created: "2026-10-08"
updated: "2026-10-08"
type: "entity"
tags: ["vision", "safety", "macos"]
sources: ["src/bokkio/visual_input.py", "src/bokkio/native/macos_capture.swift", "docs/P7-MACOS-VISUAL.md", "tests/test_visual_input.py"]
confidence: "high"
---

# 有界视觉输入：代码与验收边界

Mac `visual_input.perform()` 已实现单次 click/type API，但真实正向输入尚未通过；当前证据是输入前置拒绝且派发为零。^[src/bokkio/visual_input.py#L11] ^[docs/P7-MACOS-VISUAL.md#L15]

## 前置和后置检查

API 要求当前 OCR 目标、原始图像、完整身份、允许的动作/有界字面文字，以及明确的操作后文字。Native helper 再查进程/窗口、图像与几何、时效、会话和前台范围；不允许通过 caller confidence 直接跳过。^[src/bokkio/native/macos_capture.swift#L88]

CGEventPost 没有交付确认。回执丢失或派发后的观察/文字验证失败是 `input_completion_unknown`，不能自动重试。前置 pause/cancel 已有测试；完整运行期取消、限速和视觉 Workflow 待补齐。^[src/bokkio/visual_input.py#L39]

## 尚未接入

该 API 没有成为 DesktopAgent 的自动视觉降级，也未提供 Windows 对应输入路径或已验收跨应用正向流程。源码中存在某 API 不能作为能力已可用的证据。^[docs/STATUS.md#L5]

关联：[[entities/capture-and-ocr]]、[[concepts/action-verification]]、[[summaries/pending-and-known-gaps]]。
