---
title: "窗口采集与原生 OCR"
created: "2026-10-08"
updated: "2026-10-09"
type: "entity"
tags: ["vision", "macos", "windows", "runtime"]
sources: ["docs/P7-VISUAL-BRIDGE.md", "docs/evidence/2026-10-09-visual-bridge/README.md", "src/bokkio/macos_capture.py", "src/bokkio/native/macos_capture.swift", "src/bokkio/visual.py", "src/bokkio/visual_runtime.py", "src/bokkio/windows_capture.py"]
confidence: "high"
---

# 窗口采集与原生 OCR

采集通过包内 API 和 `capture` CLI 独立于 AX/UIA 树提供图像；图像身份、时间和坐标必须跟随结果，不能只保存一张无上下文截图。^[src/bokkio/macos_capture.py#L41] ^[src/bokkio/windows_capture.py#L206]

## 平台实现

| 平台 | 捕获 | 坐标 |
|---|---|---|
| Windows | 隔离子进程 PrintWindow 客户区 | 图像物理像素加客户区屏幕原点 |
| Mac | Swift ScreenCaptureKit 窗口，忽略阴影/鼠标 | 图像像素按 content_rect 比例转屏幕点 |

Mac helper 随包分发并按源码哈希缓存编译；proc_pidinfo 创建时间绑定进程。Windows 捕获同步阻塞风险由工作进程超时隔离。^[src/bokkio/macos_capture.py#L17] ^[src/bokkio/windows_capture.py#L206]

## OCR 与范围

Mac 本机 Apple Vision revision 3 输出文字、置信度和像素框；`find_text()` 校验图像/OCR 同一哈希、时效、范围和唯一性，返回 `action_authorized=false`。本轮英文自绘窗口 3/3 与拒绝 8/8；中文业务、多 DPI 与 Windows live capture 不自动继承该验收。^[src/bokkio/visual.py#L40] ^[docs/P7-MACOS-VISUAL.md#L15]

## Mac公共视觉接入（2026-10-09）

WindowScope/VisualObservation/VisualPolicy/VisualProvider、MacVisionProvider与HybridBackend已实现；通过显式PID/固定标题窗口接入Agent/Jev/CLI，输入标签需声明，原生可用时零OCR。恢复保留范围/策略及观察预算。^[docs/P7-VISUAL-BRIDGE.md#L5]

主机435/435；最新三次独立Mac窗口只读观察与真实Jev visual_click选择均3/3（置信度1.0），模拟Agent click/type单独验证。锁屏activation实际拒绝，未派发输入；计数文字OCR仍未验收，Office历史0/3不变。Windows工作暂缓，视觉Workflow、图标和跨窗口扩展待完成。^[docs/evidence/2026-10-09-visual-bridge/README.md#L1]

关联：[[entities/visual-input]]、[[comparisons/native-and-visual-paths]]、[[concepts/permissions-and-sessions]]。
