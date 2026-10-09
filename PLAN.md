# Bokkio 分阶段开发计划

> 需求来源：`docs/RESEARCH.md`，信息核验时间为 2026-09-23。  
> 本计划只拆解研究方案中已明确的目标架构、能力与验证问题，不引入新业务需求。

## 当前总体位置（2026-10-08）

P6 的 Windows 原计划验收完成，P7 已进入部分实现与验收。Mac 包/CLI 截图与 OCR 正常流程 3/3、拒绝 8/8；真实输入、自动 Agent 降级和 Windows 实机视觉仍待完成。三道微软 Office 原题已完成软件准备，实机 started 0 / blocked 3，评分为空。两端最新隔离回归各 373/373。

阶段位置与证据见 [总体进度](docs/STATUS.md)，下一步及所有待办见 [Pending](docs/PENDING.md)。下文保留原计划和按日期记录的历史验收。

## 1. 计划总览

目标架构按研究方案第 1.1 节与第 13.1 节组织：

```text
用户 / 自然语言 / 录制操作
          ↓
LLM / Agent 高层规划
          ↓
Jev 快速决策
          ↓
Unified Element Layer
          ↓
Windows UIA   ←→   macOS AXUIElement
          ↓
Native Apps
```

实施顺序不从 LLM 开始，而是先在本机验证最有不确定性的底层能力：

| 阶段 | 名称 | 主要架构层 | 核心问题 |
|---|---|---|---|
| P0 | 前置调研与验证环境 | 全链路准备 | 确认可复用组件和权限边界 |
| P1 | 最小 macOS AX 读取层 | macOS AXUIElement | 本机能否稳定读取真实 UI 树 |
| P2 | 统一 Element 模型与 macOS 操作 | Unified Element Layer | macOS 元素能否用统一模型表示和执行 |
| P3 | Windows UIA 读取与操作 | Windows UIA | Windows 能否接入同一套 Element API |
| P4 | Jev 局部决策层 | Jev Layer | Jev 能否从 Element Tree 选择元素和动作 |
| P5 | LLM 高层规划与执行循环 | LLM / Agent Layer | LLM 能否拆解目标并驱动 Jev/Runtime |
| P6 | Recorder 与确定性 Workflow | 旁路 Recorder | 操作轨迹能否固化为可重放流程 |
| P7 | Vision / CUA 兜底与可靠性加固 | 全链路 | Accessibility 不足时如何安全降级 |

## 2. 阶段计划

### P0：前置调研与验证环境

**目标**

- 建立 macOS 本机验证环境，准备 Windows 验证环境。
- 明确第一阶段使用的参考项目和测试应用。
- 不开发产品功能，只完成可进入 P1 的前置条件。

**范围**

做什么：

- 安装并运行 `xa11y`，验证其文档中宣称的 Accessibility Tree、Selector、Element 操作和 Python / Rust / JavaScript 绑定在本机可用。
- 运行或阅读 `NomiFun`，确认其 macOS AXUIElement + Vision OCR、Windows UI Automation 的完整产品体验可作为参考，但不直接作为本项目底座。
- 阅读并运行 `agent-desktop`、`computer-use-jev` / `jev-desktop`，只提取 Agent API、稳定 ref、Jev decision loop 的设计。
- 阅读 `computeruseprotocol`，确认 CUP 是否适合作为统一 Element Schema 的协议参考。
- 建立 macOS 测试样本：Finder、TextEdit、浏览器、系统设置，以及一个包含按钮、文本框、下拉框的固定测试应用。

明确不做什么：

- 不实现 LLM。
- 不实现 Jev。
- 不实现 Recorder。
- 不做 Windows 自动化改造。
- 不直接复用 `agent-desktop` 作为 Windows + macOS 成品底座，因为研究方案记录其 Windows 仍为 Planned。

**技术选型**

| 用途 | 选型 | 依据 |
|---|---|---|
| Desktop Runtime 底层候选 | `xa11y` | 研究方案将其列为跨平台 Element Runtime 第一选择，宣称支持 Windows UIA、macOS AXUIElement、Linux AT-SPI2，并提供 Selector、Element 操作和 Python / Rust / JavaScript 绑定 |
| 统一 Element Schema | CUP / `computeruseprotocol` | 研究方案将其作为统一 UI 表示协议，可转换 Windows UIA、macOS AXUIElement 等平台差异 |
| Agent ↔ Desktop 接口参考 | `agent-desktop` | 其 snapshot / find / click / type 等 API 与 stable ref、structured JSON 设计值得借鉴，但 macOS-only 限制明确 |
| Jev 原型参考 | `computer-use-jev`、`jev-desktop` | 两者均展示 Accessibility Tree → Element token → Action + Target 的局部决策循环 |
| 完整产品参考 | `NomiFun` | 研究方案记录其使用 React + Rust + Tauri，覆盖 macOS AXUIElement + Vision OCR 和 Windows UI Automation |
| Recorder 概念参考 | `OpenRPA`、`RPA.Windows`、`CrossMacro` | 只借鉴 Recorder / Selector / Workflow / Replay；不作为核心 Runtime。CrossMacro 更偏 Mouse/Keyboard Macro，因此不作为 Native Element Runtime 候选 |

**验收标准**

