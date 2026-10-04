# Bokkio 分阶段开发计划

> 需求来源：`docs/RESEARCH.md`，信息核验时间为 2026-09-23。  
> 本计划只拆解研究方案中已明确的目标架构、能力与验证问题，不引入新业务需求。

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

---

# 附录：原始研究方案（RESEARCH.md）

# Windows + macOS 跨平台 AI Computer Use / RPA 研究方案

> 研究目标：寻找或构建一个同时支持 **Windows + macOS** 的桌面自动化工具，具备类似 UiPath 的 Native UI Element Tree 能力，并进一步引入 **Jev 快速决策 + LLM 全局规划 / Computer Use**，最终形成“确定性 RPA + AI Agent”的混合执行体系。
>
> 信息核验时间：2026-09-23

---

## 1. 我的目标与需求

### 1.1 核心目标

希望得到一个类似下面形态的工具：

```text
                    用户
                     │
            自然语言 / 录制操作
                     │
                     ▼
             ┌──────────────┐
             │ LLM / Agent  │
             │ 高层规划      │
             └──────┬───────┘
                    │
              Task / Subtask
                    │
                    ▼
             ┌──────────────┐
             │     Jev      │
             │ 快速决策      │
             └──────┬───────┘
                    │
            Element + Action
                    │
                    ▼
        ┌────────────────────────┐
        │ Native Accessibility   │
        │ Element Runtime        │
        └───────────┬────────────┘
                    │
           ┌────────┴────────┐
           ▼                 ▼
       Windows UIA       macOS AXUIElement
           │                 │
           └────────┬────────┘
                    ▼
               Native Apps
```

### 1.2 必须满足的能力

#### A. Windows + macOS 双平台

不是“Windows 有完整能力、macOS 只能截图”，而是两边都应该尽可能使用原生 Accessibility/UI Automation：

- Windows → Microsoft UI Automation / UIA
- macOS → Accessibility API / AXUIElement

#### B. Native UI Element Tree

类似 UiPath 的核心能力：

```text
Application
 └── Window
      ├── Menu
      ├── Toolbar
      ├── Button
      ├── TextBox
      ├── ComboBox
      ├── Table
      │    ├── Row
      │    └── Cell
      └── Dialog
```

每个 Element 应尽可能具有：

- id / ref
- role / control type
- name
- value
- state
- bounds
- parent / children
- supported actions
- platform-specific raw properties

重点不是“看截图猜按钮”，而是读取 OS 暴露的真实 UI 结构。

#### C. Element-based 操作

至少支持：

- Click / Invoke
- Type
- Set Value
- Select
- Toggle
- Expand / Collapse
- Focus
- Scroll
- Keyboard
- Drag
- Window management

优先通过 Element API 操作，而不是：

```text
move mouse to x=532,y=271
click
```

#### D. Recorder / Workflow

希望进一步支持：

```text
用户操作
   ↓
读取当前 Element
   ↓
记录 Element + Action
   ↓
形成 Workflow
   ↓
保存
   ↓
后续 deterministic replay
```

例如：

```json
{
  "action": "click",
  "target": {
    "role": "button",
    "name": "Submit"
  }
}
```

最终可以形成：

```text
Open App
  ↓
Find Window
  ↓
Click Element
  ↓
Type Text
  ↓
Select Item
  ↓
Click Save
  ↓
Wait
  ↓
Verify
```

#### E. Jev 快速决策

希望把 Jev 放在 Element Tree 和高层 LLM 之间：

```text
Accessibility Tree
        ↓
       Jev
        ↓
Action + Target Element
```

Jev 不负责“理解整个企业任务”，而主要负责：

- 当前应该操作哪个 Element
- 当前应该执行什么 Action
- 是否需要继续观察
- 是否已经完成
- 是否应该停止
- 低置信度时不要盲目执行

这样可以避免每一个 Click / Type 都调用大型 LLM。

#### F. LLM / Agent 全局控制

LLM 负责更高层：

```text
“把这个 Excel 清理后保存成 PDF”
```

拆解成：

