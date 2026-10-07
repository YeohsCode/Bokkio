# P6：原生录制与确定性 Workflow / Native recording and deterministic workflows

日期：2026-10-05。P6 已完成 Windows 验收，P7 可开始；以原生 Element + Action 为中心，v1 负责固定动作，v2 增加参数、文件版本与可恢复重放。

## 实现

- `Recorder` 包装显式原生操作，记录目标上下文、前后快照、Runtime 回执和验证。点击需要调用方提供业务验证条件；文本、选择和展开可从原生回执取得条件。首版 type 重放要求空字段，避免依赖未录制的光标位置；替换文字使用 set_value。自动验证使用操作要求达到的值：focus/select/expand 为 true，collapse 为 false，文字采用请求的读回值；不能把失败后的实际状态反过来定义为成功。录制失败不会生成成功 Workflow。
- `from_agent_trace` 从已完成 Agent trace 生成 `bokkio.workflow.v1`。观察、决策、目标 ref、动作与新观察必须对应；只保留当前需求版本，未完成或无法验证的动作拒绝固化。
- Workflow 包含 intent、action、target、literal arguments、wait、verify、步骤依赖、来源和版本。内容 SHA-256 防止误改；不把 PID、HWND 或 UIA RuntimeId 固化为跨进程选择器。原生 ref 保留为提示，实际 app alias 在每次重放时显式绑定。
- `WorkflowReplay` 不调用模型。每步先读取新快照，解析 ref / role + name + 完整父级与窗口上下文，再让 Runtime 校验快照后执行。重复同名候选不取第一项，旧 ref 也不能绕过上下文或歧义检查。
- 等待和验证重试有时间上限（默认 5 秒，最多 30 秒）。派发异常可能已产生效果，因此记录未知完成并停止，不重复输入或点击。每步记录快照、解析路径、回执和验证；失败定位到 step ID。
- `repair_version` 保留失败版本，生成带 parent hash 的新版本；`request_repair` 可把失败点、错误与失败时最后一次原生快照交给 Jev/Planner 适配器提出修复。提案必须通过相同 schema 与应用范围验证，重放由调用方显式启动。
- 录制入口包括显式语义 API、成功 Agent trace，以及 `capture_receipt`：接入原生客户端已经执行的动作，核验前观察、回执和当前后观察，捕获时不二次派发。全局人工键鼠监听保留为后续可选入口。POSIX 新文件使用 0600 权限，Windows 继承目标目录 ACL，Workflow 中的文字和路径仍需要按实际用途审查。

## 命令

启动一次性 Windows interactions fixture 并取得 PID，保持 Search 为空。以下示例记录五步原生动作；录制后为每次重放启动相同初始状态的新 fixture，再绑定新 PID。

```powershell
bokkio workflow record --actions fixtures/workflows/interactions.actions.json --bind fixture=1234 --name "Native interactions" --output workflow.json
bokkio workflow replay --workflow workflow.json --bind fixture=5678 --output replay.json
```

从成功 trace 固化；左侧为 trace 中的授权 app，右侧为可重绑的 Workflow alias：

```powershell
bokkio workflow compile --trace completed-trace.json --bind 1234=notepad --name "Save draft" --output workflow.json
bokkio workflow replay --workflow workflow.json --bind notepad=5678 --output replay.json
```

修复保留原文件；`replacement-steps.json` 为审查后的完整步骤数组：

```powershell
bokkio workflow repair --workflow workflow.json --run failed-run.json --steps replacement-steps.json --reason "Update selector from fresh native observation" --output workflow-v2.json
```

编译、参数化和提交已审查修复可离线进行，不构造 native provider。模型修复只调用模型并生成版本。录制和重放经由操作系统原生辅助功能层。

## 验证范围

Windows 验证脚本：`scripts/verify_p6_windows.py`。它从真实 P5 成功 trace 编译保存 draft 的 Workflow，录制 click/type/select 及跨应用写入，并在新进程上重复同一份 JSON。每轮重放另查原生业务状态；保存文件核验字节并用新进程重开。失败版本与修复版本同时保存。初版 v2 的原生结果：

