# P7.1 capture implementation evidence

日期：2026-10-08。P7 已进入实现；**当前归档不代表交互截图实机验收通过**。

- `host-tests.log`：314/314 主机隔离回归。
- `windows-build-first-tests.log`：自绘 fixture 构建成功、0 编译错误/警告；首次 Windows 回归 314/314，有一项 pytest 缓存写入警告。
- `windows-final-tests.log`：改用专用测试缓存后，最终 Windows 回归 314/314，无警告。
- `desktop-preflight.json`：实际启动自有 fixture 后，Bokkio 捕获返回 `desktop_unavailable`，未生成图像。
- `source-hashes.json` / `guest-source-hashes.json`：六份主机与 guest 源文件 SHA-256 完全一致。
- `summary.json`：P7.1 实现、构建与测试状态；三轮原生像素和六类窗口故障实测均未开始。
- `checksums.json`：当前归档文件的字节哈希。

没有保存凭证、主机个人目录、无关应用清单或登录界面图像。没有修改登录策略或安全设置。详情见 [P7.1 报告](../../P7-CAPTURE.md)。

## English

Capture implementation, fixture compilation and isolated regressions are verified; native pixel acceptance is pending an interactive Windows desktop. Both platforms pass 314 tests. The first Windows run has one cache warning and the final run has none. Real preflight on an owned fixture returns `desktop_unavailable`, without an image. Host/guest source hashes match. No credential, unrelated inventory, login image or personal host path is archived. No security/login policy changed.
