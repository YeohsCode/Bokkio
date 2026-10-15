# Jev 开关与自定义接口实测

2026-10-15，基线 e0efada。配置页新增默认开启的 Jev 开关，以及可编辑的完整 API URL、Key 和模型名。保存用于下一任务；正在运行和历史任务保留启动模式。

| 检查 | 结果 |
|---|---:|
| Python 完整回归 | 715/715 |
| 补录 Node 回归 | 3/3 |
| macOS 最新安装版真实界面 | 19/19 |
| Windows ARM64 最新安装版真实界面 | 19/19 |
| 两端包内源码一致性与无视频检查 | 通过 |

## 真实任务

两端用相同 Electron 测试入口 `desktop/tests/bokkio-desktop-jev-options.cjs` 操作配置页，并在 TextEdit / Notepad 的可丢弃唯一文档中运行真实 Harness 任务。

1. 在界面选择自定义服务，填写本机 relay 的完整路径 `/custom/v2/decisions`、独立测试 Key、模型名 `local/custom-jev-alias`，保存配置。
2. 校验 Key 文件由系统加密，普通设置 JSON 和 Harness patch 都不包含 Key 明文。relay 实际核对路径、Authorization 和模型名，再将别名映射到真实 Jev 后端 `typesafe/jev-1.13`；调用没有使用合成决策回答。
3. 开启时调用 Jev 完成全文替换，并由外部进程原生读回。Mac 实际 3 次 Jev 请求，Windows 1 次，所有请求的自定义字段匹配。
4. 关闭 Jev，确认旧任务日志仍保留开启模式；退出并重开安装版，检查开关、URL、模型名和加密 Key 均保留。
5. 新任务改由 Harness 选择 ref/action，通过 desktop.act/input 执行另一段全文替换，并再次独立读回。两端 relay 请求数均不再增加，日志均为零次 Jev，动作选择标明 Harness。

两端未覆盖 Harness Python，均使用安装包自带 Python/SDK/MCP。测试凭证目录和任务数据目录与正式应用分开。正式应用没有写入测试 Key 或测试历史；Windows 最后按普通方式启动，没有调试端口。

自定义接口使用 Jev Decisions 的 model/state/questions 协议；测试使用 relay 的模型别名映射，不表示任意 Chat Completions 服务可直接替代 Decisions。

## 本轮发现并修正

- SDK MCP 启动会清理密钥环境变量；已使用其支持的 `!!js` 环境变量引用显式传入，普通 patch 不保存密钥值。
- 系统代理会错误转发本机 endpoint；loopback 现在直连。
- 关闭模式下重复的 100 KB 观察曾导致模型上下文溢出；全局模型默认改为 60 节点/16 KB，Jev 内部仍使用完整本机树，完整快照保留为 artifact。
- 非 type 操作的 expected_value 在派发前拒绝，避免把参数错误误记为未知派发。
- SDK 曾以 completed 结束但没有可见最终答复；现在该情况标为失败，不误报任务完成，没有增加外层 agent loop 或自动重派发。
- 配置现在优先加载，载入前开关和保存按钮禁用；重启 UI 检查等待实际加载状态。

最终 19/19 来自上述修正后重新构建的安装版；之前失败的尝试不计入通过数。

## 文件

- [Mac 安装版结果](macos-installed.json)、[开启日志](macos-enabled-trace.json)、[关闭日志](macos-disabled-trace.json)、[关闭模式界面](macos-disabled-ui.png)。
- [Windows 安装版结果](windows-installed.json)、[开启日志](windows-enabled-trace.json)、[关闭日志](windows-disabled-trace.json)。
- [完整回归](regression.txt)、[Node 回归](recording-tests.txt)、两个 package-audit JSON、[源码摘要](source-files.json)。

本次真实应用范围为上述编辑器流程；原完整业务矩阵仍按用户要求暂停。
