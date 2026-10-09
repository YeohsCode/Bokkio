---
title: "权限与可用输入会话"
created: "2026-10-08"
updated: "2026-10-09"
type: "concept"
tags: ["safety", "macos", "windows", "vision"]
sources: ["docs/MACOS-CAPTURE-PROBE.md", "docs/PENDING.md", "docs/evidence/2026-10-08-macos-session-recovery/readiness.json", "docs/evidence/2026-10-08-office-live/round-10/run.json", "src/bokkio/macos_activation.py", "src/bokkio/native/macos_capture.swift", "src/bokkio/office_runner.py", "src/bokkio/visual_input.py", "src/bokkio/windows_capture.py"]
confidence: "high"
---

# 权限与可用输入会话

权限通过与交互会话可用是不同条件，截图可用也不能证明前台输入或AX业务节点可用。每次运行检查当时状态，历史锁定记录不是用户当前物理屏幕的判断。^[src/bokkio/office_runner.py#L18]

## Mac

早期会话阻断后，恢复fixture三轮动作与12次滚动通过；第八轮后曾再次锁屏，随后解锁。第十轮启动报告session_locked=false，AX/capture/events=true；Word/Excel/PPT任务仍失败，应诊断输入确认、窗口守卫和决策，而不能继续归因锁屏。^[docs/evidence/2026-10-08-office-live/round-10/run.json#L1]

真实前台激活用Cocoa helper确认精确PID/窗口；限定输入仍检查图像、进程出生时间、窗口/几何和前台。派发后确认未知不能作为零派发重试。^[src/bokkio/macos_activation.py#L10] ^[src/bokkio/visual_input.py#L11]

## Windows

Guest认证可支持构建和文件传输，不保证进程拥有交互输入桌面。Windows截图实机像素、OCR与输入验收仍待完成。^[docs/PENDING.md#L17]

关联：[[entities/capture-and-ocr]]、[[entities/visual-input]]、[[comparisons/windows-and-macos]]。
