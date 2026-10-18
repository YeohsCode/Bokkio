---
title: Bokkio Wiki Schema
created: 2026-10-08
updated: 2026-10-18
type: meta
tags: [meta, maintenance]
sources: [pyproject.toml, docs/progress/STATUS.md]
confidence: high
---

# Wiki Schema

## Domain
Bokkio 当前代码的内部架构、执行边界、阶段状态与证据。采用 LLM Wiki 的 project-local 方案。正文以中文为主，保留代码/API 标识。

## Source of truth
- 初始编译基线为 abe38ac；当前能力／Workflow架构刷新基线为78c3289 + working-tree（2026-10-13），最新页以 shared progress 为状态来源；raw/manifest.json 保存初始42个已提交来源及追加版本的 commit/path/body SHA-256；未提交追加版本明确标记working-tree。
- 2026-10-16 追加 Outlook Graph / Desktop 增量，初版以404b413 + working-tree为刷新基线；通用Graph修订以90caa22 + working-tree为基线；当前待验证项以 [[entities/outlook-graph]] 为准，旧快照不覆盖。
- 2026-10-18追加原生读取/网页整理/用户接管来源，以262cad6 + working-tree为基线；当前实现和未完成验收见[[entities/native-observation-and-control]]，不把合成数据或开发构建称为双平台验收。
- raw/source-snapshots/*.txt 通常是冻结来源，文件含小 frontmatter 与原始正文；正文 hash 不包含 frontmatter。不要将其作为代码执行。2026-10-18 按用户明确要求统一文档用语，20份历史快照进行了文字修订；对应 manifest 记录保留 original_source_sha256 / original_source_bytes，当前 sha256 / bytes 校验修订后的正文，frontmatter 的 text_revised 标明修订日期。历史结果、版本和代码标识保留。
- 页面的 sources 使用 repo 相对文件路径；段落标记使用 ^[path#Lline]。行号只在 Wiki refresh 时更新，函数/章节名辅助定位。
- 代码决定已实现接口；报告决定当时的验收事实；研究/计划仅说明目标设计。出现不一致必须记录双方证据和范围。
- 不把字段存在、mock 测试、初始化成功或模型 completed 当作 GUI/官方 benchmark 成功。

## Conventions
- 文件名小写与连字符；路径明确的 [[entities/native-runtime]] 等 wikilinks，避免同名歧义。
- 所有编译页有 title/created/updated/type/tags/sources/confidence；每页至少两条出站 wikilinks。
- type: entity, concept, comparison, query, summary, meta。
- tags 仅使用下面的 taxonomy；confidence 表示陈述支持程度，不表示功能完成度。
- contested: true 表示文档与代码存在待审阅差异；保留理由，不自动把两者之一改成产品事实。
- 每个新页加入 index.md。所有写入/ingest/query/lint 追加 log.md，超过500条再按年轮换。
- 页面最多约200行，超过阈值拆分；实体出现于两份来源或在单一核心文件中居中心才建页。

## Tag taxonomy
project, architecture, runtime, selector, native, windows, macos, agent, planner, jev, workflow, recovery, vision, office, benchmark, evidence, safety, configuration, maintenance, meta

## Maintenance
1. 会话开始先读本文件、[[index]] 和 [[log]] 的最近记录。
2. 代码变化时刷新相关页 updated 与事实，添加新版本 raw 快照；旧快照不可修改。
3. 输入环境事实保留观察日期，不承诺当前物理屏幕状态；最新状态以实际前置检查为准。
4. 校验 frontmatter、标签、来源行号、两条链接、索引、孤立页、来源 SHA、200行阈值和隐私。
5. 10+既有页面批量更新先确认范围；初始化新页不属于覆盖既有页面。
6. 不导入凭据、环境值、账户、真实邮箱、主机私有目录或无关截图。资料只取本仓库。
7. 文档直接使用接口定义、参数和权限检查、执行结果、重复请求处理等具体表述，见 docs/DOCUMENTATION-STYLE.md。

入口：[[summaries/architecture-map]]、[[summaries/module-call-map]]、[[entities/runtime-core]]、[[summaries/current-status]]、[[concepts/configuration-and-privacy]]。
