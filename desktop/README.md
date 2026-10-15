# Bokkio Desktop Studio

Electron + React 界面；Python Runtime 执行；macOS Swift / Windows Hooks + UIA 录制。无需 Java。网页资源装在桌面应用内部，屏幕采集、全局热键、系统输入、凭证加密由本机进程负责。

开发环境使用 Python 3.12 或 3.13。安装并启动：

```sh
uv sync --extra desktop --extra mcp --extra browser --extra office
npm --prefix desktop ci
npm --prefix desktop start
```

桌面应用自动启动 Runtime，无需另开服务器。第一次在 macOS 录制前，在配置页检查辅助功能、屏幕录制和输入监控的系统授权。

打包时把托管 Python、平台依赖、SDK 和编译好的原生助手一起装进应用：

```sh
uv run python scripts/build_desktop_runtime.py
npm --prefix desktop run package
```

必须在各目标平台上构建 Python Runtime。macOS Intel 与 Apple Silicon、Windows x64 与 ARM64 的本机依赖分别打包。Windows ARM64 可以使用 x64 Python 与 x64 Harness SDK 的系统仿真，Electron 使用 ARM64。

主要页面：

- Shortcuts：真实视频预览与时间线、步骤多选/复制/删除/拖动、撤销/重做、目标拾取、图像锚点、相对位置、参数、断点、单步、运行日志、版本恢复与归档恢复。
- 录制：选择实际运行的应用和屏幕/窗口；录屏和结构化事件同步采集；暂停、继续和停止；失败/未识别步骤显示出来，草稿保留在本机。
- 对话：调用 DeepSeek Harness SDK 与 Bokkio MCP，保留任务历史、工具事件和实际结果。
- 配置：模型地址/模型/工作目录、系统加密 API Key、连接测试、系统授权状态。

本机直接执行默认开启；企业 CLI 仍使用显式策略。前台回放时主窗口让出屏幕，暂停或完成后恢复。Ctrl/⌘ + Shift + F12 全局停止；Ctrl/⌘ + Shift + P 暂停。后台回放限可验证的原生操作，不向后台应用发送普通鼠标和键盘事件。

原始录制、视频、运行数据库和凭证不进入 Git。视频会包含画面上可见内容；结构化录制排除密码控件。原型 HTML 的点击测试不计为产品验收；桌面验收直接操作 Electron 窗口并独立读取目标应用结果。


实测报告：[Desktop Studio 0.3](../docs/evidence/2026-10-15-desktop-studio/README.md)。macOS Apple Silicon 和 Windows ARM64 VM 已构建应用目录；Windows 使用 x64 Python/SDK。相同的界面和 Workflow 格式分别连接本机适配器；跨系统复用录制时，需要重新绑定系统中的应用和控件。

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
