# Outlook：通过官方 Graph PowerShell 连接

Bokkio 使用微软官方 `Microsoft.Graph.Authentication` 模块的默认应用身份访问 Graph，不需要用户注册 Entra 应用或填写 Client ID、Client Secret。当前实现提供收件箱未读邮件计数，不读取正文，也不发送或修改邮件。

## 首次连接

1. 在桌面应用打开 **配置 → Microsoft / Outlook 账户**。
2. 如果提示缺少组件，点击 **准备 Outlook 组件**。程序在本机用户目录准备 PowerShell 7，并从 PowerShell Gallery 安装认证模块，不要求用户操作终端。
3. 点击 **连接 Outlook**。页面显示设备码，点击 **打开微软登录页**，在微软页面输入设备码、登录并确认授权。
4. 状态变为 **已连接**后，可点击 **统计本周未读邮件**。统计范围为收件箱、本机时区周一零点至查询时刻收到、目前仍未读的邮件；程序遍历分页，失败时不把部分结果当成总数。

登录等待支持取消。准备组件和登录在后台执行，不阻塞 Workflow 编辑和其他配置。真实账户授权目前尚未完成：用户不在电脑旁，要求先提交本版，后续继续真实邮箱和重启验证。

## 登录一次与统一管理

- 使用 `Connect-MgGraph -Scopes Mail.ReadBasic -ContextScope CurrentUser -UseDeviceAuthentication`。同一台电脑、同一系统用户下，SDK 持久缓存登录并自动刷新令牌，通常无需每次启动重新登录。macOS 与 Windows 各自登录，不跨设备复制缓存。
- 微软密码只输入微软登录页，Bokkio 不保存密码。配置页统一展示账户、状态、验证和退出入口；令牌由官方 SDK 管理，不复制到 Bokkio 的配置、日志或模型上下文。Bokkio 只保存账户、租户和授权范围等非密钥连接元数据，并在查询前核对 SDK 当前账户。
- 模型 Provider/Jev API Key 继续使用已有系统加密存储。模型密钥解锁与 Graph 登录相互独立。
- 点击 **退出 Graph 登录**会调用官方 `Disconnect-MgGraph`。这是该系统用户的 Graph PowerShell 登录缓存，其他使用同一 SDK 缓存的脚本也可能需要重新登录；不会退出 Outlook 应用。
- 用户主动退出、授权撤销或组织要求重新认证时，需要再次登录。企业租户仍可要求管理员同意。默认应用身份用于微软全球云；世纪互联等独立云不能沿用全球云注册身份。

## 调用路径

配置页通过 `desktop_service` 和 `OutlookConnection` 管理准备、登录、状态与取消；测试统计按钮直接调用固定的 PowerShell 查询脚本。模型任务可通过共享 MCP/CLI/SDK 的 `outlook.status` 和 `outlook.unread` 工具进入 `Runtime.call`，保留操作回执与审计。

```python
from bokkio.local_runtime import LocalRuntime
from bokkio.sdk import Client

client = Client(LocalRuntime('/ABS/LOCAL/RUNTIME/STATE'))
client.open(apps=[])
result = client.call('outlook.unread', {
    'start': '2026-10-12T00:00:00+08:00',
    'end': '2026-10-19T00:00:00+08:00',
})
client.call('session.close')
```

`start` 和 `end` 必须包含时区，采用 `[start,end)`。本机 Runtime 默认开放此连接；使用显式企业策略时需由宿主设置 `outlook: true`。`outlook.status.configured` 只表示存在连接记录，实际查询仍会核验身份和访问。

Graph 查询不枚举桌面应用，不要求辅助功能、输入监控或屏幕采集权限。它不证明桌面录制/回放已通过验收，也不替代原生界面执行器。Harness 选择 Graph 工具；Jev 不参与这类 API 查询，只参与启用 Jev 时的新原生界面动作选择。

## 验证

```sh
# 真实 PowerShell 执行随包脚本；Graph cmdlet 使用自有离线夹具
BOKKIO_TEST_PWSH=/ABS/PATH/pwsh uv run python -m pytest tests/test_outlook_graph.py tests/test_outlook_powershell.py -q

# 已打包应用的真实界面；仍使用自有离线 Graph cmdlet 夹具
BOKKIO_TEST_PWSH=/ABS/PATH/pwsh BOKKIO_TEST_OUTPUT=/ABS/ISOLATED/OUTPUT BOKKIO_ELECTRON=/ABS/PACKAGED/EXECUTABLE node desktop/tests/bokkio-desktop-outlook.cjs
```

两端界面测试覆盖连接、分页计数、应用重启后的账户检查、退出、设备码显示和取消。它们不包含真实 Microsoft 账户登录或真实邮箱结果。[本版验证记录](evidence/2026-10-16-outlook-powershell/README.md)

参考：[官方认证与缓存行为](https://learn.microsoft.com/powershell/microsoftgraph/authentication-commands)、[Graph SDK 安装](https://learn.microsoft.com/powershell/microsoftgraph/installation)、[Mail.ReadBasic 权限](https://learn.microsoft.com/graph/permissions-reference#mailreadbasic)。