```text
1. 找到 Excel
2. 打开文件
3. 清理数据
4. 导出 PDF
5. 验证文件
6. 返回结果
```

每一个子任务再交给：

```text
Jev
  ↓
Element Tree
  ↓
Action
```

#### G. Computer Use 兜底

不是所有 UI 都能很好地暴露 Accessibility Tree。

因此需要 fallback：

```text
Native Element Tree
        ↓
找不到 / 不确定
        ↓
OCR / Screenshot / Vision
        ↓
CUA / VLM
        ↓
Mouse / Keyboard / Coordinate
```

最终形成：

```text
Deterministic Element Automation
          ↓
        Jev
          ↓
       LLM Agent
          ↓
     Vision / CUA
```

---

# 2. 与传统 UiPath 的区别

目标并不是简单复制 UiPath。

## 传统 RPA

```text
Recorder
   ↓
Element Selector
   ↓
Workflow
   ↓
Deterministic Replay
```

优势：

- 快
- 稳定
- 可审计
- 可重复

问题：

- UI 改变后 Selector 容易失效
- 复杂任务需要人工配置
- 对未知环境适应性有限

## 目标架构

```text
                  ┌──────────────┐
                  │ LLM / Agent  │
                  └──────┬───────┘
                         │
                    高层任务规划
                         │
                         ▼
                  ┌──────────────┐
                  │     Jev      │
                  └──────┬───────┘
                         │
                  Element + Action
                         │
                         ▼
              Native Accessibility
                         │
                ┌────────┴────────┐
                ▼                 ▼
              UIA                AX
                │                 │
                └────────┬────────┘
                         ▼
                    Native App
```

核心思想：

> **能确定性执行的事情，就不要让大模型每次重新推理。**

---

# 3. 当前调研得到的项目

## 3.1 xa11y —— 最值得研究的跨平台 Element Runtime

GitHub：

https://github.com/xa11y/xa11y

定位：

> Cross-platform desktop accessibility library for driving native desktop apps.

当前明确支持：

| 能力 | Windows | macOS | Linux |
|---|---:|---:|---:|
| Accessibility Tree | ✅ | ✅ | ✅ |
| Native backend | UI Automation | AXUIElement | AT-SPI2 |
| Selector | ✅ | ✅ | ✅ |
| Element 操作 | ✅ | ✅ | ✅ |
| Python | ✅ | ✅ | ✅ |
| Rust | ✅ | ✅ | ✅ |
| JavaScript | ✅ | ✅ | ✅ |

它提供类似 CSS 的 Selector：

```text
button
button[name='OK']
text_field[name^='Search']
group > button
window button
button:nth(2)
```

Action 包括：

```text
press
focus
blur
toggle
expand
collapse
select
set_value
type_text
increment
decrement
show_menu
```

### 为什么重要

它非常接近“UiPath Element Engine 的底座”：

```text
OS UI
  ↓
Accessibility Tree
  ↓
Unified Element API
  ↓
Selector
  ↓
Action
```

而且它本身不是一个完整 Agent，这反而是优点：

> 可以把 Jev、LLM、Workflow Engine 接到上面。

---

# 4. CUP / Computer Use Protocol —— 值得重点关注的统一 Element Schema

GitHub：

https://github.com/computeruseprotocol/computeruseprotocol

定位：

> Universal schema for AI agents to perceive and interact with any desktop UI.

它试图解决一个关键问题：

```text
Windows UIA
macOS AXUIElement
Linux AT-SPI2
Web ARIA
Android
iOS
```

每个平台的 UI Tree 都不一样。

CUP 把它们转换成统一 Schema。

例如：

```json
{
  "version": "0.1.0",
  "platform": "windows",
  "app": {
    "name": "Spotify"
  },
  "tree": [
    {
      "id": "e0",
      "role": "window",
      "name": "Spotify",
      "actions": ["click"]
    }
  ]
}
```

同时提供针对 LLM 的 Compact Representation。

### 对本项目的意义

可以考虑：

