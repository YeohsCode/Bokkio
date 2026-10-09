# Office 后续修复 / Follow-up Office fixes

日期：2026-10-09，基础提交93fd1a1。主机回归 **411/411**，包内Swift捕获/输入helper重新编译并成功捕获自有Excel窗口。Windows本轮未重测。

## 改动与验证

- 输入前拒绝现在保留期望PID/窗口ID、实际前台PID/最上层窗口ID及事件权限。守卫条件保持原样。
- 输入后失败保留派发回执、错误cause及原生字段expected/actual/matching_targets，穿过backend包装后写入Agent trace和重规划progress；未知完成仍停止、不重试。
- 对同一已绑定字段最多回读3次，总等待0.3秒；字段身份消失时立即停止。单元测试验证延迟值、持续错误值和未知派发均只提交一次输入。这不是Word实机成功证据。
- 对具有click/expand的唯一split button，显式Click/Press/Invoke当前名称时只保留click；普通Expand意图、重复身份、narrow=false的大树路径及置信度阈值保持原有处理。
- 真实Jev读取第十轮PowerPoint的已记录合成任务快照，Click New Slide返回click、置信度 **1.0**，阈值仍0.7。没有UI派发，也没有新Agent任务分数。见[ppt-decision-probe.json](ppt-decision-probe.json)。

## 实跑边界

本轮桌面工具确认Mac锁屏且自动解锁失败；原生preflight也报告session_locked=true、权限均true。因此没有启动新的Office任务。锁屏期间读取的自有窗口范围诊断不能用于解释上轮解锁会话的Excel拒绝。

上轮十轮三题均0/3仍是最新任务成绩。解锁后需检查Word未知完成后的状态，针对Excel守卫的结构化信息定位原因，验证PPT点击/后续编辑保存，再以新输入完整复跑。当前修复没有宣称Office任务通过。

文件：[validation.json](validation.json)、[SHA256SUMS](SHA256SUMS)。后续队列见[Pending](../../PENDING.md)。未发布原始桌面截图、完整UI树或凭据。

## English

Host regression passes 411 tests. Native input now retains foreground/window rejection facts and post-input receipt/readback diagnostics through Agent traces. The same bound field can be observed up to three times without reposting; a lost binding stops immediately. Explicit clicks on one observed split button no longer compete with menu expansion.

A real Jev call against the recorded synthetic PowerPoint snapshot returned click at confidence 1.0 (threshold 0.7). This is decision-only evidence, with no live dispatch or new task score. The Mac is currently locked, so the new Office run awaits an unlocked session. The prior 0/3 artifact score remains unchanged; Windows was not retested.
