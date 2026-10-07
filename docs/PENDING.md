# 当前待办 / Pending work

更新：2026-10-07。P6 的 Windows 原始验收已经完成；P7 可以开始。Mac 原生读取现已恢复，见 [Mac 续测](MACOS-FOLLOWUP.md)；四款微软 Office 应用已完成一轮 CUA 交互及文件验收，见 [Office 报告](MACOS-OFFICE-REPORT.md)。

| 优先级 | 项目 | 仍需完成的内容 |
|---|---|---|
| 当前 | Mac 平台补测 | 补充独立应用、可见节点虚拟化、大树和更多结构变化；将已有自有 Cocoa 跨应用验收扩展到文件交付与真实办公应用 |
| 当前 | Mac Workflow 扩展对照 | 参数化输入、输入/产物哈希合约、文件保存后新进程重开、跨执行进程/PID 恢复，以及真实模型修复；Windows 已通过的结果不能直接算作 Mac 通过 |
| 下一阶段 | P7 视觉兜底 | 原生窗口截图、窗口范围/DPI/坐标映射、自绘 fixture、OCR/视觉候选、有界 click/type、操作后验证 |
| 下一阶段 | P7 可靠性与跨平台回归 | 视觉路径的取消/限速/确认/未知完成处理；权限缺失、截图过期、窗口消失/移动、应用无响应等故障验收；按路径统计完整任务结果 |
| 持续 | 大树与虚拟化覆盖 | 更多独立应用；真正的 Windows VirtualizedItem provider，区分原生虚拟化与已通过的每页 25 条分页 fixture；细分检查点写入耗时 |
| 持续 | 开源 benchmark 完整接入 | 完整上游 runner、HTTP/VM 环境服务和固定 evaluator 对齐；扩展长流程及 OSWorld 设计参考任务，保留中间与最终检查；现有 WAA 为开发环境适配结果 |
| 当前 | Mac Microsoft Office / Outlook | CUA 计算、报告/摘要、草稿附件、修订及文档重开通过；补齐 Bokkio disabled 编辑区、Excel 单元格观察、Outlook 窗口遍历及未知派发处理，再做 Agent/Workflow、图表和阶段/进程恢复与三轮独立验收 |
| 暂缓 | Windows Microsoft Office / Outlook | Windows 可用许可证、激活与邮箱设置；UIA 操作能力矩阵及完整三项职业办公参考任务、需求变更、阶段恢复 |
| 可选 | 全局人工录制 | 系统级键鼠监听、语义动作归因；现有原生客户端回执和成功 Agent trace 已满足 P6 的录制来源要求 |
| 本次交付 | Commit / push | 本次提交包含 P5/P6、Mac 续测和 Office 证据；主机回归与隐私扫描已通过，按授权推送 |

## 已完成的基础

- Windows P6：录制重放 3/3、成功 trace 保存/重开 3/3、同一七步模板三组参数 3/3、重启恢复、结构变化恢复及真实模型修复。
- Windows 的 native-first Runtime、Planner/Jev、阶段状态、输入/产物版本与独立验收已有证据。
- Mac 本轮已恢复 AX 读取，并开始完成原生动作、双轴滚动、模型跨应用和确定性重放对照。确切分母及失败记录见 [续测报告](MACOS-FOLLOWUP.md)。

## English

Windows P6 acceptance is complete and P7 is ready. Mac AX fixture results and the Office CUA pilot are recorded separately. Remaining work includes broader Mac application/virtualization coverage, file-contract and process-recovery checks, Bokkio Office editor/cell/window integration, full repeated Office workflows, scoped capture/OCR/visual actions and reliability, real virtualized providers, upstream benchmark integration, paused Windows Office setup and optional global input recording. This delivery includes P5/P6 and Mac evidence after passing host tests and privacy checks. Windows acceptance does not substitute for Mac acceptance.
