---
title: "当前阶段与证据快照"
created: "2026-10-08"
updated: "2026-10-18"
type: "summary"
tags: ["project", "evidence", "runtime", "meta"]
sources: ["docs/progress/STATUS.md", "docs/evidence/2026-10-13-capability-modules/README.md", "docs/evidence/2026-10-16-outlook-powershell/README.md", "docs/OUTLOOK-GRAPH.md", "docs/evidence/2026-10-16-graph-generic/README.md", "docs/WINDOWS-MACOS-INTEGRATION-RESULTS.md"]
confidence: "high"
---

# 当前阶段与证据快照

截至2026-10-18，工作候选版0.3.0。实现8/8是交付物分母，产品成功率目标与客户／双平台验收未完成；当前事实以共享progress为准。^[docs/progress/STATUS.md#L3]

## 2026-10-18：三项整合已实现，双平台验收待完成

读取预算、Chrome/Edge原生网页视图和用户接管已接入当前Core/Desktop。完整Python回归771通过、6跳过；Node9通过；前端构建和Mac独立Runtime暂存通过。Mac自有窗口及Chrome固定页有现场结果，Windows现场、物理输入/IME和两端安装包权限尚未完成。接管默认关闭。^[docs/WINDOWS-MACOS-INTEGRATION-RESULTS.md#L5]

下一步先恢复Windows测试环境，完成浏览器/输入恢复/安装包矩阵并修复问题。没有另行安排下一批新功能；分页、阻塞调用隔离和多会话只作条件性评估。原完整业务评测继续暂停。细节见[[entities/native-observation-and-control]]。^[docs/WINDOWS-MACOS-INTEGRATION-RESULTS.md#L118]

## 2026-10-16：Desktop Outlook 增量

当前 Desktop 包为0.3.0。专用未读查询和按钮已删除，通用outlook.request读取参数化Graph数据及正文，Harness负责业务理解与汇总。Python750项、Electron9项通过，最终账户/界面生命周期两端各12/12；两端各3个真实模型对话任务完成，邮件为离线夹具。合并套件的原生option可见性断言失败后修正，生命周期独立复验；后续模型请求HTTP402，没有伪称完整复跑通过。^[docs/evidence/2026-10-16-graph-generic/README.md#L13]

一份Windows摘要的时区文字标注有误，实际Graph过滤与选中邮件符合12小时；不将传输/UX验证换算为全面业务准确率。真实Microsoft账户授权、用户邮箱和SDK重启复用待用户登录。旧业务矩阵保留原日期范围。实现与接续见 [[entities/outlook-graph]] 和 [[concepts/configuration-and-privacy]]。^[docs/evidence/2026-10-16-graph-generic/README.md#L29]


## 2026-10-13 历史增量验证

| 项目 | 结果 | 范围 |
|---|---:|---|
| 该轮完整隔离回归 | 647/647 | 包含新增模块30项和backend合成provider4项 |
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

新版Runtime Workflow与能力模块已交付。backend已确认未派发的禁用目标分类有接口与执行行为验证；真实Numbers编辑提交／保存尚未续测，原生.numbers历史1/3保留。字段写值与业务模型提交不是同一事实。^[docs/progress/STATUS.md#L15] ^[docs/progress/STATUS.md#L40]

客户应用／部署、真实人工审批、物理锁屏／多显示器与Windows当前Runtime仍待验收。旧SDK终态矩阵9/12更正为7/12；历史Office分轮成绩不作为当前Core或官方benchmark分数。^[docs/progress/STATUS.md#L48] ^[docs/progress/STATUS.md#L38]

关联：[[summaries/architecture-map]]、[[entities/runtime-core]]、[[entities/capability-modules]]、[[entities/runtime-workflow]]、[[summaries/pending-and-known-gaps]]、[[concepts/evidence-and-scoring]]。
