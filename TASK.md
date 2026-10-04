# Bokkio — 项目启动任务：通读研究方案，产出分阶段 Plan

你（codex）是本项目的首席工程师。本仓库是 **Bokkio** 的项目根。

## 第一步（本次运行的全部范围）

1. **先通读** `docs/RESEARCH.md`（Windows + macOS 跨平台 AI Computer Use / RPA 研究方案，2026-09-23 核验）。这是唯一的需求来源，不要凭空扩展需求。
2. 基于该文档，产出一份**分阶段开发计划**，写入 `PLAN.md`，要求：
   - 按研究方案第 1.1 节的架构图组织：LLM 高层规划 → Jev 快速决策 → Native Accessibility Runtime（Windows UIA / macOS AXUIElement）→ Native Apps
   - 每阶段：目标、范围（做什么/明确不做什么）、技术选型（结合 RESEARCH.md 第 2 节对现有工具的调研结论）、可验证的验收标准、预估工作量
   - 阶段顺序建议从**最小可跑通的 macOS AX 读取层**开始（本机是 macOS，可先落地验证），Windows UIA 放后续阶段
   - 明确列出风险与开放问题（如 Jev 决策头接入方式、免安装 vs 需辅助权限等）
3. 在 `PLAN.md` 末尾给出一个"下一步建议"：第一个阶段具体怎么开工。
4. **本次运行只做计划，不写实现代码。**

## 约束

- 技术选型引用 RESEARCH.md 里已核验的工具/仓库结论；如需补充调研，用网络查证后再写入，不要编造。
- 语言：中文。
- 完成后 `git add -A && git commit -m "docs: Bokkio 分阶段开发计划（基于 RESEARCH.md）"`。