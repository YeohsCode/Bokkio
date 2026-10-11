# 当前待办 / Pending work

更新：2026-10-11。**P6 Windows 已验收，P7 部分实现；完整 Office 开发轮 r28、r30 各通过 3/3；最新完成轮 r33 为 0/3，连续三轮 3/3 尚未达到。按用户要求提交当前快照，实机验收暂停。**

## 优先执行

| 顺序 | 待办 | 完成条件 / 当前缺口 |
|---|---|---|
| 1 | 最新实机输入回归 | 最新助手已在三个新进程通过 3/3，各两次尝试；保持身份、焦点、时效和零重复输入守卫 |
| 2 | Word 完整格式与保存 | 验证 Heading 1、正文 Calibri 11pt、1.15 行距及内容保持。独立 GUI 探针及 r26 完整 Agent 全部检查通过；选区、阶段衔接和明确命令意图仍需稳定验收 |
| 3 | PPT 完整 Agent 任务 | 标题页、Alpha Initiative、Save As 独立文件检查。脚本/固定标题子任务探针产物通过，不算全任务；完整 Agent 已成功输入标题，r14 用六次尝试完成全部保存/标题/布局检查，仍需连续稳定验收 |
| 4 | 固定三题稳定验收 | 新隔离输入、串行执行、每题 15 次动作尝试，连续三轮 3/3。Excel 在多个完整开发轮通过；各轮代码不同，不能视作稳定验收 |
| 5 | 故障恢复与优化 | 真实取消、权限/窗口/进程变化、未知完成、保存后重开；三题通过后再扩展职业办公流程和性能优化 |

现有 GPT-4.1 Planner + Jev；不新增 Astra 依赖。截图本机 OCR，业务模型接收文字/候选并计文字 token。未知完成仅只读核对：成功条件由假变真才继续，不重发；已有静态条件不能证明命令。主机 **519/519**，Windows 历史 **373/373**。见[本次证据](evidence/2026-10-10-office-progress/README.md)。

## 平台与可靠性

| 项目 | 仍需完成 |
|---|---|
| Windows P7（暂缓） | 实机截图像素、移动/DPI、窗口故障验收；原生 OCR/视觉输入和跨应用验证 |
| Mac 捕获与输入 | 多显示器/比例、窗口竞争、OCR 行合并、真实办公覆盖；最新字段 transport/编辑完成正向实机验收 |
| Mac Workflow | 视觉动作录制重放、文件/参数合约、保存后新进程重开、不同 PID/执行进程恢复及真实模型修复 |
| P7.4–P7.5 | 完整取消、限速、崩溃与未知完成恢复；权限缺失、图像过期、窗口关闭/移动、无响应；分别统计 native/visual/Workflow/Agent |
| 大树与虚拟化 | 更多独立应用和真实 Windows VirtualizedItem provider；分页 fixture 不等于完整虚拟化验收 |
| Office 其他原生覆盖 | Outlook 深度遍历、Excel 单元格观察、Word/PPT 编辑区与对话框；已有 CUA 流程不计作 Bokkio Agent 成功 |

## Benchmark、暂缓与可选项

- **原始 VLM 评分**：已保留原始 prompt/model/checks；实际执行需要独立 `QWEN_API_KEY`。当前只读 OOXML 是 Mac 适配评分。
- **上游环境对齐**：WindowsWorld/WAA VM、HTTP/server runner、初始化与 evaluator；Mac adapted run 不是官方成绩。
- **职业办公长流程**：图表、需求变更、邮件草稿、文件交付、暂停/进程恢复及三轮独立验收；真实邮件发送需用户指示。
- **Windows Office 暂缓**：许可证、激活、Outlook 设置及完整 UIA 办公流程。
- **可选录制**：全局人工键鼠监听；P6 已有原生回执及成功 trace 录制来源。

历史：[十轮失败与恢复](evidence/2026-10-08-office-live/README.md)、[前次锁屏重跑](evidence/2026-10-09-office-rerun/README.md)。本次代码与证据按用户要求一起提交。

## English

Latest input helper passed 3/3 in fresh processes. Full Office development rounds r28 and r30 each passed 3/3. The latest completed round r33 passed 0/3; three consecutive 3/3 rounds remain pending. Live acceptance is paused for the requested code snapshot. Continue fresh serial Office rounds under 15 attempts per task when resumed. Host tests: 519; historical Windows tests: 373. Windows remains paused.
