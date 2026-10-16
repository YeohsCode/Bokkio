---
title: Bokkio Wiki Log
created: 2026-10-08
updated: 2026-10-16
type: meta
tags: [meta, maintenance]
sources: [docs/STATUS.md, docs/progress/STATUS.md]
confidence: high
---

# Wiki Log

追加维护历史；定位规则见 [[SCHEMA]]，导航见 [[index]]。

## [2026-10-08] create | Bokkio project-local LLM Wiki

- 使用 LLM Wiki project-local 方案，基线 abe38ac。
- 新建SCHEMA/index/log、22份编译页、42份原始来源快照与来源manifest。
- Created: comparisons/native-and-visual-paths.md
- Created: comparisons/windows-and-macos.md
- Created: concepts/action-verification.md
- Created: concepts/configuration-and-privacy.md
- Created: concepts/element-identity.md
- Created: concepts/evidence-and-scoring.md
- Created: concepts/permissions-and-sessions.md
- Created: concepts/recovery-and-versioning.md
- Created: entities/benchmark-adapters.md
- Created: entities/bokkio.md
- Created: entities/capture-and-ocr.md
- Created: entities/desktop-agent.md
- Created: entities/native-runtime.md
- Created: entities/office-pilot.md
- Created: entities/planner-and-jev.md
- Created: entities/visual-input.md
- Created: entities/workflow-engine.md
- Created: queries/extending-native-runtime.md
- Created: queries/office-pilot-readiness.md
- Created: summaries/architecture-map.md
- Created: summaries/current-status.md
- Created: summaries/pending-and-known-gaps.md

## [2026-10-08] ingest | Current code and acceptance evidence

- 来源集合见 raw/manifest.json；不读取私有配置或VM认证文件。
- 记录 Office executor 构造参数不匹配，见 [[entities/office-pilot]] 与 [[summaries/pending-and-known-gaps]]。
- 当前状态和原始历史分母分开保留。

## [2026-10-08] ingest | Immutable source inventory

- Created: raw/manifest.json
- Created: raw/source-snapshots/README.md.txt
- Created: raw/source-snapshots/PLAN.md.txt
- Created: raw/source-snapshots/pyproject.toml.txt
- Created: raw/source-snapshots/docs/STATUS.md.txt
- Created: raw/source-snapshots/docs/PENDING.md.txt
- Created: raw/source-snapshots/docs/RESEARCH.md.txt
- Created: raw/source-snapshots/docs/P6-CLOSURE.md.txt
- Created: raw/source-snapshots/docs/MACOS-FOLLOWUP.md.txt
- Created: raw/source-snapshots/docs/MACOS-OFFICE-REPORT.md.txt
- Created: raw/source-snapshots/docs/MACOS-CAPTURE-PROBE.md.txt
- Created: raw/source-snapshots/docs/P7-MACOS-VISUAL.md.txt
- Created: raw/source-snapshots/docs/OFFICE-PILOT-READINESS.md.txt
- Created: raw/source-snapshots/docs/BENCHMARK-PLAN.md.txt
- Created: raw/source-snapshots/docs/SECURITY-REVIEW.md.txt
- Created: raw/source-snapshots/fixtures/windowsworld-office/manifest.json.txt
- Created: raw/source-snapshots/docs/evidence/2026-10-08-office-pilot-ready/run.json.txt
- Created: raw/source-snapshots/docs/evidence/2026-10-08-p7-macos-runtime/validation.json.txt
- Created: raw/source-snapshots/src/bokkio/agent.py.txt
- Created: raw/source-snapshots/src/bokkio/arena.py.txt
- Created: raw/source-snapshots/src/bokkio/cli.py.txt
- Created: raw/source-snapshots/src/bokkio/decision.py.txt
- Created: raw/source-snapshots/src/bokkio/jev.py.txt
- Created: raw/source-snapshots/src/bokkio/macos_capture.py.txt
- Created: raw/source-snapshots/src/bokkio/model.py.txt
- Created: raw/source-snapshots/src/bokkio/office_benchmark.py.txt
- Created: raw/source-snapshots/src/bokkio/office_judge.py.txt
- Created: raw/source-snapshots/src/bokkio/office_runner.py.txt
- Created: raw/source-snapshots/src/bokkio/planner.py.txt
- Created: raw/source-snapshots/src/bokkio/scroll.py.txt
- Created: raw/source-snapshots/src/bokkio/selector.py.txt
- Created: raw/source-snapshots/src/bokkio/visual.py.txt
- Created: raw/source-snapshots/src/bokkio/visual_input.py.txt
- Created: raw/source-snapshots/src/bokkio/windows_capture.py.txt
- Created: raw/source-snapshots/src/bokkio/windows_uia.py.txt
- Created: raw/source-snapshots/src/bokkio/workflow.py.txt
- Created: raw/source-snapshots/src/bokkio/workflow_inputs.py.txt
- Created: raw/source-snapshots/src/bokkio/workflow_repair.py.txt
- Created: raw/source-snapshots/src/bokkio/xa11y_backend.py.txt
- Created: raw/source-snapshots/src/bokkio/native/macos_capture.swift.txt
- Created: raw/source-snapshots/tests/test_office_benchmark.py.txt
- Created: raw/source-snapshots/tests/test_visual_input.py.txt
- Created: raw/source-snapshots/tests/test_workflow_extended.py.txt

