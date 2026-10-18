---
title: "原生 Runtime：xa11y 适配层"
created: "2026-10-08"
updated: "2026-10-18"
type: "entity"
tags: ["runtime", "native", "windows", "macos"]
sources: ["src/bokkio/xa11y_backend.py", "src/bokkio/runtime.py", "docs/progress/STATUS.md", "docs/WINDOWS-MACOS-INTEGRATION-RESULTS.md"]
confidence: "high"
---

# 原生 Runtime：xa11y 适配层

本页的“原生 Runtime”指 `Xa11yBackend`，是当前0.3.0 `runtime.Runtime` 下方的原生 backend；会话、企业授权与审批在 [[entities/runtime-core]]。旧 CLI/Agent/Workflow 也直接使用此 backend，但不会自动经过新 Core。^[src/bokkio/xa11y_backend.py#L55] ^[src/bokkio/runtime.py#L85]

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
- macOS 当前 `_app_tree(window_selector=...)` 在遍历目标窗口前计算兄弟身份，减少无关文档读取，保持 scoped/full ref 和动作前后范围一致。Windows本轮也已在正文递归前选择窗口；两端均保留兄弟身份计算，不把顶层元数据读取说成完全消除。^[src/bokkio/xa11y_backend.py#L554]
- 结构 ref 不是长期 OS 指针；应用重启、控件重建/重命名等需重新观察。disabled、不可提交或只读字段仍应拒绝；编辑值读回确认不等于表格业务模型已经提交。^[src/bokkio/xa11y_backend.py#L198] ^[docs/progress/STATUS.md#L34]

当前 Mac 精确窗口回归/实测与 Windows 当前 Runtime 验收应分别看 [[summaries/current-status]]。相关：[[concepts/element-identity]]、[[concepts/action-verification]]、[[summaries/module-call-map]]、[[comparisons/windows-and-macos]]。

## 本轮读取与接管接线

snapshot支持读取节点/时间/深度预算，Mac主遍历和补查共享；read.complete=false的树只读。网页整理与用户接管通过Core/Desktop入口接入，旧backend入口不自动拥有完整暂停协调。接口、代码位置和真实验收缺口见[[entities/native-observation-and-control]]。^[docs/WINDOWS-MACOS-INTEGRATION-RESULTS.md#L21]
