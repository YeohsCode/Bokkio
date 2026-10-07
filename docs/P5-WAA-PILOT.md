# P5：固定五项 WAA 原生 pilot

日期：2026-10-05。当前已进入 **P6：原生 Recorder 与确定性 Workflow**，首版录制与成功 trace 重放验收见 [P6 报告](P6-WORKFLOW.md)。本报告保留 P5 的全部轮次与评分边界。

**最终同代码完整复测 v26、v27 各为 4/5，五项 Agent 均正常 completed，中间派发与新观察对账全部通过。** Documents 完整目标路径独立确认；原始标题期望 `Documents` 与实际 `Documents - File Explorer` 不一致，两轮都保留 0 分。此前崩溃、准备失败和同名控件歧义均保留；Settings 修复后三次定向复测各 1/1。原始 evaluator 未改分。两端各 **265 项隔离测试**通过。

## 范围与评分边界

执行的是此前预选的五题，身份与顺序见 [清单](benchmarks/windows-arena-pilot.json)。固定上游版本为 `6d39ed88c545a0d40a7a02e39b928e278df7332b`。原始任务 JSON、输入/gold 文件、MIT 许可和源码哈希放在 [bundle](../fixtures/waa-pilot/README.md)。

当前环境为 Fusion Windows 11 IoT LTSC ARM64、x64 Python 3.12.13，Planner 为 `openai/gpt-4.1`（low），Jev 为 `typesafe/jev-1.13`。任务使用独立可丢弃文件夹，替换上游 Docker 用户路径；Settings 初期通过注册表播种通知状态；v6 证明该值与系统缓存/UI 不一致，因此复测改为实际操作原生开关准备初始状态，回到 Settings 默认页后再交给 Agent。初始化派发单独记录，结束后恢复原生状态与原注册表值。这些都是 **adapted development runs**，不能与官方榜单直接比较。

`prepare_waa_pilot.py` 从固定 Git 对象导出原始 `DesktopEnv.evaluate` 函数体、所需 getter 和 metric。执行前核验 manifest、任务、资产和 evaluator 哈希；gold 仅交给独立 evaluator。两条 Notepad metric 按上游 AND 合并，`FAIL` 按上游规则计 0。文件不存在、内容不匹配和 grader 错误均保留在失败分母中。

Controller 用隔离文件读取、Win32 活动窗口标题、Shell COM Details 模式和注册表通知状态替代上游服务端传输。Postconfig 可重开交付文件并保存新进程原生快照。评分期望值保持原始任务定义。

## 逐步 Computer Use 适配

- `NativeArenaAgent.predict()` 暂停在待执行原生命令，不能自行派发；`step()` 仅接受完整匹配的请求，拒绝改写与重放。
- 每个实际派发各占一个 runner step；失败派发也单独记录。执行后读取新 UIA，再检查子任务状态。P5 阶段规划、恢复与预算留在同一个 worker 中。
- `WAAAgentAdapter` 实现固定上游 `lib_run_single.py` 实际使用的四元组返回值；`WAAEnvironmentBridge` 接入原生 action space 并委托原环境 reset/observations/evaluate。
- 已验证协议、取消/恢复和开发 harness；完整上游 HTTP/VM server runner 尚未运行。

## 全部轮次

“已记录尝试”包含准备失败；这些条目的 metric 为 null、原生派发为 0。中断未评分与未开始任务另列，不能视为完整评分轮次。