```text
Windows UIA
      │
      ▼
   xa11y
      │
      ▼
CUP Unified Element Model
      │
      ├── Jev
      ├── LLM
      ├── Recorder
      └── Workflow Engine
```

这可以避免以后所有 Agent 逻辑都写死 Windows / macOS。

---

# 5. agent-desktop —— 很好的 Agent ↔ Desktop Runtime 参考

GitHub：

https://github.com/lahfir/agent-desktop

项目当前核心是：

> Agent 通过 OS Accessibility Tree 查看和操作桌面。

技术：

- Rust
- Native CLI
- FFI
- Accessibility Tree
- Stable refs
- Structured JSON
- Session
- Workflow-oriented interaction
- Chromium CDP interop

它强调：

> 不是猜像素，而是读取真实 UI 结构。

它目前基于 xa11y。

### 重要限制

截至 2026-09：

| 平台 | 状态 |
|---|---|
| macOS | ✅ |
| Windows | Planned |
| Linux | Planned |

所以它**不能直接作为当前 Windows + macOS 成品底座**。

但它的架构非常值得借鉴。

---

# 6. jev-desktop —— Jev + Accessibility Tree 的关键参考

GitHub：

https://github.com/lahfir/agent-desktop/tree/main/skills/jev-desktop

它实现的核心 Loop：

```text
Goal
 ↓
Read Accessibility Tree
 ↓
Jev 决策
 ↓
选择 Action + Target
 ↓
执行
 ↓
重新读取 Tree
 ↓
Jev 再决策
 ↓
...
```

关键点：

> Tree 不需要全部暴露给调用 Agent。

它通过：

```text
snapshot
 ↓
compact refs
 ↓
Jev
```

减少上下文消耗。

### 当前能力

Jev 可以选择：

```text
CLICK
TYPE_TEXT
CHECK
UNCHECK
EXPAND
COLLAPSE
SCROLL
DRILL
WIDEN
WAIT
DONE
BLOCKED
```

这正符合：

> **Jev 做局部快速决策，LLM 做全局任务规划。**

---

# 7. computer-use-jev —— 最直接的 Jev Computer Use 原型

GitHub：

https://github.com/paulsmith/computer-use-jev

它当前是 macOS。

架构：

```text
macOS Accessibility API
        ↓
apps / windows / snapshot
        ↓
Element Tokens
a1 / w2 / e5
        ↓
Jev
        ↓
Action + Target
        ↓
执行
        ↓
重新 snapshot
```

特别值得学习的一点：

> Jev 只能从当前真实存在的 Element token 中选择目标。

因此不是：

```text
Jev:
click x=532 y=271
```

而是：

```text
snapshot:
e1 = Search
e2 = Save
e3 = Cancel

Jev:
CLICK e2
```

这让决策空间天然受到约束。

---

# 8. NomiFun —— 当前最值得实际运行验证的完整跨平台产品之一

GitHub：

https://github.com/nomifun/nomifun-desktop

它是一个完整的本地 AI workstation，而不是单纯 RPA library。

技术架构：

```text
React
 +
Rust
 +
Tauri
```

Native Computer Use：

```text
Accessibility Tree
+
Set-of-Marks
+
OCR
```

当前项目资料明确写明：

```text
macOS → AXUIElement + Vision OCR
Windows → UI Automation
Linux → AT-SPI2 partial
```

因此它目前在“Windows + macOS Computer Use”这个目标上，比 agent-desktop 更接近可直接验证的产品。

### 值得研究的地方

- Windows UI Automation
- macOS AXUIElement
- Element Tree
- Set-of-Marks
- OCR
- Computer Use
- Browser Use
- MCP
- Agent Runtime
- 本地执行

### 与目标的差距

它目前不是：

```text
LLM
 ↓
Jev
 ↓
Element
```

而更接近：

```text
Agent / LLM
 ↓
Computer Use
 ↓
Accessibility + Vision
```

因此可以把它作为完整产品参考，而不是 Jev Runtime 的直接答案。

---

# 9. CrossMacro —— 跨平台 Recorder 参考

GitHub：

https://github.com/alper-han/CrossMacro

