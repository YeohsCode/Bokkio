# Mac path recheck evidence

2026-10-08。仅新建的自有 Cocoa fixture，按 PID 和准确窗口标题限定。

- `session-preflight.json`：AX/屏幕录制预检查为 true；当前测试会话锁定标志为 true，不等于对用户物理屏幕的观察。
- `controls-preflight.json`、`xa11y-preflight.json`：嵌套 application / 零窗口，原生动作未开始。
- `native-ax-counts.json`、`native-ax-roles.json`：直接 AXWindows 有一个条目，但角色仍为 AXApplication。
- `capture-pid-only.json`：同 PID 两个窗口，拒绝歧义。
- `capture-v1.json`：图形初始化崩溃 0/3。
- `capture-v2.json`：初始化 Cocoa / MainActor 后修正，三轮截图生成成功。
- `capture-v3.json`、`owned-window-*.png`：仓库可复现脚本三轮 3/3；PNG/PID/尺寸/哈希独立检查，样图完整。
- `checksums.json`：归档字节哈希。

没有输入、授权变更、账户数据或无关应用截图。仅说明 Mac 窗口捕获诊断可继续；Runtime 接入、完整 P7 验收和 AX 动作仍待完成。详见 [报告](../../MACOS-CAPTURE-PROBE.md)。

## English

Owned-fixture capture diagnostics succeed independently of CUA. The initial graphics initialization crash remains 0/3; corrected v2 and reproducible v3 are separate. V3 passes 3/3 PID/PNG-dimension/hash checks. Current AX returns application proxies, including direct native reads. No inputs, account data, unrelated windows or security changes are included. This is diagnostic evidence, not complete P7 Runtime acceptance.