| 检查 | 原生结果 |
|---|---|
| 录制六步：focus/type/click/expand/select＋Notepad 写入 | 6 个语义动作，完整前后观察与回执 |
| 同一录制 JSON 重放 | 3/3；每轮 6 个派发，6 个目标通过上下文恢复；独立业务状态全部通过 |
| 真实 P5 成功 trace 编译与重放 | 3/3；每轮 5 个派发；16 字节 draft、SHA-256 与原产物一致，新进程重开通过 |
| 故意破坏选择器 | 第一步失败，0 个派发 |
| 生成 revision 2 后重放 | 通过；保留失败版本及 parent hash |

v1 的部署预检缺少 trace 样例，0 个原生任务开始；修正打包后运行 v2。之后增加空字段 type 约束并处理 P5 的原生边界读取崩溃；v3 定向复核：录制 Workflow 重放 **1/1**（6 次派发、6 次上下文恢复、3 项独立检查均通过）；v16 成功 trace 固化后重放 **1/1**（5 次派发、16 字节产物及新进程重开均通过）；失败选择器仍为 0 派发，revision 2 修复重放通过。v3 的执行源码哈希保留；后续 checked 歧义恢复与录制无效果验收修复后，使用 v4 重新完成最终代码三次重放，各轮分母分别保留。完整证据见 [归档索引](evidence/2026-10-05-p6-workflow/README.md)。

### 首版最终代码 v4（历史结果）

| 检查 | 结果 |
|---|---|
| 六步跨应用录制与同一 JSON 新进程重放 | **3/3**；每轮 6 个派发、6 个上下文恢复、3 项独立业务检查均通过 |
| 真实 v16 Notepad 成功 trace 固化与重放 | **3/3**；每轮 5 个派发、16 字节与 SHA-256 一致，新进程重开通过 |
| 错误选择器 | 0 派发，结构化失败 |
| revision 2 修复重放 | 通过，原版本与 parent hash 保留 |
| 隔离回归 | macOS 主机 265/265；Windows 虚机 265/265 |

v4 的六个执行源码哈希对应首版验收代码；本轮扩展修改了 workflow、CLI 和 backend，当前代码另做原生验收。它包含最新 checked 条件歧义恢复及“动作无效果不能生成成功录制”修复，未把旧代码的重复次数计入最终代码结果。所有重放不调用模型；P5 trace 仍来自真实 Planner/Jev 运行。此表为开发环境原生验收，不是官方 benchmark 分数。

隔离测试覆盖新 PID/ref、歧义、父级改变、等待、验证、未知完成、暂停/取消、篡改、应用边界、成功 trace 编译及新版本修复。它们不能替代真实桌面验收。

## v2 参数与文件版本

`parameterize` 从审查过的 JSON pointer 位置生成新版本。参数为完整字符串替换，类型为 `string`、绝对 `path` 或 `sha256`；限制长度，必须提供全部声明参数，额外字段与 NUL 拒绝。可参数化文本值、名称、父节点名称和文件路径/哈希，不能参数化 app、action、risk 或 ref。

```powershell
bokkio workflow parameterize --workflow workflow.json --spec parameter-spec.json --output template.json
bokkio workflow replay --workflow template.json --parameters values.json --bind explorer=1234 --bind notepad=5678 --window-bind explorer=hwnd:0xabc --output run.json
```

`parameter-spec.json` 包含 `parameters`、`slots`、`inputs`、`deliveries` 四个字段。例：

```json
{
  "parameters": {"body": {"type": "string", "max_length": 4000}},
  "slots": {"/steps/0/arguments/value": "body", "/steps/0/verify/0/equals": "body"},
  "inputs": [],
  "deliveries": []
}
```

这些 pointer 必须对应实际 Workflow 的字符串位置。文件合约为 `{"id":"source","path":{"param":"source_path"},"sha256":{"param":"source_hash"}}`，相应参数需在 `parameters` 声明；也支持固定绝对路径和哈希。输入每步前及完成时重新校验，已有交付文件拒绝覆盖，输入不能同时作为输出；派发后记录产物版本，结束核验预期 SHA-256。合约证明字节版本，正文含义与业务正确性仍要独立验收。

## 跨进程恢复

原子保存的 `bokkio.workflow-run.v2` 包含模板、绑定值与检查点哈希，步骤回执和输入/产物版本。暂停或进程中断后，保持同一个模板、参数与应用 alias，重新绑定 PID/窗口：

