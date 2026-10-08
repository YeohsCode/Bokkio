---
title: "Pending 与已知集成缺口"
created: "2026-10-08"
updated: "2026-10-08"
type: "summary"
tags: ["maintenance", "office", "vision", "safety"]
sources: ["docs/PENDING.md", "src/bokkio/office_runner.py", "src/bokkio/agent.py", "src/bokkio/cli.py", "tests/test_office_benchmark.py"]
confidence: "high"
---

# Pending 与已知集成缺口

按先修复可复现代码问题、再获取真实执行证据的顺序推进；环境恢复不是所有缺口的唯一条件。^[docs/PENDING.md#L5]

## 首要代码问题

`office_runner._native_run()` 使用 `required_files`，`DesktopAgent.__init__()` 不接受该参数。建议复用 CLI 的 final_verifier 机制并补真实 constructor wiring 验证。这是当前代码事实，尚未在本次 Wiki 工作中修复。^[src/bokkio/office_runner.py#L111] ^[src/bokkio/agent.py#L157] ^[src/bokkio/cli.py#L242]

## 验收与实现队列

1. 修复上述接口后，恢复输入/AX并实际跑固定三题，保留所有失败及独立产物分数。
2. 解决 Office disabled 编辑区、Excel 观察、Outlook 深度等原生覆盖；接入真正的自动视觉降级。
3. Mac input 正向与 Windows capture/OCR/input；再做不同 DPI、窗口竞争、取消/限速/恢复。
4. Mac 文件/进程 Workflow、真实虚拟化、原始 VLM 和完整上游环境；之后扩展长流程。^[docs/PENDING.md#L17]

现有 Office runner 测试传入 mock executor，环境阻断不会调用 _native_run，因此373/373没有排除这个 wiring 风险。^[tests/test_office_benchmark.py#L100]

关联：[[queries/office-pilot-readiness]]、[[entities/visual-input]]、[[entities/native-runtime]]、[[summaries/current-status]]。
