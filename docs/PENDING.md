# 当前待办 / Pending work

更新：2026-10-09。**P6 Windows 验收完成，P7 部分实现；Office 原题已执行，最新独立评分 0/3。** 阶段与实际分母见 [总体进度](STATUS.md)。

## 优先执行

| 顺序 | 待办 | 完成条件 / 当前缺口 |
|---|---|---|
| 1 | Word 输入后确认 | 保存并独立验证标题、字体/字号、行距及内容保持；最新派发后的字段确认未知，需先检查实际状态，不能盲目重试 |
| 2 | Excel 字段输入与前台范围 | 定位 `input_unavailable` 的具体窗口/前台原因，验证最新原生边界定位、D 列范围、Currency 和保存；旧 OCR 脚本探针通过不等于当前 Agent 路径通过 |
| 3 | PowerPoint 规划与动作覆盖 | 补齐标题页/文本/保存候选与弹窗成功条件；最新置信度不足，保留当前阈值和 15 步预算 |
| 4 | 完整复跑固定三题 | 使用新隔离工作区，逐步记录动作、最终产物和失败；已有十轮各 0/3，第三轮并发干扰单独标注 |
| 5 | 通用 P7 视觉降级与重放 | Office runner 已限定接入 writable combo；仍需通用 Planner/Jev/Workflow、视觉步骤重放及完整正向/故障验收 |

## 平台与可靠性

| 项目 | 仍需完成 |
|---|---|
| Windows P7 | 实机截图像素、移动/DPI、窗口故障验收；原生 OCR/候选与视觉输入实现和跨应用验证 |
| Mac 捕获与输入 | 多显示器/比例、窗口竞争、OCR 行合并、真实办公覆盖；最新字段 transport 正向验收与确认失败诊断 |
| Mac Workflow | 文件/参数合约、保存后新进程重开、不同 PID/执行进程恢复及真实模型修复 |
| P7.4–P7.5 | 完整取消、限速、崩溃与未知完成恢复；权限缺失、图像过期、窗口关闭/移动、无响应等故障；分别统计 native / visual / Workflow / Agent |
| 大树与虚拟化 | 更多独立应用和真实 Windows VirtualizedItem provider；分页 fixture 不能替代完整虚拟化验收 |
| Office 其他原生覆盖 | Outlook 深度遍历、Excel 单元格观察、Word/PPT 编辑区与对话框；已有 CUA 流程不计作 Bokkio Agent 成功 |

## Benchmark、暂缓与可选项

- **原始 VLM 评分**：入口已保留原始 prompt/model/checks；实际调用及截图轨迹待完成，需要独立 `QWEN_API_KEY`。OOXML 评分可独立运行。
- **上游环境对齐**：WindowsWorld / WAA VM、HTTP/server runner、初始化与 evaluator；Mac adapted run 不作为官方成绩。
- **职业办公长流程**：图表、需求变更、邮件草稿、文件交付、暂停/进程恢复及三轮独立状态验收；真实邮件发送需用户指示。
- **Windows Office 暂缓**：许可证、激活与 Outlook 设置及完整 UIA 办公流程。
- **可选录制**：全局人工键鼠监听；P6 已有原生回执及成功 trace 录制来源。

## 本轮收尾

构造接口、AXConfirm、窗口身份/激活、只读选区与阶段规划修复已加入代码；十轮失败、Excel 脚本探针和恢复证据已整理。主机回归 **403/403**；Windows 历史 **373/373**。本轮测试和文档形成独立提交。

## English

P6 Windows acceptance is complete; P7 is partial. The Office pilot has executed ten diagnostic rounds, each scoring 0/3. Priorities are Word verification after posted input, Excel pre-input foreground/window refusal, PowerPoint planning/action coverage, and a fresh full pilot rerun. The earlier scripted Excel success is separate from Agent results and the latest native-bounds route.

Remaining work includes general visual fallback and Workflow replay, Windows live capture/OCR/input, wider Mac input and file/process workflows, reliability, real virtualized providers, VLM judging and upstream environment integration. Windows Office activation stays paused. Current host regression is 403/403; the historical Windows result is 373/373. Evidence: [live report](evidence/2026-10-08-office-live/README.md).
