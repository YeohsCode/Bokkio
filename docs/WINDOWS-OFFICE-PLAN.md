# Windows 职业办公跨应用流程

2026-10-04 更新：按用户要求暂缓激活与 Office 办公实测，先运行 Explorer/Notepad 外部多步任务，见 [WAA 实测](P5-WAA-LONGCHAIN.md)。已安装的微软应用保留。

Update: Office activation and workflow tests are paused at the user's request. Native Explorer/Notepad benchmark development runs continue; see the [WAA report](P5-WAA-LONGCHAIN.md).

日期：2026-10-03。状态：**Office 七款应用已安装并通过启动读取；激活、邮件设置与完整办公流程待完成**。

## 目标与参考

按用户要求，Windows 继续以原生 Computer Use 为主，加入 Word、Excel、PowerPoint、邮件客户端与 File Explorer 组成的职业办公流程。参考 WindowsWorld 的跨应用任务与中间进度/最终完成评测；参考 OSWorld 2 系列的长流程、动态需求和状态维护设计。[WindowsWorld](https://github.com/HITsz-TMG/WindowsWorld)、[OSWorld 2](https://osworld-v2.xlang.ai/)。

WindowsWorld 提供中间与最终指标，评测使用 VLM judge；其标准动作设置包括 PyAutoGUI/computer_13。Bokkio 先实施自己的 UIA 开发任务与独立验收，正式接入时核对任务版本、环境和允许的动作接口。[WindowsWorld 论文](https://arxiv.org/html/2604.27776v1)。

以下三条是 Bokkio 设计的参考任务，尚未执行，不属于已导入或已通过的官方 WindowsWorld 题目。

## 首批三条任务

| ID | 职业流程 | 原生应用与操作 | 关键中间验收 | 最终验收 |
| --- | --- | --- | --- | --- |
| OFFICE-01 | 周报与资料交付 | Excel 筛选并汇总订单；Word 编写周报；Explorer 整理文件；邮件客户端保存交付草稿 | 输入版本正确；筛选、数量与总额正确；报告数字一致；文件已保存；草稿附件正确 | 重新打开工作簿与报告，内容一致；指定目录与文件名正确；草稿保留正确主题、正文和附件 |
| OFFICE-02 | 会议汇报准备 | Excel 整理部门指标；PowerPoint 制作摘要与图表页；Explorer 整理输出；邮件客户端保存会议草稿 | 统计范围正确；幻灯片标题、表格/图表数据一致；演示稿已保存；附件对应最终版本 | 重新打开演示稿，页数和关键指标正确；交付目录完整；草稿引用最终演示稿 |
| OFFICE-03 | 需求变更与修订 | 读取邮件中的修订要求；更新 Excel 数据；更新 Word 报告与 PowerPoint 摘要；Explorer 管理新版产物 | 新要求已读取并记录；受影响数据重算；报告与演示稿同步；草稿附件更新 | 所有交付物符合最新要求，无重复条目；重新打开后数值、版本与附件一致 |

邮件流程的终点为保存草稿。实际发送作为单独动作，需用户明确指示；本计划不授权发送真实邮件。

## 应用与测试数据准备

- 核对虚机中 Word、Excel、PowerPoint、邮件客户端和 Explorer 的安装、版本、语言、许可与 UIA 支持，记录能力矩阵。先前安装核对显示办公应用未安装；后续已安装 Microsoft 365 七款应用并通过启动读取，许可证匹配、激活与 Outlook 设置待完成，见 [安装记录](WINDOWS-OFFICE-SETUP.md)。Notepad 的原生菜单保存、文件校验与新进程重开三轮通过，真实 Planner/Jev 完成阶段后的暂停恢复通过。Office 操作能力矩阵仍待扩展，见 [前置实测](P5-OFFICE-PREREQUISITES.md)。
- 用户明确要求使用客户实际采用的微软桌面 Office：Word、Excel、PowerPoint、Outlook 与 File Explorer。后续办公流程不采用替代套件；激活前继续准备 UIA 检查和独立验收，编辑能力以激活后实测为准。
- 每轮使用专用目录、合成订单与测试身份，保存初始状态和输入版本；不用用户已有业务文档。
- 初始化工具可以准备输入文件。被测 Agent 通过 UIA 读取和操作应用，产物由应用保存；独立 evaluator 可以只读检查保存文件。
- 开始前固定任务目标、验收项、输入及参考答案版本。模型可见目标和实际界面；独立评分答案与 evaluator 配置不进入规划器上下文。

## 中间步骤与最终完成

每个验收项记录：`id`、业务描述、依赖、证据来源、检查结果、输入版本、产物版本、时间和失败原因。

1. **中间验收**：完成关键业务状态后检查，例如已选对订单范围、总额已更新、报告已保存。检查来源优先为新 UIA 观察与只读文件校验。
2. **最终验收**：单独重新打开产物，检查持久化内容、跨文件一致性、保存位置及草稿附件。中间进度高不能自动判为最终成功。
3. **证据分工**：动作日志说明执行了什么；原生状态与产物说明结果是什么。不能仅凭点击成功或模型总结判为通过。
4. **评分记录**：报告中间通过项/适用项、最终通过与否、动作数、重规划数、人工介入、端到端耗时及模型成本。失败、阻断和未覆盖均保留。

视觉布局检查需要时单独记录方法与不确定性；待 P7 增加视觉能力后扩展，不将无法检查的布局自动判为通过。

## 长流程状态与恢复

这是后续实现要求，当前 P5 已保留完整子任务完成记录，并通过两个已完成阶段后的暂停恢复；以下业务状态与产物依赖仍需实现：

- 保存事实及来源、约束、当前阶段、待解决问题和产物位置/版本。
- 规划当前阶段的子任务及成功条件；每阶段有动作、时间与重试预算，总任务保留总预算。
- 新需求或源数据变化时，标记受影响的计算与下游产物待更新；保留变化前后的证据。
- 恢复时重新核对应用、当前输入与已有产物。区分历史上已完成的步骤和当前仍成立的交付状态，避免重复写入。
- 失败恢复只重做失效部分。P6 重放保留任务与 Workflow 版本、验证条件及修复记录。

独立评分验收项与执行恢复数据分别定义：前者用于衡量完成情况，后者用于决定下一步。官方隐藏验收项保持在评测端。

## 实施顺序

| 顺序 | 工作 | 验收与阶段 |
| --- | --- | --- |
| 1 | 应用矩阵与基础原生动作 | P5：验证打开/切换窗口、菜单、单元格与文本编辑、Save As、附件选择，并记录不支持的控件 |
| 2 | OFFICE-01 基线 | P5：完成阶段执行与保存后验证；以约 20–30 个动作作为首轮预算目标，按实际 UI 调整并披露 |
| 3 | OFFICE-02、OFFICE-03 | P5：扩大产物种类与应用数量，加入需求变更和下游更新 |
| 4 | 暂停、重启与干扰 | P5：在已完成中间阶段后暂停恢复；覆盖焦点变化、临时对话框和应用重启；检查无重复写入及产物正确 |
| 5 | 成功 trace 转为 Workflow | P6：确定性重放、阶段验证与失败修复；保留新旧版本 |
| 6 | 官方任务与视觉覆盖 | 适配 WindowsWorld evaluator 与运行协议；需要视觉的任务随 P7 扩展 |

每条参考任务先完成一次独立验收，再进行至少三轮独立初始状态的重复运行，披露全部结果。阶段验收同时要求最终产物检查与中间证据完整，成功率以实际记录为准。

## English summary

Windows acceptance uses Microsoft desktop Word, Excel, PowerPoint, Outlook and File Explorer, matching the customer's applications. Alternative office suites are outside this acceptance scope. WindowsWorld informs intermediate and final evaluation; OSWorld 2 informs long-running task state and changing requirements.

Three proposed development tasks cover weekly reporting, meeting materials and synchronized revisions. These tasks have not run and are not official WindowsWorld results. Verify intermediate business states, then independently reopen and inspect persisted deliverables. Mail tasks end with saved drafts.

P5 adds application coverage, phased execution, artifact verification and recovery after completed stages. P6 adds workflow replay and versioned repairs. Official benchmark integration must preserve its evaluator and disclose the observation/action protocol; P7 expands visual checks.
