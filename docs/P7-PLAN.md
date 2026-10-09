# P7：原生桌面视觉兜底与可靠性

P6 的 Windows 原生验收已闭合，P7 当前为部分实现与验收。Mac 捕获/OCR Runtime 已通过，Windows 截图代码已落地但实机像素验收待完成；有界输入正向及自动 Agent 降级仍待完成。两端最新隔离回归各 373/373，阶段位置见 [总体进度](STATUS.md)。项目继续围绕 **Computer Use**：操作系统窗口、原生应用和跨应用任务。

## 2026-10-09公共接口进展

Mac provider与公共OCR协议、Agent/Jev/CLI显式窗口降级已实现。主机435/435；原生只读观察与真实Jev决策3/3。当前锁屏，实际输入未派发；视觉Workflow和更多目标类型待实现。Windows工作按用户要求暂缓。见[P7视觉接入](P7-VISUAL-BRIDGE.md)。下方日期记录保留当时结果。

## 顺序与交付

| 子阶段 | 工作 | 退出条件 |
|---|---|---|
| P7.1 | Windows 自有窗口截图；统一窗口范围、DPI 和屏幕坐标；暴露截图与输入能力 | 图像绑定 PID/HWND、采集时间、尺寸与 SHA-256；最小化、窗口消失、权限不足有结构化错误 |
| P7.2 | OCR/视觉目标候选与降级策略 | 原生查找确定无目标或目标不暴露动作时才降级；候选保留截图区域、标签与置信度；歧义拒绝 |
| P7.3 | 有界坐标 click/type 与原生验证回路 | 自绘测试应用里完成点击和输入；执行前核验窗口、图像时效与坐标范围；操作后新截图/原生观察验证 |
| P7.4 | 取消、限速、确认与崩溃恢复 | 每次输入受执行预算和取消信号约束；敏感操作经明确策略确认；未知完成停止且不重复派发 |
| P7.5 | 持续回归与平台对照 | 原生路径、确定性 Workflow、Jev/Planner 和视觉路径分别统计；保存每次失败、耗时、中间检查与最终产物 |

**第一项实现**：Windows 窗口截图接口与自绘 fixture。fixture 只暴露窗口，不暴露内部按钮/输入框，迫使验收真正走视觉定位。先校验截图和 DPI，再增加 OCR 与坐标动作。2026-10-06 Mac AX 原生读取、动作和 Workflow 对照已恢复，见 [Mac 续测](MACOS-FOLLOWUP.md)；Mac 基础窗口采集/OCR 已验收，后续输入、平台扩展及视觉链路仍需分别验收。Windows Office 激活继续暂缓。

**Mac Office 实测输入（2026-10-07）**：四应用 CUA 交互和六份文件校验通过，见 [报告](MACOS-OFFICE-REPORT.md)。Bokkio 需补齐 Word/PPT disabled 元数据下的编辑能力判断、Excel 单元格寻址/公式回读、Outlook 窗口限定后遍历，以及 AXPress 报错但 UI 已变化的未知完成处理。现有 CUA 能力不计作 Bokkio P7 实现；所有兜底仍需有界派发与操作后验证。

## 可继续的 Mac 路径（2026-10-08）

[独立窗口截图诊断](MACOS-CAPTURE-PROBE.md) 已通过 3/3，可推进 Mac 采集接口和视觉候选开发；当前 AX 前置检查失败。Windows 交互截图暂不能验收时，先完成 Mac 窗口图像/身份/坐标合约的 Runtime 接入。CUA 锁定错误不作为全部 Mac 开发停止的条件；后续动作仍按各平台实际能力独立验收。

## Mac Runtime 进展（同日）

[Mac Runtime 报告](P7-MACOS-VISUAL.md)：截图已接入包/CLI，Vision OCR 与候选定位正常流程 3/3、拒绝用例 8/8。有界输入代码已实现并实测派发前拒绝；P7.3 真实点击/输入与 P7.2 自动 Agent 降级仍待验收/接入。两端隔离回归各 355/355。

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

P7.1 implementation has started after Windows P6 acceptance. Capture and the fixture are implemented; native pixel acceptance awaits an interactive desktop. See the [capture report](P7-CAPTURE.md). The first implementation is scoped native-window capture and a custom-drawn fixture, followed by OCR/visual candidates, bounded coordinate actions, post-action verification and reliability controls. Captures carry the authorized PID/HWND, time, dimensions, DPI mapping and content hash.

Visual fallback is allowed when accessibility cannot expose a target or action. Unknown dispatch completion stops execution; it cannot trigger a second coordinate action. Ambiguity needs fresh distinguishing evidence. Window changes invalidate the previous capture. Coordinate operations retain the semantic intent, screenshot region and receipt, with fresh verification before replay.

Acceptance covers a real click/type visual task, unchanged P6 native workflows and explicit fault cases. Regression reports separate native, deterministic, Jev/Planner and visual paths, with intermediate checks and independently verified deliverables. Mac AX fixture acceptance passes as recorded in the [Mac follow-up](MACOS-FOLLOWUP.md). The [Office CUA pilot](MACOS-OFFICE-REPORT.md) identifies editor metadata, cell readback, scoped traversal and unknown-dispatch gaps; it does not implement Bokkio fallback. Mac capture/visual acceptance, Windows Office activation and upstream benchmark integration remain pending.

## 当前退出条件与 Office 入口

P7 尚未整体完成。首先恢复实际输入条件并运行固定的三道 Office 原题，保留每题失败与独立产物结果；再修复 Office 覆盖和自动视觉降级。原始VLM评分、跨应用长流程和完整上游环境仍待完成，见 [Office准备报告](OFFICE-PILOT-READINESS.md) 与 [Pending](PENDING.md)。

P7 remains incomplete. Mac capture/OCR is verified, but positive input, automatic fallback, Windows live vision and full reliability remain pending. The fixed Office pilot is blocked before execution; run it after input is available, then repair coverage and align judging/upstream environments.
