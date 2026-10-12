# 总体进度 / Overall status

**当前主线入口：** [跨环境共享进度](progress/README.md)。新 Runtime 的完成度、待办和两端接续以该目录为准；下面旧 P0–P7/Office 内容保留为历史。

2026-10-12 当前主线：主机回归 571/571；三开发调用方已有固定流程验收。自主业务首轮及复测已执行，共 46 个用例结果、26 个业务启动；四个重点任务最新 9/12，本轮窗口／作业故障矩阵 16/18，审计 9/9，见[执行报告](evidence/2026-10-12-business-eval/README.md)与[共享状态](progress/STATUS.md)。以下旧阶段数字保留为历史。

## 新主线：三天 Computer Use Runtime

2026-10-11 已按新定位实施工作候选版 `0.2.0`：统一 Runtime、MCP/CLI/Python SDK、生成代码作业、Browser、SQLite 操作/审批追溯、查询统计与导出。Mac 原生字段、无 OCR 图标点击、代码驱动原生动作/CSV、系统 Calculator 各有 3/3 记录；官方 MCP/CLI/SDK 连通通过。整体计划仍待 Windows 实机和客户业务样本验收；详见 [Runtime 交付状态](RUNTIME-DELIVERY.md) 和 [指南](RUNTIME-GUIDE.md)。下面是旧 P0–P7 路线的历史状态，Office 连续三轮不再是新主线的前置条件。

更新：2026-10-11。**P6 Windows 原生验收完成，P7 部分实现；完整 Office 开发轮 r28、r30 各通过 3/3；最新完成轮 r33 为 0/3，连续三轮 3/3 尚未达到。按用户要求提交当前快照，实机验收暂停。**

## 阶段位置

| 阶段 | 当前交付与验收 |
|---|---|
| P0–P3：环境、元素模型、原生 Runtime | Windows/macOS 基础开发验收完成；应用覆盖和稳定性继续扩展 |
| P4：Jev 局部决策 | 真实模型、难例与大树开发样本已有验收；通用应用覆盖待扩展 |
| P5：规划与跨应用执行 | Windows 阶段恢复、文件交付与需求修订通过；Mac Office 单轮三题通过，连续稳定验收待完成 |
| P6：Recorder / Workflow | Windows 原计划验收完成；Mac 基础重放通过，文件合约与跨进程扩展待完成 |
| P7.1：截图与坐标 | Mac 包/CLI 与原生图像验收通过；Windows 接口与 fixture 已实现，实机像素验收待完成 |
| P7.2：OCR / 视觉候选 | Mac 公共 OCR、授权窗口 Agent/Jev/CLI 降级已接入；只读观察/决策 3/3，视觉 Workflow 待实现 |
| P7.3：有界输入 | 最新 Mac 自绘新进程固定子任务输入 3/3，各两次尝试；Excel 在开发轮重复通过；Word r26 全任务已通过，PPT r14 已通过 |
| P7.4–P7.5：可靠性与持续回归 | 覆盖部分取消、身份、时效与未知完成只读核对；完整故障恢复及连续三轮验收未完成 |

单元测试、固定子任务 fixture、脚本探针和完整 Agent 任务分别报告，不换算成通用 Computer Use 成功率。

## 最新结果

- 主机隔离回归 **519/519**；Swift capture helper 编译通过。Windows 保留历史 **373/373**，按用户要求暂缓。
- 自绘 Mac 输入：三个新进程，固定 Planner 子任务、真实 Jev/Agent，独立业务 JSON **3/3**；每次恰好点击一次并输入正确 CODE。它不代表通用 Planner 的实机验收。
- 断电后 Office r7–r12 各 **1/3**，均只有 Excel 完整任务通过。r12 Word 8 次尝试在正文选区衔接处失败；PPT 3 次尝试成功输入标题，Save As 尚未完成。各轮代码不同，属于开发诊断。
- r14 完整轮 **2/3**：Excel 3 次尝试、PPT 6 次尝试，全部独立文件检查通过。该轮 Word 在空正文选区计划处停下；后续 r26 已完整通过。
- Word 独立 GUI 探针保存后通过内容、Heading 1、正文 Calibri 11pt 和 1.15 行距全部检查；PPT 独立探针也通过标题页和保存检查。两者均不计入完整 Agent 成绩。
- 当前 Mac 已解锁。断电后的输入 r9 在三个新进程通过 3/3，各两次尝试，独立业务状态正确；不是通用 Planner 验收。
- 阶段重规划保留待办子任务；拒绝空选区 Word 格式化与静态菜单成功条件，修复 Save/Save As 前缀匹配。最新完整 Office 轮 r33 已结束；当前暂停实机验收以提交快照。
- 原始 VLM judge 未运行，没有官方榜单成绩；现有 GPT-4.1 Planner + Jev 不调用 Astra，截图本机 OCR，业务模型仍有文字 token 费用。

最新证据：[输入与 Office 进展](evidence/2026-10-10-office-progress/README.md)。历史诊断：[Office 十轮实跑](evidence/2026-10-08-office-live/README.md)、[公共视觉接入](evidence/2026-10-09-visual-bridge/README.md)、[前次锁屏尝试](evidence/2026-10-09-office-rerun/README.md)。

## 下一步顺序

1. 最新真实自绘输入 fixture 已通过；继续只清理明确属于测试的旧文档。
2. 验证 Word 正文字体/字号/1.15 行距、标题样式及保存；完成 PPT 标题页输入和 Save As 全任务。
3. 使用新隔离输入串行执行固定三题，每题保持 15 次动作尝试；达到连续三轮 3/3。
4. 随后扩展故障恢复、视觉 Workflow、跨应用职业办公流程、原始 VLM 评分和性能优化。Windows 继续暂缓。

详细缺口见 [Pending](PENDING.md)，公共接口见 [P7](P7-VISUAL-BRIDGE.md)。

## English

Windows P6 is accepted; P7 remains partial. Host regression passes 519 tests. The current native helper passed real click/type in three fresh painted Mac processes with fixed Planner contracts and independent business checks, two attempts each. Full Office development rounds r28 and r30 each passed 3/3. The latest completed round r33 passed 0/3; three consecutive 3/3 rounds remain pending. Live acceptance is paused for the requested code snapshot. Scripted Word/PPT probes are separate from full Agent scores.

The Mac is unlocked. Continue fresh serial Office rounds under the original 15-attempt budget until three consecutive 3/3 rounds pass, then expand fault recovery and performance work. No Astra call, screenshot upload to business models or official VLM score is claimed. Windows stays paused.
