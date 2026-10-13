# Workflow Studio 与后台桌面回放执行报告

日期：2026-10-13；开发基线 f6e2c6c，当前源码 SHA 见 [source-files.json](source-files.json)。这些是功能合同／自有应用测试，不能代替三调用方自主业务成功率或客户验收。原完整业务复测仍按用户要求暂停。

## 已交付

- 本机 Web UX：新建、应用选择、开始／暂停／继续／停止录制、查看与编辑步骤、重排／移除、当前控件选取、网页／脚本步骤、版本历史、归档、回放和运行记录。已在当前 Codex 内置浏览器实际操作；其不支持原生 prompt，已改为 HTML 表单对话框。
- 声明式 JSON：`bokkio.runtime-workflow.v1`；应用安装身份、语义选择器、动作参数、等待／完成检查、版本和 SHA。Python／Shell／PowerShell 是代码步骤，整个工作流不是脚本。
- macOS 被动录制：所选应用、实际鼠标事件和文字读回；不再派发录制动作，暂停终止监听，拥有者退出时停止；密码排除、未识别手势显式待审阅，Studio 控制面板排除。
- Runtime 回放：CLI、SDK、MCP 使用同一授权、精确审批、作业、审计和检查点。按应用身份重新启动、绑定新 PID；窗口移动用新原生观察定位，歧义拒绝、未知完成不重发。
- 桌面也可选 headless：后台原生 AX／UIA 传输，不使用鼠标／键盘或视觉兜底。需要这些通道的控件在派发前拒绝；应用自行激活会停止检查效果。macOS 仍需要未锁定的交互桌面和 WindowServer，不等于无显示服务器执行。

## 结果与分母

| 验证 | 结果 | 范围 |
|---|---:|---|
| [全回归](regression.json) | **613/613** | 包含 26 项 Workflow 合同；不是业务任务数量 |
| [Runtime 实机矩阵](integration-latest.json) | **9/9** | 三种窗口位置、关闭后自动启动、新 PID、歧义、后台原生、审计关联、网页／代码两种模式 |
| [被动文字读回](readback-latest.json) | **4/4** | 独立 Runtime 产生测试输入；暂停排除、恢复边界、录制器零写派发 |
| [真实 OS 生成事件录制／回放](physical-latest.json) | **5/5** | 鼠标按钮与文字、无录制问题、零重复派发、同一 JSON 重放后独立字段／点击次数 |
| [后台桌面见证](background-latest.json) | **5/5** | 目标先关闭，后台启动并回放完整录制；独立前台应用及鼠标位置未变，无像素／激活兜底 |
| [官方 MCP stdio](mcp-latest.json) | **通过** | 真实 Core、六个 workflow 工具、实际应用状态及操作关联；工具总数 30 |
| [安装包](package.json) | **通过** | 源码／Swift／HTML／JS／CSS 打包；checkout 外安装、管理界面与 API 验证 |

录制事件由受控输入生成器产生，使用真实 OS 事件管道；它验证监听器与回放，并不冒充用户本人或客户参加的演示。后台见证使用另一个自有应用留在前台，比较前后 PID 和鼠标位置；没有用 Terminal、客户文档或其他用户应用充当操作目标。

[UX 记录](UX.json)保留版本编辑和控件选择验证；截图仅留本机，不进入 Git。JSON 和计划／进度进入公共 Git 目录；原始截图、SQLite、运行请求、个人路径和访问令牌不提交。

## 初次失败与更正

- [首批实机矩阵](integration-initial.json) **5/9**：四份原生样本的输入／按钮已经执行，但测试将静态标签类型写为 text，实际是 static_text，完成检查失败。更正测试断言后重新执行，不覆盖首次分数。
- [初次 OS 输入生成](physical-initial.json)在文字输入阶段因光标闪烁触发 `capture_changed`，已知零派发的观察最多两次后终止；未得到完整 Workflow 成绩。一项实际指针 focus 捕获证据留在私有日志。后续仅让自有 fixture 在取图前结束光标焦点，保持相同图像／前台守卫，取得完整 5/5。没有修改或绕过 Runtime 图像守卫。
- [后台见证初始化](background-witness-initial.json)发生在见证窗口尚未就绪时；激活回执为 unknown，不重发该操作。测试加入只读窗口就绪检查后，另开批次验证。
- [初次前台预检](initial-pointer-preflight.json)仅证明目标窗口未到最前；无法据此认定阻挡者是系统通知。先前口头归因已更正。当前前台恢复后实际 OS 事件管道已通过。

## 待验收／范围限制

Windows 人工监听与对应 UIA／后台启动实机验收、用户本人完整演示、客户应用与数据、额外物理显示器和缩放仍待对应环境。原生选择器支持语义不变的移动／重绑，不保证控件改名、布局重构或任意画布手势自动恢复。启动应用不等于自动打开所有业务文档；不存在的窗口明确超时失败。

后台原生与服务器无 GUI 是不同执行条件。没有交互桌面的机器需网页／脚本／应用 API 通道；普通 macOS GUI 应用不能自动变成无显示服务。代码仍沿用 trusted-host 边界，没有新增 OS 文件沙箱、云 SSO 或签名发行。

指南：[WORKFLOW-STUDIO.md](../../WORKFLOW-STUDIO.md)。测试目录：fixtures/workflow-recording；合同 tests/test_runtime_workflow.py；实机脚本 verify_workflow_recording、verify_manual_recording、verify_physical_recording、verify_background_workflow、verify_workflow_mcp。
