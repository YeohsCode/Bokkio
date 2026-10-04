# TASK-P0P1：前置验证环境 + 最小 macOS AX 读取层

先通读 `PLAN.md`（总计划）和 `docs/RESEARCH.md`（研究方案），本次只做 **P0 + P1** 两个阶段，P2 之后不做。

## P0：前置调研与验证环境（按 PLAN.md §P0）

目标：验证底层 Runtime 选型，产出验证记录，不写产品功能。

1. **xa11y 验证（重点）**：从 GitHub 找到 xa11y 仓库，克隆到 `vendor/`（或按其安装方式安装），在本机实际安装并运行其示例，验证：
   - macOS AXUIElement backend 能读取真实应用（TextEdit / Finder / 浏览器）的 Accessibility Tree
   - Selector、Element 操作 API 的形态
   - Python / Rust / JavaScript 绑定中哪个在本机可用
   - 安装方式、权限要求（辅助功能授权）、异常表现
2. 若 xa11y 无法满足，评估备选并记录差异（不要直接重写 runtime）。
3. 阅读 agent-desktop、computer-use-jev / jev-desktop、computeruseprotocol 的设计，只提取 API 设计要点，写进 `docs/NOTES.md`。
4. 建 macOS 测试样本清单：Finder、TextEdit、浏览器、系统设置。
5. 输出 `docs/P0-VERIFICATION.md`：xa11y 是否满足 P1 读取层要求；不满足则列出缺失能力。

## P1：最小 macOS AX 读取层（按 PLAN.md §P1）

优先用 xa11y 的 macOS backend；不足时才封装原生 AXUIElement（用 Python/PyObjC 或 Swift 均可，但接口按未来 Rust Runtime 边界设计）。

实现 CLI：`bokkio`（Python 入口即可），命令：
- `bokkio apps` — 列出可见应用
- `bokkio windows --app <pid或名称>` — 列出应用窗口
- `bokkio snapshot --app <...> [--window <...>]` — 输出完整 AX 树（tree 视图 + `--json` JSON 视图）
- `bokkio find --app <...> --role <role> [--name <name>]` — 查询元素
- `bokkio get <ref>` — 读取单个元素详情

元素字段：`ref`（稳定 id）、`role`、`name`、`value`、`state`、`bounds`、`parent`、`children`、`platform_data`（macOS 原始 AX 属性），取不到的字段显式 null。

要求：
- 元素引用在两次 snapshot 间尽量稳定（记录稳定性规则）
- 辅助功能权限未授予时报错信息明确指出权限问题
- 本阶段只读，不实现 click/type/set value
- 至少对 3 个应用（TextEdit、Finder、Safari 或 Chrome）实测 snapshot，其中含一个表现较差的应用，差异记入 `docs/P1-REPORT.md`

## 验收（必须自测，不停在理论上能跑）

1. `bokkio apps` / `snapshot` 在 TextEdit 上真实跑通，把 JSON 输出样例（截断到合理长度）贴进 P1 报告
2. `pytest` 通过（元素字段完整性、树结构、find 查询）
3. 每完成一个阶段 git commit（P0 一个、P1 一个），commit message 用 `feat(bokkio): ...` / `docs(bokkio): ...`
4. 生成 `docs/P0-VERIFICATION.md` 和 `docs/P1-REPORT.md`
5. 若某步被权限/环境卡死，记录卡点与绕过尝试，不要伪造输出；最后在报告里明确说"哪些验收项未达成及原因"

## 边界

- vendor-neutral：不硬编码任何 LLM 供应商名（本阶段不涉及 LLM 调用）
- 不做 Windows、不做 Jev、不做 LLM、不做 Recorder
- 若某工具文档与实际行为不符，以实测为准并记录