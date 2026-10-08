---
title: "如何判断 Office 题库是否可以跑"
created: "2026-10-08"
updated: "2026-10-08"
type: "query"
tags: ["office", "benchmark", "evidence"]
sources: ["src/bokkio/office_runner.py", "src/bokkio/agent.py", "tests/test_office_benchmark.py", "docs/OFFICE-PILOT-READINESS.md"]
confidence: "high"
---

# 如何判断 Office 题库是否可以跑

当前答案：原题/输入/评分软件已准备，实际任务未开始；还需要修复真实 executor 的构造接口，并完成交互环境及 Office 操作验收。^[src/bokkio/office_runner.py#L111] ^[docs/OFFICE-PILOT-READINESS.md#L18]

## 运行前检查

1. 先修复 required_files 与 final_verifier 的接口不匹配，补覆盖真实配置构造路径的测试。CLI 已有 require-file → callback 的参考实现。^[src/bokkio/agent.py#L157] ^[src/bokkio/cli.py#L242]
2. `prepare` 使用新隔离目录；输入内容不得提前满足目标。^[src/bokkio/office_benchmark.py#L64]
3. 前置环境失败时 planned/started/blocked 分开记录，score=null，不调用模型。^[src/bokkio/office_runner.py#L115]
4. 桌面可用后，先跑三题并保留失败；native覆盖和视觉自动降级需要逐步补齐。^[docs/PENDING.md#L5]

## 命令入口

```sh
uv run python scripts/office_pilot.py prepare --workspace /tmp/bokkio-office-new
uv run python scripts/office_pilot.py run --workspace /tmp/bokkio-office-new
```

这些命令表示入口，不保证当前真实 executor 可执行完成。现有 mock executor 测试验证环境阻断/评分边界，没有覆盖上述构造器问题。^[tests/test_office_benchmark.py#L100]

关联：[[entities/office-pilot]]、[[concepts/permissions-and-sessions]]、[[summaries/pending-and-known-gaps]]。
