# 桌面对话 Jev 接线实测

2026-10-15；基线 72d0ba9。桌面对话新原生 UI 操作已接通 Harness SDK → Jev → Runtime/Driver，旧 SDK 循环保留。Runtime 本身仍不依赖模型。Shortcuts 固定步骤回放保持原路径。

| 检查 | 结果 | 实际操作 |
|---|---:|---|
| Python 完整回归 | 697/697 | 原有接口检查与新增 Jev 接线、幂等、并发、界面变化、观察过期、取消、未知派发、MCP、凭证和日志记录检查 |
| 补录合并 Node 测试 | 3/3 | 保留既有 Workflow 编辑行为 |
| macOS 开发版 | 14/14 | Harness 实际任务 → 两次真实 Jev 决策 → TextEdit 全文替换、Right 键 → 独立原生读回 |
| macOS 安装版 | 14/14 | 同样链路，自带 Python/SDK/MCP 执行 |
| Windows ARM64 安装版 | 14/14 | 同样链路，Notepad，使用包内 x64 Python/SDK 与 ARM64 Electron |
| macOS 安装版兼容复测 | 13/13 | 真实操作录制/回放及独立读回、固定 Workflow 三层日志、真实模型纯读取任务 |
| Windows 安装版兼容复测 | 13/13 | 同上，固定回放与纯读取任务实际零次 Jev |
| 两端包内审计 | 通过 | 关键 Python、Electron 源码一致，SDK 由包内环境运行，无视频实现/字段或打包测试代码 |

两端安装版各产生两条实际 decision.requested / decision.returned / decision.selected；第一次选择 set_value，第二次选择 key；选中结果分别通过 desktop.act 与 desktop.input 派发。每个局部步骤包含原观察、模型返回后的新观察、执行、独立读回，父子关系按真实操作 ID 关联。任务最终文本为 `Bokkio Jev 三层链路验证`，外部测试进程重新读取应用验证，未从助手文字推断成功。

macOS 安装版 Harness 默认 Python 已确认位于 `Bokkio.app/Contents/Resources/runtime/python/bin/python3`。测试没有覆盖成开发环境 Python。Windows 测试也未设置 Harness Python 覆盖。

## 关键行为

- Harness 提交局部目标和允许字面值，Jev 从原生控件树选择动作与 ref。显式键盘/右键/拖动输入保留，目标仍由 Jev 选择。
- Jev 请求、返回、选中和失败事件直接进入本地审计；界面显示模型、ref、动作、置信度及驱动结果。纯读取不会伪造 Jev 调用。
- Model 返回后刷新观察，语义树变化则零派发；慢响应不会直接使用过期 observation_id。
- step operation_id 持久幂等；并发重复请求不再次调用模型，不再次输入。未知完成保持未知，不自动重放。
- Jev 不可用、无效输出或低置信度会失败并交回 Harness，不静默改走直接控件动作。
- Jev 独立密钥使用系统 safeStorage，普通配置不保存密钥；全局模型在 OpenRouter 时允许共用 Key，其他 provider Key 不转发。

## 证据

- [Mac 安装版结果](macos-installed.json)、[决策与执行树](macos-trace.json)、[Jev 控件决策界面](macos-jev-decision.png)。
- [Windows 安装版结果](windows-installed.json)、[决策与执行树](windows-trace.json)。
- [Mac 固定回放/纯读取兼容复测](macos-compatibility.json)、[Windows 兼容复测](windows-compatibility.json)。
- [完整回归](regression.txt)、[Node 回归](recording-tests.txt)、两端 package-audit JSON、[源码摘要](source-files.json)。

真实测试入口为 `desktop/tests/bokkio-desktop-jev.cjs`，使用既有可丢弃唯一编辑器文档；测试凭证由外部环境显式注入，未写入仓库或正式应用凭证库。测试数据与正式应用历史分开。首次开发测试曾把合法 foreground replace_text 排除在断言外，断言已按实际执行器实际行为修正；最终表格对应重跑后的成功结果，安装版首步实际为原生 set_value。

原完整业务矩阵继续保持用户要求的暂停。本报告的真实应用范围为上述 TextEdit/Notepad 流程。