| 轮次 | 计划 | 已记录尝试 | 通过 | 说明 |
|---|---:|---:|---:|---|
| v1 | 5 | 0 | 未评分 | 第一题已执行 5 个原生动作并保存 draft；驱动中断，未进入独立评分，另四题未开始 |
| v2 | 5 | 5 | 1 | Explorer 标题后缀导致三题初始化失败；Settings 原生宿主进程绑定失败 |
| v3 | 5 | 5 | 2 | Details 修复；地址建议身份与 Copy 的静态成功条件阻断 |
| v4 | 5 | 5 | 3 | Settings 通过；目录导航和重复 Rename 仍失败 |
| v5 | 5 | 5 | 2 | 通知 UI 缓存与播种值不一致；地址只被选中而未提交，复制任务耗尽 24 动作 |
| v6 | 5 | 5 | 2 | 原生 Enter 导航成功，但精确标题评分为 0；复制反复导航后写 trace 失败；通知 UI Off 而注册表仍为 1 |
| v7 | 5 | 5 | 1 | 导航路径独立校验通过，标题评分仍 0；Notepad Save 低置信度阻断；复制已完成但重命名计划重复 Rename；通知初始状态修正后，模型重复导航而阻断 |
| v8 | 5 | 5 | 3 | Notepad、Details、关闭通知通过；目录路径与重命名文件已正确，但两题的 Agent 完成状态仍阻断 |
| v9 | 2 | 0 | 未开始 | guest 回归预检失败；新增样例需两次恢复，却使用了默认一次预算 |
| v10 | 2 | 2 | 0 | 初始化失败：harness 指定 5 次重规划，Runtime 上限为 3；无原生派发 |
| v11 | 2 | 2 | 0 | 导航 completed，独立路径通过，精确标题仍 0；复制正确，但已选文件被候选过滤排除，错误选择 Documents 导航项 |
| v12 | 1 | 0 | 未开始 | 新回归测试检出上述候选过滤冲突；guest 预检阻止派发 |
| v13 | 1 | 1 | 1 | 复制＋重命名定向通过；12 个派发、1 次重规划，目标字节与源文件一致，原文保持 |
| v14 | 5 | 5 | 4 | 五项 Agent completed；导航完整路径通过，原始精确标题仍 0 |
| v15 | 5 | 1 | 1 | 第二题执行 1 个动作后 native provider access violation，未评分；另三题未开始，不能视为完整一轮 |
| v16 | 5 | 5 | 4 | 改用 VARIANT 边界属性读取后五项 completed；原始标题评分仍 0 |
| v17 | 5 | 5 | 3 | 四项 Agent completed；Settings 绑定过早，准备失败、0 派发 |
| v18 | 1 | 1 | 0 | Settings 同名隐藏 CoreWindow 干扰准备；0 派发 |
| v19 | 1 | 1 | 0 | Notifications 页面未就绪；0 派发 |
| v20 | 1 | 1 | 0 | 原生导航尚未取得内容树；0 派发 |
| v21 | 1 | 1 | 0 | 单次通知 URI 启动仍只暴露后台框架；0 派发 |
| v22 | 1 | 1 | 0 | 准备已成功；2 派发关闭开关，面包屑与开关同名导致完成条件歧义 |
| v23 | 1 | 1 | 1 | 原生 focus 与父级约束修复后，2 派发 completed |
| v24 | 1 | 1 | 1 | 同代码 Settings 连续复测，2 派发 completed |
| v25 | 1 | 1 | 1 | 同代码 Settings 第三次复测，2 派发 completed |
| v26 | 5 | 5 | 4 | 最终代码完整复测：五项 completed，独立业务检查通过；仅原始标题 metric=0 |
| v27 | 5 | 5 | 4 | 同七个源码哈希连续完整复测，结果一致；无原生进程崩溃 |

全部原始结果与失败轨迹见 [证据](evidence/2026-10-04-waa-pilot/README.md)。v2–v4 的复制任务起始于 Desktop，v5 起按上游 config 改为 Documents；这些轮次不能视为完全相同环境上的连续稳定性验收。v1 的 COM 清理使用了错误的 VOID 调用包装，测试日志含线程警告；修正后回归无该警告。中断与此相关，但现有证据不足以证明驱动退出的唯一原因。

## 本轮修复

1. 规划窗口白名单取自同一次快照，减少一次完整 UIA 遍历并避免状态不一致。
2. Settings 内部 CoreWindow 与宿主窗口 PID 通过原生祖先关系绑定；不能仅凭名称放宽进程检查。
3. Explorer 原生动作定位使用最近 HWND。重复 WinUI 地址建议只有在 PID、RuntimeId 和能力一致时合并，不能仅凭名称/坐标去重。
4. `requires_action` 要求 Copy/Paste/提交等命令实际派发，防止静态选择状态提前“证明”命令完成。普通页面和已达到期望的开关仍允许原生状态验收。
5. 增加受限 `submit` 动作：只用于 Explorer 可写原生字段。发送 Enter 前核验拥有窗口、前台、焦点、PID、RuntimeId 与字段值；部分派发标记为未知完成，需重新观察。
6. 点击 Rename 后出现新可写字段时触发阶段规划，避免继续重复点击 Rename。通知初始状态由真实原生开关准备，避免只改注册表而未更新系统缓存。
7. 地址提交改变原生窗口而旧谓词未通过时，立即进入新阶段规划；不能继续追逐已清空的地址栏值。
8. 原生 inline editor 的名称、值和能力进入规划 progress；编辑框已打开时禁止计划再次点击 Rename。实际 Explorer 编辑器类为 `UIRenameTextElement`，在窗口/焦点/身份保护下支持 Enter。
9. 内联编辑器标记从每次原生规划观察中重新取得，错误恢复也保留该上下文；提交目标绑定唯一有 RuntimeId 的原生 filename editor，排除地址栏。重命名已实际完成后，规划需只读检查新行，不能再查找消失的旧名。
10. 目录导航不能以 window.focused 验收；合同验证拒绝该谓词，提交结果包含已派发地址与实际窗口标题。
11. 显式 Select 命令与原生 selected 条件绑定唯一文件行；要求实际派发时保留已选中行，避免因通常的幂等过滤而只剩同名目录导航。重复或不唯一的行拒绝派发。
12. 明确要求点击 Save/Open 按钮，且 Windows 经典对话框存在唯一匹配确认按钮时，收窄命令候选；仍核验新快照及置信度。Settings 初始化通过原生 Home 项返回起始页，避免 `ms-settings:` 保留旧页面。