明确支持：

- Windows
- macOS
- Linux

核心能力：

```text
Record
 ↓
Mouse / Keyboard
 ↓
Workflow
 ↓
Replay
```

并支持：

- Scheduling
- CLI
- MCP
- Screen-aware automation
- Window management

### 但是它不是核心候选

原因：

它更偏：

```text
Macro / Input Automation
```

而不是：

```text
Native Accessibility Element Automation
```

因此：

> 可以研究它的 Recorder / Workflow UX，但不应该把它作为 Native Element Runtime 的核心技术参考。

---

# 10. 传统 RPA：OpenRPA / RPA.Windows

## OpenRPA

适合研究：

- Recorder
- Workflow Designer
- Selector
- RPA 流程
- Enterprise RPA

但主要是 Windows 路线。

## RPA.Windows

适合研究：

- Windows UI Automation
- Windows Element
- Locator
- Recorder
- Robot Framework

它的价值主要是：

> 研究传统 RPA 如何把 Windows UI Element 转换为可复现的 Robot/Workflow 操作。

但它无法解决 macOS 跨平台问题。

---

# 11. 项目横向比较

| 项目 | Win | macOS | Native Element | Recorder | Workflow | Jev | LLM/Agent | 主要价值 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| **xa11y** | ✅ | ✅ | ⭐⭐⭐⭐⭐ | △ | △ | ❌ | ❌ | 跨平台 Element Runtime |
| **CUP** | ✅* | ✅* | ⭐⭐⭐⭐⭐ | ❌ | ❌ | ❌ | ⭐⭐⭐ | 统一 Element Schema |
| **agent-desktop** | 🟡 | ✅ | ⭐⭐⭐⭐⭐ | ❌ | △ | ✅ | Agent调用 | Agent Desktop Runtime |
| **jev-desktop** | 🟡 | ✅ | ⭐⭐⭐⭐⭐ | ❌ | △ | ⭐⭐⭐⭐⭐ | ❌ | Jev Decision Loop |
| **computer-use-jev** | ❌ | ✅ | ⭐⭐⭐⭐⭐ | ❌ | ❌ | ⭐⭐⭐⭐⭐ | ❌ | Jev + Native CUA 原型 |
| **NomiFun** | ✅ | ✅ | ⭐⭐⭐⭐ | △ | △ | ❌ | ⭐⭐⭐⭐ | 完整跨平台 Computer Use 产品 |
| **CrossMacro** | ✅ | ✅ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ❌ | △ | 跨平台 Recorder |
| **OpenRPA** | ✅ | ❌ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ❌ | △ | 传统 RPA |
| **RPA.Windows** | ✅ | ❌ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ❌ | ❌ | Windows RPA |

\* CUP 是协议/Schema，不等于完整的 OS Driver。

---

# 12. 当前最重要的判断

没有必要继续单纯搜索：

> “有没有一个开源的 UiPath，Windows + macOS + Recorder + Element Tree + AI？”

目前更现实的结论是：

> **没有一个成熟开源项目完整覆盖全部目标。**

但已经存在足够好的组件，可以组合成目标架构。

---

# 13. 推荐的目标架构

## 13.1 四层模型

```text
┌─────────────────────────────────────────────┐
│              LLM / Agent Layer              │
│                                             │
│ Goal / Planning / Reasoning / Verification  │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│                 Jev Layer                   │
│                                             │
│ Fast Action + Element Decision              │
│ Local UI reasoning                          │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│            Unified Element Layer             │
│                                             │
│ CUP-like representation / Element refs      │
└──────────────────────┬──────────────────────┘
                       │
              ┌────────┴─────────┐
              ▼                  ▼
       Windows UIA          macOS AXUIElement
              │                  │
              └────────┬─────────┘
                       ▼
┌─────────────────────────────────────────────┐
│             Native Applications             │
└─────────────────────────────────────────────┘
```

旁边再挂：

```text
Recorder
   ↓
Element + Action
   ↓
Workflow JSON
   ↓
Deterministic Replay
```

以及：

