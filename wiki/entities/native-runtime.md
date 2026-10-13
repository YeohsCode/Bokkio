---
title: "原生 Runtime：xa11y 适配层"
created: "2026-10-08"
updated: "2026-10-13"
type: "entity"
tags: ["runtime", "native", "windows", "macos"]
sources: ["src/bokkio/xa11y_backend.py", "src/bokkio/runtime.py", "docs/progress/STATUS.md"]
confidence: "high"
---

# 原生 Runtime：xa11y 适配层

本页的“原生 Runtime”指 `Xa11yBackend`，是 0.2.0 `runtime.Runtime` 下方的原生 backend；会话、企业授权与审批在 [[entities/runtime-core]]。旧 CLI/Agent/Workflow 也直接使用此 backend，但不会自动经过新 Core。^[src/bokkio/xa11y_backend.py#L55] ^[src/bokkio/runtime.py#L85]

## 接口与调用关系

| 接口 | 职责 / 下游 |
|---|---|
| apps / windows | xa11y.App.list 与应用树枚举 |
| snapshot(app, window) | _app_tree → xa11y 元素规范化 → MacAX/WindowsUIA 注解；可限定窗口 |
| find / get | selector/ref 查当前原生树 |
| perform | 重读同范围、核对树摘要/ref/状态/能力 → 原生派发 → 同范围读回/verification |

`runtime._native_call()` 用单一专用线程访问真实 backend；直接旧入口不因此自动获得 Core 的线程/桌面锁保障。共享支持模块为 model（错误/ref/hash）、selector（树与查询）、scroll（滚动与读回）。^[src/bokkio/runtime.py#L74] ^[src/bokkio/xa11y_backend.py#L132]

## macOS 与 Windows

- MacAX 通过 AX/CoreFoundation 补充属性、能力、字段/菜单动作；WindowsUIA 提供 Value/Scroll/Selection/Invoke 等能力和经典字段提交，基础树仍由 xa11y 适配。^[src/bokkio/xa11y_backend.py#L77]
- macOS 当前 `_app_tree(window_selector=...)` 在遍历目标窗口前计算兄弟身份，减少无关文档读取，保持 scoped/full ref 和动作前后范围一致。Windows 仍在树读取后做窗口选择，不能推广同一优化到两端。^[src/bokkio/xa11y_backend.py#L386] ^[src/bokkio/xa11y_backend.py#L394]
- 结构 ref 不是长期 OS 指针；应用重启、控件重建/重命名等需重新观察。disabled、不可提交或只读字段仍应拒绝；编辑值读回确认不等于表格业务模型已经提交。^[src/bokkio/xa11y_backend.py#L198] ^[docs/progress/STATUS.md#L34]

当前 Mac 精确窗口回归/实测与 Windows 当前 Runtime 验收应分别看 [[summaries/current-status]]。相关：[[concepts/element-identity]]、[[concepts/action-verification]]、[[summaries/module-call-map]]、[[comparisons/windows-and-macos]]。
