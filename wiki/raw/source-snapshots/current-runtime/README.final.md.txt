---
source_path: README.md
source_version: working-tree-current-runtime-final
ingested: 2026-10-13
sha256: c49e4e1c873cc3238c1ed93210671640b56f2e9258d1732709333da9964f61cc
text_revised: 2026-10-18
revision_reason: user-requested plain-language terminology
original_body_sha256: 45ef1f12adc5709df42c70f6dcd1c9e62d73bd8a5e4f8239f682360f9c3ed6e1
---

# Bokkio

面向 Windows 与 macOS 的通用 Computer Use Runtime，供不同 Harness、Agent IDE 与 Agent 调用，支持原生/视觉动作、生成代码、审批与操作审计。

A model-independent computer use runtime for Windows and macOS: native/pixel actions, generated code, human approvals and operation audit through MCP, CLI and Python SDK.

**工作候选版本 / Working candidate:** `0.2.0` — 通用执行 Core，MCP、CLI、Python SDK、生成代码、Browser、审批、可查询统计的操作日志。

**2026-10-13 状态：** 回归 **587/587**，macOS 审计 **9/9**、窗口/作业矩阵 **18/18**；完整自主业务主批 **26/36**（当前 Codex 12/12、Hermes 8/12、DeepSeek 6/12），关键家族三份样本 **17/27**，GUI **0/18**，三调用方延迟自动管理员审批恢复 **9/9**。本轮自动测试已执行，产品成功率目标、客户人工审批、物理环境与 Windows 当前 Runtime 验收尚未完成。当前 Codex 保留会话且编写评测器，其 bridge 成绩不称盲测或公平排名。

**跨环境 Agent 共享入口 / Shared handoff:** [计划、进度、完成度与待办](docs/progress/README.md) · [结构化状态](docs/progress/state.json) · [接续步骤](docs/progress/HANDOFF.md)。这些文档和脱敏验收报告由 Git 跟踪；每端完成工作后更新并推送。

使用方法见 [Runtime 指南](docs/RUNTIME-GUIDE.md)，详细实测范围见 [交付报告](docs/RUNTIME-DELIVERY.md)。历史 `0.1.0` Planner/Jev/Workflow 内容保留在下文。

**测试加强：** [计划](docs/TEST-STRENGTHENING-PLAN.md) · [EVAL 工作包](docs/progress/test-strengthening.json) · [完整主批与审批报告](docs/evidence/2026-10-12-macos-completion/README.md)。36 次 any-tool 主批及 18 次稳定性追加均实际执行，GUI 与业务分轨；每调用方至少 10/12 和关键家族三份全过的目标尚未满足。历史原始分数保留：SDK 终态核验将旧重点矩阵从 9/12 更正为 7/12，不能用退出码 0 单独判定 SDK 完成。

