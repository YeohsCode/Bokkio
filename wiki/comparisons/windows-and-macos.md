---
title: "Windows 与 Mac：能力和验收对照"
created: "2026-10-08"
updated: "2026-10-08"
type: "comparison"
tags: ["windows", "macos", "evidence"]
sources: ["docs/STATUS.md", "docs/MACOS-FOLLOWUP.md", "docs/P6-CLOSURE.md", "src/bokkio/windows_capture.py", "src/bokkio/macos_capture.py"]
confidence: "high"
---

# Windows 与 Mac：能力和验收对照

跨平台统一数据模型不意味着各平台已完成相同验收。环境、API、流程与日期必须保留。^[docs/STATUS.md#L5]

| 能力 | Windows | Mac |
|---|---|---|
| 原生层 | UIA + Value/Scroll/RuntimeId补充 | AX，当前读取出现代理节点 |
| P6 | 原计划与文件/进程扩展验收完成 | 历史 Cocoa 基础对照通过，文件扩展待完成 |
| 截图/OCR | 截图已编码，live验收和OCR待完成 | Runtime自绘3/3，拒绝8/8 |
| 视觉输入 | 未实现对应完整路径 | 代码存在，前置零派发拒绝，正向未通过 |
| Office | 已安装，激活继续暂缓 | CUA兼容性历史流程通过，Bokkio原题未开始 |

平台结果来源分别是 P6 和 Mac 续测报告，不能折成一个全平台成功率。^[docs/P6-CLOSURE.md#L5] ^[docs/MACOS-FOLLOWUP.md#L5]

坐标与截图边界也不同：Windows 当前使用客户区物理像素，Mac 图像映射屏幕点并包含窗口标题栏。^[src/bokkio/windows_capture.py#L53] ^[src/bokkio/macos_capture.py#L83]

关联：[[entities/native-runtime]]、[[concepts/permissions-and-sessions]]、[[summaries/current-status]]。
