# Fixed Graph operations. Request data arrives as JSON, never as PowerShell source.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
function Emit($value) { [Console]::WriteLine(($value | ConvertTo-Json -Depth 8 -Compress)) }
try {
    $request = [Console]::In.ReadLine() | ConvertFrom-Json
    if ($request.action -eq 'prepare') {
        if (!(Get-Module -ListAvailable Microsoft.Graph.Authentication)) {
            Install-Module Microsoft.Graph.Authentication -Scope CurrentUser -Repository PSGallery -Force -ErrorAction Stop | Out-Null
        }
    }
    $module = Get-Module -ListAvailable Microsoft.Graph.Authentication | Sort-Object Version -Descending | Select-Object -First 1
    if (!$module) { Emit @{kind='result'; status='needs_setup'; message='需要安装 Microsoft.Graph.Authentication'}; exit 0 }
    Import-Module $module.Path -ErrorAction Stop
    if ($request.action -in @('probe','prepare')) {
        Emit @{kind='result';status='ready';module_version=$module.Version.ToString();powershell_version=$PSVersionTable.PSVersion.ToString()}; exit 0
    }
    # The official SDK owns CurrentUser cache persistence and refresh. A device
    # challenge is observable, so background reads can stop instead of opening UI.
    Connect-MgGraph -Scopes 'Mail.ReadBasic' -ContextScope CurrentUser -UseDeviceAuthentication -NoWelcome -ErrorAction Stop
    $context = Get-MgContext
    if (!$context -or !$context.Account) { throw 'BOKKIO_AUTH_REQUIRED' }
    if ($request.account -and $context.Account -ne $request.account) { throw 'BOKKIO_ACCOUNT_CHANGED' }
    if ($request.action -eq 'disconnect') {
        Disconnect-MgGraph -ErrorAction Stop | Out-Null
        Emit @{kind='result';status='disconnected'}; exit 0
    }
    if ($request.action -in @('connect','check')) {
        # Verify mailbox access, rather than claiming success from a cached context.
        $null = Invoke-MgGraphRequest -Method GET -Uri 'https://graph.microsoft.com/v1.0/me/mailFolders/inbox?$select=id' -OutputType PSObject
        Emit @{kind='result';status='connected';account=$context.Account;tenant=$context.TenantId;scopes=@($context.Scopes)}; exit 0
    }
    if ($request.action -ne 'unread') { throw 'Unknown operation' }
    $start = [DateTimeOffset]::Parse($request.start).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    $end = [DateTimeOffset]::Parse($request.end).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    $filter = [Uri]::EscapeDataString("isRead eq false and receivedDateTime ge $start and receivedDateTime lt $end")
    $uri = 'https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages?$select=id&$top=1000&$filter=' + $filter
    $count = 0; $pages = 0
    do {
        if (([Uri]$uri).Host -ne 'graph.microsoft.com') { throw 'Unexpected Graph pagination host' }
        $page = Invoke-MgGraphRequest -Method GET -Uri $uri -OutputType PSObject
        $count += @($page.value).Count; $pages++
        $uri = $page.'@odata.nextLink'
        if ($pages -ge 100 -and $uri) { throw 'Mailbox query exceeded 100 pages; narrow the time range' }
    } while ($uri)
    Emit @{kind='result';status='completed';account=$context.Account;folder='inbox';start=$start;end=$end;count=$count;pages=$pages;source='Microsoft Graph / PowerShell'}
} catch {
    # Do not forward SDK exceptions: they may contain authentication payloads.
    $message = $_.Exception.Message
    $code = 'graph_failed'; $hint = 'Graph 请求失败，请检查连接或重新登录。'
    if ($message -match 'BOKKIO_ACCOUNT_CHANGED') { $code='account_changed';$hint='Graph SDK 当前账户已改变，请在配置中重新连接。' }
    elseif ($message -match 'BOKKIO_AUTH_REQUIRED|Authentication|AADSTS|Credential') { $code='authentication_required';$hint='微软登录需要重新验证，请在配置中连接 Outlook。' }
    elseif ($message -match '403|AccessDenied|Authorization_RequestDenied') { $code='access_denied';$hint='微软拒绝邮箱访问，请检查 Mail.ReadBasic 授权或组织策略。' }
    Emit @{kind='result';status='failed';error_code=$code;message=$hint}; exit 1
}