[中文](#中文) · [English](#english)

**项目知识库 / Project knowledge base:** [当前架构 / Architecture](wiki/summaries/architecture-map.md) · [模块调用 / Module calls](wiki/summaries/module-call-map.md) · [LLM Wiki](wiki/index.md) · [维护规则 / Maintenance schema](wiki/SCHEMA.md) · [维护日志 / Change log](wiki/log.md)

## 中文

### 项目定位与当前进展

Bokkio 为企业提供通用 Computer Use 执行工具。调用方的 Harness、Agent IDE 或 Agent 负责理解任务、选择通道和判断业务结果；Bokkio 负责获准资源上的观察、原生/视觉动作、生成代码/脚本、Browser、审批与操作证据。Core 不依赖固定模型或业务流程，DeepSeek Harness 是可选调用方。

macOS 开发覆盖计划中的四类能力：原生、视觉、生成代码组合、Browser。客户应用类待确定，物理环境矩阵和客户部署/人工审批待验收。Windows 新 Runtime 已提供实现及安装脚本，当前实机验收尚未完成；先前保存的 VM 凭据已找回并成功登录。

最新定位和三天交付门槛见 [实施计划](docs/PLAN-REPOSITIONING.md)，完成度及剩余工作统一维护在 [共享进度](docs/progress/STATUS.md)。统计分母是开发能力覆盖，不表示通用软件成功率或双平台生产验收完成。

### 当前系统架构（0.2.0）

当前实现是 Python 包，三种入口共用 `Runtime.call()`：MCP stdio、CLI JSON 和 Python SDK。调用方负责模型、任务规划、通道选择及业务验收；Core 负责会话授权、审批、执行、作业和可追溯证据。以下图描述当前代码，Rust 与完整 CUP 适配仍是后续方向。

```mermaid
flowchart TB
    Caller["Harness / Agent IDE / Agent"]
    Caller --> MCP["MCP stdio · mcp_server.py"]
    Caller --> CLI["CLI JSON · runtime_cli.py"]
    Caller --> SDK["Python SDK · sdk.Client"]
    MCP --> Core["Runtime.call · runtime.py"]
    CLI --> Core
    SDK --> Core
    Schema["tool_schema.py · 工具参数定义"] --> Core
    Policy["管理员策略 · Session / 资源授权 / 审批"] --> Core
    Core <--> Store["audit.AuditStore · SQLite / Artifact 文件"]
    Admin["本地管理员 CLI · approve"] --> Store
    Core --> Native["原生通道 · Xa11yBackend"]
    Core --> Pixel["截图 / 像素输入 · desktop_input.py"]
    Core --> Jobs["代码 / 进程 · executor.py worker"]
    Core --> Browser["Browser · browser_driver.py worker"]
    Native --> AX["macOS AX / Windows UIA"]
    Pixel --> Capture["Swift ScreenCaptureKit / Windows capture + SendInput"]
    Jobs --> Script["Python / Shell / PowerShell / argv"]
    Browser --> Chromium["Playwright · 持久 Chromium 页面"]
    Jobs --> Store
    Browser --> Store
    AX --> Desktop["获准桌面应用"]
    Capture --> Desktop
```

| 层 / 模块 | 责任与调用关系 |
|---|---|
| 接入层 | `mcp_server.serve`、`runtime_cli.main`、`sdk.Client.call` → `Runtime.call`；`tool_schema` 提供统一工具接口定义 |
| Core | `Runtime.call` → 参数/Session/授权/审批检查 → `_execute` → `_finish`；默认拒绝资源访问 |
| 原生 | `_native_call` → `Xa11yBackend` → xa11y 与 `MacAX` / `WindowsUIA`；`model`、`selector`、`scroll` 支撑身份、查询和验证 |
| 截图与像素 | `desktop_input` → `macos_capture` / `windows_capture`、Swift helper / Windows SendInput；坐标来自新鲜截图，无需 OCR 标签 |
| 代码与进程 | `executor.launch` → 独立 worker → Python/Shell/PowerShell/argv；生成 Python 可通过 `Client.from_environment()` 继承会话并回调 Core |
| Browser | `browser_driver.call` → 每会话持久 worker → Playwright Chromium；精确 origin 和 `expected_url` 约束操作 |
| 审批与证据 | `AuditStore` 保存 SQLite 会话、操作、审批、事件及 artifact 元数据；管理员 CLI 决定审批；Agent 查询状态、日志、统计与产物 |
| 可选旧扩展 | `cli` → `DesktopAgent` → Planner/Jev，或 Recorder/WorkflowReplay → backend；仍直接使用 backend，不自动获得新 Core 的授权检查与审计记录 |

原生调用在单一专用线程执行；原生动作、激活、像素和 Browser 派发共用跨进程桌面锁，锁等待后再次核验范围。代码/进程在独立 worker 运行，以 `job.get`/`job.cancel` 管理。SQLite 和私有文件保存跨进程状态；当前是单机架构，trusted-host 代码与 GUI 不提供逐文件 OS 沙箱。

#### 模块调用图

```mermaid
flowchart LR
    Entry["MCP / CLI / SDK"] --> Call["Runtime.call"]
    Call --> Check["schema / session / grants / approval"]
    Check --> Dispatch["Runtime._execute"]
    Dispatch --> NT["单一原生线程 · _native_call"]
    NT --> XA["Xa11yBackend.snapshot / perform"]
    XA --> Win["WindowsUIA"]
    XA --> Mac["MacAX"]
    Dispatch --> Input["desktop_input.capture / activate / perform"]
    Input --> WC["windows_capture.py"]
    Input --> MC["macos_capture.py + Swift helper"]
    Input --> MA["macos_activation.py + Swift helper"]
    Dispatch --> EX["executor.launch / get / cancel"]
    EX --> EW["executor.worker · 子进程"]
    EW -.-> Client["sdk.Client.from_environment"]
    Client --> Call
    Dispatch --> BC["browser_driver.call"]
    BC --> BW["browser_driver.worker · 本地 HTTP / token"]
    BW --> PW["Playwright"]
    Call <--> Audit["AuditStore · events / operations / approvals"]
    EW --> Audit
    BW --> Audit
```

#### 一次观察与动作的调用时序

```mermaid
sequenceDiagram
    participant C as 调用方 MCP/CLI/SDK
    participant R as Runtime.call
    participant A as AuditStore/SQLite
    participant H as 本地管理员 CLI
    participant B as 执行后端
    C->>R: session.open
    R->>A: 保存 OS 用户、进程身份、资源授权与 TTL
    R-->>C: session_id
    C->>R: desktop.observe / desktop.capture
    R->>B: 读取获准 app/window
    R->>A: 保存 observation 与 artifact
    R-->>C: observation_id、ref 或图片
    C->>R: 写请求 + observation_id + operation_id
    R->>A: 认领 operation_id，记录 request.received
    R->>R: 校验 schema、session、资源与观察
    opt require_approval = true
        R->>A: approval.requested
        R-->>C: approval_required，零派发
        H->>A: 查看精确请求并 approved/denied
        C->>R: 原 ID、原工具、原参数恢复请求
        R->>R: 重新校验授权与观察时效
        R->>A: 消耗有效批准
    end
    R->>A: 持久化 execution.intent
    R->>B: 派发；桌面输入取得锁后再次校验
    B-->>R: 动作回执或 job_id
    R->>A: 保存结果与 execution.finished
    R-->>C: verified / executed / queued / completion_unknown
    C->>R: 新观察、job.get、evidence.check、audit.query
    R-->>C: 当前状态及证据
    Note over C,B: 调用方独立判断业务结果；unknown 不盲目重发
```

`observation_id` 有效期 15 秒；审批申请有效期 300 秒，审批不延长观察有效期。过期观察需重新读取并创建新操作。`operation_id` 绑定工具、参数和会话；同一请求重复调用返回记录，未知完成需先查证。`verified` 表示动作后置检查确认，`executed` 表示已执行，`queued` 需继续查作业；这些状态均不能单独证明业务完成。代码审批也不自动批准其 SDK 子动作。

详细设计与代码引用见 [Wiki 架构](wiki/summaries/architecture-map.md)、[完整模块调用地图](wiki/summaries/module-call-map.md) 和 [操作生命周期](wiki/concepts/runtime-contracts.md)。最新验收分母及缺口见 [共享状态](docs/progress/STATUS.md)。

### 历史 P0–P7 记录

以下保留原阶段的成绩、限制与证据。旧 Office 三题和 Planner/Jev 循环不作为新 Core 的必经路径。

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

### Runtime 安装与调用

macOS 执行 `sh scripts/install_runtime.sh`；Windows 执行 `powershell -File scripts/install_runtime.ps1`。MCP 需要 Python 3.10+，两端还需实际宿主授权和可用交互桌面。

```sh
uv run bokkio-runtime --help
uv run bokkio-runtime --policy examples/runtime-policy.json call capabilities
```

策略模板默认拒绝资源访问；根据获准应用、路径和 origin 配置后再打开 session。CLI、SDK、MCP 接入及独立审批命令见 [指南](docs/RUNTIME-GUIDE.md)，验证和跨平台交接见 [接续说明](docs/progress/HANDOFF.md)。代码执行为 trusted-host，需明确授权。

以下安装及调用示例属于保留的旧 `bokkio` CLI；旧入口不纳入新 Runtime 的企业授权边界。

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

### 历史阶段路线图

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

### 后续工作

当前按 [共享待办](docs/progress/STATUS.md) 执行：macOS 物理环境矩阵、客户应用任务、客户部署/人工审批，以及 Windows 独立实机验收；三种开发调用方的路径与限制见 [Harness 实测](docs/evidence/2026-10-12-harness/README.md)。原 Office/Workflow 任务保留为历史诊断与可选回归，不持续向 Core 添加应用业务规则。

### Computer Use 测试集

已固定 WindowsAgentArena 源码版本、154 份任务配置及五项原生 pilot。另选三项 Explorer/Notepad 多步任务，已在 ARM64 虚机实际运行 Planner → Jev → UIA，并复用指定版本的 evaluator 函数独立校验；所有尝试见 [实测报告](docs/P5-WAA-LONGCHAIN.md)。这些是明确改动环境与路径的开发试跑，不能作为官方榜单得分。原先五项 pilot 已执行，逐次派发、中间检查、独立评分和失败记录见 [pilot 报告](docs/P5-WAA-PILOT.md)。WindowsWorld 的微软 Office 三题已在 macOS 适配环境实际执行，r28/r30 各 3/3、最新完整轮 r33 为 0/3，未取得稳定或官方成绩，见 [最新 Office 记录](docs/evidence/2026-10-10-office-progress/README.md)；OSWorld 2 仍为长流程设计参考。以上为旧 Agent 的历史成绩，不替代当前 Runtime 自主业务评测。接入边界见 [测试集接入计划](docs/BENCHMARK-PLAN.md)。

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

### Positioning and current status

Bokkio is an enterprise computer use execution tool. External harnesses, Agent IDEs and agents plan tasks and choose channels; the shared Core observes and acts on approved resources, runs generated code/scripts, controls an isolated browser, and records approvals and operation evidence. No model or application-specific planning loop is required.

As of 2026-10-12, host regression passes **550/550**. Real process faults pass 5/5, the local desktop/job matrix scores 18/18, and the unadapted Numbers/MCP development sample passes 3/3. The native/SQLite audit contract passes 9/9; physical lock/display and customer acceptance remain pending. macOS has development evidence for native actions, pixel/Unicode input, generated-code combinations and browser operations. Three user-selected developer caller paths pass independent acceptance: current Codex through an official MCP client bridge, and installed Hermes/DeepSeek through MCP code.run plus delegated native SDK calls (GLM 5.3 Flash). Native Codex CLI attachment and DeepSeek per-model-turn native calls have separate unresolved results; see [harness evidence](docs/evidence/2026-10-12-harness/README.md). Customer application tasks, physical environment checks and deployment/manual approval remain pending. Current-runtime Windows live acceptance is pending; the saved VM credentials were recovered and login succeeded.

Use the [shared progress folder](docs/progress/README.md) for the plan, completion counts, pending work and cross-environment handoff. These documents and sanitized evidence are tracked in Git. The candidate is not yet a fully accepted dual-platform release.

### Current architecture (0.2.0)

The Python implementation shares `Runtime.call()` across MCP stdio, CLI JSON and the Python SDK. The caller owns model selection, planning, channel selection and business verification. Core owns sessions, resource checks, approvals, execution, jobs and evidence. The [Chinese architecture section](#当前系统架构020) includes the system diagram, module call graph and request sequence; [Wiki architecture](wiki/summaries/architecture-map.md) and the [complete module map](wiki/summaries/module-call-map.md) link these relationships to code.

| Module | Calls and responsibility |
|---|---|
| `mcp_server`, `runtime_cli`, `sdk` | Forward requests to `Runtime.call`; `tool_schema` defines the common input contract |
| `runtime` | Validate schema/session/grants/approval, dispatch through `_execute`, persist the result through `_finish` |
| `xa11y_backend` | Native snapshots/actions via xa11y and `MacAX`/`WindowsUIA`; model/selector/scroll support identity and verification |
| `desktop_input` | Window capture/activation/pixel input via platform capture and native helpers; no OCR label required |
| `executor` | Durable code/process workers, output limits, timeout and cancellation; generated Python can call the delegated SDK |
| `browser_driver` | Persistent per-session Playwright worker with granted origins and exact `expected_url` checks |
| `audit` | SQLite sessions/operations/approvals/events and artifact metadata; local admin CLI grants approval |
| Legacy Agent/Workflow | Optional direct-backend clients; existing paths do not pass through the new Runtime authorization/audit boundary |

Native calls use one dedicated thread. Native actions, activation, pixel input and Browser calls share a cross-process desktop lock and revalidate after waiting. Code/process jobs run in independent workers. This is a local architecture; trusted-host scripts and GUI operations do not provide a per-file OS sandbox.

Observations expire after 15 seconds; approvals expire after 300 seconds and do not extend observations. Repeated operation IDs return recorded results for the same request. Unknown completion requires independent inspection before any new dispatch. A code approval does not grant approval to SDK child actions. `verified`, `executed` and `queued` describe execution evidence; the caller still checks business results. See [lifecycle contracts](wiki/concepts/runtime-contracts.md) and [current acceptance status](docs/progress/STATUS.md).

### Historical P0–P7 results

The following records retain their original dates and denominators. Office task scores and Planner/Jev are historical diagnostics and optional client capabilities.

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

### Runtime setup

Run `sh scripts/install_runtime.sh` on macOS or `powershell -File scripts/install_runtime.ps1` on Windows. MCP requires Python 3.10+. Configure explicitly approved resources in the default-deny policy template. See the [guide](docs/RUNTIME-GUIDE.md) and [handoff](docs/progress/HANDOFF.md) for startup, validation and the trusted-host code boundary.

The following legacy `bokkio` CLI examples remain available and are outside the new Runtime enterprise authorization boundary.

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

### Historical roadmap

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

### Further work

Follow the [shared status and pending work](docs/progress/STATUS.md): macOS physical fault checks, customer tasks, customer Harness integration, and Windows live acceptance. Keep historical Office/Workflow diagnostics separate from current Runtime acceptance.

### Computer Use benchmarks

WindowsAgentArena preparation includes a pinned revision, 154 task files and a proposed five-task native pilot. Three additional Explorer/Notepad tasks have now run through the real Planner → Jev → UIA loop in the ARM64 VM, with independent checks using pinned evaluator functions. The [report](docs/P5-WAA-LONGCHAIN.md) preserves every attempt. These development runs adapt the environment and paths and do not provide official leaderboard scores. The original five-task pilot has run; its [report](docs/P5-WAA-PILOT.md) records steps, intermediate checks, scoring and failures. WindowsWorld Office tasks have also run in the adapted macOS environment: r28/r30 each passed 3/3, while the latest complete r33 scored 0/3; see [latest Office evidence](docs/evidence/2026-10-10-office-progress/README.md). These legacy-agent results do not validate the current Runtime with autonomous tasks. OSWorld 2 remains a design reference. See the [integration plan](docs/BENCHMARK-PLAN.md) and [new evaluation plan](docs/TEST-STRENGTHENING-PLAN.md).

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