```text
Element Tree Failure
        ↓
       Jev
        ↓
     LLM Agent
        ↓
    Vision / CUA
```

---

# 14. 最终执行策略：四级 Fallback

## Level 0：Deterministic RPA

```text
Workflow
 ↓
Selector
 ↓
Element
 ↓
Action
```

适合重复任务。

优点：

- 最快
- 最便宜
- 最稳定
- 可审计

---

## Level 1：Jev

```text
Accessibility Tree
 ↓
Jev
 ↓
Element + Action
```

适合：

- UI 有轻微变化
- 不想每一步调用 LLM
- 当前页面的操作空间比较明确

---

## Level 2：LLM Agent

```text
User Goal
 ↓
LLM
 ↓
Task decomposition
 ↓
Jev / Desktop Tools
```

适合：

- 多 App
- 多页面
- 复杂任务
- 未知 Workflow

---

## Level 3：Vision / CUA

```text
Accessibility unavailable
       ↓
Screenshot
       ↓
OCR / VLM / CUA
       ↓
Mouse / Keyboard
```

适合：

- Canvas
- 游戏
- Remote Desktop
- 自绘 UI
- Accessibility Tree 不完整的应用
- 非标准控件

---

# 15. Recorder 应该怎么设计

目标不是单纯录：

```text
Mouse(x,y)
Keyboard("hello")
Click()
```

而应该录：

```json
{
  "action": "click",
  "target": {
    "role": "button",
    "name": "Submit",
    "window": "Order Management"
  },
  "fallback": {
    "vision": true
  }
}
```

再加入 Selector 的多级稳定性：

```text
1. Stable element reference
2. Accessibility properties
3. Parent-child relationship
4. Window / application context
5. Visual fallback
6. LLM re-grounding
```

例如：

```text
Exact ref
   ↓ fail
role + name
   ↓ fail
role + name + parent
   ↓ fail
fuzzy accessibility match
   ↓ fail
OCR / Vision
   ↓ fail
LLM / CUA
```

---

# 16. Workflow 不应该只是“录制脚本”

建议 Workflow 本身就是一种可执行计划：

```json
{
  "name": "Create Purchase Order",
  "steps": [
    {
      "id": "s1",
      "intent": "open purchase order",
      "action": "click",
      "target": {
        "role": "button",
        "name": "Purchase Order"
      }
    },
    {
      "id": "s2",
      "intent": "enter supplier",
      "action": "set_value",
      "target": {
        "role": "combobox",
        "name": "Supplier"
      },
      "value": "{{supplier}}"
    }
  ]
}
```

这样：

> Recorder 只是生成 Workflow 的一种方式。

Workflow 也可以由：

- 人工创建
- LLM 生成
- Jev 执行后自动固化
- 录制后由 LLM 优化

---

# 17. 一个更有价值的模式：Agent → Workflow 固化

这是整个项目非常值得做的能力。

第一次：

```text
用户：
“帮我在系统里创建一个采购订单”
```

Agent：

```text
LLM
 ↓
Jev
 ↓
Element Tree
 ↓
完成任务
```

系统自动记录：

```text
Observe
 ↓
Action
 ↓
Observe
 ↓
Action
 ↓
...
```

然后生成：

```text
Workflow v1
```

以后重复任务：

```text
Workflow
 ↓
Deterministic Replay
```

只有失败时：

```text
Workflow
 ↓ fail
Jev
 ↓ fail
LLM
```

于是系统会逐渐从：

> AI Agent

变成：

> **AI Agent + 自学习式 RPA Workflow Library**

这比单纯做一个 CUA Agent 更有产品价值。

---

# 18. 建议的技术栈

## Desktop Runtime

优先：

**Rust**

原因：

- Windows/macOS 双平台
- 原生 API
- 性能
- 单二进制
- 易于提供 Python / Node / Go FFI
- 适合做长期驻留 Desktop Runtime

参考：

```text
Rust
 ├── Windows UIA
 ├── macOS AXUIElement
 ├── Unified Element Model
 ├── Input
 ├── Window Management
 ├── Screenshot
 └── Workflow Runtime
```