### 历史完整轮次 v8

| 任务 | 原生派发步数 | Agent 状态 | 固定 evaluator | 独立业务证据 |
|---|---:|---|---:|---|
| Notepad 保存 draft | 5 | completed | 1 | 16 字节与 gold 一致；新进程重开 |
| 导航 Documents | 5 | blocked | 0 | Shell COM 按 owned HWND 确认完整隔离目标路径 |
| Details 视图 | 1 | completed | 1 | Shell COM 模式 4 |
| Copy＋Rename | 13 | blocked | 0 | 目标 `example_renamed.txt` 已落盘，6 字节与源文件完全一致；原文保持 |
| 关闭通知 | 2 | completed | 1 | 主开关 checked=false，注册表 ToastEnabled=0；原生及注册表状态恢复 |

严格评分 **3/5**。导航和重命名的业务结果已达到，但 Agent 没有正常完成，两题按上游 FAIL 规则计 0，不能算通过。v7 导航曾 completed，但因期望 `Documents`、实际标题 `Documents - File Explorer` 给分 0；v8 的 0 分还涉及完成判断阻断，不能全部归因于标题后缀。

有效原生轮次使用 24 动作、3 次重规划、8 阶段的预算，合同修复与运行恢复共享预算。v10 尝试配置 5 次重规划，被 Runtime 拒绝，未派发；随后恢复原预算并增加 harness 预算兼容性测试。定向复测的选择与分母另记。

## 回归与诊断边界

最新 macOS 与 Windows 各 265 项隔离测试通过，覆盖逐步派发/取消/恢复、上游返回协议、原生身份去重、命令派发要求、Enter 的焦点/身份/字段变化拒绝、部分输入派发和状态转换规划。真实原生测试另计，不能用隔离测试数量证明五题完成。

v6 的复制 trace 出现持久化错误；当时工具正在拷贝运行中的大 trace，可能占用 Windows 文件替换句柄。现有错误隐藏了底层 I/O 码，无法断言唯一原因。后续不再在线拷贝活动任务的大 trace，待 result 落盘后收集。保留该轮失败；checkpoint 锁恢复的既有独立测试仍通过。

### 最终定向复测

- **v11 导航：** 3 次原生派发，Agent completed；owned HWND 的 Shell COM 目录路径与本题完整 Documents 路径一致。原始标题 getter 返回 `Documents - File Explorer`，与期望 `Documents` 不一致，metric=0。
- **v13 Copy＋Rename：** 12 次原生派发、1 次重规划，Agent completed，metric=1；每次成功派发后有新观察，step/trace 对账通过。`Documents/example_renamed.txt` 为 6 字节，SHA-256 `95a2f1edb08a76120b82cec7c93ca477618639f04beac7d2aeba2dc039d43715`，与原文一致。总耗时 320.906 秒，其中 UIA 238.996、Planner 22.828、Jev 28.532 秒。
- v13 的七个执行源码哈希保留；后续边界读取补丁更改 Windows UIA 代码。此前失败、初始化错误及预检失败均保留，详见 run/failure index。未将定向复测合并成完整一轮成绩。

## 原生读取崩溃与修复后复测

v14 五项均 completed，严格 4/5。连续的 v15 在第二题 set_value 后的新观察中退出，Windows 进程码为 `0xC0000005`；诊断栈最后位于 `WindowsUIA._element` 的 `CurrentBoundingRectangle` 调用。第一题已评分通过，第二题只有 1 个成功派发且未评分，第三至五题未开始。原始部分 summary、派发、trace 和 native stack 均保留，不能按完整一轮报告。

补丁通过 `GetCurrentPropertyValue(UIA_BoundingRectanglePropertyId)` 的 VARIANT 数组取得 left/top/width/height，保留精确边界、进程、类型、名称和类检查。对非四项数组、非有限数值和超出 4096 候选的读取拒绝定位，避免继续接受不完整原生身份。旧 struct-return getter 不再调用。诊断定位了发生异常的调用；现有证据不证明 emulation、provider 或 COM marshaling 中的唯一根因。

修复后的 v16 完整记录如下。v17–v25 的准备与验收问题及分母另列，最终完整复测继续保留原始标题评分。