## [2026-10-08] update | Repository navigation and known gap

- Updated: README.md，加入知识库入口。
- Updated: docs/PENDING.md，加入已核对的 Office constructor 缺口；未修改 Runtime。
- Created: _meta/validation.json，来源/标签/索引/页大小/接口核对结果。

## [2026-10-08] lint | 0 structural issues; 1 review flag

- 技能 lint：25 个Markdown文件，22个编译页，110条已解析链接，0孤立页/0断链/必需frontmatter通过。
- 附加检查：42份来源body哈希、39个来源文件引用、索引、标签、200行阈值和来源行号均通过。
- 待审阅项：[[entities/office-pilot]] contested，真实executor调用与Agent构造签名不一致，未在本次知识库任务中修复。

## [2026-10-08] refresh | Mac desktop recovery and executor repair

- 更新5个状态/Office/权限页面及索引；保留旧blocked证据和旧raw来源。
- 新证据：Mac会话解锁，原生fixture动作3/3及12次滚动通过，三个Office文档窗口可读；新工作区可尝试，未执行题目。
- Office executor改final_verifier，新增真实DesktopAgent构造路径测试；主机374/374。
- 追加working-tree来源快照，以body SHA-256标识版本；不会把未提交状态标记成历史commit。

## [2026-10-08] lint | Recovery refresh clean

- 25页、110条解析链接，零孤立页/断链；50份raw正文哈希及全部来源行号有效。
- Office constructor review flag已解除；题目成功与P7视觉输入验收仍待实跑。

## [2026-10-09] refresh | Office live runs and bounded input

- 更新6个Office/状态/权限/输入页面及索引，追加来源版本，不改旧raw。
- 十轮共30次原题执行，各轮独立评分0/3；第三轮并发干扰和各轮代码变化保留。
- 最新解锁会话失败是Word派发后确认、Excel输入前守卫、PPT置信度；不再写“未开始”。
- 较早OCR版本Excel脚本探针通过，明确不是Agent成绩或最新native-bounds验收。主机403/403，Windows历史373/373。

## [2026-10-09] lint | Live-run refresh validated

- 25个Markdown页面、110条解析链接，零孤立页/断链；69份不可变来源正文哈希、来源行号和两份证据SHA256SUMS通过。
- 全工作树隐私扫描的24项命中均为历史WAA runner去重请求UUID，来源arena.py的uuid4().hex；没有凭据命中。
- 主机403项回归通过；保留Office0/3与较早OCR脚本探针的证据范围。

## [2026-10-09] refresh | Office input diagnostics and explicit click

- 更新6个既有页面及索引，追加raw版本，保留之前的69份不可变来源。
- 增加输入范围拒绝事实、派发回执/原生回读诊断、3次有限回读和split button显式点击收窄；未知完成不重试。
- 真实Jev在记录的合成PPT快照上返回click/1.0，没有live dispatch或新任务分数；主机411/411、Swift helper重编译/自有窗口捕获通过。
- Mac当前锁屏且自动解锁失败，完整GUI复跑待解锁；不把此状态用于解释之前解锁时的失败。

## [2026-10-09] refresh | Shared visual provider and Mac Agent routing

- 更新6个采集/输入/状态/权限/Office页面及索引，追加raw版本，保留之前82份来源。
- Mac provider、公共OCR协议、HybridBackend及Agent/Jev/CLI opt-in接入完成；范围、预算、取消、歧义、未知完成、模拟click/type和恢复约束有测试。
- 主机435/435；最新实机只读观察及真实Jev选择各3/3，模型只接收文字候选。锁屏activation真实拒绝，零输入；计数OCR限制与历史失败保留。
- Windows工作按用户要求暂缓；真实输入、视觉Workflow、跨窗口/图标等保持pending。

## [2026-10-09] record | Office dataset rerun blocked before execution

- 公共视觉代码4b6de28已提交并推送；新工作区三题初始化通过目标负例检查。
- 实际runner planned3/started0/blocked3、score=null；Mac锁屏且自动解锁失败，权限均通过，零模型/题目动作。
- 保留原题15步预算与历史执行成绩；Windows维持暂缓，原始VLM未调用。更新当前状态与证据，追加不可变来源版本。

## [2026-10-13] refresh | Current Runtime architecture and module calls

