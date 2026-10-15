# 决策分工与实时日志

2026-10-15。桌面对话支持按配置开关 Jev：启用时 Harness 全局规划 → Jev 原生界面局部决策 → Runtime/Driver 执行及读回；关闭时 Harness 同时选择动作与控件，直接调用 Runtime。

## 实际调用

| 入口 | 规划与动作选择 | 执行 | Jev 是否参与 |
|---|---|---|---|
| 桌面对话的新原生 UI 操作（Jev 开启） | Harness 拆分局部目标；`desktop.step` 调用 Jev，从当前控件树选择动作和目标 | 相同的 Runtime 会话内观察、派发、读回 | 是，以真实 decision.requested/returned/selected 事件为证 |
| 桌面对话的新原生 UI 操作（Jev 关闭） | Harness 规划并选择动作与控件 | 原有 Runtime MCP → Driver | 否，不加载 Jev 或要求其凭证 |
| 桌面对话的读取、文件、代码、浏览器工具编排 | Harness 选择对应工具 | Runtime 对应执行器 | 不强制经过原生 UI 决策器 |
| Shortcuts 回放 | 保存的固定步骤，运行时重新定位并验证 | Runtime → Driver | 否 |
| 独立 `bokkio run` CLI | OpenRouterPlanner → Jev | 原有 execute_decision → backend | 是，除 plan-only |

Jev 开启时，桌面对话的 MCP 入口是 `desktop_decision.py`。它在模型无关 Runtime 外组合已有 `decision.decide` 与 JevProvider，保留 Harness SDK 原有循环。没有启用另一套 agent loop，也没有把旧 CLI 的直接 backend 执行接到桌面入口。

## 一次局部步骤

1. Harness 提供 app、精确 window、局部 goal 和 allowed_values，不指定 ref。
2. 观察真实窗口，把完整原生树留在本机，并以现有闭集决策格式交给 Jev。
3. Jev 选择原生动作、控件和允许值，返回置信度。键盘、右键、拖动等显式输入可由 Harness 提供 input 参数，Jev 选择当前控件目标。
4. 再观察一次，刷新观察有效期；语义树变化则不派发，返回 Harness 重规划。
5. 相同会话通过 Runtime desktop.act / desktop.input 执行，沿用原生线程、锁、检查和持久回执；随后读回。
6. Harness 根据真实读回继续任务。输入回执与任务业务成功分开；Jev 故障或低置信度不会自动降级为 Harness 直接点控件。

Jev 开启时，桌面对话 MCP 公布 desktop.step，底层动作接口留给执行器和固定 Workflow。代码/进程能力保留用于文件和数据任务，提示模型不通过代码绕过原生 UI 决策；这不是代码沙箱。

每个 desktop.step 有持久 operation_id；重复或并发请求不会重新调用模型或再次派发。进程中断留下的未完成步骤返回 completion_unknown，须先查审计；已知原生派发结果不会被后续读回失败抹掉。Jev 返回后及派发时重新检查会话，停止后的任务不能继续输入。

## 配置

配置页提供“启用 Jev”开关（默认开启）、服务预设/自定义、完整 API URL、模型名称和独立 Key。选择预设会填入其 endpoint 与默认模型，URL 和模型均可修改。自定义 URL 接受 HTTP(S)，请求使用 Jev Decisions 的 model/state/questions 协议；不自动追加路径。

保存开关后从下一任务生效，每个任务保留启动时的模式；切换配置不会改写历史日志或在运行中更换决策器。关闭模式使用原有 runtime_cli --local serve，公布 desktop.act/input/pixel，不加载 Jev，不要求 Jev URL/模型/Key。

独立 Jev Key 优先。本机配置或环境变量密钥只用于匹配的 endpoint；规划模型的 OpenRouter Key 仅共用到其官方 Decisions 地址。自定义新地址需要对应 Key，避免把其他服务的凭据转发到新主机。loopback 接口直连，不经过系统 HTTP 代理。

Electron 用系统 safeStorage 分开保存规划与 Jev 密钥；服务内仅保留内存副本，普通配置 JSON 和 Harness patch 不包含密钥；Harness patch 使用 SDK 的 !!js 环境变量引用，显式传递给 MCP 子进程，避免 SDK 的环境清理把独立 Key 丢弃。macOS/Windows 使用相同设置 UI，各自连接同一套 Python 接口与原生适配器。

## 三层嵌套日志

- L1：Harness 任务及会话状态。
- L2：启用时为真实 Jev 决策，显示模型、选中动作、ref、置信度、请求/返回/失败事件；关闭时原生工具标为 Harness 动作选择；读取、文件等工具标为 Harness 编排。
- L3：该决策下的 Runtime 观察、动作、读回，显示实际操作 ID、状态、是否派发和耗时。

Jev 节点直接来自审计事件，在 SDK 最终回执到达前即可显示；SDK call_id 返回后通过 operation_id 关联。只有发出真实 Jev 请求才把本任务 jev_active 标为 true，纯读取与固定 Workflow 仍显示零次。UI 不展示模型隐藏推理，不按相邻时间猜关系。

固定 Shortcuts 仍显示 Workflow → 固定步骤/轮次 → 执行验证。父操作通过 ContextVar、线程上下文和已有代码作业环境传递。缓存回执不作为再次派发，取消或中断后不把未返回的决策一直显示为运行中。

## 实测

本次接线报告见 [Jev 桌面对话实测](evidence/2026-10-15-desktop-jev/README.md)。此前 [日志专项报告](evidence/2026-10-15-layered-logs/README.md) 是接通 Jev 之前的冻结记录。

Jev 开关、自定义 URL/Key/模型与重启实测见[配置与模式测试](evidence/2026-10-15-jev-options/README.md)。

全局模型默认观察为 60 节点 / 16 KB，Jev 的本机完整树不受该返回预算影响，完整快照继续留为 artifact。非法 expected_value（非 type）在派发前明确拒绝，SDK 无可见最终答复时标为失败，避免空回复被当作任务完成。
