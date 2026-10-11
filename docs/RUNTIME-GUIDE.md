# Bokkio Computer Use Runtime

新入口为 `bokkio-runtime`，核心不调用模型，也不要求 Planner/Jev。MCP、CLI、Python SDK 使用同一个执行与授权入口。旧 `bokkio act/run/workflow` 仍是历史开发接口，**不属于新企业执行边界**；生产集成使用新入口。API 版本为 `bokkio.runtime.v1`。

## 安装

macOS：在源码交付包中运行 `sh scripts/install_runtime.sh`。Windows：运行 `powershell -File scripts/install_runtime.ps1`。脚本使用 `uv.lock`，安装 MCP/Browser extras 和 Chromium；需要可用的包源。它们是可复现安装脚本，不宣称已提供离线依赖镜像或签名原生安装器。

Core 支持 Python 3.9+；官方 MCP SDK 要求 Python 3.10+。macOS 安装脚本优先保留现有解释器和授权，Windows 脚本默认使用 x64 Python 3.12，因为当前 xa11y 分发使用 win_amd64 wheel。macOS 原生助手需要 Apple Command Line Tools、Accessibility/录屏/输入权限。Windows 需要已解锁的交互会话；UAC、安全桌面不会被绕过。实际验收平台与未完成项见 [交付状态](RUNTIME-DELIVERY.md)。

## 人工配置权限

从 `examples/runtime-policy.json` 复制一份本地配置。默认无应用/路径/域名权限，写入和宿主脚本禁用。管理员选择必要资源，例如只授权自己的可丢弃测试应用：

```json
{
  "apps": ["BokkioRuntimeNative"],
  "windows": {},
  "paths": ["/absolute/path/to/disposable-workspace"],
  "origins": ["http://127.0.0.1:8080"],
  "write": true,
  "trusted_host": false,
  "require_approval": true,
  "ttl": 3600
}
```

Windows 路径用 JSON 转义，例如 `C:\\BokkioScratch`。`apps` 是当前应用名或 PID，打开会话时绑定进程创建身份；应用重启后重新开会话。`windows` 可用应用名映射精确窗口标题列表；留空表示授权整个应用，包括其弹窗。资源范围由人工配置，不由 Agent 的 session 请求扩大。

`trusted_host: true` 是明确给予宿主 Python/Shell/PowerShell/argv 执行权限，**不是沙箱**；cwd 约束不能阻止脚本直接访问其他文件、UI 或网络。私有 SQLite 同宿主用户可访问，具有任意宿主执行权限的脚本也可能影响本地审批/审计；需要抵抗该行为时必须接入隔离 worker/独立服务身份，本版本尚不承诺此保证。审批工具不通过 MCP 暴露，但不是 OS 隔离的替代品。

`require_approval: false` 只应由人工为已经授权的受限任务设置，操作日志会记录策略哈希；不意味着所有任务均获准。策略变更后重启 MCP 服务；关闭会话会拒绝后续请求，并触发作业取消。已派发操作的副作用不能撤销。

## CLI 与 SDK

```sh
uv run bokkio-runtime --state /absolute/path/to/private-state --policy /absolute/path/to/policy.json call session.open
uv run bokkio-runtime --state /absolute/path/to/private-state --policy /absolute/path/to/policy.json call desktop.observe --session SESSION --args '{"app":"BokkioRuntimeNative"}'
```

动作使用上次返回的 `observation_id` 和元素 `ref`，同一 app/window；观察有效期 15 秒。`desktop.capture` 返回截图 artifact；`desktop.pixel` 使用图像像素 x/y，不要求 OCR 或目标文本。像素输入前窗口须处于前台且未被遮挡；可用 `desktop.activate` 激活精确获准窗口。读回或业务文件检查负责判断是否完成。

```python
from bokkio.sdk import Client

client = Client.from_policy("/absolute/private-state", "/absolute/policy.json")
client.open()
observation = client.call("desktop.observe", {"app": "BokkioRuntimeNative"})
# 从 observation 的 nodes 选择实际观察到的 ref。
response = client.call("desktop.act", {
    "app": "BokkioRuntimeNative", "action": "set_value",
    "ref": observed_ref, "value": "hello",
    "observation_id": observation["result"]["observation_id"]
}, operation_id="caller-generated-unique-id")
```

通过 `examples/runtime_client.py` 可调用 SDK。完整工具 schema 由 MCP `tools/list` 提供，也在 `bokkio.tool_schema.SCHEMAS` 中。每次返回 operation_id、session_id、状态、派发事实和结果；业务完成与动作派发区分。原生字段后置检查确认时返回 `verified`；其他动作的 `executed` 需再验证。

## 审批与恢复

