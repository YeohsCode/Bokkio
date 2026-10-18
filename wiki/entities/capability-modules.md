---
title: "能力模块：发现、接口定义与Office文件实现"
created: "2026-10-13"
updated: "2026-10-18"
type: "entity"
tags: ["architecture", "runtime", "office", "safety", "evidence"]
sources: ["src/bokkio/capability_registry.py", "docs/CAPABILITY-MODULES.md", "src/bokkio/modules/office_xlsx_contract.py", "src/bokkio/executor.py", "src/bokkio/modules/office_xlsx.py", "docs/evidence/2026-10-13-capability-modules/README.md"]
confidence: "high"
---

# 能力模块：发现、接口定义与Office文件实现

当前实现为一个本地静态注册的可选office.xlsx模块，默认关闭。外部Harness负责规划和业务验收；Registry提供摘要、完整接口定义和确定的实现绑定。^[src/bokkio/capability_registry.py#L29] ^[docs/CAPABILITY-MODULES.md#L1]

## 输入输出与执行规则

module.list → capability.list → capability.get → capability.invoke。接口定义包含能力／模块版本、输入输出、side_effect、前置条件、预期效果、验证与恢复规则；SHA256绑定元数据、实现源码和依赖版本。发现不导入openpyxl；执行要求可选office extra。^[src/bokkio/capability_registry.py#L42] ^[src/bokkio/modules/office_xlsx_contract.py#L9]

精确调用仍需Session、modules和paths允许列表、write／trusted_host及原有精确审批。读取能力的side_effect为read，但首版宿主代码通道仍要求write／trusted_host。返回job_id，结果在job.get.result.output；不把进程exit0当业务完成。^[src/bokkio/capability_registry.py#L55] ^[src/bokkio/executor.py#L238]

## Office文件支持范围

| 能力 | 语义 |
|---|---|
| xlsx.read_range | 源SHA256固定、有界范围读取字面值 |
| xlsx.update_cells | 源不修改、另存新文件、发布前后独立读回 |
| xlsx.verify_cells | 重新打开磁盘文件并比较预期值 |

一次1000个单元格、源10MiB／ZIP展开50MiB；拒绝公式重算、覆盖输出、合并目标和已识别复杂包特征。更新只操作保存的.xlsx，不操作当前打开的Excel／Numbers。先临时保存／核验，再以不覆盖hard-link发布；文件系统不支持时明确失败。^[src/bokkio/modules/office_xlsx.py#L14] ^[src/bokkio/modules/office_xlsx.py#L109]

## 恢复与证据

升级导致接口定义变化时旧请求零派发拒绝，worker再校验接口与实现的一致性。重复operation ID查回既有作业；发布后无法核验、结果缺失或绑定不符保持unknown，不切换实现或盲重发。^[src/bokkio/modules/office_xlsx.py#L117] ^[src/bokkio/executor.py#L251]

模块30项加backend派发事实4项检查包含在647回归中；受控文件对照code/module各3/3。模型成本、速度和自主成功率收益未证明；Windows／客户任务／旧GUI适配迁移未验收。^[docs/evidence/2026-10-13-capability-modules/README.md#L18]

独立插件安装、热升级、语义检索和三层规划不属于本轮。trusted-host仍是宿主执行边界，策略变更沿用重启服务规则。^[docs/CAPABILITY-MODULES.md#L30]

关联：[[entities/runtime-core]]、[[entities/runtime-workflow]]、[[summaries/module-call-map]]、[[concepts/runtime-contracts]]、[[summaries/current-status]]。
