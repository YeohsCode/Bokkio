# macOS Runtime 续测证据

日期：2026-10-12。基于提交 4d5d0cf 的工作树，当前代码文件哈希见 source-files.json。不同开发轮分别保留，不合并为固定版本稳定率；最终包另行复测。

| 证据 | 结果与范围 |
|---|---|
| fault-matrix-r7-summary.json | 完整本机矩阵 16/18：窗口移动/缩放、像素变化、前台接管、真实 15 秒过期、锁等待时关闭会话、同名歧义、进程退出、最小化与五项真实进程故障通过；重建后的正向点击、当前显示器坐标正向点击均被系统通知的前台守卫零派发拒绝 |
| fault-matrix-r6-summary.json | 前一完整开发轮 15/18；还包含最小化动画期间 capture_timeout，后续 fixture 确认实际最小化且不在屏幕后再检查，r7 通过 |
| job-faults-summary.json | 五项真实作业故障 5/5；子进程忽略 SIGTERM 仍被取消、超时/关会话终止树、worker SIGKILL 后未知完成不重发、输出持续读取并截断 |
| native-contract-summary.json | 自包含 Cocoa 原生 fixture；原生字段、代码、Browser 各 3/3，MCP/CLI、审批和日志对账通过；不依赖 ignored vendor |
| mcp-manifest-summary.json | 通用任务清单 + 官方 MCP SDK，三个中文字段写入、审批及独立读回 3/3；管理员自动批准只用于自有可丢弃 fixture |
| numbers-mcp-summary.json | 当前 Codex 通过官方 MCP client bridge，生成/打开三份本机 CSV，再用观察到的 ref 写入 Numbers 工作表名称字段；原生确认、独立读回、导入值与源 CSV 哈希保持 3/3。83 条导出事件、5 次批准使用、3 次原生写操作。开发管理员审批，非客户人工批准；没有为 Numbers 增加 Core 规则；未验收 .numbers 保存与新进程重开 |
| fault-matrix-r2/r3/r4/r5-partial.json、runner-interruptions.json | 保留早期坐标假设错误、前台拒绝和最小化动画导致的 runner 中断，不当作完整矩阵成绩 |

实际环境只有一个 2560×1440、scale=1 显示器。未做真实锁屏/解锁、第二显示器或不同缩放。客户应用和实际客户 Harness 尚未指定，Numbers 与当前 Codex 的成绩仅为开发证据。

原始数据库、截图、账号身份、精确请求和运行输出在本机私有测试目录。此目录只保存可共享摘要和校验和。接续以 [共享状态](../../progress/STATUS.md) 为准。

最终 wheel 安装到独立环境后的复测见 final-wheel-summary.json：原生/代码/Browser 各 3/3，官方 MCP/CLI、审批及日志对账通过。主机完整回归 546/546（9.02 秒），不替代上述未完成桌面和客户验收。
