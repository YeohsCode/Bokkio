---
title: Bokkio Wiki Log
created: 2026-10-08
updated: 2026-10-09
type: meta
tags: [meta, maintenance]
sources: [docs/STATUS.md]
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
