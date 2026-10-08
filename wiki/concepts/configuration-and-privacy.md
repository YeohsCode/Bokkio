---
title: "配置、数据范围与隐私"
created: "2026-10-08"
updated: "2026-10-08"
type: "concept"
tags: ["configuration", "safety", "maintenance"]
sources: ["src/bokkio/jev.py", "src/bokkio/planner.py", "src/bokkio/office_runner.py", "docs/SECURITY-REVIEW.md"]
confidence: "high"
---

# 配置、数据范围与隐私

Wiki 只记录配置接口和变量名称，凭据与 VM 认证文件不进入 Wiki 或 Git。^[docs/SECURITY-REVIEW.md#L62]

## Provider 配置

Jev 的 config_path 与环境覆盖决定提供方/模型；Planner 使用独立配置和可选推理强度。QWEN_API_KEY 是原始 judge 的独立需求，不等于已有 OpenRouter key。这里只记录变量名，值不采集。^[src/bokkio/jev.py#L14] ^[src/bokkio/planner.py#L151] ^[src/bokkio/office_judge.py#L18]

## 模型与证据范围

Office native scope 尝试去掉 recent 子树、非任务窗口及外部分享动作；真实 GUI 场景仍需验收。发布证据只含合成窗口/输入，解包 Office XML 也需接受个人路径、邮件、凭据模式扫描。^[src/bokkio/office_runner.py#L80] ^[docs/SECURITY-REVIEW.md#L62]

## Wiki 维护

raw 来源快照来自当前 Git 版本，正文 hash 校验；它们不可修改。更新事实时新增快照并刷新编译页，不引入主目录私有配置。操作和 lint 追加到日志。参见 [[SCHEMA]]。

关联：[[entities/planner-and-jev]]、[[concepts/evidence-and-scoring]]、[[summaries/pending-and-known-gaps]]。
