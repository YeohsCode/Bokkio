---
title: "当前阶段与证据快照"
created: "2026-10-08"
updated: "2026-10-13"
type: "summary"
tags: ["project", "evidence", "runtime", "meta"]
sources: ["docs/progress/STATUS.md", "docs/evidence/2026-10-13-capability-modules/README.md"]
confidence: "high"
---

# 当前阶段与证据快照

截至2026-10-13，工作候选版0.2.0。实现8/8是交付物分母，产品成功率目标与客户／双平台验收未完成；当前事实以共享progress为准。^[docs/progress/STATUS.md#L3]

## 最新源码的独立验证

| 项目 | 结果 | 范围 |
|---|---:|---|
| 最新完整隔离回归 | 647/647 | 包含新增模块30项和backend合成provider4项 |
| 受控文件对照 | 6/6 | 三份样本code/module两路；独立打开文件核验 |
| 临时wheel检查 | 通过 | 新模块包含、可选依赖声明、解包导入；不是独立完整安装或发行 |
| Workflow初轮回归 | 613/613 | 能力模块之前的版本与独立报告 |
| 后台启动／完整录制见证 | 5/5 | 自有应用、独立前台／鼠标见证，非客户任务 |

依据：^[docs/evidence/2026-10-13-capability-modules/README.md#L17] ^[docs/progress/STATUS.md#L7]

模块对照的通用路径包含精确解法代码。两路均一次执行请求，模块有额外校验成本；没有模型成本／速度／自主成功率提升结论。^[docs/evidence/2026-10-13-capability-modules/README.md#L22]

## 上一冻结版本业务证据

| 项目 | 历史结果 | 版本范围 |
|---|---:|---|
| 完整any-tool主批 | 26/36 | Codex12/12、Hermes8/12、DeepSeek6/12 |
| 关键家族三份样本 | 17/27 | 同一冻结源码；不能合并不同轮次补分 |
| GUI对照复测 | 0/18 | 全部启动，部分流程／范围可行性限制单列 |
| 30／90／300秒审批恢复 | 9/9 | 独立fixture自动管理员，非人工 |
| 审计／窗口作业 | 9/9、18/18 | 上一冻结版本的独立报告 |

依据：^[docs/progress/STATUS.md#L17]

完整业务复测已暂停，暂停前12个Codex重放记录为4通过／2失败／6预检阻塞，不是新完整矩阵。旧分数不填入新增源码。当前Codex保留上下文且编写评分器，不称盲测或公平排名。^[docs/progress/STATUS.md#L9] ^[docs/progress/STATUS.md#L32]

## 最新实现与剩余缺口

新版Runtime Workflow与能力模块已交付。backend已确认未派发的禁用目标分类有合同验证；真实Numbers编辑提交／保存尚未续测，原生.numbers历史1/3保留。字段写值与业务模型提交不是同一事实。^[docs/progress/STATUS.md#L15] ^[docs/progress/STATUS.md#L40]

客户应用／部署、真实人工审批、物理锁屏／多显示器与Windows当前Runtime仍待验收。旧SDK终态矩阵9/12更正为7/12；历史Office分轮成绩不作为当前Core或官方benchmark分数。^[docs/progress/STATUS.md#L48] ^[docs/progress/STATUS.md#L38]

关联：[[summaries/architecture-map]]、[[entities/runtime-core]]、[[entities/capability-modules]]、[[entities/runtime-workflow]]、[[summaries/pending-and-known-gaps]]、[[concepts/evidence-and-scoring]]。
