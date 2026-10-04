# P5 Windows 办公流程前置实测

日期：2026-10-03。当前仍处于 P5 验收与稳定性补齐阶段。后续已完成七款 Office 应用安装与启动读取，激活和邮箱设置待完成，见 [安装记录](WINDOWS-OFFICE-SETUP.md)。

## 本轮结果

| 检查 | 结果 | 范围 |
| --- | --- | --- |
| 应用安装核对 | Office、LibreOffice、Thunderbird 未安装；Notepad、Explorer 可用 | 固定安装路径与卸载注册表；尚未形成 Office UIA 矩阵 |
| 已完成中间阶段后的暂停恢复 | 1/1 通过；3 动作，0 重规划，48.552 秒 | 真实 GLM Planner / Jev / 原生 UIA；Search 连续写入三个不同值，第二阶段完成后暂停，恢复只写第三个值 |
| 原生文件菜单、保存与重开 | 三轮 3/3 通过；每轮 9 动作，约 9.5–9.7 秒 | 确定性 UIA 能力验证，未使用 Planner/Jev；每轮启动新 Notepad、Save As 保存独立文件、另一个新进程通过 Open 对话框重开 |
| 隔离回归测试 | macOS 和 Windows 各 114 项通过 | 新增重复写入、重规划 ID 复用、最终状态重新观察三项回归 |

文件的正文由 UIA 写入，文件由 Notepad 保存。验证器只读磁盘内容及哈希，并独立检查重开后的原生文本值。Open 对话框的下拉按钮也叫 Open，因此将执行目标绑定到对话框的直接子按钮，避免同名误选。

上述结果是开发验证。三条完整办公参考任务尚未运行，不是 WindowsWorld 或 WindowsAgentArena 官方成绩。

## 恢复修复

此前恢复会重新检查已经完成的中间步骤。如果后续步骤覆盖了同一状态，恢复可能再次执行早期写入。

现在成功后的新观察立即生成完整子任务完成记录。恢复用完整定义匹配历史记录，保留已完成的中间步骤；仅凭相同 ID 不会跳过不同工作。最后一步仍需观察当前状态。记录中明确区分历史完成证据与当前观察。

这一修复尚未实现业务事实来源、输入版本变化检测、文件依赖或产物版本失效传播。旧检查点若仅存部分子任务定义，会继续检查当前状态，不会自动取得新记录的保留语义。不能据此认定完整办公产物始终有效。

## Windows 会话

本轮开始时 Windows 没有已登录用户，VMware 拒绝交互启动。通过仅绑定 Mac 本机回环地址、使用私有认证密码的虚机控制台，用已有测试账号自动登录后，实测得以继续。控制台设置与账号凭据留在 Mac 私有目录，不进入仓库；控制台通道用于测试环境准备，测试动作仍通过 UIA。

## 下一批工作

1. 使用微软桌面 Word、Excel、PowerPoint 与 Outlook，记录许可、版本、语言和 UIA 能力。用户明确要求匹配客户应用，后续不使用替代办公套件。
2. 实施 OFFICE-01：表格汇总、报告、Explorer 文件整理与邮件草稿；同时加入中间业务检查和最终文件重开检查。
3. 扩展 OFFICE-02、OFFICE-03，加入事实来源、约束、产物版本、需求更新和失效部分的恢复；每项先完成独立验收，再做三轮重跑。
4. 完成 Windows P5 验收后适配官方初始化与 evaluator，运行预先固定的原生任务子集，并进入 P6 Recorder / Workflow 重放。视觉覆盖在 P7 扩展。

## 复现

已登录测试账号后，在 guest 仓库执行：

```powershell
.venv\Scripts\python.exe scripts\verify_p5_stage_resume.py --fixture fixtures\windows-interactions\bin\Release\net8.0-windows\bokkio-interactions-fixture.exe --output C:\BokkioTasks\stage-resume
.venv\Scripts\python.exe scripts\verify_windows_file_roundtrip.py --output C:\BokkioTasks\file-roundtrip
```

脚本只关闭自己创建的进程。文件验证每次创建独立目录，保留完整动作、原生观察、最终文件与摘要。

证据：[本轮证据目录](evidence/2026-10-03-p5-office-prerequisites/README.md)。

## English summary

P5 remains in Windows acceptance and stability work. The initial inventory had no Office suite or mail client. Seven Office apps were subsequently installed and passed native startup reads; see the [installation report](WINDOWS-OFFICE-SETUP.md). A real Planner/Jev/UIA test paused after two verified intermediate writes and resumed with only the remaining write: three actions, zero replans. Three independent deterministic UIA runs saved files through Notepad menus and dialogs, reopened them in new processes, and checked native content plus persisted bytes. These are development checks, not official benchmark results.

New completion receipts match the full subtask definition, retaining historical intermediate work while freshly observing the final step. Input changes, artifact dependencies and version invalidation remain pending. Both host and guest passed 114 isolated tests. Next: prepare the office applications, execute the three office workflows, complete P5 acceptance, then integrate official evaluation and build P6 recording/replay.