1. 本机能够运行至少一个 `xa11y` 示例，读取指定应用的 Accessibility Tree。
2. 记录 `xa11y` 的安装方式、权限要求、绑定方式、可用 action、异常表现和本机测试结果。
3. 输出一份简短验证记录：`xa11y` 是否满足 P1 读取层要求；若不满足，列出缺失能力。
4. Windows 测试机器或虚拟机可用，但不要求完成自动化验证。
5. 明确项目语言边界：核心 Runtime 优先 Rust，验证脚本可使用 `xa11y` 已提供的 Python 或 JavaScript 绑定。

**预估工作量**：0.5–1 周。

### P1：最小 macOS AX 读取层

**目标**

- 在 macOS 本机建立最小可跑通的 AXUIElement 读取能力。
- 验证真实 Native UI Tree，而不是截图识别。

**范围**

做什么：

- 获取前台应用、窗口和 Accessibility Tree。
- 输出元素的 `id / ref`、`role`、`name`、`value`、`state`、`bounds`、`parent / children`。
- 将 macOS AX 原始属性映射到平台无关的中间 JSON 结构。
- 支持按应用、窗口、role、name 的最小查询。
- 输出树形视图和 JSON 视图，便于人工验证。

明确不做什么：

- 不执行 click、type、set value。
- 不做完整 Windows UIA。
- 不接入 Jev 或 LLM。
- 不追求所有第三方应用的完整树覆盖率。
- 不做长期驻留服务、安装器或图形界面。

**技术选型**

- 优先使用 `xa11y` 的 macOS AXUIElement backend；若 P0 发现其读取能力不足，再评估封装原生 AXUIElement API，但必须先记录差异。
- 临时 CLI 或验证脚本可使用 Python / JavaScript；核心数据结构按未来 Rust Runtime 的边界设计。

**验收标准**

1. 在已授予辅助功能权限后，命令行可列出目标应用和窗口。
2. 对 TextEdit 或浏览器执行 `snapshot`，输出包含窗口、按钮、文本框、静态文本等真实 AX 元素。
3. 每个元素至少包含 `id / ref`、`role`、`name`、`value`、`state`、`bounds`、`parent`、`children`，无法获取的字段显式标为 `null` 或空。
4. 同一 UI 状态下连续读取两次，稳定字段的一致性可复现；动态 ref 的变化方式被记录。
5. 辅助功能权限未授予时，错误信息能明确指出 macOS 权限问题。
6. 至少记录三个应用的读取结果差异，包括一个表现较差的应用。

**预估工作量**：1–2 周。

### P2：统一 Element 模型与 macOS 操作

**目标**

- 将 P1 的读取结果升级为 CUP-like `UnifiedElement` 模型。
- 在 macOS 上打通最小 Element-based 操作闭环。

**范围**

做什么：

- 定义统一 Element Schema：`platform`、`role`、`name`、`value`、`state`、`bounds`、`actions`、`parent`、`children`、`platform_data`。
- 实现 Selector v1：优先 exact ref，其次 role + name，再考虑父级上下文。
- 实现最小 action：click / invoke、type、set value、select、focus、scroll。
- 建立执行前后 snapshot，用于验证操作是否生效。
- 保留 macOS AX 原始属性，便于诊断平台差异。

明确不做什么：

- 不实现 drag、完整窗口管理和全部系统控件。
- 不做模糊匹配和 LLM re-grounding。
- 不做 Workflow 文件格式。
- 不做 Windows。
- 不承诺免授权运行；macOS 辅助功能权限在本阶段是明确前置条件。

**技术选型**

- Runtime 继续优先封装或使用 `xa11y`。
- Element Schema 参考 CUP 的 JSON 结构和 compact representation，但可先定义项目内 `UnifiedElement`，待协议适配性确认后再决定是否直接采用 CUP。
- Selector 策略参考研究方案第 15 节的六级稳定性思路，但 P2 只实现前三层确定性部分。

**验收标准**

1. `snapshot` 输出的每个元素可被后续 `find` 稳定引用。
2. 对固定测试应用完成 click → type → set value / select → 读取结果的完整用例。
3. 同一操作在 UI 未变化时连续重放三次成功。
4. Selector 找不到目标时返回结构化错误，包含候选元素摘要，而不是裸异常。
5. 输出 `UnifiedElement` 与 macOS 原始属性的映射表。
6. 记录 macOS AX 支持和不支持的 action，以及每个 action 的实际验证结果。

**预估工作量**：2–3 周。

### P3：Windows UIA 读取与操作

**目标**

- 将 Windows UIA 接入同一个 Unified Element API。
- 验证跨平台 Runtime 是否成立。

**范围**

做什么：

- 在 Windows 上读取应用、窗口和 UIA Tree。
- 将 UIA Control Type、Name、Value、状态、 bounding rectangle、pattern/action 映射到统一模型。
- 复用 P2 的 `snapshot`、`find` 和最小 action API。
- 覆盖 Notepad、Explorer、Edge 或 Chrome、系统设置和一个固定 WinForms / WPF 测试应用。
- 记录 UIA pattern 与 macOS AX action 的差异。

明确不做什么：

- 不做 Linux。
- 不做企业级 UIA 容错。
- 不做 Recorder。
- 不做 Vision fallback。
- 不把 Windows-only 的 OpenRPA / RPA.Windows 作为 Runtime；它们只用于研究 Locator、Recorder 和 Workflow 概念。

