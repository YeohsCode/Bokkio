# Workflow Studio：手工录制、维护与 Runtime 回放

本机浏览器 UX 已实现。运行 `bokkio-runtime studio` 自动打开界面；开发环境可用 `uv run bokkio-runtime studio`。默认数据目录为 `~/.bokkio/runtime`，用 `--state` 指定其他工作区。`--no-open` 仅输出本机地址，`--port` 可固定端口。

## 使用路径

1. 新建 Workflow，填写名称和说明，加载运行中的应用并勾选需要录制的应用。
2. 开始录制，然后在所选应用中点击控件、输入文字。暂停会停止捕获进程，继续录制保留暂停边界；停止后将步骤载入编辑区。
3. 查看步骤，修改输入值、窗口标题、动作和控件上下文；调整顺序或移除步骤。通过“＋ 桌面步骤”读取当前窗口的控件并添加动作，也可加入网页或脚本步骤。未识别的操作会提示审阅，不自动当成已完成步骤。
4. 保存为新版本。查看历史版本、修改、重新保存或归档均在同一界面完成。归档保留版本和运行记录；编辑冲突要求重新加载，不覆盖别人的改动。
5. 选择有头或无头回放。桌面步骤也支持无头后台原生模式；它不主动激活前台、不派发鼠标／键盘输入，但仍需要未锁定的交互桌面和 WindowServer。网页使用隔离 Chromium，按所选模式启动；脚本是否能无头运行取决于其自身依赖，不会自动把桌面点击转换成脚本。
6. 开始回放；默认逐项审批，可查看精确请求与目标。用户也可明确授权本次所列流程动作和资源。传入管理员 `--policy` 时该策略始终是上限，界面不能扩大授权。
7. 在运行记录查看步骤、Core operation ID、审批、失败和完成状态。暂停在当前操作后的安全边界生效；取消会拒绝未派发的待审批请求，并尝试取消代码作业。

这是本机 Web UI，没有新增云服务、账户或 npm 构建链。地址仅监听 127.0.0.1；API 要求随机访问令牌，校验 Host/Origin。工作流和私有运行请求保存在本机，不上传模型提供方。POSIX 私有文件使用 0600 权限。

## 录制范围

macOS 录制器使用被动事件监听，捕获所选应用中的点击和输入；通过 AX 值读回归并文字修改，覆盖编辑器和输入提交。只保存最后的字段值，不保存原始按键文本或剪贴板内容。安全输入字段排除。观察在独立队列进行，捕获器不会吞掉输入或再次执行动作；拥有者进程退出时捕获器停止。

原生目标保存 role、name、identifier 和窗口／父级上下文，不保存屏幕坐标作为回放身份。窗口移动、跨屏位置变化和新 PID 不使已命名的原生控件选择器失效；同名／同 identifier 的歧义目标拒绝执行。窗口标题、应用布局或控件语义改变仍可能需要编辑流程，不能保证任意界面变化都能自动恢复。

快捷键、拖拽、右键和无法语义定位的画布操作会进入待审阅列表；滚动可补充为明确的原生 scroll 步骤。当前不把这些手势静默编译成不可靠坐标宏。点击默认完成检查只确认目标存在，用户应补充业务结果检查。Windows 手工键鼠监听尚待 Windows 环境实现和验收。

## 应用启动与健壮性

工作流保存应用的安装路径、名称和 bundle ID；运行时不复用录制 PID。无头模式使用 `desktop.launch background=true` 请求后台启动；若应用自行激活，会停止并报告其效果待检查。新 `desktop.launch` 工具只能启动管理员 `launch_apps` 中的精确身份，不接受调用方提供 shell 或任意 executable。它执行原有写入授权、审批、审计，再等待应用注册，绑定实际 PID 和进程出生身份。

同一安装身份对应多个实例时拒绝猜测。每步重新观察、重新定位并验证结果；原生控件不依赖录制位置。步骤之间进程消失或身份改变时，重新通过受控启动请求绑定应用。启动应用不等同于恢复任意业务文档；缺失窗口会等待至步骤期限后明确失败。

每个动作先保存精确 operation ID，再通过 `Runtime.call()` 派发。中断后读取同一个回执；已经完成的动作不重发，未知完成停止。审批后的观察过期只允许已知零派发的重新观察／新请求，且需要新的精确批准，最多两次。不延长原生观察 TTL，也不把一次父层批准当成子动作的批准。

