---
title: "微软 Office 原题 pilot"
created: "2026-10-08"
updated: "2026-10-08"
type: "entity"
tags: ["office", "benchmark", "agent", "evidence"]
sources: ["src/bokkio/office_benchmark.py", "src/bokkio/office_runner.py", "src/bokkio/agent.py", "docs/OFFICE-PILOT-READINESS.md", "fixtures/windowsworld-office/manifest.json"]
confidence: "high"
contested: true
---

# 微软 Office 原题 pilot

首批固定 WindowsWorld 三道 L1 原题，Mac 环境适配：Word 标题/正文格式、Excel D 列货币格式、PowerPoint 标题页。原始任务、revision、校验哈希、许可及 15 步预算保留。^[fixtures/windowsworld-office/manifest.json#L1]

## 准备与评分

`prepare()` 仅初始化隔离输入：Word 初始格式未达标、Excel 非货币、PPT 目标不存在。`evaluate()` 只读检查保存的 OOXML，模型 completed 不能替代文件证据。原始 VLM judge 入口保留 prompt/model，但需独立凭据且未实际运行。^[src/bokkio/office_benchmark.py#L64] ^[src/bokkio/office_judge.py#L18]

## 实际就绪程度

归档运行 planned 3、started 0、blocked 3，score null。软件准备与任务执行不同；目前不能称为三题可成功运行。^[docs/evidence/2026-10-08-office-pilot-ready/run.json#L1]

**代码审阅发现接口不一致**：`_native_run()` 传 `required_files=` 给 DesktopAgent，而构造器只接受 `final_verifier` / `required_sources`。这条路径被环境检查提前挡住，现有 mock executor 测试未覆盖。文档“执行入口已实现”需要以这个未解决问题限定；恢复桌面也不会自动消除 TypeError。^[src/bokkio/office_runner.py#L111] ^[src/bokkio/agent.py#L157]

关联：[[queries/office-pilot-readiness]]、[[concepts/evidence-and-scoring]]、[[summaries/pending-and-known-gaps]]。
