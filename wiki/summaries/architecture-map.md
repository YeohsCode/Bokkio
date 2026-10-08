---
title: "架构与代码导航"
created: "2026-10-08"
updated: "2026-10-08"
type: "summary"
tags: ["architecture", "project", "maintenance"]
sources: ["pyproject.toml", "src/bokkio/cli.py", "src/bokkio/agent.py", "src/bokkio/workflow.py", "src/bokkio/office_runner.py"]
confidence: "high"
---

# 架构与代码导航

从入口到执行按模块职责阅读，比按提交时间浏览更容易定位改动。^[src/bokkio/cli.py#L12]

```mermaid
flowchart TD
    CLI[CLI / Python API] --> Agent[DesktopAgent]
    Agent --> Plan[Planner 阶段与成功条件]
    Agent --> Jev[Jev 闭集动作和目标]
    Jev --> Runtime[Xa11yBackend / WindowsUIA]
    Runtime --> OS[原生桌面应用]
    Agent --> Trace[Trace / Checkpoint]
    Trace --> Workflow[Recorder / WorkflowReplay]
    CLI --> Capture[限定窗口 Capture / OCR]
    Capture --> Candidate[只读视觉候选]
    Candidate --> Input[显式 Mac Input API]
    Input --> Verify[新图像和文字验证]
```

Capture/Candidate/Input 与 Agent 的自动降级连线尚未实现，图中不把它画成已运行的 Agent 路径。^[docs/STATUS.md#L5]

## 文件地图

| 模块 | 主文件 |
|---|---|
| 公共入口 | cli.py、pyproject.toml |
| 模型循环 | agent.py、planner.py、jev.py、decision.py |
| 元素与原生补充 | model.py、selector.py、xa11y_backend.py、windows_uia.py |
| 流程 | workflow.py、workflow_inputs.py、workflow_repair.py |
| 视觉 | windows_capture.py、macos_capture.py、native/macos_capture.swift、visual.py、visual_input.py |
| 评测 | arena.py、office_benchmark.py、office_runner.py、office_judge.py |

关联：[[entities/bokkio]]、[[entities/planner-and-jev]]、[[entities/workflow-engine]]、[[entities/capture-and-ocr]]、[[entities/benchmark-adapters]]。