**技术选型**

- 首选 `xa11y` Windows UIA backend。
- 若其 Windows 支持不足，评估 Rust + Windows UI Automation 实现统一 backend，但先做 benchmark 结论，不直接重写。
- 持续使用 CUP-like schema 做平台归一化。

**验收标准**

1. 同一个上层 API 在 macOS 和 Windows 上均能输出统一 JSON 结构的 Element Tree。
2. 同一组测试任务在两端均可完成：打开应用、读取树、点击按钮、输入文本、选择项、读取结果。
3. 对 `role / name / parent / actions` 建立跨平台映射表。
4. 至少记录 10 个 Windows UIA 与 macOS AX 的行为差异和归一化策略。
5. 输出 `xa11y` Windows backend 的性能基准：50、100、300、1000 个元素下 snapshot / find 的耗时。
6. 若必须绕开 `xa11y`，给出缺失能力、工作量估算和迁移方案。

**预估工作量**：3–5 周。

### P4：Jev 局部决策层

**目标**

- 建立 “Accessibility Tree → Jev → Element + Action” 的局部决策闭环。
- 避免每一步都调用大型 LLM。

**范围**

做什么：

- 将 compact Element Tree 和目标子任务交给 Jev。
- 约束 Jev 只能选择当前 snapshot 中存在的 element ref。
- 输出结构化结果：`action`、`target`、`value`、`confidence`、`done`、`blocked`、`reason`。
- 执行动作后重新 snapshot，再进入下一轮 Jev 决策。
- 低置信度、找不到目标或风险动作时停止并交回上层。
- 先用固定 UI 状态构建离线评测集，再接实时桌面。

明确不做什么：

- 不让 Jev 做全局任务规划。
- 不让 Jev 处理企业流程语义。
- 不让 Jev 输出任意坐标。
- 不接入 Vision fallback。
- 不做多 Agent 并发。

**技术选型**

- 以 `computer-use-jev` 和 `jev-desktop` 的 Element token 决策模式为参考。
- 保留 LLM provider 无关接口；Jev 决策头可以是托管模型、本地模型或微调头，具体接入方式作为开放问题保留。
- 上下文使用 CUP-like compact representation，避免完整大树直接进入模型。

**验收标准**

1. Jev 输入为 Element Tree + 子任务，输出为结构化 Element + Action，而不是自然语言计划。
2. 决策目标只能引用当前 snapshot 中存在的元素 ref；非法 ref 被拒绝。
3. 在 50 / 100 / 300 / 1000 个元素的数据集上测量延迟、token 用量、正确元素选择率和错误动作率。
4. 覆盖研究方案列出的难例：相似元素、动态列表、深层 Tree、Tree 变化。
5. 实时桌面端完成至少五个任务：点击按钮、输入文本、选择下拉框、展开/折叠、滚动。
6. 低置信度结果不会自动执行，而是返回需要人工、LLM 或重新观察的状态。

**预估工作量**：3–6 周。

### P5：LLM 高层规划与执行循环

**目标**

- 接入 LLM / Agent 层，让自然语言目标被拆解为子任务，并驱动 Jev 和 Runtime。

**范围**

做什么：

- 定义 Planner 输入输出：用户目标、约束、平台能力、当前任务状态。
- Planner 只产出 Task / Subtask / verification condition，不直接选择具体元素。
- Jev 继续负责当前页面上的 Element + Action。
- 建立观察结果回传：snapshot、执行结果、错误类型、任务进度。
- 支持任务暂停、确认、取消和失败恢复。
- 实现研究方案第 20 节中的简单与中等 benchmark 的跨平台子集。
- Windows 参考 WindowsWorld 职业办公跨应用任务，覆盖 Word、Excel、PowerPoint、邮件草稿和文件管理；参考 OSWorld 2 的分阶段执行、状态维护与需求变化。具体任务和验收见 [Windows 办公流程计划](docs/WINDOWS-OFFICE-PLAN.md)。

明确不做什么：

- 不把某个 LLM vendor 写死进 Runtime。
- 不实现完整 Vision / CUA。
- 不自动固化 Workflow。
- 不做多 Agent 编排和企业级审批系统。

**技术选型**

- LLM 接口保持 OpenAI、Claude、Gemini、本地模型和 MCP Agent 可替换；研究方案明确建议不绑定模型。
- Desktop Tools API 参考 `agent-desktop`：`snapshot`、`find`、`get`、`click`、`type`、`select`、`toggle`、`scroll`、`keyboard`、`window`。
- 分层职责固定为：LLM = What / Why，Jev = Which Element / Which Action，Runtime = How。

**验收标准**

1. 给定自然语言目标，LLM 能生成结构化子任务清单，每个子任务包含成功条件或验证方式。
2. Agent loop 能完成至少三个 macOS 任务和对应的 Windows 任务。
3. 至少覆盖一个浏览器任务和一个本地应用任务。
4. Jev 执行失败时，LLM 能基于新 snapshot 重新拆解或调整子任务。
5. 所有 planner 决策、Jev 决策、Runtime action、observation 和错误都有结构化 trace。
6. 对敏感动作建立确认策略；默认不允许无确认执行删除、支付、发送消息类操作。
7. Windows 办公流程分别记录中间业务状态与最终产物验收；保存后重新打开检查跨文件一致性，覆盖需求变更后更新和已完成阶段后的暂停恢复。新验收项尚未实测。

