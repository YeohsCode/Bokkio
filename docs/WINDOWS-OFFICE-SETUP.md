# Windows Office 安装与启动检查

2026-10-04 更新：按用户要求暂缓激活与 Office 办公实测，先运行 Explorer/Notepad 外部多步任务，见 [WAA 实测](P5-WAA-LONGCHAIN.md)。已安装的微软应用保留。

Update: Office activation and workflow tests are paused at the user's request. Native Explorer/Notepad benchmark development runs continue; see the [WAA report](P5-WAA-LONGCHAIN.md).

日期：2026-10-03。**安装完成；激活和邮件账号配置待完成。**

## 安装结果

在现有 Windows 11 IoT Enterprise LTSC Evaluation ARM64 虚机中，通过 Microsoft Office Deployment Tool 安装 Microsoft 365 Apps 完整桌面套件。安装器退出码为 `0`。

| 应用 | 启动文件 | 文件版本 | 安装后原生启动窗口读取 |
| --- | --- | --- | --- |
| Word | WINWORD.EXE | 16.0.20430.20140 | 通过，71 节点 |
| Excel | EXCEL.EXE | 16.0.20430.20140 | 通过，78 节点 |
| PowerPoint | POWERPNT.EXE | 16.0.20430.20140 | 通过，71 节点 |
| Outlook（经典版） | OUTLOOK.EXE | 16.0.20430.20140 | 通过，8 节点；启动界面稀疏，账号设置仍待完成 |
| OneNote | ONENOTE.EXE | 16.0.20430.20140 | 通过，162 节点 |
| Access | MSACCESS.EXE | 16.0.20430.20140 | 通过，72 节点 |
| Publisher | MSPUB.EXE | 16.0.20430.20140 | 通过，69 节点 |

安装配置为 `O365ProPlusRetail`、Current channel、`OfficeClientEdition="64"`、`en-us`，版本由微软当前渠道选择。程序位于 `C:\Program Files\Microsoft Office\root\Office16`。

