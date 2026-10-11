# 跨环境接续说明

## 开始工作

1. git pull，阅读 [共享状态](STATUS.md)、[结构化待办](state.json) 和 [计划](../PLAN-REPOSITIONING.md)。确认当前分支及本地变更，避免覆盖另一端工作。
2. 使用项目 uv.lock 安装，Runtime 主线不需要模型 API Key。策略模板 examples/runtime-policy.json 默认为拒绝，按本机实际测试资源配置。
3. 选取一个待办 ID，在状态中注明平台和进行中；完成后补充结果、失败、修订和证据路径。避免两端同时修改相同代码文件；推送前拉取并处理冲突。

## macOS

```sh
sh scripts/install_runtime.sh
uv sync --frozen --extra mcp --extra browser --group test
uv run pytest -q
uv run python scripts/verify_runtime.py --output /tmp/bokkio-runtime-acceptance-NEW
```

最后一条只验证代码/Browser/MCP/CLI/审批/审计。原生验证需启动明确授权的自有测试应用，再增加 --native-app APP --field Search；不能将省略原生项的结果称为桌面验收。辅助功能、屏幕录制和真实交互桌面按指南确认。

自绘视觉 fixture 源码位于 fixtures/cocoa-visual/main.swift，编译并包装成 App 后运行：

```sh
uv run python scripts/verify_runtime_visual.py --fixture /ABS/PATH/Test.app/Contents/MacOS/Test --output /tmp/bokkio-runtime-visual-NEW
```

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