**预估工作量**：4–8 周。

### P6：Recorder 与确定性 Workflow

**目标**

- 将人工录制或 Agent 成功轨迹转化为 Element + Action Workflow。
- 让重复任务优先走确定性重放。

**范围**

做什么：

- 录制用户或 Agent 的 Element action、目标上下文、前后 snapshot 和执行结果。
- 生成 Workflow JSON，包含 `intent`、`action`、`target`、`value`、等待条件和验证条件。
- 实现确定性 replay、失败点定位和基础重试。
- Selector 使用多级 fallback：exact ref → role + name → role + name + parent → 窗口/应用上下文。
- 支持从成功 Agent trace 自动生成 Workflow v1，这是研究方案强调的高价值模式。
- 职业办公 Workflow 保存阶段依赖、输入/产物版本和验证条件；重放后独立核验交付物，需求变化与修复保留新旧版本。

明确不做什么：

- 不做完整图形化 Workflow Designer。
- 不做企业调度系统。
- 不做跨机器凭据同步。
- 不把 Mouse/Keyboard Macro 作为主要录制模型。
- 不承诺所有录制轨迹都能免修改重放。

**技术选型**

- Workflow 和 Selector 概念参考 OpenRPA / RPA.Windows，但 Runtime 不依赖它们。
- CrossMacro 只用于研究 Recorder / Workflow UX；因其偏 Mouse/Keyboard Macro，不作为 Element Runtime 选型。
- Workflow 表达参考研究方案第 16 节：Workflow 是可执行计划，不只是脚本。

**验收标准**

1. 录制一次 click、type、select 后，生成的 JSON 能无修改重放三次。
2. 同一 Workflow 在 macOS 或 Windows 的相同应用状态下重放成功，业务层不感知平台。
3. UI 小幅变化时，Selector 能通过 role + name 或父级上下文恢复；无法恢复时给出结构化失败原因。
4. Agent 成功 trace 能转换为 Workflow v1。
5. Workflow 失败时可选择交回 Jev 或 LLM 修复，且修复过程保留原 Workflow 版本。
6. 每个步骤记录 observation、action、selector 解析结果和验证结果。

**预估工作量**：4–8 周。

### P7：Vision / CUA 兜底与可靠性加固

**目标**

- 在 Accessibility Tree 不足时提供可控的视觉兜底。
- 将系统从功能验证推进到可靠桌面自动化运行时。

**范围**

做什么：

- 实现 screenshot、OCR / Set-of-Marks 和坐标 action 的降级路径。
- 定义切换规则：Accessibility 无目标、Element action 失败、UI 自绘、Remote Desktop、Canvas。
- 将视觉命中的坐标尽量回绑到 screenshot 区域或可观察元素，供后续修复。
- 加入权限检查、审计日志、执行速率控制、敏感动作确认和崩溃恢复。
- 建立 Windows + macOS 长期回归任务集，覆盖研究方案中的简单、中等、复杂任务。

明确不做什么：

- 不追求游戏和全自绘复杂界面的高成功率。
- 不做无人监督的高风险自动执行。
- 不把 Vision 作为第一优先路径。
- 不做完整企业 RBAC / 多租户平台。

**技术选型**

- Vision 路线参考 `NomiFun` 的 Accessibility Tree + Set-of-Marks + OCR 组合。
- Vision 只作为研究方案第 14 节定义的 Level 3 fallback。
- Runtime 继续保持 Rust 优先，必要时通过 FFI 提供 Python / Node / Go 接入。

**验收标准**

1. Accessibility Tree 找不到目标时，系统能按策略降级到 OCR / Vision / CUA，而不是直接失败。
2. Vision 动作能产生可审计的 screenshot、mark、坐标、置信度和执行结果。
3. 至少一个 Accessibility 表现差的应用通过视觉兜底完成 click + type。
4. 所有自动化执行均有限速、确认和取消机制。
5. 输出跨平台回归报告：任务、平台、路径（Deterministic / Jev / LLM / Vision）、耗时、成功率和失败原因。
6. 权限缺失、屏幕录制受限、应用无响应和 Tree 大幅变化都有可测试的错误路径。

**预估工作量**：6–10 周。

## 3. 关键风险

### 技术风险

1. **`xa11y` 能力不足**  
   研究方案认为它是最接近目标的跨平台 Element Runtime，但仍要求先 benchmark。若 Tree 提取、Selector、action 覆盖、Element identity 或性能不足，Runtime 工作量会显著增加。

2. **Windows UIA 与 macOS AXUIElement 语义不对齐**  
   两边的 role、state、action pattern、tree 深度和可操作控件不同。统一模型必须保留 `platform_data`，否则会丢失诊断和执行所需的平台信息。

3. **动态 UI 破坏 Element ref**  
   窗口切换、异步加载、列表重绘、对话框出现都会导致 ref 失效。需要 Snapshot version、稳定属性、父级上下文和失败重读机制。

4. **Jev 决策头接入方式未定**  
   研究方案确认了 `Element Tree → action + target` 的方向，但未决定使用托管模型、本地模型还是专用微调决策头。P4 必须先做离线 benchmark，再选择接入方式。