微软说明 Windows 11 ARM 安装 64 位 Microsoft 365 Apps 时会自动包含 ARM 优化组件，因此配置与注册表中的 `x64` 标签符合这种部署方式。[微软配置文档](https://learn.microsoft.com/en-us/microsoft-365-apps/deploy/office-deployment-tool-configuration-options)。

## 来源与安装证据

- ODT 来自 [微软下载中心](https://www.microsoft.com/en-us/download/details.aspx?id=49117)，包名 `officedeploymenttool_20326-20112.exe`，工具版本 `16.0.20326.20112`。
- ODT 包和提取出的 `setup.exe` 都通过 Windows Authenticode 校验，签名发布者为 Microsoft Corporation。
- ODT 包 SHA256：`fbb64358fd4168acd52ee4efe47ffd032b6231dfb415ae2dce61b0e58ba67f86`。
- `setup.exe` SHA256：`50facf295f357d8230b4d50678536148e32f34b4ac33387269d5a72c93ff810a`。
- 实际安装运行从 15:52:06 到 16:12:58，约 20 分 51 秒，时区为 UTC+08:00；这不包含前面的下载工具与提权准备时间。
- 安装脚本只对自身 PowerShell 进程使用执行策略参数；机器的全局脚本策略保持原有设置。通过已有私有虚机控制台处理本轮安装的 UAC 请求。

配置、退出状态、安装版本与原生快照保存在 [证据目录](evidence/2026-10-03-office-install/README.md)。不提交安装二进制、账号凭据或激活密钥。

## 原生检查与限制

使用 `scripts/verify_office_startup.py` 启动专属进程，通过 xa11y / Windows UIA 读取启动窗口，再关闭脚本创建的进程。未向文档、邮箱或账号表单写入数据。

- 后台安装尚未完成时，首次检查为 6/7：PowerPoint 的 FindFirstBuildCache 超时。保留该失败记录。
- PowerPoint 单独延长启动等待到 10 秒后通过。
- 安装器退出后，统一检查七个应用，等待 5 秒，原生启动窗口读取 7/7 通过。

此处证明安装、启动及启动窗口的原生可读性。单元格编辑、Word 正文、幻灯片操作、保存文件、邮件草稿与附件选择仍需后续实测。

## 激活与后续工作

多个应用显示 `Sign in to set up Office`；OneNote 显示试用提示。尚未登录或激活，也未开启试用、购买订阅或配置真实邮箱。

用户随后明确要求只使用客户采用的微软桌面 Office，并希望避免信用卡。后续不使用替代办公套件。进一步检索微软官方文档发现：Office 在新电脑上可提供一次性的五天免费宽限许可，领取前需要接受其许可条款。这条说明证明存在短期免费许可，并不证明当前虚机已取得该许可或必然符合领取条件。[微软说明：GraceDialog / GraceEula](https://learn.microsoft.com/en-us/microsoft-365-apps/privacy/essential-services#officelicensingflowsgracedialog)。

本轮通过 Bokkio / Windows UIA 读取 Word 的启动控件，点击唯一的 `Sign in or create account`，随后通过虚机控制台确认已到 Word 内的 Microsoft 登录表单。当前仍需账号登录；未显示五天许可选择，未填写账号资料，也未提交订阅或付款。登录后再核对是否出现 `Start your 5-day pass` 及具体条款；若可领取，记录实际到期时间并实测编辑与保存。短期许可到期后仍需现有或新购的适用许可证，不能作为长期测试环境的许可来源。

用户选择先使用试用许可。2026-10-03 核对微软官方入口：Microsoft 365 Family 提供一个月试用，包含桌面办公应用；注册需要 Microsoft 账号和信用卡，默认到期自动续费。Business Standard 也提供一个月试用并要求信用卡。[Family 试用入口](https://www.microsoft.com/en-us/microsoft-365/try)、[试用 FAQ](https://www.microsoft.com/EN-US/microsoft-365/microsoft-365-for-home-and-school-faq)、[Business Standard 试用](https://www.microsoft.com/en-us/microsoft-365/business/microsoft-365-business-standard-one-month-trial)。

已在虚机 Edge 打开 Family 官方试用注册入口，确认当前停在 Microsoft 账号登录页。试用尚未领取，账号登录及付款资料需要用户在微软页面直接填写。领取后应关闭定期计费，并确认页面显示到期日期，避免试用结束收费；付款资料和账号密码不写入仓库。[微软关闭试用续费说明](https://support.microsoft.com/en-us/accounts-billing/subscriptions/cancel-your-free-trial-of-microsoft-365)。

现有桌面程序保留。领取许可后，核对实际订阅并匹配部署产品，再登录激活和验证编辑保存。当前部署为 `O365ProPlusRetail`，不能假定它已经匹配 Family 许可；微软明确说明错误的产品 ID 会导致无法激活。[产品 ID 与许可证对应表](https://learn.microsoft.com/en-us/microsoft-365/troubleshoot/installation/product-ids-supported-office-deployment-click-to-run)。

有相应许可的登录/激活完成后，再验证编辑与保存。微软说明未获许可的安装会限制编辑功能，因此本轮不将启动检查计入 OFFICE-01 完整办公流程通过。[激活文档](https://learn.microsoft.com/en-us/microsoft-365-apps/licensing-activation/overview-licensing-activation-microsoft-365-apps)。

下一步：匹配许可证并激活 Office；完成 Outlook 的测试账号或离线草稿环境；扩展应用 UIA 操作矩阵；执行 OFFICE-01 的中间业务检查和最终文件检查。整体仍在 P5 验收阶段。

## 复现启动检查

在已登录的 Windows 测试用户会话、guest 仓库中执行：

```powershell
.venv\Scripts\python.exe scripts\verify_office_startup.py --output C:\BokkioTasks\office-startup
```

## English summary

Microsoft 365 Apps installed successfully in the existing Windows 11 ARM64 VM. Word, Excel, PowerPoint, classic Outlook, OneNote, Access and Publisher are present at version 16.0.20430.20140. ODT and setup passed Microsoft signature verification; the installer exited with code 0.

The post-install native startup-window check passed for all seven apps. An earlier PowerPoint timeout is preserved and passed on retry. These checks cover startup visibility, not document editing or complete office workflows. Office activation and Outlook account configuration remain pending. The user chose a trial: Microsoft's Family offer provides one month with desktop apps, requires a Microsoft account and a credit card, and renews automatically unless recurring billing is turned off. The official trial signup entry is open in the VM at the Microsoft account sign-in screen; no trial subscription has been started. After the user completes secure signup, match the deployment product to the actual license, activate Office, verify editing and saving, then continue the P5 office capability matrix and OFFICE-01 acceptance.

The user requires Microsoft desktop Office and wants to avoid a credit card. Alternative office suites are outside scope. Microsoft's essential-services documentation describes a one-time five-day grace license on new PCs. Word was inspected and its sign-in button clicked through Windows UIA; the native Microsoft account form is open. The five-day offer has not appeared or been activated. Account sign-in is required to continue checking eligibility; actual editing, saving and expiration must be verified before reporting a usable trial.
