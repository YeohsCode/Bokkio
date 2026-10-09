---
title: "如何判断 Office 题库是否可以跑"
created: "2026-10-08"
updated: "2026-10-09"
type: "query"
tags: ["office", "benchmark", "evidence"]
sources: ["docs/OFFICE-PILOT-READINESS.md", "docs/STATUS.md", "docs/evidence/2026-10-08-macos-session-recovery/readiness.json", "docs/evidence/2026-10-08-office-live/README.md", "docs/evidence/2026-10-09-office-fix/README.md", "src/bokkio/agent.py", "src/bokkio/office_runner.py", "tests/test_office_benchmark.py"]
confidence: "high"
---

# 如何判断 Office 题库是否可以跑

入口已能实际启动：十轮共30次执行，各轮独立评分0/3。当前问题是执行覆盖；不能再描述成题目尚未开始。最新运行启动时会话未锁且权限通过，失败发生于Word确认、Excel输入守卫和PPT决策。^[docs/OFFICE-PILOT-READINESS.md#L16]

## 每次运行

1. 检查交互会话和权限，使用新隔离工作区；输入不能提前满足目标。
2. 保持原题和15次动作预算，记录派发、确认和未知完成；未知派发先检查，不能盲目重试。
3. 独立验证保存产物。runner completed、字段草稿值或脚本能力探针不等于Agent成功。
4. 保留历史失败；第三轮并发干扰和各轮代码变化分别标注。^[docs/evidence/2026-10-08-office-live/README.md#L5]

```sh
uv run python scripts/office_pilot.py prepare --workspace /tmp/bokkio-office-new
uv run python scripts/office_pilot.py run --workspace /tmp/bokkio-office-new
```

主机411/411；Windows373/373为历史回归。原始VLM/官方环境仍未执行。^[docs/STATUS.md#L21]

## 后续修复（2026-10-09）

输入拒绝与回读诊断已保留到Agent trace；同一字段最多3次回读，不重复派发。显式split button点击收窄后，真实Jev对记录的PPT快照返回click、置信度1.0（阈值0.7）。主机411/411；Mac当前锁屏，新GUI任务未开始，历史0/3仍为最新产物成绩。该决策探针没有live dispatch或Agent分数。^[docs/evidence/2026-10-09-office-fix/README.md#L1]

关联：[[entities/office-pilot]]、[[concepts/permissions-and-sessions]]、[[summaries/pending-and-known-gaps]]。