5. **Jev 误操作风险**  
   错误点击、输入、删除、发送、支付或修改系统设置可能造成不可逆影响。低置信度和敏感动作必须阻断或要求确认。

6. **Vision fallback 的可回绑性有限**  
   坐标动作完成后不一定能对应到真实 Element。若无法回绑，Workflow 修复和确定性重放都会受限。

7. **Agent trace 不等于稳定 Workflow**  
   Agent 成功路径可能包含不必要的探索、动态等待和偶发 UI 状态。直接固化可能生成脆弱流程，需要清洗、参数化和验证条件。

### 平台与部署风险

1. **macOS 辅助功能权限**  
   AXUIElement 读取和操作通常需要用户显式授权。P1 不应假设免安装、免授权可用。

2. **macOS 屏幕录制与自动化权限分离**  
   Accessibility、Screenshot、Apple Events、输入监听可能要求不同权限。P7 前应将权限状态作为运行时能力的一部分暴露。

3. **免安装 vs 需辅助权限 / helper process 仍未决**  
   免安装体验更轻，但可能限制权限引导、后台 snapshot、崩溃恢复和长期驻留能力。需要在 P1/P2 用真实权限流程验证后决策。

4. **Windows 版本、应用框架和 UIA 实现差异**  
   Win32、WinForms、WPF、Electron、浏览器和自绘控件暴露的 UIA Tree 差异较大。测试矩阵必须覆盖原生与 Web/混合应用。

5. **安全边界**  
   桌面自动化可以读取窗口内容、截图和操作用户会话。日志、trace 和 Workflow 文件都可能包含敏感数据，需要脱敏与访问控制策略。

6. **审计与合规**  
   LLM 规划、Jev 决策、Runtime 执行和 Vision 降级必须可追溯，否则难以用于业务流程。

## 4. 开放问题

1. `xa11y` 是否可以直接成为 Bokkio 的长期 Runtime，还是只需要作为过渡验证层？
2. Unified Element Schema 是直接采用 CUP，还是项目内定义 CUP-like `UnifiedElement`？
3. Jev 决策头使用哪种形态：通用多模态模型、本地小模型、专用微调 policy head，还是混合路由？
4. Jev 的安全执行边界如何配置：哪些 action 需要确认，哪些应用、窗口或字段禁止访问？
5. macOS 最终发布形态是 CLI、单二进制、后台 helper、菜单栏应用，还是完整桌面应用？
6. 免安装优先还是稳定后台 Runtime 优先？两者的辅助功能授权、权限恢复和升级策略不同。
7. Recorder 以人工实时录制为主，还是以 Agent trace 自动固化为第一入口？
8. Workflow 的跨平台目标是“同一业务 JSON 可两端执行”，还是允许按平台拆分步骤？
9. Vision 兜底是否只允许在用户授权的会话中启用？
10. 多应用并发执行、窗口焦点抢占和后台自动化在两个 OS 上的真实边界是什么？

## 5. 下一步建议：P0 与 P1 具体开工方式

1. **建立验证记录**  
   在仓库新增 `docs/VALIDATION.md`，分别记录 `xa11y`、`NomiFun`、`agent-desktop`、`computer-use-jev` / `jev-desktop`、CUP 的运行环境、命令、结果、限制和结论。

2. **先验证 `xa11y` 的 macOS 读取路径**  
   授予辅助功能权限后，对 Finder、TextEdit 和浏览器执行最小 snapshot。目标是确认 AX Tree、selector、元素属性和 Python / Rust / JavaScript 绑定的真实可用性。

3. **固定测试矩阵**  
   P1 至少选择：
   - Finder：窗口、列表、按钮。
   - TextEdit：文本输入区、菜单、窗口标题。
   - Safari 或 Chrome：地址栏、搜索框、按钮、页面内基础控件。
   - 一个固定测试应用：包含 button、text field、checkbox、combobox、table。

4. **定义 P1 冻结版 CLI 合约**  
   只承诺五个命令形状：
   ```text
   apps        # 列出可见应用
   windows     # 列出指定应用窗口
   snapshot    # 输出树形 / JSON Element Tree
   find        # 按 ref / role / name 查询
   get         # 输出单个元素详情
   ```
   本阶段不添加 action 命令，避免读取层未稳定前扩大范围。

5. **产出三个决策点**  
   P1 结束时必须回答：
   - `xa11y` 能否满足 P2 操作层？
   - macOS 需要哪些权限，权限失败如何引导？
   - 哪些 AX 属性必须保留在 `platform_data`，哪些可进入统一模型？

6. **不要先写 LLM**  
   P1 的正确完成标准是“本机能稳定看见真实 UI”。只有读取层可靠后，才进入操作、Jev 和 Planner。

## 6. 当前执行重点（2026-10-02，续）

本项目的目标是 **Computer Use：操作原生桌面应用和跨应用流程**。浏览器用于检验混合界面的 Accessibility 兼容性。最新实测见 `docs/P1-REPORT.md`、`docs/P2-REPORT.md`、`docs/P3-REPORT.md`。

已完成：