## CLI、SDK 与 MCP

新入口属于企业 Runtime；历史 `bokkio workflow` 仍保留为旧开发接口，两者 schema 不互相冒充。

```sh
bokkio-runtime --state ~/.bokkio/runtime studio
bokkio-runtime --state ~/.bokkio/runtime workflow list
bokkio-runtime --state ~/.bokkio/runtime workflow show WORKFLOW_ID
bokkio-runtime --state ~/.bokkio/runtime --policy policy.json workflow replay WORKFLOW_ID --mode headed
bokkio-runtime --state ~/.bokkio/runtime --policy policy.json workflow resume RUN_ID
bokkio-runtime --state ~/.bokkio/runtime workflow status RUN_ID
```

工作流数据格式为声明式 **JSON**（`bokkio.runtime-workflow.v1`），不是 VBA、Python 或 Go 程序。Python／Shell／PowerShell 是可选代码步骤；原生、网页步骤保存动作与参数。YAML 不是当前持久化格式。

工作流数据在 `STATE/workflows/ID/REVISION.json`；运行检查点在 `STATE/workflow-runs`，审计仍在同一 Runtime SQLite 中。JSON 字段包含应用身份、步骤、等待和完成检查，网页／代码资源在 `resources.paths`、`resources.origins` 中声明。高级编辑可以维护完整 JSON；运行冻结已保存版本，编辑不会改变正在运行的流程。

MCP / `Client.call()` 新增 `workflow.list/get/run/status/resume/cancel`。管理员策略用 `workflows` 显式允许工作流 ID，`launch_apps` 允许启动身份，另配置 apps、paths、origins 和原有 write/approval/trusted_host。先 `session.open`（应用尚未运行时传 `apps: []`），再 `workflow.run`，轮询 `workflow.status`；管理员处理待审批子动作后调用 `workflow.resume`。运行和查询均绑定原 Session；不能用其他 Session 读取或恢复运行。

```json
{
  "apps": ["TextEdit"],
  "launch_apps": {
    "editor": {"name": "TextEdit", "path": "/System/Applications/TextEdit.app", "bundle_id": "com.apple.TextEdit"}
  },
  "workflows": ["REPLACE_WITH_SAVED_WORKFLOW_ID"],
  "write": true,
  "trusted_host": false,
  "require_approval": true
}
```

策略中的 alias 必须与保存的 Workflow 对应。以上是结构示例，不会自动创建可执行流程。代码执行沿用 trusted-host 边界，未提供逐文件 OS 沙箱。

## 测试与当前限制

专用测试目录为 `fixtures/workflow-recording`，合同测试为 `tests/test_runtime_workflow.py`；实机脚本是 `scripts/verify_workflow_recording.py`、`scripts/verify_manual_recording.py` 和 `scripts/verify_workflow_mcp.py`、`scripts/verify_physical_recording.py`、`scripts/verify_background_workflow.py`。覆盖窗口移动、进程重绑、启动延迟、歧义、版本冲突、暂停、取消、审批到期、未知完成不重发、代码作业和两个浏览器模式。

本机最终分数及源码哈希见 [Workflow 报告](evidence/2026-10-13-workflow-studio/README.md)。真实 OS 事件录制／回放已通过；初次前台预检失败的具体阻挡原因未确认，原始结果保留。生成的输入／AX 读回不冒充真实人工验收，前台与图像守卫保持不变。当前三调用方完整业务矩阵仍按用户要求暂停，历史成绩不能填入这次新增源码的验收表。

### 桌面无头支持边界

无头后台桌面使用经过验证的 AX／UIA 原生传输。需要鼠标、键盘或视觉兜底的控件在派发前明确拒绝，不能偷偷抢前台。录制文本按 set_value 固化；依赖光标的 type/select_text 需先改为可核验原生写入。原生动作若令目标应用自行成为前台，保留未知效果并停止，不自动重复。macOS 当前已用独立前台应用和鼠标位置验证后台启动与完整录制重放；Windows 对应传输仍需实机确认。没有桌面会话的服务器执行需要网页／代码／应用 API 通道，不能把普通 macOS GUI 应用自动变成无显示服务。
