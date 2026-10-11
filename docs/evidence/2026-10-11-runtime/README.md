# Runtime 开发验收证据

日期：2026-10-11。接口版本 `bokkio.runtime.v1`，工作候选版本 0.2.0。

此目录只收录自有 fixture、系统 Calculator 和本地 Browser 的摘要，不收录原始截图、私有 SQLite、账号身份或主机路径。不同开发修订不合并成固定版本稳定率。

- `icon-click-summary.json`：无 OCR 图标点击 3/3，原始窗口业务 JSON 确认点击数。
- `code-native-summary.json`：生成 Python 代码调用委派 SDK，原生字段和 CSV 独立核对 3/3。
- `calculator-summary.json`：通用 ref 动作计算 1+2=3，3/3；Core 没有 Calculator 分支。
- `wheel-acceptance-summary.json`：独立虚拟环境安装 wheel 后，代码、Browser、原生字段、官方 MCP、CLI、管理员审批和日志对账；零派发 stale 拒绝可以重新观察，尝试保留。
- `visual-input-r1-summary.json` / `visual-input-r2-summary.json`：三个新自绘进程中文输入与无文字图标点击。r1 2/3，r2 3/3；r2 没有放宽驱动时效/身份校验，仅在已知零派发时重新观察。

固定最新包的复测另存 final 摘要。`SHA256SUMS` 对应本目录 JSON。客户业务样本和 Windows 实机验收尚待完成，见 [交付状态](../../RUNTIME-DELIVERY.md)。

- `delivery-wheel-summary.json` / `delivery-visual-summary.json`：最终代码独立 wheel 的固定三轮结果。
- `handoff-validation-summary.json`：本次 Git 共享文档、541 项回归、构建与凭据排除检查；Windows 登录成功，但未运行当前 Runtime 实机矩阵。
