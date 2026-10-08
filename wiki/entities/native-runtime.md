---
title: "原生 Runtime：xa11y 适配层"
created: "2026-10-08"
updated: "2026-10-08"
type: "entity"
tags: ["runtime", "native", "windows", "macos"]
sources: ["src/bokkio/xa11y_backend.py", "src/bokkio/windows_uia.py", "src/bokkio/selector.py"]
confidence: "high"
---

# 原生 Runtime：xa11y 适配层

`Xa11yBackend` 是原生应用发现、树读取、元素查找与动作派发入口；Windows UIA 补充不替代整套树模型。^[src/bokkio/xa11y_backend.py#L52]

## 关键接口

| 接口 | 职责 |
|---|---|
| apps / windows | 枚举应用和窗口 |
| snapshot(app, window) | 取得新原生树，可限定窗口 |
| find / get | 按语义或 ref 读取当前元素 |
| perform | 检查范围、树版本、状态、能力，然后派发并读回 |

窗口筛选发生在应用树构建之后。因此不支持的深层子树仍可能先导致失败；Outlook 的深度保护问题是相关实例。^[src/bokkio/xa11y_backend.py#L108]

## 状态与平台差异

Windows `WindowsUIA` 提供 ValuePattern、ScrollPattern、RuntimeId 和有范围的原生动作。Mac AX 的 disabled 编辑区与 application 代理必须当作实际能力缺口诊断，不能全局忽略 enabled 检查。^[src/bokkio/windows_uia.py#L14] ^[src/bokkio/xa11y_backend.py#L174]

关联：[[concepts/element-identity]]、[[concepts/action-verification]]、[[comparisons/windows-and-macos]]。
