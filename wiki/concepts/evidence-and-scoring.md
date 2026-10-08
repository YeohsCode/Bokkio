---
title: "证据、评分与真实分母"
created: "2026-10-08"
updated: "2026-10-08"
type: "concept"
tags: ["evidence", "benchmark", "office"]
sources: ["docs/STATUS.md", "docs/P6-CLOSURE.md", "docs/P7-MACOS-VISUAL.md", "docs/evidence/2026-10-08-office-pilot-ready/run.json", "src/bokkio/office_benchmark.py"]
confidence: "high"
---

# 证据、评分与真实分母

软件实现、隔离测试、原生动作、完整任务和官方评分是不同证据层，不能相互替代。^[docs/STATUS.md#L20]

## 当前数字的含义

| 数字 | 支持的结论 |
|---|---|
| 373/373 两端 | 对应版本的隔离测试通过 |
| Mac 3/3 + 8/8 | 自绘窗口捕获/OCR正常与拒绝验收通过 |
| P6 重放 3/3 | 对应 Windows 流程完成独立验收 |
| Office started 0 / blocked 3 | 任务尚未开始，不能报 0% 或 100% Agent 成功率 |

上述结果各自绑定原始范围、日期及代码版本。^[docs/P6-CLOSURE.md#L5] ^[docs/P7-MACOS-VISUAL.md#L15] ^[docs/evidence/2026-10-08-office-pilot-ready/run.json#L1]

## 独立文件验收

Office scorer 检查内容保持、Word 样式继承/字体/行距、Excel 货币格式、PPT 标题 placeholder/layout。原题 rubric 的 VLM 中间检查与本地 OOXML 分数分别报告，后者不是官方 VLM 成绩。^[src/bokkio/office_benchmark.py#L130]

关联：[[entities/office-pilot]]、[[summaries/current-status]]、[[comparisons/windows-and-macos]]。