## Element Schema

优先研究：

**CUP**

并考虑自己定义：

```text
UnifiedElement
```

例如：

```json
{
  "id": "e17",
  "platform": "windows",
  "role": "button",
  "name": "Submit",
  "value": null,
  "state": ["enabled"],
  "bounds": [100, 200, 120, 40],
  "actions": ["click"],
  "parent": "e3",
  "platform_data": {}
}
```

## Cross-platform native driver

第一选择：

**xa11y**

先不要重复造轮子。

## Agent Desktop Interface

参考：

**agent-desktop**

采用：

```text
snapshot
find
get
click
type
select
toggle
scroll
keyboard
window
```

这种 Agent-friendly API。

## Fast Decision

接：

**Jev**

原则：

```text
LLM = What / Why
Jev = Which Element / Which Action
Runtime = How
```

## High-level Agent

可以支持：

- OpenAI
- Claude
- Gemini
- 本地模型
- MCP Agent

不要把模型写死。

## Vision fallback

支持：

- Screenshot
- OCR
- VLM
- CUA

只有 Accessibility Tree 不足时才启用。

---

# 19. 推荐的 MVP

不要一开始做完整 UiPath。

第一阶段只做：

```text
Windows + macOS
       ↓
Native Accessibility Tree
       ↓
统一 Element Schema
       ↓
snapshot
       ↓
click
       ↓
type
       ↓
select
       ↓
keyboard
```

然后：

```text
Jev
 ↓
选择 Element
 ↓
执行 Action
```

最后：

```text
LLM
 ↓
Goal
 ↓
Jev Loop
 ↓
完成任务
```

---

# 20. MVP 验证任务

建议准备 10 个跨平台任务：

### 简单

1. 打开 Finder / Explorer
2. 打开应用
3. 点击按钮
4. 输入文本
5. 选择下拉框

### 中等

6. 创建一个文本文件
7. 在浏览器搜索
8. 在系统设置修改一个选项
9. 在 Excel / Numbers 修改单元格

### 复杂

10. 跨 App 完成一个完整业务流程

要求：

```text
同一个 Agent API
        ↓
Windows
        +
macOS
```

业务层完全不感知底层平台。

---

# 21. 最值得验证的技术问题

## P0

### 1. Windows UIA 与 macOS AXUIElement 能否形成统一 Element Model？

这是第一关键问题。

### 2. xa11y 是否已经足够作为底层 Runtime？

不要先开发，先 benchmark。

### 3. Jev 在 Element Tree 上的速度 / 成功率

重点测试：

```text
50 elements
100 elements
300 elements
1000 elements
```

以及：

- 正确 Element
- 多个相似 Element
- 动态列表
- 深层 Tree
- Tree 发生变化

### 4. Jev 是否适合做 Local Action Policy？

即：

```text
LLM → Task
Jev → Action
```

而不是：

```text
LLM → 每一步 Action
```

---

# 22. P1

### 5. Recorder 如何生成稳定 Selector？

### 6. Workflow 如何处理 UI 变化？

### 7. Element Tree 与 Screenshot 如何融合？

### 8. Accessibility 失败时什么时候切换 Vision？

### 9. LLM 如何恢复失败 Workflow？

---

# 23. P2

### 10. Agent → Workflow 自动固化

### 11. Workflow → Agent 自动修复

### 12. 多 Agent 并发控制

### 13. 权限 / Approval / Security

### 14. 企业级 Audit Log

---

# 24. 最终产品形态

如果最终做成产品，我认为可以不是：

> “另一个 UiPath”

而是：

## AI Native RPA / Computer Use Platform

```text
                   ┌─────────────────┐
                   │      User       │
                   └────────┬────────┘
                            │
                   Natural Language
                            │
                            ▼
                  ┌──────────────────┐
                  │  LLM / Planner   │
                  └────────┬─────────┘
                           │
                     Task / Subtask
                           │
                           ▼
                  ┌──────────────────┐
                  │       Jev        │
                  │ Fast UI Decision │
                  └────────┬─────────┘
                           │
                     Element + Action
                           │
                           ▼
                  ┌──────────────────┐
                  │ Unified Desktop  │
                  │ Runtime          │
                  └────────┬─────────┘
                           │
               ┌───────────┴───────────┐
               ▼                       ▼
          Windows UIA             macOS AX
               │                       │
               └───────────┬───────────┘
                           ▼
                      Native Apps
```

