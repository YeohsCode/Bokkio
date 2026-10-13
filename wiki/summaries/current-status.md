---
title: "当前阶段与证据快照"
created: "2026-10-08"
updated: "2026-10-13"
type: "summary"
tags: ["project", "evidence", "runtime", "meta"]
sources: ["docs/progress/STATUS.md", "docs/evidence/2026-10-12-macos-completion/README.md", "README.md"]
confidence: "high"
---

# 当前阶段与证据快照

更新至 2026-10-13；当前工作候选版 0.2.0。主架构已从历史 Planner/Jev 循环转为模型无关通用 Runtime，核心交付物 8/8 已实现，但产品成功率目标和完整客户/双平台验收尚未完成。最新事实以 docs/progress/STATUS.md 为入口，旧 docs/STATUS.md 与旧 Wiki 专题保留历史观察日期。^[docs/progress/STATUS.md#L3]

## 最新自动验证

| 项目 | 当前记录 | 证据范围 |
|---|---:|---|
| 主机回归 | 587/587 | GUI 完成后串行测试 |
| 原生 / SQLite / 审计合同 | 9/9 | 授权、审批、意图、缓存及统计对账 |
| 本机窗口 / 作业矩阵 | 18/18 | 两项正向物理输入实际成功；真实锁屏/额外显示器未测 |
| Core 安全类别 | 8/8 | 每类至少一项实测，不是全异常覆盖 |
| 独立安装包 | 原生/代码/Browser 各 3/3 | 新 venv、锁定依赖、MCP/CLI、自动批准与审计 |
| 自主 any-tool 主批 | 26/36 | Codex 12/12、Hermes 8/12、DeepSeek 6/12；全部启动 |
| 关键家族三份样本 | 17/27 | 同一冻结源码；追加两批 7/9、5/9 |
| GUI 复测 | 0/18 | 全部启动；部分流程/范围可行性限制单列 |
| 30/90/300 秒审批恢复 | 9/9 | 独立 fixture 管理员自动批准，不是人工 |
| MCP 图片交付 | 通过 | PNG/ImageContent、尺寸与哈希检查 |

依据：^[docs/progress/STATUS.md#L5] ^[docs/evidence/2026-10-12-macos-completion/README.md#L47]

主批每调用方至少 10/12、六类各有通过、关键家族三份全过的目标未满足。当前 Codex 保留会话并编写评分器，是 official MCP client bridge，不能称盲测或与其他调用方公平排名。GUI 对照不能据此判定某应用完全不支持。^[docs/progress/STATUS.md#L20]

## 最新实现与具体缺口

Mac 精确窗口遍历、scoped/full ref 一致、Pages RTF 渲染文字/OCR/新进程重开验收、SDK 终态/预算核对已修订；实现和独立评分仍分别记录。Numbers .numbers 持久化保留历史 1/3，本轮两份补测未保存：控件字段写值确认但业务模型未提交，保存 disabled；Core 保守 unknown 且未重发，需要通用分类/提交修复。^[docs/progress/STATUS.md#L22] ^[docs/progress/STATUS.md#L29]

Windows 当前 Runtime 独立实机、客户应用/数据/部署、真实人工审批、真实锁屏/解锁及第二显示器/缩放仍待验收。历史 Windows UIA/Planner、Mac OCR 和 Office 题库结果不能替代这些分母。^[docs/progress/STATUS.md#L31]

## 历史证据与更正

旧业务 r1～r4 保留原始记录；SDK 终态核验使旧重点矩阵 9/12 更正为 7/12，不按 exit 0 判定 SDK 完成。2026-10-09 Office 十轮各 0/3、后续 r28/r30 各 3/3、r33 为 0/3 仍是旧 Agent 的分轮事实，不是新 Core 或官方 benchmark 成绩。^[docs/progress/STATUS.md#L26] ^[README.md#L275]

关联：[[summaries/architecture-map]]、[[entities/runtime-core]]、[[summaries/pending-and-known-gaps]]、[[concepts/evidence-and-scoring]]、[[entities/office-pilot]]。
