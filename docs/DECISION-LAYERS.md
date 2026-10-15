# 决策分工与实时日志

2026-10-15。结论：原 Planner → Jev → Driver 有实现和旧实测；当前桌面对话入口没有接入这条链路。不能将三个嵌套框解释为三个独立决策器已经在运行。

## 当前实际调用

| 入口 | 规划与动作选择 | 执行 | Jev 是否参与 |
|---|---|---|---|
| 桌面对话 | 同一个 Harness SDK 负责规划和工具选择 | Bokkio MCP → Runtime → Driver/作业/Workflow | 否 |
| Shortcuts 回放 | 保存的固定步骤，运行时重新定位并验证 | Runtime → Driver | 否 |
| 独立 `bokkio run` CLI | OpenRouterPlanner 规划子任务，Jev 选择局部动作和目标 | execute_decision → 原生 backend | 是，除 plan-only 模式 |

源码入口：`desktop_chat.py` 的 SDK 桥接、`cli.py` 的 DesktopAgent 构造、`agent.py` 的 make_plan/decide/execute_decision。当前 Runtime 是模型无关执行边界，没有自动调用 Jev。旧 CLI 的三层记录不能作为当前桌面对话已经启用 Jev 的证据。

## 界面中的三层嵌套

对话：任务/规划（Harness）→ 工具选择（Harness）→ 执行与验证（Runtime/Driver）。界面明确标出 Jev 未参与，三层代表职责与证据层级。任务根节点显示会话状态；完成检查以驱动及 Workflow 的验证结果为准。

Shortcuts：Workflow → 固定步骤（含轮次）→ 观察、定位、动作和验证回执。根节点标明没有调用 Planner/Jev。录制仍是操作录制，本次没有恢复视频功能。

日志可展开/收起；运行中及失败节点默认展开。分别显示失败、拒绝、排队、取消、结果未知、执行已返回和读回验证通过。工具返回事件本身不证明操作成功。

## 日志证据与关联

- L2 来自公开 SDK `tool/call` 与 `tool/result`，持久保存 call_id、工具名、目标摘要、operation_id 和返回状态；不生成或展示模型隐藏推理。
- L3 来自 Runtime SQLite 操作与事件，带实际 operation_id、状态、是否派发、时间、耗时和错误。
- 父操作使用 ContextVar，并在 Workflow 工作线程中显式复制上下文；代码子作业继续使用已有 BOKKIO_PARENT_OPERATION。
- Workflow 请求携带 run_id、step_id、cycle，才能准确归入具体步骤；上下文在退出、异常和暂停后恢复。
- 通过真实 ID 与会话/task_id 关联，不按时间或工具名猜父子。未关联的记录单独标明，待明确 ID 返回后归位。
- 同一 operation_id 被多次引用会显示共享回执，不当作再次派发。取消后的最终作业状态会更新到对应组。
- 原始通知窗口裁剪不会删除已归档的工具选择摘要；完整执行记录仍在审计库。多任务之间不混入其他会话日志。

本次增加的是可观测性，没有重新接入 Jev、替换 Harness 的 agent loop 或改变执行策略。恢复独立局部决策器需要实际接线和另行实测，不能由日志 UI 代替。

## 实测

见[本轮分层日志报告](evidence/2026-10-15-layered-logs/README.md)。本轮还发现并修复 Mac 环境/安装包缺少 Harness SDK 的问题；打包现在必须在被打包的 Python 内成功导入 SDK 与 runtime 包。安装版用真实模型和 MCP 调用验证 SDK 可运行。
