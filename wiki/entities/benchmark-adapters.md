---
title: "外部 Benchmark 适配入口"
created: "2026-10-08"
updated: "2026-10-08"
type: "entity"
tags: ["benchmark", "agent", "evidence"]
sources: ["src/bokkio/arena.py", "docs/BENCHMARK-PLAN.md", "fixtures/windowsworld-office/manifest.json"]
confidence: "high"
---

# 外部 Benchmark 适配入口

WAA 逐步适配与 WindowsWorld Office pilot 是不同入口，不能把前者的 Explorer/Notepad 成绩换成微软 Office 成绩。^[docs/BENCHMARK-PLAN.md#L1]

## WAA

`NativeArenaAgent.predict()` 只返回待执行请求，`step()` 校验原请求再释放一次派发；改变、重放和未消费请求均拒绝。Adapter 兼容上游四值 predict，Bridge 对接环境 step/history/evaluate。完整 HTTP/VM runner 尚未验收。^[src/bokkio/arena.py#L106] ^[src/bokkio/arena.py#L135]

## WindowsWorld

Office pilot 固定原题及独立产物评分；初始化、平台、输入生成和 native action-space 差异被标记为 adapted run。OSWorld 长流程是设计参考，不能推断官方 runner 已接入。^[fixtures/windowsworld-office/manifest.json#L1]

关联：[[entities/office-pilot]]、[[comparisons/native-and-visual-paths]]、[[concepts/evidence-and-scoring]]。
