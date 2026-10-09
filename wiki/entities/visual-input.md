---
title: "有界视觉输入：代码与验收边界"
created: "2026-10-08"
updated: "2026-10-09"
type: "entity"
tags: ["vision", "safety", "macos"]
sources: ["docs/P7-MACOS-VISUAL.md", "docs/PENDING.md", "docs/evidence/2026-10-08-office-live/README.md", "docs/evidence/2026-10-09-office-fix/README.md", "src/bokkio/native/macos_capture.swift", "src/bokkio/visual_input.py", "tests/test_visual_input.py"]
confidence: "high"
---

# 有界视觉输入：代码与验收边界

Mac visual_input.perform支持click/type/replace。一般目标用OCR唯一候选；内部Office路径可绑定当前唯一可写combo的原生边界，模型仍选择闭合ref，不提供坐标。^[src/bokkio/visual_input.py#L11]

## 派发与确认

helper核对图像/进程出生时间、窗口身份/几何、时效、会话和前台。replace执行点击、Cmd+A、文字与Enter共8个事件；新观察确认文字或新鲜原生字段值。receipt丢失或派发后验证失败为input_completion_unknown，不能自动重试。^[src/bokkio/visual_input.py#L57]

独立Excel脚本探针用较早OCR字段定位确认两次替换并保存，独立货币格式校验通过。最新原生边界路径仍有零派发拒绝和派发后确认失败，尚未通过完整Agent任务。^[docs/evidence/2026-10-08-office-live/README.md#L20]

Office runner仅在授权文档窗口的可写combo接入transport。通用Agent自动降级、Windows输入、视觉Workflow和完整取消/限速/恢复仍待实现或验收。^[docs/PENDING.md#L5]

## 后续修复（2026-10-09）

输入拒绝与回读诊断已保留到Agent trace；同一字段最多3次回读，不重复派发。显式split button点击收窄后，真实Jev对记录的PPT快照返回click、置信度1.0（阈值0.7）。主机411/411；Mac当前锁屏，新GUI任务未开始，历史0/3仍为最新产物成绩。该决策探针没有live dispatch或Agent分数。^[docs/evidence/2026-10-09-office-fix/README.md#L1]

关联：[[entities/capture-and-ocr]]、[[concepts/action-verification]]、[[summaries/pending-and-known-gaps]]。
