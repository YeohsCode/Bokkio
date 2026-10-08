# P7 Mac Runtime 与视觉定位 / Mac capture and visual candidates

日期：2026-10-08。**Mac 窗口截图已接入 Bokkio 包和 CLI，原生 OCR 与唯一候选定位完成实机验收。有界输入执行器已实现，真实点击/输入尚未验收通过。**

## 当前能力

- `capture` 在 macOS 使用包内 ScreenCaptureKit helper，明确绑定 PID、CGWindowID、内核进程创建时间、窗口范围、采集范围、像素/屏幕点比例、时间和 PNG SHA-256。客户区与标题栏均在捕获范围内，忽略阴影及鼠标。
- Swift helper 随 wheel 打包，首次使用通过 Apple Command Line Tools 编译至源码哈希限定的本机缓存；macOS 14+ 的 ScreenCaptureKit API 为基础，当前实测使用本机 SDK。缺少编译器/权限、窗口歧义、几何变化、工作进程超时等返回结构化错误。
- `--ocr` 在本机执行 Apple Vision revision 3，准确模式，配置 English / Simplified Chinese 且关闭语言校正。本轮业务验收文字为英文，中文业务任务尚未验收。
- `visual-find` 对同一 PNG 的 OCR 精确文字做置信度、时效、范围与哈希校验；重复标签拒绝，Python API 可以通过明确区域消除歧义。输出含图像/屏幕坐标与窗口身份，`action_authorized=false`。
- `visual_input.perform` 为单次显式 click/type 请求；必须提供 OCR 目标与操作后预期文字。检查图像、进程、窗口及原始几何，要求当前输入会话与前台窗口可用，限制文本长度/控制字符，并在派发后重新捕获/OCR 核验。没有回执或验证失败均为 `input_completion_unknown`，不自动重试。

输入 API 不是自动 Agent 降级链路。Planner/Jev/Workflow 尚未接入 OCR 候选；完整取消、限速、坐标步骤重放、跨应用视觉任务和 Windows OCR 仍待实现/验收。

## 实机与回归结果

| 检查 | 结果 |
|---|---|
| 三次独立自绘应用启动 | **3/3**；窗口身份、PNG/CRC、四角色块、fixture 几何、OCR 按钮/输入区域中心及屏幕坐标全部通过 |
| 独立业务区域检查 | “Run check” 中心落在实际绘制按钮中，“Enter code” 中心落在输入区域中；窗口无内部 Cocoa 控件 |
| 八类拒绝 | **8/8**：未知文字、图像篡改、过期截图、错误窗口 ID、关闭进程、同名文字、同名窗口及最小化 |
| 明确范围恢复 | 同名文字以指定区域定位通过；同名窗口以准确 CGWindowID 捕获通过 |
| CLI 实机 | `capture --ocr` 与 `visual-find` 均返回 0，目标身份/坐标正确 |
| 主机与 Windows 隔离回归 | **各 355/355**；guest 源码哈希匹配本次代码，Windows 交互截图仍待验收 |
| Wheel | 构建成功，包内包含 Swift helper；原生 helper 构建和本机调用成功 |
| 输入前置实测 | `input_desktop_unavailable`，回执 `dispatched=0`；无鼠标/键盘事件派发，正向点击/输入不计作通过 |

自绘 fixture 的业务文字、按钮和输入框均由 NSView 绘制；没有 NSButton/NSTextField 子控件。本轮 AX 返回 application 代理，尚未独立验证解锁后 AX 树是否按预期省略这些业务区域。没有使用浏览器、DOM 或外部模型读取截图。

## 轮次与修正

1. Runtime 首次使用 NSRunningApplication 的 launchDate 绑定进程，但该信息在当前启动方式下不可用；改用 `proc_pidinfo` 的创建秒/微秒。
2. 第一次 OCR 候选检查发现 Vision 归一化边界的浮点误差产生微小负坐标；原生转换后与图像范围求交，再进行严格候选校验。
3. runtime v1、v2、v3 分开归档。最终 v3 的三轮正常流程与八类拒绝全部通过，源码哈希匹配当前实现。
4. 输入原型与最终前置实测均在派发前拒绝。截图可用不等于前台输入可用；没有修改登录策略或安全设置，也没有尝试通过事件绕过会话限制。

这些结果限于本机、自有 fixture 与当前比例；多显示器/多 DPI、窗口移动竞争、真实办公布局、OCR 合并文本行、第三方 GPU 应用和更多可靠性故障仍需扩展。正常流程分母为三次独立初始状态，不能视为完整桌面成功率。

## 使用

```sh
uv run bokkio capture --pid PID --title BokkioVisual --ocr --timeout 15 --output /tmp/new-window.png
uv run bokkio visual-find --image /tmp/new-window.png --metadata /tmp/new-window.png.json --text "Run check"
```

Python：`bokkio.macos_capture.capture_window`、`bokkio.visual.find_text`、`bokkio.visual_input.perform`。输出拒绝覆盖，截图查找默认时效 15 秒。区域坐标为图像像素，Mac 输入点为屏幕点；不会再次乘 DPI 比例。捕获/候选可独立使用，输入要求额外的环境和验证条件。

验收命令：先构建 `fixtures/cocoa-visual/main.swift` 为 `BokkioVisual.app`，再运行 `scripts/verify_macos_visual.py --fixture APP --output NEW_DIR`。

证据见 [归档索引](evidence/2026-10-08-p7-macos-runtime/README.md)。下一步完成输入正向验收与自动降级策略，再扩展视觉回路和跨应用任务。

## English

Mac scoped capture is integrated into the Bokkio package and CLI, with a bundled, source-hash-cached Swift helper. Capture binds PID/window ID, kernel process birth, geometry, screen-point mapping, time and PNG hash. Local Apple Vision OCR produces text/confidence/pixel boxes; exact candidate selection rejects stale/tampered images and ambiguity. Candidates do not authorize input.

Final native capture/OCR acceptance passes 3/3 independent painted-window runs and 8/8 rejection cases. Explicit region and window-ID disambiguation pass, as do real capture/find CLI calls. Host and Windows each pass 355 tests; guest source hashes match. Wheel packaging includes the native helper. English labels were tested; configured Chinese OCR is not business-task acceptance.

Bounded click/type code requires scoped foreground input, unchanged image/geometry/process identity, literal text and explicit post-action OCR verification. Unknown completion never retries. Real input preflight returns `input_desktop_unavailable` with zero dispatch; positive click/type acceptance is pending. Planner/Jev/Workflow visual integration, full reliability, Windows OCR, broader applications and multi-display/DPI coverage remain separate work. Historical diagnostic and failed initialization records are preserved.