- 本机 Accessibility 授权与原生读取；最新 TextEdit、Finder、系统设置、固定 Cocoa 应用及 Safari 本地页面矩阵通过。
- P2 统一模型、Selector 和核心原生动作再次完成三轮真实 CLI 验证；34 项隔离测试通过。
- 有效 macOS 滚动通过 AX 数值滚动条实现。三轮 0 → 0.25 → 0 往返均确认位置变化及 81 个内容节点位移；边界请求返回未移动。
- type 增加显式期望值验证；检查失败和目标消失返回 `unconfirmed`。
- `structural-v2` 稳定唯一、不可点击文本子节点的 ref。Finder 三组快照均无 ref 增减，仍有名称和坐标变化；交互控件的名称身份保留。
- P3 Windows UIA 在本机 Fusion 的 ARM64 Windows 11 IoT Enterprise LTSC 2024 Evaluation 虚机内通过：五应用读取、三轮 WinForms 动作、失效 ref 与 50/100/300/1000 原生控件规模基准；Windows 34 项测试通过。账户密码已自动设置、认证并记录在 Mac 私有目录。CPython 为 x64 模拟，结果不代表原生 x64 性能。

### 当前阶段与平台优先级

**P6 已完成 Windows 原生验收，P7 启动条件已满足。** 最终代码完成六步录制重放 3/3、真实 trace 保存重开 3/3，以及三组参数化跨应用重放、应用/执行进程重启恢复、结构变化和真实模型修复。见 [P6 验收](docs/P6-CLOSURE.md)。P7 已实现 Windows 截图接口、自绘 fixture 和 Mac 截图/OCR Runtime；Windows 像素验收、真实输入与自动视觉降级待完成，见 [P7 计划](docs/P7-PLAN.md)。

Windows 11 虚机继续可用；2026-10-06 已恢复 Mac 原生对照，见 [Mac 续测](docs/MACOS-FOLLOWUP.md)。原 P6 标准接受 macOS 或 Windows，本轮采用 Windows；macOS AX provider 对照、Office 激活和完整上游 benchmark 集成继续保留为平台/扩展工作。P5 的 Windows 原生规划、跨应用、恢复和交付已有实测；跨平台及已激活 Office 流程仍需分别验收。

### 本次续执行