```powershell
bokkio workflow replay --workflow template.json --parameters values.json --resume paused.json --bind explorer=1234 --bind notepad=9999 --window-bind explorer=hwnd:0xabc --output resumed.json
```

恢复检查源文件和已产生的交付物是否变化，并复核检查点最后状态中仍然成立的原生条件。已经被后续操作覆盖的历史中间状态保留在已验证回执中。完成步骤跳过；已存回执但验证中断的步骤只验证，不重复派发。未知派发、取消、失败检查点或被改动的参数不能自动恢复。

## 结构变化与模型修复

`target.fallback="named_context"` 是显式启用的结构变化策略：保留完整有名称的祖先顺序和窗口锚点，可跨过新增的无名容器；不同有名父节点或多候选仍拒绝。

```powershell
bokkio workflow repair --workflow template.json --run failed.json --model-repair --planner-model openai/gpt-4.1 --reason "Recover the observed Search field" --output repaired.json
```

`OpenRouterWorkflowRepair` 只在原生观察的有限候选中选择目标或拒绝，仅更换失败步骤的 selector。动作、参数、验证、应用范围和文件合约保持；生成 parent-linked 新版本后再单独重放。API 配置沿用仓库外的 Planner 配置。修复调用记录模型、usage 与耗时；重放本身不调用模型。

## 观察开销

Runtime 动作前仍重新读取并校验决策快照；动作后本就读取原生树。Workflow 复用这份刚生成的后观察作为首次验证，条件未成立时再新读取。隔离计数验收中每个常规动作由四次原生树遍历减为三次。此结果是遍历次数减少，不代表端到端耗时按相同比例减少。未提供后观察的 backend 继续使用独立快照。

扩展原生验收使用 `scripts/verify_p6_complete.py`，三组参数、一次跨进程恢复、无名容器变化和真实模型修复均通过；最终 v5 的录制重放 3/3、成功 trace 重放 3/3，以及失败轮次见 [P6 验收](P6-CLOSURE.md)。macOS AX 原生对照、全局人工输入监听和完整 benchmark runner 保留为平台/后续工作；Office 激活按既有要求暂缓。P7 顺序见 [P7 计划](P7-PLAN.md)。

## English

**P6 Windows acceptance is complete; P7 can start.** The runtime provides semantic recording, completed Agent-trace compilation and deterministic replay. Versioned workflows retain intents, actions, contextual selectors, dependencies, bounded waits and verification. App aliases are explicitly rebound; remembered refs cannot bypass context or ambiguity checks.

Workflow v2 adds reviewed whole-string parameters and input/output SHA-256 contracts. App scope, actions, risk and refs cannot be parameters. Sources are checked before each step and at completion; existing outputs are refused. Atomic checkpoints preserve the workflow and parameter hashes, native receipts and artifact versions. Resume rebinds processes, rechecks current outcomes, skips completed actions and verifies received actions without repeating them. Unknown dispatch completion cannot resume automatically.

`Recorder.capture_receipt` accepts actions already performed by a native client, checking the before/after observations without dispatching again. Optional named-context fallback permits unnamed wrappers while preserving named ancestors and the window anchor. The concrete OpenRouter repair adapter chooses from bounded native candidates, changes only the failed selector and creates a parent-linked version. Replay itself calls no model.

The first verification reuses the fresh tree already read after dispatch. Normal traversal count drops from four to three; unmet conditions continue to poll fresh trees. The Runtime still validates the decision snapshot immediately before dispatch.

Final native results:

- Core v5: 3/3 unchanged six-action recording replays and 3/3 real Notepad trace save/reopen replays; zero-dispatch failure and parent-linked repair passed.
- Closure v3: 3/3 parameter cases on one seven-step Explorer → Notepad → Explorer template; restart/resume dispatched only the remaining action.
- Native wrapper recovery, two client receipt captures and actual GPT-4.1 repair passed. Host and Windows each pass 292 isolated tests.

All failures and historical v1–v4 core results remain in their separate archives. See the [acceptance report](P6-CLOSURE.md), [closure evidence](evidence/2026-10-05-p6-closure/README.md) and [historical core evidence](evidence/2026-10-05-p6-workflow/README.md). These are development acceptance checks. macOS comparison, global input capture, paused Office activation and full upstream benchmark integration remain explicit follow-up work. The [P7 plan](P7-PLAN.md) starts with native-window capture and a custom-drawn visual fixture.
