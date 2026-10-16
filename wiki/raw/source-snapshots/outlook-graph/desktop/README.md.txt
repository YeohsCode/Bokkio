---
source_path: desktop/README.md
source_version: working-tree-based-on-404b413b4e980acdd9f1975e8630c877f2278d05
ingested: 2026-10-16
sha256: ac4c547bcb8d711e4bfd96dc56b1c0b3e12b6503ffa4ad380273ca43c80d9d40
---

# Bokkio Desktop Studio

Electron + React 界面；Python Runtime 执行；macOS Swift / Windows Hooks + UIA 录制。无需 Java。网页资源装在桌面应用内部，全局热键、系统输入、凭证加密由本机进程负责。

开发环境使用 Python 3.12 或 3.13。安装并启动：

```sh
uv sync --extra desktop --extra mcp --extra browser --extra office
npm --prefix desktop ci
npm --prefix desktop start
```

桌面应用自动启动 Runtime，无需另开服务器。第一次在 macOS 录制前，在配置页检查辅助功能和输入监控的系统授权。

打包时把托管 Python、平台依赖、SDK 和编译好的原生助手一起装进应用，必须通过打包 Python 的实际 SDK 导入检查：

```sh
uv run python scripts/build_desktop_runtime.py
npm --prefix desktop run package
```

必须在各目标平台上构建 Python Runtime。macOS Intel 与 Apple Silicon、Windows x64 与 ARM64 的本机依赖分别打包。Windows ARM64 可以使用 x64 Python 与 x64 Harness SDK 的系统仿真，Electron 使用 ARM64。

主要页面：

- Shortcuts：操作步骤表、步骤多选/复制/删除/拖动、撤销/重做、目标拾取、图像锚点、相对位置、参数、断点、单步、运行日志、版本恢复与归档恢复。
- 录制：无需预选应用，跨应用演示后自动识别；捕获点击、输入、快捷键及控件/窗口属性，生成结构化步骤；暂停、继续和停止；失败/未识别步骤显示出来，草稿保留在本机。
- 对话：调用 DeepSeek Harness SDK 与 Bokkio MCP；启用 Jev 时，新原生界面操作经 Harness 全局规划 → Jev 局部动作/控件选择 → Runtime 执行/读回；关闭时 Harness 直接选择动作和控件，三层日志对应真实决策和操作 ID；纯读取、固定 Workflow 不调用 Jev。
- 配置：Microsoft / Outlook 账户连接、取消、状态、退出与未读统计；全局模型与 Jev 开关/自定义 API URL/模型/独立密钥、工作目录、系统加密凭证、连接测试、系统授权状态。

本机直接执行默认开启；企业 CLI 仍使用显式策略。前台回放时主窗口让出屏幕，暂停或完成后恢复。Ctrl/⌘ + Shift + F12 全局停止；Ctrl/⌘ + Shift + P 暂停。后台回放限可验证的原生操作，不向后台应用发送普通鼠标和键盘事件。

操作录制生成 Workflow，回放重新操作应用。图像锚点按需截取窗口中的控件区域；macOS 仅在使用图像定位时需要屏幕采集授权。原始输入、运行数据库和凭证不进入 Git；录制排除密码控件。原型 HTML 的点击测试不计为产品验收；桌面验收直接操作 Electron 窗口并独立读取目标应用结果。


当前专项：[操作录制修正](../docs/evidence/2026-10-15-operation-recording/README.md)。历史实测：[Desktop Studio 0.3](../docs/evidence/2026-10-15-desktop-studio/README.md)。macOS Apple Silicon 和 Windows ARM64 VM 已构建应用目录；Windows 使用 x64 Python/SDK。相同的界面和 Workflow 格式分别连接本机适配器；跨系统复用录制时，需要重新绑定系统中的应用和控件。

实际界面测试按顺序运行，避免多个回放争用前台应用。macOS 文本流程使用一个可丢弃的 TextEdit 文档：

```sh
node desktop/tests/bokkio-desktop-flow.cjs
node desktop/tests/bokkio-desktop-editor.cjs
node desktop/tests/bokkio-desktop-long-recording.cjs
```

Windows 测试连接本机以 `--remote-debugging-port=9228` 启动的 Bokkio；先打开一个可丢弃的 Notepad 文档。`BOKKIO_TEST_PYTHON` 指向包含项目依赖的 Python，`BOKKIO_TEST_CDP` 可修改调试端口：

```sh
node desktop/tests/bokkio-desktop-windows.cjs
# 配置测试 provider 后，检查实际 SDK 代码作业停止
node desktop/tests/bokkio-desktop-windows-stop.cjs
```

测试用的调试端口无需加入正常桌面快捷方式。图像与修复测试还需运行自有 Cocoa fixture；对话测试需显式配置测试 provider 环境变量，不从个人配置自动读取凭据。

分层日志与当前决策路径见[实际分工](../docs/DECISION-LAYERS.md)。日志可全部展开/收起，按真实操作 ID 关联；同一操作的缓存回执不会显示为新派发。

Jev 接线实测：显式配置 BOKKIO_TEST_API_KEY / BOKKIO_TEST_BASE_URL / BOKKIO_TEST_MODEL，在可丢弃的唯一 TextEdit/Notepad 文档上运行 `node desktop/tests/bokkio-desktop-jev.cjs`。测试实际模型、原生全文替换、键盘输入、独立读回、Jev 事件与三层 UI。凭证仅进服务内存；用 BOKKIO_ELECTRON 指定安装版。见[报告](../docs/evidence/2026-10-15-desktop-jev/README.md)。

Jev 配置：选择预设或填写完整 HTTP(S) endpoint、模型名和对应 Key，保存后用于下一任务。自定义接口遵循 Jev Decisions 协议，关闭时不加载 Jev。历史任务保留执行时的模式。`node desktop/tests/bokkio-desktop-jev-options.cjs` 使用隔离凭证目录验证自定义服务、开关两种模式与重启持久化；本机 relay 将自定义模型别名映射到真实 Jev 后端。

## Outlook Graph / PowerShell

配置页点击准备组件、连接，使用微软页面的设备码完成首次授权。Bokkio 复用官方 Graph PowerShell 默认应用身份，用户不需要创建 Entra 应用。每台电脑/系统用户使用 CurrentUser SDK 缓存，令牌自动刷新；密码不交给 Bokkio，账户入口统一，令牌不复制进模型密钥库。Graph 未读查询不需要桌面辅助功能，当前只统计收件箱，不读正文、不发送/修改邮件。

[连接与缓存指南](../docs/OUTLOOK-GRAPH.md) · [两端 UI 测试与待验证项](../docs/evidence/2026-10-16-outlook-powershell/README.md)。两端 UI 各 10/10 为离线 Graph 夹具；真实账户和重启后的令牌复用尚待登录验证。
