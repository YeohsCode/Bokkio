---
title: "Computer Use Core：会话、执行与审计"
created: "2026-10-13"
updated: "2026-10-13"
type: "entity"
tags: ["architecture", "runtime", "safety", "evidence"]
sources: ["src/bokkio/runtime.py", "src/bokkio/tool_schema.py", "src/bokkio/runtime_cli.py", "src/bokkio/audit.py", "src/bokkio/executor.py", "src/bokkio/browser_driver.py", "docs/RUNTIME-GUIDE.md", "docs/progress/STATUS.md"]
confidence: "high"
---

# Computer Use Core：会话、执行与审计

`runtime.Runtime` 是 0.2.0 新边界；MCP、CLI、SDK 将工具请求交给 `call()`，由 Core 验证、审批、分派和记录。底层 `Xa11yBackend` 只负责原生树与动作，二者不是同一个层级。^[src/bokkio/runtime.py#L58]

## 公共接口

API schema 为 `bokkio.runtime.v1`；工具名与输入 schema 分别在 runtime.TOOLS 和 tool_schema.SCHEMAS 定义。审批批准没有 Agent MCP 工具，只通过本地管理员 CLI / AuditStore.decide。^[src/bokkio/runtime.py#L21] ^[src/bokkio/tool_schema.py#L14] ^[src/bokkio/runtime_cli.py#L61]

| 方法 / 协作模块 | 职责 |
|---|---|
| call / _finish | operation_id 认领/请求哈希、参数/范围校验、审批、意图和结果持久化 |
| _session / _app / _path | OS 用户/TTL、应用进程创建身份/精确窗口、会话与当前策略的文件根目录 |
| _observation / _get_observation | Session 范围的原生或像素观察，15 秒时效 |
| _native_call | 单线程 native backend 调用；输入派发前核验 session/资源 |
| _dispatch_scope | 桌面锁取得后重新校验，变化时零派发拒绝 |
| _execute | 原生/像素/代码/Browser 与证据/日志的路由 |
| AuditStore | 私有 SQLite、请求与事件、审批决定、摘要查询/导出/统计 |
| executor | 持久 job，独立 worker、子进程身份、取消与 worker_lost 核对 |

依据：^[src/bokkio/runtime.py#L178] ^[src/bokkio/runtime.py#L165] ^[src/bokkio/audit.py#L54]

## 数据与授权

SQLite 保存 sessions、operations、approvals、events、artifacts、observations，按需创建 jobs 与 browsers。PNG/完整原生 snapshot/作业文件存在私有目录；artifact 元数据记录 session、operation、SHA-256、MIME、字节数，读取时再次验证哈希。^[src/bokkio/audit.py#L61] ^[src/bokkio/runtime.py#L77] ^[src/bokkio/executor.py#L19] ^[src/bokkio/browser_driver.py#L26]

管理员策略默认拒绝 apps/paths/origins、写与 trusted-host；Session 不能扩大策略应用列表或 TTL。app 绑定 PID 和进程出生身份，应用重启必须重新开 Session。现有进程的 policy 是内存配置，修改 JSON 后应重启 MCP 服务；跨进程共享同一目录不构成远程服务。^[src/bokkio/runtime.py#L61] ^[docs/RUNTIME-GUIDE.md#L32]

## 返回结果的解释

读工具成功返回 completed；原生后置检查 confirmed 时写操作可返回 verified，其余已执行写操作返回 executed；code/process 提交返回 queued。作业需看 `job.get.result.status` 与输出；worker 最终结果也更新原操作回执。CLI exit 0 或外层 completed 都不能替代业务验收。^[src/bokkio/runtime.py#L271] ^[src/bokkio/executor.py#L244]

审计区分逻辑操作、请求尝试、缓存、拒绝、派发及审批等待；业务成功率与模型费用没有相应输入时为 null。请求正文存本地私有 operations，常规 events/export 只导出形状、长度和哈希等摘要。^[src/bokkio/audit.py#L43] ^[src/bokkio/audit.py#L126]

## 当前限制

trusted-host 代码可直接操作宿主文件/UI/网络；cwd 路径检查不是 OS 沙箱。同用户任意宿主执行可影响本地审批/审计，需更强隔离时应另建 worker/服务身份。取消不可撤销副作用，幂等记录不保证 GUI exactly-once。未知结果和禁用目标的保守分类缺口见最新状态。^[docs/RUNTIME-GUIDE.md#L30] ^[docs/progress/STATUS.md#L34]

关联：[[summaries/architecture-map]]、[[summaries/module-call-map]]、[[concepts/runtime-contracts]]、[[entities/native-runtime]]、[[summaries/current-status]]。
