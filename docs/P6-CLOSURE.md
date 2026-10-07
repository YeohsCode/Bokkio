# P6 验收闭合 / P6 acceptance

日期：2026-10-05。平台：Fusion Windows 11 IoT LTSC ARM64，x64 Python 3.12.13。重放使用原生 UIA；没有浏览器或 DOM 控制。

## 扩展原生验收

`scripts/verify_p6_complete.py` 的 closure v3 使用一份不变的七步 Workflow：Explorer 选源文件 → Notepad 写入、菜单保存 → Explorer 选报告。每组在独立 Python 进程中重放，绑定新应用进程和自有 Explorer 窗口。

| 验收 | 结果 | 独立证据 |
|---|---|---|
| 原生客户端回执接入 | 2/2 | Explorer 源文件/报告选择；捕获不二次派发 |
| 同一 v2 模板，三组参数 | 3/3；每组 7 次派发 | 16、21、28 字节交付物；SHA-256、源文件保持、Explorer 选择和新 Notepad 进程重开均通过 |
| 独立执行进程退出＋Notepad 重启后恢复 | 1/1 | 前 6 步已保存，重新绑定不同 PID 后仅派发最后 1 步；17 字节报告保持，重开通过 |
| UI 增加无名容器 | 1/1 | 实际 WinForms 结构变化，解析路径为 `named_context` |
| 真实模型修复 | 1/1 | 原失败版本 0 派发；GPT-4.1 选择原生 Search，父版本哈希保留，新版本确定性重放通过 |
| 观察遍历优化 | 隔离计数验收通过 | 常规动作从 4 次树遍历减为 3 次；快照变化仍阻止派发，验证等待仍读取新树 |
| 隔离回归 | 主机 292/292；Windows 292/292 | 包括改动输入/交付物、检查点篡改、未知完成、歧义与应用范围拒绝 |

closure v1 在基线模板校验中失败：用于校验 path 参数的样例未使用 Windows 绝对路径；基线准备中已有一次源文件选择调用，但该次回执未独立归档；参数化正式用例未开始。v2 完成两次基线回执和 Notepad 保存；第一组参数用例因目录父节点未参数化而在 s1 零派发停止，剩余组未开始。修正后 v3 执行上述全部扩展项；前两轮保留，未合并为最终成功分母。

## 原始 P6 标准

原有六步 focus/type/click/expand/select＋跨应用写入、成功 Notepad trace 固化、结构化失败和修复由 `scripts/verify_p6_windows.py` 复核。v4 为历史首版代码的 3/3 录制重放和 3/3 trace 重放；本轮 v5 使用与 closure v3 相同的八个 Runtime/Planner 源码哈希，结果另行保存。

最终 v5：六步录制 JSON 重放 **3/3**（每轮六次派发、六次上下文恢复及三项独立业务检查），真实五步 Notepad trace 重放 **3/3**（每轮 16 字节及 SHA-256 一致，新进程重开通过）。错误 selector 零派发；保留父版本的 revision 2 修复重放通过。

原计划六项验收均已满足：三次不改 JSON 重放、Windows 同状态原生运行、小幅结构变化恢复/结构化失败、成功 trace 固化、真实模型修复保留旧版本，以及逐步观察/动作/解析/验证日志。**P6 完成，P7 可开始。** [证据索引](evidence/2026-10-05-p6-closure/README.md) 保存各轮分母、执行源码哈希、输入 trace、产物、检查点和失败版本；最终八个共用模块源码哈希与 2026-10-05 的验收代码一致。2026-10-06 的 Mac table_row 能力修正和对照结果另见 [Mac 续测](MACOS-FOLLOWUP.md)。

## P7 入口与保留项

原始 P6 标准接受 **macOS 或 Windows** 的重放验收。本轮采用 Windows。macOS AX provider 对照、暂缓的 Office 激活、全局人工键鼠监听和完整上游 benchmark runner 继续列为平台/扩展待办；原生客户端回执和成功 Agent trace 已提供两种可用录制来源。

[P7 计划](P7-PLAN.md) 以 Windows 原生窗口截图和自绘 fixture 开始，随后实现 OCR/视觉候选、坐标动作和可靠性回归。已有原生确定性路径、版本、暂停/恢复、失败审计及独立文件验收可供接入。

本报告为开发环境验收；保留原 WAA 评分，不提供官方 leaderboard 分数，也不宣称 macOS 或已激活 Office 流程通过。

## English

The expanded P6 acceptance passed in the Windows VM. One unchanged seven-step Explorer → Notepad → Explorer template passed three parameter cases, including independent byte/hash, preserved-source, selected-file and fresh-process reopen checks. Restart/resume passed with only the remaining action dispatched. Two native-client receipts were captured without repeating their actions. An actual unnamed-wrapper variation used named-context fallback. A real GPT-4.1 selector repair preserved the original version; its failed predecessor dispatched zero actions and the repaired deterministic replay passed.

Host and Windows each pass 292 isolated tests. Earlier closure v1/v2 failures remain separate. Final core v5 passed 3/3 unchanged six-action recording replays and 3/3 real Notepad trace save/reopen replays. Its zero-dispatch failure and parent-linked repair also passed. All six original acceptance criteria are met on Windows, and the final executed shared source hashes match the 2026-10-05 acceptance implementation. The subsequent Mac table-row fix and acceptance are documented in the [Mac report](MACOS-FOLLOWUP.md). The scope accepts one supported desktop platform. macOS provider checks, Office activation, global human input capture and full benchmark integration remain visible follow-up items. P6 is complete and P7 can start; its first task is native-window capture and a custom-drawn visual fixture.