旁边：

```text
             Recorder
                 │
                 ▼
             Workflow
                 │
        ┌────────┴────────┐
        ▼                 ▼
 Deterministic         Agent
 Replay                Repair
```

底层再加：

```text
Accessibility
      ↓
OCR
      ↓
Vision / CUA
```

---

# 25. 当前推荐路线

## 第一优先级：直接验证

### ① NomiFun

目的：

> 看完整 Windows + macOS Computer Use 的实际体验。

重点观察：

- Windows UIA
- macOS AX
- Element Tree
- OCR
- Agent
- MCP
- Rust Runtime

---

## 第二优先级：拆底层

### ② xa11y

目的：

> 判断它能不能成为自己的 Native Desktop Runtime。

重点：

- Tree extraction
- Selector
- Actions
- Element identity
- Windows/macOS 差异
- 性能

---

## 第三优先级：研究 Jev

### ③ computer-use-jev / jev-desktop

目的：

> 把 Jev 变成“局部 UI Action Policy”。

核心验证：

```text
Element Tree
 ↓
Jev
 ↓
Action + Element
```

而不是让 Jev 负责整个 Agent。

---

## 第四优先级：研究统一协议

### ④ CUP

目的：

> 解决 Windows/macOS/Linux/Web 的 Element representation。

---

## 第五优先级：研究传统 RPA

### ⑤ OpenRPA / RPA.Windows

目的：

> 只借鉴 Recorder、Selector、Workflow、Replay。

不要把整个架构照搬过来。

---

# 26. 最终判断

目前最合理的技术路线不是：

```text
寻找一个开源 UiPath
```

而是：

```text
                  NomiFun
                    │
              产品 / UX 参考
                    │
                    ▼
             ┌────────────┐
             │  xa11y     │
             │ Element    │
             │ Runtime    │
             └─────┬──────┘
                   │
                   ▼
                  CUP
             Unified Schema
                   │
                   ▼
                  Jev
            Fast UI Decision
                   │
                   ▼
              LLM / Agent
           Global Planning
                   │
                   ▼
            Vision / CUA
              Final Fallback
```

同时吸收：

```text
OpenRPA / RPA.Windows
        ↓
Recorder + Workflow + Replay
```

最终形成：

> **Native Element-first + Jev-fast-decision + LLM-global-planning + Vision/CUA-fallback + Workflow-replay**

这是目前最符合目标的架构方向。

---

# 27. 下一步建议

### Step 1：先不写代码

先把下面 5 个项目实际跑起来 / 阅读源码：

1. `xa11y`
2. `NomiFun`
3. `agent-desktop`
4. `computer-use-jev`
5. `computeruseprotocol`

### Step 2：做一个最小 benchmark

统一测试：

```text
打开 App
读取 Tree
找到 Button
Click
输入文字
选择菜单
读取结果
```

分别测试：

```text
Windows
macOS
```

### Step 3：验证 Jev

让 Jev 只做：

```text
Input:
Accessibility Tree

Output:
{
  action,
  target,
  confidence,
  done
}
```

不要让它负责整个任务。

### Step 4：接 LLM

变成：

```text
LLM:
“完成采购订单”

       ↓

Plan

       ↓

Jev:
“下一步点哪个 Element？”

       ↓

Runtime:
执行

       ↓

Observation

       ↓

Jev

       ↓

...
```

### Step 5：最后做 Recorder

将成功的 Agent Trace：

```text
Observation
Action
Observation
Action
...
```

固化成：

```text
Workflow
```

于是系统天然拥有：

```text
Record
→ Learn
→ Replay
→ Repair
→ Agent fallback
```

这会是整个项目最有价值的一层。