| 任务 | 派发 | Agent | 原始 metric | 独立结果 |
|---|---:|---|---:|---|
| Notepad draft | 5 | completed | 1 | 16 字节与 gold 一致，新进程重开 |
| Documents 导航 | 3 | completed | 0 | owned HWND 的完整 Documents 路径一致；精确标题差异 |
| Details | 1 | completed | 1 | CurrentViewMode=4 |
| Copy＋Rename | 12 | completed | 1 | 6 字节与输入一致，原文保持 |
| Notifications | 2 | completed | 1 | 关闭通知并恢复原生和注册表初始状态 |

## Settings 准备与同名控件验收

v17–v21 的失败发生在 Agent 之前；错误有各自分母，不能归为成功或省略。Settings 同时暴露隐藏 CoreWindow 与可见 ApplicationFrameWindow；caption 出现早于 UIA 注册。准备现仅绑定唯一可见、已注册且 HWND/PID 再核验仍存活的宿主。只启动一次通知 URI，并给仅暴露框架的窗口一次原生 focus，等待真实开关；不以注册表写值代替原生准备。

v22 证明准备修复有效，但 Notifications 面包屑按钮与真正开关同名，宽泛的 role/name 条件产生两个候选。关闭开关后仍 blocked。Runtime 现在遇到 checked 条件歧义会先交回 Planner，提供真实父级与状态；Planner 使用开关的实际 immediate parent_name。保留唯一候选要求，避免重点击已经关闭的开关。v23、v24、v25 各 1/1，均为 2 派发、正常 completed；源码哈希相同。原生与注册表初始状态分别恢复。

## 最终同代码完整复测

| 任务 | v26 派发 | v27 派发 | Agent 状态 | 两轮原始 metric | 独立结果 |
|---|---:|---:|---|---:|---|
| Notepad draft | 5 | 5 | completed | 1 | 16 字节与 gold 一致，新进程重开 |
| Documents 导航 | 3 | 3 | completed | 0 | owned HWND 完整目标路径一致；标题后缀差异 |
| Details | 1 | 1 | completed | 1 | CurrentViewMode=4 |
| Copy＋Rename | 12 | 12 | completed | 1 | 目标 6 字节与输入一致，原文保持 |
| Notifications | 2 | 2 | completed | 1 | 开关关闭、注册表为 0；两种初始状态均恢复 |

两轮各自为 4/5，不合并分母。全部成功派发后读取新原生观察；runner step、trace 与独立评分对账通过。七个执行源码哈希一致并与该轮 P5 代码匹配。后续 P6 增加 CLI 与 backend 的可选后观察返回，P5 分数保留为该源码版本结果。Settings 三次定向通过属于另外三轮。

## 当前限制与后续工作

原始精确标题评分保留为 0；它与路径和 Agent 完成检查分别记录。P6 已进入并通过初版原生录制、三次新进程重放、真实 trace 固化及版本修复验收。完整上游 server runner 和 x64 官方环境对齐继续作为 benchmark 集成工作，不把改分当作完成。Office 激活按用户要求暂缓；2026-10-05 的 macOS 自有 fixture 对照仍返回嵌套 application，保留原生 provider 待办。

## English

Final consecutive full rounds v26 and v27 each scored **4/5**, with all five agents completed and native intermediate checks reconciled. The full navigation path passed independent verification; the original exact-title metric remains zero in both rounds. Earlier interrupted, setup and ambiguous-completion failures remain archived. Settings passed three separate targeted confirmations after visible UIA-root binding, native focus and exact-parent verification fixes. All seven executed P5 source hashes identify those rounds. Later P6 changes extend the CLI and add opt-in post-action observations in the backend; these P5 scores remain tied to their archived source revisions. Host and Windows passed **265 isolated tests** at that stage.

The original five WAA pilots are now exercised with a stepwise native action adapter and an independently pinned evaluator. Each dispatch consumes one runner step; predictions cannot execute, and altered/replayed requests are rejected. Phase planning and recovery remain in the worker. The adapter implements the upstream runner's four-value prediction contract and provides a native environment bridge. Full upstream HTTP/VM server execution remains pending.

These Fusion ARM64 runs adapt paths, setup and controller transport and are development results. Original task expectations and the upstream evaluator body remain pinned; internal completion cannot replace external scoring. All failures, interrupted/unstarted tasks, intermediate native observations, component timings and artifact bytes are retained. Versioned rounds use different fixes and some setup differences, so combined successes are not a single passing full round.

P6 recording and deterministic replay are implemented and exercised. Broader benchmark integration, Office activation and macOS native-read acceptance remain separate pending work; official task expectations are preserved.
