# Mac Office 实跑证据 / Live Office evidence

记录日期：2026-10-08–09。三道固定 WindowsWorld L1 原题，每题 15 次动作尝试。十轮实际启动 30 次任务，各轮独立产物评分均 **0/3**。这是 Mac adapted 开发诊断，没有官方成绩。

## 文件索引

- [summary.json](summary.json)：各轮启动/评分、第三轮并发标记及整理时工作树源码哈希；这些哈希不表示所有历史轮次使用同一版本。
- round-1 至 round-10 的 run.json：环境、应用版本、执行状态、独立 OOXML 检查及保存时效。
- 各轮 execution-summary.json：停止原因、动作回执摘要、原始私有 trace 的 SHA-256。actions 是动作尝试次数，可包含派发前失败；action_receipts 是返回的动作记录，两者可能不同。
- [最新运行](round-10/run.json)、[最新动作摘要](round-10/execution-summary.json)。报告 completed 仅表示执行循环返回；三题 Agent 均 blocked，passed=false。
- [scripted-transport-probe.json](scripted-transport-probe.json)：较早 OCR 字段定位版本的独立 Excel 脚本探针，两次替换各 8 个事件，保存文件的数据保持和货币格式通过。agent_score=false；它不能证明最新原生边界定位路径通过。
- [native-controls.json](native-controls.json)：自有 fixture 三轮原生动作与 12 次滚动检查。
- [post-r8-session.json](post-r8-session.json)：第八轮后观察到的历史锁屏状态；第十轮启动检查显示未锁屏。
- [validation.json](validation.json)：本轮 403 项主机回归及证据范围；Windows 373 项为历史结果。
- [SHA256SUMS](SHA256SUMS)：本目录除清单自身以外全部文件的 SHA-256。

## 最新失败与修复范围

| 第十轮任务 | 动作尝试 | 停止原因 | 最终产物 |
|---|---:|---|---|
| Word win_adm_l1_003 | 4 | 输入派发后确认未知，停止并要求检查当前状态 | 内容保持；标题/正文格式失败，未验证新保存 |
| Excel win_acc_l1_001 | 2 | input_unavailable，在输入前拒绝 | 数据保持；货币格式失败，未验证新保存 |
| PowerPoint win_pro_l1_003 | 0 | 决策置信度不足 | 目标文件不存在 |

AXConfirm 派发、只读选区、跨窗口身份、真实前台激活、草稿值确认和弹窗阶段规划已有修复。最新失败仍需诊断，不能仅凭单元测试宣布 Office 全任务成功。第三轮存在并发 fixture 干扰；各轮代码也有变化，不能汇总为固定版本的 benchmark 成功率。

公共目录仅保存合成任务结果、校验值及裁剪后的动作摘要；原始桌面截图、完整 UI 树、模型配置和实际 Office 文件留在本地临时工作区。下一步见 [Pending](../../PENDING.md)。

## English

Ten development rounds started all three tasks (30 executions), each scoring 0/3 on independent artifacts. Round 3 had concurrent fixture activity and code changed across rounds. Latest blockers: Word post-input verification, Excel pre-input foreground/window rejection, and PowerPoint decision confidence. The unlocked-session preflight passed on round 10.

The earlier scripted Excel probe passed two replacements and saved-artifact checks using OCR field targeting. It is separate from Agent scoring and does not validate the latest native-bounds route. Host regression passes 403 tests; Windows remains at its historical 373. No original VLM or official benchmark score is reported. Public evidence excludes raw desktop images, UI inventories and credentials.
