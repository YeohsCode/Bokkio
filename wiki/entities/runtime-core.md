---
title: "Computer Use Core：会话、执行与审计"
created: "2026-10-13"
updated: "2026-10-13"
type: "entity"
tags: ["architecture", "runtime", "safety", "evidence"]
sources: ["src/bokkio/runtime.py", "src/bokkio/mcp_server.py", "src/bokkio/tool_schema.py", "src/bokkio/runtime_cli.py", "src/bokkio/audit.py", "docs/CAPABILITY-MODULES.md", "src/bokkio/capability_registry.py", "src/bokkio/executor.py", "src/bokkio/runtime_workflow.py", "src/bokkio/model.py", "docs/progress/STATUS.md", "docs/RUNTIME-GUIDE.md"]
confidence: "high"
---

# Computer Use Core：会话、执行与审计

Runtime是0.2.0的统一执行边界。MCP、CLI、SDK均调用Runtime.call；底层Xa11yBackend只负责原生树与动作。Core不调用模型，业务规划仍由外部Harness承担。^[src/bokkio/runtime.py#L61] ^[src/bokkio/mcp_server.py#L31]

## 公共接口与路由

工具集合和输入合同在runtime.TOOLS／tool_schema.SCHEMAS中定义；审批批准不作为Agent MCP工具公开，由本地管理员CLI／AuditStore.decide处理。^[src/bokkio/runtime.py#L21] ^[src/bokkio/tool_schema.py#L14] ^[src/bokkio/runtime_cli.py#L41]

| 方法／模块 | 职责 |
|---|---|
| call / _finish | 请求认领、哈希、校验、审批、意图与结果持久化 |
| _session / _app / _path | OS身份、TTL、进程出生身份、窗口／文件范围 |
| _observation / _get_observation | 会话观察与15秒时效 |
| _native_call / _dispatch_scope | 专用原生线程、锁后资源重验 |
| _execute | 原生／像素／Browser／代码、模块／Workflow与证据路由 |
| AuditStore / executor | 私有SQLite、审批与审计、持久作业／取消／worker身份 |

依据：^[src/bokkio/runtime.py#L183] ^[src/bokkio/runtime.py#L390] ^[src/bokkio/audit.py#L54]

## 授权与数据

默认apps/paths/origins/modules、写和trusted_host拒绝；Session不能扩大管理员策略。应用绑定PID和出生身份；新版受控desktop.launch可按精确安装身份启动并更新绑定。修改策略文件后重启MCP服务，已启动代码worker使用委派会话策略。^[src/bokkio/runtime.py#L62] ^[docs/CAPABILITY-MODULES.md#L30]

sessions、operations、approvals、events、artifacts等保存在私有SQLite，PNG／完整观察和作业文件保存在私有目录。事件只保存形状、长度、哈希等摘要；请求正文仍是本地私有记录。^[src/bokkio/audit.py#L43] ^[src/bokkio/audit.py#L61]

## 可选模块与新版Workflow

模块摘要／合同发现只读元数据；capability.invoke检查模块／路径／write／trusted_host、版本／源码／依赖与合同SHA，进入原有精确审批和executor作业。output结构化证据缺失或绑定不符保持unknown。^[src/bokkio/capability_registry.py#L55] ^[src/bokkio/executor.py#L238]

新RuntimeWorkflow保存版本与精确子操作检查点；workflow.*在Core启动Runner，后续每个子动作仍经SDK回到Core。旧workflow.py直接backend回放保留历史入口。^[src/bokkio/runtime.py#L405] ^[src/bokkio/runtime_workflow.py#L161]

## 返回事实与限制

读请求completed、已执行写请求executed、确认后置条件verified、code/process/capability提交queued。必须继续查询作业终态与模块output；进程exit0或外层completed不证明业务目标达成。^[src/bokkio/runtime.py#L276] ^[src/bokkio/executor.py#L270]

backend明确未派发的禁用目标等拒绝通过BokkioActionRefused携带dispatched=false；派发后失去回执仍保持unknown。真实Numbers编辑提交／保存尚未复核。^[src/bokkio/model.py#L31] ^[docs/progress/STATUS.md#L15]

trusted-host不是OS沙箱；同用户任意宿主代码可影响本地资源，取消不可撤销副作用，幂等记录不保证GUI exactly-once。客户／双平台支持范围以独立验收为准。^[docs/RUNTIME-GUIDE.md#L30]

关联：[[summaries/architecture-map]]、[[summaries/module-call-map]]、[[concepts/runtime-contracts]]、[[entities/native-runtime]]、[[entities/capability-modules]]、[[entities/runtime-workflow]]、[[summaries/current-status]]。