- [x] Windows 原生 ScrollPattern 方向滚动；必须同时读回位置与内容变化，边界返回未确认。
- [x] ValuePattern 保留空字符串，校验只读控件；Notepad 原生 Edit 文档统一为 text_area。
- [x] 动作能力与执行方法对齐，增加 expand/collapse，并验证状态。
- [x] Windows 顶层窗口筛选，Settings 内部标题栏等保留在树中。
- [x] structural-v3：唯一 Windows HWND 支撑重复控件重排；重建后的旧 ref 拒绝。
- [x] 原生输入和滚动三轮测试、1,000 行 owner-data ListView 覆盖；补测四档规模基准。
- [x] Jev OpenRouter / TypeSafe transport、闭集 action/ref/value、置信度检查和快照检查。
- [x] 五种脚本化决策通过真实 Windows 操作链路；这是 Runtime 接口验证。
- [x] macOS 横纵滚动专用 Cocoa fixture 已编译；树循环改为有界错误。
- [x] macOS 横纵滚动 12 次确认、真实 Cocoa 子节点重排后同一 Workflow 重放通过。
- [ ] macOS 真正可见节点虚拟化、更多独立应用与结构变化实测。
- [ ] 仅暴露可见节点的原生虚拟化 provider：当前 Windows UIA 仍暴露全部 1,000 行。
- [x] 从本地 Jev 工程找到 OpenRouter key，配置 Mac 与 Windows 私有文件；key 不入仓库。
- [x] 真实 Jev 五样本离线评测 5/5；Windows 五个实时任务 5/5，实际下拉选择使用两步。
- [x] 50/100/300/1,000 控件规模评测：12 个开发样本中 9 个命中、3 个低置信度拒绝；记录 API 延迟、token 和费用。
- [x] 原生难例 4/4：同名元素父级区分、动态控件替换、旧决策拒绝、深层树七步执行。
- [x] 大树上下文收窄：重复开发评测 12/12；1,000 控件新目标 137/619/997 的原生点击三例通过，置信度仍为 0.7。
- [x] 原生分页部分暴露：每页仅 25 个 UIA 条目；换页后旧引用返回 stale_ref；真实 Planner/Jev 的两项流程通过。
- [ ] 扩大独立应用与真正 VirtualizedItem provider 覆盖，验证更多 viewport 和结构变化。
- [x] P5 首版：JSON Schema 子任务规划、应用/窗口绑定、原生成功条件、Jev/Runtime 循环及完整 trace。
- [x] bounded blocked/failed、动作与重规划预算、暂停/取消/恢复检查点。
- [x] Windows 三条真实跨应用任务 3/3；故意改变 UI 后拒绝旧决策并由真实 LLM 重规划恢复。
- [x] 两套 macOS Cocoa 跨应用 fixture 已编译，三条模型任务脚本已就绪。
- [x] P5 规划观察：目标名称、同名候选、父级/窗口、小范围相邻控件及状态标签；无名称命中时按窗口抽样，最多 240 节点。
- [x] 子任务窗口读取失败进入有界恢复；已完成子任务的具体目标和成功条件进入重规划上下文。
- [x] Windows 两次连续状态变化恢复、暂停/恢复及应用重启后的旧决策拒绝通过。
- [x] 七步真实跨应用流程与原生动作顺序验证通过，1,015 节点规划观察保留 13 节点。
- [x] Windows 检查点临时文件锁：有限重试及原生句柄占用复现实测通过。
- [x] 分页跨应用任务的模型、snapshot、窗口枚举与原生执行分项计时；检查点细分计时仍待补。
- [x] 外部 benchmark 准备：固定 WindowsAgentArena 源码版本，读取 154 份配置并记录哈希，预列五项原生 pilot，现已实现逐步派发与固定 evaluator 并执行；完整上游环境与服务端 runner 对齐仍待完成。
- [x] 三项 WAA 多步开发试跑：Explorer/Notepad 真实 Planner/Jev/UIA，复用固定版本 metric 函数，独立检查中间步骤、文件与新进程重开；保留所有失败及复测，详见 [报告](docs/P5-WAA-LONGCHAIN.md)。
- [x] 固定 WAA 三题修复后连续两轮各 3/3；两端 152 项隔离测试通过，仍在 P5 扩大验收阶段。
- [x] 原生 ValuePattern/RuntimeId 写入校验与搜索别名去重；绑定进程后获取新快照；阶段续规划、对话框 presence 条件与缺少交付文件时的补救；见 [修复报告](docs/P5-WAA-RECOVERY.md)。
- [x] 预选六种 WAA 派生输入：混合扩展名与十文件清单、严格 5 MiB 边界、多文件大小报告、标点大小写与零命中计数。原生暂停后用新 Runtime 恢复，独立核验源哈希、内容、保存与新进程重开；所有轮次保留，见 [续测报告](docs/P5-NATIVE-VARIATIONS.md)。
- [x] 最终 PNG 复测 1/1；需求变更最终两版 2/2，原文/旧交付/旧历史保持与新进程重开通过；当时两端各 195 项隔离测试通过。
- [x] 显式需求修订、按版本隔离完成记录与源事实、产物路径/大小/哈希版本记录；Windows 经典 Open 完整源路径约束，拒绝历史目录里的同名文件。
- [x] Explorer 原生菜单动作能力/RuntimeId 与勾选状态验证、Popup 导航保留、菜单变化后的阶段重读；统一有界计划校验，阻止旧窗口标题和矛盾条件。
- [x] Planner 推理强度可配置；成功条件支持父级名称约束；决策名称匹配排除验收 JSON 键名和 Windows 目标路径。
- [x] 纳入 WindowsWorld 办公跨应用与 OSWorld 2 长流程设计参考，定义三项参考任务、中间步骤和最终产物验收。
- [x] Office 安装前核对：当时 Office 未安装；Notepad 原生菜单保存、文件校验与新进程重开三轮通过。
- [x] 完整子任务完成记录：真实 Planner/Jev 在两个已完成阶段后暂停，恢复只执行第三次写入；不重复历史中间动作，最后一步检查当前状态。
- [x] 安装 Microsoft 365 七款桌面应用，版本 16.0.20430.20140，安装器退出码 0；安装后原生启动窗口读取 7/7 通过，初次 PowerPoint 超时保留并复查通过。
- [ ] Office 激活与 Outlook 设置：按用户要求暂缓，待可用微软许可证后恢复。
- [ ] Office 与邮件客户端 UIA 操作能力矩阵、三项办公参考任务、需求变更与阶段恢复实测。
- [x] macOS 原生横纵滚动与三条真实 Planner/Jev 跨应用任务 3/3；第三条旧快照在派发前拒绝并重规划恢复，见 [Mac 续测](docs/MACOS-FOLLOWUP.md)。

证据和命令见 `docs/RUNTIME-FOLLOWUP.md`、`docs/P4-REPORT.md`、`docs/P5-REPORT.md` 、`docs/P5-FOLLOWUP.md` 、`docs/P5-PAGED.md` 、`docs/P5-OFFICE-PREREQUISITES.md` 与 `docs/WINDOWS-OFFICE-SETUP.md`。最新 292 项隔离测试在 macOS 主机和 Windows 通过；固定五项 pilot 见 [报告](docs/P5-WAA-PILOT.md)。本轮新增测试与原生变体验收见 [续测报告](docs/P5-NATIVE-VARIATIONS.md)，WAA 开发试跑见 [长链路实测](docs/P5-WAA-LONGCHAIN.md)。

P5 Windows 最终确认：v26、v27 各 4/5，五项 Agent completed；原始标题评分差异保留。Settings 三次定向复测各 1/1，七个执行源码哈希匹配该轮验收代码。

### P6 已完成的 Windows 验收

