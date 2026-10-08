---
title: "权限与可用输入会话"
created: "2026-10-08"
updated: "2026-10-08"
type: "concept"
tags: ["safety", "macos", "windows", "vision"]
sources: ["src/bokkio/office_runner.py", "src/bokkio/native/macos_capture.swift", "src/bokkio/windows_capture.py", "docs/MACOS-CAPTURE-PROBE.md"]
confidence: "high"
---

# 权限与可用输入会话

权限预检查通过与交互会话可用是不同条件。窗口捕获可工作，也不能证明前台键鼠路径或 AX 业务节点可用。^[src/bokkio/office_runner.py#L18]

## Mac

当前记录为 AX/capture/events 权限 true，但测试会话报告锁定、前台 loginwindow。独立 ScreenCaptureKit 捕获自有窗口成功；AX 返回 application 代理，输入在原生守卫处拒绝。这个记录不是对用户眼前物理屏幕的通用判断。^[docs/MACOS-CAPTURE-PROBE.md#L5] ^[src/bokkio/native/macos_capture.swift#L88]

## Windows

Guest authentication 可以支持文件传输、构建和单元测试，但不保证启动进程拥有交互输入桌面。截图检查输入桌面、明确窗口和几何；已观察到 desktop_unavailable。^[src/bokkio/windows_capture.py#L96]

源码不应因任务受阻而关闭会话/范围检查。可继续准备代码、图像观察与评分，真实输入另行验收。^[docs/PENDING.md#L5]

关联：[[entities/capture-and-ocr]]、[[entities/visual-input]]、[[comparisons/windows-and-macos]]。