需要审批的请求返回 `approval_required`、`approval_id` 和 `operation_id`，不派发。人工先查看精确私有请求，再决定：

```sh
uv run bokkio-runtime --state STATE approvals --id APPROVAL --show-request
uv run bokkio-runtime --state STATE approve APPROVAL --decision approved --reason '授权的测试窗口写入'
```

客户端使用**原 operation_id、原工具和原参数**重试。参数或代码改变不能沿用旧 ID/审批。可选决定为 approved、denied、revoked；批准有效期五分钟，使用后 consumed。观察/截图仍受自己的时效限制，批准不延长观察有效期。过期观察须重新观察并提交新请求。

重复已完成 operation_id 返回记录，不再次执行。正在执行或崩溃后没有结果的操作返回 `completion_unknown`，先检查 UI/文件和日志，禁止盲目重发。取消无法撤销已经发生的副作用。此幂等机制不承诺 GUI exactly-once。

## 生成代码、进程与 Browser

`code.run` 参数：code、language（python/shell/powershell）、cwd、timeout（≤300 秒）、output_limit（≤1 MB）。`process.run` 使用 argv 数组，不做 shell 拼接。二者需写入及 trusted-host 授权，返回 queued 和 job_id。用 `job.get` 查询、`job.cancel` 取消，或 SDK `client.wait_job(job_id)`。

生成 Python 代码用 `Client.from_environment()` 继承已批准 session；SDK 子调用的日志带父 operation_id。`examples/generated_code.py` 演示 CSV 处理与独立结果检查。stdout/stderr 有上限，持续排空后丢弃超限部分并标记 truncated；超时/取消停止进程树。启动 worker 不代表脚本已派发，实际派发由 job.started/job.finished 和最终 receipt 报告。

Browser 用独立 Playwright worker 保存每会话页面状态，CLI/SDK 跨进程仍可连续操作。`browser.open` 指定 URL；`browser.act` 支持唯一 CSS selector 的 fill/click/press，并要求 expected_url 为上次 open/observe 返回的精确 URL，避免审批等待期间目标悄悄切到另一页面；`browser.observe` 返回有界正文和表单值。网络请求与 WebSocket 受精确 origin 限制，服务 worker 禁用；这不是针对恶意 Chromium 或宿主脚本的 OS 网络沙箱。

`evidence.check` 支持获准文件的存在、哈希及 CSV 行/列检查，返回注册 artifact。`artifact.read` 校验 session、大小和保存时哈希；图片通过 MCP 原生 ImageContent 返回。业务语义正确性由调用者/独立 judge 决定。

## 日志、统计、追溯

所有工具请求、授权、审批、意图、派发结果和代码作业写入私有 SQLite。派发前意图持久化失败则拒绝执行；未完成记录保持可追溯，不自动重发。日志包含可信 OS 身份、平台/架构、task/session/operation/attempt/父操作、请求哈希和结果摘要；普通审计导出不包含任意代码/输入/输出正文。session.open 可指定只含字母/数字/点/冒号/横线的 task_id，否则自动生成关联 ID；不要把敏感业务正文放入此标识。

```sh
uv run bokkio-runtime --state STATE events --session SESSION --follow --after 0
uv run bokkio-runtime --state STATE events --operation OPERATION
uv run bokkio-runtime --state STATE stats --session SESSION
uv run bokkio-runtime --state STATE export --session SESSION --format csv --output audit.csv
```

Agent 可用 session 限定的 `audit.query`、`events.follow`、`metrics.summary`、`approval.status` 和 `audit.export`。支持时间、工具、状态、事件和操作过滤；after 是持久递增序号。导出通过 artifact 获取。逻辑操作、调用尝试、实际派发、审批等待和耗时分别统计；没有客户端模型费用/业务 judge 时，费用和业务成功率返回 null。

本地管理员 CLI 可以查询全部本机记录；MCP 工具只读取自身 session。私有请求、截图和作业输出仍在本地状态目录，应按企业数据策略管理。会话过期会阻止读取，但本版本尚未自动物理清理所有历史数据；不要把它描述为防篡改集中审计库。

## MCP 配置

```json
{
  "mcpServers": {
    "bokkio": {
      "command": "/absolute/path/to/Bokkio/.venv/bin/bokkio-runtime",
      "args": ["--state", "/absolute/private-state", "--policy", "/absolute/policy.json", "serve"]
    }
  }
}
```

Windows command 使用虚拟环境的 `Scripts/bokkio-runtime.exe`。stdio 服务采用官方 MCP SDK，stdout 仅用于协议。工具参数格式为 `{"arguments": {具体工具参数}, "session_id": "SESSION", "operation_id": "可选唯一ID"}`。session.open 返回会话 ID；不要安装或授权额外模型服务才能调用 Core。