- [x] 语义 Recorder：目标、前后快照、原生回执与条件；Workflow v1 含 intent/action/target/value、wait/verify、依赖及版本哈希。
- [x] 完成 Agent trace 的观察/决策/回执校验及固化；未完成、无验证或依赖未知光标位置的动作拒绝固化。
- [x] 确定性重放、ref 与完整语义上下文核验、歧义拒绝、失败点定位、有界观察重试；未知派发结果不重复动作。
- [x] 失败 Workflow 生成保留父版本的新版本；可向 Jev/Planner 适配器交出修复上下文，提案验证后单独重放。
- [x] Windows click/type/select 与跨应用写入录制；同一 JSON 在新进程三次重放并独立核验通过。
- [x] 真实 P5 成功 Notepad trace 固化后的五步 Workflow 三次保存/重开通过；0 派发的失败版本与 revision 2 修复重放通过。
- [x] 一份七步 Explorer → Notepad → Explorer 模板，三组参数全部通过；源文件与交付物 SHA-256、保存重开和不同 PID/执行进程恢复通过，仅派发剩余一步。
- [x] 原生客户端语义回执入口 `capture_receipt`，实际捕获两次 Explorer 选择，不重复派发；成功 Agent trace 固化继续可用。
- [x] 无名容器结构变化的 named-context 恢复，以及真实 GPT-4.1 selector 修复；原失败版本零派发，新版本保留 parent hash 并重放通过。
- [x] 常规重放复用动作后新观察，遍历由四次降为三次；执行前快照校验和等待期间新观察保留。
- [x] 主机与 Windows 隔离回归各 292/292；输入/产物变化、检查点篡改、未知完成、应用范围和歧义均有拒绝用例。

### 平台与可选扩展

- [ ] 可选录制扩展：全局人工键鼠监听。当前已满足原计划“人工录制或成功 Agent trace”的来源要求。
- [x] macOS 原生 AX 对照恢复；动作 3/3、录制重放 3/3、成功 trace 重放 3/3、结构重排、零派发失败/版本修复与暂停恢复通过。
- [ ] macOS 文件交付、参数化文件合约、跨执行进程/PID 恢复、真实模型修复扩展对照。

实现与原生结果见 [P6 文档](docs/P6-WORKFLOW.md)。WAA 的完整上游 runner 和环境对齐继续作为 benchmark 集成工作；Office 激活仍按既有要求暂缓。扩展原生结果见 [P6 验收](docs/P6-CLOSURE.md)，最终 v5 的三次录制与三次成功 trace 重放均通过；P7 已可开始，后续按 [P7 计划](docs/P7-PLAN.md) 推进窗口截图、自绘目标与视觉兜底。

## Mac Office 实测（2026-10-07）

- [x] 四应用 CUA 交互：Excel/Word/PowerPoint/Outlook 基线、修订、草稿附件及文档重开；六份文件独立校验，v1 字节保留。
- [ ] Bokkio Agent/Workflow Office 验收：disabled 编辑区能力、Excel 单元格读写、Outlook 窗口遍历、未知 AXPress 完成、三轮重复与进程恢复仍待实现/验收。

详见 [Office 报告](docs/MACOS-OFFICE-REPORT.md)。CUA pilot 不计作 Bokkio P7 兜底实现；Windows Office 暂缓状态保留。

## 2026-10-09更新

Mac公共视觉协议、Apple Vision provider、Agent/Jev/CLI文字降级已实现；主机435/435，最新原生只读观察/决策3/3，实际输入待交互会话。Office历史十轮各0/3保留；Windows工作暂缓。见[视觉接入](docs/P7-VISUAL-BRIDGE.md)与[当前进度](docs/STATUS.md)。以下历史阶段记录保留当时证据。

## 当前 Pending

完整剩余项及优先级见 [Pending 清单](docs/PENDING.md)。最新主机与 Windows 隔离回归各 373/373；这不代替 Windows 新截图和 Office GUI 的实机验收。

## P7.1 实现进展（2026-10-08）

- [x] Windows 原生客户区捕获 API/CLI，窗口身份、时间、图像哈希、DPI 与物理坐标映射；隔离 PrintWindow 超时。
- [x] 自绘 fixture 构建与只读像素/移动/故障验收脚本；主机和 Windows 各 314 项隔离测试通过。
- [ ] 三轮交互窗口像素/坐标和六类窗口故障实测：guest 前置检查返回 `desktop_unavailable`，Mac CUA 报锁定，交互桌面尚不可用。
- [ ] P7.2 OCR/视觉候选、P7.3 有界输入与后续可靠性。

P7 已进入实现，P7.1 尚未满足实机退出条件，详见 [报告](docs/P7-CAPTURE.md)。

### 同日 Mac 路径复查

ScreenCaptureKit 自有窗口截图诊断 3/3，可继续 Mac 捕获/视觉研发；当前 AX 返回 application 代理，元素操作前置检查失败。诊断尚未接入 Runtime，不计作 P7.1 全部通过。见 [报告](docs/MACOS-CAPTURE-PROBE.md)。

### Mac P7 Runtime 进展（同日）

- [x] 生产包/CLI Mac 窗口采集、内核进程身份、图像/坐标合约及本机 Vision OCR；正常流程 3/3，拒绝用例 8/8，CLI 实机通过。
- [x] 有界输入代码、单次回执、操作后 OCR 验证与未知完成不重试；实机输入前置拒绝为零派发。
- [ ] 正向点击/输入、自动 Planner/Jev/Workflow 降级、更多可靠性故障及 Windows OCR。

两端隔离回归 355/355；详情见 [报告](docs/P7-MACOS-VISUAL.md)。

## Office 原题 pilot 准备（2026-10-08）

固定 WindowsWorld 提交与三道微软 Office L1 原题；初始化、原生 runner、独立文件评分与原始 VLM 入口已落地。两端回归各 373/373。实机试跑planned 3、started 0、blocked 3，未取得任务成绩；交互会话恢复后继续原生编辑和视觉降级覆盖。详见 [报告](docs/OFFICE-PILOT-READINESS.md)。
