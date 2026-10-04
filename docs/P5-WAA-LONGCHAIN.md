# P5：WindowsAgentArena 原生多步实测

日期：2026-10-04（北京时间）。Office 激活按用户要求暂缓；本轮使用 **Explorer + Notepad**，真实 Planner → Jev → UIA。没有通过浏览器、shell 或文件 API 代替 agent 完成输出。

后续诊断、修复与复测见 [修复报告](P5-WAA-RECOVERY.md)。本文保留原先 15 次尝试的结果。

## 结果

固定三题，五轮共 **15 次尝试，端到端通过 0/15；最后一轮 0/3**。所有轮次的三项指定版本 metric 分数均为 0。没有生成目标交付文件，因而没有完成新进程重开验收。这些是发现 P5 缺口的开发试跑，不能作为官方榜单成绩。

| 固定任务 | 流程 | 最后一轮 | 动作尝试 / 重规划 | 最后阻断 |
| --- | --- | --- | --- | --- |
| png-list | Explorer 查找 PNG → 读取文件名 → Notepad 清单 → 保存 → 重开 | blocked | 0 / 2 | 决策置信度低于阈值 |
| size-report | Explorer 读取大小 → 筛选 >5MB → Notepad 报告 → 保存 → 重开 | failed | 4 / 1 | UIA `FindFirstBuildCache` 超时 |
| word-count | Notepad 打开输入 → 读取/统计 example → 写数字 → 另存 → 重开 | failed | 3 / 1 | UIA `FindFirstBuildCache` 超时 |

“动作尝试”取 agent 的 `actions`，其中可能包含派发后失败的调用；成功派发与结果见逐步 trace。`completed_steps` 是子任务 ID 记录，不能单凭个数认定业务完成。

大小报告在第三轮已完成原生尺寸验证、Notepad 写入、打开 Save As 和设置完整目标路径；第五轮仍有运行波动。计数任务打开过 Open 对话框并填写输入路径，但未取得输入正文的原生读取证据。PNG 源文件列表可读取，搜索框操作尚未完成。**局部推进不等于端到端通过。**

## 固定任务与环境

WAA revision：`6d39ed88c545a0d40a7a02e39b928e278df7332b`。三题在首次执行前固定，与原先五项未运行 pilot 分开记录。

| Case | 上游配置（相对 examples/） | 初始化 |
| --- | --- | --- |
| png-list | `file_explorer/016c9a9d-f2b9-4428-8fdb-f74f4439ece6-WOS.json` | 三个上游 PNG 输入 |
| size-report | `file_explorer/2d292a2d-686b-4e72-80f7-af6c232b1258-WOS.json` | 两个上游文件 + 15,000,000 字节 testing.bin |
| word-count | `notepad/a7d4b6c5-569b-452e-9e1d-ffdb3d431d15-WOS.json` | 上游 largefile.txt；实际仅 1,129 字节 |

VM：Windows 11 IoT Enterprise LTSC Evaluation ARM64，build 26100；Notepad `10.0.26100.8457`，Explorer `10.0.26100.8117`。使用既有 Python 3.12 x64 / xa11y 0.15 环境。模型记录在 trace：Planner `z-ai/glm-5.3-flash`，Jev `typesafe/jev-1.13-20260917`。每题最多 32 次动作尝试、2 次重规划。

这三题覆盖读取、判断、跨应用写入和保存等多步链路，**尚未覆盖 WindowsWorld 的职业办公长流程、OSWorld 2 的长时任务或大文本压力测试**。WindowsWorld/OSWorld 2 继续作为设计参考；微软 Office 任务待可用许可证后恢复。

## 执行与独立验收

- 每题、每轮建立独立随机目录，绑定 Pictures / Downloads / Desktop / Documents。只启动测试自己的 Notepad 和 Explorer 窗口；Explorer 用 HWND 绑定，结束后只关闭拥有的窗口/进程。
- 初始化复制上游输入；用等价文件创建代替上游 `fsutil` 创建 testing.bin。准备脚本可以使用文件 API；被测 agent 只能使用原生操作。
- 原始 JSON、输入/gold 下载 URL、字节数和 SHA-256 在 manifest 中。Gold 不进入规划或决策上下文，仅在执行后用于 metric。资源 URL 原本指向远端分支；本轮保存下载内容哈希。重新下载时应核对是否一致。
- 导出并校验指定 revision 的四个函数：`exact_match`、`compare_text_file`、`get_all_png_file_names`、`get_is_file_saved_desktop`。保留函数正文及 MIT license；导出的代码 SHA-256 在 runner 中固定，变化时拒绝导入。Getter 的传输层改为只读本地适配。
- 最终验收要求 agent completed、指定版本 metric=1、原生读取/编辑/Save As/目标路径/保存按钮证据、文件存在，以及独立 Notepad 新进程重开。大小报告额外要求文件名集合精确匹配；上游 getter 本身只检查包含 testing.bin。
- 上游计数题 postconfig 的再次打开和 Ctrl+S，改为独立新进程重开与字节未变化检查。没有接入完整官方 server/runner，也未复刻官方 OS 镜像；以上环境、路径和 postconfig 改动决定本轮只能标记为 **adapted development run**。
- 第一至第三轮的 `native_save_dispatched` 曾把菜单 Save 计入保存证据；第四轮起改为要求 Save **button**。第三轮大小报告原始字段为 true，但审计结果为 false；原始记录保留，修正见 [证据审计](evidence/2026-10-04-waa-longchain/evidence-audit.json)。总通过数始终为 0。

## 五轮记录与修复