- 依据 0feda6d 工作树更新 README 中英文当前架构；当前设计移至历史 P0–P7 前，增加系统图、模块调用图、观察/审批/派发时序和模块职责。
- 刷新 architecture-map、bokkio、native-runtime、current-status、pending-and-known-gaps；新建 runtime-core、module-call-map、runtime-contracts；同步 index 与 SCHEMA。
- 明确 Runtime.call 与 Xa11yBackend 的层级、三入口/四通道、专用原生线程、桌面锁、独立代码/Browser worker、SDK 父子调用与独立审批。
- 更新共享状态至 2026-10-13：587/587、审计 9/9、矩阵 18/18、业务 26/36、稳定性 17/27、GUI 0/18；保留旧失败/评分更正和人工/客户/Windows 待验收。
- 追加 current-runtime 不可变来源快照，逐文件核对 HEAD；README 未提交版本标 working-tree，旧快照不覆写。旧专题保留其 dated 范围，由当前状态链接后续事实。

## [2026-10-13] lint | Current Runtime refresh validated

- 28 个 Markdown 文件、25 个编译页、149 条已解析 wikilinks；零断链/孤立页，frontmatter/tags/index/200 行限制通过。
- 199 处来源行号、65 个来源文件、36 个 Python 模块及 23 个公开工具路由核对通过；修复四页 sources 遗漏，正文历史日期不改。
- 157 份不可变来源正文 SHA-256/字节数验证；本次追加49份（含最终图布局修订后的 README 版本），之前108份保持原样；新增来源凭据模式扫描零命中。
- README 与 Wiki 共7处 Mermaid 块语法通过，4种独立图在 headless Chromium 实际渲染；检查系统图/调用图/时序，移除反馈连线标签遮挡。
- _meta/validation.json 记录本次文档检查和历史验证；587项等产品成绩仅引用已有报告，本次没有新增 GUI/产品回归成绩。

## [2026-10-13] refresh | Capability modules and Runtime Workflow

- 更新6个当前架构／调用／Core／项目边界／状态／待办页；新建capability-modules、runtime-workflow两实体，索引27个编译页。历史直接backend Workflow专题保留其日期与范围。
- README更新系统架构、功能布局、模块调用图和中英文职责表；按当前代码描述模块通过已有worker运行、新Workflow子动作回到同一Core。功能布局采用窄幅树形排列，回调以同名Core子动作节点说明。
- 新增41份capability-workflow不可变来源，之前157份快照逐字保留；当前未提交来源明确标working-tree、已提交来源记录78c3289基线与SHA256。
- 647隔离回归／6份受控文件核验引用上一实施轮证据，保留34项新合同、初轮失败、模块额外校验成本和客户／Windows待验收。业务26/36、稳定性17/27、GUI0/18保持原冻结版本；完整业务复测继续暂停。

## [2026-10-13] lint | Capability/Workflow architecture validated

- scripts/validate_wiki.py检查27个编译页／30个Markdown、169条wikilinks、225处来源行号、66个来源文件，零断链／孤立页／索引或元数据错误；44个Python模块与34个公开工具映射完整。
- 198份不可变来源SHA256与frontmatter校验通过，新41份来源凭据模式扫描无命中。
- README／Wiki共8处Mermaid语法通过；4种独立图在本机Chromium渲染，架构／功能布局／调用图已视觉检查。结果保存wiki/_meta/validation.json。
- 本轮只更新文档及维护校验工具；没有恢复已暂停的自主业务或GUI矩阵。

## [2026-10-16] refresh | Desktop Outlook Graph / PowerShell

- README 与 Desktop README 补充账户入口、官方默认应用身份、SDK 缓存、密码管理及 Graph 工具；新增用户连接指南和双平台证据。
- 新建 outlook-graph 实体，刷新架构／模块调用／状态／配置隐私／索引／Schema。55个Python模块与38个公开工具映射完整；Graph经Runtime执行，配置页管理直接调用，不虚构Jev参与。
- 736项Python、9项Electron及双平台打包UI各10/10引用本次实施证据；UI使用真实PowerShell与自有离线cmdlet，不代表真实邮箱成绩。为避免截图包含本机目录，macOS截图改为账户卡片并复跑10/10。
- 正常安装版真实SDK已提供设备码；用户不在电脑旁，要求先提交。真实账户授权、邮箱查询、SDK重启复用仍待验证；没有继续发起授权。
- 追加outlook-graph不可变来源版本，基线404b413 + working-tree；198份既有快照保持原样。

## [2026-10-16] lint | Outlook documentation validated

- 28个编译页／31个Markdown、184条wikilinks、239处来源行号，零断链／孤立页／元数据错误；55个Python模块与38个工具映射完整。
- 221份不可变来源SHA256与字节数通过，本次新增23份；新增来源凭据与主机私有目录扫描无命中。证据只含自有离线账户夹具。
- 8处Mermaid语法通过，6种独立图在Chromium实际渲染；新增Graph系统图和调用关系已视觉检查。检查详情写入_meta/validation.json。
- 本轮文档维护不新增真实邮箱或SDK登录持久性成绩；真实账户验证保留待办。
