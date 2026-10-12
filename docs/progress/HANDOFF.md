# 跨环境接续说明

## 开始工作

1. git pull，阅读 [共享状态](STATUS.md)、[结构化待办](state.json) 和 [计划](../PLAN-REPOSITIONING.md)。确认当前分支及本地变更，避免覆盖另一端工作。
2. 使用项目 uv.lock 安装，Runtime 主线不需要模型 API Key。策略模板 examples/runtime-policy.json 默认为拒绝，按本机实际测试资源配置。
3. 选取一个待办 ID，在状态中注明平台和进行中；完成后补充结果、失败、修订和证据路径。避免两端同时修改相同代码文件；推送前拉取并处理冲突。

新业务评测按 [测试加强计划](../TEST-STRENGTHENING-PLAN.md) 和 test-strengthening.json 的 EVAL-01～08 接续。先冻结题目/输入/评分/预算，再准备薄 runner；不要沿用 verify_harness_clients.py 的精确代码提示作为自主任务。GUI/any-tool、首次/修复后、macOS/Windows 分轨计数；首轮及修复复测已开始，详见[执行报告](../evidence/2026-10-12-business-eval/README.md)。不要将旧轮补分或重评分计成新调用方尝试。

## macOS

```sh
sh scripts/install_runtime.sh
uv sync --frozen --extra mcp --extra browser --group test
uv run pytest -q
uv run python scripts/verify_runtime.py --output /tmp/bokkio-runtime-acceptance-NEW
```

最后一条只验证代码/Browser/MCP/CLI/审批/审计。原生验证可先编译 fixtures/cocoa-runtime/main.swift（无需 vendor），启动生成的 App，再增加 --native-app BokkioRuntimeContract --field Search；不能将省略原生项的结果称为桌面验收。辅助功能、屏幕录制和真实交互桌面按指南确认。

原生 fixture 编译命令：

```sh
uv run python scripts/build_native_fixture.py --source fixtures/cocoa-runtime/main.swift --output /tmp/BokkioRuntimeContract.app --name BokkioRuntimeContract
```

自绘视觉 fixture 源码位于 fixtures/cocoa-visual/main.swift，编译并包装成 App 后运行：

```sh
uv run python scripts/verify_runtime_visual.py --fixture /ABS/PATH/Test.app/Contents/MacOS/Test --output /tmp/bokkio-runtime-visual-NEW
```

原生/代码/Browser 验收使用 scripts/verify_runtime.py。审计合同使用 scripts/verify_runtime_audit.py --fixture NATIVE_EXECUTABLE --output NEWDIR。窗口/作业故障使用 scripts/verify_runtime_faults.py --fixture VISUAL_EXECUTABLE --output NEWDIR，显式记录屏幕锁、显示器及前台阻塞。MCP 字段闭环使用 scripts/verify_runtime_mcp_native.py；examples/mcp-native-task.json 提供自有原生 fixture 模板，先配置本机 policy。自动管理员审批只有显式 --approve-owned-fixture 才启用，不能代替客户人工审批。

用户已指定当前 Codex、系统 Hermes、DeepSeek Harness 三种开发调用方，见 [Harness 证据](../evidence/2026-10-12-harness/README.md)。scripts/verify_harness_clients.py 只做自有 fixture 验收；原生逐回合路径与 sdk-code 组合路径分别记录。DeepSeek 测试环境使用官方 SDK 0.1.5rc1，自带 native runtime，不新增 Core 模型依赖。本 Mac 的 Hermes 配置 key 仅在内存中读取并注入进程；其他环境使用自己的私有配置，不复制 key 到公共文件。Codex CLI 当前模型兼容性失败，与当前会话 MCP bridge 通过单列。

## Windows

在已登录的交互桌面上，从 Git checkout 启动 PowerShell：

