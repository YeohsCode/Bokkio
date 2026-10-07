# P7：原生桌面视觉兜底与可靠性

P6 的 Windows 原生验收闭合后，P7 可以开始。项目继续围绕 **Computer Use**：操作系统窗口、原生应用和跨应用任务。

## 顺序与交付

| 子阶段 | 工作 | 退出条件 |
|---|---|---|
| P7.1 | Windows 自有窗口截图；统一窗口范围、DPI 和屏幕坐标；暴露截图与输入能力 | 图像绑定 PID/HWND、采集时间、尺寸与 SHA-256；最小化、窗口消失、权限不足有结构化错误 |
| P7.2 | OCR/视觉目标候选与降级策略 | 原生查找确定无目标或目标不暴露动作时才降级；候选保留截图区域、标签与置信度；歧义拒绝 |
| P7.3 | 有界坐标 click/type 与原生验证回路 | 自绘测试应用里完成点击和输入；执行前核验窗口、图像时效与坐标范围；操作后新截图/原生观察验证 |
| P7.4 | 取消、限速、确认与崩溃恢复 | 每次输入受执行预算和取消信号约束；敏感操作经明确策略确认；未知完成停止且不重复派发 |
| P7.5 | 持续回归与平台对照 | 原生路径、确定性 Workflow、Jev/Planner 和视觉路径分别统计；保存每次失败、耗时、中间检查与最终产物 |

**第一项实现**：Windows 窗口截图接口与自绘 fixture。fixture 只暴露窗口，不暴露内部按钮/输入框，迫使验收真正走视觉定位。先校验截图和 DPI，再增加 OCR 与坐标动作。2026-10-06 Mac AX 原生读取、动作和 Workflow 对照已恢复，见 [Mac 续测](MACOS-FOLLOWUP.md)；Mac 窗口采集与视觉路径仍需分别验收。Windows Office 激活继续暂缓。

**Mac Office 实测输入（2026-10-07）**：四应用 CUA 交互和六份文件校验通过，见 [报告](MACOS-OFFICE-REPORT.md)。Bokkio 需补齐 Word/PPT disabled 元数据下的编辑能力判断、Excel 单元格寻址/公式回读、Outlook 窗口限定后遍历，以及 AXPress 报错但 UI 已变化的未知完成处理。现有 CUA 能力不计作 Bokkio P7 实现；所有兜底仍需有界派发与操作后验证。

## 降级边界

- Element action 已派发且结果未知时，停止并恢复诊断；不能借视觉路径再点一次。
- AX/UIA 候选歧义时，必须取得新的可区分证据；旧 ref 或模型置信度不能直接选第一项。
- 截图绑定本次授权窗口。窗口移动、缩放、替换、重启或失去前台时重新观察和校验。
- Workflow 中的语义意图与验证条件继续保留。坐标步骤记录图像区域与动作回执；只有重新定位并验证后才可重放。

## 验收任务

1. 自绘应用：点击按钮 → 输入测试文字 → 独立检查新截图/可读业务结果。
2. 原生 UIA 任务：沿用 P6 参数化 Explorer → Notepad → Explorer，验证视觉功能不会改变默认原生路径。
3. 故障：窗口关闭、图像过期、DPI 变化、目标歧义、权限缺失、应用无响应、动作完成未知、暂停/取消。
4. 跨应用长流程：保留源文件 SHA-256、最终产物版本、新进程重开和中间步骤检查。

长期 benchmark 使用固定任务与独立 evaluator；本地开发验收与官方测试分数分别报告。

## English

P7 starts after Windows P6 acceptance closes. The first implementation is scoped native-window capture and a custom-drawn fixture, followed by OCR/visual candidates, bounded coordinate actions, post-action verification and reliability controls. Captures carry the authorized PID/HWND, time, dimensions, DPI mapping and content hash.

Visual fallback is allowed when accessibility cannot expose a target or action. Unknown dispatch completion stops execution; it cannot trigger a second coordinate action. Ambiguity needs fresh distinguishing evidence. Window changes invalidate the previous capture. Coordinate operations retain the semantic intent, screenshot region and receipt, with fresh verification before replay.

Acceptance covers a real click/type visual task, unchanged P6 native workflows and explicit fault cases. Regression reports separate native, deterministic, Jev/Planner and visual paths, with intermediate checks and independently verified deliverables. Mac AX fixture acceptance passes as recorded in the [Mac follow-up](MACOS-FOLLOWUP.md). The [Office CUA pilot](MACOS-OFFICE-REPORT.md) identifies editor metadata, cell readback, scoped traversal and unknown-dispatch gaps; it does not implement Bokkio fallback. Mac capture/visual acceptance, Windows Office activation and upstream benchmark integration remain pending.
