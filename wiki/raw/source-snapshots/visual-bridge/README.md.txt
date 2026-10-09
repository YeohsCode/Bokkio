---
source_path: README.md
source_version: working-tree
ingested: 2026-10-09
sha256: cccc614f9baad60d80c0d8060cb30331884c0bdf4f05c93e7905e1aa1b3575f8
---

# Bokkio

面向 Windows 与 macOS 的原生桌面自动化项目，探索确定性 Workflow、Jev 局部决策与 LLM 全局规划的协作。

A native desktop automation project for Windows and macOS, exploring how deterministic workflows, Jev UI decisions and LLM planning can work together.

**当前版本 / Current release:** `0.1.0` — Windows UIA / macOS Accessibility CLI，已接入真实 Jev / Windows UIA and macOS Accessibility CLI with real Jev integration.

[中文](#中文) · [English](#english)

**项目知识库 / Project knowledge base:** [LLM Wiki](wiki/index.md) · [维护规则 / Maintenance schema](wiki/SCHEMA.md) · [维护日志 / Change log](wiki/log.md)

## 中文

### 项目背景

Bokkio 源于一个具体需求：在 Windows 和 macOS 上，通过统一接口读取原生应用的 UI 元素，并逐步完成点击、输入、选择和跨应用流程自动化。项目希望具备类似 UiPath 的元素树与流程重放能力，同时引入 AI 来处理任务规划和 UI 变化。

底层优先使用操作系统提供的真实 UI 结构：Windows UI Automation（UIA）和 macOS Accessibility（AXUIElement）。按钮、文本框、菜单和表格应尽可能通过角色、名称、状态及父子关系定位；当 Accessibility 信息不足时，再引入 OCR 与视觉操作兜底。Bokkio 的 Computer Use 覆盖桌面应用、系统设置和跨应用流程；浏览器只是其中一种测试环境。

长期目标是把一次成功的 Agent 执行过程转化为可保存、可验证、可重复执行的 Workflow。重复任务走确定性重放，遇到 UI 变化或执行失败时，再由 Jev 或 LLM 协助恢复。

项目需求来自 [研究方案](docs/RESEARCH.md)，实施范围与验收标准见 [分阶段计划](PLAN.md)。这些文档描述目标设计；当前交付范围见下节。

### 当前进展

截至 **2026-10-09**：

**总体位置：P6 Windows 验收完成，P7 部分实现。** Office 原题已实跑十轮，各轮独立评分 **0/3**；最新失败为 Word 输入后确认、Excel 输入前窗口/前台拒绝与 PowerPoint 决策置信度不足。独立 Excel 脚本探针完成字段替换和保存校验，完整 Agent 任务与最新字段 transport 尚未通过。主机回归 **435/435**，Windows 历史 **373/373**。见 [实跑报告](docs/evidence/2026-10-08-office-live/README.md)。

Mac公共视觉接口和Agent/CLI OCR降级已落地；最新自绘窗口只读观察与真实Jev决策3/3，真实输入仍待验收。见[视觉接入](docs/P7-VISUAL-BRIDGE.md)。

完整阶段位置见 [总体进度](docs/STATUS.md)，按优先级执行的剩余项见 [Pending](docs/PENDING.md)。以下保留各阶段的历史验收与对应分母：

- **P0：macOS 环境与授权已验证。** xa11y 构建、Python 绑定和原生 Cocoa 测试应用可用；Fusion 与 Windows 11 ARM 虚机已配置，Windows 已安装，账户已验证。
- **P1：实机读取已验证。** TextEdit、Finder、系统设置和固定原生应用的 AX 树均可读取；Safari 本地页面作为兼容性样本。本轮枚举到 35 个应用，元素查询、窗口筛选和 ref 查找通过验证。
- **P2：核心原生动作闭环通过三轮测试。** 按钮点击后的状态变化、文本写入与输入、焦点、表格行选择均验证成功；下拉框写值和单选按钮选择也通过验证；新增三轮原生滚动往返测试通过。114 项隔离测试通过。
- **已知限制：** Finder 的三组连续快照 ref 已保持一致，仍需验证节点重排与虚拟化；TextEdit 部分节点角色为 `unknown`。滚动支持暴露数值滚动条的 macOS 容器和暴露 ScrollPattern 的 Windows 容器；2026-10-06 的 macOS 双轴滚动、三条模型跨应用任务和 Workflow 对照已通过；文件流程与虚拟化继续扩展，见 [Mac 续测](docs/MACOS-FOLLOWUP.md)。
- **P3：Windows UIA 验证通过。** 虚机内五个应用读取、三轮原生 WinForms 动作、失效 ref 和 50/100/300/1,000 控件性能基准均已完成；Windows 114 项隔离测试通过。实测差异见 [P3 报告](docs/P3-REPORT.md)。
- **Runtime 续测通过：** Windows 方向滚动、空值回读、只读能力检查、顶层窗口筛选、重复控件重排与重建，以及真实 Notepad 输入。50 条原生测试记录和五种决策动作链路见 [续测报告](docs/RUNTIME-FOLLOWUP.md)。
- **P4 实测推进中：** OpenRouter Jev 已配置；五个原生离线样本命中，Windows 五个实时任务通过，包含两步下拉选择。四类原生难例通过。收窄目标上下文后，四档规模开发样本多轮达到 12/12；新增 1,000 控件原生点击三例通过。详见 [P4 报告](docs/P4-REPORT.md)。P5 首版已通过七步跨应用流程、两次连续变化恢复、暂停恢复及应用重启续测，详见 [P5 续测](docs/P5-FOLLOWUP.md)；P6 的 Recorder/Workflow 已完成 Windows 原生验收，视觉兜底待 P7。

- **P5 阶段恢复与文件交付基础：** 修复历史中间状态被覆盖后的重复执行；真实 Planner/Jev 在第二阶段完成后暂停，恢复仅执行剩余一步。Notepad 原生菜单保存、文件校验与新进程重开三轮通过。后续已安装七款 Office 应用并通过原生启动读取；激活与邮箱配置待完成，见 [Office 安装记录](docs/WINDOWS-OFFICE-SETUP.md)。基础动作证据见 [前置实测](docs/P5-OFFICE-PREREQUISITES.md)。
- **P5 部分暴露续测：** 新增每页只暴露 25 个 UIA 条目的原生分页应用，两条真实 Planner/Jev 流程通过，包括换页后选择 Row 997 并写入 Notepad；旧引用返回 `stale_ref`。已记录模型与原生调用耗时，见 [分页报告](docs/P5-PAGED.md)。

**WAA 修复续测：** 固定三题最新两轮各 **3/3**：PNG 清单、大小报告、计数文件均完成原生流程、持久化和新进程重开；源文件哈希保持不变。修复搜索重复身份、对话框文本提交、词频与阶段规划；缺少交付文件会触发补救。失败原因与最新原生验收见 [修复报告](docs/P5-WAA-RECOVERY.md)。

**此前 P5 变体验收：** 六种新输入各有通过记录；完整 v5 为 5/6、定向 v6 为 3/3，最终 PNG v8 为 1/1。需求变更最终通过 2/2，交付 7 → 5 并保留旧文件和历史。macOS / Windows 各 195 项隔离测试通过。实现完整源路径约束、需求版本与产物哈希，并修复原生菜单导航、勾选验收和同名 Open 按钮；见 [全部分轮结果](docs/P5-NATIVE-VARIATIONS.md)。

**固定五题 pilot：** 最终同代码 v26、v27 完整复测各 4/5，五项 Agent 全部 completed，中间步骤与独立产物验收通过。导航路径正确，原始精确标题评分因环境后缀差异仍为 0。修复原生边界读取崩溃、Settings 准备和同名控件验收；Settings 三次定向复测各 1/1。保留全部失败与真实分母，见 [pilot 报告](docs/P5-WAA-PILOT.md)。

**P6 历史 Windows 验收（2026-10-05）：** 最终代码的六步录制重放 **3/3**、真实 Notepad trace 保存/重开 **3/3**；一份七步跨应用模板换三组参数 **3/3**，重启恢复仅执行剩余一步，结构变化与真实模型修复通过。主机和 Windows 各 **292 项隔离测试通过**；见 [P6 验收](docs/P6-CLOSURE.md)。

**Mac 原生续测（2026-10-06）：** 动作与真实模型跨应用各 3/3；录制及成功 trace 重放各 3/3，双轴滚动、结构重排与暂停恢复通过。修正 `table_row` 选择能力，主机回归 293/293；见 [报告](docs/MACOS-FOLLOWUP.md)。

**Mac Office 交互测试（2026-10-07）：** Excel 计算、Word/PPT 摘要、Outlook 草稿附件、需求修订与关闭后重开完成；六份保存文件独立校验通过，金额 320 → 370，三份 v1 哈希保持不变。UI 由 CUA 操作，Bokkio 仅作读取诊断；Office 编辑区元数据、Excel 单元格观察与 Outlook 遍历仍需适配，尚未完成 Bokkio Agent/Workflow 办公验收。见 [Office 报告](docs/MACOS-OFFICE-REPORT.md)。

**P7.1 已开始实现（2026-10-08）：** Windows 客户区截图 CLI、窗口身份/DPI/物理坐标元数据、自绘 fixture 和验收脚本已实现；主机与 Windows 各 314 项隔离测试通过。guest 捕获前置检查返回 `desktop_unavailable`，三轮交互像素验收待可用 Windows 桌面。见 [P7.1 报告](docs/P7-CAPTURE.md)。

**Mac 路径复查（同日）：** 独立 ScreenCaptureKit 自有窗口截图诊断 3/3；当前 AX 前置检查失败。可继续 Mac 截图与视觉研发，生产 Runtime 接入和动作验收待完成，见 [复查报告](docs/MACOS-CAPTURE-PROBE.md)。

**Mac P7 Runtime（同日）：** 截图已接入包与 CLI，本机 Vision OCR 和目标候选定位三轮 3/3、八类拒绝 8/8；两端隔离回归各 355/355。有界输入执行器已实现，但实机前置检查零派发拒绝，点击/输入与自动 Agent 降级尚未验收。见 [报告](docs/P7-MACOS-VISUAL.md)。

**微软 Office 原题 pilot（2026-10-08–09）：** 固定三道 L1 原题、初始化、原生 runner、独立评分与原始 VLM 入口已实现；早期会话阻断后完成十轮实际执行，各轮 0/3。AXConfirm、只读选区、窗口身份与阶段规划已修复，剩余失败及脚本能力证据分别保留。见 [执行报告](docs/OFFICE-PILOT-READINESS.md)。

当前实现为 **Python + xa11y 0.15.x**，Windows 额外使用 comtypes 读取原生 UIA ValuePattern 与 ScrollPattern；经典对话框 Edit 的文本提交使用已验证的 Win32 编辑消息。后续核心 Runtime 优先考虑 Rust；统一元素模型参考 CUP（Computer Use Protocol），目前尚未实现完整 CUP 协议适配。Jev 使用 OpenRouter Decisions API 的 `typesafe/jev-1.13`，也保留 TypeSafe 直连选项。当前小样本结果不能代表通用桌面成功率。

### 目标架构

```text
用户目标 / 自然语言
        ↓
LLM / Planner                 拆解任务与定义成功条件
        ↓
Jev                           选择当前元素与下一步动作
        ↓
Unified Element Runtime       元素模型、定位与执行
        ↓
Windows UIA / macOS AX         访问原生应用

执行轨迹 → Recorder → Workflow → 确定性重放
Accessibility 信息不足 → OCR / Vision / 坐标操作兜底
```

当前已实现 **原生读取与动作、真实 Jev、P5 规划循环、P6 语义录制、参数化与可恢复确定性重放**，P7 已增加 Mac 窗口捕获/OCR；完整视觉执行链路待完成。

### 安装与权限

前置条件：macOS 或 Windows、Python 3.9+、已安装 `uv`。从新环境开始：

```bash
git clone https://github.com/YeohsCode/Bokkio.git
cd Bokkio
uv sync --group test
uv run bokkio --help
```

在 **系统设置 → 隐私与安全性 → 辅助功能** 中，给运行 CLI 的宿主应用（例如终端）或实际 Python 解释器授权，重新运行 CLI；若权限仍未生效，再重启宿主应用。早期完整 AX 读取曾通过；2026-10-06 自有 Cocoa fixture 的 AX 读取和动作已恢复并通过续测；权限缺失仍需按错误提示处理。

Windows 通过 UIA 读取原生桌面；建议先在自己的可丢弃测试文件和应用窗口上验证。当前实测环境为 Windows 11 ARM64 虚机和 x64 Python 3.12。

权限缺失时，CLI 返回非零退出码并提示授权位置。若只能读取菜单栏等局部内容，请检查权限及目标应用的 Accessibility 支持情况。

### 使用方法

先打开目标应用，再执行：

```bash
uv run bokkio apps
uv run bokkio windows --app TextEdit --json
uv run bokkio snapshot --app TextEdit
uv run bokkio snapshot --app TextEdit --json
uv run bokkio snapshot --app TextEdit --window 0 --json
uv run bokkio find --app TextEdit --role button --name Save
uv run bokkio get REF --app TextEdit
uv run bokkio act --app TextEdit --action click --ref REF
uv run bokkio act --app BokkioTest --action set_value --role text_field --name Search --value ""
uv run bokkio act --app BokkioTest --action type --role text_field --name Search --value "Hello" --expect-value "Hello"
uv run bokkio act --app BokkioTest --action scroll --role scroll_bar --direction down --amount 0.25
```

- `--app` 接受 PID 或应用名称；使用 `apps` 返回的名称。
- `--window` 优先匹配完整窗口 ref、原生稳定 ID 和完整标题，再匹配从 0 开始的索引或标题子串。
- `snapshot` 默认输出缩进树，`--json` 输出完整数据。未指定窗口时，从应用根节点读取，包含应用级节点和菜单栏。
- `find` 按 role 和可选 name 做不区分大小写的精确匹配；名称必须符合目标应用的语言与实际 AX 内容，示例中的 `Save` 仅为示意。
- `find` 和 `get` 默认输出 JSON。将 `REF` 替换为应用级 JSON snapshot 或 `find` 返回的完整 ref；树形视图只显示前 8 位。
- `get` 重新读取当前应用树。窗口快照和应用快照中的同一元素共用 ref。
- `act` 提供 `click`、`invoke`、`type`、`set_value`、`select`、`focus`、`scroll`、`expand`、`collapse` 和 `submit` 接口；通过 `--ref` 或 `--role` 配合可选 `--name`、`--parent` 定位。`type` 与 `set_value` 需要 `--value`。`submit` 限于 Explorer 的可写原生字段；发送 Enter 前核验窗口、焦点、进程、RuntimeId 和字段值。动作会返回执行前后元素和验证状态。只有对已授权的测试应用执行动作。

`set_value`、`focus`、`select`、`expand`、`collapse` 和 `scroll` 检查执行后的值或状态；`type --expect-value` 检查输入结果。click 及未指定期望值的 type 返回 `observed`，需要任务自己的成功条件。滚动需指定 `--direction up/down/left/right`；`--amount` 是整个滚动范围的比例，默认 `0.25`。可定位滚动条或其容器内的元素；Windows 使用容器 ScrollPattern；位置与内容均变化才确认滚动。目标不支持时明确报错，到达边界返回 `unconfirmed`。实测证据见 [P2 报告](docs/P2-REPORT.md)。

### 元素数据与引用

每个元素包含：

| 字段 | 含义 |
|---|---|
| `ref` | 基于应用身份和结构路径生成的 20 字符哈希 |
| `platform`, `actions` | 平台名称与规范化的原生动作能力 |
| `role`, `name`, `value` | 元素角色、名称与值 |
| `state` | enabled、focused、selected 等状态 |
| `bounds` | `x / y / width / height`，不可用时为 `null` |
| `parent`, `children` | 父元素 ref 与嵌套子元素列表 |
| `platform_data` | 原始 AX 数据，以及 description、actions、native stable ID |

缺失值使用显式 `null` 或空结构。JSON snapshot 外层包含 `app`、`window_filter` 和 `windows`；未指定窗口时，`windows` 中保存应用根树。

ref 是基于当前结构的引用。TextEdit、系统设置和固定应用的连续快照 ref 保持一致；Finder 在三组连续读取中，动态文本名称变化但 ref 集合保持一致。`structural-v3` 对父节点下唯一的不可点击 static_text 忽略名称变化，Windows 唯一 HWND 进入身份路径，使重复控件重排后 ref 保持稳定、重建后旧 ref 失效；交互控件仍保留名称身份。旧快照需重新获取。应用重启、交互控件改名、结构变化和兄弟节点顺序变化都可能使引用失效。窗口列表、窗口快照与应用快照共用 ref。`get` 找不到 ref 时会要求重新获取 snapshot；`act` 遇到 stale ref 返回结构化错误。

### 待办与路线图

| 阶段 | 内容 | 状态 |
|---|---|---|
| P0 | 依赖、权限与参考实现验证 | macOS 完成；Windows 虚机已配置，系统与账户已就绪 |
| P1 | macOS AX 只读 CLI | 实机矩阵已验证；动态 ref 限制已记录 |
| P2 | Unified Element、Selector 与 macOS 操作 | 核心动作及三轮滚动通过；稳定性覆盖继续扩展 |
| P3 | Windows UIA 读取与操作 | 五应用读取、三轮动作和四档规模基准通过 |
| P4 | Jev 局部决策与评测 | 真实五任务及难例通过；大树开发样本 12/12，三例实时大树点击通过 |
| P5 | LLM 任务规划与执行循环 | 首版已实现；Windows 七步流程、恢复及分页部分暴露通过，macOS 三条模型对照通过；独立应用继续扩展 |
| P6 | Recorder 与确定性 Workflow 重放 | Windows 验收完成；参数、文件版本、恢复与模型修复通过 |
| P7 | Vision / CUA 兜底与可靠性加固 | Mac 采集/OCR 已验收；Windows 像素、真实输入、自动降级与完整可靠性待完成 |

### 当前阶段与后续工作

**P6 完成，P7 当前为部分实现与验收。** Mac 捕获/OCR 已通过；输入正向、自动降级和 Windows 实机视觉仍待完成，Office原题早期受环境阻断，同日恢复后新工作区已可试跑。

1. 使用已通过Mac输入检查的新工作区实际运行固定三题 Office pilot，独立核验保存文件和全部失败。
2. 修复真实 Office 原生覆盖，接入 Planner/Jev/Workflow 视觉降级并完成 click/type 正向验收。
3. 扩展 Windows 视觉、Mac 文件/进程恢复、多显示器/比例和可靠性，随后对齐完整上游测试环境。

详见 [总体进度](docs/STATUS.md)、[P7 计划](docs/P7-PLAN.md) 和 [Pending](docs/PENDING.md)。

### Computer Use 测试集

已固定 WindowsAgentArena 源码版本、154 份任务配置及五项原生 pilot。另选三项 Explorer/Notepad 多步任务，已在 ARM64 虚机实际运行 Planner → Jev → UIA，并复用指定版本的 evaluator 函数独立校验；所有尝试见 [实测报告](docs/P5-WAA-LONGCHAIN.md)。这些是明确改动环境与路径的开发试跑，不能作为官方榜单得分。原先五项 pilot 已执行，逐次派发、中间检查、独立评分和失败记录见 [pilot 报告](docs/P5-WAA-PILOT.md)。WindowsWorld 的微软 Office 原始三题已导入，实际任务未开始；OSWorld 2 仍为长流程设计参考。接入边界见 [测试集接入计划](docs/BENCHMARK-PLAN.md)。

### Jev 决策入口

配置 `OPENROUTER_API_KEY`，或使用仓库外的私有 `jev.json`。开发验收环境已配置；克隆到新环境后，请设置自己的 API key。

- macOS：`~/Library/Application Support/Bokkio/jev.json`（文件权限 0600）。
- Windows：`%LOCALAPPDATA%\Bokkio\jev.json`。
- JSON 字段：`source: "openrouter"`、`model: "typesafe/jev-1.13"`、`api_key`。
- `BOKKIO_JEV_CONFIG` 可指定其他私有路径；环境 key 优先于文件。`BOKKIO_JEV_SOURCE` / `BOKKIO_JEV_MODEL` 可覆盖提供方与模型。直连 TypeSafe 使用 `TYPESAFE_API_KEY`。

```bash
uv run bokkio decide --app BokkioTest --goal '将 Search 设置为 "hello"' --allow-value hello
# 增加 --execute 可执行一次通过检查的决策
uv run python scripts/evaluate_jev.py --cases docs/evidence/2026-10-02-runtime-followup/jev-cases.json --output /tmp/bokkio-jev-evaluation.json
```

`decide` 默认只返回决策。它把所选应用或 `--window` 窗口的原生元素树发送给配置的 Jev 提供方；文字值来自 `--allow-value`。动作和目标通过闭集 Choice 选择，目标超过 255 项时分组选取；Noul 表示目标已满足的程度。执行前重读同一范围，拒绝快照变化、不支持的动作、失效 ref、低置信度和无法区分的重复节点。Choice 的 confidence 不是正确率，`done` 仍需任务自己的成功条件。

### P5 规划与执行入口

私有 `planner.json` 与 Jev 配置放在同一目录，字段为 `api_key` 和 `model`；本机及 Windows 的 Planner 已改为已验证的 GPT-4.1，Jev 保持不变。可用 `BOKKIO_PLANNER_CONFIG`、`BOKKIO_PLANNER_MODEL` 或 `OPENROUTER_API_KEY` 覆盖。`BOKKIO_PLANNER_REASONING_EFFORT` 或配置字段 `reasoning_effort` 可指定模型支持的推理强度；WAA runner 使用 `low`，未配置时保留提供方默认。

```bash
uv run bokkio run --goal '将 Search 设置为 hello 并提交' --allow-app BokkioWorkflowA --trace /tmp/bokkio-task.json --plan-only
# 执行时去掉 --plan-only；跨应用时重复 --allow-app
```

每个子任务都有原生可观察的成功条件。`--max-actions` 和 `--max-replans` 限制执行与恢复次数；`--max-phases` 限制读取新资料/打开对话框后的阶段续规划次数（默认 4）。`--require-file` 可重复指定必须存在的交付文件，恢复时保留相同要求。通过 `--control-file` 提供暂停/取消信号，再用 `--resume` 恢复同一目标和应用白名单。CLI 输出状态摘要，完整快照与模型/动作记录写入 trace。涉及发送、支付、删除等的步骤会被阻断。实现与实测限制见 [P5 报告](docs/P5-REPORT.md)。


Planner 的 `requires_action` 可要求子任务至少实际派发一次原生命令，避免以已经存在的选择状态证明 Copy/Paste 或地址提交。通常已满足的页面、选择或开关状态仍可直接验收。

`--require-source` 可重复指定原文的完整路径：执行前核验 Windows 经典 Open 对话框的原生路径读值，读取后保存当前需求版本的源事实；未读取指定源时阻止正文写入和完成。新需求必须重新读原文。此约束目前适用于英文 Windows 经典 Open 对话框。

需求变化时，使用 `--resume`、新的 `--goal` 和 `--amend-reason`，从暂停或已完成的检查点建立下一需求版本；应用白名单保持一致，累计预算继续计算。旧步骤保留在历史中，新需求重新观察并规划。`--require-file` 的已验证交付记录包含路径、大小和 SHA-256，写入 `artifact_versions`；它证明文件存在及当时的字节版本，内容正确性仍由任务验收检查。

### P6 录制与重放入口

先启动可丢弃原生应用并取得 PID；录制与重放分别显式绑定授权应用。重放直接调用 Runtime，不调用模型。

```powershell
bokkio workflow record --actions fixtures/workflows/interactions.actions.json --bind fixture=1234 --name "Native interactions" --output workflow.json
bokkio workflow replay --workflow workflow.json --bind fixture=5678 --output replay.json
```

支持 `workflow compile` 从成功 trace 固化；`workflow parameterize` 添加经过审查的文本/路径/哈希参数和输入/交付版本；`workflow replay --parameters values.json --resume paused.json` 在应用重启后恢复。用 `--window-bind alias=hwnd:0x...` 显式限定窗口。

`workflow repair --model-repair` 由模型从原生候选中修复失败 selector，生成保留父版本的新版本；随后重放不调用模型。原生客户端回执可接入 `Recorder.capture_receipt`，捕获时不重复执行动作。输入状态、合约、条件和完整命令见 [P6 文档](docs/P6-WORKFLOW.md)。

### 开发与文档

```bash
uv run --group test pytest -q
```

292 项隔离测试覆盖逐步派发、原生提交保护、字段、树结构、ref、查询、窗口筛选、动作、滚动、动态文本与错误。真实桌面验证另用 `scripts/verify_native.py`：先启动名为 `BokkioTest` 的固定原生应用及矩阵中的应用，创建空白 TextEdit 窗口，再执行：

```bash
uv run python scripts/verify_native.py --output /tmp/bokkio-evidence
```

脚本会操作固定测试应用，并保存读取摘要和动作结果；当前实测证据及测试应用构建步骤见 [验证指南](docs/evidence/2026-10-01-followup/README.md)。

- `src/bokkio/`：CLI、元素模型与 xa11y 适配层。
- `tests/`：隔离单元测试。
- [研究方案](docs/RESEARCH.md)：项目背景、候选技术与目标架构。
- [阶段计划](PLAN.md)：P0–P7 范围与验收标准。
- [P0/P1 任务书](TASK-P0P1.md)：当前交付范围。
- [P0 验证记录](docs/P0-VERIFICATION.md)、[设计笔记](docs/NOTES.md)、[P1 报告](docs/P1-REPORT.md)、[P2 报告](docs/P2-REPORT.md)：验证证据、实现说明和未达成项。

发布前的历史和压缩测试证据已完成密钥与隐私检查，见 [检查记录](docs/SECURITY-REVIEW.md)。

## English

### Background

Bokkio started from a practical need: inspect native UI elements through one interface on Windows and macOS, then use those elements to click, type, select, and automate tasks across applications. The project aims to combine UiPath-like element trees and workflow replay with AI for task planning and adaptation to UI changes.

The runtime prioritizes the UI structure exposed by the operating system: Windows UI Automation (UIA) and macOS Accessibility (AXUIElement). Buttons, text fields, menus, and tables should be located through roles, names, states, and parent–child relationships where available. OCR and visual actions are planned fallbacks when accessibility data is insufficient. Bokkio's Computer Use scope includes desktop applications, system settings, and tasks across applications; a browser is one test environment within that scope.

The long-term goal is to turn a successful Agent execution into a saved, verifiable, repeatable workflow. Recurring tasks use deterministic replay; Jev or an LLM can help recover when the UI changes or execution fails.

The [research proposal](docs/RESEARCH.md) defines the requirements, and the [phased plan](PLAN.md) defines scope and acceptance criteria. Those documents describe the intended design; the delivered scope is summarized below.

### Current status

As of **2026-10-09**:

**Overall position: Windows P6 acceptance is complete; P7 is partial.** Ten Office development rounds each scored **0/3** on independent artifacts. Latest blockers: Word verification after input, Excel pre-input foreground/window refusal and PowerPoint decision confidence. A separate scripted Excel probe passed field replacement and saved-artifact checks; full Agent tasks and the latest field transport remain unvalidated. Host regression: **435/435**; historical Windows: **373/373**. See the [live report](docs/evidence/2026-10-08-office-live/README.md).

Mac shared visual interfaces and opt-in Agent/CLI OCR fallback are implemented. Latest native read-only observations and real Jev choices pass 3/3; live input remains pending. See the [visual bridge](docs/P7-VISUAL-BRIDGE.md).

See [overall status](docs/STATUS.md) and the prioritized [pending list](docs/PENDING.md). Historical acceptance below retains its original dates and denominators.

- **P0: macOS environment and permissions verified.** xa11y builds, Python bindings, and the native Cocoa test app work. Fusion and a Windows 11 ARM VM are configured; Windows and its local account are ready.
- **P1: live reads verified.** AX trees from TextEdit, Finder, System Settings, and the fixed native app are readable. Safari serves as a local compatibility sample. The follow-up enumerated 35 applications; element queries, window filters, and ref lookup passed.
- **P2: three native action sequences passed.** Button status changes, text writes and typing, focus, and table row selection were verified. Combo box writes and radio selection passed; three additional native scroll round trips passed. At that stage, 114 isolated tests passed.
- **Known limits:** Finder ref sets remained stable in three consecutive snapshot pairs; reordering and virtualization still need coverage. Some TextEdit roles are `unknown`. Scrolling supports macOS numeric scroll bars and Windows ScrollPattern containers. Mac two-axis scrolling, three live model cross-app tasks and workflow comparison passed on 2026-10-06. Broader application and virtualization coverage remains pending; see the [Mac report](docs/MACOS-FOLLOWUP.md).
- **P3: Windows UIA validation passed.** Five app reads, three native WinForms action sequences, stale-ref handling, and benchmarks at 50/100/300/1,000 controls completed inside the VM. All 114 Windows isolated tests passed. See the [P3 report](docs/P3-REPORT.md).
- **Runtime follow-up passed:** Windows directional scrolling, empty-value readback, read-only capabilities, top-level window filtering, duplicate control reordering/rebuilding, and real Notepad input. See the [follow-up report](docs/RUNTIME-FOLLOWUP.md) for 50 native records and five scripted decision/action checks.
- **P4 evaluation underway:** OpenRouter Jev is configured. Five saved native cases matched, and five live Windows tasks passed, including a two-step dropdown selection. Four native hard cases also passed. Bounded context improved repeated scale development runs to 12/12; three additional live clicks in a 1,000-control tree passed. See the [P4 report](docs/P4-REPORT.md). The P5 loop passed a seven-action cross-app task, repeated recovery, pause/resume and app restart checks; see the [P5 follow-up](docs/P5-FOLLOWUP.md). P6 recording and replay are now implemented; visual fallback remains P7 work.

- **P5 stage recovery and file prerequisites:** Completed intermediate steps now retain full execution receipts. A real Planner/Jev test resumed after stage two with only the remaining write. Three deterministic native Notepad save/reopen runs passed. Seven Office apps have since been installed and passed native startup reads; activation and mail setup remain pending. See the [installation report](docs/WINDOWS-OFFICE-SETUP.md) and [prerequisite report](docs/P5-OFFICE-PREREQUISITES.md).
- **P5 partial-exposure checks:** Two real Planner/Jev flows passed in a native paginated app exposing only 25 UIA rows at a time, including navigation to Row 997 followed by Notepad input. Old row refs return `stale_ref`; native and model call timings are recorded. See the [pagination report](docs/P5-PAGED.md).

**Historical Windows P6 acceptance (2026-10-05):** Final code passed **3/3** unchanged recording replays and **3/3** real-trace save/reopen replays. One seven-step cross-app template passed **3/3** parameter cases. Restart/resume dispatched only the remaining action; native structure recovery and real model repair passed. Host and Windows each pass **292 isolated tests**. See the [P6 acceptance report](docs/P6-CLOSURE.md).

**Mac native follow-up (2026-10-06):** Controls and live model cross-app tasks each pass 3/3. Recorded and compiled workflows each replay 3/3. Two-axis scrolling, actual control reorder and pause/resume pass. The Mac table-row capability fix passes 293 host tests. See the [Mac report](docs/MACOS-FOLLOWUP.md).

**Mac Office interactive pilot (2026-10-07):** Excel calculations, Word/PPT summaries, an Outlook draft with attachments, revisions and document reopening completed. Six saved files pass independent checks; the total changes from 320 to 370 and all three v1 hashes remain unchanged. CUA operated the UI; Bokkio performed read-only diagnostics. Editor metadata, Excel cell observation and Outlook traversal still need integration before Bokkio Agent/Workflow Office acceptance. See the [Office report](docs/MACOS-OFFICE-REPORT.md).

**P7.1 implementation started (2026-10-08):** Scoped Windows client-area capture, identity/DPI/physical-coordinate metadata, a custom-drawn fixture and acceptance runner are implemented. Host and Windows each pass 314 isolated tests. The guest capture preflight returns `desktop_unavailable`; three native pixel runs await an interactive Windows desktop. See the [P7.1 report](docs/P7-CAPTURE.md).

**Mac path recheck (same day):** Scoped ScreenCaptureKit diagnostics pass 3/3 on owned windows while current AX preflight fails. Mac capture/vision development can continue; Runtime integration and input acceptance remain pending. See the [recheck report](docs/MACOS-CAPTURE-PROBE.md).

**Mac P7 Runtime (same day):** Package/CLI capture and local Vision OCR candidate selection pass 3/3 native runs and 8/8 rejection cases. Host and Windows each pass 355 tests. Bounded input is implemented but real preflight rejects with zero dispatch; positive input and automatic Agent fallback remain pending. See the [report](docs/P7-MACOS-VISUAL.md).

**Microsoft Office original-task pilot (2026-10-08–09):** Three pinned L1 tasks have isolated initialization, native execution, independent grading and an original VLM entry. Following the early session block, ten actual rounds each scored 0/3. AXConfirm, text selection, window identity and phase planning were repaired; remaining failures and scripted capability evidence are preserved separately. See the [execution report](docs/OFFICE-PILOT-READINESS.md).

The current implementation uses **Python + xa11y 0.15.x**, with comtypes for native Windows ValuePattern and ScrollPattern support. Verified Win32 edit messages commit text in classic dialogs. Rust is the preferred direction for the future core runtime. The element model draws on CUP (Computer Use Protocol); full CUP protocol adaptation is not implemented. Jev uses `typesafe/jev-1.13` through OpenRouter Decisions, with a direct TypeSafe option. These small development samples do not establish general desktop success rates.

### Intended architecture

```text
User goal / natural language
        ↓
LLM / Planner                 Decompose tasks and define success conditions
        ↓
Jev                           Choose a current element and next action
        ↓
Unified Element Runtime       Model, locate, and operate on elements
        ↓
Windows UIA / macOS AX         Access native applications

Execution trace → Recorder → Workflow → Deterministic replay
Insufficient accessibility data → OCR / Vision / coordinate action fallback
```

Native reads/actions, real Jev decisions, P5 planning and P6 recording/parameterized resumable replay are available. P7 adds verified Mac capture/OCR; the complete visual execution loop is pending. Historical Mac native fixture results remain separate from current AX preflight failures.

### Installation and permissions

Requirements: macOS or Windows, Python 3.9+, and `uv`. For a fresh checkout:

```bash
git clone https://github.com/YeohsCode/Bokkio.git
cd Bokkio
uv sync --group test
uv run bokkio --help
```

Grant Accessibility permission to the CLI host application (such as your terminal) or resolved Python interpreter under **System Settings → Privacy & Security → Accessibility**, then rerun the CLI. Restart the host if permission still does not take effect. Earlier full AX reads passed, but a current native AX read failure remains unresolved; Windows is the primary acceptance platform.

Windows reads native desktop controls through UIA. The tested environment is a Windows 11 ARM64 VM with x64 Python 3.12; start with disposable test files and app windows.

When permission is missing, the CLI exits with a nonzero status and explains where to grant access. If only partial content such as a menu bar is visible, check permissions and the target application's accessibility support.

### Usage

Open the target application first, then run:

```bash
uv run bokkio apps
uv run bokkio windows --app TextEdit --json
uv run bokkio snapshot --app TextEdit
uv run bokkio snapshot --app TextEdit --json
uv run bokkio snapshot --app TextEdit --window 0 --json
uv run bokkio find --app TextEdit --role button --name Save
uv run bokkio get REF --app TextEdit
uv run bokkio act --app TextEdit --action click --ref REF
uv run bokkio act --app BokkioTest --action set_value --role text_field --name Search --value ""
uv run bokkio act --app BokkioTest --action type --role text_field --name Search --value "Hello" --expect-value "Hello"
uv run bokkio act --app BokkioTest --action scroll --role scroll_bar --direction down --amount 0.25
```

- `--app` accepts a PID or application name. Use the name returned by `apps`.
- `--window` first matches an exact window ref, native stable ID or title, then a zero-based index or title substring.
- `snapshot` prints an indented tree by default; `--json` returns full data. Without a window filter, traversal starts at the application root and includes application-level nodes and menus.
- `find` uses case-insensitive exact matching for role and optional name. Names must match the application's language and actual AX data; `Save` is illustrative.
- `find` and `get` return JSON by default. Replace `REF` with a full ref from an application-level JSON snapshot or `find`; the tree view shows only the first 8 characters.
- `get` reads the current application tree again. An element in a window snapshot shares its ref with the application snapshot.
- `act` provides `click`, `invoke`, `type`, `set_value`, `select`, `focus`, `scroll`, `expand`, and `collapse`. Target an element with `--ref` or `--role` plus optional `--name` and `--parent`. `type` and `set_value` require `--value`. The response includes before/after elements and verification status. Run actions only against a test application you have authorized.

`set_value`, `focus`, `select`, `expand`, `collapse`, and `scroll` check values or state after execution. `type --expect-value` checks the resulting text. Click and type without an expected value return `observed` and require task-specific success checks. Scrolling requires `--direction up/down/left/right`; `--amount` is a fraction of the entire scroll range, default `0.25`. Target a scroll bar or an element inside its container. Windows uses container ScrollPattern; both position and content changes are needed for confirmation. Unsupported targets return an error; reaching a boundary returns `unconfirmed`. See the [P2 report](docs/P2-REPORT.md) for evidence.

### Element data and references

Every element contains:

| Field | Meaning |
|---|---|
| `ref` | A 20-character hash derived from application identity and structural path |
| `platform`, `actions` | Platform name and normalized native action capabilities |
| `role`, `name`, `value` | Element role, name, and value |
| `state` | States such as enabled, focused, and selected |
| `bounds` | `x / y / width / height`, or `null` when unavailable |
| `parent`, `children` | Parent ref and nested child elements |
| `platform_data` | Raw AX data plus description, actions, and native stable ID |

Missing values are explicit `null` or empty structures. The JSON snapshot wrapper contains `app`, `window_filter`, and `windows`. Without a window filter, `windows` holds the application-root tree.

Refs describe the current structure. Consecutive snapshots retained identical ref sets in TextEdit, System Settings, and the fixed app. Dynamic Finder text names changed while ref sets remained stable in three snapshot pairs. `structural-v3` ignores name changes for a single non-clickable static_text child. Unique Windows HWNDs enter identity paths, preserving duplicate refs through reorder and invalidating refs when controls are rebuilt. Interactive controls retain name-based identities. Refresh snapshots created by older versions. App restarts, interactive element renaming, structural changes, and sibling reordering can invalidate refs. Window lists and window/application snapshots share refs. `get` asks for a fresh snapshot when resolution fails; `act` returns a structured stale-ref error.

### Pending work and roadmap

| Phase | Scope | Status |
|---|---|---|
| P0 | Dependencies, permissions, and reference implementations | macOS verified; Windows VM configured, OS and local account ready |
| P1 | Read-only macOS AX CLI | Live matrix verified; dynamic ref limits documented |
| P2 | Unified elements, selectors, and macOS actions | Core actions and three scroll runs passed; broader stability coverage pending |
| P3 | Windows UIA reads and actions | Five app reads, three action runs, and four scale benchmarks passed |
| P4 | Jev local decisions and evaluation | Five live tasks and hard cases passed; scale samples 12/12, three additional live large-tree clicks passed |
| P5 | LLM planning and execution loop | First version implemented; Windows seven-action, recovery and partial-exposure checks passed; three Mac model comparison tasks pass; broader applications pending |
| P6 | Recording and deterministic workflow replay | Windows acceptance complete; parameters, file versions, resume and model repair passed |
| P7 | Vision / CUA fallback and reliability | Mac capture/OCR verified; Windows live pixels, positive input, automatic fallback and reliability pending |

The fixed native WAA trio passed two consecutive rounds at **3/3**, including persistence, fresh-process reopening and unchanged input hashes. Recovery verifies writable patterns and RuntimeIds, commits classic-dialog edits, derives native word counts, plans after newly observed data and checks missing deliverables. See the [diagnosis and results](docs/P5-WAA-RECOVERY.md).

**Earlier native variation checks:** Each of six new fixtures has a passing attempt across rounds: full v5 was 5/6, targeted v6 was 3/3, and final PNG v8 was 1/1. Final requirement changes passed 2/2, delivering 7 then 5 while preserving prior files and history. Host and Windows each passed 195 isolated tests at that stage. Full source-path constraints, versioned requirements and artifact hashes accompany native menu and same-named Open-button fixes. See the [complete round-by-round report](docs/P5-NATIVE-VARIATIONS.md).

**Fixed five-task pilot:** Final consecutive full rounds v26 and v27 each scored 4/5, with all five agents completed and intermediate/native artifact checks passed. Navigation reached the correct folder; the unchanged title metric remains zero because of an environment suffix. Native rectangle acquisition, Settings readiness and same-named control verification were repaired. Three separate Settings confirmations each passed 1/1. All failures and denominators remain in the [pilot report](docs/P5-WAA-PILOT.md).

### Current phase and further work

**P6 is complete; P7 is partially implemented and under validation.** Mac capture/OCR passes; positive input, automatic fallback and Windows live visual acceptance remain pending. The earlier Office pilot was blocked; same-day recovery makes a new workspace ready to attempt.

1. Restore input availability and run the fixed three-task Office pilot in a fresh workspace, independently verifying saved artifacts and retaining every failure.
2. Repair Office native coverage, connect Planner/Jev/Workflow visual fallback, and validate click/type.
3. Expand Windows vision, Mac file/process recovery, multi-display/DPI and reliability, then align full upstream benchmark environments.

See [overall status](docs/STATUS.md), the [P7 plan](docs/P7-PLAN.md) and the [pending list](docs/PENDING.md).

### Computer Use benchmarks

WindowsAgentArena preparation includes a pinned revision, 154 task files and a proposed five-task native pilot. Three additional Explorer/Notepad tasks have now run through the real Planner → Jev → UIA loop in the ARM64 VM, with independent checks using pinned evaluator functions. The [report](docs/P5-WAA-LONGCHAIN.md) preserves every attempt. These development runs adapt the environment and paths and do not provide official leaderboard scores. The original five-task pilot has run; its [report](docs/P5-WAA-PILOT.md) records steps, intermediate checks, scoring and failures. WindowsWorld and OSWorld 2 inform the design. See the [integration plan](docs/BENCHMARK-PLAN.md).

### Jev decision entry point

Set `OPENROUTER_API_KEY`, or use a private `jev.json` outside the repository. The development test environment is configured; supply your own API key in a fresh checkout.

- macOS: `~/Library/Application Support/Bokkio/jev.json` (mode 0600).
- Windows: `%LOCALAPPDATA%\Bokkio\jev.json`.
- JSON fields: `source: "openrouter"`, `model: "typesafe/jev-1.13"`, and `api_key`.
- `BOKKIO_JEV_CONFIG` overrides the file path. Environment keys take precedence. `BOKKIO_JEV_SOURCE` / `BOKKIO_JEV_MODEL` override provider and model. Direct TypeSafe access uses `TYPESAFE_API_KEY`.

```bash
uv run bokkio decide --app BokkioTest --goal 'Set Search to "hello"' --allow-value hello
# Add --execute to perform one accepted decision
uv run python scripts/evaluate_jev.py --cases docs/evidence/2026-10-02-runtime-followup/jev-cases.json --output /tmp/bokkio-jev-evaluation.json
```

`decide` returns a decision by default. It sends the native tree for the selected app or `--window` to the configured Jev provider. Text comes from `--allow-value`. Operation and target use closed Choice options; more than 255 targets use groups. Noul measures observed goal satisfaction. Execution rereads the same scope and rejects changed state, unsupported actions, stale refs, low confidence, and indistinguishable duplicates. Choice confidence is not accuracy; `done` still needs an independent task success condition.

### P5 planning and execution entry point

Private `planner.json` lives beside the Jev config and contains `api_key` and `model`. This Mac and Windows VM use the verified GPT-4.1 planner; Jev remains unchanged. Overrides: `BOKKIO_PLANNER_CONFIG`, `BOKKIO_PLANNER_MODEL` and `OPENROUTER_API_KEY`.

Set `BOKKIO_PLANNER_REASONING_EFFORT` or private `reasoning_effort` to a level supported by the selected model. The WAA runner uses `low`; otherwise the provider default is retained.

```bash
uv run bokkio run --goal 'Set Search to hello and submit it' --allow-app BokkioWorkflowA --trace /tmp/bokkio-task.json --plan-only
# Remove --plan-only to execute; repeat --allow-app for cross-app tasks
```

Every subtask has observable native success conditions. `--max-actions` and `--max-replans` bound execution and recovery. `--max-phases` bounds continuation after new source data or dialogs (default 4). Repeat `--require-file` for deliverables that must exist; retain the same requirements when resuming. A `--control-file` supplies pause/cancel signals; `--resume` continues with the same goal and app allowlist. The CLI prints a status summary and writes complete model/action/observation traces to the checkpoint. Sending, payment and deletion steps are blocked. See the [P5 report](docs/P5-REPORT.md) for implementation and tested limits.


Repeat `--require-source` to require native acquisition of full source paths before editor writes or completion. The current adapter checks the native filename field in an English classic Windows Open dialog and retains source facts for the current goal revision. A new revision must acquire its source again.

To change requirements, combine `--resume`, a new `--goal` and `--amend-reason` at a paused or completed checkpoint. Keep the app allowlist; cumulative budgets still apply. Old receipts remain in history and the new revision starts with fresh observations and planning. Verified `--require-file` deliveries record paths, byte counts and SHA-256 in `artifact_versions`. These identify persisted bytes; task-specific checks still determine content correctness.

### P6 recording and replay

Start a disposable native app and bind its PID explicitly. Replay calls the native Runtime without model requests.

```powershell
bokkio workflow record --actions fixtures/workflows/interactions.actions.json --bind fixture=1234 --name "Native interactions" --output workflow.json
bokkio workflow replay --workflow workflow.json --bind fixture=5678 --output replay.json
```

`workflow compile` converts a completed trace. `workflow parameterize` adds reviewed text/path/hash parameters and file-version contracts. `workflow replay --parameters values.json --resume paused.json` resumes with rebound applications; `--window-bind alias=hwnd:0x...` scopes the native window.

`workflow repair --model-repair` asks the model to choose a native selector and creates a parent-linked version. Replay itself calls no model. Native client receipts can enter `Recorder.capture_receipt` without dispatching the captured action again. See the [P6 guide](docs/P6-WORKFLOW.md) for initial states, contracts, conditions and complete commands.

### Development and documentation

```bash
uv run --group test pytest -q
```

The 220 isolated tests cover fields, tree structure, refs, queries, window filters, actions, scrolling, dynamic labels, and errors. Live desktop verification uses `scripts/verify_native.py`. Launch the fixed native app as `BokkioTest` and the matrix apps, create a blank TextEdit window, then run:

```bash
uv run python scripts/verify_native.py --output /tmp/bokkio-evidence
```

The script operates on the fixed test app and saves read summaries and action results. See the [verification guide](docs/evidence/2026-10-01-followup/README.md) for evidence and fixture build steps.

- `src/bokkio/`: CLI, element model, and xa11y adapter.
- `tests/`: isolated unit tests.
- [Research proposal](docs/RESEARCH.md): motivation, candidate technologies, and intended architecture (Chinese).
- [Phased plan](PLAN.md): P0–P7 scope and acceptance criteria (Chinese).
- [P0/P1 task brief](TASK-P0P1.md): current delivery scope (Chinese).
- [P0 verification](docs/P0-VERIFICATION.md), [design notes](docs/NOTES.md), [P1 report](docs/P1-REPORT.md), and [P2 report](docs/P2-REPORT.md): evidence, implementation details, and unmet criteria (English).

Publication files and decompressed evidence were checked for credentials and personal data; see the [privacy review](docs/SECURITY-REVIEW.md).