```powershell
powershell -File scripts/install_runtime.ps1
uv sync --frozen --extra mcp --extra browser --group test --python cpython-3.12.13-windows-x86_64-none
uv run pytest -q
uv run python scripts/verify_runtime.py --output "$env:TEMP\bokkio-runtime-acceptance-NEW"
dotnet build fixtures/windows-visual/windows-visual.csproj -c Release
uv run python scripts/verify_runtime_visual.py --fixture fixtures/windows-visual/bin/Release/net8.0-windows/bokkio-visual-fixture.exe --output "$env:TEMP\bokkio-runtime-visual-NEW"
```

.NET 8 SDK 用于测试 fixture；如实际输出名不同，以 csproj 的构建结果为准。另选自有 WinForms/UIA 字段应用执行原生三轮，增加 verify_runtime.py 的 --native-app/--field；仓库历史 vendor fixture 不随 Git 分发，不能假设新电脑上已存在。

特别验证 PowerShell UTF8 中文、Windows OS 身份、单线程 COM、物理像素/DPI、输入前窗口/前台/hash、取消进程树；记录 Windows 版本、CPU/解释器架构和缩放。ARM guest 的 x64 Python 仿真成绩不代表实体 x64 设备。

## 证据和完成条件

每个验收使用新的输出目录；保留失败与零派发重观察尝试，未知完成不得自动重发。将不含凭据、账号、客户数据及绝对主机路径的摘要放到 docs/evidence/DATE-runtime-PLATFORM/，写明源修订、命令、环境、独立检查和分母，添加 SHA256SUMS。原始 SQLite、截图与私有请求不提交。

更新 docs/progress/STATUS.md 与 state.json；涉及产品范围同时更新 README 和 RUNTIME-DELIVERY。提交中文说明并推送，另一端通过 Git 接续。最终支持范围以两端实机、客户任务和故障矩阵为准。

## 本机凭据记录

此前 Windows VM 登录凭据已在 Mac 私有目录保存，2026-10-11 已验证可登录。凭据不进入公共进度文件或 Git，其他 Windows 设备使用各自账户。无需在其他环境复制旧 VM 的密码或自动登录设置。

## 自主业务评测接续

本机 runner 为 macOS：`scripts/evaluate_runtime_business.py`；12 题输入和只读业务判定在 `evals/runtime_business.py`，catalog 为 `fixtures/runtime-business-eval/suite.json`。每轮使用新的私有输出目录；命令示例：

```sh
uv run python scripts/evaluate_runtime_business.py --output /tmp/bokkio-business-NEW --tasks T03 T05 T09 T11 --variant 3 --pregranted-disposable-only
```

配置本机 Hermes、DeepSeek Python 路径；`--hermes-runtime` 可指定已经准备好的私有 Hermes 数据根。直接复制 Hermes 环境会保留绝对路径记录，不能假定复制后可启动。启动/安装时间计入用例墙钟；不要在统计时悄悄扣除。该 runner 不改用户原配置，key 仅从私有 Hermes 读取并传入子进程环境。

当前 Codex bridge：runner 发出 ready 后，阅读目标 prompt，以 official MCP client 调用 Core 完成目标，随后写 ready 所属目录的 complete.json，仅作调用方完成信号。其他调用方由 runner 自主运行；不要给它们提供业务解法代码。Codex 保留上下文且编写评分器，报告须继续披露。

历史证据可用 `scripts/regrade_runtime_business.py` 重评分；必须验证原产物哈希未改，只使用评分开始之前的作业完成事件。原始分数和更正分数并列；重评分不是新尝试。macOS 原生表格 judge 处理表名空单元格，文档 judge 校验章节内事实、逐发票金额、任一章节的总额与原样 appendix，不能要求未在目标中规定的标签格式。Windows 需换成对应应用并增加实机评分，不直接运行本 Mac 的应用绑定。

最新重点矩阵为 Codex 4/4、Hermes 2/4、DeepSeek 3/4。不要自动放宽预算来补分：Hermes 错负责人、两种调用方 Preview 超预算需要在新的冻结轮次处理。最新本机故障 16/18，UserNotificationCenter 顶层窗口阻塞两项正向输入；保持零派发守卫，待正常解除遮挡后补测。