| 轮次 | 配置/变化 | 通过数 | 主要发现 |
| --- | --- | --- | --- |
| first | 原有默认 Planner | 0/3 | 三题均在规划阶段截断，0 次动作 |
| v2 | Planner reasoning effort=low | 0/3 | 能返回计划；Size 同名验收不成立；菜单/文件操作暴露原生缺口 |
| v3 | 成功条件增加 parent_name；动态窗口与完整路径规划提示 | 0/3 | Size 精确验收通过，推进到 Save As 路径填写；保存仍被置信度拦住 |
| v4 | 目标路径不参与名称候选；对话框不作为整片子树匹配；纠正保存证据 | 0/3 | 仍有低置信度和 UIA 超时，部分错误目标操作保留在 trace |
| v5 | 验收 JSON 键名不作为 UI 名称候选 | 0/3 | 最后结果见首表；仍未完成交付 |

首轮单独诊断记录：8,000 completion tokens 全为 reasoning，content 为空，finish_reason=length。模型元数据显示默认 effort=max 且 reasoning mandatory，支持 low/high/max；所以选择 low，保留截断拒绝逻辑。第二轮 PNG 初始规划用了 465 reasoning tokens 并返回完整 JSON，约 10.5 秒。低档推理解决了本轮起始规划截断，但**没有解决原生操作失败**。[OpenRouter 推理预算说明](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens)、[模型元数据入口](https://openrouter.ai/api/v1/models)。

代码变化：

1. Planner 支持参数、`BOKKIO_PLANNER_REASONING_EFFORT` 或 private planner.json 的 `reasoning_effort`；未设置时保持 provider 默认。Runner 显式使用 low。需选择模型支持的档位。
2. 成功条件可用 `parent_name` 精确区分重复字段，仍要求唯一候选。旧四字段条件与旧 checkpoint 保持可读。
3. 候选名称匹配排除 Windows 绝对路径、对话框整片展开，以及验收 JSON 的键名；原目标、路径值和完整条件仍发送给决策模型。
4. 新增准备/执行工具，校验任务和输入哈希，独立 metric、原生中间证据与最终文件验收，保留所有尝试。

回归：**macOS 124/124，Windows 124/124**。Windows 有一条 pytest 缓存目录写权限 warning，测试本身通过。新增测试覆盖同名字段父级约束、预算配置/截断拒绝、目标路径与 JSON 键名候选、Explorer HWND 隔离、变更 evaluator 拒绝、无源读取/保存证据时不能算通过。准备工具重新导出并下载后，三题 JSON、所有输入/gold 和 metric 正文与首轮一致。

## 下一步（仍在 P5）

1. **原生能力与定位。** 复现 Explorer 的 Search Pictures 包装/子控件及 UIProperty 字段；核对可写能力、重复身份和实际 UIA pattern。处理 Open/Save 对话框中的同名字段、文件名隐藏和动态窗口。
2. **原生观察超时。** 定位 `FindFirstBuildCache(...)=0x80131505`；记录单次调用耗时，做有限重试/进程隔离，保持窗口范围和 stale-ref 检查。当前原因尚未证明是 ARM 仿真、xa11y 缓存还是特定 provider。
3. **阶段规划。** 打开资料后重新获取正文，再生成依赖正文的 allowed_values、计数与后续验收。避免首次完整规划虚构未知计数，或用焦点/窗口标题代替业务事实。
4. 重跑原先固定三题并保留失败。稳定交付后再扩大 WAA 子集、适配完整官方 runner，推进 P6。Office 与 macOS 对照继续保留为待办。

## 重跑

准备（Mac 或 Windows；输出目录必须是新的）：

```bash
python scripts/prepare_waa_longchain.py --checkout /path/to/WindowsAgentArena --output /path/to/bundle
```

Windows 活跃用户会话中执行（已配置真实 Planner/Jev）：

```powershell
.venv\Scripts\python.exe scripts\verify_waa_longchain.py `
  --bundle C:\BokkioWorkspace\longchain-bundle `
  --output C:\BokkioTasks\waa-longchain-next
```

默认固定三题；`--rounds 1..3`。每次使用新目录，不覆盖既有失败。当前代码不能宣称稳定完成这三题。

证据：[全部轮次与初始化](evidence/2026-10-04-waa-longchain/)、[最后一轮](evidence/2026-10-04-waa-longchain/waa-longchain-v5/summary.json)、[失败索引](evidence/2026-10-04-waa-longchain/failure-index.json)、[初始预算诊断](evidence/2026-10-04-waa-longchain/longchain-planner-diag.json)。完整 UIA/model/action trace、原始上游 JSON 与导出 metric 代码压缩为 gzip，保留原始字节；其他文本证据统一为 LF 换行；不含 API key。输入/gold 文件未直接提交，可按记录重建并校验哈希。

## English summary

Office activation is paused at the user's request. Three fixed WAA Explorer/Notepad tasks ran through the real Planner/Jev/native UIA loop in isolated folders: PNG listing, a size-based file report and counting occurrences in a text file. Five development rounds made 15 attempts: **0/15 completed, with 0/3 in the final round**. No target deliverables were persisted. Every failure and retry is retained.

This run added configurable planner reasoning effort, parent names for unique success checks, and fixes for irrelevant action candidates introduced by destination paths, dialog names and verification JSON keys. The size-report task advanced through reading sizes, editing Notepad and filling Save As in an earlier round, but final delivery remains unreliable. Low confidence and native UIA cache timeouts remain unresolved; 124 isolated tests passed on both hosts.

Pinned evaluator functions were reused independently, with explicit transport, path, OS and postconfig adaptations. These are development results, not official leaderboard scores or completed WindowsWorld/OSWorld 2 evaluations. Continue P5 by repairing native capability/identity and dialog handling, diagnosing observation timeouts, and planning again after new source text is read. Re-run the same tasks before expanding coverage or entering P6.
