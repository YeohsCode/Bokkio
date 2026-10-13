---
title: "Pending 与已知集成缺口"
created: "2026-10-08"
updated: "2026-10-13"
type: "summary"
tags: ["maintenance", "runtime", "safety", "evidence"]
sources: ["docs/progress/STATUS.md", "README.md", "docs/RUNTIME-GUIDE.md", "src/bokkio/visual_runtime.py", "docs/CAPABILITY-MODULES.md"]
confidence: "high"
---

# Pending 与已知集成缺口

截至 2026-10-13，待办以共享 progress 状态/工作包为准；当前任务是通用 Runtime 的客户与双平台交付，旧Office和直接backend Workflow作为历史诊断；新版Runtime Workflow／文件模块已交付，不继续向 Core 添加软件业务流程。^[docs/progress/STATUS.md#L43] ^[README.md#L177]

## 当前队列

| 工作包 | 尚待完成 |
|---|---|
| MAC-01 | 真实锁屏/解锁、第二物理显示器或不同缩放 |
| MAC-NATIVE-02 | backend零派发分类已修复且有合成provider合同；真实Numbers现场分类、编辑提交/菜单路径、两份.numbers持久化待验收；unknown 不升级通过、不盲重发 |
| EVAL-QUALITY | Hermes/DeepSeek 完整终态、事实读取、GUI 保存/编辑、Harness 图片消费；GUI T01 范围变更用新 suite revision |
| CLIENT-01 | 客户指定未参与调优应用、可丢弃数据和独立评分条件 |
| HARNESS-01 | 客户部署、真实人工批准与等待成本；9/9 延迟自动批准仅是合同证据 |
| WIN-01 | 另一台 Windows 电脑上的当前 Runtime 安装/原生/像素/代码/Browser/审批/审计验收 |
| RELEASE-01 | 客户环境、双平台最终固定矩阵与支持范围；保留每端 14/15 和安全门槛 |

依据：^[docs/progress/STATUS.md#L43]

## 新复用能力的验收边界

Runtime Workflow还需用户／客户任务、Windows监听和物理环境验收；office.xlsx文件模块还需Windows／客户任务及自主Harness收益评估。完整业务矩阵继续暂停，647回归和6/6文件对照不替代旧业务分数。 ^[docs/progress/STATUS.md#L13] ^[docs/CAPABILITY-MODULES.md#L111]

## 证据与实现边界

- 实现 8/8、Mac 开发能力类别 4/5、Windows 新 Runtime 0/5 是不同分母；业务主批 26/36、稳定性 17/27、GUI 0/18 的失败必须保留。^[docs/progress/STATUS.md#L56]
- 新 Core/调用适配修订后冻结代码，重跑受影响主批和三份稳定性；评分更正和新尝试分开，不能覆盖旧失败。^[docs/progress/STATUS.md#L50]
- 无逐文件 OS 沙箱、远程 fleet、多租户 SSO、集中防篡改日志、签名安装器或离线依赖镜像；如要抵抗同用户任意宿主代码，需另建隔离执行/身份边界。^[docs/progress/STATUS.md#L56] ^[docs/RUNTIME-GUIDE.md#L30]

## 历史扩展的定位

旧 P5/P6/P7、Office 专题的 updated 日期是当时证据快照，不能读取为今天的全部产品能力。Mac HybridBackend 文字降级已实现，但新 Core 的 native/pixel/code/Browser 由调用方选择；视觉 Workflow、原始 VLM 或上游官方题库成绩不能从已有 Core 接口推断。^[src/bokkio/visual_runtime.py#L158] ^[docs/RUNTIME-GUIDE.md#L3]

关联：[[summaries/current-status]]、[[summaries/architecture-map]]、[[entities/runtime-core]]、[[entities/capability-modules]]、[[entities/runtime-workflow]]、[[concepts/runtime-contracts]]、[[entities/visual-input]]、[[queries/office-pilot-readiness]]。
